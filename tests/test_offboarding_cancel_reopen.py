"""Fase 8: cancelamento terminal e reabertura controlada (RF-031, RF-032)."""

# ruff: noqa: F811

from __future__ import annotations

from typing import Any

import pytest
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import connection

from apps.accounts.models import User
from apps.notifications.models import Notification, NotificationEvent
from apps.offboarding.models import (
    OffboardingProcess,
    ProcessAuditEvent,
    ProcessEventType,
    ProcessSectorTask,
    ProcessStatus,
    SectorTaskStatus,
)
from apps.offboarding.services import (
    CancelProcessCommand,
    CancelProcessService,
    IdempotencyConflict,
    ReopenProcessCommand,
    ReopenProcessService,
    open_processes_for_actor,
    sector_tasks_for_actor,
)
from apps.pending_items.models import BlockingLevel, PendingItem
from tests.test_offboarding_release import (
    close,
    manager_coordinator,
    ready_process,
    register_processing,
    release,
)
from tests.test_offboarding_start import (  # noqa: F401
    PASSWORD,
    actor,
    process,
)
from tests.test_offboarding_tasks import complete_task, start_task, started_task
from tests.test_pending_items_evidence import create_pending

pytestmark = pytest.mark.django_db


def cancel(
    actor: User,
    process: OffboardingProcess,
    *,
    key: str = "cancel-1",
    expected_version: int | None = None,
    reason: str = "Colaborador desistiu do desligamento.",
) -> Any:
    return CancelProcessService().execute(
        CancelProcessCommand(
            actor=actor,
            process_uuid=str(process.uuid),
            expected_version=expected_version if expected_version is not None else process.version,
            idempotency_key=key,
            reason=reason,
        )
    )


def reopen(
    actor: User,
    process: OffboardingProcess,
    *,
    key: str = "reopen-1",
    expected_version: int | None = None,
    reason: str = "Rescisão anulada pelo Jurídico.",
    task_ids: tuple[int, ...] = (),
) -> Any:
    return ReopenProcessService().execute(
        ReopenProcessCommand(
            actor=actor,
            process_uuid=str(process.uuid),
            expected_version=expected_version if expected_version is not None else process.version,
            idempotency_key=key,
            reason=reason,
            task_ids=task_ids,
        )
    )


def superadmin() -> User:
    return User.objects.create_superuser(
        username="super.reabertura",
        email="super.reabertura@example.invalid",
        password=PASSWORD,
    )


def test_cancel_kills_open_tasks_frees_the_key_and_keeps_the_history(
    actor: User,
    process: OffboardingProcess,
) -> None:
    task = started_task(actor, process)
    start_task(actor, task)
    task.refresh_from_db()
    pending_item = create_pending(
        actor,
        task,
        blocking_level=BlockingLevel.BLOCKING,
    ).pending_item
    process.refresh_from_db()
    expected_version = process.version

    result = cancel(actor, process, expected_version=expected_version)
    replay = cancel(actor, process, expected_version=expected_version)
    process.refresh_from_db()
    task.refresh_from_db()

    assert not result.replayed
    assert replay.replayed
    assert process.status == ProcessStatus.CANCELLED
    assert process.cancelled_by == actor
    assert process.cancelled_at is not None
    assert process.cancellation_reason == "Colaborador desistiu do desligamento."
    # A chave sai de circulação: outro processo pode ser aberto para o mesmo
    # colaborador (ADR-051).
    assert process.active_employee_key is None
    assert process.version == expected_version + 1
    assert task.status == SectorTaskStatus.CANCELLED

    cancellation = ProcessAuditEvent.objects.get(
        process=process,
        event_type=ProcessEventType.CANCELLED,
    )
    assert cancellation.data["cancelled_task_ids"] == [task.pk]
    assert cancellation.data["reason"] == "Colaborador desistiu do desligamento."
    assert (
        ProcessAuditEvent.objects.filter(
            process=process,
            event_type=ProcessEventType.SECTOR_TASK_CANCELLED,
        ).count()
        == 1
    )
    # Nada do histórico é apagado; a tarefa apenas some da lista do setor.
    assert PendingItem.objects.filter(pk=pending_item.pk).exists()
    assert list(sector_tasks_for_actor(actor)) == []
    assert list(open_processes_for_actor(actor)) == []


