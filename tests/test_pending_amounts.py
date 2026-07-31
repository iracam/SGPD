"""Phase 6, slice 1: pretension and decision records behind a pending item."""

# ruff: noqa: F811

from __future__ import annotations

import json
from datetime import timedelta
from decimal import Decimal
from typing import Any

import pytest
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import IntegrityError, transaction
from django.test import Client
from django.urls import reverse
from django.utils import timezone

from apps.accounts.models import (
    Role,
    RoleAssignment,
    ScopeType,
    User,
    build_scope_key,
)
from apps.offboarding.models import ProcessAuditEvent, ProcessEventType, SectorTaskStatus
from apps.pending_items.models import (
    DECIDED_STATUSES,
    BlockingLevel,
    DecisionOutcome,
    PendingAmount,
    PendingCategory,
    PendingDecision,
    PendingItem,
    PendingStatus,
)
from apps.pending_items.services import (
    AssessPendingAmountCommand,
    AssessPendingAmountService,
    ChangePendingStatusCommand,
    ChangePendingStatusService,
    ContestPendingAmountCommand,
    ContestPendingAmountService,
    CreatePendingItemCommand,
    CreatePendingItemService,
    DecidePendingAmountCommand,
    DecidePendingAmountService,
    RegisterPendingAmountCommand,
    RegisterPendingAmountService,
)
from apps.sectors.models import SectorResponsible, ValidationSector
from tests.test_offboarding_start import (  # noqa: F401
    PASSWORD,
    actor,
    configured_draft,
    process,
    start,
)
from tests.test_offboarding_tasks import complete_task, start_task, started_task

pytestmark = pytest.mark.django_db


def analysis_task(actor: User, process: Any) -> Any:
    task = started_task(actor, process)
    start_task(actor, task)
    task.refresh_from_db()
    return task


def create_value_pending(
    actor: User,
    task: Any,
    *,
    key: str = "pending-value",
    blocking_level: str = BlockingLevel.BLOCKING_UNTIL_DECISION,
) -> PendingItem:
    result = CreatePendingItemService().execute(
        CreatePendingItemCommand(
            actor=actor,
            task_id=task.pk,
            expected_task_version=task.version,
            idempotency_key=key,
            category=PendingCategory.VALUE,
            title="Notebook não devolvido",
            description="Pretensão de cobrança do equipamento não devolvido.",
            blocking_level=blocking_level,
            checklist_item_id=task.checklist_items.get().pk,
            items=(),
        )
    )
    return result.pending_item


def build_amount(pending_item: PendingItem, actor: User, **overrides: Any) -> PendingAmount:
    values: dict[str, Any] = {
        "pending_item": pending_item,
        "amount_informed": Decimal("1250.00"),
        "justification": "Valor de mercado do equipamento não devolvido.",
        "informed_by": actor,
    }
    values.update(overrides)
    return PendingAmount(**values)


def test_blocking_until_decision_survives_the_widened_column(
    actor: User,
    process: Any,
) -> None:
    task = analysis_task(actor, process)
    pending_item = create_value_pending(actor, task)

    pending_item.refresh_from_db()
    assert pending_item.blocking_level == BlockingLevel.BLOCKING_UNTIL_DECISION
    assert pending_item.category == PendingCategory.VALUE


