"""Fase 8: prontidão calculada, liberação, processamento declarado e encerramento."""

# ruff: noqa: F811

from __future__ import annotations

from datetime import timedelta
from typing import Any

import pytest
from django.contrib.auth.models import Permission
from django.core.exceptions import PermissionDenied, ValidationError
from django.utils import timezone

from apps.accounts.models import (
    PEOPLE_DEPARTMENT_MANAGER_ROLE_CODE,
    PEOPLE_DEPARTMENT_ROLE_CODE,
    Role,
    RoleAssignment,
    ScopeType,
    User,
    build_scope_key,
)
from apps.offboarding.models import (
    OffboardingProcess,
    ProcessAuditEvent,
    ProcessEventType,
    ProcessStatus,
)
from apps.offboarding.readiness import (
    ProcessSituation,
    closing_blockers,
    evaluate_process_readiness,
)
from apps.offboarding.services import (
    CloseProcessCommand,
    CloseProcessService,
    IdempotencyConflict,
    RegisterTerminationProcessingCommand,
    RegisterTerminationProcessingService,
    ReleaseProcessCommand,
    ReleaseProcessService,
    completed_processes_for_actor,
    open_processes_for_actor,
)
from apps.pending_items.models import BlockingLevel, PendingItem, PendingStatus
from apps.pending_items.services import (
    ChangePendingStatusCommand,
    ChangePendingStatusService,
)
from apps.templates_engine.models import ChecklistResponseType
from tests.test_offboarding_start import (  # noqa: F401
    PASSWORD,
    actor,
    configured_draft,
    process,
    start,
)
from tests.test_offboarding_tasks import complete_task, start_task, started_task
from tests.test_pending_amounts import (
    create_value_pending,
    decide_amount,
    enable_amounts,
    register_amount,
)
from tests.test_pending_items_evidence import create_pending

pytestmark = pytest.mark.django_db


def ready_process(actor: User, process: OffboardingProcess) -> tuple[OffboardingProcess, Any]:
    """Processo iniciado com a única tarefa concluída — pronto para o DP."""

    task = started_task(actor, process)
    start_task(actor, task)
    task.refresh_from_db()
    complete_task(actor, task)
    task.refresh_from_db()
    process.refresh_from_db()
    return process, task


def change_pending_status(
    actor: User,
    pending_item: PendingItem,
    status: str,
    *,
    key: str,
) -> PendingItem:
    pending_item.refresh_from_db()
    result = ChangePendingStatusService().execute(
        ChangePendingStatusCommand(
            actor=actor,
            pending_uuid=str(pending_item.uuid),
            expected_version=pending_item.version,
            idempotency_key=key,
            status=status,
            comment="Tratativa registrada na trilha da pendência.",
        )
    )
    return result.pending_item


def second_coordinator(actor: User) -> User:
    """Outro `DP` no escopo: a ADR-048 proíbe quem informou decidir a pretensão."""

    user = User.objects.create_user(
        username="dp.decisor",
        email="dp.decisor@example.invalid",
        password=PASSWORD,
    )
    RoleAssignment.objects.create(
        user=user,
        role=Role.objects.get(code=PEOPLE_DEPARTMENT_ROLE_CODE),
        scope_type=ScopeType.GLOBAL,
        scope_key=build_scope_key(ScopeType.GLOBAL, None, None),
        valid_from=timezone.now() - timedelta(days=1),
        assigned_by=actor,
    )
    return user


def manager_coordinator(actor: User) -> User:
    """`DP_GERENTE` com a permissão de override, como o `bootstrap_roles` concede."""

    role, _ = Role.objects.get_or_create(
        code=PEOPLE_DEPARTMENT_MANAGER_ROLE_CODE,
        defaults={"name": "Gerência do Departamento Pessoal"},
    )
    permission = Permission.objects.get(
        content_type__app_label="offboarding",
        codename="override_process_blockers",
    )
    role.permissions.add(permission)
    user = User.objects.create_user(
        username="dp.gerente",
        email="dp.gerente@example.invalid",
        password=PASSWORD,
    )
    RoleAssignment.objects.create(
        user=user,
        role=role,
        scope_type=ScopeType.GLOBAL,
        scope_key=build_scope_key(ScopeType.GLOBAL, None, None),
        valid_from=timezone.now() - timedelta(days=1),
        assigned_by=actor,
    )
    return user


