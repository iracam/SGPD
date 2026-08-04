"""Authenticated API for opening offboarding-process drafts."""

from __future__ import annotations

import logging
from typing import Any, cast

from django.core.exceptions import PermissionDenied
from django.db.models import Exists, F, OuterRef, Q
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.authorization import active_assignments, has_global_authority, has_permission
from apps.accounts.models import PEOPLE_DEPARTMENT_ROLE_CODES, ScopeType, User
from apps.integrations.senior.exceptions import (
    SeniorContractError,
    SeniorUnavailableError,
)
from apps.integrations.senior.repository import SeniorRepository
from apps.sectors.models import SectorScope
from apps.templates_engine.models import (
    ValidationGroupSector,
    ValidationGroupVersion,
    VersionStatus,
)
from apps.templates_engine.services import resolve_applicable_group_versions
from config.api import api_error

from .models import (
    DraftOverrideAction,
    EmployeeSnapshot,
    OffboardingProcess,
    ProcessChecklistItem,
    ProcessSectorTask,
)
from .readiness import ProcessReadiness, closing_blockers, evaluate_process_readiness
from .serializers import (
    CancelProcessSerializer,
    CloseProcessSerializer,
    CompleteSectorTaskSerializer,
    OpenOffboardingProcessSerializer,
    ProcessQuerySerializer,
    RegisterTerminationProcessingSerializer,
    ReleaseProcessSerializer,
    ReopenProcessSerializer,
    SectorTaskQuerySerializer,
    StartOffboardingProcessSerializer,
    StartSectorTaskSerializer,
    UpdateDraftSelectionSerializer,
)
from .services import (
    CancelProcessCommand,
    CancelProcessService,
    ChecklistAnswerValue,
    CloseProcessCommand,
    CloseProcessService,
    CompleteSectorTaskCommand,
    CompleteSectorTaskService,
    DraftSectorOverrideValue,
    GetDraftProcessContextService,
    IdempotencyConflict,
    OpenOffboardingProcessCommand,
    OpenOffboardingProcessService,
    ProcessTransitionResult,
    RegisterTerminationProcessingCommand,
    RegisterTerminationProcessingService,
    ReleaseProcessCommand,
    ReleaseProcessService,
    ReopenProcessCommand,
    ReopenProcessService,
    StartOffboardingProcessCommand,
    StartOffboardingProcessService,
    StartSectorTaskCommand,
    StartSectorTaskService,
    UpdateDraftSelectionCommand,
    UpdateDraftSelectionService,
    completed_processes_for_actor,
    open_processes_for_actor,
    processes_for_actor,
    sector_tasks_for_actor,
)

logger = logging.getLogger(__name__)

#: Tudo que `process_payload` projeta: sem isto, cada marca formal custaria uma
#: consulta por linha da listagem.
PROCESS_RELATED = (
    "opened_by",
    "started_by",
    "released_by",
    "processing_registered_by",
    "closed_by",
    "cancelled_by",
    "employee_snapshot",
)


def _require_process_coordinator(actor: User) -> None:
    if (
        not has_global_authority(actor)
        and not active_assignments(actor)
        .filter(role__code__in=PEOPLE_DEPARTMENT_ROLE_CODES)
        .exists()
    ):
        raise PermissionDenied("O ator não possui o papel DP vigente.")


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


def _actor_ref(process: OffboardingProcess, field: str) -> dict[str, Any] | None:
    """Ator de uma marca formal, sem consultar o banco quando não há marca."""

    actor_id = getattr(process, f"{field}_id")
    if actor_id is None:
        return None
    actor = getattr(process, field)
    return {"id": actor_id, "username": actor.username}