def test_amount_requires_value_category_justification_and_currency(
    actor: User,
    process: Any,
) -> None:
    task = analysis_task(actor, process)
    value_pending = create_value_pending(actor, task)
    other_pending = (
        CreatePendingItemService()
        .execute(
            CreatePendingItemCommand(
                actor=actor,
                task_id=task.pk,
                expected_task_version=task.version,
                idempotency_key="pending-equipment",
                category=PendingCategory.EQUIPMENT,
                title="Crachá não devolvido",
                description="Devolução pendente do crachá corporativo.",
                blocking_level=BlockingLevel.BLOCKING,
                checklist_item_id=None,
                items=(),
            )
        )
        .pending_item
    )

    with pytest.raises(ValidationError) as category_error:
        build_amount(other_pending, actor).full_clean()
    assert "pending_item" in category_error.value.message_dict

    with pytest.raises(ValidationError) as justification_error:
        build_amount(value_pending, actor, justification="   ").full_clean()
    assert "justification" in justification_error.value.message_dict

    with pytest.raises(ValidationError) as currency_error:
        build_amount(value_pending, actor, currency="R$").full_clean()
    assert "currency" in currency_error.value.message_dict

    amount = build_amount(value_pending, actor, currency="brl")
    amount.full_clean()
    amount.save()
    assert amount.currency == "BRL"
    assert amount.version == 1
    assert amount.approved_by_id is None and amount.approved_at is None


def test_amount_pairs_approver_with_instant_and_refuses_negative_value(
    actor: User,
    process: Any,
) -> None:
    task = analysis_task(actor, process)
    pending_item = create_value_pending(actor, task)

    with pytest.raises(ValidationError) as pairing_error:
        build_amount(pending_item, actor, approved_by=actor).full_clean()
    assert "approved_by" in pairing_error.value.message_dict

    amount = build_amount(pending_item, actor)
    amount.full_clean()
    amount.save()

    amount.amount_approved = Decimal("-1.00")
    with pytest.raises(IntegrityError), transaction.atomic():
        amount.save(update_fields=("amount_approved",))


def test_amount_and_decision_reject_bulk_writes_and_deletion(
    actor: User,
    process: Any,
) -> None:
    task = analysis_task(actor, process)
    pending_item = create_value_pending(actor, task)
    amount = build_amount(pending_item, actor)
    amount.full_clean()
    amount.save()

    with pytest.raises(ValidationError):
        PendingAmount.objects.filter(pk=amount.pk).update(amount_approved=Decimal("10.00"))
    with pytest.raises(ValidationError):
        PendingAmount.objects.filter(pk=amount.pk).delete()
    with pytest.raises(ValidationError):
        amount.delete()

    decision = PendingDecision(
        pending_item=pending_item,
        decision=DecisionOutcome.CHARGE_APPROVED,
        opinion="Cobrança aprovada após análise do valor apurado.",
        decided_by=actor,
    )
    decision.full_clean()
    decision.save()

    with pytest.raises(ValidationError):
        PendingDecision.objects.filter(pk=decision.pk).delete()
    with pytest.raises(ValidationError):
        decision.delete()


def test_decision_is_append_only_and_records_segregation_override(
    actor: User,
    process: Any,
) -> None:
    task = analysis_task(actor, process)
    pending_item = create_value_pending(actor, task)

    with pytest.raises(ValidationError) as opinion_error:
        PendingDecision(
            pending_item=pending_item,
            decision=DecisionOutcome.WAIVED,
            opinion="  ",
            decided_by=actor,
        ).full_clean()
    assert "opinion" in opinion_error.value.message_dict

    first = PendingDecision(
        pending_item=pending_item,
        decision=DecisionOutcome.REJECTED,
        opinion="Rejeitada por falta de comprovação.",
        decided_by=actor,
    )
    first.full_clean()
    first.save()

    first.opinion = "Parecer reescrito."
    with pytest.raises(ValidationError):
        first.save()

    second = PendingDecision(
        pending_item=pending_item,
        decision=DecisionOutcome.CHARGE_APPROVED,
        opinion="Reanálise aprovou a cobrança; SuperAdmin decidiu o próprio lançamento.",
        decided_by=actor,
        segregation_override=True,
    )
    second.full_clean()
    second.save()

    decisions = list(PendingDecision.objects.filter(pending_item=pending_item))
    assert [decision.decision for decision in decisions] == [
        DecisionOutcome.REJECTED,
        DecisionOutcome.CHARGE_APPROVED,
    ]
    assert decisions[0].opinion == "Rejeitada por falta de comprovação."
    assert decisions[1].segregation_override is True
    assert decisions[1].decided_at >= decisions[0].decided_at


