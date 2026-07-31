"""Phase 6, slice 1: pretension and decision records behind a pending item."""

# ruff: noqa: F811

from __future__ import annotations

from decimal import Decimal
from typing import Any

import pytest
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.utils import timezone

from apps.accounts.models import User
from apps.pending_items.models import (
    BlockingLevel,
    DecisionOutcome,
    PendingAmount,
    PendingCategory,
    PendingDecision,
    PendingItem,
    PendingStatus,
)
from apps.pending_items.services import (
    CreatePendingItemCommand,
    CreatePendingItemService,
)
from tests.test_offboarding_start import (  # noqa: F401
    PASSWORD,
    actor,
    configured_draft,
    process,
    start,
)
from tests.test_offboarding_tasks import start_task, started_task

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