def release(
    actor: User,
    process: OffboardingProcess,
    *,
    key: str = "release-1",
    expected_version: int | None = None,
    notes: str = "Consolidado conferido.",
    override_reason: str = "",
) -> Any:
    return ReleaseProcessService().execute(
        ReleaseProcessCommand(
            actor=actor,
            process_uuid=str(process.uuid),
            expected_version=expected_version or process.version,
            idempotency_key=key,
            notes=notes,
            override_reason=override_reason,
        )
    )


def register_processing(
    actor: User,
    process: OffboardingProcess,
    *,
    key: str = "processing-1",
    reference: str = "RES-2026-0001",
    processed_on: Any = None,
    expected_version: int | None = None,
) -> Any:
    return RegisterTerminationProcessingService().execute(
        RegisterTerminationProcessingCommand(
            actor=actor,
            process_uuid=str(process.uuid),
            expected_version=expected_version or process.version,
            idempotency_key=key,
            termination_reference=reference,
            processed_on=processed_on or timezone.localdate(),
            notes="Rescisão processada no Senior.",
        )
    )


def close(
    actor: User,
    process: OffboardingProcess,
    *,
    key: str = "close-1",
    expected_version: int | None = None,
    override_reason: str = "",
) -> Any:
    return CloseProcessService().execute(
        CloseProcessCommand(
            actor=actor,
            process_uuid=str(process.uuid),
            expected_version=expected_version or process.version,
            idempotency_key=key,
            notes="Encerramento formal.",
            override_reason=override_reason,
        )
    )


def test_readiness_walks_from_validation_to_ready_without_persisting_anything(
    actor: User,
    process: OffboardingProcess,
) -> None:
    task = started_task(actor, process)
    process.refresh_from_db()

    initial = evaluate_process_readiness(process)
    assert initial.situation == ProcessSituation.IN_VALIDATION
    assert initial.blockers
    assert not initial.is_ready
    assert initial.task_count == 1 and initial.completed_task_count == 0

    start_task(actor, task)
    task.refresh_from_db()
    complete_task(actor, task)
    process.refresh_from_db()

    final = evaluate_process_readiness(process)
    assert final.situation == ProcessSituation.READY_FOR_REVIEW
    assert final.is_ready
    assert final.completed_task_count == 1
    # A situação é leitura: o estado formal continua sendo o do início.
    assert process.status == ProcessStatus.STARTED


def test_pending_and_undecided_amount_shape_the_calculated_situation(
    actor: User,
    process: OffboardingProcess,
) -> None:
    task = started_task(actor, process)
    start_task(actor, task)
    task.refresh_from_db()
    enable_amounts(task)
    pending_item = create_pending(
        actor,
        task,
        blocking_level=BlockingLevel.NON_BLOCKING,
    ).pending_item
    process.refresh_from_db()

    with_open_pending = evaluate_process_readiness(process)
    assert with_open_pending.situation == ProcessSituation.WITH_PENDING_ITEMS
    assert with_open_pending.open_pending_count == 1

    task.refresh_from_db()
    value_pending = create_value_pending(actor, task, key="pending-value-situacao")
    register_amount(actor, value_pending, key="amount-situacao")
    process.refresh_from_db()

    with_amount = evaluate_process_readiness(process)
    assert with_amount.situation == ProcessSituation.AWAITING_DECISION
    assert with_amount.undecided_amount_count == 1
    # A pendência de valor nasce `BLOQUEANTE_ATE_DECISAO`: o impedimento vem da
    # classificação, e a pretensão não é contada duas vezes.
    assert any("aguarda a decisão" in blocker for blocker in with_amount.blockers)
    assert pending_item.status == PendingStatus.OPEN