def _formal_marks_payload(process: OffboardingProcess) -> dict[str, Any]:
    """Datas, atores e textos de cada ato formal do ciclo (ADR-051)."""

    return {
        "released_at": process.released_at.isoformat() if process.released_at else None,
        "released_by": _actor_ref(process, "released_by"),
        "release_notes": process.release_notes,
        "release_override_reason": process.release_override_reason,
        # Declaração de conferência humana, não espelho do Senior.
        "termination_reference": process.termination_reference,
        "termination_processed_on": (
            process.termination_processed_on.isoformat()
            if process.termination_processed_on
            else None
        ),
        "processing_registered_at": (
            process.processing_registered_at.isoformat()
            if process.processing_registered_at
            else None
        ),
        "processing_registered_by": _actor_ref(process, "processing_registered_by"),
        "processing_notes": process.processing_notes,
        "closed_at": process.closed_at.isoformat() if process.closed_at else None,
        "closed_by": _actor_ref(process, "closed_by"),
        "closing_notes": process.closing_notes,
        "closing_override_reason": process.closing_override_reason,
        "cancelled_at": process.cancelled_at.isoformat() if process.cancelled_at else None,
        "cancelled_by": _actor_ref(process, "cancelled_by"),
        "cancellation_reason": process.cancellation_reason,
    }


def readiness_payload(readiness: ProcessReadiness) -> dict[str, Any]:
    """Situação calculada e o que impede a liberação. Nada aqui é estado gravado."""

    return {
        "situation": readiness.situation,
        "is_ready": readiness.is_ready,
        "blockers": list(readiness.blockers),
        "warnings": list(readiness.warnings),
        "task_count": readiness.task_count,
        "required_task_count": readiness.required_task_count,
        "completed_task_count": readiness.completed_task_count,
        "open_task_count": readiness.open_task_count,
        "blocking_pending_count": readiness.blocking_pending_count,
        "open_pending_count": readiness.open_pending_count,
        "undecided_amount_count": readiness.undecided_amount_count,
    }


def process_payload(process: OffboardingProcess) -> dict[str, Any]:
    started_by: dict[str, Any] | None = None
    if process.started_by_id is not None:
        assert process.started_by is not None
        started_by = {
            "id": process.started_by_id,
            "username": process.started_by.username,
        }
    completion_at = getattr(process, "completion_at", None)
    return {
        "uuid": str(process.uuid),
        "status": process.status,
        "company_code": process.company_code,
        "branch_code": process.branch_code,
        "employee_type_code": process.employee_type_code,
        "employee_registration": process.employee_registration,
        "opened_by": {
            "id": process.opened_by_id,
            "username": process.opened_by.username,
        },
        "opened_at": process.opened_at.isoformat(),
        "started_at": process.started_at.isoformat() if process.started_at else None,
        "started_by": started_by,
        "completion_at": completion_at.isoformat() if completion_at else None,
        "planned_termination_date": process.planned_termination_date.isoformat(),
        "due_date": process.due_date.isoformat(),
        "reason": process.reason,
        "priority": process.priority,
        "notes": process.notes,
        "version": process.version,
        "formal": _formal_marks_payload(process),
        "employee_snapshot": _snapshot_payload(process.employee_snapshot),
    }


def _checklist_item_payload(item: ProcessChecklistItem) -> dict[str, Any]:
    response = item.response
    if isinstance(response, dict) and set(response) == {"value"}:
        response = response["value"]
    payload = {
        "id": item.pk,
        "code": item.code_snapshot,
        "question": item.question_snapshot,
        "response_type": item.response_type_snapshot,
        "is_required": item.is_required,
        "blocks_process": item.blocks_process,
        "requires_evidence": item.requires_evidence,
        "allows_pending": item.allows_pending,
        "display_order": item.display_order,
        "config": item.config_snapshot,
        "response": response,
        "answered_at": item.answered_at.isoformat() if item.answered_at else None,
    }
    from apps.evidence.api import evidence_payload

    payload["evidences"] = [
        evidence_payload(evidence) for evidence in item.evidences.all() if evidence.is_active
    ]
    return payload


