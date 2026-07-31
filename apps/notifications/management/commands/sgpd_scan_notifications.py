"""Varre prazos e enfileira lembretes, atrasos e escaladas (ADR-049).

Acionado pelo agendador do sistema operacional no DEV. Rodar de novo não
duplica aviso: cada marco tem chave própria por destinatário.
"""

from __future__ import annotations

from typing import Any

from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandParser

from apps.notifications.deadlines import ScanDeadlinesCommand, ScanDeadlinesService


class Command(BaseCommand):
    help = "Enfileira as notificações de prazo das tarefas e dos processos em aberto."

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument(
            "--dispatch",
            action="store_true",
            help="Despacha a fila logo após a varredura.",
        )

    def handle(self, *args: Any, **options: Any) -> None:
        result = ScanDeadlinesService().execute(ScanDeadlinesCommand())
        self.stdout.write(
            f"enfileiradas={result.queued} "
            f"tarefas={result.tasks_scanned} "
            f"processos={result.processes_scanned} "
            f"sem_destinatario={result.without_recipients}"
        )
        if options["dispatch"]:
            call_command("sgpd_dispatch_notifications", stdout=self.stdout)