def test_optional_item_left_blank_is_not_an_inconsistency_but_an_answered_one_is(
    actor: User,
    process: OffboardingProcess,
) -> None:
    """A prontidão usa a régua da conclusão, não uma mais dura que a dela.

    Item opcional com `requires_evidence` que o setor legitimamente deixou em
    branco é aceito por `_validated_answers` e não pode virar impedimento
    permanente da liberação — o processo ficaria sem saída. Já o item opcional
    que foi respondido sem a evidência exigida é divergência real do que a
    conclusão validou, e continua impedindo.
    """

    process, task = ready_process(actor, process)
    item = task.checklist_items.get()

    # 1. Arquivo opcional sem evidência: a conclusão só exige arquivo do item
    #    obrigatório (`services._validated_answers`).
    item.response_type_snapshot = ChecklistResponseType.FILE
    item.is_required = False
    item.requires_evidence = True
    item.response = None
    item.save()
    assert evaluate_process_readiness(process).is_ready

    # 2. Item comum opcional, exigindo evidência, deixado em branco.
    item.response_type_snapshot = ChecklistResponseType.BOOLEAN
    item.save()
    assert evaluate_process_readiness(process).is_ready

    # 3. O mesmo item, agora respondido e sem a evidência exigida.
    item.response = {"value": True}
    item.save()
    readiness = evaluate_process_readiness(process)
    assert not readiness.is_ready
    assert any("sem a evidência exigida" in blocker for blocker in readiness.blockers)


def test_release_refuses_open_task_and_records_trail_when_ready(
    actor: User,
    process: OffboardingProcess,
) -> None:
    task = started_task(actor, process)
    process.refresh_from_db()

    with pytest.raises(ValidationError) as blocked:
        release(actor, process)
    assert "release" in blocked.value.message_dict

    start_task(actor, task)
    task.refresh_from_db()
    complete_task(actor, task)
    process.refresh_from_db()
    expected_version = process.version

    result = release(actor, process, expected_version=expected_version)
    replay = release(actor, process, expected_version=expected_version)
    process.refresh_from_db()

    assert not result.replayed
    assert replay.replayed
    assert process.status == ProcessStatus.RELEASED
    assert process.released_by == actor
    assert process.released_at is not None
    assert process.release_notes == "Consolidado conferido."
    assert process.version == expected_version + 1
    events = ProcessAuditEvent.objects.filter(
        process=process,
        event_type=ProcessEventType.RELEASED,
    )
    assert events.count() == 1
    assert events.get().data["task_count"] == 1


def test_release_override_is_barred_to_plain_dp_even_with_reason(
    actor: User,
    process: OffboardingProcess,
) -> None:
    """A permissão de override é do `DP_GERENTE`; `DP` puro continua barrado (ADR-054)."""

    started_task(actor, process)
    process.refresh_from_db()

    with pytest.raises(ValidationError) as blocked:
        release(actor, process, override_reason="Urgência do desligamento.")
    assert "release" in blocked.value.message_dict
    process.refresh_from_db()
    assert process.status == ProcessStatus.STARTED
    assert process.release_override_reason == ""


def test_release_override_by_manager_requires_reason_and_is_audited(
    actor: User,
    process: OffboardingProcess,
) -> None:
    started_task(actor, process)
    process.refresh_from_db()
    manager = manager_coordinator(actor)

    with pytest.raises(ValidationError) as missing_reason:
        release(manager, process, key="release-sem-motivo")
    assert "override_reason" in missing_reason.value.message_dict
    process.refresh_from_db()
    assert process.status == ProcessStatus.STARTED

    reason = "Desligamento urgente autorizado pela gerência."
    result = release(manager, process, key="release-override", override_reason=reason)
    process.refresh_from_db()

    assert not result.replayed
    assert process.status == ProcessStatus.RELEASED
    assert process.released_by == manager
    assert process.release_override_reason == reason
    event = ProcessAuditEvent.objects.get(process=process, event_type=ProcessEventType.RELEASED)
    assert event.data["overridden_blockers"]
    assert event.data["override_reason"] == reason


