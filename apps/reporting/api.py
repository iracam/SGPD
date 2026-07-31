"""API dos indicadores de operação (RF-034, RF-035).

Somente leitura e sem parâmetro: o recorte é o do ator. A view não decide
visibilidade — quem decide é `evaluate_dashboard`, sobre as mesmas funções que
a listagem de processos e a de tarefas já usam.
"""

from __future__ import annotations

from typing import Any, cast

from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.models import User

from .indicators import (
    CoordinationIndicators,
    CriticalProcess,
    DashboardIndicators,
    KeyedCount,
    SectorIndicators,
    evaluate_dashboard,
)


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
