"""Transactional pending-item use cases."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Any

from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Q, QuerySet
from django.utils import timezone

from apps.accounts.models import User
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
from config.middleware import correlation_id

from .models import (
    BlockingLevel,
    PendingCategory,
    PendingComment,
    PendingItem,
    PendingItemLine,
    PendingStatus,
)

PENDING_CREATED_DESCRIPTION = "Registro explícito e idempotente de pendência setorial."
PENDING_COMMENTED_DESCRIPTION = "Comentário append-only registrado na pendência."
PENDING_STATUS_CHANGED_DESCRIPTION = "Transição explícita do estado de regularização."

ALLOWED_TRANSITIONS: dict[str, frozenset[str]] = {
    PendingStatus.OPEN: frozenset({PendingStatus.IN_REGULARIZATION}),
    PendingStatus.IN_REGULARIZATION: frozenset({PendingStatus.REGULARIZED}),
    PendingStatus.REGULARIZED: frozenset({PendingStatus.IN_REGULARIZATION, PendingStatus.CLOSED}),
    PendingStatus.CLOSED: frozenset(),
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