def test_cancel_warns_the_sector_that_still_had_work(
    actor: User,
    process: OffboardingProcess,
) -> None:
    task = started_task(actor, process)
    process.refresh_from_db()

    cancel(actor, process)

    message = Notification.objects.get(event=NotificationEvent.PROCESS_CANCELLED)
    assert message.recipient == actor
    assert message.task_id == task.pk
    assert task.sector.name in message.subject


def test_cancelling_a_draft_needs_no_task_and_frees_the_key(
    actor: User,
    process: OffboardingProcess,
) -> None:
    cancel(actor, process)
    process.refresh_from_db()

    assert process.status == ProcessStatus.CANCELLED
    assert process.started_at is None
    assert process.active_employee_key is None
    assert not ProcessSectorTask.objects.filter(process=process).exists()
    assert not Notification.objects.filter(event=NotificationEvent.PROCESS_CANCELLED).exists()


def test_cancel_refuses_empty_reason_stale_version_and_a_reused_key(
    actor: User,
    process: OffboardingProcess,
) -> None:
    with pytest.raises(ValidationError) as without_reason:
        cancel(actor, process, reason="   ")
    assert "reason" in without_reason.value.message_dict

    with pytest.raises(ValidationError, match="alterado por outra sessão"):
        cancel(actor, process, expected_version=process.version + 5)

    process.refresh_from_db()
    assert process.status == ProcessStatus.DRAFT

    cancel(actor, process, key="cancel-conflito")
    process.refresh_from_db()

    with pytest.raises(IdempotencyConflict):
        cancel(
            actor,
            process,
            key="cancel-conflito",
            reason="Outro motivo.",
        )


def test_plain_dp_cannot_cancel_a_released_process(
    actor: User,
    process: OffboardingProcess,
) -> None:
    """Desfazer ato formal é da gerência; `DP` puro para na liberação (ADR-056)."""

    process, _ = ready_process(actor, process)
    release(actor, process)
    process.refresh_from_db()

    with pytest.raises(PermissionDenied, match="gerência do Departamento Pessoal"):
        cancel(actor, process, key="cancel-liberado")

    process.refresh_from_db()
    assert process.status == ProcessStatus.RELEASED


def test_manager_cancels_a_closed_process_preserving_the_formal_marks(
    actor: User,
    process: OffboardingProcess,
) -> None:
    """Cancelar o encerrado não reescreve a história: acrescenta o fim dela (ADR-056)."""

    process, _ = ready_process(actor, process)
    release(actor, process)
    process.refresh_from_db()
    register_processing(actor, process)
    process.refresh_from_db()
    close(actor, process)
    process.refresh_from_db()
    assert process.status == ProcessStatus.CLOSED
    released_at = process.released_at
    closed_at = process.closed_at

    manager = manager_coordinator(actor)
    cancel(manager, process, key="cancel-encerrado", reason="Rescisão anulada em juízo.")

    process.refresh_from_db()
    assert process.status == ProcessStatus.CANCELLED
    assert process.cancelled_by == manager
    assert process.cancellation_reason == "Rescisão anulada em juízo."
    # As marcas do que aconteceu antes continuam gravadas.
    assert process.released_at == released_at
    assert process.closed_at == closed_at
    assert process.termination_reference
    event = ProcessAuditEvent.objects.filter(
        process=process,
        event_type=ProcessEventType.CANCELLED,
    ).get()
    assert event.actor == manager