def _task_payload(
    task: ProcessSectorTask,
    *,
    include_items: bool = False,
    viewer: User | None = None,
) -> dict[str, Any]:
    payload = {
        "id": task.pk,
        "status": task.status,
        "sector": {
            "id": task.sector_id,
            "code": task.sector_code_snapshot,
            "name": task.sector_name_snapshot,
            # Habilitação viva, não snapshot: o service lê a mesma coluna ao
            # aceitar a pretensão de cobrança.
            "allows_amount": task.sector.allows_amount,
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
        "completed_at": task.completed_at.isoformat() if task.completed_at else None,
        "notes": task.notes,
        "checklist_item_count": task.checklist_items.count(),
        "version": task.version,
    }
    if include_items:
        from apps.evidence.api import evidence_payload
        from apps.pending_items.api import pending_item_payload
        from apps.pending_items.services import can_analyse_amounts

        can_analyse_amount = viewer is not None and can_analyse_amounts(viewer, task.process)

        payload["process"] = {
            "uuid": str(task.process.uuid),
            "company_code": task.process.company_code,
            "branch_code": task.process.branch_code,
            "employee_name": task.process.employee_snapshot.employee_name,
            "employee_registration": task.process.employee_registration,
            "due_date": task.process.due_date.isoformat(),
        }
        payload["checklist_items"] = [
            _checklist_item_payload(item) for item in task.checklist_items.all()
        ]
        payload["pending_items"] = [
            pending_item_payload(pending_item, can_analyse_amount=can_analyse_amount)
            for pending_item in task.pending_items.all()
        ]
        payload["evidences"] = [
            evidence_payload(evidence) for evidence in task.evidences.all() if evidence.is_active
        ]
    return payload


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
    applicable_rules = ValidationGroupSector.objects.filter(
        group_version_id=OuterRef("pk"),
    ).filter(
        Q(sector__scopes__scope_type=ScopeType.GLOBAL)
        | Q(
            sector__scopes__scope_type=ScopeType.COMPANY,
            sector__scopes__company_code=process.company_code,
        )
        | Q(
            sector__scopes__scope_type=ScopeType.BRANCH,
            sector__scopes__company_code=process.company_code,
            sector__scopes__branch_code=process.branch_code,
        )
    )
    versions = (
        ValidationGroupVersion.objects.filter(
            status=VersionStatus.PUBLISHED,
            group__is_active=True,
            group__current_version_id=F("pk"),
        )
        .annotate(has_applicable_rule=Exists(applicable_rules))
        .filter(has_applicable_rule=True)
        .select_related("group")
        .prefetch_related(
            "sector_rules__sector__scopes",
            "sector_rules__template_version__template",
        )
        .order_by("group_id")
    )
    return [_available_group_payload(version, process) for version in versions]


def _applicability_suggestion(
    process: OffboardingProcess,
    available_version_ids: set[int],
) -> dict[str, Any]:
    """Sugere grupos pelo snapshot; a seleção continua sendo do DP.

    Só entram grupos que também estão disponíveis para o processo, para não
    sugerir o que a SPA não consegue exibir nem o início conseguiria resolver.
    """
    snapshot = getattr(process, "employee_snapshot", None)
    if snapshot is None:
        return {"group_version_ids": [], "matches": []}
    matches = [
        match
        for match in resolve_applicable_group_versions(
            company_code=snapshot.company_code,
            branch_code=snapshot.branch_code,
            employee_type_code=snapshot.employee_type_code,
            job_structure_code=snapshot.job_structure_code,
            job_code=snapshot.job_code,
            cost_center_code=snapshot.cost_center_code,
            reference_date=timezone.localdate(),
        )
        if match.group_version_id in available_version_ids
    ]
    return {
        "group_version_ids": [match.group_version_id for match in matches],
        "matches": [
            {
                "rule_id": match.rule_id,
                "rule_name": match.rule_name,
                "priority": match.priority,
                "group_id": match.group_id,
                "group_name": match.group_name,
                "group_version_id": match.group_version_id,
            }
            for match in matches
        ],
    }


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
    available_groups = _available_groups(process)
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
        "available_groups": available_groups,
        "applicability_suggestion": _applicability_suggestion(
            process,
            {group["version_id"] for group in available_groups},
        ),
        "tasks": [_task_payload(task) for task in tasks],
    }


