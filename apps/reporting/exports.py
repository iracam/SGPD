"""Exportações CSV dos relatórios (RF-036).

Três conjuntos, todos no recorte de período e na visibilidade de
`processes_for_actor`: processos, tarefas de setor e pendências com o eixo de
valor. O ato de exportar é gravado em `SGPD_REPORT_EXPORT` **antes** de os
bytes saírem — download interrompido continua sendo acesso ao dado
(`SECURITY.md` §6).

O que não vai no arquivo, por decisão explícita: CPF (nem mascarado), motivo do
desligamento, justificativa da pretensão e parecer da decisão. São texto de
juízo ou dado restrito (`SECURITY.md` §5); a conferência precisa do número, do
estado e de quem decidiu, e isso o arquivo carrega. Quem precisa do texto o lê
no sistema, onde o acesso é auditado linha a linha.

O arquivo é para leitura humana em planilha pt-BR: separador `;`, BOM UTF-8,
decimal com vírgula e data em `dd/mm/aaaa`. Sem o BOM o Excel abre acentuação
quebrada, e é a primeira coisa que alguém relata.

Sem `annotate(Count(...))` sobre o processo: a anotação leva todas as colunas
projetadas para o `GROUP BY`, e `REASON`/`NOTES` são NCLOB — o Oracle recusa
agrupar por LOB (ORA-00932). As contagens vêm de consultas próprias, agrupadas
pela chave, e se juntam em Python.
"""

from __future__ import annotations

import csv
import io
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from typing import Any

from django.db.models import Count, Q
from django.utils import timezone

from apps.accounts.models import User
from apps.offboarding.models import (
    OPEN_TASK_STATUSES,
    ProcessSectorTask,
    ProcessStatus,
    SectorTaskStatus,
)
from apps.offboarding.services import processes_for_actor
from apps.pending_items.models import (
    BlockingLevel,
    PendingCategory,
    PendingItem,
    PendingStatus,
)
from config.middleware import correlation_id

from .models import ExportDataset, ReportExport
from .reports import Period

#: Teto de linhas de uma exportação. Acima disso a resposta é uma recusa
#: legível pedindo recorte menor: devolver arquivo truncado sem avisar seria
#: pior — quem confere somaria o que não é o total.
EXPORT_ROWS = 5000


class ExportTooLarge(Exception):
    """Recorte grande demais para um arquivo só."""


@dataclass(frozen=True, slots=True)
class ExportFile:
    filename: str
    content: bytes
    row_count: int


def _date(value: date | None) -> str:
    return value.strftime("%d/%m/%Y") if value else ""


def _moment(value: datetime | None) -> str:
    if value is None:
        return ""
    return timezone.localtime(value).strftime("%d/%m/%Y %H:%M")


def _number(value: Decimal | float | None) -> str:
    if value is None:
        return ""
    return f"{value:.2f}".replace(".", ",")


def _hours_between(start: datetime | None, end: datetime | None) -> str:
    if start is None or end is None:
        return ""
    return _number((end - start).total_seconds() / 3600)


def _label(choices: Any, value: str) -> str:
    return str(dict(choices).get(value, value))


def _process_rows(actor: User, period: Period) -> tuple[list[str], list[list[str]]]:
    """Uma linha por processo aberto no período."""

    processes = (
        processes_for_actor(actor)
        .filter(opened_at__gte=period.start_at, opened_at__lte=period.end_at)
        .select_related("employee_snapshot")
        .order_by("-opened_at", "-pk")
    )
    identifiers = list(processes.values_list("pk", flat=True))
    tasks = {
        int(row["process_id"]): (int(row["total"]), int(row["open_total"]))
        for row in ProcessSectorTask.objects.filter(process_id__in=identifiers)
        .values("process_id")
        .annotate(
            total=Count("pk"),
            open_total=Count("pk", filter=Q(status__in=OPEN_TASK_STATUSES)),
        )
    }
    pendings = {
        int(row["process_id"]): int(row["total"])
        for row in PendingItem.objects.filter(process_id__in=identifiers)
        .values("process_id")
        .annotate(total=Count("pk"))
    }
    header = [
        "Referência",
        "UUID",
        "Estado formal",
        "Empresa",
        "Filial",
        "Nome da filial",
        "Matrícula",
        "Colaborador",
        "Prioridade",
        "Desligamento previsto",
        "Data limite",
        "Aberto em",
        "Iniciado em",
        "Liberado em",
        "Rescisão processada em",
        "Encerrado em",
        "Cancelado em",
        "Tarefas",
        "Tarefas em aberto",
        "Pendências",
    ]
    rows = []
    for process in processes:
        snapshot = process.employee_snapshot
        total_tasks, open_tasks = tasks.get(process.pk, (0, 0))
        rows.append(
            [
                str(process.uuid)[:8],
                str(process.uuid),
                _label(ProcessStatus.choices, process.status),
                str(process.company_code),
                str(process.branch_code),
                snapshot.branch_legal_name,
                str(process.employee_registration),
                snapshot.employee_name,
                process.priority,
                _date(process.planned_termination_date),
                _date(process.due_date),
                _moment(process.opened_at),
                _moment(process.started_at),
                _moment(process.released_at),
                _date(process.termination_processed_on),
                _moment(process.closed_at),
                _moment(process.cancelled_at),
                str(total_tasks),
                str(open_tasks),
                str(pendings.get(process.pk, 0)),
            ]
        )
    return header, rows


