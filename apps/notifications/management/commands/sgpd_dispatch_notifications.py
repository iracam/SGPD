"""Despacha a fila de notificações (ADR-049).

Acionado pelo agendador do sistema operacional no DEV. Rodar duas vezes em
paralelo é seguro: cada mensagem é tomada sob lock e revalidada antes de
consumir tentativa.
"""

from __future__ import annotations

from datetime import timedelta
from typing import Any

from django.core.management.base import BaseCommand, CommandParser

from apps.notifications.services import (
    DispatchNotificationsCommand,
    DispatchNotificationsService,
)


class Command(BaseCommand):
    help = "Envia as notificações pendentes e reabre as presas em envio."

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument(
            "--limit",
            type=int,
            default=None,
            help="Quantas mensagens tentar nesta execução.",
        )
        parser.add_argument(
            "--stale-minutes",
            type=int,
            default=None,
            help="Minutos após os quais uma mensagem em envio volta para a fila.",
        )

    def handle(self, *args: Any, **options: Any) -> None:
        stale_minutes: int | None = options["stale_minutes"]
        result = DispatchNotificationsService().execute(
            DispatchNotificationsCommand(
                limit=options["limit"],
                stale_after=(
                    timedelta(minutes=stale_minutes) if stale_minutes is not None else None
                ),
            )
        )
        self.stdout.write(
            f"enviadas={result.sent} "
            f"falhas={result.failed} "
            f"reagendadas={result.rescheduled} "
            f"reabertas={result.requeued}"
        )