class ProcessListCreateView(APIView):
    permission_classes = [IsAuthenticated]
    repository_class = SeniorRepository
    service_class = OpenOffboardingProcessService

    def get(self, request: Request) -> Response:
        actor = cast(User, request.user)
        _require_process_coordinator(actor)

        serializer = ProcessQuerySerializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)
        data = cast(dict[str, Any], serializer.validated_data)
        if data["completed"]:
            process_query = completed_processes_for_actor(actor)
        elif data["open"]:
            process_query = open_processes_for_actor(actor)
        else:
            process_query = processes_for_actor(actor)
        processes = process_query.select_related(*PROCESS_RELATED)
        if data["status"]:
            processes = processes.filter(status=data["status"])
        if data["completed"]:
            processes = processes.order_by(
                F("completion_at").desc(nulls_last=True),
                "-opened_at",
                "-pk",
            )
        else:
            processes = processes.order_by("-opened_at", "-pk")
        offset = data["offset"]
        rows = processes[offset : offset + data["limit"]]
        return Response(
            {
                "offset": offset,
                "limit": data["limit"],
                "results": [process_payload(process) for process in rows],
            }
        )

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

        process = OffboardingProcess.objects.select_related(*PROCESS_RELATED).get(pk=process.pk)
        return Response(process_payload(process), status=201)


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


def _formal_payload(actor: User, process_uuid: Any) -> dict[str, Any]:
    """Estado formal, situação calculada e as tarefas que a reabertura alcança.

    A prontidão é recalculada em toda leitura: o que a tela mostra é sempre
    derivado do que está gravado agora, nunca do que ela leu antes (ADR-051).
    """

    process = get_object_or_404(
        processes_for_actor(actor).select_related(*PROCESS_RELATED),
        uuid=process_uuid,
    )
    readiness = evaluate_process_readiness(process)
    tasks = (
        ProcessSectorTask.objects.filter(process=process)
        .select_related("sector", "template_version")
        .prefetch_related("checklist_items")
        .order_by("sector_code_snapshot", "pk")
    )
    return {
        "process": process_payload(process),
        "readiness": readiness_payload(readiness),
        # Impedimento do encerramento é outra pergunta: a liberação admite
        # pendência que o encerramento não admite.
        "closing_blockers": list(closing_blockers(process)),
        # A SPA só oferece o override a quem o service aceitaria (ADR-054); a
        # decisão em si continua sendo revalidada sob lock no service.
        "can_override_blockers": has_permission(
            actor,
            "offboarding.override_process_blockers",
            company_code=process.company_code,
            branch_code=process.branch_code,
        ),
        "tasks": [_task_payload(task) for task in tasks],
    }


class ProcessReadinessView(APIView):
    """Conferência do ciclo formal: o que já foi decidido e o que ainda impede."""

    permission_classes = [IsAuthenticated]

    def get(self, request: Request, process_uuid: str) -> Response:
        actor = cast(User, request.user)
        _require_process_coordinator(actor)
        return Response(_formal_payload(actor, process_uuid))


class _ProcessTransitionView(APIView):
    """Ato formal do ciclo: a view valida contrato, o service decide tudo o mais."""

    permission_classes = [IsAuthenticated]
    serializer_class: type[Any]

    def execute(
        self,
        *,
        actor: User,
        process_uuid: str,
        idempotency_key: str,
        data: dict[str, Any],
    ) -> ProcessTransitionResult:
        raise NotImplementedError

    def post(self, request: Request, process_uuid: str) -> Response:
        actor = cast(User, request.user)
        _require_process_coordinator(actor)
        get_object_or_404(processes_for_actor(actor), uuid=process_uuid)
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            result = self.execute(
                actor=actor,
                process_uuid=process_uuid,
                idempotency_key=request.headers.get("Idempotency-Key", ""),
                data=cast(dict[str, Any], serializer.validated_data),
            )
        except IdempotencyConflict as exc:
            return api_error(code="idempotency_conflict", message=str(exc), status_code=409)
        except PermissionDenied as exc:
            # A negativa é regra de negócio legível — falta de `DP` no escopo ou
            # a exclusividade do SuperAdmin na reabertura —, e quem a recebe já
            # enxerga o processo: não é sonda de existência.
            return api_error(code="permission_denied", message=str(exc), status_code=403)
        payload = _formal_payload(actor, process_uuid)
        payload["idempotency_replayed"] = result.replayed
        return Response(payload)