def test_override_reason_is_refused_when_there_is_no_blocker(
    actor: User,
    process: OffboardingProcess,
) -> None:
    process, _ = ready_process(actor, process)
    manager = manager_coordinator(actor)

    with pytest.raises(ValidationError) as extra_reason:
        release(manager, process, override_reason="Não deveria ser aceita.")
    assert "override_reason" in extra_reason.value.message_dict
    process.refresh_from_db()
    assert process.status == ProcessStatus.STARTED


def test_release_override_also_available_to_superadmin(
    actor: User,
    process: OffboardingProcess,
) -> None:
    started_task(actor, process)
    process.refresh_from_db()
    superadmin = User.objects.create_superuser(
        username="super.override",
        email="super.override@example.invalid",
        password=PASSWORD,
    )
    reason = "SuperAdmin decide sem barreira (ADR-044)."

    release(superadmin, process, key="release-super-override", override_reason=reason)
    process.refresh_from_db()

    assert process.status == ProcessStatus.RELEASED
    assert process.release_override_reason == reason


def test_release_refuses_stale_version_and_reused_key_with_other_content(
    actor: User,
    process: OffboardingProcess,
) -> None:
    process, _ = ready_process(actor, process)

    with pytest.raises(ValidationError, match="alterado por outra sessão"):
        release(actor, process, expected_version=process.version + 5)

    release(actor, process, key="release-conflito")
    process.refresh_from_db()

    with pytest.raises(IdempotencyConflict):
        release(
            actor,
            process,
            key="release-conflito",
            expected_version=process.version,
            notes="Outro parecer.",
        )


def test_regularization_reopened_after_the_sector_concluded_blocks_the_release(
    actor: User,
    process: OffboardingProcess,
) -> None:
    """A conclusão da tarefa não é salvo-conduto: a prontidão é refeita na liberação."""

    task = started_task(actor, process)
    start_task(actor, task)
    task.refresh_from_db()
    pending_item = create_pending(actor, task, key="pending-bloqueante").pending_item
    change_pending_status(
        actor,
        pending_item,
        PendingStatus.IN_REGULARIZATION,
        key="pending-regularizar",
    )
    change_pending_status(
        actor,
        pending_item,
        PendingStatus.REGULARIZED,
        key="pending-regularizada",
    )
    task.refresh_from_db()
    complete_task(actor, task)
    process.refresh_from_db()
    assert evaluate_process_readiness(process).is_ready

    change_pending_status(
        actor,
        pending_item,
        PendingStatus.IN_REGULARIZATION,
        key="pending-reaberta",
    )
    process.refresh_from_db()

    with pytest.raises(ValidationError) as blocked:
        release(actor, process)
    assert any(
        "não foi regularizada" in message for message in blocked.value.message_dict["release"]
    )

    change_pending_status(
        actor,
        pending_item,
        PendingStatus.REGULARIZED,
        key="pending-regularizada-2",
    )
    process.refresh_from_db()

    release(actor, process)
    process.refresh_from_db()
    assert process.status == ProcessStatus.RELEASED


def test_undecided_amount_blocks_the_release_until_the_decision(
    actor: User,
    process: OffboardingProcess,
) -> None:
    task = started_task(actor, process)
    start_task(actor, task)
    task.refresh_from_db()
    enable_amounts(task)
    pending_item = create_value_pending(actor, task, key="pending-valor-liberacao")
    pending_item = register_amount(actor, pending_item, key="amount-liberacao")
    task.refresh_from_db()

    with pytest.raises(ValidationError):
        complete_task(actor, task, key="task-complete-travada")

    decide_amount(second_coordinator(actor), pending_item, key="decide-liberacao")
    task.refresh_from_db()
    complete_task(actor, task, key="task-complete-liberada")
    process.refresh_from_db()

    readiness = evaluate_process_readiness(process)
    assert readiness.is_ready
    release(actor, process)
    process.refresh_from_db()
    assert process.status == ProcessStatus.RELEASED