def test_decision_axis_statuses_are_available_without_new_transitions(
    actor: User,
    process: Any,
) -> None:
    task = analysis_task(actor, process)
    pending_item = create_value_pending(actor, task)

    assert pending_item.status == PendingStatus.OPEN
    assert PendingStatus.SUBMITTED_FOR_REVIEW in PendingStatus.values
    assert PendingStatus.CONTESTED in PendingStatus.values

    pending_item.status = PendingStatus.CHARGE_APPROVED
    pending_item.save(update_fields=("status",))
    pending_item.refresh_from_db()
    assert pending_item.status == PendingStatus.CHARGE_APPROVED
    assert pending_item.updated_at <= timezone.now()


def enable_amounts(task: Any) -> None:
    sector = ValidationSector.objects.get(pk=task.sector_id)
    sector.allows_amount = True
    sector.save(update_fields=("allows_amount",))


def value_pending_ready(actor: User, process: Any) -> tuple[Any, PendingItem]:
    task = analysis_task(actor, process)
    enable_amounts(task)
    return task, create_value_pending(actor, task)


def register_amount(
    actor: User,
    pending_item: PendingItem,
    *,
    key: str = "amount-register",
    amount: Decimal = Decimal("1250.00"),
) -> PendingItem:
    return (
        RegisterPendingAmountService()
        .execute(
            RegisterPendingAmountCommand(
                actor=actor,
                pending_uuid=str(pending_item.uuid),
                expected_version=pending_item.version,
                idempotency_key=key,
                amount_informed=amount,
                justification="Valor de mercado do equipamento não devolvido.",
            )
        )
        .pending_item
    )


def decide_amount(
    actor: User,
    pending_item: PendingItem,
    *,
    key: str = "amount-decide",
    decision: str = DecisionOutcome.CHARGE_APPROVED,
    approved: Decimal | None = Decimal("980.00"),
) -> PendingItem:
    return (
        DecidePendingAmountService()
        .execute(
            DecidePendingAmountCommand(
                actor=actor,
                pending_uuid=str(pending_item.uuid),
                expected_version=pending_item.version,
                idempotency_key=key,
                decision=decision,
                opinion="Parecer da análise sobre a pretensão de cobrança.",
                amount_approved=approved,
            )
        )
        .pending_item
    )


def make_dp(actor: User, username: str) -> User:
    dp = User.objects.create_user(
        username=username,
        email=f"{username}@example.invalid",
        password=PASSWORD,
    )
    RoleAssignment.objects.create(
        user=dp,
        role=Role.objects.get(code="DP"),
        scope_type=ScopeType.GLOBAL,
        scope_key=build_scope_key(ScopeType.GLOBAL, None, None),
        valid_from=timezone.now() - timedelta(hours=1),
        assigned_by=actor,
    )
    return dp


