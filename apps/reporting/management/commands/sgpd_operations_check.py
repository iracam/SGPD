"""Sonda operacional para o agendador e para o runbook (R63, RNF-009).

Feita para rodar sem ninguém olhando: imprime o estado da fila, do
armazenamento e da retenção, e sai com código 1 quando a fila está parada.
Assim o próprio `crontab` — ou qualquer monitor externo — percebe o agendamento
morto sem depender de alguém abrir a tela.

Não envia, não reprocessa e não apaga nada.
"""

from __future__ import annotations

import sys
from typing import Any

from django.core.management.base import BaseCommand, CommandParser
from django.utils import timezone

from apps.reporting.operations import evaluate_operations


class Command(BaseCommand):
    help = "Verifica fila de notificações, armazenamento de evidências e retenção."

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument(
            "--quiet",
            action="store_true",
            help="Só imprime quando há problema; útil no agendador.",
        )

    def handle(self, *args: Any, **options: Any) -> None:
        status = evaluate_operations()
        queue = status.queue
        if not options["quiet"] or queue.is_stalled:
            counts = " ".join(
                f"{name.lower()}={total}" for name, total in sorted(queue.counts.items())
            )
            self.stdout.write(f"fila: {counts or 'vazia'}")
            self.stdout.write(
                "ultimo_envio: "
                + (
                    timezone.localtime(queue.last_sent_at).isoformat()
                    if queue.last_sent_at is not None
                    else "nunca"
                )
            )
            self.stdout.write(
                "pendente_mais_antiga: "
                + (
                    timezone.localtime(queue.oldest_pending_at).isoformat()
                    if queue.oldest_pending_at is not None
                    else "nenhuma"
                )
            )
            self.stdout.write(
                f"evidencias: {status.storage.evidence_count} bytes={status.storage.evidence_bytes}"
            )
            self.stdout.write(
                f"retencao: encerrados={status.retention.closed_processes} "
                f"alem_de_{status.retention.retention_years}_anos="
                f"{status.retention.beyond_retention}"
            )
            self.stdout.write(queue.verdict)
        if queue.is_stalled:
            # Saída diferente de zero é o que faz o agendador ou o monitor
            # externo reclamar: o veredito precisa ser acionável sem tela.
            sys.exit(1)
