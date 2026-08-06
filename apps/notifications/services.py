"""Enfileiramento e despacho das notificações (ADR-049).

O enfileiramento roda **dentro** da transação de quem o chama: a mensagem só
existe se o fato que a originou existir, e nunca ao contrário. O despacho roda
depois, fora da requisição, e trata cada mensagem isoladamente — uma recusa do
SMTP não derruba o lote nem a mudança de domínio que já foi confirmada.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any

from django.core.exceptions import ValidationError
from django.core.mail import EmailMessage
from django.db import IntegrityError, transaction
from django.db.models import Max
from django.template.exceptions import TemplateDoesNotExist
from django.template.loader import render_to_string
from django.utils import timezone

from apps.accounts.models import User
from apps.offboarding.models import OffboardingProcess, ProcessSectorTask
from apps.sectors.models import ValidationSector
from config.middleware import correlation_id

from .config import EmailConfig
from .models import (
    Notification,
    NotificationAttempt,
    NotificationChannel,
    NotificationEvent,
    NotificationStatus,
)

logger = logging.getLogger(__name__)

#: Espera antes de cada nova tentativa, em segundos. A última se repete até
#: esgotar `max_attempts`.
RETRY_BACKOFF_SECONDS: tuple[int, ...] = (60, 300, 900, 3600)

#: Limite do erro guardado na linha: o suficiente para diagnosticar sem
#: transformar a fila em depósito de stack trace.
MAX_ERROR_LENGTH = 2000

STALE_ATTEMPT_ERROR = "Tentativa interrompida: o despachante não confirmou o envio."


@dataclass(frozen=True, slots=True)
class EnqueueNotificationCommand:
    event: str
    process: OffboardingProcess
    recipients: tuple[User, ...]
    task: ProcessSectorTask | None = None
    sector: ValidationSector | None = None
    #: Discriminador do marco dentro do alvo. Vazio usa a tarefa ou o processo,
    #: o que basta para eventos que acontecem uma única vez por alvo.
    scope: str = ""
    context: dict[str, Any] | None = None


@dataclass(frozen=True, slots=True)
class EnqueueResult:
    created: tuple[Notification, ...]
    #: Destinatários que já tinham a mesma mensagem deste marco.
    duplicated: int
    #: Destinatários sem endereço utilizável, por `id` de usuário.
    without_address: tuple[int, ...]


@dataclass(frozen=True, slots=True)
class DispatchNotificationsCommand:
    limit: int | None = None
    stale_after: timedelta | None = None


@dataclass(frozen=True, slots=True)
class DispatchResult:
    sent: int
    failed: int
    rescheduled: int
    requeued: int
    #: Verdadeiro quando a central está com o envio desligado: a fila continua
    #: acumulando e nada é entregue.
    disabled: bool = False


def _url(base: str, path: str) -> str:
    return f"{base}{path}"


def message_context(
    command: EnqueueNotificationCommand,
    recipient: User,
    config: EmailConfig,
) -> dict[str, Any]:
    """Contexto legível da mensagem.

    Nome do colaborador, CPF e valores ficam de fora por decisão: o e-mail
    atravessa a rede corporativa e pode chegar a uma caixa errada, enquanto o
    sistema já autoriza quem pode ver o dado. O que vai no corpo é o suficiente
    para a pessoa saber o que fazer e onde.
    """

    process = command.process
    task = command.task
    sector = command.sector or (task.sector if task is not None else None)
    context: dict[str, Any] = {
        "process_ref": str(process.uuid)[:8],
        "process_uuid": str(process.uuid),
        "process_due_date": process.due_date,
        "employee_registration": process.employee_registration,
        "sector_name": sector.name if sector is not None else "",
        "task_due_at": task.due_at if task is not None else None,
        "recipient_name": recipient.get_short_name() or recipient.get_username(),
        "tasks_url": _url(config.base_url, "/fe/tarefas"),
        "process_url": _url(config.base_url, "/fe/processos"),
        "amounts_url": _url(config.base_url, f"/fe/processos/{process.uuid}/valores"),
    }
    context.update(command.context or {})
    return context


def render_message(event: str, context: dict[str, Any]) -> tuple[str, str]:
    """Renderiza o template do evento: primeira linha é o assunto, resto é o corpo."""

    if event not in NotificationEvent.values:
        raise ValidationError({"event": f"Evento de notificação desconhecido: {event}."})
    try:
        rendered = render_to_string(f"notifications/{event}.txt", context)
    except TemplateDoesNotExist as missing:
        raise ValidationError(
            {"event": f"Não há template de mensagem para o evento {event}."}
        ) from missing
    subject, _, body = rendered.strip().partition("\n")
    subject = " ".join(subject.split())
    body = body.strip()
    if not subject or not body:
        raise ValidationError(
            {"event": f"O template do evento {event} precisa de assunto e corpo."}
        )
    # Truncar o assunto é preferível a derrubar a transação de domínio por um
    # nome de setor longo; o corpo repete a mesma informação.
    return subject[:200], body


def _dedup_key(*, event: str, channel: str, scope: str, recipient_id: int) -> str:
    key = f"{event}:{channel}:{scope}:{recipient_id}"
    if len(key) > 120:
        raise ValidationError({"dedup_key": "A chave de deduplicação excede o contrato."})
    return key


def _default_scope(command: EnqueueNotificationCommand) -> str:
    if command.task is not None:
        return f"t{command.task.pk}"
    return f"p{command.process.pk}"


def _schedule_immediate_dispatch(notification_pk: int) -> None:
    """Pede ao worker que despache esta mensagem assim que o fato for confirmado.

    Depois do commit, nunca antes: agendar dentro da transação enviaria e-mail
    de um fato que ainda pode ser revertido.

    Falhar aqui não é erro de domínio. Se o broker estiver fora, a mensagem
    continua `PENDENTE` no Oracle e a varredura periódica a entrega — a fila
    durável é exatamente o que permite tratar este disparo como aceleração, e
    não como transporte (ADR-057).
    """

    def _publish() -> None:
        # Import tardio: `tasks` importa este módulo, e o ciclo só não existe
        # porque a resolução acontece na hora da chamada.
        from .tasks import dispatch_notification

        try:
            dispatch_notification.delay(notification_pk)
        except Exception:
            logger.warning(
                "notification.immediate_dispatch_not_scheduled",
                extra={"notification_pk": notification_pk},
            )

    transaction.on_commit(_publish)


class EnqueueNotificationService:
    """Grava a mensagem na mesma transação do fato que a originou.

    Chamar duas vezes o mesmo marco para o mesmo destinatário não duplica: a
    chave de deduplicação é única no banco e a segunda gravação é absorvida.
    """

    def execute(self, command: EnqueueNotificationCommand) -> EnqueueResult:
        # Uma leitura da central por lote: o orçamento de tentativas e a URL
        # base valem para todas as mensagens deste marco.
        config = EmailConfig.from_settings()
        scope = command.scope or _default_scope(command)
        channel = NotificationChannel.EMAIL
        created: list[Notification] = []
        without_address: list[int] = []
        duplicated = 0
        seen: set[int] = set()
        keys = {
            recipient.pk: _dedup_key(
                event=command.event,
                channel=channel,
                scope=scope,
                recipient_id=recipient.pk,
            )
            for recipient in command.recipients
        }
        # Varrer o mesmo marco de novo é o caso normal, não a exceção: uma
        # consulta resolve o lote antes de montar qualquer mensagem.
        already_queued = set(
            Notification.objects.filter(dedup_key__in=list(keys.values())).values_list(
                "dedup_key", flat=True
            )
        )
        for recipient in command.recipients:
            if recipient.pk in seen:
                continue
            seen.add(recipient.pk)
            if not recipient.is_active:
                continue
            key = keys[recipient.pk]
            if key in already_queued:
                duplicated += 1
                continue
            address = (recipient.email or "").strip()
            if not address:
                without_address.append(recipient.pk)
                logger.warning(
                    "notification.recipient_without_address",
                    extra={"recipient_id": recipient.pk, "event": command.event},
                )
                continue
            subject, body = render_message(
                command.event, message_context(command, recipient, config)
            )
            notification = Notification(
                event=command.event,
                channel=channel,
                dedup_key=key,
                process=command.process,
                task=command.task,
                sector=command.sector or (command.task.sector if command.task else None),
                recipient=recipient,
                recipient_email=address,
                subject=subject,
                body=body,
                context=command.context or {},
                max_attempts=config.max_attempts,
                next_attempt_at=timezone.now(),
                correlation_id=correlation_id.get() or "",
            )
            try:
                # Savepoint próprio: a colisão da chave não pode envenenar a
                # transação de domínio em curso. Duas varreduras simultâneas
                # chegam aqui e a segunda é absorvida — nunca duplicada.
                with transaction.atomic():
                    notification.full_clean()
                    notification.save()
            except (IntegrityError, ValidationError) as clash:
                if not Notification.objects.filter(dedup_key=key).exists():
                    raise clash
                duplicated += 1
                continue
            created.append(notification)
        for notification in created:
            _schedule_immediate_dispatch(notification.pk)
        return EnqueueResult(
            created=tuple(created),
            duplicated=duplicated,
            without_address=tuple(without_address),
        )


def _backoff(attempts: int) -> timedelta:
    index = min(max(attempts, 1), len(RETRY_BACKOFF_SECONDS)) - 1
    return timedelta(seconds=RETRY_BACKOFF_SECONDS[index])


class DispatchNotificationsService:
    """Envia o que está na fila, uma mensagem por vez.

    A entrega é ao menos uma vez: a linha é marcada como `ENVIANDO` e confirmada
    depois do SMTP aceitar. Se o processo morrer no meio, a mensagem volta para
    a fila e pode chegar duplicada — perder aviso seria pior.
    """

    def execute(self, command: DispatchNotificationsCommand) -> DispatchResult:
        config = EmailConfig.from_settings()
        if not config.enabled:
            # Desligar o envio não descarta mensagem: a fila espera em
            # `PENDENTE` e sai inteira quando alguém religar.
            logger.warning("notification.dispatch_disabled")
            return DispatchResult(sent=0, failed=0, rescheduled=0, requeued=0, disabled=True)
        limit = command.limit if command.limit is not None else config.batch_size
        # `is None` e não `or`: uma janela de zero é legítima e falsy.
        stale_after = (
            command.stale_after
            if command.stale_after is not None
            else timedelta(minutes=config.stale_minutes)
        )
        requeued = self._requeue_stale(timezone.now() - stale_after)
        # Sem `select_for_update` aqui: o Oracle não combina `FOR UPDATE` com
        # `FETCH FIRST`. A lista é uma sugestão e cada linha é revalidada sob
        # lock antes de consumir tentativa.
        candidates = list(
            Notification.objects.filter(
                status=NotificationStatus.PENDING,
                next_attempt_at__lte=timezone.now(),
            )
            .order_by("next_attempt_at", "pk")
            .values_list("pk", flat=True)[:limit]
        )
        sent = failed = rescheduled = 0
        for notification_pk in candidates:
            status = self._attempt(notification_pk, config)
            if status == NotificationStatus.SENT:
                sent += 1
            elif status == NotificationStatus.FAILED:
                failed += 1
            elif status is not None:
                rescheduled += 1
        return DispatchResult(
            sent=sent,
            failed=failed,
            rescheduled=rescheduled,
            requeued=requeued,
        )

    def execute_one(self, notification_pk: int) -> str | None:
        """Tenta uma única mensagem, para o despacho imediato do `on_commit`.

        Devolve o estado em que a mensagem ficou, ou `None` quando não havia o
        que fazer — envio desligado na central, mensagem já entregue, tomada por
        outro despachante ou ainda esperando o backoff. Rodar duas vezes a mesma
        mensagem é seguro pela mesma razão do lote: `_claim` revalida sob lock.
        """

        config = EmailConfig.from_settings()
        if not config.enabled:
            logger.warning("notification.dispatch_disabled")
            return None
        return self._attempt(notification_pk, config)

    def _attempt(self, notification_pk: int, config: EmailConfig) -> str | None:
        try:
            claimed = self._claim(notification_pk)
        except Notification.DoesNotExist:
            # A exclusão do processo leva a fila dele junto (ADR-056). Uma
            # tarefa agendada antes disso chega aqui sem alvo, e não ter o que
            # enviar é resultado legítimo, não erro.
            logger.info("notification.vanished", extra={"notification_pk": notification_pk})
            return None
        if claimed is None:
            return None
        notification, attempt_pk = claimed
        error = self._deliver(notification, config)
        return self._close(notification.pk, attempt_pk, error=error)

    @transaction.atomic
    def _requeue_stale(self, threshold: datetime) -> int:
        stale = list(
            Notification.objects.filter(
                status=NotificationStatus.SENDING,
                updated_at__lt=threshold,
            ).values_list("pk", flat=True)
        )
        requeued = 0
        for notification_pk in stale:
            notification = Notification.objects.select_for_update().get(pk=notification_pk)
            if notification.status != NotificationStatus.SENDING:
                continue
            now = timezone.now()
            open_attempts = NotificationAttempt.objects.select_for_update().filter(
                notification=notification,
                finished_at__isnull=True,
            )
            for attempt in open_attempts:
                attempt.finished_at = now
                attempt.succeeded = False
                attempt.error = STALE_ATTEMPT_ERROR
                attempt.save(update_fields=("finished_at", "succeeded", "error"))
            notification.last_error = STALE_ATTEMPT_ERROR
            if notification.attempts_exhausted:
                notification.status = NotificationStatus.FAILED
            else:
                notification.status = NotificationStatus.PENDING
                notification.next_attempt_at = now + _backoff(notification.attempts)
            notification.version += 1
            notification.save(
                update_fields=(
                    "status",
                    "last_error",
                    "next_attempt_at",
                    "version",
                    "updated_at",
                )
            )
            requeued += 1
        return requeued

    @transaction.atomic
    def _claim(self, notification_pk: int) -> tuple[Notification, int] | None:
        notification = Notification.objects.select_for_update().get(pk=notification_pk)
        if notification.status != NotificationStatus.PENDING:
            return None
        if notification.next_attempt_at > timezone.now():
            return None
        if notification.attempts_exhausted:
            notification.status = NotificationStatus.FAILED
            notification.version += 1
            notification.save(update_fields=("status", "version", "updated_at"))
            return None
        notification.attempts += 1
        notification.status = NotificationStatus.SENDING
        notification.version += 1
        notification.save(update_fields=("attempts", "status", "version", "updated_at"))
        # A numeração da tentativa é histórica e nunca se repete; `attempts` é o
        # orçamento da rodada corrente e volta a zero quando alguém reprocessa.
        last_number = NotificationAttempt.objects.filter(notification=notification).aggregate(
            last=Max("attempt_number")
        )["last"]
        attempt = NotificationAttempt(
            notification=notification,
            attempt_number=(last_number or 0) + 1,
        )
        attempt.full_clean()
        attempt.save()
        return notification, attempt.pk

    def _deliver(self, notification: Notification, config: EmailConfig) -> str:
        try:
            message = EmailMessage(
                subject=notification.subject,
                body=notification.body,
                from_email=config.default_from_email or None,
                to=[notification.recipient_email],
            )
            message.send(fail_silently=False)
        except Exception as failure:
            logger.warning(
                "notification.delivery_failed",
                extra={
                    "notification_uuid": str(notification.uuid),
                    "event": notification.event,
                    "attempt": notification.attempts,
                },
            )
            return f"{type(failure).__name__}: {failure}"[:MAX_ERROR_LENGTH]
        return ""

    @transaction.atomic
    def _close(self, notification_pk: int, attempt_pk: int, *, error: str) -> str:
        notification = Notification.objects.select_for_update().get(pk=notification_pk)
        attempt = NotificationAttempt.objects.select_for_update().get(pk=attempt_pk)
        now = timezone.now()
        attempt.finished_at = now
        attempt.succeeded = not error
        attempt.error = error
        attempt.save(update_fields=("finished_at", "succeeded", "error"))
        notification.last_error = error
        if not error:
            notification.status = NotificationStatus.SENT
            notification.sent_at = now
        elif notification.attempts_exhausted:
            notification.status = NotificationStatus.FAILED
        else:
            notification.status = NotificationStatus.PENDING
            notification.next_attempt_at = now + _backoff(notification.attempts)
        notification.version += 1
        notification.save(
            update_fields=(
                "status",
                "sent_at",
                "last_error",
                "next_attempt_at",
                "version",
                "updated_at",
            )
        )
        return str(notification.status)
