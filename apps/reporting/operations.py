"""Monitoramento operacional (RNF-007, RNF-009, risco R63).

A fila de notificações só anda quando o agendador do sistema operacional chama
os comandos (ADR-049). Se ele parar, nada quebra e ninguém é avisado: as
mensagens simplesmente se acumulam em `PENDENTE` e o sistema segue respondendo
normalmente. É o risco R63, e este módulo é a sonda que o torna visível.

O veredito é deliberadamente simples e explicável: mensagem pendente há mais
tempo que a janela tolerada significa que ninguém a despachou. Não há
heartbeat do agendador — inventar um seria mais uma coisa para parar em
silêncio; a própria fila é a evidência.

Tudo aqui é leitura. Nenhuma sonda envia, reprocessa ou apaga o que quer que
seja.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta

from django.db.models import Count, Max, Min, Q, Sum
from django.utils import timezone

from apps.evidence.models import Evidence
from apps.notifications.models import Notification, NotificationStatus
from apps.offboarding.models import OffboardingProcess, ProcessStatus

#: Minutos de tolerância antes de declarar a fila parada. A sugestão de
#: `crontab` em `ENVIRONMENT.md` §3 roda de dez em dez minutos; o triplo disso
#: absorve execução atrasada sem esconder agendador morto.
STALE_QUEUE_MINUTES = 30

#: Retenção operacional definida em `SECURITY.md` §14, contada do encerramento.
RETENTION_YEARS = 5


@dataclass(frozen=True, slots=True)
class QueueHealth:
    counts: dict[str, int]
    oldest_pending_at: datetime | None
    last_sent_at: datetime | None
    stale_minutes: int
    is_stalled: bool
    verdict: str


@dataclass(frozen=True, slots=True)
class StorageUsage:
    evidence_count: int
    evidence_bytes: int


@dataclass(frozen=True, slots=True)
class RetentionStatus:
    closed_processes: int
    beyond_retention: int
    oldest_closed_at: datetime | None
    retention_years: int


@dataclass(frozen=True, slots=True)
class OperationsStatus:
    checked_at: datetime
    queue: QueueHealth
    storage: StorageUsage
    retention: RetentionStatus


def _queue_health(now: datetime) -> QueueHealth:
    counts = {
        str(row["status"]): int(row["total"])
        for row in Notification.objects.values("status").annotate(total=Count("pk"))
    }
    aggregates = Notification.objects.aggregate(
        oldest_pending=Min("created_at", filter=Q(status=NotificationStatus.PENDING)),
        last_sent=Max("sent_at"),
    )
    oldest_pending = aggregates["oldest_pending"]
    limit = now - timedelta(minutes=STALE_QUEUE_MINUTES)
    is_stalled = oldest_pending is not None and oldest_pending < limit
    if is_stalled:
        # Texto puro: a mensagem é lida na tela e no log do agendador, e nenhum
        # dos dois interpreta marcação.
        verdict = (
            "Há mensagem pendente há mais de "
            f"{STALE_QUEUE_MINUTES} minutos: o agendamento provavelmente parou. "
            "Confira o agendamento do usuário da aplicação — RUNBOOK.md, seção 2."
        )
    elif oldest_pending is not None:
        verdict = "Fila com mensagem recente aguardando o próximo despacho."
    else:
        verdict = "Nenhuma mensagem aguardando envio."
    return QueueHealth(
        counts=counts,
        oldest_pending_at=oldest_pending,
        last_sent_at=aggregates["last_sent"],
        stale_minutes=STALE_QUEUE_MINUTES,
        is_stalled=is_stalled,
        verdict=verdict,
    )


def _storage_usage() -> StorageUsage:
    aggregates = Evidence.objects.filter(is_active=True).aggregate(
        total=Count("pk"),
        bytes=Sum("size_bytes"),
    )
    return StorageUsage(
        evidence_count=int(aggregates["total"] or 0),
        evidence_bytes=int(aggregates["bytes"] or 0),
    )


def _retention_status(now: datetime) -> RetentionStatus:
    """Quanto já passou da retenção — o expurgo continua manual e autorizado.

    O encerramento formal da Fase 8 é o marco da contagem (`SECURITY.md` §14).
    A sonda conta; apagar evidência é ato humano, e nenhuma rotina o faz.
    """

    closed = OffboardingProcess.objects.filter(
        status=ProcessStatus.CLOSED,
        closed_at__isnull=False,
    )
    limit = now - timedelta(days=365 * RETENTION_YEARS)
    return RetentionStatus(
        closed_processes=closed.count(),
        beyond_retention=closed.filter(closed_at__lt=limit).count(),
        oldest_closed_at=closed.aggregate(oldest=Min("closed_at"))["oldest"],
        retention_years=RETENTION_YEARS,
    )


def evaluate_operations() -> OperationsStatus:
    now = timezone.now()
    return OperationsStatus(
        checked_at=now,
        queue=_queue_health(now),
        storage=_storage_usage(),
        retention=_retention_status(now),
    )