def test_cancelling_an_already_cancelled_process_is_refused(
    actor: User,
    process: OffboardingProcess,
) -> None:
    started_task(actor, process)
    process.refresh_from_db()
    cancel(actor, process, key="cancel-primeiro")
    process.refresh_from_db()

    with pytest.raises(ValidationError, match="já está cancelado"):
        cancel(actor, process, key="cancel-segundo")


def test_sector_responsible_without_dp_cannot_cancel(
    actor: User,
    process: OffboardingProcess,
) -> None:
    started_task(actor, process)
    process.refresh_from_db()
    responsible = User.objects.create_user(
        username="responsavel.cancelamento",
        email="responsavel.cancelamento@example.invalid",
        password=PASSWORD,
    )

    with pytest.raises(PermissionDenied, match="papel DP"):
        cancel(responsible, process)

    process.refresh_from_db()
    assert process.status == ProcessStatus.STARTED


def test_reopen_is_exclusive_to_the_superadmin(
    actor: User,
    process: OffboardingProcess,
) -> None:
    """O `DP` que liberou não desfaz o próprio ato sozinho (ADR-051)."""

    process, _ = ready_process(actor, process)
    release(actor, process)
    process.refresh_from_db()

    with pytest.raises(PermissionDenied, match="SuperAdmin"):
        reopen(actor, process)

    process.refresh_from_db()
    assert process.status == ProcessStatus.RELEASED
    assert not ProcessAuditEvent.objects.filter(
        process=process,
        event_type=ProcessEventType.REOPENED,
    ).exists()


def test_reopening_retakes_the_key_even_when_it_reads_back_as_an_empty_string(
    actor: User,
    process: OffboardingProcess,
) -> None:
    """A chave liberada volta do Oracle como `''`, não como `None`.

    O Oracle guarda a chave liberada em NULL, mas o backend do Django devolve
    string vazia ao ler um `CharField`. Uma reabertura que só reconhecesse
    `None` deixaria o processo voltar à ativa sem retomar a chave, e a unicidade
    do banco — a árbitra da ADR-051 — nunca seria consultada: dois processos
    vivos para o mesmo colaborador. Aqui a leitura do Oracle é reproduzida
    gravando a string vazia.
    """

    process, _task = ready_process(actor, process)
    release(actor, process)
    process.refresh_from_db()
    register_processing(actor, process)
    process.refresh_from_db()
    close(actor, process)
    process.refresh_from_db()
    with connection.cursor() as cursor:
        cursor.execute(
            "UPDATE SGPD_OFFBOARDING_PROCESS SET ACTIVE_EMPLOYEE_KEY = '' WHERE ID = %s",
            [process.pk],
        )
    process.refresh_from_db()
    assert process.active_employee_key == ""

    reopen(superadmin(), process, expected_version=process.version)
    process.refresh_from_db()

    assert process.status == ProcessStatus.STARTED
    assert process.active_employee_key == "1:2:1:321"


