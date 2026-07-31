"""Operação da fila: quem enxerga e quem reprocessa (RF-027, R07).

Vive fora de `services.py` de propósito. O enfileiramento é chamado pelos
services de domínio; a operação chama os services de domínio de volta para
resolver visibilidade. Manter os dois módulos separados mantém a dependência em
um sentido só.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any

from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import QuerySet
from django.utils import timezone

from apps.accounts.models import User
from apps.offboarding.models import (
    OffboardingProcess,
    ProcessActionIdempotency,
    ProcessAuditEvent,
    ProcessEventType,
)
from apps.offboarding.services import IdempotencyConflict, processes_for_actor
from config.middleware import correlation_id

from .models import Notification, NotificationStatus

NOTIFICATION_REPROCESSED_DESCRIPTION = "Notificação recolocada na fila por decisão explícita."

#: Só a mensagem que desistiu volta para a fila. Reenviar uma entregue
#: duplicaria o e-mail; as demais situações já caminham sozinhas.
REPROCESSABLE_STATUSES = frozenset({NotificationStatus.FAILED})


@dataclass(frozen=True, slots=True)
class ReprocessNotificationCommand:
    actor: User
    notification_uuid: str
    expected_version: int
    idempotency_key: str


@dataclass(frozen=True, slots=True)
class ReprocessResult:
    notification: Notification
    replayed: bool


def notifications_for_actor(actor: User) -> QuerySet[Notification]:
    """A fila é conferência do processo: quem só responde por setor não a enxerga.

    Mesma régua da consolidação de valores — o painel de operação mostra para
    quem cada aviso foi, e isso atravessa os setores do processo.
    """

    if not actor.is_active:
        return Notification.objects.none()
    return Notification.objects.filter(
        process_id__in=processes_for_actor(actor).values("pk"),
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


def _action(notification_pk: int) -> str:
    value = f"NOTIFREPROC:{notification_pk}"
    if len(value) > 30:
        raise ValidationError("O identificador da ação excede o contrato de idempotência.")
    return value


class ReprocessNotificationService:
    """Devolve à fila uma mensagem que desistiu, com trilha de quem mandou."""

    @transaction.atomic
    def execute(self, command: ReprocessNotificationCommand) -> ReprocessResult:
        key = _validated_key(command.idempotency_key)
        request_hash = _canonical_hash(
            {
                "notification_uuid": command.notification_uuid,
                "expected_version": command.expected_version,
            }
        )
        visible = notifications_for_actor(command.actor).filter(uuid=command.notification_uuid)
        if not visible.exists():
            raise Notification.DoesNotExist("Notificação inexistente ou fora do escopo.")
        notification = Notification.objects.select_for_update().get(uuid=command.notification_uuid)
        process = OffboardingProcess.objects.select_for_update().get(pk=notification.process_id)
        action = _action(notification.pk)
        replay = self._replay(
            process=process,
            actor=command.actor,
            action=action,
            key=key,
            request_hash=request_hash,
        )
        if replay is not None:
            return replay
        if notification.status not in REPROCESSABLE_STATUSES:
            raise ValidationError(
                "Só uma notificação em falha volta para a fila; as demais seguem sozinhas."
            )
        if notification.version != command.expected_version:
            raise ValidationError("A notificação foi alterada por outra sessão. Recarregue.")

        attempts_before = notification.attempts
        notification.status = NotificationStatus.PENDING
        # Orçamento novo de tentativas: as anteriores continuam registradas em
        # `SGPD_NOTIFICATION_ATTEMPT` e nenhuma delas é apagada.
        notification.attempts = 0
        notification.next_attempt_at = timezone.now()
        notification.version += 1
        notification.save(
            update_fields=(
                "status",
                "attempts",
                "next_attempt_at",
                "version",
                "updated_at",
            )
        )
        ProcessAuditEvent.objects.create(
            process=process,
            event_type=ProcessEventType.NOTIFICATION_REPROCESSED,
            actor=command.actor,
            description=NOTIFICATION_REPROCESSED_DESCRIPTION,
            data={
                "notification_uuid": str(notification.uuid),
                "event": notification.event,
                "channel": notification.channel,
                "recipient_id": notification.recipient_id,
                "attempts_before": attempts_before,
                "notification_version": notification.version,
            },
            correlation_id=correlation_id.get(),
        )
        ProcessActionIdempotency.objects.create(
            process=process,
            action=action,
            idempotency_key=key,
            request_hash=request_hash,
            response={
                "notification_uuid": str(notification.uuid),
                "status": notification.status,
                "version": notification.version,
            },
            actor=command.actor,
        )
        return ReprocessResult(notification=notification, replayed=False)

    def _replay(
        self,
        *,
        process: OffboardingProcess,
        actor: User,
        action: str,
        key: str,
        request_hash: str,
    ) -> ReprocessResult | None:
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
        notification = Notification.objects.get(uuid=previous.response["notification_uuid"])
        return ReprocessResult(notification=notification, replayed=True)