def test_sector_responsible_without_dp_cannot_release(
    actor: User,
    process: OffboardingProcess,
) -> None:
    process, task = ready_process(actor, process)
    responsible = User.objects.create_user(
        username="responsavel.setor",
        email="responsavel.setor@example.invalid",
        password=PASSWORD,
    )

    with pytest.raises(PermissionDenied, match="papel DP"):
        release(responsible, process)

    process.refresh_from_db()
    assert process.status == ProcessStatus.STARTED


def test_superadmin_runs_the_whole_formal_cycle_without_dp_role(
    actor: User,
    process: OffboardingProcess,
) -> None:
    process, _ = ready_process(actor, process)
    superadmin = User.objects.create_superuser(
        username="super.encerramento",
        email="super.encerramento@example.invalid",
        password=PASSWORD,
    )

    release(superadmin, process, key="release-super")
    process.refresh_from_db()
    register_processing(superadmin, process, key="processing-super")
    process.refresh_from_db()
    close(superadmin, process, key="close-super")
    process.refresh_from_db()

    assert process.status == ProcessStatus.CLOSED
    assert process.released_by == superadmin
    assert process.closed_by == superadmin


def test_processing_requires_release_and_a_plausible_date(
    actor: User,
    process: OffboardingProcess,
) -> None:
    process, _ = ready_process(actor, process)

    with pytest.raises(ValidationError, match="processo liberado"):
        register_processing(actor, process)

    release(actor, process)
    process.refresh_from_db()

    with pytest.raises(ValidationError) as future:
        register_processing(
            actor,
            process,
            key="processing-futuro",
            processed_on=timezone.localdate() + timedelta(days=1),
        )
    assert "processed_on" in future.value.message_dict

    with pytest.raises(ValidationError) as before_release:
        register_processing(
            actor,
            process,
            key="processing-antes",
            processed_on=timezone.localdate() - timedelta(days=3),
        )
    assert "processed_on" in before_release.value.message_dict

    with pytest.raises(ValidationError) as without_reference:
        register_processing(actor, process, key="processing-sem-numero", reference="   ")
    assert "termination_reference" in without_reference.value.message_dict

    expected_version = process.version
    result = register_processing(actor, process, expected_version=expected_version)
    replay = register_processing(actor, process, expected_version=expected_version)
    process.refresh_from_db()

    assert not result.replayed
    assert replay.replayed
    assert process.status == ProcessStatus.PROCESSED
    assert process.termination_reference == "RES-2026-0001"
    assert process.termination_processed_on == timezone.localdate()
    assert process.processing_registered_by == actor
    event = ProcessAuditEvent.objects.get(
        process=process,
        event_type=ProcessEventType.PROCESSING_REGISTERED,
    )
    assert event.data["termination_reference"] == "RES-2026-0001"


def test_closing_requires_processed_status_and_no_pending_in_progress(
    actor: User,
    process: OffboardingProcess,
) -> None:
    task = started_task(actor, process)
    start_task(actor, task)
    task.refresh_from_db()
    # Pendência informativa aberta não impede concluir nem liberar, mas o
    # encerramento formal exige que nada continue em curso.
    pending_item = create_pending(
        actor,
        task,
        key="pending-antes-encerrar",
        blocking_level=BlockingLevel.NON_BLOCKING,
    ).pending_item
    task.refresh_from_db()
    complete_task(actor, task)
    process.refresh_from_db()
    release(actor, process)
    process.refresh_from_db()

    with pytest.raises(ValidationError, match="rescisão processada"):
        close(actor, process)

    register_processing(actor, process)
    process.refresh_from_db()

    assert closing_blockers(process)
    with pytest.raises(ValidationError) as blocked:
        close(actor, process)
    assert "close" in blocked.value.message_dict

    change_pending_status(
        actor,
        pending_item,
        PendingStatus.IN_REGULARIZATION,
        key="pending-encerrar",
    )
    change_pending_status(
        actor,
        pending_item,
        PendingStatus.REGULARIZED,
        key="pending-encerrada",
    )
    process.refresh_from_db()

    close(actor, process)
    process.refresh_from_db()

    assert process.status == ProcessStatus.CLOSED
    assert process.closed_by == actor
    assert process.active_employee_key is None
    assert PendingItem.objects.filter(process=process).exists()
    assert ProcessAuditEvent.objects.filter(
        process=process,
        event_type=ProcessEventType.CLOSED,
    ).exists()