class ProcessReleaseView(_ProcessTransitionView):
    serializer_class = ReleaseProcessSerializer

    def execute(
        self,
        *,
        actor: User,
        process_uuid: str,
        idempotency_key: str,
        data: dict[str, Any],
    ) -> ProcessTransitionResult:
        return ReleaseProcessService().execute(
            ReleaseProcessCommand(
                actor=actor,
                process_uuid=process_uuid,
                expected_version=data["expected_version"],
                idempotency_key=idempotency_key,
                notes=data["notes"],
                override_reason=data["override_reason"],
            )
        )


class ProcessTerminationProcessingView(_ProcessTransitionView):
    serializer_class = RegisterTerminationProcessingSerializer

    def execute(
        self,
        *,
        actor: User,
        process_uuid: str,
        idempotency_key: str,
        data: dict[str, Any],
    ) -> ProcessTransitionResult:
        return RegisterTerminationProcessingService().execute(
            RegisterTerminationProcessingCommand(
                actor=actor,
                process_uuid=process_uuid,
                expected_version=data["expected_version"],
                idempotency_key=idempotency_key,
                termination_reference=data["termination_reference"],
                processed_on=data["processed_on"],
                notes=data["notes"],
            )
        )


class ProcessCloseView(_ProcessTransitionView):
    serializer_class = CloseProcessSerializer

    def execute(
        self,
        *,
        actor: User,
        process_uuid: str,
        idempotency_key: str,
        data: dict[str, Any],
    ) -> ProcessTransitionResult:
        return CloseProcessService().execute(
            CloseProcessCommand(
                actor=actor,
                process_uuid=process_uuid,
                expected_version=data["expected_version"],
                idempotency_key=idempotency_key,
                notes=data["notes"],
                override_reason=data["override_reason"],
            )
        )


class ProcessCancelView(_ProcessTransitionView):
    serializer_class = CancelProcessSerializer

    def execute(
        self,
        *,
        actor: User,
        process_uuid: str,
        idempotency_key: str,
        data: dict[str, Any],
    ) -> ProcessTransitionResult:
        return CancelProcessService().execute(
            CancelProcessCommand(
                actor=actor,
                process_uuid=process_uuid,
                expected_version=data["expected_version"],
                idempotency_key=idempotency_key,
                reason=data["reason"],
            )
        )


class ProcessReopenView(_ProcessTransitionView):
    serializer_class = ReopenProcessSerializer

    def execute(
        self,
        *,
        actor: User,
        process_uuid: str,
        idempotency_key: str,
        data: dict[str, Any],
    ) -> ProcessTransitionResult:
        return ReopenProcessService().execute(
            ReopenProcessCommand(
                actor=actor,
                process_uuid=process_uuid,
                expected_version=data["expected_version"],
                idempotency_key=idempotency_key,
                reason=data["reason"],
                task_ids=tuple(data["task_ids"]),
            )
        )


class ProcessTaskListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request: Request, process_uuid: str) -> Response:
        actor = cast(User, request.user)
        _require_process_coordinator(actor)
        process = get_object_or_404(
            processes_for_actor(actor),
            uuid=process_uuid,
        )
        serializer = SectorTaskQuerySerializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)
        data = cast(dict[str, Any], serializer.validated_data)
        tasks = (
            ProcessSectorTask.objects.filter(process=process)
            .select_related("sector", "template_version", "completed_by")
            .prefetch_related("checklist_items")
        )
        if data["status"]:
            tasks = tasks.filter(status=data["status"])
        tasks = tasks.order_by(
            F("completed_at").desc(nulls_last=True),
            "due_at",
            "pk",
        )
        offset = data["offset"]
        rows = tasks[offset : offset + data["limit"]]
        return Response(
            {
                "offset": offset,
                "limit": data["limit"],
                "results": [_task_payload(task) for task in rows],
            }
        )


