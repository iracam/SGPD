"""Relatórios mínimos do RF-036.

Leitura pura, como os indicadores: nada aqui grava nem decide. A visibilidade é
a de `processes_for_actor` — conferência do escopo do `DP`, a mesma régua da
consolidação de valores e do painel de notificações.

Duas naturezas convivem no mesmo recorte de período e o payload diz qual é qual:

- **fato ocorrido** — o período filtra a data do fato (processo encerrado,
  tarefa concluída, pendência identificada, valor informado, processo aberto ou
  liberado);
- **fotografia de agora** — atraso não tem data própria; processo vencido e
  setor atrasado são o estado deste instante, e o período não os alcança.

Média de duração é calculada em Python, de propósito. O Oracle guarda a
subtração de dois `TIMESTAMP` como `INTERVAL DAY TO SECOND`, e `AVG` sobre
intervalo é `ORA-00932`; o SQLite dos testes aceitaria de bom grado, e a suíte
passaria enquanto o relatório quebraria na primeira execução real — foi assim
com o `DISTINCT` sobre LOB na Fase 7. A consulta projeta só os dois instantes,
sem tocar em `REASON`/`NOTES`.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from decimal import Decimal
from statistics import median

from django.db.models import Count, Q, Sum
from django.db.models.functions import TruncMonth
from django.utils import timezone

from apps.accounts.models import User
from apps.offboarding.models import (
    OPEN_TASK_STATUSES,
    ProcessSectorTask,
    SectorTaskStatus,
)
from apps.offboarding.services import (
    completed_processes_for_actor,
    open_processes_for_actor,
    processes_for_actor,
)
from apps.pending_items.models import (
    DECIDED_STATUSES,
    PendingCategory,
    PendingItem,
    unresolved_blocking_q,
)

#: Janela padrão quando ninguém informa período.
DEFAULT_PERIOD_DAYS = 90

#: Teto de linhas por relatório. Conferência é leitura humana; o que passa
#: disso é exportação, não tela.
REPORT_ROWS = 20

MONTHS_PT = (
    "jan",
    "fev",
    "mar",
    "abr",
    "mai",
    "jun",
    "jul",
    "ago",
    "set",
    "out",
    "nov",
    "dez",
)


@dataclass(frozen=True, slots=True)
class Period:
    start: date
    end: date

    @property
    def start_at(self) -> datetime:
        return timezone.make_aware(datetime.combine(self.start, time.min))

    @property
    def end_at(self) -> datetime:
        return timezone.make_aware(datetime.combine(self.end, time.max))

    @classmethod
    def resolve(cls, start: date | None, end: date | None) -> Period:
        today = timezone.localdate()
        resolved_end = end or today
        return cls(
            start=start or resolved_end - timedelta(days=DEFAULT_PERIOD_DAYS),
            end=resolved_end,
        )


@dataclass(frozen=True, slots=True)
class DurationRow:
    key: str
    label: str
    total: int
    average_hours: float | None


@dataclass(frozen=True, slots=True)
class CountRow:
    key: str
    label: str
    total: int
    detail: int = 0


@dataclass(frozen=True, slots=True)
class AmountRow:
    currency: str
    informed: Decimal
    approved: Decimal
    undecided: int


@dataclass(frozen=True, slots=True)
class OverdueRow:
    process_uuid: str
    employee_name: str
    company_code: int
    branch_code: int
    due_date: date
    days_overdue: int
    open_tasks: int


@dataclass(frozen=True, slots=True)
class CycleTime:
    """Tempo médio do processo, do início à conclusão."""

    processes: int
    average_days: float | None
    median_days: float | None


@dataclass(frozen=True, slots=True)
class Reports:
    period: Period
    process_cycle_time: CycleTime
    sector_cycle_time: tuple[DurationRow, ...]
    pending_by_category: tuple[CountRow, ...]
    processes_by_company: tuple[CountRow, ...]
    overdue_processes: tuple[OverdueRow, ...]
    overdue_process_count: int
    sector_delays: tuple[DurationRow, ...]
    amounts: tuple[AmountRow, ...]
    released_by_month: tuple[CountRow, ...]
    released_total: int


def _hours(delta: timedelta) -> float:
    return round(delta.total_seconds() / 3600, 1)


def _days(delta: timedelta) -> float:
    return round(delta.total_seconds() / 86400, 1)


def _month_label(moment: datetime | date) -> str:
    return f"{MONTHS_PT[moment.month - 1]}/{moment.year}"


def _process_cycle_time(actor: User, period: Period) -> CycleTime:
    """Do início do processo à sua conclusão, na mesma definição do hub.

    Conclusão é o encerramento formal quando existe; sem ele, a última tarefa
    concluída — é o que `completed_processes_for_actor` já considera concluído.
    """

    rows = (
        completed_processes_for_actor(actor)
        .filter(
            started_at__isnull=False,
        )
        .filter(
            Q(closed_at__gte=period.start_at, closed_at__lte=period.end_at)
            | Q(
                closed_at__isnull=True,
                completion_at__gte=period.start_at,
                completion_at__lte=period.end_at,
            )
        )
    )
    # `completion_at` é anotação de `completed_processes_for_actor`; o plugin do
    # mypy só enxerga campos declarados no model e não atravessa a função.
    projection = rows.values_list(
        "started_at",
        "closed_at",
        "completion_at",  # type: ignore[misc]
    )
    durations = [
        (closed_at or completion_at) - started_at
        for started_at, closed_at, completion_at in projection
        if started_at is not None and (closed_at or completion_at) is not None
    ]
    if not durations:
        return CycleTime(processes=0, average_days=None, median_days=None)
    total = sum(durations, timedelta())
    return CycleTime(
        processes=len(durations),
        average_days=_days(total / len(durations)),
        median_days=_days(median(durations)),
    )


def _sector_cycle_time(actor: User, period: Period) -> tuple[DurationRow, ...]:
    rows = ProcessSectorTask.objects.filter(
        process_id__in=processes_for_actor(actor).values("pk"),
        status=SectorTaskStatus.COMPLETED,
        completed_at__gte=period.start_at,
        completed_at__lte=period.end_at,
    ).values_list("sector_id", "sector_name_snapshot", "started_at", "completed_at")

    buckets: dict[tuple[int, str], list[timedelta]] = {}
    for sector_id, sector_name, started_at, completed_at in rows:
        if completed_at is None:
            continue
        buckets.setdefault((sector_id, sector_name), []).append(completed_at - started_at)
    ordered = sorted(
        buckets.items(),
        key=lambda item: (-sum(item[1], timedelta()) / len(item[1]), item[0][1]),
    )
    return tuple(
        DurationRow(
            key=str(sector_id),
            label=sector_name,
            total=len(durations),
            average_hours=_hours(sum(durations, timedelta()) / len(durations)),
        )
        for (sector_id, sector_name), durations in ordered[:REPORT_ROWS]
    )


def _pending_by_category(actor: User, period: Period) -> tuple[CountRow, ...]:
    labels = dict(PendingCategory.choices)
    rows = (
        PendingItem.objects.filter(
            process_id__in=processes_for_actor(actor).values("pk"),
            identified_at__gte=period.start_at,
            identified_at__lte=period.end_at,
        )
        .values("category")
        .annotate(
            total=Count("pk"),
            # Bloqueio ainda de pé: a mesma `Q` que trava a conclusão da tarefa.
            blocking=Count("pk", filter=unresolved_blocking_q()),
        )
        .order_by("-total", "category")[:REPORT_ROWS]
    )
    return tuple(
        CountRow(
            key=str(row["category"]),
            label=labels.get(str(row["category"]), str(row["category"])),
            total=int(row["total"]),
            detail=int(row["blocking"]),
        )
        for row in rows
    )


def _processes_by_company(actor: User, period: Period) -> tuple[CountRow, ...]:
    rows = (
        processes_for_actor(actor)
        .filter(opened_at__gte=period.start_at, opened_at__lte=period.end_at)
        .values("company_code")
        .annotate(total=Count("pk"))
        .order_by("-total", "company_code")[:REPORT_ROWS]
    )
    return tuple(
        CountRow(
            key=str(row["company_code"]),
            label=f"Empresa {row['company_code']}",
            total=int(row["total"]),
        )
        for row in rows
    )


def _overdue_processes(actor: User, now: datetime) -> tuple[tuple[OverdueRow, ...], int]:
    """Fotografia de agora: processo em aberto com data limite vencida."""

    today = timezone.localdate(now)
    processes = open_processes_for_actor(actor).filter(due_date__lt=today)
    total = processes.count()
    open_counts = {
        int(row["process_id"]): int(row["total"])
        for row in ProcessSectorTask.objects.filter(
            process_id__in=processes.values("pk"),
            status__in=OPEN_TASK_STATUSES,
        )
        .values("process_id")
        .annotate(total=Count("pk"))
    }
    rows = processes.select_related("employee_snapshot").order_by("due_date", "pk")[:REPORT_ROWS]
    return (
        tuple(
            OverdueRow(
                process_uuid=str(process.uuid),
                employee_name=process.employee_snapshot.employee_name,
                company_code=process.company_code,
                branch_code=process.branch_code,
                due_date=process.due_date,
                days_overdue=(today - process.due_date).days,
                open_tasks=open_counts.get(process.pk, 0),
            )
            for process in rows
        ),
        total,
    )


def _sector_delays(actor: User, now: datetime) -> tuple[DurationRow, ...]:
    """Fotografia de agora: setores com tarefa vencida e o atraso médio delas."""

    rows = ProcessSectorTask.objects.filter(
        process_id__in=processes_for_actor(actor).values("pk"),
        status__in=OPEN_TASK_STATUSES,
        due_at__lt=now,
    ).values_list("sector_id", "sector_name_snapshot", "due_at")

    buckets: dict[tuple[int, str], list[timedelta]] = {}
    for sector_id, sector_name, due_at in rows:
        buckets.setdefault((sector_id, sector_name), []).append(now - due_at)
    ordered = sorted(buckets.items(), key=lambda item: (-len(item[1]), item[0][1]))
    return tuple(
        DurationRow(
            key=str(sector_id),
            label=sector_name,
            total=len(delays),
            average_hours=_hours(sum(delays, timedelta()) / len(delays)),
        )
        for (sector_id, sector_name), delays in ordered[:REPORT_ROWS]
    )


def _amounts(actor: User, period: Period) -> tuple[AmountRow, ...]:
    """Informado e aprovado por moeda.

    Somar moedas diferentes numa linha seria falso — a consolidação por
    processo já separa assim (ADR-009, RF-026). O aprovado só existe depois da
    decisão; a rejeitada e a abonada resolvem em zero no service e somam sem
    tratamento especial.
    """

    rows = (
        PendingItem.objects.filter(
            process_id__in=processes_for_actor(actor).values("pk"),
            category=PendingCategory.VALUE,
            amount__isnull=False,
            amount__informed_at__gte=period.start_at,
            amount__informed_at__lte=period.end_at,
        )
        .values("amount__currency")
        .annotate(
            informed=Sum("amount__amount_informed"),
            approved=Sum("amount__amount_approved"),
            undecided=Count("pk", filter=~Q(status__in=DECIDED_STATUSES)),
        )
        .order_by("amount__currency")
    )
    return tuple(
        AmountRow(
            currency=str(row["amount__currency"]),
            informed=row["informed"] or Decimal("0.00"),
            approved=row["approved"] or Decimal("0.00"),
            undecided=int(row["undecided"]),
        )
        for row in rows
    )


def _released_by_month(actor: User, period: Period) -> tuple[tuple[CountRow, ...], int]:
    rows = (
        processes_for_actor(actor)
        .filter(released_at__gte=period.start_at, released_at__lte=period.end_at)
        .annotate(month=TruncMonth("released_at"))
        .values("month")
        .annotate(total=Count("pk"))
        .order_by("month")
    )
    materialized = [
        CountRow(
            key=row["month"].date().isoformat(),
            label=_month_label(row["month"]),
            total=int(row["total"]),
        )
        for row in rows
    ]
    return tuple(materialized), sum(row.total for row in materialized)


def build_reports(actor: User, *, start: date | None, end: date | None) -> Reports:
    period = Period.resolve(start, end)
    now = timezone.now()
    overdue_rows, overdue_total = _overdue_processes(actor, now)
    released_rows, released_total = _released_by_month(actor, period)
    return Reports(
        period=period,
        process_cycle_time=_process_cycle_time(actor, period),
        sector_cycle_time=_sector_cycle_time(actor, period),
        pending_by_category=_pending_by_category(actor, period),
        processes_by_company=_processes_by_company(actor, period),
        overdue_processes=overdue_rows,
        overdue_process_count=overdue_total,
        sector_delays=_sector_delays(actor, now),
        amounts=_amounts(actor, period),
        released_by_month=released_rows,
        released_total=released_total,
    )