def test_pretension_runs_from_informed_to_approved_with_trail(
    actor: User,
    process: Any,
) -> None:
    task, pending_item = value_pending_ready(actor, process)

    pending_item = register_amount(actor, pending_item)
    assert pending_item.status == PendingStatus.SUBMITTED_FOR_REVIEW
    assert pending_item.amount.amount_informed == Decimal("1250.00")
    assert pending_item.amount.informed_by == actor

    pending_item = (
        AssessPendingAmountService()
        .execute(
            AssessPendingAmountCommand(
                actor=actor,
                pending_uuid=str(pending_item.uuid),
                expected_version=pending_item.version,
                idempotency_key="amount-assess",
                amount_assessed=Decimal("1100.00"),
                justification="Apuração considerou a depreciação do equipamento.",
            )
        )
        .pending_item
    )
    assert pending_item.status == PendingStatus.SUBMITTED_FOR_REVIEW

    pending_item = (
        ContestPendingAmountService()
        .execute(
            ContestPendingAmountCommand(
                actor=actor,
                pending_uuid=str(pending_item.uuid),
                expected_version=pending_item.version,
                idempotency_key="amount-contest",
                amount_contested=Decimal("500.00"),
                justification="Colaborador contesta o estado de conservação.",
            )
        )
        .pending_item
    )
    assert pending_item.status == PendingStatus.CONTESTED

    decider = make_dp(actor, "dp-decisor")
    pending_item = decide_amount(decider, pending_item)

    amount = pending_item.amount
    amount.refresh_from_db()
    assert pending_item.status == PendingStatus.CHARGE_APPROVED
    assert amount.amount_assessed == Decimal("1100.00")
    assert amount.amount_contested == Decimal("500.00")
    assert amount.amount_approved == Decimal("980.00")
    assert amount.approved_by == decider
    assert amount.approved_at is not None
    assert amount.amount_processed is None

    decision = pending_item.decisions.get()
    assert decision.decision == DecisionOutcome.CHARGE_APPROVED
    assert decision.segregation_override is False

    events = list(
        ProcessAuditEvent.objects.filter(
            process=task.process,
            event_type__startswith="PENDING_AMOUNT_",
        ).order_by("pk")
    )
    assert [event.event_type for event in events] == [
        ProcessEventType.PENDING_AMOUNT_INFORMED,
        ProcessEventType.PENDING_AMOUNT_ASSESSED,
        ProcessEventType.PENDING_AMOUNT_CONTESTED,
        ProcessEventType.PENDING_AMOUNT_DECIDED,
    ]
    assert events[-1].data["segregation_override"] is False
    assert events[-1].data["amount_approved"] == "980.00"
    assert pending_item.comments.count() == 4


def test_rejection_and_waiver_settle_the_pretension_at_zero(
    actor: User,
    process: Any,
) -> None:
    _, pending_item = value_pending_ready(actor, process)
    pending_item = register_amount(actor, pending_item)
    decider = make_dp(actor, "dp-rejeita")

    pending_item = decide_amount(
        decider,
        pending_item,
        decision=DecisionOutcome.REJECTED,
        approved=None,
    )

    amount = pending_item.amount
    amount.refresh_from_db()
    assert pending_item.status == PendingStatus.REJECTED
    assert amount.amount_approved == Decimal("0.00")
    assert amount.approved_by == decider


def test_sector_without_allows_amount_cannot_inform_value(
    actor: User,
    process: Any,
) -> None:
    task = analysis_task(actor, process)
    pending_item = create_value_pending(actor, task)

    with pytest.raises(ValidationError, match="não está habilitado a lançar valores"):
        register_amount(actor, pending_item)

    assert not PendingAmount.objects.filter(pending_item=pending_item).exists()
    pending_item.refresh_from_db()
    assert pending_item.status == PendingStatus.OPEN


def test_non_value_pending_has_no_pretension(actor: User, process: Any) -> None:
    task = analysis_task(actor, process)
    enable_amounts(task)
    other = (
        CreatePendingItemService()
        .execute(
            CreatePendingItemCommand(
                actor=actor,
                task_id=task.pk,
                expected_task_version=task.version,
                idempotency_key="pending-material",
                category=PendingCategory.EQUIPMENT,
                title="Crachá não devolvido",
                description="Devolução pendente do crachá corporativo.",
                blocking_level=BlockingLevel.BLOCKING,
                checklist_item_id=None,
                items=(),
            )
        )
        .pending_item
    )

    with pytest.raises(ValidationError, match="categoria Valor"):
        register_amount(actor, other)


