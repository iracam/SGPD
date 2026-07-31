"""Phase 7, slice 1: the durable outbox behind every notification."""

# ruff: noqa: F811

from __future__ import annotations

from datetime import timedelta
from io import StringIO
from smtplib import SMTPException
from typing import Any
from unittest import mock

import pytest
from django.core import mail
from django.core.exceptions import ValidationError
from django.core.management import call_command
from django.db import IntegrityError, connection, transaction
from django.utils import timezone

from apps.accounts.models import (
    PEOPLE_DEPARTMENT_ROLE_CODE,
    Role,
    RoleAssignment,
    ScopeType,
    User,
    build_scope_key,
)
from apps.notifications.deadlines import ScanDeadlinesCommand, ScanDeadlinesService
from apps.notifications.models import (
    Notification,
    NotificationAttempt,
    NotificationEvent,
    NotificationStatus,
)
from apps.notifications.services import (
    STALE_ATTEMPT_ERROR,
    DispatchNotificationsCommand,
    DispatchNotificationsService,
    DispatchResult,
    EnqueueNotificationCommand,
    EnqueueNotificationService,
    EnqueueResult,
)
from apps.offboarding.models import OffboardingProcess, ProcessSectorTask
from apps.sectors.models import SectorResponsible, ValidationSector
from tests.test_offboarding_start import (  # noqa: F401
    PASSWORD,
    actor,
    configured_draft,
    process,
    start,
)
from tests.test_offboarding_tasks import started_task

pytestmark = pytest.mark.django_db


def build_notification(
    *,
    task: ProcessSectorTask,
    recipient: User,
    dedup_key: str = "TAREFA_VENCIDA:EMAIL:task:1:user:1",
    **overrides: Any,
) -> Notification:
    fields: dict[str, Any] = {
        "event": NotificationEvent.TASK_OVERDUE,
        "dedup_key": dedup_key,
        "process": task.process,
        "task": task,
        "sector": task.sector,
        "recipient": recipient,
        "recipient_email": recipient.email,
        "subject": "Tarefa vencida no processo demissional",
        "body": "A tarefa do setor está vencida e aguarda conclusão.",
        "context": {"task_id": task.pk},
        "next_attempt_at": timezone.now(),
    }
    fields.update(overrides)
    return Notification(**fields)


def test_outbox_row_survives_full_clean_where_the_bank_does_not_compare_boolean(
    actor: User,
    process: Any,
) -> None:
    """Notificação pendente tem `sent_at` ausente e isso não pode virar violação.

    Mesma armadilha da Fase 6: `Q.check()` só envolve a condição em
    `Coalesce(..., True)` onde `supports_comparing_boolean_expr` é verdadeiro —
    no Oracle é falso. A condição precisa decidir o caso ausente sozinha, senão
    nenhuma notificação chega a ser enfileirada no DEV.
    """

    task = started_task(actor, process)
    notification = build_notification(task=task, recipient=actor)

    with mock.patch.object(connection.features, "supports_comparing_boolean_expr", False):
        notification.full_clean()

        notification.status = NotificationStatus.SENT
        with pytest.raises(ValidationError) as sent_without_instant:
            notification.full_clean()

    assert "SGPD_CK_NOTIF_SENT_AT" in str(sent_without_instant.value)


def test_dedup_key_blocks_the_same_milestone_twice(actor: User, process: Any) -> None:
    task = started_task(actor, process)
    first = build_notification(task=task, recipient=actor)
    first.full_clean()
    first.save()

    duplicate = build_notification(task=task, recipient=actor)
    with pytest.raises(IntegrityError), transaction.atomic():
        duplicate.save()


def test_outbox_rejects_bulk_writes_and_deletion(actor: User, process: Any) -> None:
    task = started_task(actor, process)
    notification = build_notification(task=task, recipient=actor)
    notification.full_clean()
    notification.save()

    with pytest.raises(ValidationError):
        Notification.objects.filter(pk=notification.pk).update(
            status=NotificationStatus.SENT,
        )
    with pytest.raises(ValidationError):
        Notification.objects.filter(pk=notification.pk).delete()
    with pytest.raises(ValidationError):
        notification.delete()


