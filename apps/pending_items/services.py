"""Transactional pending-item use cases."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Any, cast

from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.db.models import Q, QuerySet
from django.utils import timezone

from apps.accounts.authorization import has_effective_role, has_global_authority
from apps.accounts.models import PEOPLE_DEPARTMENT_ROLE_CODE, RoleAssignment, User
from apps.offboarding.models import (
    OffboardingProcess,
    ProcessActionIdempotency,
    ProcessAuditEvent,
    ProcessEventType,
    ProcessSectorTask,
    SectorTaskStatus,
)
from apps.offboarding.services import (
    IdempotencyConflict,
    lock_sector_task_and_authority,
    processes_for_actor,
    sector_tasks_for_actor,
)
from apps.sectors.models import ValidationSector
from config.middleware import correlation_id

from .models import (
    DECIDED_STATUSES,
    BlockingLevel,
    DecisionOutcome,
    PendingAmount,
    PendingCategory,
    PendingComment,
    PendingDecision,
    PendingItem,
    PendingItemLine,
    PendingStatus,
)

PENDING_CREATED_DESCRIPTION = "Registro explícito e idempotente de pendência setorial."
PENDING_COMMENTED_DESCRIPTION = "Comentário append-only registrado na pendência."
PENDING_STATUS_CHANGED_DESCRIPTION = "Transição explícita do estado de regularização."
AMOUNT_INFORMED_DESCRIPTION = "Pretensão de cobrança informada para análise."
AMOUNT_ASSESSED_DESCRIPTION = "Valor apurado registrado na análise da pretensão."
AMOUNT_CONTESTED_DESCRIPTION = "Contestação do valor registrada na pretensão."
AMOUNT_DECIDED_DESCRIPTION = "Decisão explícita sobre a pretensão de cobrança."

#: Transições do eixo de regularização, únicas alcançáveis pelo endpoint genérico
#: de situação. O eixo de decisão só é alcançado pelos services de valor, que
#: exigem pretensão registrada; daqui ele só tem saída para o encerramento.
ALLOWED_TRANSITIONS: dict[str, frozenset[str]] = {
    PendingStatus.OPEN: frozenset({PendingStatus.IN_REGULARIZATION}),
    PendingStatus.IN_REGULARIZATION: frozenset({PendingStatus.REGULARIZED}),
    PendingStatus.REGULARIZED: frozenset({PendingStatus.IN_REGULARIZATION, PendingStatus.CLOSED}),
    PendingStatus.SUBMITTED_FOR_REVIEW: frozenset(),
    PendingStatus.CONTESTED: frozenset(),
    PendingStatus.CHARGE_APPROVED: frozenset({PendingStatus.CLOSED}),
    PendingStatus.REJECTED: frozenset({PendingStatus.CLOSED}),
    PendingStatus.WAIVED: frozenset({PendingStatus.CLOSED}),
    PendingStatus.CLOSED: frozenset(),
}

#: Estados em que a pretensão ainda aguarda decisão.
UNDER_REVIEW_STATUSES = frozenset({PendingStatus.SUBMITTED_FOR_REVIEW, PendingStatus.CONTESTED})

#: Situação da pendência resultante de cada decisão.
DECISION_STATUS: dict[str, str] = {
    DecisionOutcome.CHARGE_APPROVED: PendingStatus.CHARGE_APPROVED,
    DecisionOutcome.REJECTED: PendingStatus.REJECTED,
    DecisionOutcome.WAIVED: PendingStatus.WAIVED,
}


@dataclass(frozen=True, slots=True)
class PendingLineValue:
    description: str
    code: str = ""
    asset_tag: str = ""
    serial_number: str = ""
    quantity: Decimal = Decimal("1")
    unit: str = "UN"
    item_condition: str = ""
    extra_data: dict[str, Any] | None = None


@dataclass(frozen=True, slots=True)
class CreatePendingItemCommand:
    actor: User
    task_id: int
    expected_task_version: int
    idempotency_key: str
    category: str
    title: str
    description: str
    blocking_level: str
    checklist_item_id: int | None = None
    regularization_due_at: datetime | None = None
    items: tuple[PendingLineValue, ...] = ()


@dataclass(frozen=True, slots=True)
class ChangePendingStatusCommand:
    actor: User
    pending_uuid: str
    expected_version: int
    idempotency_key: str
    status: str
    comment: str


@dataclass(frozen=True, slots=True)
class AddPendingCommentCommand:
    actor: User
    pending_uuid: str
    expected_version: int
    idempotency_key: str
    comment: str


@dataclass(frozen=True, slots=True)
class RegisterPendingAmountCommand:
    actor: User
    pending_uuid: str
    expected_version: int
    idempotency_key: str
    amount_informed: Decimal
    justification: str
    currency: str = "BRL"


@dataclass(frozen=True, slots=True)
class AssessPendingAmountCommand:
    actor: User
    pending_uuid: str
    expected_version: int
    idempotency_key: str
    amount_assessed: Decimal
    justification: str


@dataclass(frozen=True, slots=True)
class ContestPendingAmountCommand:
    actor: User
    pending_uuid: str
    expected_version: int
    idempotency_key: str
    amount_contested: Decimal
    justification: str


@dataclass(frozen=True, slots=True)
class DecidePendingAmountCommand:
    actor: User
    pending_uuid: str
    expected_version: int
    idempotency_key: str
    decision: str
    opinion: str
    amount_approved: Decimal | None = None


@dataclass(frozen=True, slots=True)
class PendingMutationResult:
    pending_item: PendingItem
    replayed: bool


def pending_items_for_actor(actor: User) -> QuerySet[PendingItem]:
    if not actor.is_active:
        return PendingItem.objects.none()
    return PendingItem.objects.filter(
        Q(task_id__in=sector_tasks_for_actor(actor).values("pk"))
        | Q(process_id__in=processes_for_actor(actor).values("pk"))
    )


def _validated_key(value: str) -> str:
    key = value.strip()
    if not key:
        raise ValidationError({"idempotency_key": "Informe a chave de idempotência."})
    if len(key) > 100:
        raise ValidationError(
            {"idempotency_key": "A chave de idempotência aceita até 100 caracteres."}
        )
    return key


def _canonical_hash(payload: dict[str, Any]) -> str:
    encoded = json.dumps(
        payload,
        separators=(",", ":"),
        sort_keys=True,
        ensure_ascii=False,
        default=str,
    ).encode()
    return hashlib.sha256(encoded).hexdigest()


def _action(prefix: str, identifier: int) -> str:
    value = f"{prefix}:{identifier}"
    if len(value) > 30:
        raise ValidationError("O identificador da ação excede o contrato de idempotência.")
    return value


def _replay(
    *,
    process: OffboardingProcess,
    actor: User,
    action: str,
    key: str,
    request_hash: str,
) -> PendingMutationResult | None:
    previous_rows = list(
        ProcessActionIdempotency.objects.select_for_update().filter(
            process=process, action=action, idempotency_key=key
        )
    )
    if not previous_rows:
        return None
    previous = previous_rows[0]
    if previous.actor_id != actor.pk or previous.request_hash != request_hash:
        raise IdempotencyConflict("A chave de idempotência já foi usada com outro conteúdo.")
    pending_uuid = previous.response.get("pending_uuid")
    pending_item = PendingItem.objects.get(uuid=pending_uuid)
    return PendingMutationResult(pending_item=pending_item, replayed=True)


def _record_idempotency(
    *,
    process: OffboardingProcess,
    pending_item: PendingItem,
    actor: User,
    action: str,
    key: str,
    request_hash: str,
) -> None:
    ProcessActionIdempotency.objects.create(
        process=process,
        action=action,
        idempotency_key=key,
        request_hash=request_hash,
        response={
            "pending_uuid": str(pending_item.uuid),
            "status": pending_item.status,
            "version": pending_item.version,
        },
        actor=actor,
    )


def _lock_pending_and_authority(
    *,
    actor: User,
    pending_uuid: str,
    at: datetime,
) -> tuple[User, OffboardingProcess, ProcessSectorTask, PendingItem]:
    task_id = PendingItem.objects.values_list("task_id", flat=True).get(uuid=pending_uuid)
    locked_actor, process, task = lock_sector_task_and_authority(
        actor=actor,
        task_id=task_id,
        at=at,
        allow_process_coordinator=True,
    )
    pending_item = PendingItem.objects.select_for_update().get(
        uuid=pending_uuid,
        task=task,
    )
    return locked_actor, process, task, pending_item


class CreatePendingItemService:
    @transaction.atomic
    def execute(self, command: CreatePendingItemCommand) -> PendingMutationResult:
        key = _validated_key(command.idempotency_key)
        item_payload = [
            {
                "description": item.description,
                "code": item.code,
                "asset_tag": item.asset_tag,
                "serial_number": item.serial_number,
                "quantity": str(item.quantity),
                "unit": item.unit,
                "item_condition": item.item_condition,
                "extra_data": item.extra_data or {},
            }
            for item in command.items
        ]
        request_hash = _canonical_hash(
            {
                "task_id": command.task_id,
                "expected_task_version": command.expected_task_version,
                "category": command.category,
                "title": command.title,
                "description": command.description,
                "blocking_level": command.blocking_level,
                "checklist_item_id": command.checklist_item_id,
                "regularization_due_at": command.regularization_due_at,
                "items": item_payload,
            }
        )
        actor, process, task = lock_sector_task_and_authority(
            actor=command.actor,
            task_id=command.task_id,
            at=timezone.now(),
            allow_process_coordinator=True,
        )
        action = _action("PCREATE", task.pk)
        replay = _replay(
            process=process,
            actor=actor,
            action=action,
            key=key,
            request_hash=request_hash,
        )
        if replay is not None:
            return replay
        if task.status != SectorTaskStatus.IN_ANALYSIS:
            raise ValidationError("Pendências só podem ser registradas em tarefa em análise.")
        if task.version != command.expected_task_version:
            raise ValidationError("A tarefa foi alterada por outra sessão. Recarregue a página.")
        if command.category not in PendingCategory.values:
            raise ValidationError({"category": "A categoria da pendência é inválida."})
        if command.blocking_level not in BlockingLevel.values:
            raise ValidationError({"blocking_level": "A classificação de bloqueio é inválida."})
        checklist_item = None
        if command.checklist_item_id is not None:
            checklist_item = task.checklist_items.select_for_update().get(
                pk=command.checklist_item_id
            )
            if not checklist_item.allows_pending:
                raise ValidationError(
                    {"checklist_item_id": "O item de checklist não permite pendência."}
                )

        pending_item = PendingItem(
            process=process,
            task=task,
            checklist_item=checklist_item,
            category=command.category,
            title=command.title,
            description=command.description,
            blocking_level=command.blocking_level,
            regularization_due_at=command.regularization_due_at,
            registered_by=actor,
        )
        pending_item.full_clean()
        pending_item.save()
        for item_value in command.items:
            line = PendingItemLine(
                pending_item=pending_item,
                description=item_value.description,
                code=item_value.code,
                asset_tag=item_value.asset_tag,
                serial_number=item_value.serial_number,
                quantity=item_value.quantity,
                unit=item_value.unit,
                item_condition=item_value.item_condition,
                extra_data=item_value.extra_data or {},
            )
            line.full_clean()
            line.save()
        ProcessAuditEvent.objects.create(
            process=process,
            event_type=ProcessEventType.PENDING_CREATED,
            actor=actor,
            description=PENDING_CREATED_DESCRIPTION,
            data={
                "pending_uuid": str(pending_item.uuid),
                "task_id": task.pk,
                "sector_id": task.sector_id,
                "checklist_item_id": command.checklist_item_id,
                "category": pending_item.category,
                "blocking_level": pending_item.blocking_level,
                "status": pending_item.status,
                "item_count": len(command.items),
                "pending_version": pending_item.version,
            },
            correlation_id=correlation_id.get(),
        )
        _record_idempotency(
            process=process,
            pending_item=pending_item,
            actor=actor,
            action=action,
            key=key,
            request_hash=request_hash,
        )
        return PendingMutationResult(pending_item=pending_item, replayed=False)


class AddPendingCommentService:
    @transaction.atomic
    def execute(self, command: AddPendingCommentCommand) -> PendingMutationResult:
        key = _validated_key(command.idempotency_key)
        comment_text = command.comment.strip()
        request_hash = _canonical_hash(
            {
                "pending_uuid": command.pending_uuid,
                "expected_version": command.expected_version,
                "comment": comment_text,
            }
        )
        actor, process, task, pending_item = _lock_pending_and_authority(
            actor=command.actor,
            pending_uuid=command.pending_uuid,
            at=timezone.now(),
        )
        action = _action("PCOMM", pending_item.pk)
        replay = _replay(
            process=process,
            actor=actor,
            action=action,
            key=key,
            request_hash=request_hash,
        )
        if replay is not None:
            return replay
        if pending_item.status == PendingStatus.CLOSED:
            raise ValidationError("Uma pendência encerrada não aceita novos comentários.")
        if pending_item.version != command.expected_version:
            raise ValidationError("A pendência foi alterada por outra sessão. Recarregue a página.")
        comment = PendingComment(pending_item=pending_item, author=actor, text=comment_text)
        comment.full_clean()
        comment.save()
        pending_item.version += 1
        pending_item.full_clean()
        pending_item.save(update_fields=("version", "updated_at"))
        ProcessAuditEvent.objects.create(
            process=process,
            event_type=ProcessEventType.PENDING_COMMENTED,
            actor=actor,
            description=PENDING_COMMENTED_DESCRIPTION,
            data={
                "pending_uuid": str(pending_item.uuid),
                "task_id": task.pk,
                "comment_id": comment.pk,
                "pending_version": pending_item.version,
            },
            correlation_id=correlation_id.get(),
        )
        _record_idempotency(
            process=process,
            pending_item=pending_item,
            actor=actor,
            action=action,
            key=key,
            request_hash=request_hash,
        )
        return PendingMutationResult(pending_item=pending_item, replayed=False)


class ChangePendingStatusService:
    @transaction.atomic
    def execute(self, command: ChangePendingStatusCommand) -> PendingMutationResult:
        key = _validated_key(command.idempotency_key)
        comment_text = command.comment.strip()
        request_hash = _canonical_hash(
            {
                "pending_uuid": command.pending_uuid,
                "expected_version": command.expected_version,
                "status": command.status,
                "comment": comment_text,
            }
        )
        actor, process, task, pending_item = _lock_pending_and_authority(
            actor=command.actor,
            pending_uuid=command.pending_uuid,
            at=timezone.now(),
        )
        action = _action("PSTATUS", pending_item.pk)
        replay = _replay(
            process=process,
            actor=actor,
            action=action,
            key=key,
            request_hash=request_hash,
        )
        if replay is not None:
            return replay
        if pending_item.version != command.expected_version:
            raise ValidationError("A pendência foi alterada por outra sessão. Recarregue a página.")
        if command.status not in ALLOWED_TRANSITIONS.get(pending_item.status, frozenset()):
            raise ValidationError(
                f"A transição de {pending_item.status} para {command.status} não é permitida."
            )
        comment = PendingComment(pending_item=pending_item, author=actor, text=comment_text)
        comment.full_clean()
        comment.save()
        previous_status = pending_item.status
        pending_item.status = command.status
        pending_item.version += 1
        pending_item.full_clean()
        pending_item.save(update_fields=("status", "version", "updated_at"))
        ProcessAuditEvent.objects.create(
            process=process,
            event_type=ProcessEventType.PENDING_STATUS_CHANGED,
            actor=actor,
            description=PENDING_STATUS_CHANGED_DESCRIPTION,
            data={
                "pending_uuid": str(pending_item.uuid),
                "task_id": task.pk,
                "previous_status": previous_status,
                "status": pending_item.status,
                "comment_id": comment.pk,
                "pending_version": pending_item.version,
            },
            correlation_id=correlation_id.get(),
        )
        _record_idempotency(
            process=process,
            pending_item=pending_item,
            actor=actor,
            action=action,
            key=key,
            request_hash=request_hash,
        )
        return PendingMutationResult(pending_item=pending_item, replayed=False)


def can_analyse_amounts(actor: User, process: OffboardingProcess) -> bool:
    """Leitura sem lock de quem apura e decide valor, para a API oferecer a ação."""

    return has_effective_role(
        actor,
        PEOPLE_DEPARTMENT_ROLE_CODE,
        company_code=process.company_code,
        branch_code=process.branch_code,
    )


def _require_coordinator(actor: User, process: OffboardingProcess) -> None:
    """Exigir DP vigente no escopo do processo, ou a autoridade global (ADR-044)."""

    if has_global_authority(actor):
        return
    list(RoleAssignment.objects.select_for_update().filter(user=actor).order_by("pk"))
    if not can_analyse_amounts(actor, process):
        raise PermissionDenied("A análise de valores exige DP vigente no escopo do processo.")


def _positive_amount(value: Decimal | None, field: str) -> Decimal:
    if value is None or value <= 0:
        raise ValidationError({field: "O valor informado deve ser maior que zero."})
    return value


def _locked_amount(pending_item: PendingItem) -> PendingAmount:
    try:
        return cast(
            PendingAmount,
            PendingAmount.objects.select_for_update().get(pending_item=pending_item),
        )
    except PendingAmount.DoesNotExist as exc:
        raise ValidationError("A pendência ainda não possui pretensão registrada.") from exc


def _amount_context(
    *,
    actor: User,
    pending_uuid: str,
    require_coordinator: bool,
) -> tuple[User, OffboardingProcess, ProcessSectorTask, PendingItem]:
    locked_actor, process, task, pending_item = _lock_pending_and_authority(
        actor=actor,
        pending_uuid=pending_uuid,
        at=timezone.now(),
    )
    if require_coordinator:
        _require_coordinator(locked_actor, process)
    if pending_item.category != PendingCategory.VALUE:
        raise ValidationError("Somente pendência de categoria Valor possui pretensão de cobrança.")
    return locked_actor, process, task, pending_item


def _register_amount_trail(
    *,
    process: OffboardingProcess,
    task: ProcessSectorTask,
    pending_item: PendingItem,
    amount: PendingAmount,
    actor: User,
    text: str,
    event_type: str,
    description: str,
    extra: dict[str, Any],
) -> None:
    """Comentar, versionar e auditar a pendência na mesma transação da pretensão."""

    comment = PendingComment(pending_item=pending_item, author=actor, text=text)
    comment.full_clean()
    comment.save()
    ProcessAuditEvent.objects.create(
        process=process,
        event_type=event_type,
        actor=actor,
        description=description,
        data={
            "pending_uuid": str(pending_item.uuid),
            "task_id": task.pk,
            "sector_id": task.sector_id,
            "currency": amount.currency,
            "status": pending_item.status,
            "comment_id": comment.pk,
            "pending_version": pending_item.version,
            "amount_version": amount.version,
            **extra,
        },
        correlation_id=correlation_id.get(),
    )


class RegisterPendingAmountService:
    """Lançar a pretensão de cobrança: valor é solicitação de análise (ADR-009)."""

    @transaction.atomic
    def execute(self, command: RegisterPendingAmountCommand) -> PendingMutationResult:
        key = _validated_key(command.idempotency_key)
        justification = command.justification.strip()
        request_hash = _canonical_hash(
            {
                "pending_uuid": command.pending_uuid,
                "expected_version": command.expected_version,
                "amount_informed": command.amount_informed,
                "currency": command.currency,
                "justification": justification,
            }
        )
        actor, process, task, pending_item = _amount_context(
            actor=command.actor,
            pending_uuid=command.pending_uuid,
            require_coordinator=False,
        )
        action = _action("PAMOUNT", pending_item.pk)
        replay = _replay(
            process=process,
            actor=actor,
            action=action,
            key=key,
            request_hash=request_hash,
        )
        if replay is not None:
            return replay
        if pending_item.version != command.expected_version:
            raise ValidationError("A pendência foi alterada por outra sessão. Recarregue a página.")
        if pending_item.status != PendingStatus.OPEN:
            raise ValidationError("Somente uma pendência aberta aceita o lançamento do valor.")
        sector = ValidationSector.objects.select_for_update().get(pk=task.sector_id)
        if not sector.allows_amount:
            raise ValidationError(
                {"amount_informed": "O setor não está habilitado a lançar valores."}
            )
        if PendingAmount.objects.filter(pending_item=pending_item).exists():
            raise ValidationError("A pendência já possui pretensão registrada.")

        amount = PendingAmount(
            pending_item=pending_item,
            amount_informed=_positive_amount(command.amount_informed, "amount_informed"),
            currency=command.currency,
            justification=justification,
            informed_by=actor,
        )
        amount.full_clean()
        amount.save()
        pending_item.status = PendingStatus.SUBMITTED_FOR_REVIEW
        pending_item.version += 1
        pending_item.full_clean()
        pending_item.save(update_fields=("status", "version", "updated_at"))
        _register_amount_trail(
            process=process,
            task=task,
            pending_item=pending_item,
            amount=amount,
            actor=actor,
            text=justification,
            event_type=ProcessEventType.PENDING_AMOUNT_INFORMED,
            description=AMOUNT_INFORMED_DESCRIPTION,
            extra={"amount_informed": str(amount.amount_informed)},
        )
        _record_idempotency(
            process=process,
            pending_item=pending_item,
            actor=actor,
            action=action,
            key=key,
            request_hash=request_hash,
        )
        return PendingMutationResult(pending_item=pending_item, replayed=False)


class AssessPendingAmountService:
    """Registrar o valor apurado na análise; a pretensão continua aguardando decisão."""

    @transaction.atomic
    def execute(self, command: AssessPendingAmountCommand) -> PendingMutationResult:
        key = _validated_key(command.idempotency_key)
        justification = command.justification.strip()
        request_hash = _canonical_hash(
            {
                "pending_uuid": command.pending_uuid,
                "expected_version": command.expected_version,
                "amount_assessed": command.amount_assessed,
                "justification": justification,
            }
        )
        actor, process, task, pending_item = _amount_context(
            actor=command.actor,
            pending_uuid=command.pending_uuid,
            require_coordinator=True,
        )
        action = _action("PASSESS", pending_item.pk)
        replay = _replay(
            process=process,
            actor=actor,
            action=action,
            key=key,
            request_hash=request_hash,
        )
        if replay is not None:
            return replay
        if pending_item.version != command.expected_version:
            raise ValidationError("A pendência foi alterada por outra sessão. Recarregue a página.")
        if pending_item.status not in UNDER_REVIEW_STATUSES:
            raise ValidationError("Somente uma pretensão em análise aceita valor apurado.")
        amount = _locked_amount(pending_item)
        amount.amount_assessed = _positive_amount(command.amount_assessed, "amount_assessed")
        amount.version += 1
        amount.full_clean()
        amount.save(update_fields=("amount_assessed", "version", "updated_at"))
        previous_status = pending_item.status
        pending_item.status = PendingStatus.SUBMITTED_FOR_REVIEW
        pending_item.version += 1
        pending_item.full_clean()
        pending_item.save(update_fields=("status", "version", "updated_at"))
        _register_amount_trail(
            process=process,
            task=task,
            pending_item=pending_item,
            amount=amount,
            actor=actor,
            text=justification,
            event_type=ProcessEventType.PENDING_AMOUNT_ASSESSED,
            description=AMOUNT_ASSESSED_DESCRIPTION,
            extra={
                "amount_assessed": str(amount.amount_assessed),
                "previous_status": previous_status,
            },
        )
        _record_idempotency(
            process=process,
            pending_item=pending_item,
            actor=actor,
            action=action,
            key=key,
            request_hash=request_hash,
        )
        return PendingMutationResult(pending_item=pending_item, replayed=False)


class ContestPendingAmountService:
    """Registrar a contestação do valor, que devolve a pretensão à análise."""

    @transaction.atomic
    def execute(self, command: ContestPendingAmountCommand) -> PendingMutationResult:
        key = _validated_key(command.idempotency_key)
        justification = command.justification.strip()
        request_hash = _canonical_hash(
            {
                "pending_uuid": command.pending_uuid,
                "expected_version": command.expected_version,
                "amount_contested": command.amount_contested,
                "justification": justification,
            }
        )
        actor, process, task, pending_item = _amount_context(
            actor=command.actor,
            pending_uuid=command.pending_uuid,
            require_coordinator=False,
        )
        action = _action("PCONTEST", pending_item.pk)
        replay = _replay(
            process=process,
            actor=actor,
            action=action,
            key=key,
            request_hash=request_hash,
        )
        if replay is not None:
            return replay
        if pending_item.version != command.expected_version:
            raise ValidationError("A pendência foi alterada por outra sessão. Recarregue a página.")
        if pending_item.status != PendingStatus.SUBMITTED_FOR_REVIEW:
            raise ValidationError(
                "Somente uma pretensão encaminhada para análise pode ser contestada."
            )
        amount = _locked_amount(pending_item)
        amount.amount_contested = _positive_amount(command.amount_contested, "amount_contested")
        amount.version += 1
        amount.full_clean()
        amount.save(update_fields=("amount_contested", "version", "updated_at"))
        pending_item.status = PendingStatus.CONTESTED
        pending_item.version += 1
        pending_item.full_clean()
        pending_item.save(update_fields=("status", "version", "updated_at"))
        _register_amount_trail(
            process=process,
            task=task,
            pending_item=pending_item,
            amount=amount,
            actor=actor,
            text=justification,
            event_type=ProcessEventType.PENDING_AMOUNT_CONTESTED,
            description=AMOUNT_CONTESTED_DESCRIPTION,
            extra={"amount_contested": str(amount.amount_contested)},
        )
        _record_idempotency(
            process=process,
            pending_item=pending_item,
            actor=actor,
            action=action,
            key=key,
            request_hash=request_hash,
        )
        return PendingMutationResult(pending_item=pending_item, replayed=False)


class DecidePendingAmountService:
    """Decidir a pretensão com parecer, sob segregação de função (ADR-048)."""

    @transaction.atomic
    def execute(self, command: DecidePendingAmountCommand) -> PendingMutationResult:
        key = _validated_key(command.idempotency_key)
        opinion = command.opinion.strip()
        request_hash = _canonical_hash(
            {
                "pending_uuid": command.pending_uuid,
                "expected_version": command.expected_version,
                "decision": command.decision,
                "opinion": opinion,
                "amount_approved": command.amount_approved,
            }
        )
        actor, process, task, pending_item = _amount_context(
            actor=command.actor,
            pending_uuid=command.pending_uuid,
            require_coordinator=True,
        )
        action = _action("PDECIDE", pending_item.pk)
        replay = _replay(
            process=process,
            actor=actor,
            action=action,
            key=key,
            request_hash=request_hash,
        )
        if replay is not None:
            return replay
        if pending_item.version != command.expected_version:
            raise ValidationError("A pendência foi alterada por outra sessão. Recarregue a página.")
        if pending_item.status not in UNDER_REVIEW_STATUSES:
            raise ValidationError("Somente uma pretensão em análise pode ser decidida.")
        if command.decision not in DECISION_STATUS:
            raise ValidationError({"decision": "A decisão sobre o valor é inválida."})
        amount = _locked_amount(pending_item)

        # Segregação de função: quem informou o valor não o aprova. O SuperAdmin
        # rompe essa barra pela ADR-048, e a trilha registra que ele o fez.
        decides_own_amount = amount.informed_by_id == actor.pk
        segregation_override = decides_own_amount and has_global_authority(actor)
        if decides_own_amount and not segregation_override:
            raise PermissionDenied("Quem informou o valor não pode decidir a própria pretensão.")

        if command.decision == DecisionOutcome.CHARGE_APPROVED:
            approved = _positive_amount(command.amount_approved, "amount_approved")
        else:
            approved = Decimal("0.00")
        decided_at = timezone.now()
        amount.amount_approved = approved
        amount.approved_by = actor
        amount.approved_at = decided_at
        amount.version += 1
        amount.full_clean()
        amount.save(
            update_fields=("amount_approved", "approved_by", "approved_at", "version", "updated_at")
        )
        decision = PendingDecision(
            pending_item=pending_item,
            decision=command.decision,
            opinion=opinion,
            decided_by=actor,
            segregation_override=segregation_override,
        )
        decision.full_clean()
        decision.save()
        pending_item.status = DECISION_STATUS[command.decision]
        pending_item.version += 1
        pending_item.full_clean()
        pending_item.save(update_fields=("status", "version", "updated_at"))
        _register_amount_trail(
            process=process,
            task=task,
            pending_item=pending_item,
            amount=amount,
            actor=actor,
            text=opinion,
            event_type=ProcessEventType.PENDING_AMOUNT_DECIDED,
            description=AMOUNT_DECIDED_DESCRIPTION,
            extra={
                "decision": command.decision,
                "decision_id": decision.pk,
                "amount_approved": str(amount.amount_approved),
                "segregation_override": segregation_override,
            },
        )
        _record_idempotency(
            process=process,
            pending_item=pending_item,
            actor=actor,
            action=action,
            key=key,
            request_hash=request_hash,
        )
        return PendingMutationResult(pending_item=pending_item, replayed=False)


@dataclass(frozen=True, slots=True)
class AmountTotals:
    """Somatório por moeda: consolidar moedas diferentes numa linha seria falso."""

    currency: str
    informed: Decimal
    assessed: Decimal
    contested: Decimal
    approved: Decimal
    processed: Decimal


@dataclass(frozen=True, slots=True)
class ProcessAmountConsolidation:
    process: OffboardingProcess
    pending_items: tuple[PendingItem, ...]
    totals: tuple[AmountTotals, ...]
    undecided_count: int
    #: Decisões em que o decisor é quem informou o valor, pela exceção da ADR-048.
    segregation_overrides: tuple[PendingDecision, ...]


def consolidate_process_amounts(process: OffboardingProcess) -> ProcessAmountConsolidation:
    """Consolidar as pretensões do processo para conferência, sem alterar nada.

    Só entra na conta a pendência de categoria `VALOR` com pretensão lançada. A
    decisão rejeitada e a abonada resolvem em zero no service, então somam sem
    tratamento especial; `VALOR_PROCESSADO` continua vindo do Senior (ADR-009).
    """

    rows = tuple(
        PendingItem.objects.filter(
            process=process,
            category=PendingCategory.VALUE,
            amount__isnull=False,
        )
        .select_related("task", "amount__informed_by", "amount__approved_by")
        .prefetch_related("decisions__decided_by")
        .order_by("identified_at", "pk")
    )
    buckets: dict[str, list[Decimal]] = {}
    for pending_item in rows:
        amount = pending_item.amount
        bucket = buckets.setdefault(amount.currency, [Decimal("0.00")] * 5)
        for index, value in enumerate(
            (
                amount.amount_informed,
                amount.amount_assessed,
                amount.amount_contested,
                amount.amount_approved,
                amount.amount_processed,
            )
        ):
            if value is not None:
                bucket[index] += value
    totals = tuple(
        AmountTotals(
            currency=currency,
            informed=values[0],
            assessed=values[1],
            contested=values[2],
            approved=values[3],
            processed=values[4],
        )
        for currency, values in sorted(buckets.items())
    )
    return ProcessAmountConsolidation(
        process=process,
        pending_items=rows,
        totals=totals,
        undecided_count=sum(1 for row in rows if row.status not in DECIDED_STATUSES),
        segregation_overrides=tuple(
            decision
            for row in rows
            for decision in row.decisions.all()
            if decision.segregation_override
        ),
    )
