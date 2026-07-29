"""Authenticated API for opening offboarding-process drafts."""

from __future__ import annotations

import logging
from typing import Any, cast

from django.core.exceptions import PermissionDenied
from django.db.models import F, Q
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.authorization import has_effective_role
from apps.accounts.models import PEOPLE_DEPARTMENT_ROLE_CODE, ScopeType, User
from apps.integrations.senior.exceptions import (
    SeniorContractError,
    SeniorUnavailableError,
)
from apps.integrations.senior.repository import SeniorRepository
from apps.sectors.models import SectorScope
from apps.templates_engine.models import ValidationGroupVersion, VersionStatus
from config.api import api_error

from .models import (
    DraftOverrideAction,
    EmployeeSnapshot,
    OffboardingProcess,
    ProcessSectorTask,
)
from .serializers import (
    ManagerCandidateQuerySerializer,
    OpenOffboardingProcessSerializer,
    StartOffboardingProcessSerializer,
    UpdateDraftSelectionSerializer,
)
from .services import (
    DraftSectorOverrideValue,
    GetDraftProcessContextService,
    IdempotencyConflict,
    OpenOffboardingProcessCommand,
    OpenOffboardingProcessService,
    StartOffboardingProcessCommand,
    StartOffboardingProcessService,
    UpdateDraftSelectionCommand,
    UpdateDraftSelectionService,
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
    started_by: dict[str, Any] | None = None
    if process.started_by_id is not None:
        assert process.started_by is not None
        started_by = {
            "id": process.started_by_id,
            "username": process.started_by.username,
        }
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
        "started_at": process.started_at.isoformat() if process.started_at else None,
        "started_by": started_by,
        "planned_termination_date": process.planned_termination_date.isoformat(),
        "due_date": process.due_date.isoformat(),
        "reason": process.reason,
        "priority": process.priority,
        "notes": process.notes,
        "version": process.version,
        "employee_snapshot": _snapshot_payload(process.employee_snapshot),
    }


def _task_payload(task: ProcessSectorTask) -> dict[str, Any]:
    return {
        "id": task.pk,
        "status": task.status,
        "sector": {
            "id": task.sector_id,
            "code": task.sector_code_snapshot,
            "name": task.sector_name_snapshot,
        },
        "template": {
            "version_id": task.template_version_id,
            "code": task.template_code_snapshot,
            "version_number": task.template_version_snapshot,
        },
        "is_required": task.is_required,
        "blocks_process": task.blocks_process,
        "sla_hours": task.sla_hours_snapshot,
        "due_at": task.due_at.isoformat(),
        "started_at": task.started_at.isoformat(),
        "checklist_item_count": task.checklist_items.count(),
        "version": task.version,
    }


def _scope_applies(scope: SectorScope, process: OffboardingProcess) -> bool:
    return (
        scope.scope_type == ScopeType.GLOBAL
        or (scope.scope_type == ScopeType.COMPANY and scope.company_code == process.company_code)
        or (
            scope.scope_type == ScopeType.BRANCH
            and scope.company_code == process.company_code
            and scope.branch_code == process.branch_code
        )
    )


def _available_group_payload(
    version: ValidationGroupVersion,
    process: OffboardingProcess,
) -> dict[str, Any]:
    sectors = [
        {
            "id": rule.sector_id,
            "code": rule.sector.code,
            "name": rule.sector.name,
            "is_required": rule.is_required,
            "blocks_process": rule.blocks_process,
            "template_version_id": rule.template_version_id,
            "template_code": rule.template_version.template_id,
            "template_version_number": rule.template_version.version_number,
        }
        for rule in version.sector_rules.all()
        if any(_scope_applies(scope, process) for scope in rule.sector.scopes.all())
    ]
    return {
        "version_id": version.pk,
        "group_id": version.group_id,
        "code": version.group.code,
        "name": version.group.name,
        "description": version.group.description,
        "version_number": version.version_number,
        "sectors": sectors,
    }