def test_reopening_a_closed_process_retakes_the_key_and_returns_the_task(
    actor: User,
    process: OffboardingProcess,
) -> None:
    process, task = ready_process(actor, process)
    release(actor, process)
    process.refresh_from_db()
    register_processing(actor, process)
    process.refresh_from_db()
    close(actor, process)
    process.refresh_from_db()
    assert process.active_employee_key is None
    expected_version = process.version
    admin = superadmin()

    result = reopen(admin, process, expected_version=expected_version, task_ids=(task.pk,))
    replay = reopen(admin, process, expected_version=expected_version, task_ids=(task.pk,))
    process.refresh_from_db()
    task.refresh_from_db()

    assert not result.replayed
    assert replay.replayed
    assert process.status == ProcessStatus.STARTED
    assert process.released_at is None and process.released_by is None
    assert process.processing_registered_at is None
    assert process.termination_reference == ""
    assert process.termination_processed_on is None
    assert process.closed_at is None and process.closed_by is None
    assert process.active_employee_key == "1:2:1:321"
    assert task.status == SectorTaskStatus.IN_ANALYSIS
    assert task.completed_at is None and task.completed_by is None

    event = ProcessAuditEvent.objects.get(
        process=process,
        event_type=ProcessEventType.REOPENED,
    )
    assert event.actor == admin
    assert event.data["reason"] == "Rescisão anulada pelo Jurídico."
    assert event.data["reopening"] == 1
    assert event.data["reopened_task_ids"] == [task.pk]
    # O estado anterior é o que a `WORKFLOWS.md` §8 exige registrar.
    assert event.data["previous_state"]["status"] == ProcessStatus.CLOSED
    assert event.data["previous_state"]["termination_reference"] == "RES-2026-0001"
    assert (
        ProcessAuditEvent.objects.filter(
            process=process,
            event_type=ProcessEventType.SECTOR_TASK_REOPENED,
        ).count()
        == 1
    )
    # O trabalho voltou para o setor: o processo reaparece no card de abertos.
    assert list(open_processes_for_actor(actor)) == [process]
    assert list(sector_tasks_for_actor(actor)) == [task]


def test_reopening_without_task_only_undoes_the_formal_mark(
    actor: User,
    process: OffboardingProcess,
) -> None:
    process, task = ready_process(actor, process)
    release(actor, process)
    process.refresh_from_db()
    admin = superadmin()

    reopen(admin, process)
    process.refresh_from_db()
    task.refresh_from_db()

    assert process.status == ProcessStatus.STARTED
    assert process.released_at is None
    assert task.status == SectorTaskStatus.COMPLETED
    assert not Notification.objects.filter(event=NotificationEvent.PROCESS_REOPENED).exists()


def test_reopening_gives_back_the_task_the_release_closed_without_conclusion(
    actor: User,
    process: OffboardingProcess,
) -> None:
    """Reabrir devolve ao setor o trabalho que o override passou por cima.

    A concluída volta para análise; a que a liberação encerrou sem conclusão
    nunca chegou lá e recomeça pendente — do contrário, reabrir devolveria o
    processo à ativa sem caminho para o setor fazer o que faltou.
    """

    task = started_task(actor, process)
    process.refresh_from_db()
    manager = manager_coordinator(actor)
    release(
        manager,
        process,
        key="release-override-reabertura",
        override_reason="Setor não realizou a conferência dentro do prazo.",
    )
    process.refresh_from_db()
    task.refresh_from_db()
    assert task.status == SectorTaskStatus.CANCELLED
    admin = superadmin()

    reopen(admin, process, task_ids=(task.pk,))
    process.refresh_from_db()
    task.refresh_from_db()

    assert process.status == ProcessStatus.STARTED
    assert task.status == SectorTaskStatus.PENDING
    event = ProcessAuditEvent.objects.get(
        process=process,
        event_type=ProcessEventType.SECTOR_TASK_REOPENED,
    )
    assert event.data["previous_status"] == SectorTaskStatus.CANCELLED
    assert event.data["status"] == SectorTaskStatus.PENDING

    # E o setor volta a poder trabalhar: o caminho completo, do zero.
    start_task(actor, task, key="start-apos-reabertura")
    task.refresh_from_db()
    complete_task(actor, task, key="complete-apos-reabertura")
    task.refresh_from_db()
    assert task.status == SectorTaskStatus.COMPLETED