def test_close_override_is_barred_to_plain_dp_even_with_reason(
    actor: User,
    process: OffboardingProcess,
) -> None:
    task = started_task(actor, process)
    start_task(actor, task)
    task.refresh_from_db()
    create_pending(
        actor,
        task,
        key="pending-close-dp-barrado",
        blocking_level=BlockingLevel.NON_BLOCKING,
    )
    task.refresh_from_db()
    complete_task(actor, task)
    process.refresh_from_db()
    release(actor, process, key="release-close-dp-barrado")
    process.refresh_from_db()
    register_processing(actor, process, key="processing-close-dp-barrado")
    process.refresh_from_db()
    assert closing_blockers(process)

    with pytest.raises(ValidationError) as blocked:
        close(actor, process, override_reason="Tentativa sem permissão.")
    assert "close" in blocked.value.message_dict
    process.refresh_from_db()
    assert process.status == ProcessStatus.PROCESSED
    assert process.closing_override_reason == ""


def test_close_override_by_manager_requires_reason_and_is_audited(
    actor: User,
    process: OffboardingProcess,
) -> None:
    task = started_task(actor, process)
    start_task(actor, task)
    task.refresh_from_db()
    pending_item = create_pending(
        actor,
        task,
        key="pending-close-override",
        blocking_level=BlockingLevel.NON_BLOCKING,
    ).pending_item
    task.refresh_from_db()
    complete_task(actor, task)
    process.refresh_from_db()
    release(actor, process, key="release-close-override")
    process.refresh_from_db()
    register_processing(actor, process, key="processing-close-override")
    process.refresh_from_db()
    assert closing_blockers(process)

    manager = manager_coordinator(actor)

    with pytest.raises(ValidationError) as missing_reason:
        close(manager, process, key="close-sem-motivo")
    assert "override_reason" in missing_reason.value.message_dict
    process.refresh_from_db()
    assert process.status == ProcessStatus.PROCESSED

    reason = "Pendência informativa aceita pela gerência."
    close(manager, process, key="close-override", override_reason=reason)
    process.refresh_from_db()
    pending_item.refresh_from_db()

    assert process.status == ProcessStatus.CLOSED
    assert process.closing_override_reason == reason
    event = ProcessAuditEvent.objects.get(process=process, event_type=ProcessEventType.CLOSED)
    assert event.data["overridden_blockers"]
    assert event.data["override_reason"] == reason
    # O override libera o encerramento, não a pendência: ela segue no próprio
    # ciclo, e a auditoria é a única evidência do rompimento.
    assert pending_item.status == PendingStatus.OPEN


def test_closing_frees_the_employee_key_for_a_new_process(
    actor: User,
    process: OffboardingProcess,
) -> None:
    process, _ = ready_process(actor, process)
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
        reason="Reabertura administrativa do desligamento.",
        priority="Alta",
    )

    assert successor.pk != process.pk
    assert process.active_employee_key is None


def test_released_process_leaves_the_open_card_and_reaches_the_completed_one(
    actor: User,
    process: OffboardingProcess,
) -> None:
    task = started_task(actor, process)
    process.refresh_from_db()
    assert list(open_processes_for_actor(actor)) == [process]

    start_task(actor, task)
    task.refresh_from_db()
    complete_task(actor, task)
    process.refresh_from_db()
    release(actor, process)
    process.refresh_from_db()

    assert list(open_processes_for_actor(actor)) == []
    assert [row.pk for row in completed_processes_for_actor(actor)] == [process.pk]