def test_notification_requires_recipient_address_and_a_task_of_its_own_process(
    actor: User,
    process: Any,
) -> None:
    task = started_task(actor, process)

    without_address = build_notification(task=task, recipient=actor, recipient_email="")
    with pytest.raises(ValidationError) as missing_address:
        without_address.full_clean()
    assert "recipient_email" in missing_address.value.message_dict

    foreign = build_notification(task=task, recipient=actor)
    foreign.process = _other_process(process)
    with pytest.raises(ValidationError) as foreign_task:
        foreign.full_clean()
    assert "task" in foreign_task.value.message_dict


def _other_process(process: Any) -> Any:
    return OffboardingProcess.objects.create(
        company_code=process.company_code,
        branch_code=process.branch_code,
        employee_type_code=process.employee_type_code,
        employee_registration=process.employee_registration + 1,
        active_employee_key=f"{process.active_employee_key}-outro",
        opened_by=process.opened_by,
        planned_termination_date=process.planned_termination_date,
        due_date=process.due_date,
        reason=process.reason,
        priority=process.priority,
    )


def test_delivery_attempt_is_open_or_closed_as_a_whole(actor: User, process: Any) -> None:
    task = started_task(actor, process)
    notification = build_notification(task=task, recipient=actor)
    notification.full_clean()
    notification.save()

    attempt = NotificationAttempt(notification=notification, attempt_number=1)
    attempt.full_clean()
    attempt.save()
    assert attempt.finished_at is None and attempt.succeeded is None

    attempt.succeeded = True
    with pytest.raises(ValidationError) as half_closed:
        attempt.full_clean()
    assert "SGPD_CK_NOTIF_ATT_CLOSED" in str(half_closed.value)

    attempt.finished_at = timezone.now()
    attempt.full_clean()
    attempt.save()

    with pytest.raises(ValidationError):
        attempt.delete()


# --- Fatia 2: enfileiramento, mensagem e despacho ---------------------------


def enqueue(
    task: ProcessSectorTask,
    recipients: tuple[User, ...],
    *,
    event: str = NotificationEvent.TASK_OVERDUE,
    scope: str = "",
) -> EnqueueResult:
    return EnqueueNotificationService().execute(
        EnqueueNotificationCommand(
            event=event,
            process=task.process,
            task=task,
            recipients=recipients,
            scope=scope,
        )
    )


def test_enqueue_writes_one_message_per_recipient_and_never_repeats_the_milestone(
    actor: User,
    process: Any,
) -> None:
    task = started_task(actor, process)
    other = User.objects.create_user(
        username="setor.dois",
        email="setor.dois@example.invalid",
        password=PASSWORD,
        first_name="Setor",
        last_name="Dois",
    )

    first = enqueue(task, (actor, other, actor))
    assert len(first.created) == 2
    assert first.duplicated == 0

    again = enqueue(task, (actor, other))
    assert again.created == () and again.duplicated == 2
    assert Notification.objects.count() == 2

    message = Notification.objects.get(recipient=actor)
    assert message.status == NotificationStatus.PENDING
    assert message.subject.startswith("Tarefa vencida no setor")
    assert str(task.process.uuid)[:8] in message.body
    assert "/fe/tarefas" in message.body


def test_enqueue_skips_recipient_without_address_without_losing_the_others(
    actor: User,
    process: Any,
) -> None:
    task = started_task(actor, process)
    silent = User.objects.create_user(
        username="sem.email",
        password=PASSWORD,
        first_name="Sem",
        last_name="Email",
    )

    result = enqueue(task, (actor, silent))

    assert len(result.created) == 1
    assert result.without_address == (silent.pk,)


def test_enqueue_refuses_an_event_without_message_template(
    actor: User,
    process: Any,
) -> None:
    task = started_task(actor, process)

    with pytest.raises(ValidationError):
        enqueue(task, (actor,), event="EVENTO_INEXISTENTE")