def test_each_reopening_warns_the_sector_again(
    actor: User,
    process: OffboardingProcess,
) -> None:
    """Reabrir duas vezes é dois avisos: tarefa e ordem entram na chave.

    Sem a tarefa na chave, dois setores do mesmo responsável — ou dois processos
    reabertos pela primeira vez — colidiriam e o segundo aviso sumiria.
    """

    process, task = ready_process(actor, process)
    release(actor, process)
    process.refresh_from_db()
    admin = superadmin()

    reopen(admin, process, task_ids=(task.pk,))
    process.refresh_from_db()
    task.refresh_from_db()
    complete_task(actor, task, key="task-complete-2")
    process.refresh_from_db()
    release(actor, process, key="release-2")
    process.refresh_from_db()
    task.refresh_from_db()

    reopen(admin, process, key="reopen-2", task_ids=(task.pk,))

    messages = Notification.objects.filter(event=NotificationEvent.PROCESS_REOPENED)
    assert messages.count() == 2
    assert {message.dedup_key.rsplit(":", 2)[-2] for message in messages} == {
        f"t{task.pk}r1",
        f"t{task.pk}r2",
    }
    assert (
        ProcessAuditEvent.objects.filter(
            process=process,
            event_type=ProcessEventType.REOPENED,
        ).count()
        == 2
    )


def test_reopen_refuses_a_process_that_never_reached_a_formal_state(
    actor: User,
    process: OffboardingProcess,
) -> None:
    started_task(actor, process)
    process.refresh_from_db()
    admin = superadmin()

    with pytest.raises(ValidationError, match="liberado, processado ou encerrado"):
        reopen(admin, process, key="reopen-iniciado")

    cancel(actor, process)
    process.refresh_from_db()

    # O cancelamento é terminal: não há caminho de volta (ADR-051).
    with pytest.raises(ValidationError, match="liberado, processado ou encerrado"):
        reopen(admin, process, key="reopen-cancelado")

    process.refresh_from_db()
    assert process.status == ProcessStatus.CANCELLED


def test_reopen_only_returns_a_completed_task_of_the_process(
    actor: User,
    process: OffboardingProcess,
) -> None:
    process, task = ready_process(actor, process)
    release(actor, process)
    process.refresh_from_db()
    admin = superadmin()

    with pytest.raises(ValidationError) as alien:
        reopen(admin, process, key="reopen-alheia", task_ids=(task.pk + 1000,))
    assert "não pertence ao processo" in str(alien.value.message_dict["task_ids"])

    ProcessSectorTask.objects.filter(pk=task.pk).update(
        status=SectorTaskStatus.IN_ANALYSIS,
        completed_at=None,
        completed_by=None,
    )

    with pytest.raises(ValidationError) as not_completed:
        reopen(admin, process, key="reopen-em-analise", task_ids=(task.pk,))
    assert "não está concluída" in str(not_completed.value.message_dict["task_ids"])

    process.refresh_from_db()
    assert process.status == ProcessStatus.RELEASED


def test_reopen_is_refused_when_another_process_took_the_employee_key(
    actor: User,
    process: OffboardingProcess,
) -> None:
    """A unicidade do banco é a árbitra, não a leitura prévia (ADR-051)."""

    process, task = ready_process(actor, process)
    release(actor, process)
    process.refresh_from_db()
    register_processing(actor, process)
    process.refresh_from_db()
    close(actor, process)
    process.refresh_from_db()

    successor = OffboardingProcess.objects.create(
        company_code=process.company_code,
        branch_code=process.branch_code,
        employee_type_code=process.employee_type_code,
        employee_registration=process.employee_registration,
        active_employee_key="1:2:1:321",
        opened_by=actor,
        planned_termination_date=process.planned_termination_date,
        due_date=process.due_date,
        reason="Segundo desligamento do mesmo colaborador.",
        priority="Alta",
    )
    admin = superadmin()

    with pytest.raises(ValidationError, match="outro processo não encerrado"):
        reopen(admin, process, task_ids=(task.pk,))

    process.refresh_from_db()
    successor.refresh_from_db()
    assert process.status == ProcessStatus.CLOSED
    assert process.active_employee_key is None
    assert successor.active_employee_key == "1:2:1:321"
    assert not ProcessAuditEvent.objects.filter(
        process=process,
        event_type=ProcessEventType.REOPENED,
    ).exists()