def test_informer_cannot_decide_but_superadmin_overrides_with_a_mark(
    actor: User,
    process: Any,
) -> None:
    _, pending_item = value_pending_ready(actor, process)
    pending_item = register_amount(actor, pending_item)

    with pytest.raises(PermissionDenied, match="não pode decidir a própria pretensão"):
        decide_amount(actor, pending_item)

    pending_item.refresh_from_db()
    assert pending_item.status == PendingStatus.SUBMITTED_FOR_REVIEW
    assert not pending_item.decisions.exists()

    superadmin = User.objects.create_superuser(
        username="super-valores",
        email="super-valores@example.invalid",
        password=PASSWORD,
    )
    superadmin_pending = create_value_pending(
        superadmin,
        pending_item.task,
        key="pending-super",
    )
    superadmin_pending = register_amount(
        superadmin,
        superadmin_pending,
        key="amount-super",
    )
    superadmin_pending = decide_amount(
        superadmin,
        superadmin_pending,
        key="decide-super",
    )

    decision = superadmin_pending.decisions.get()
    assert superadmin_pending.status == PendingStatus.CHARGE_APPROVED
    assert decision.segregation_override is True
    assert decision.decided_by == superadmin
    event = ProcessAuditEvent.objects.filter(
        event_type=ProcessEventType.PENDING_AMOUNT_DECIDED,
        data__pending_uuid=str(superadmin_pending.uuid),
    ).get()
    assert event.data["segregation_override"] is True


def test_sector_responsible_without_dp_cannot_assess_or_decide(
    actor: User,
    process: Any,
) -> None:
    task, pending_item = value_pending_ready(actor, process)
    pending_item = register_amount(actor, pending_item)

    responsible = User.objects.create_user(
        username="responsavel-setor",
        email="responsavel-setor@example.invalid",
        password=PASSWORD,
    )
    SectorResponsible.objects.create(
        sector=ValidationSector.objects.get(pk=task.sector_id),
        user=responsible,
        valid_from=timezone.now() - timedelta(hours=1),
        assigned_by=actor,
        updated_by=actor,
    )

    with pytest.raises(PermissionDenied, match="DP vigente no escopo"):
        AssessPendingAmountService().execute(
            AssessPendingAmountCommand(
                actor=responsible,
                pending_uuid=str(pending_item.uuid),
                expected_version=pending_item.version,
                idempotency_key="assess-responsavel",
                amount_assessed=Decimal("900.00"),
                justification="Tentativa de apuração pelo setor.",
            )
        )

    with pytest.raises(PermissionDenied, match="DP vigente no escopo"):
        decide_amount(responsible, pending_item, key="decide-responsavel")

    assert not pending_item.decisions.exists()


def test_amount_services_replay_and_refuse_stale_versions(
    actor: User,
    process: Any,
) -> None:
    _, pending_item = value_pending_ready(actor, process)
    stale_version = pending_item.version

    first = RegisterPendingAmountService().execute(
        RegisterPendingAmountCommand(
            actor=actor,
            pending_uuid=str(pending_item.uuid),
            expected_version=stale_version,
            idempotency_key="amount-once",
            amount_informed=Decimal("1250.00"),
            justification="Valor de mercado do equipamento não devolvido.",
        )
    )
    replay = RegisterPendingAmountService().execute(
        RegisterPendingAmountCommand(
            actor=actor,
            pending_uuid=str(pending_item.uuid),
            expected_version=stale_version,
            idempotency_key="amount-once",
            amount_informed=Decimal("1250.00"),
            justification="Valor de mercado do equipamento não devolvido.",
        )
    )

    assert not first.replayed
    assert replay.replayed
    assert PendingAmount.objects.filter(pending_item=pending_item).count() == 1

    with pytest.raises(ValidationError, match="alterada por outra sessão"):
        RegisterPendingAmountService().execute(
            RegisterPendingAmountCommand(
                actor=actor,
                pending_uuid=str(pending_item.uuid),
                expected_version=stale_version,
                idempotency_key="amount-stale",
                amount_informed=Decimal("1250.00"),
                justification="Valor de mercado do equipamento não devolvido.",
            )
        )


