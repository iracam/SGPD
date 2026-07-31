"""Phase 7, slice 1: the durable outbox behind every notification."""

# ruff: noqa: F811

from __future__ import annotations

from typing import Any
from unittest import mock

import pytest
from django.core.exceptions import ValidationError
from django.db import IntegrityError, connection, transaction
from django.utils import timezone

from apps.accounts.models import User
from apps.notifications.models import (
    Notification,
    NotificationAttempt,
    NotificationEvent,
    NotificationStatus,
)
from apps.offboarding.models import OffboardingProcess, ProcessSectorTask
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
