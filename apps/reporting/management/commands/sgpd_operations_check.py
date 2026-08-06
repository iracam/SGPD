"""Sonda operacional para o plantão e para o runbook (R63, RNF-009).

Em operação normal quem roda a sonda é o Beat (ADR-057), e o veredito aparece
em `/fe/operacao`. Este comando é a mesma leitura à mão: imprime o estado da
fila, do agendamento, do armazenamento e da retenção, e sai com código 1 quando
a fila está parada — é o que permite a um monitor externo perceber o problema
sem abrir a tela.

Não envia, não reprocessa, não apaga e **não registra batimento**: quem passa
por aqui é gente conferindo, não o agendamento provando que está vivo.

O modo silencioso continua governado só pela fila. O batimento é impresso como
contexto, mas não faz o comando falar: logo depois de um boot ele está ausente
por definição, e uma sonda que reclama sempre deixa de ser lida. Quem cobra o
agendamento parado com a fila vazia é a tela de operação.
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
        scheduler = status.scheduler
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
                "ultimo_batimento: "
                + (
                    timezone.localtime(scheduler.last_beat_at).isoformat()
                    if scheduler.last_beat_at is not None
                    else "nunca"
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
            self.stdout.write(scheduler.verdict)
        if queue.is_stalled:
            # Saída diferente de zero é o que faz o monitor externo reclamar: o
            # veredito precisa ser acionável sem tela. Só a fila parada
            # qualifica — batimento ausente é o esperado em quem acabou de
            # subir, e falhar por isso ensinaria a ignorar a saída.
            sys.exit(1)
