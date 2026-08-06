"""Monitoramento operacional (RNF-007, RNF-009, risco R63).

A fila de notificações só anda quando o Beat dispara e o worker executa
(ADR-057). Se um dos dois parar, nada quebra e ninguém é avisado: as mensagens
simplesmente se acumulam em `PENDENTE` e o sistema segue respondendo
normalmente. É o risco R63, e este módulo é a sonda que o torna visível.

São dois sinais independentes, de propósito:

- **a fila**: mensagem pendente há mais tempo que a janela tolerada significa
  que ninguém a despachou. É a evidência mais direta, e não depende de nada
  além do próprio Oracle;
- **o batimento**: cada execução periódica grava o instante no cache
  compartilhado. Batimento velho denuncia o agendamento parado mesmo quando não
  há mensagem alguma esperando — o silêncio que a fila sozinha não distingue de
  tranquilidade.

Enquanto o agendamento vivia no sistema operacional, este módulo dizia que um
heartbeat seria só mais uma coisa para parar em silêncio, e o código de saída do
comando bastava: o systemd marcava a unidade como `failed`. Com o Beat não há
código de saída a observar, e a decisão se inverteu pelo motivo que a
desqualificava antes — quem lê o batimento é o processo web, que está vivo por
definição quando alguém abre a tela. Quem escreve pode morrer; quem lê, não.

Tudo aqui é leitura. Nenhuma sonda envia, reprocessa ou apaga o que quer que
seja.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta

from django.core.cache import cache
from django.db.models import Count, Max, Min, Q, Sum
from django.utils import timezone

from apps.evidence.models import Evidence
from apps.notifications.models import Notification, NotificationStatus
from apps.offboarding.models import OffboardingProcess, ProcessStatus

#: Minutos de tolerância antes de declarar a fila parada. A varredura do Beat
#: roda de dez em dez minutos; o triplo disso absorve execução atrasada sem
#: esconder agendamento morto.
STALE_QUEUE_MINUTES = 30

#: Chave do batimento no cache compartilhado. Prefixada pelo `KEY_PREFIX` dos
#: settings, porque o Redis é de outras aplicações também (ADR-057).
SCHEDULER_HEARTBEAT_KEY = "scheduler-heartbeat"

#: Quanto o batimento sobrevive sem ser renovado. Bem acima do intervalo da
#: sonda: expirar a chave rápido demais acusaria parada a cada atraso normal.
SCHEDULER_HEARTBEAT_TTL_SECONDS = 24 * 60 * 60

#: Minutos sem batimento antes de declarar o agendamento parado. A sonda roda a
#: cada trinta; o dobro tolera um atraso sem tolerar um serviço morto.
STALE_HEARTBEAT_MINUTES = 60

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
class SchedulerHealth:
    last_beat_at: datetime | None
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
    scheduler: SchedulerHealth
    storage: StorageUsage
    retention: RetentionStatus


def record_scheduler_beat(at: datetime | None = None) -> datetime:
    """Marca que o agendamento está vivo. Chamado pela tarefa periódica.

    Escrever é a única coisa que este módulo faz fora da leitura, e é sobre o
    próprio monitoramento — não toca domínio.
    """

    beat = at or timezone.now()
    cache.set(SCHEDULER_HEARTBEAT_KEY, beat.isoformat(), timeout=SCHEDULER_HEARTBEAT_TTL_SECONDS)
    return beat


def _scheduler_health(now: datetime) -> SchedulerHealth:
    raw = cache.get(SCHEDULER_HEARTBEAT_KEY)
    last_beat: datetime | None = None
    if isinstance(raw, str):
        try:
            last_beat = datetime.fromisoformat(raw)
        except ValueError:
            # Chave de outra origem ou de um formato antigo: tratada como
            # ausência, que já é o veredito conservador.
            last_beat = None
    if last_beat is None:
        return SchedulerHealth(
            last_beat_at=None,
            stale_minutes=STALE_HEARTBEAT_MINUTES,
            is_stalled=True,
            verdict=(
                "Nenhum batimento do agendamento registrado: o worker e o Beat podem "
                "nunca ter subido, ou o cache compartilhado foi reiniciado. "
                "Confira os serviços — RUNBOOK.md, seção 2."
            ),
        )
    is_stalled = last_beat < now - timedelta(minutes=STALE_HEARTBEAT_MINUTES)
    if is_stalled:
        verdict = (
            f"O agendamento não dá sinal há mais de {STALE_HEARTBEAT_MINUTES} minutos: "
            "o Beat ou o worker provavelmente pararam. "
            "Confira os serviços — RUNBOOK.md, seção 2."
        )
    else:
        verdict = "Agendamento ativo."
    return SchedulerHealth(
        last_beat_at=last_beat,
        stale_minutes=STALE_HEARTBEAT_MINUTES,
        is_stalled=is_stalled,
        verdict=verdict,
    )


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
        scheduler=_scheduler_health(now),
        storage=_storage_usage(),
        retention=_retention_status(now),
    )
