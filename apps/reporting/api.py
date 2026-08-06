"""API dos indicadores e dos relatórios (RF-034, RF-035, RF-036).

Somente leitura. O painel não recebe parâmetro — o recorte é o do ator; os
relatórios recebem apenas o período. As views não decidem visibilidade: quem
decide é `evaluate_dashboard`/`build_reports`, sobre as mesmas funções que a
listagem de processos e a de tarefas já usam.
"""

from __future__ import annotations

from typing import Any, cast

from django.http import HttpResponse
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.authorization import active_assignments, has_global_authority
from apps.accounts.models import PEOPLE_DEPARTMENT_ROLE_CODES, User
from config.api import api_error

from .exports import ExportTooLarge, build_export
from .indicators import (
    CoordinationIndicators,
    CriticalProcess,
    DashboardIndicators,
    KeyedCount,
    SectorIndicators,
    evaluate_dashboard,
)
from .models import ExportDataset
from .operations import OperationsStatus, evaluate_operations
from .reports import (
    AmountRow,
    CountRow,
    DurationRow,
    OverdueRow,
    Period,
    Reports,
    build_reports,
)
from .serializers import ReportQuerySerializer


def _count_payload(row: KeyedCount) -> dict[str, Any]:
    return {"key": row.key, "label": row.label, "total": row.total}


def _critical_payload(row: CriticalProcess) -> dict[str, Any]:
    return {
        "process_uuid": row.uuid,
        "process_ref": row.uuid[:8],
        "employee_name": row.employee_name,
        "company_code": row.company_code,
        "branch_code": row.branch_code,
        "due_date": row.due_date.isoformat(),
        "overdue_tasks": row.overdue_tasks,
    }


def _coordination_payload(block: CoordinationIndicators) -> dict[str, Any]:
    return {
        "open_processes": block.open_processes,
        "completed_processes": block.completed_processes,
        "draft_processes": block.draft_processes,
        "cancelled_processes": block.cancelled_processes,
        "overdue_processes": block.overdue_processes,
        "due_soon_processes": block.due_soon_processes,
        "open_pending_items": block.open_pending_items,
        "blocking_pending_items": block.blocking_pending_items,
        "amounts_awaiting_decision": block.amounts_awaiting_decision,
        "by_status": [_count_payload(row) for row in block.by_status],
        "delayed_sectors": [_count_payload(row) for row in block.delayed_sectors],
        "amount_totals": [
            # O valor viaja como string: `Decimal` em JSON vira float e float
            # não é dinheiro. A SPA formata, não recalcula.
            {"currency": row.currency, "informed": f"{row.informed:.2f}"}
            for row in block.amount_totals
        ],
        "critical_processes": [_critical_payload(row) for row in block.critical_processes],
    }


def _sector_payload(block: SectorIndicators) -> dict[str, Any]:
    return {
        "pending_tasks": block.pending_tasks,
        "overdue_tasks": block.overdue_tasks,
        "due_soon_tasks": block.due_soon_tasks,
        "by_company": [_count_payload(row) for row in block.by_company],
        "by_branch": [_count_payload(row) for row in block.by_branch],
        "critical_processes": [_critical_payload(row) for row in block.critical_processes],
    }


def dashboard_payload(indicators: DashboardIndicators) -> dict[str, Any]:
    return {
        "generated_at": indicators.generated_at.isoformat(),
        "coordination": (
            _coordination_payload(indicators.coordination)
            if indicators.coordination is not None
            else None
        ),
        "sector": (_sector_payload(indicators.sector) if indicators.sector is not None else None),
    }