def _task_rows(actor: User, period: Period) -> tuple[list[str], list[list[str]]]:
    """Uma linha por tarefa criada no período, com a conclusão quando houver."""

    tasks = (
        ProcessSectorTask.objects.filter(
            process_id__in=processes_for_actor(actor).values("pk"),
            started_at__gte=period.start_at,
            started_at__lte=period.end_at,
        )
        .select_related("process", "process__employee_snapshot", "completed_by")
        .order_by("-started_at", "-pk")
    )
    header = [
        "Processo",
        "Colaborador",
        "Empresa",
        "Filial",
        "Setor",
        "Template",
        "Versão",
        "Situação",
        "Obrigatória",
        "Bloqueia",
        "Prazo",
        "Criada em",
        "Concluída em",
        "Horas até concluir",
        "Concluída por",
    ]
    rows = []
    for task in tasks:
        completed_at = task.completed_at
        rows.append(
            [
                str(task.process.uuid)[:8],
                task.process.employee_snapshot.employee_name,
                str(task.process.company_code),
                str(task.process.branch_code),
                task.sector_name_snapshot,
                task.template_code_snapshot,
                str(task.template_version_snapshot),
                _label(SectorTaskStatus.choices, task.status),
                "Sim" if task.is_required else "Não",
                "Sim" if task.blocks_process else "Não",
                _moment(task.due_at),
                _moment(task.started_at),
                _moment(completed_at),
                _hours_between(task.started_at, completed_at),
                task.completed_by.username if task.completed_by is not None else "",
            ]
        )
    return header, rows


def _pending_rows(actor: User, period: Period) -> tuple[list[str], list[list[str]]]:
    """Uma linha por pendência identificada no período, com o eixo de valor."""

    pendings = (
        PendingItem.objects.filter(
            process_id__in=processes_for_actor(actor).values("pk"),
            identified_at__gte=period.start_at,
            identified_at__lte=period.end_at,
        )
        .select_related(
            "process",
            "process__employee_snapshot",
            "task",
            "amount",
            "amount__informed_by",
            "amount__approved_by",
        )
        .prefetch_related("decisions")
        .order_by("-identified_at", "-pk")
    )
    header = [
        "Processo",
        "Colaborador",
        "Setor",
        "Categoria",
        "Título",
        "Bloqueio",
        "Situação",
        "Identificada em",
        "Moeda",
        "Informado",
        "Apurado",
        "Contestado",
        "Aprovado",
        "Processado",
        "Informado por",
        "Decidido por",
        "Segregação rompida",
    ]
    rows = []
    for pending in pendings:
        amount = getattr(pending, "amount", None)
        decisions = list(pending.decisions.all())
        last = decisions[-1] if decisions else None
        rows.append(
            [
                str(pending.process.uuid)[:8],
                pending.process.employee_snapshot.employee_name,
                pending.task.sector_name_snapshot if pending.task_id else "",
                _label(PendingCategory.choices, pending.category),
                pending.title,
                _label(BlockingLevel.choices, pending.blocking_level),
                _label(PendingStatus.choices, pending.status),
                _moment(pending.identified_at),
                amount.currency if amount else "",
                _number(amount.amount_informed) if amount else "",
                _number(amount.amount_assessed) if amount else "",
                _number(amount.amount_contested) if amount else "",
                _number(amount.amount_approved) if amount else "",
                _number(amount.amount_processed) if amount else "",
                amount.informed_by.username if amount else "",
                last.decided_by.username if last is not None else "",
                "Sim" if any(row.segregation_override for row in decisions) else "Não",
            ]
        )
    return header, rows


_BUILDERS = {
    ExportDataset.PROCESSES: _process_rows,
    ExportDataset.TASKS: _task_rows,
    ExportDataset.PENDING_ITEMS: _pending_rows,
}


def build_export(actor: User, *, dataset: str, period: Period) -> ExportFile:
    """Monta o arquivo e grava a trilha do ato, nesta ordem.

    A trilha vem antes do envio de propósito: quem pediu o dado pediu, ainda
    que a rede caia no meio do download.
    """

    header, rows = _BUILDERS[ExportDataset(dataset)](actor, period)
    if len(rows) > EXPORT_ROWS:
        raise ExportTooLarge(
            f"O recorte gera {len(rows)} linhas e o limite por arquivo é {EXPORT_ROWS}. "
            "Reduza o período."
        )
    buffer = io.StringIO()
    writer = csv.writer(buffer, delimiter=";", quoting=csv.QUOTE_MINIMAL)
    writer.writerow(header)
    writer.writerows(rows)
    ReportExport.objects.create(
        dataset=dataset,
        actor=actor,
        period_start=period.start,
        period_end=period.end,
        row_count=len(rows),
        correlation_id=correlation_id.get(),
    )
    return ExportFile(
        filename=f"sgpd-{dataset.lower()}-{period.start:%Y%m%d}-{period.end:%Y%m%d}.csv",
        # BOM explícito: sem ele o Excel pt-BR abre a acentuação quebrada.
        content=buffer.getvalue().encode("utf-8-sig"),
        row_count=len(rows),
    )