def test_dispatch_sends_the_queue_and_closes_the_attempt(actor: User, process: Any) -> None:
    task = started_task(actor, process)
    enqueue(task, (actor,))

    result = DispatchNotificationsService().execute(DispatchNotificationsCommand())

    assert result.sent == 1 and result.failed == 0 and result.rescheduled == 0
    assert len(mail.outbox) == 1
    assert mail.outbox[0].to == [actor.email]

    message = Notification.objects.get()
    assert message.status == NotificationStatus.SENT
    assert message.sent_at is not None and message.attempts == 1
    attempt = message.delivery_attempts.get()
    assert attempt.succeeded is True and attempt.finished_at is not None
    assert attempt.error == ""

    assert DispatchNotificationsService().execute(DispatchNotificationsCommand()).sent == 0
    assert len(mail.outbox) == 1


def test_dispatch_reschedules_with_backoff_and_gives_up_after_the_last_attempt(
    actor: User,
    process: Any,
) -> None:
    task = started_task(actor, process)
    enqueue(task, (actor,))
    message = Notification.objects.get()
    message.max_attempts = 2
    message.save(update_fields=("max_attempts",))

    with mock.patch(
        "apps.notifications.services.EmailMessage.send",
        side_effect=SMTPException("mailbox unavailable"),
    ):
        first = DispatchNotificationsService().execute(DispatchNotificationsCommand())
        message.refresh_from_db()
        assert first.rescheduled == 1 and first.failed == 0
        assert message.status == NotificationStatus.PENDING
        assert message.next_attempt_at > timezone.now()
        assert "mailbox unavailable" in message.last_error

        # A espera do backoff é real: sem avançar o relógio nada é tentado.
        assert DispatchNotificationsService().execute(DispatchNotificationsCommand()) == (
            DispatchResult(sent=0, failed=0, rescheduled=0, requeued=0)
        )

        message.next_attempt_at = timezone.now()
        message.save(update_fields=("next_attempt_at",))
        second = DispatchNotificationsService().execute(DispatchNotificationsCommand())

    message.refresh_from_db()
    assert second.failed == 1
    assert message.status == NotificationStatus.FAILED
    assert message.attempts == 2
    assert message.delivery_attempts.count() == 2
    assert all(attempt.succeeded is False for attempt in message.delivery_attempts.all())


def test_dispatch_reopens_a_message_left_in_flight(actor: User, process: Any) -> None:
    task = started_task(actor, process)
    enqueue(task, (actor,))
    message = Notification.objects.get()
    message.status = NotificationStatus.SENDING
    message.attempts = 1
    message.save(update_fields=("status", "attempts"))
    NotificationAttempt.objects.create(notification=message, attempt_number=1)

    result = DispatchNotificationsService().execute(
        DispatchNotificationsCommand(stale_after=timedelta(seconds=0))
    )

    message.refresh_from_db()
    assert result.requeued == 1
    assert message.status in {NotificationStatus.PENDING, NotificationStatus.SENT}
    attempt = message.delivery_attempts.get(attempt_number=1)
    assert attempt.succeeded is False
    assert attempt.error == STALE_ATTEMPT_ERROR


def test_dispatch_command_is_the_entry_point_of_the_queue(actor: User, process: Any) -> None:
    task = started_task(actor, process)
    enqueue(task, (actor,))
    output = StringIO()

    call_command("sgpd_dispatch_notifications", "--limit", "10", stdout=output)

    assert "enviadas=1" in output.getvalue()
    assert Notification.objects.get().status == NotificationStatus.SENT


# --- Fatia 3: varredura de prazos, lembretes e escaladas --------------------


def overdue(task: ProcessSectorTask, *, hours: int) -> ProcessSectorTask:
    task.due_at = timezone.now() - timedelta(hours=hours)
    task.save(update_fields=("due_at",))
    return task


def queued_events(**filters: Any) -> set[str]:
    return set(Notification.objects.filter(**filters).values_list("event", flat=True))


def test_scan_queues_every_reached_milestone_once(actor: User, process: Any) -> None:
    overdue(started_task(actor, process), hours=72)

    first = ScanDeadlinesService().execute(ScanDeadlinesCommand())

    assert queued_events() == {
        NotificationEvent.TASK_DUE_SOON,
        NotificationEvent.TASK_DUE_IMMINENT,
        NotificationEvent.TASK_OVERDUE,
        NotificationEvent.TASK_OVERDUE_CRITICAL,
    }
    assert first.queued == 4 and first.tasks_scanned == 1

    again = ScanDeadlinesService().execute(ScanDeadlinesCommand())

    assert again.queued == 0
    assert Notification.objects.count() == 4


