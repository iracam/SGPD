"""Authenticated API for opening offboarding-process drafts."""

from __future__ import annotations

import logging
from typing import Any, cast

from django.core.exceptions import PermissionDenied
from django.db.models import Q
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.authorization import has_effective_role
from apps.accounts.models import PEOPLE_DEPARTMENT_ROLE_CODE, User
from apps.integrations.senior.exceptions import (
    SeniorContractError,
    SeniorUnavailableError,
)
from apps.integrations.senior.repository import SeniorRepository
from config.api import api_error

from .models import EmployeeSnapshot, OffboardingProcess
from .serializers import (
    ManagerCandidateQuerySerializer,
    OpenOffboardingProcessSerializer,
)
from .services import (
    OpenOffboardingProcessCommand,
    OpenOffboardingProcessService,
)

logger = logging.getLogger(__name__)


def _snapshot_payload(snapshot: EmployeeSnapshot) -> dict[str, Any]:
    return {
        "company_code": snapshot.company_code,
        "branch_code": snapshot.branch_code,
        "branch_legal_name": snapshot.branch_legal_name,
        "employee_type_code": snapshot.employee_type_code,
        "employee_type_description": snapshot.employee_type_description,
        "registration": snapshot.registration,
        "employee_name": snapshot.employee_name,
        "admission_date": snapshot.admission_date.isoformat(),
        "leave_code": snapshot.leave_code,
        "leave_description": snapshot.leave_description,
        "leave_date": snapshot.leave_date.isoformat() if snapshot.leave_date else None,
        "job_structure_code": snapshot.job_structure_code,
        "job_code": snapshot.job_code,
        "job_description": snapshot.job_description,
        "cost_center_code": snapshot.cost_center_code,
        "cost_center_description": snapshot.cost_center_description,
        "source_updated_at": (
            snapshot.source_updated_at.isoformat() if snapshot.source_updated_at else None
        ),
        "source_queried_at": snapshot.source_queried_at.isoformat(),
    }


def process_payload(process: OffboardingProcess) -> dict[str, Any]:
    return {
        "uuid": str(process.uuid),
        "status": process.status,
        "company_code": process.company_code,
        "branch_code": process.branch_code,
        "employee_type_code": process.employee_type_code,
        "employee_registration": process.employee_registration,
        "manager": {
            "id": process.manager_id,
            "name": process.manager_name_snapshot,
            "email": process.manager_email_snapshot,
        },
        "opened_by": {
            "id": process.opened_by_id,
            "username": process.opened_by.username,
        },
        "opened_at": process.opened_at.isoformat(),
        "planned_termination_date": process.planned_termination_date.isoformat(),
        "due_date": process.due_date.isoformat(),
        "reason": process.reason,
        "priority": process.priority,
        "notes": process.notes,
        "version": process.version,
        "employee_snapshot": _snapshot_payload(process.employee_snapshot),
    }


class ProcessListCreateView(APIView):
    permission_classes = [IsAuthenticated]
    repository_class = SeniorRepository
    service_class = OpenOffboardingProcessService

    def post(self, request: Request) -> Response:
        serializer = OpenOffboardingProcessSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = cast(dict[str, Any], serializer.validated_data)
        try:
            process = self.service_class(repository=self.repository_class()).execute(
                OpenOffboardingProcessCommand(
                    actor=cast(User, request.user),
                    company_code=data["company_code"],
                    branch_code=data["branch_code"],
                    employee_type_code=data["employee_type_code"],
                    employee_registration=data["employee_registration"],
                    manager_user_id=data["manager_user_id"],
                    planned_termination_date=data["planned_termination_date"],
                    due_date=data["due_date"],
                    reason=data["reason"],
                    priority=data["priority"],
                    notes=data["notes"],
                )
            )
        except SeniorUnavailableError:
            return api_error(
                code="senior_unavailable",
                message="Senior HCM indisponível para abrir o processo.",
                status_code=503,
            )
        except SeniorContractError:
            logger.exception("offboarding_open_senior_contract_error")
            return api_error(
                code="senior_contract_error",
                message="Resposta inválida da fonte cadastral.",
                status_code=502,
            )

        process = (
            OffboardingProcess.objects.select_related("manager", "opened_by")
            .select_related("employee_snapshot")
            .get(pk=process.pk)
        )
        return Response(process_payload(process), status=201)


class ManagerCandidateListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request: Request) -> Response:
        serializer = ManagerCandidateQuerySerializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)
        data = cast(dict[str, Any], serializer.validated_data)
        actor = cast(User, request.user)
        if not has_effective_role(
            actor,
            PEOPLE_DEPARTMENT_ROLE_CODE,
            company_code=data["company"],
            branch_code=data["branch"],
        ):
            raise PermissionDenied(
                "O ator não possui o papel DP vigente para a empresa e a filial informadas."
            )

        users = User.objects.filter(is_active=True).order_by(
            "first_name",
            "last_name",
            "username",
            "pk",
        )
        query = data["q"]
        if query:
            users = users.filter(
                Q(first_name__icontains=query)
                | Q(last_name__icontains=query)
                | Q(username__icontains=query)
                | Q(email__icontains=query)
            )
        results = [
            {
                "id": user.pk,
                "username": user.username,
                "display_name": user.get_full_name().strip() or user.username,
                "email": user.email,
            }
            for user in users[: data["limit"]]
        ]
        return Response({"limit": data["limit"], "results": results})