def _responsible_task_queryset(actor: User) -> Any:
    return (
        sector_tasks_for_actor(actor)
        .select_related(
            "process",
            "process__employee_snapshot",
            "sector",
            "template_version",
            "completed_by",
        )
        .prefetch_related(
            "checklist_items__evidences__uploaded_by",
            "pending_items__items",
            "pending_items__comments__author",
            "pending_items__registered_by",
            "pending_items__amount__informed_by",
            "pending_items__amount__approved_by",
            "pending_items__decisions__decided_by",
            "evidences__pending_item",
            "evidences__uploaded_by",
        )
        .order_by(
            F("completed_at").desc(nulls_last=True),
            "-started_at",
            "-pk",
        )
    )


class SectorTaskListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request: Request) -> Response:
        serializer = SectorTaskQuerySerializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)
        data = cast(dict[str, Any], serializer.validated_data)
        tasks = _responsible_task_queryset(cast(User, request.user))
        if data["status"]:
            tasks = tasks.filter(status=data["status"])
        offset = data["offset"]
        rows = tasks[offset : offset + data["limit"]]
        return Response(
            {
                "offset": offset,
                "limit": data["limit"],
                "results": [
                    _task_payload(task, include_items=True, viewer=cast(User, request.user))
                    for task in rows
                ],
            }
        )


class SectorTaskDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request: Request, task_id: int) -> Response:
        task = get_object_or_404(
            _responsible_task_queryset(cast(User, request.user)),
            pk=task_id,
        )
        return Response(_task_payload(task, include_items=True, viewer=cast(User, request.user)))


class SectorTaskStartView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request: Request, task_id: int) -> Response:
        get_object_or_404(
            _responsible_task_queryset(cast(User, request.user)),
            pk=task_id,
        )
        serializer = StartSectorTaskSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = cast(dict[str, Any], serializer.validated_data)
        try:
            result = StartSectorTaskService().execute(
                StartSectorTaskCommand(
                    actor=cast(User, request.user),
                    task_id=task_id,
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
        task = get_object_or_404(
            _responsible_task_queryset(cast(User, request.user)),
            pk=result.task.pk,
        )
        payload = _task_payload(task, include_items=True, viewer=cast(User, request.user))
        payload["idempotency_replayed"] = result.replayed
        return Response(payload)


class SectorTaskCompleteView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request: Request, task_id: int) -> Response:
        get_object_or_404(
            _responsible_task_queryset(cast(User, request.user)),
            pk=task_id,
        )
        serializer = CompleteSectorTaskSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = cast(dict[str, Any], serializer.validated_data)
        try:
            result = CompleteSectorTaskService().execute(
                CompleteSectorTaskCommand(
                    actor=cast(User, request.user),
                    task_id=task_id,
                    expected_version=data["expected_version"],
                    idempotency_key=request.headers.get("Idempotency-Key", ""),
                    answers=tuple(
                        ChecklistAnswerValue(
                            item_id=answer["item_id"],
                            value=answer["value"],
                        )
                        for answer in data["answers"]
                    ),
                    notes=data["notes"],
                )
            )
        except IdempotencyConflict as exc:
            return api_error(
                code="idempotency_conflict",
                message=str(exc),
                status_code=409,
            )
        task = get_object_or_404(
            _responsible_task_queryset(cast(User, request.user)),
            pk=result.task.pk,
        )
        payload = _task_payload(task, include_items=True, viewer=cast(User, request.user))
        payload["idempotency_replayed"] = result.replayed
        return Response(payload)
