"""Tarefa periódica da sonda de operação (ADR-057, R63).

A sonda continua sendo leitura: ela conta e narra, não conserta. O que esta
tarefa acrescenta é o batimento — a prova de que o agendamento está vivo, lida
depois pelo processo web em `/fe/operacao`.
"""

from __future__ import annotations

import logging
from typing import Any

from celery import shared_task

from .operations import evaluate_operations, record_scheduler_beat

logger = logging.getLogger(__name__)


@shared_task(name="apps.reporting.operations_check")
def operations_check() -> dict[str, Any]:
    """Avalia o estado operacional e registra o batimento do agendamento.

    O batimento é gravado mesmo quando o veredito é ruim: ele responde "o
    agendamento está rodando?", não "está tudo bem?". Confundir as duas coisas
    faria uma fila parada esconder um Beat morto.
    """

    status = evaluate_operations()
    beat = record_scheduler_beat(status.checked_at)
    if status.queue.is_stalled:
        # Sem código de saída para o systemd observar, o log em nível de erro é
        # o que sobra para quem vigia de fora. A tela continua sendo a
        # testemunha principal.
        logger.error(
            "operations.queue_stalled",
            extra={
                "oldest_pending_at": (
                    status.queue.oldest_pending_at.isoformat()
                    if status.queue.oldest_pending_at is not None
                    else None
                ),
                "stale_minutes": status.queue.stale_minutes,
            },
        )
    return {
        "beat_at": beat.isoformat(),
        "queue_stalled": status.queue.is_stalled,
        "pending": status.queue.counts.get("PENDENTE", 0),
    }