def test_decision_axis_is_unreachable_without_a_pretension(
    actor: User,
    process: Any,
) -> None:
    _, pending_item = value_pending_ready(actor, process)

    with pytest.raises(ValidationError, match="não é permitida"):
        ChangePendingStatusService().execute(
            ChangePendingStatusCommand(
                actor=actor,
                pending_uuid=str(pending_item.uuid),
                expected_version=pending_item.version,
                idempotency_key="status-atalho",
                status=PendingStatus.SUBMITTED_FOR_REVIEW,
                comment="Tentativa de encaminhar sem valor.",
            )
        )

    # A pendência sem pretensão continua ABERTA, e o guard de estado da decisão
    # rejeita antes mesmo de procurar o valor.
    with pytest.raises(ValidationError, match="em análise pode ser decidida"):
        decide_amount(make_dp(actor, "dp-sem-valor"), pending_item)

    pending_item.refresh_from_db()
    assert pending_item.status == PendingStatus.OPEN


def test_decided_pretension_only_leaves_towards_closure(
    actor: User,
    process: Any,
) -> None:
    _, pending_item = value_pending_ready(actor, process)
    pending_item = register_amount(actor, pending_item)
    pending_item = decide_amount(make_dp(actor, "dp-encerra"), pending_item)

    with pytest.raises(ValidationError, match="em análise pode ser decidida"):
        decide_amount(make_dp(actor, "dp-outro"), pending_item, key="decide-again")

    closed = ChangePendingStatusService().execute(
        ChangePendingStatusCommand(
            actor=actor,
            pending_uuid=str(pending_item.uuid),
            expected_version=pending_item.version,
            idempotency_key="status-encerrar",
            status=PendingStatus.CLOSED,
            comment="Cobrança aprovada e pendência encerrada.",
        )
    )

    assert closed.pending_item.status == PendingStatus.CLOSED
    assert closed.pending_item.decisions.count() == 1


@pytest.mark.parametrize(
    ("decision", "approved"),
    (
        (DecisionOutcome.CHARGE_APPROVED, Decimal("980.00")),
        (DecisionOutcome.WAIVED, None),
    ),
)
def test_blocking_until_decision_holds_the_task_until_the_pretension_is_decided(
    actor: User,
    process: Any,
    decision: str,
    approved: Decimal | None,
) -> None:
    task, pending_item = value_pending_ready(actor, process)

    with pytest.raises(ValidationError, match="espera da decisão"):
        complete_task(actor, task)

    pending_item = register_amount(actor, pending_item)
    with pytest.raises(ValidationError, match="espera da decisão"):
        complete_task(actor, task, key="complete-em-analise")

    pending_item = decide_amount(
        make_dp(actor, "dp-libera"),
        pending_item,
        decision=decision,
        approved=approved,
    )

    task.refresh_from_db()
    result = complete_task(actor, task, key="complete-decidida")
    assert pending_item.status in DECIDED_STATUSES
    assert result.task.status == SectorTaskStatus.COMPLETED


def test_regularization_alone_does_not_release_a_pending_blocked_until_decision(
    actor: User,
    process: Any,
) -> None:
    task, pending_item = value_pending_ready(actor, process)

    for status, key in (
        (PendingStatus.IN_REGULARIZATION, "status-em-regularizacao"),
        (PendingStatus.REGULARIZED, "status-regularizada"),
    ):
        pending_item = (
            ChangePendingStatusService()
            .execute(
                ChangePendingStatusCommand(
                    actor=actor,
                    pending_uuid=str(pending_item.uuid),
                    expected_version=pending_item.version,
                    idempotency_key=key,
                    status=status,
                    comment=f"Transição para {status}.",
                )
            )
            .pending_item
        )

    # Regularizar basta para `BLOQUEANTE`, não para `BLOQUEANTE_ATE_DECISAO`.
    with pytest.raises(ValidationError, match="espera da decisão"):
        complete_task(actor, task)

    # O encerramento explícito e auditado é a única saída sem decisão de valor.
    ChangePendingStatusService().execute(
        ChangePendingStatusCommand(
            actor=actor,
            pending_uuid=str(pending_item.uuid),
            expected_version=pending_item.version,
            idempotency_key="status-encerrada",
            status=PendingStatus.CLOSED,
            comment="Pendência encerrada sem pretensão de cobrança.",
        )
    )

    task.refresh_from_db()
    result = complete_task(actor, task, key="complete-encerrada")
    assert result.task.status == SectorTaskStatus.COMPLETED