def test_scan_stops_at_the_milestone_the_clock_reached(actor: User, process: Any) -> None:
    task = started_task(actor, process)
    task.due_at = timezone.now() + timedelta(hours=30)
    task.save(update_fields=("due_at",))

    ScanDeadlinesService().execute(ScanDeadlinesCommand())

    assert queued_events() == {NotificationEvent.TASK_DUE_SOON}


def test_overdue_reaches_people_department_and_critical_reaches_the_escalation_sector(
    actor: User,
    process: Any,
) -> None:
    task = overdue(started_task(actor, process), hours=72)
    people = User.objects.create_user(
        username="dp.escopo",
        email="dp.escopo@example.invalid",
        password=PASSWORD,
        first_name="DP",
        last_name="Escopo",
    )
    RoleAssignment.objects.create(
        user=people,
        role=Role.objects.get(code=PEOPLE_DEPARTMENT_ROLE_CODE),
        scope_type=ScopeType.GLOBAL,
        scope_key=build_scope_key(ScopeType.GLOBAL, None, None),
        valid_from=timezone.now() - timedelta(days=1),
        assigned_by=actor,
    )
    escalation_owner = User.objects.create_user(
        username="escalada.dono",
        email="escalada.dono@example.invalid",
        password=PASSWORD,
        first_name="Escalada",
        last_name="Dono",
    )
    escalation = ValidationSector.objects.create(
        code="ESCALADA",
        name="Escalada",
        default_due_hours=24,
    )
    SectorResponsible.objects.create(
        sector=escalation,
        user=escalation_owner,
        valid_from=timezone.now() - timedelta(hours=1),
        assigned_by=actor,
        updated_by=actor,
    )
    task.sector.escalation_sector = escalation
    task.sector.save(update_fields=("escalation_sector",))

    ScanDeadlinesService().execute(ScanDeadlinesCommand())

    def recipients(event: str) -> set[str]:
        return set(
            Notification.objects.filter(event=event).values_list("recipient__username", flat=True)
        )

    assert recipients(NotificationEvent.TASK_DUE_SOON) == {actor.username}
    assert recipients(NotificationEvent.TASK_OVERDUE) == {actor.username, people.username}
    assert recipients(NotificationEvent.TASK_OVERDUE_CRITICAL) == {
        actor.username,
        people.username,
        escalation_owner.username,
    }


def test_milestone_without_anyone_to_warn_is_counted_and_queues_nothing(
    actor: User,
    process: Any,
) -> None:
    task = started_task(actor, process)
    task.due_at = timezone.now() + timedelta(hours=30)
    task.save(update_fields=("due_at",))
    responsibility = SectorResponsible.objects.get(sector=task.sector, user=actor)
    responsibility.valid_until = timezone.now() - timedelta(minutes=1)
    responsibility.save(update_fields=("valid_until",))

    result = ScanDeadlinesService().execute(ScanDeadlinesCommand())

    assert result.queued == 0
    assert result.without_recipients == 1
    assert not Notification.objects.exists()


def test_process_near_its_deadline_warns_the_people_department(
    actor: User,
    process: Any,
) -> None:
    task = started_task(actor, process)
    task.due_at = timezone.now() + timedelta(days=30)
    task.save(update_fields=("due_at",))
    process.due_date = timezone.localdate()
    process.save(update_fields=("due_date",))

    result = ScanDeadlinesService().execute(ScanDeadlinesCommand())

    message = Notification.objects.get(event=NotificationEvent.PROCESS_DUE_SOON)
    assert result.processes_scanned == 1
    assert message.recipient == actor
    assert message.task_id is None
    assert "1 tarefa(s)" in message.body


def test_scan_command_can_dispatch_in_the_same_run(actor: User, process: Any) -> None:
    overdue(started_task(actor, process), hours=72)
    output = StringIO()

    call_command("sgpd_scan_notifications", "--dispatch", stdout=output)

    assert "enfileiradas=4" in output.getvalue()
    assert "enviadas=4" in output.getvalue()
    assert len(mail.outbox) == 4