def _available_groups(process: OffboardingProcess) -> list[dict[str, Any]]:
    versions = (
        ValidationGroupVersion.objects.filter(
            status=VersionStatus.PUBLISHED,
            group__is_active=True,
            group__current_version_id=F("pk"),
        )
        .filter(
            Q(sector_rules__sector__scopes__scope_type=ScopeType.GLOBAL)
            | Q(
                sector_rules__sector__scopes__scope_type=ScopeType.COMPANY,
                sector_rules__sector__scopes__company_code=process.company_code,
            )
            | Q(
                sector_rules__sector__scopes__scope_type=ScopeType.BRANCH,
                sector_rules__sector__scopes__company_code=process.company_code,
                sector_rules__sector__scopes__branch_code=process.branch_code,
            )
        )
        .select_related("group")
        .prefetch_related(
            "sector_rules__sector__scopes",
            "sector_rules__template_version__template",
        )
        .distinct()
        .order_by("group_id")
    )
    return [_available_group_payload(version, process) for version in versions]


def _draft_payload(actor: User, process_uuid: str) -> dict[str, Any]:
    context = GetDraftProcessContextService().execute(actor, process_uuid)
    process = context.process
    selected = process.selected_groups.select_related("group_version__group").order_by(
        "group_version__group_id"
    )
    overrides = process.sector_overrides.select_related(
        "sector",
        "template_version__template",
    ).order_by("sector_id")
    tasks = process.sector_tasks.select_related(
        "sector",
        "template_version",
    ).prefetch_related("checklist_items")
    return {
        "process": process_payload(process),
        "selection": {
            "group_version_ids": [selection.group_version_id for selection in selected],
            "groups": [
                {
                    "version_id": selection.group_version_id,
                    "code": selection.group_version.group.code,
                    "name": selection.group_version.group.name,
                    "version_number": selection.group_version.version_number,
                }
                for selection in selected
            ],
            "overrides": [
                {
                    "sector_id": override.sector_id,
                    "sector_code": override.sector.code,
                    "action": override.action,
                    "template_version_id": override.template_version_id,
                    "is_required": override.is_required,
                    "blocks_process": override.blocks_process,
                    "due_hours_override": override.due_hours_override,
                    "reason": override.reason,
                }
                for override in overrides
            ],
            "resolved_sectors": [
                {
                    "sector_id": plan.sector.pk,
                    "code": plan.sector.code,
                    "name": plan.sector.name,
                    "template_version_id": plan.template_version.pk,
                    "template_code": plan.template_version.template_id,
                    "template_version_number": plan.template_version.version_number,
                    "is_required": plan.is_required,
                    "blocks_process": plan.blocks_process,
                    "sla_hours": plan.sla_hours,
                    "source": "MANUAL" if plan.override else "GROUP",
                }
                for plan in context.plans
            ],
            "blockers": list(context.blockers),
        },
        "available_groups": _available_groups(process),
        "tasks": [_task_payload(task) for task in tasks],
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


class ProcessDraftDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request: Request, process_uuid: str) -> Response:
        return Response(_draft_payload(cast(User, request.user), process_uuid))


class ProcessDraftSelectionView(APIView):
    permission_classes = [IsAuthenticated]

    def put(self, request: Request, process_uuid: str) -> Response:
        serializer = UpdateDraftSelectionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = cast(dict[str, Any], serializer.validated_data)
        UpdateDraftSelectionService().execute(
            UpdateDraftSelectionCommand(
                actor=cast(User, request.user),
                process_uuid=process_uuid,
                expected_version=data["expected_version"],
                group_version_ids=tuple(data["group_version_ids"]),
                overrides=tuple(
                    DraftSectorOverrideValue(
                        sector_id=item["sector_id"],
                        action=DraftOverrideAction(item["action"]),
                        reason=item["reason"],
                        template_version_id=item.get("template_version_id"),
                        is_required=item["is_required"],
                        blocks_process=item["blocks_process"],
                        due_hours_override=item.get("due_hours_override"),
                    )
                    for item in data["overrides"]
                ),
            )
        )
        return Response(_draft_payload(cast(User, request.user), process_uuid))


class ProcessStartView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request: Request, process_uuid: str) -> Response:
        serializer = StartOffboardingProcessSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = cast(dict[str, Any], serializer.validated_data)
        try:
            result = StartOffboardingProcessService().execute(
                StartOffboardingProcessCommand(
                    actor=cast(User, request.user),
                    process_uuid=process_uuid,
                    expected_version=data["expected_version"],
                    idempotency_key=request.headers.get("Idempotency-Key", ""),
                )
            )
        except IdempotencyConflict as exc:
            return api_error(
                code="idempotency_conflict",
                message=str(exc),
                status_code=409,
            )
        payload = _draft_payload(cast(User, request.user), process_uuid)
        payload["idempotency_replayed"] = result.replayed
        return Response(payload)