def test_value_pending_below_blocking_does_not_hold_the_task(
    actor: User,
    process: Any,
) -> None:
    task = analysis_task(actor, process)
    enable_amounts(task)
    pending_item = create_value_pending(
        actor,
        task,
        blocking_level=BlockingLevel.NON_BLOCKING,
    )
    register_amount(actor, pending_item)

    task.refresh_from_db()
    result = complete_task(actor, task)

    assert result.task.status == SectorTaskStatus.COMPLETED
    assert PendingItem.objects.get(pk=pending_item.pk).status == PendingStatus.SUBMITTED_FOR_REVIEW


def api_post(
    client: Client,
    route: str,
    pending_item: PendingItem,
    body: dict[str, Any],
    key: str,
) -> Any:
    return client.post(
        reverse(route, kwargs={"pending_uuid": str(pending_item.uuid)}),
        data=json.dumps(body),
        content_type="application/json",
        HTTP_IDEMPOTENCY_KEY=key,
    )


def test_amount_api_runs_the_axis_and_publishes_the_pretension(
    actor: User,
    process: Any,
    client: Client,
) -> None:
    task, pending_item = value_pending_ready(actor, process)
    client.force_login(actor)

    informed = api_post(
        client,
        "pending-items-api:pending-amount",
        pending_item,
        {
            "expected_version": pending_item.version,
            "amount_informed": "1250.00",
            "justification": "Valor de mercado do equipamento não devolvido.",
        },
        "api-amount-informar",
    )
    assert informed.status_code == 200
    body = informed.json()
    assert body["status"] == "ENCAMINHADA_ANALISE"
    assert body["amount"]["amount_informed"] == "1250.00"
    assert body["amount"]["currency"] == "BRL"
    assert body["amount"]["informed_by"]["username"] == actor.username
    assert body["amount"]["amount_approved"] is None
    assert body["amount"]["decisions"] == []
    assert body["can_analyse_amount"] is True

    # Segregação da ADR-048: quem informou não decide, e o motivo chega legível.
    denied = api_post(
        client,
        "pending-items-api:pending-amount-decision",
        pending_item,
        {
            "expected_version": body["version"],
            "decision": "APROVADA_COBRANCA",
            "opinion": "Parecer de quem informou.",
            "amount_approved": "980.00",
        },
        "api-amount-autoaprovar",
    )
    assert denied.status_code == 403
    assert denied.json()["code"] == "permission_denied"
    assert "não pode decidir" in denied.json()["message"]

    client.force_login(make_dp(actor, "dp-api"))
    assessed = api_post(
        client,
        "pending-items-api:pending-amount-assessment",
        pending_item,
        {
            "expected_version": body["version"],
            "amount_assessed": "1100.00",
            "justification": "Apuração considerou a depreciação.",
        },
        "api-amount-apurar",
    )
    assert assessed.status_code == 200
    decided = api_post(
        client,
        "pending-items-api:pending-amount-decision",
        pending_item,
        {
            "expected_version": assessed.json()["version"],
            "decision": "APROVADA_COBRANCA",
            "opinion": "Cobrança aprovada pelo valor apurado.",
            "amount_approved": "1100.00",
        },
        "api-amount-decidir",
    )

    assert decided.status_code == 200
    amount = decided.json()["amount"]
    assert decided.json()["status"] == "APROVADA_COBRANCA"
    assert amount["amount_assessed"] == "1100.00"
    assert amount["amount_approved"] == "1100.00"
    assert amount["amount_processed"] is None
    assert amount["decisions"][0]["decision"] == "APROVADA_COBRANCA"
    assert amount["decisions"][0]["segregation_override"] is False


