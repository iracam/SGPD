"""Indicadores de operação do painel (RF-034, RF-035).

Leitura pura: nada aqui grava, enfileira ou decide. Cada número é derivado do
que está no banco no instante da consulta, como a situação calculada da
ADR-051 — o painel não guarda contador próprio, porque contador guardado
envelhece e passa a mentir.

A visibilidade não é reinventada: o bloco de coordenação usa
`processes_for_actor` e o bloco de setor usa `sector_tasks_for_actor`, as
mesmas funções que a listagem de processos e a de tarefas já usam. Quem não
enxerga o processo não pode enxergá-lo somado.

Armadilhas do Oracle observadas aqui, todas já cobradas em fases anteriores:
`SGPD_OFFBOARDING_PROCESS` carrega `REASON` e `NOTES` como NCLOB, então
nenhuma consulta pode pedir `DISTINCT` sobre o processo (ORA-00932) — a
duplicidade do join morre em subconsulta antes de projetar coluna; e os
agrupamentos nunca recaem sobre um queryset anotado com `Exists`, para que a
anotação não vá parar no `GROUP BY`.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Any

from django.db.models import Count, QuerySet, Sum
from django.utils import timezone

from apps.accounts.authorization import active_assignments, has_global_authority
from apps.accounts.models import PEOPLE_DEPARTMENT_ROLE_CODE, User
from apps.notifications.config import EmailConfig
from apps.offboarding.models import (
    OPEN_TASK_STATUSES,
    OffboardingProcess,
    ProcessSectorTask,
    ProcessStatus,
)
from apps.offboarding.services import (
    completed_processes_for_actor,
    open_processes_for_actor,
    processes_for_actor,
    sector_tasks_for_actor,
)
from apps.pending_items.models import (
    DECIDED_STATUSES,
    PendingCategory,
    PendingItem,
    PendingStatus,
    unresolved_blocking_q,
)

#: Situações em que a pendência já não espera trabalho de ninguém. A
#: regularização entra aqui porque é o que libera a tarefa bloqueada
#: (`BLOCKING_RELEASE_STATUSES`); as decididas entram pela mesma régua do eixo
#: de valor.
RESOLVED_PENDING_STATUSES = frozenset({PendingStatus.REGULARIZED}) | DECIDED_STATUSES

#: Quantas linhas cada recorte do painel devolve. O painel é de operação: lista
#: longa vira relatório, e relatório é a fatia seguinte.
TOP_ROWS = 5


@dataclass(frozen=True, slots=True)
class KeyedCount:
    """Um recorte contado, com o rótulo já legível (ADR-047)."""

    key: str
    label: str
    total: int


@dataclass(frozen=True, slots=True)
class CurrencyTotal:
    currency: str
    informed: Decimal


@dataclass(frozen=True, slots=True)
class CriticalProcess:
    """Processo que já perdeu prazo, na visão de quem o vê."""

    uuid: str
    employee_name: str
    company_code: int
    branch_code: int
    due_date: date
    overdue_tasks: int


@dataclass(frozen=True, slots=True)
class CoordinationIndicators:
    """Painel do `DP` (RF-034): o que está em aberto e o que já estourou."""

    open_processes: int
    completed_processes: int
    draft_processes: int
    cancelled_processes: int
    by_status: tuple[KeyedCount, ...]
    overdue_processes: int
    due_soon_processes: int
    open_pending_items: int
    blocking_pending_items: int
    delayed_sectors: tuple[KeyedCount, ...]
    amounts_awaiting_decision: int
    amount_totals: tuple[CurrencyTotal, ...]
    critical_processes: tuple[CriticalProcess, ...]


@dataclass(frozen=True, slots=True)
class SectorIndicators:
    """Painel do setor (RF-035): o que o responsável ainda deve entregar."""

    pending_tasks: int
    overdue_tasks: int
    due_soon_tasks: int
    by_company: tuple[KeyedCount, ...]
    by_branch: tuple[KeyedCount, ...]
    critical_processes: tuple[CriticalProcess, ...]


@dataclass(frozen=True, slots=True)
class DashboardIndicators:
    generated_at: datetime
    coordination: CoordinationIndicators | None
    sector: SectorIndicators | None


def _coordinates_processes(actor: User) -> bool:
    """Mesma régua de `_require_process_coordinator`, sem levantar exceção."""

    return (
        has_global_authority(actor)
        or active_assignments(actor).filter(role__code=PEOPLE_DEPARTMENT_ROLE_CODE).exists()
    )


def _process_due_horizon(config: EmailConfig, now: datetime) -> date:
    """Última data limite que ainda conta como “próxima do prazo”.

    A janela é a mesma que dispara `PROCESSO_PROXIMO_LIMITE` na varredura
    (`WORKFLOWS.md` §7): o painel e o e-mail precisam concordar sobre o que é
    urgente, senão o `DP` recebe aviso de um processo que o painel diz estar
    tranquilo.
    """

    return (now + timedelta(hours=config.process_due_soon_hours)).date()


def _status_label(status: str) -> str:
    return dict(ProcessStatus.choices).get(status, status)


def _visible_pending_items(processes: QuerySet[OffboardingProcess]) -> QuerySet[PendingItem]:
    return PendingItem.objects.filter(process_id__in=processes.values("pk"))


def _coordination_indicators(actor: User, now: datetime) -> CoordinationIndicators:
    config = EmailConfig.from_settings()
    today = timezone.localdate(now)
    processes = processes_for_actor(actor)
    open_processes = open_processes_for_actor(actor)

    by_status = tuple(
        KeyedCount(
            key=str(row["status"]),
            label=_status_label(str(row["status"])),
            total=int(row["total"]),
        )
        for row in processes.values("status").annotate(total=Count("pk")).order_by("status")
    )
    counts = {row.key: row.total for row in by_status}

    pending_items = _visible_pending_items(processes)
    amounts = pending_items.filter(
        category=PendingCategory.VALUE,
        amount__isnull=False,
    ).exclude(status__in=DECIDED_STATUSES)

    delayed = (
        ProcessSectorTask.objects.filter(
            process_id__in=processes.values("pk"),
            status__in=OPEN_TASK_STATUSES,
            due_at__lt=now,
        )
        .values("sector_id", "sector_name_snapshot")
        .annotate(total=Count("pk"))
        .order_by("-total", "sector_name_snapshot")[:TOP_ROWS]
    )

    return CoordinationIndicators(
        open_processes=open_processes.count(),
        completed_processes=completed_processes_for_actor(actor).count(),
        draft_processes=counts.get(ProcessStatus.DRAFT.value, 0),
        cancelled_processes=counts.get(ProcessStatus.CANCELLED.value, 0),
        by_status=by_status,
        overdue_processes=open_processes.filter(due_date__lt=today).count(),
        due_soon_processes=open_processes.filter(
            due_date__gte=today,
            due_date__lte=_process_due_horizon(config, now),
        ).count(),
        open_pending_items=pending_items.exclude(status__in=RESOLVED_PENDING_STATUSES).count(),
        blocking_pending_items=pending_items.filter(unresolved_blocking_q()).count(),
        delayed_sectors=tuple(
            KeyedCount(
                key=str(row["sector_id"]),
                label=str(row["sector_name_snapshot"]),
                total=int(row["total"]),
            )
            for row in delayed
        ),
        amounts_awaiting_decision=amounts.count(),
        amount_totals=tuple(
            CurrencyTotal(
                currency=str(row["amount__currency"]),
                informed=row["informed"] or Decimal("0.00"),
            )
            for row in amounts.values("amount__currency")
            .annotate(informed=Sum("amount__amount_informed"))
            .order_by("amount__currency")
        ),
        critical_processes=_critical_processes(processes.values("pk"), now),
    )


def _critical_processes(
    process_ids: QuerySet[Any],
    now: datetime,
) -> tuple[CriticalProcess, ...]:
    """Processos iniciados com tarefa vencida, os mais atrasados primeiro.

    A contagem vem das tarefas e o cabeçalho vem do processo: sem a subconsulta
    de `pk`, o join com a tarefa duplicaria o processo e o Oracle recusaria o
    `DISTINCT` sobre `REASON`/`NOTES`.
    """

    overdue = (
        ProcessSectorTask.objects.filter(
            process_id__in=process_ids,
            process__status=ProcessStatus.STARTED,
            status__in=OPEN_TASK_STATUSES,
            due_at__lt=now,
        )
        .values("process_id")
        .annotate(total=Count("pk"))
        .order_by("-total", "process_id")[:TOP_ROWS]
    )
    rows = {int(row["process_id"]): int(row["total"]) for row in overdue}
    if not rows:
        return ()
    processes = OffboardingProcess.objects.filter(pk__in=rows).select_related("employee_snapshot")
    return tuple(
        sorted(
            (
                CriticalProcess(
                    uuid=str(process.uuid),
                    employee_name=process.employee_snapshot.employee_name,
                    company_code=process.company_code,
                    branch_code=process.branch_code,
                    due_date=process.due_date,
                    overdue_tasks=rows[process.pk],
                )
                for process in processes
            ),
            key=lambda row: (-row.overdue_tasks, row.due_date),
        )
    )


def _sector_indicators(actor: User, now: datetime) -> SectorIndicators:
    config = EmailConfig.from_settings()
    # A visibilidade traz `Exists` anotados; agrupar sobre ela levaria a
    # anotação para o `GROUP BY`. A subconsulta de `pk` isola o recorte.
    visible = sector_tasks_for_actor(actor).values("pk")
    tasks = ProcessSectorTask.objects.filter(pk__in=visible)
    open_tasks = tasks.filter(status__in=OPEN_TASK_STATUSES)
    due_soon_limit = now + timedelta(hours=config.task_due_soon_hours)

    by_company = (
        open_tasks.values("process__company_code")
        .annotate(total=Count("pk"))
        .order_by("-total", "process__company_code")[:TOP_ROWS]
    )
    by_branch = (
        open_tasks.values(
            "process__company_code",
            "process__branch_code",
            "process__employee_snapshot__branch_legal_name",
        )
        .annotate(total=Count("pk"))
        .order_by("-total", "process__company_code", "process__branch_code")[:TOP_ROWS]
    )

    return SectorIndicators(
        pending_tasks=open_tasks.count(),
        overdue_tasks=open_tasks.filter(due_at__lt=now).count(),
        due_soon_tasks=open_tasks.filter(due_at__gte=now, due_at__lte=due_soon_limit).count(),
        by_company=tuple(
            KeyedCount(
                key=str(row["process__company_code"]),
                label=f"Empresa {row['process__company_code']}",
                total=int(row["total"]),
            )
            for row in by_company
        ),
        by_branch=tuple(
            KeyedCount(
                key=f"{row['process__company_code']}:{row['process__branch_code']}",
                # O nome da filial é o do snapshot do colaborador: é o que a
                # abertura congelou e o que as demais telas mostram.
                label=str(row["process__employee_snapshot__branch_legal_name"])
                or f"Filial {row['process__branch_code']}",
                total=int(row["total"]),
            )
            for row in by_branch
        ),
        critical_processes=_critical_processes(
            OffboardingProcess.objects.filter(
                pk__in=tasks.values("process_id"),
            ).values("pk"),
            now,
        ),
    )


def evaluate_dashboard(actor: User) -> DashboardIndicators:
    """Indicadores do ator: coordenação, setor, ou os dois.

    Cada bloco aparece por capacidade, não por papel declarado: o de
    coordenação exige `DP` vigente ou autoridade global; o de setor exige
    enxergar ao menos uma tarefa. Quem acumula os dois vê os dois — e o
    SuperAdmin, por definição, sempre vê ambos.
    """

    now = timezone.now()
    coordination = _coordination_indicators(actor, now) if _coordinates_processes(actor) else None
    tasks_visible = sector_tasks_for_actor(actor).exists()
    return DashboardIndicators(
        generated_at=now,
        coordination=coordination,
        sector=_sector_indicators(actor, now) if tasks_visible else None,
    )