class DashboardView(APIView):
    """Indicadores do painel do ator autenticado.

    Sem bloco algum, a resposta é `null` nos dois: é informação, não negativa —
    o usuário existe, autenticou e simplesmente não coordena processo nem
    responde por setor. Devolver 403 aqui esconderia o painel de quem só
    precisa saber que não há nada para ele.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request: Request) -> Response:
        actor = cast(User, request.user)
        return Response(dashboard_payload(evaluate_dashboard(actor)))


def _duration_payload(row: DurationRow) -> dict[str, Any]:
    return {
        "key": row.key,
        "label": row.label,
        "total": row.total,
        "average_hours": row.average_hours,
    }


def _row_payload(row: CountRow) -> dict[str, Any]:
    return {"key": row.key, "label": row.label, "total": row.total, "detail": row.detail}


def _amount_payload(row: AmountRow) -> dict[str, Any]:
    return {
        "currency": row.currency,
        "informed": f"{row.informed:.2f}",
        "approved": f"{row.approved:.2f}",
        "undecided": row.undecided,
    }


def _overdue_payload(row: OverdueRow) -> dict[str, Any]:
    return {
        "process_uuid": row.process_uuid,
        "process_ref": row.process_uuid[:8],
        "employee_name": row.employee_name,
        "company_code": row.company_code,
        "branch_code": row.branch_code,
        "due_date": row.due_date.isoformat(),
        "days_overdue": row.days_overdue,
        "open_tasks": row.open_tasks,
    }


def reports_payload(reports: Reports) -> dict[str, Any]:
    return {
        "period": {
            "start": reports.period.start.isoformat(),
            "end": reports.period.end.isoformat(),
        },
        "process_cycle_time": {
            "processes": reports.process_cycle_time.processes,
            "average_days": reports.process_cycle_time.average_days,
            "median_days": reports.process_cycle_time.median_days,
        },
        "sector_cycle_time": [_duration_payload(row) for row in reports.sector_cycle_time],
        "pending_by_category": [_row_payload(row) for row in reports.pending_by_category],
        "processes_by_company": [_row_payload(row) for row in reports.processes_by_company],
        "overdue_processes": {
            "total": reports.overdue_process_count,
            "results": [_overdue_payload(row) for row in reports.overdue_processes],
        },
        "sector_delays": [_duration_payload(row) for row in reports.sector_delays],
        "amounts": [_amount_payload(row) for row in reports.amounts],
        "released_processes": {
            "total": reports.released_total,
            "results": [_row_payload(row) for row in reports.released_by_month],
        },
    }


def _require_process_coordinator(actor: User) -> None:
    """Relatório é conferência do escopo do `DP`.

    Ele atravessa todos os setores do processo, então quem só responde por um
    setor não o alcança — a mesma régua da consolidação de valores e da fila de
    notificações.
    """

    if (
        not has_global_authority(actor)
        and not active_assignments(actor)
        .filter(role__code__in=PEOPLE_DEPARTMENT_ROLE_CODES)
        .exists()
    ):
        raise PermissionDenied("O ator não possui o papel DP vigente.")


def _requested_period(request: Request) -> Period:
    serializer = ReportQuerySerializer(data=request.query_params)
    serializer.is_valid(raise_exception=True)
    data = cast(dict[str, Any], serializer.validated_data)
    return Period.resolve(data["start"], data["end"])


class ReportsView(APIView):
    """Relatórios mínimos do RF-036, no recorte de período informado."""

    permission_classes = [IsAuthenticated]

    def get(self, request: Request) -> Response:
        actor = cast(User, request.user)
        _require_process_coordinator(actor)
        period = _requested_period(request)
        return Response(reports_payload(build_reports(actor, start=period.start, end=period.end)))


def operations_payload(status: OperationsStatus) -> dict[str, Any]:
    return {
        "checked_at": status.checked_at.isoformat(),
        "queue": {
            "counts": status.queue.counts,
            "oldest_pending_at": (
                status.queue.oldest_pending_at.isoformat()
                if status.queue.oldest_pending_at is not None
                else None
            ),
            "last_sent_at": (
                status.queue.last_sent_at.isoformat()
                if status.queue.last_sent_at is not None
                else None
            ),
            "stale_minutes": status.queue.stale_minutes,
            "is_stalled": status.queue.is_stalled,
            "verdict": status.queue.verdict,
        },
        "scheduler": {
            "last_beat_at": (
                status.scheduler.last_beat_at.isoformat()
                if status.scheduler.last_beat_at is not None
                else None
            ),
            "stale_minutes": status.scheduler.stale_minutes,
            "is_stalled": status.scheduler.is_stalled,
            "verdict": status.scheduler.verdict,
        },
        "storage": {
            "evidence_count": status.storage.evidence_count,
            "evidence_bytes": status.storage.evidence_bytes,
        },
        "retention": {
            "closed_processes": status.retention.closed_processes,
            "beyond_retention": status.retention.beyond_retention,
            "oldest_closed_at": (
                status.retention.oldest_closed_at.isoformat()
                if status.retention.oldest_closed_at is not None
                else None
            ),
            "retention_years": status.retention.retention_years,
        },
    }


class OperationsView(APIView):
    """Sonda operacional: fila, armazenamento e retenção (R63, RNF-009).

    É diagnóstico técnico do ambiente, não conferência de processo: só o
    SuperAdmin a enxerga, como a central de configuração (ADR-031, ADR-050).
    """

    permission_classes = [IsAuthenticated]

    def get(self, request: Request) -> Response:
        if not has_global_authority(cast(User, request.user)):
            raise PermissionDenied("A operação técnica é exclusiva do SuperAdmin.")
        return Response(operations_payload(evaluate_operations()))


class ExportView(APIView):
    """Exportação CSV de um conjunto, no mesmo recorte dos relatórios.

    O arquivo sai como anexo e o ato fica na trilha `SGPD_REPORT_EXPORT`, com
    ator, conjunto, período, linhas e correlation ID: exportar leva dado
    pessoal para fora do sistema e a LGPD exige auditoria de acesso
    (`SECURITY.md` §6).
    """

    permission_classes = [IsAuthenticated]

    def get(self, request: Request, dataset: str) -> HttpResponse:
        actor = cast(User, request.user)
        _require_process_coordinator(actor)
        chosen = dataset.upper()
        if chosen not in ExportDataset.values:
            return api_error(
                code="unknown_dataset",
                message="Conjunto de exportação desconhecido.",
                status_code=404,
            )
        period = _requested_period(request)
        try:
            export = build_export(actor, dataset=chosen, period=period)
        except ExportTooLarge as exc:
            # Recusa legível em vez de arquivo truncado: quem confere somaria o
            # que não é o total e não teria como saber.
            return api_error(code="export_too_large", message=str(exc), status_code=400)
        response = HttpResponse(export.content, content_type="text/csv; charset=utf-8")
        response["Content-Disposition"] = f'attachment; filename="{export.filename}"'
        response["X-Export-Rows"] = str(export.row_count)
        return response