def test_amount_api_rejects_broken_contracts_and_replays_by_key(
    actor: User,
    process: Any,
    client: Client,
) -> None:
    _, pending_item = value_pending_ready(actor, process)
    client.force_login(actor)

    body = {
        "expected_version": pending_item.version,
        "amount_informed": "1250.00",
        "justification": "Valor de mercado do equipamento não devolvido.",
    }
    first = api_post(client, "pending-items-api:pending-amount", pending_item, body, "api-replay")
    replay = api_post(client, "pending-items-api:pending-amount", pending_item, body, "api-replay")
    assert first.status_code == 200
    assert replay.json()["idempotency_replayed"] is True

    conflict = api_post(
        client,
        "pending-items-api:pending-amount",
        pending_item,
        {**body, "amount_informed": "2000.00"},
        "api-replay",
    )
    assert conflict.status_code == 409
    assert conflict.json()["code"] == "idempotency_conflict"

    decider = make_dp(actor, "dp-contrato")
    client.force_login(decider)
    without_amount = api_post(
        client,
        "pending-items-api:pending-amount-decision",
        pending_item,
        {
            "expected_version": first.json()["version"],
            "decision": "APROVADA_COBRANCA",
            "opinion": "Aprovação sem valor.",
        },
        "api-decidir-sem-valor",
    )
    assert without_amount.status_code == 400
    assert "amount_approved" in without_amount.json()["details"]

    waived_with_amount = api_post(
        client,
        "pending-items-api:pending-amount-decision",
        pending_item,
        {
            "expected_version": first.json()["version"],
            "decision": "ABONADA",
            "opinion": "Abono com valor informado por engano.",
            "amount_approved": "10.00",
        },
        "api-abonar-com-valor",
    )
    assert waived_with_amount.status_code == 400
    assert PendingItem.objects.get(pk=pending_item.pk).status == PendingStatus.SUBMITTED_FOR_REVIEW


def test_task_payload_carries_the_amount_and_the_sector_permission(
    actor: User,
    process: Any,
    client: Client,
) -> None:
    task, pending_item = value_pending_ready(actor, process)
    register_amount(actor, pending_item)
    client.force_login(actor)

    response = client.get(reverse("offboarding-task-api:task-list"))

    assert response.status_code == 200
    row = next(item for item in response.json()["results"] if item["id"] == task.pk)
    assert row["sector"]["allows_amount"] is True
    pending = row["pending_items"][0]
    assert pending["amount"]["amount_informed"] == "1250.00"
    assert pending["can_analyse_amount"] is True


def test_responsible_without_dp_sees_the_amount_but_not_the_analysis(
    actor: User,
    process: Any,
    client: Client,
) -> None:
    task, pending_item = value_pending_ready(actor, process)
    register_amount(actor, pending_item)
    responsible = User.objects.create_user(
        username="responsavel-valor",
        email="responsavel-valor@example.invalid",
        password=PASSWORD,
    )
    SectorResponsible.objects.create(
        sector=ValidationSector.objects.get(pk=task.sector_id),
        user=responsible,
        valid_from=timezone.now() - timedelta(hours=1),
        assigned_by=actor,
        updated_by=actor,
    )
    client.force_login(responsible)

    listed = client.get(
        reverse("pending-items-api:pending-list"),
        {"task_id": task.pk},
    )

    assert listed.status_code == 200
    pending = listed.json()["results"][0]
    assert pending["amount"]["amount_informed"] == "1250.00"
    assert pending["can_analyse_amount"] is False

    denied = api_post(
        client,
        "pending-items-api:pending-amount-assessment",
        pending_item,
        {
            "expected_version": pending["version"],
            "amount_assessed": "900.00",
            "justification": "Tentativa de apurar sem DP.",
        },
        "api-apurar-sem-dp",
    )
    assert denied.status_code == 403
    assert "DP vigente" in denied.json()["message"]
