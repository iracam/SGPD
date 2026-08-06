"""Tarefas do worker para a fila de notificações (ADR-057).

Cada tarefa é uma casca fina sobre um service: a regra continua em
`services.py` e em `deadlines.py`, e trocar o transporte não deve significar
reescrever domínio. O payload nunca carrega dado pessoal — vai a chave
primária, e a tarefa relê do Oracle (`SECURITY.md` §13.1).
"""

from __future__ import annotations

import logging
import uuid

from celery import shared_task

from config.middleware import correlation_id

from .deadlines import ScanDeadlinesCommand, ScanDeadlinesService
from .services import DispatchNotificationsCommand, DispatchNotificationsService

logger = logging.getLogger(__name__)


def _new_correlation_id() -> str:
    """Um identificador por execução, para o log da tarefa ser rastreável.

    Fora da requisição não existe cabeçalho de onde herdar, e sem isto as linhas
    do worker sairiam com o correlation ID vazio.
    """

    value = uuid.uuid4().hex
    correlation_id.set(value)
    return value


@shared_task(name="apps.notifications.scan_deadlines")
def scan_deadlines() -> dict[str, int]:
    """Enfileira lembretes, atrasos e escaladas dos prazos vencendo.

    Idempotente por chave de deduplicação: rodar de novo muda a latência do
    aviso, nunca a quantidade.
    """

    _new_correlation_id()
    result = ScanDeadlinesService().execute(ScanDeadlinesCommand())
    return {
        "queued": result.queued,
        "tasks_scanned": result.tasks_scanned,
        "processes_scanned": result.processes_scanned,
        "without_recipients": result.without_recipients,
    }


@shared_task(name="apps.notifications.dispatch_queue")
def dispatch_queue(limit: int | None = None) -> dict[str, int]:
    """Despacha o lote pendente — a rede de segurança do envio imediato.

    Recolhe o que o `on_commit` não conseguiu agendar, o que falhou e voltou
    para a fila com backoff e o que ficou preso em `ENVIANDO`.
    """

    _new_correlation_id()
    result = DispatchNotificationsService().execute(DispatchNotificationsCommand(limit=limit))
    return {
        "sent": result.sent,
        "failed": result.failed,
        "rescheduled": result.rescheduled,
        "requeued": result.requeued,
    }


@shared_task(name="apps.notifications.dispatch_notification")
def dispatch_notification(notification_pk: int) -> str | None:
    """Tenta uma mensagem específica, logo depois do commit que a criou.

    É o que tira a latência do intervalo da varredura. Perder este disparo não
    perde a mensagem: ela continua `PENDENTE` no Oracle e o lote a alcança.
    """

    _new_correlation_id()
    return DispatchNotificationsService().execute_one(notification_pk)
