"""Transactional use cases for the offboarding workflow."""

from __future__ import annotations

import copy
import hashlib
import json
import math
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from typing import Any

from django.core.exceptions import PermissionDenied, ValidationError
from django.db import IntegrityError, transaction
from django.db.models import Exists, OuterRef, Q, QuerySet, Subquery
from django.utils import timezone

from apps.accounts.authorization import (
    active_assignments,
    has_effective_role,
    has_global_authority,
    has_permission,
)
from apps.accounts.models import (
    PEOPLE_DEPARTMENT_ROLE_CODE,
    PEOPLE_DEPARTMENT_ROLE_CODES,
    RoleAssignment,
    User,
)
from apps.integrations.senior.dto import EmployeeDetail
from apps.integrations.senior.exceptions import SeniorContractError
from apps.integrations.senior.repository import SeniorRepository
from apps.notifications.triggers import (
    notify_process_cancelled,
    notify_process_reopened,
    notify_task_assigned,
)
from apps.sectors.models import (
    SectorResponsible,
    SectorScope,
    ValidationSector,
)
from apps.templates_engine.models import (
    ChecklistResponseType,
    ChecklistTemplateItem,
    ChecklistTemplateVersion,
    ValidationGroupVersion,
    VersionStatus,
)
from config.middleware import correlation_id

from .models import (
    OPEN_TASK_STATUSES,
    DraftOverrideAction,
    EmployeeSnapshot,
    OffboardingProcess,
    ProcessActionIdempotency,
    ProcessAuditEvent,
    ProcessChecklistItem,
    ProcessEventType,
    ProcessSectorOverride,
    ProcessSectorTask,
    ProcessStatus,
    ProcessTaskGroupSource,
    ProcessValidationGroup,
    SectorTaskStatus,
)
from .readiness import closing_blockers, evaluate_process_readiness

PROCESS_OPENED_DESCRIPTION = "Abertura explícita de processo demissional por ator autorizado."
DRAFT_SELECTION_DESCRIPTION = "Seleção de grupos e ajustes por ator autorizado."
PROCESS_STARTED_DESCRIPTION = "Início explícito e idempotente por ator autorizado."
SECTOR_TASK_STARTED_DESCRIPTION = "Início explícito da análise por ator autorizado."
SECTOR_TASK_COMPLETED_DESCRIPTION = "Conclusão explícita da validação pelo setor."
PROCESS_RELEASED_DESCRIPTION = "Liberação explícita para rescisão por ator autorizado."
PROCESSING_REGISTERED_DESCRIPTION = "Registro declarado do processamento da rescisão no Senior."
PROCESS_CLOSED_DESCRIPTION = "Encerramento formal do processo por ator autorizado."
PROCESS_CANCELLED_DESCRIPTION = "Cancelamento justificado do processo por ator autorizado."
PROCESS_REOPENED_DESCRIPTION = "Reabertura justificada do processo por SuperAdmin."
SECTOR_TASK_CANCELLED_DESCRIPTION = "Tarefa cancelada junto com o processo."
SECTOR_TASK_REOPENED_DESCRIPTION = "Tarefa devolvida ao setor pela reabertura do processo."
START_ACTION = "START"
RELEASE_ACTION = "RELEASE"
PROCESSING_ACTION = "PROCESSING"
CLOSE_ACTION = "CLOSE"
CANCEL_ACTION = "CANCEL"
REOPEN_ACTION = "REOPEN"

#: Estados em que a tarefa continua visível para o responsável do setor. Depois
#: da liberação ela é só leitura — `lock_sector_task_and_authority` exige
#: processo iniciado para qualquer movimento — e o cancelamento a retira da
#: lista.
TASK_VISIBLE_PROCESS_STATUSES = (
    ProcessStatus.STARTED,
    ProcessStatus.RELEASED,
    ProcessStatus.PROCESSED,
    ProcessStatus.CLOSED,
)

#: Estados em que uma pendência já existente ainda pode ser resolvida. A tarefa
#: congela na liberação, mas a pendência precisa poder terminar: o encerramento
#: formal exige que nada continue em curso, e sem isto ele seria inalcançável.
PENDING_RESOLUTION_PROCESS_STATUSES = (
    ProcessStatus.STARTED,
    ProcessStatus.RELEASED,
    ProcessStatus.PROCESSED,
)

#: Estados formais que já saíram das mãos dos setores e vão para `Concluídos`.
FORMALLY_ADVANCED_PROCESS_STATUSES = (
    ProcessStatus.RELEASED,
    ProcessStatus.PROCESSED,
    ProcessStatus.CLOSED,
)


def _require_people_department_role(
    actor: User,
    *,
    company_code: int,
    branch_code: int,
) -> None:
    if not has_effective_role(
        actor,
        PEOPLE_DEPARTMENT_ROLE_CODE,
        company_code=company_code,
        branch_code=branch_code,
    ):
        raise PermissionDenied(
            "O ator não possui o papel DP vigente para a empresa e a filial informadas."
        )


def _required_text(value: str, field: str, message: str) -> str:
    normalized = value.strip()
    if not normalized:
        raise ValidationError({field: message})
    return normalized


def _employee_key(
    company_code: int,
    branch_code: int,
    employee_type_code: int,
    registration: int,
) -> str:
    return f"{company_code}:{branch_code}:{employee_type_code}:{registration}"


def _aware_datetime(value: datetime | None) -> datetime | None:
    if value is None or timezone.is_aware(value):
        return value
    return timezone.make_aware(value)


def _validate_employee_identity(
    employee: EmployeeDetail,
    *,
    company_code: int,
    branch_code: int,
    employee_type_code: int,
    registration: int,
) -> None:
    returned_key = (
        employee.company,
        employee.branch,
        employee.employee_type,
        employee.registration,
    )
    expected_key = (company_code, branch_code, employee_type_code, registration)
    if returned_key != expected_key:
        raise SeniorContractError("O Senior retornou uma chave de colaborador divergente.")


def _lock_actor(actor: User) -> User:
    try:
        return User.objects.select_for_update().get(pk=actor.pk)
    except User.DoesNotExist as exc:
        raise PermissionDenied("O ator não está mais disponível.") from exc


def _lock_people_department_assignments(actor: User) -> None:
    # Materialize without slicing: Oracle cannot combine FOR UPDATE with the
    # row limiting generated by first()/exists().
    list(
        RoleAssignment.objects.select_for_update()
        .filter(user=actor, role__code__in=PEOPLE_DEPARTMENT_ROLE_CODES)
        .order_by("pk")
    )


@dataclass(frozen=True, slots=True)
class OpenOffboardingProcessCommand:
    actor: User
    company_code: int
    branch_code: int
    employee_type_code: int
    employee_registration: int
    planned_termination_date: date
    due_date: date
    reason: str
    priority: str
    notes: str = ""


class OpenOffboardingProcessService:
    def __init__(self, *, repository: SeniorRepository | None = None) -> None:
        self._repository = repository or SeniorRepository()

    def execute(self, command: OpenOffboardingProcessCommand) -> OffboardingProcess:
        reason = _required_text(command.reason, "reason", "O motivo é obrigatório.")
        priority = _required_text(
            command.priority,
            "priority",
            "A prioridade é obrigatória.",
        )
        notes = command.notes.strip()

        # Fail before consulting personal data when the actor has no functional
        # authority. The same check is repeated after locking inside the write
        # transaction so revocation and opening have a deterministic winner.
        _require_people_department_role(
            command.actor,
            company_code=command.company_code,
            branch_code=command.branch_code,
        )
        employee = self._repository.get_employee(
            company=command.company_code,
            branch=command.branch_code,
            employee_type=command.employee_type_code,
            registration=command.employee_registration,
        )
        if employee is None:
            raise ValidationError(
                {
                    "employee_registration": (
                        "O colaborador não existe ou deixou de ser elegível no Senior HCM."
                    )
                }
            )
        _validate_employee_identity(
            employee,
            company_code=command.company_code,
            branch_code=command.branch_code,
            employee_type_code=command.employee_type_code,
            registration=command.employee_registration,
        )
        source_queried_at = timezone.now()

        with transaction.atomic():
            actor = _lock_actor(command.actor)
            _lock_people_department_assignments(actor)
            _require_people_department_role(
                actor,
                company_code=command.company_code,
                branch_code=command.branch_code,
            )
            active_employee_key = _employee_key(
                command.company_code,
                command.branch_code,
                command.employee_type_code,
                command.employee_registration,
            )
            existing = list(
                OffboardingProcess.objects.select_for_update()
                .filter(active_employee_key=active_employee_key)
                .order_by("pk")
            )
            if existing:
                raise ValidationError(
                    {
                        "employee_registration": (
                            "Já existe um processo não encerrado para este colaborador."
                        )
                    }
                )

            process = OffboardingProcess(
                status=ProcessStatus.DRAFT,
                company_code=command.company_code,
                branch_code=command.branch_code,
                employee_type_code=command.employee_type_code,
                employee_registration=command.employee_registration,
                active_employee_key=active_employee_key,
                opened_by=actor,
                planned_termination_date=command.planned_termination_date,
                due_date=command.due_date,
                reason=reason,
                priority=priority,
                notes=notes,
            )
            process.full_clean(exclude={"active_employee_key"})
            try:
                process.save()
            except IntegrityError as exc:
                raise ValidationError(
                    {
                        "employee_registration": (
                            "Já existe um processo não encerrado para este colaborador."
                        )
                    }
                ) from exc

            snapshot = EmployeeSnapshot(
                process=process,
                company_code=employee.company,
                branch_code=employee.branch,
                branch_legal_name=employee.legal_name,
                employee_type_code=employee.employee_type,
                employee_type_description=employee.employee_type_description,
                registration=employee.registration,
                employee_name=employee.name,
                masked_cpf=employee.masked_cpf,
                admission_date=employee.admission_date.date(),
                leave_code=employee.leave_code,
                leave_description=employee.leave_description,
                leave_date=employee.leave_date.date() if employee.leave_date else None,
                job_structure_code=employee.job_structure,
                job_code=employee.job_code,
                job_description=employee.job_description,
                cost_center_code=employee.cost_center,
                cost_center_description=employee.cost_center_description,
                source_updated_at=_aware_datetime(employee.source_updated_at),
                source_queried_at=source_queried_at,
            )
            snapshot.full_clean()
            snapshot.save()

            ProcessAuditEvent.objects.create(
                process=process,
                event_type=ProcessEventType.OPENED,
                actor=actor,
                description=PROCESS_OPENED_DESCRIPTION,
                data={
                    "status": ProcessStatus.DRAFT,
                    "company_code": command.company_code,
                    "branch_code": command.branch_code,
                    "employee_type_code": command.employee_type_code,
                    "employee_registration": command.employee_registration,
                    "planned_termination_date": command.planned_termination_date.isoformat(),
                    "due_date": command.due_date.isoformat(),
                    "priority": priority,
                },
                correlation_id=correlation_id.get(),
            )
            return process


class IdempotencyConflict(Exception):
    """The same idempotency key was reused for a different request."""


@dataclass(frozen=True, slots=True)
class DraftSectorOverrideValue:
    sector_id: int
    action: DraftOverrideAction
    reason: str
    template_version_id: int | None = None
    is_required: bool = True
    blocks_process: bool = True
    due_hours_override: int | None = None


@dataclass(frozen=True, slots=True)
class UpdateDraftSelectionCommand:
    actor: User
    process_uuid: str
    expected_version: int
    group_version_ids: tuple[int, ...]
    overrides: tuple[DraftSectorOverrideValue, ...] = ()


@dataclass(frozen=True, slots=True)
class ResolvedSectorPlan:
    sector: ValidationSector
    template_version: ChecklistTemplateVersion
    is_required: bool
    blocks_process: bool
    sla_hours: int
    group_selections: tuple[ProcessValidationGroup, ...]
    override: ProcessSectorOverride | None = None


@dataclass(frozen=True, slots=True)
class StartOffboardingProcessCommand:
    actor: User
    process_uuid: str
    expected_version: int
    idempotency_key: str


@dataclass(frozen=True, slots=True)
class StartOffboardingProcessResult:
    process: OffboardingProcess
    tasks: tuple[ProcessSectorTask, ...]
    replayed: bool


@dataclass(frozen=True, slots=True)
class DraftProcessContext:
    process: OffboardingProcess
    plans: tuple[ResolvedSectorPlan, ...]
    blockers: tuple[str, ...]


def _lock_actor_and_dp_assignment(actor: User) -> User:
    try:
        locked_actor = User.objects.select_for_update().get(pk=actor.pk)
    except User.DoesNotExist as exc:
        raise PermissionDenied("O ator não está mais disponível.") from exc
    _lock_people_department_assignments(locked_actor)
    return locked_actor


def _lock_process(process_uuid: str) -> OffboardingProcess:
    try:
        return (
            OffboardingProcess.objects.select_for_update()
            .select_related("employee_snapshot")
            .get(uuid=process_uuid)
        )
    except (ValueError, ValidationError) as exc:
        raise OffboardingProcess.DoesNotExist from exc


def _require_process_dp(actor: User, process: OffboardingProcess) -> None:
    _require_people_department_role(
        actor,
        company_code=process.company_code,
        branch_code=process.branch_code,
    )


def _scope_filter(process: OffboardingProcess) -> Q:
    return (
        Q(scope_type="GLOBAL")
        | Q(scope_type="COMPANY", company_code=process.company_code)
        | Q(
            scope_type="BRANCH",
            company_code=process.company_code,
            branch_code=process.branch_code,
        )
    )


def _applicable_sector_ids(
    process: OffboardingProcess,
    sector_ids: set[int],
    *,
    lock: bool,
) -> set[int]:
    scopes = SectorScope.objects.filter(sector_id__in=sector_ids).filter(_scope_filter(process))
    if lock:
        scopes = scopes.select_for_update()
    return set(scopes.values_list("sector_id", flat=True))


def _validate_override_values(
    overrides: tuple[DraftSectorOverrideValue, ...],
) -> tuple[DraftSectorOverrideValue, ...]:
    by_sector: dict[int, DraftSectorOverrideValue] = {}
    for index, value in enumerate(overrides):
        if value.sector_id <= 0:
            raise ValidationError({f"overrides.{index}.sector_id": "Selecione um setor válido."})
        if value.sector_id in by_sector:
            raise ValidationError({"overrides": "O mesmo setor possui mais de um ajuste."})
        reason = value.reason.strip()
        if not reason:
            raise ValidationError(
                {f"overrides.{index}.reason": "A justificativa do ajuste é obrigatória."}
            )
        if value.due_hours_override is not None and value.due_hours_override <= 0:
            raise ValidationError(
                {f"overrides.{index}.due_hours_override": "O prazo deve ser maior que zero."}
            )
        if value.action == DraftOverrideAction.INCLUDE and value.template_version_id is None:
            raise ValidationError(
                {
                    f"overrides.{index}.template_version_id": (
                        "A inclusão exige uma versão de template."
                    )
                }
            )
        if value.action == DraftOverrideAction.EXCLUDE and value.template_version_id is not None:
            raise ValidationError(
                {
                    f"overrides.{index}.template_version_id": (
                        "A remoção não deve informar um template."
                    )
                }
            )
        by_sector[value.sector_id] = DraftSectorOverrideValue(
            sector_id=value.sector_id,
            action=value.action,
            reason=reason,
            template_version_id=value.template_version_id,
            is_required=value.is_required,
            blocks_process=value.blocks_process,
            due_hours_override=value.due_hours_override,
        )
    return tuple(by_sector[sector_id] for sector_id in sorted(by_sector))


def _group_versions_for_selection(
    group_version_ids: tuple[int, ...],
) -> tuple[ValidationGroupVersion, ...]:
    unique_ids = set(group_version_ids)
    if not unique_ids:
        raise ValidationError({"group_version_ids": "Selecione ao menos um grupo de validação."})
    versions = tuple(
        ValidationGroupVersion.objects.select_for_update()
        .filter(pk__in=unique_ids)
        .select_related("group")
        .prefetch_related("sector_rules")
        .order_by("group_id", "version_number")
    )
    if len(versions) != len(unique_ids):
        raise ValidationError({"group_version_ids": "Um dos grupos selecionados não existe."})
    group_ids = {version.group_id for version in versions}
    if len(group_ids) != len(versions):
        raise ValidationError({"group_version_ids": "Selecione somente uma versão de cada grupo."})
    for version in versions:
        if (
            version.status != VersionStatus.PUBLISHED
            or not version.group.is_active
            or version.group.current_version_id != version.pk
        ):
            raise ValidationError(
                {
                    "group_version_ids": (
                        f"O grupo {version.group.code} não está em uma versão vigente publicada."
                    )
                }
            )
    return versions


class UpdateDraftSelectionService:
    @transaction.atomic
    def execute(self, command: UpdateDraftSelectionCommand) -> OffboardingProcess:
        process = _lock_process(command.process_uuid)
        _require_process_dp(command.actor, process)
        if process.status != ProcessStatus.DRAFT:
            raise ValidationError("Somente um rascunho pode ter sua seleção alterada.")
        if process.version != command.expected_version:
            raise ValidationError("O processo foi alterado por outra sessão. Recarregue a página.")

        group_versions = _group_versions_for_selection(command.group_version_ids)
        override_values = _validate_override_values(command.overrides)
        group_sector_ids = {
            rule.sector_id for version in group_versions for rule in version.sector_rules.all()
        }
        for value in override_values:
            if (
                value.action == DraftOverrideAction.EXCLUDE
                and value.sector_id not in group_sector_ids
            ):
                raise ValidationError(
                    {
                        "overrides": (
                            "Um setor só pode ser removido quando estiver presente "
                            "nos grupos selecionados."
                        )
                    }
                )
            if value.action == DraftOverrideAction.INCLUDE and value.sector_id in group_sector_ids:
                raise ValidationError(
                    {
                        "overrides": (
                            "Um setor já fornecido pelo grupo não pode ser incluído "
                            "novamente de forma manual."
                        )
                    }
                )

        sector_ids = group_sector_ids | {value.sector_id for value in override_values}
        sectors = {
            sector.pk: sector
            for sector in ValidationSector.objects.select_for_update()
            .filter(pk__in=sector_ids)
            .order_by("pk")
        }
        if sectors.keys() != sector_ids:
            raise ValidationError({"overrides": "Um dos setores informados não existe."})

        included_template_ids = {
            value.template_version_id
            for value in override_values
            if value.template_version_id is not None
        }
        templates = {
            version.pk: version
            for version in ChecklistTemplateVersion.objects.select_for_update()
            .filter(pk__in=included_template_ids)
            .select_related("template")
            .order_by("pk")
        }
        if templates.keys() != included_template_ids:
            raise ValidationError(
                {"overrides": "Uma das versões de template informadas não existe."}
            )

        applicable = _applicable_sector_ids(process, sector_ids, lock=True)
        for value in override_values:
            if value.action != DraftOverrideAction.INCLUDE:
                continue
            sector = sectors[value.sector_id]
            template = templates[value.template_version_id]
            if not sector.is_active or sector.pk not in applicable:
                raise ValidationError(
                    {"overrides": (f"O setor {sector.code} não está ativo no escopo do processo.")}
                )
            if (
                template.status != VersionStatus.PUBLISHED
                or not template.template.is_active
                or template.template.current_version_id != template.pk
            ):
                raise ValidationError(
                    {
                        "overrides": (
                            f"A inclusão de {sector.code} exige o template vigente publicado "
                            "informado."
                        )
                    }
                )

        actor = _lock_actor_and_dp_assignment(command.actor)
        _require_process_dp(actor, process)
        process.selected_groups.all().delete()
        process.sector_overrides.all().delete()
        for group_version in group_versions:
            ProcessValidationGroup.objects.create(
                process=process,
                group_version=group_version,
                selected_by=actor,
            )
        for value in override_values:
            override = ProcessSectorOverride(
                process=process,
                sector=sectors[value.sector_id],
                action=value.action,
                template_version=(
                    templates[value.template_version_id]
                    if value.template_version_id is not None
                    else None
                ),
                is_required=value.is_required,
                blocks_process=value.blocks_process,
                due_hours_override=value.due_hours_override,
                reason=value.reason,
                changed_by=actor,
            )
            override.full_clean()
            override.save()

        process.version += 1
        process.full_clean(exclude={"active_employee_key"})
        process.save(update_fields=("version",))
        ProcessAuditEvent.objects.create(
            process=process,
            event_type=ProcessEventType.DRAFT_SELECTION_UPDATED,
            actor=actor,
            description=DRAFT_SELECTION_DESCRIPTION,
            data={
                "group_version_ids": [version.pk for version in group_versions],
                "overrides": [
                    {
                        "sector_id": value.sector_id,
                        "action": value.action,
                        "reason": value.reason,
                    }
                    for value in override_values
                ],
                "process_version": process.version,
            },
            correlation_id=correlation_id.get(),
        )
        return process


def _selected_configuration(
    process: OffboardingProcess,
    *,
    lock: bool,
) -> tuple[
    tuple[ProcessValidationGroup, ...],
    tuple[ProcessSectorOverride, ...],
]:
    selections = ProcessValidationGroup.objects.filter(process=process)
    if lock:
        selections = selections.select_for_update()
    selected = tuple(
        selections.select_related("group_version__group")
        .prefetch_related(
            "group_version__sector_rules__sector__scopes",
            "group_version__sector_rules__template_version__template",
        )
        .order_by("group_version__group_id", "pk")
    )
    overrides = ProcessSectorOverride.objects.filter(process=process)
    if lock:
        overrides = overrides.select_for_update()
    adjusted = tuple(
        overrides.select_related(
            "sector",
            "template_version__template",
        ).order_by("sector_id", "pk")
    )
    return selected, adjusted


def resolve_draft_sector_plans(
    process: OffboardingProcess,
    *,
    lock: bool = False,
) -> tuple[ResolvedSectorPlan, ...]:
    selected, overrides = _selected_configuration(process, lock=lock)
    rules = [
        (selection, rule)
        for selection in selected
        for rule in selection.group_version.sector_rules.all()
    ]
    sector_ids = {rule.sector_id for _, rule in rules} | {
        override.sector_id for override in overrides
    }
    locked_sectors: dict[int, ValidationSector] = {}
    locked_templates: dict[int, ChecklistTemplateVersion] = {}
    if lock:
        locked_sectors = {
            sector.pk: sector
            for sector in ValidationSector.objects.select_for_update()
            .filter(pk__in=sector_ids)
            .order_by("pk")
        }
        template_ids = {rule.template_version_id for _, rule in rules} | {
            override.template_version_id
            for override in overrides
            if override.template_version_id is not None
        }
        locked_templates = {
            version.pk: version
            for version in ChecklistTemplateVersion.objects.select_for_update()
            .filter(pk__in=template_ids)
            .select_related("template")
            .order_by("pk")
        }
    applicable = _applicable_sector_ids(process, sector_ids, lock=lock)
    plans: dict[int, ResolvedSectorPlan] = {}
    for selection, rule in rules:
        if rule.sector_id not in applicable:
            continue
        sector = locked_sectors.get(rule.sector_id, rule.sector)
        template_version = locked_templates.get(
            rule.template_version_id,
            rule.template_version,
        )
        sla_hours = (
            rule.due_hours_override
            or template_version.default_due_hours
            or sector.default_due_hours
        )
        current = plans.get(rule.sector_id)
        if current is not None and current.template_version.pk != template_version.pk:
            raise ValidationError(
                {
                    "group_version_ids": (
                        f"Os grupos selecionados usam templates diferentes para {sector.code}."
                    )
                }
            )
        plans[rule.sector_id] = ResolvedSectorPlan(
            sector=sector,
            template_version=template_version,
            is_required=rule.is_required or (current.is_required if current else False),
            blocks_process=rule.blocks_process or (current.blocks_process if current else False),
            sla_hours=min(sla_hours, current.sla_hours) if current else sla_hours,
            group_selections=((*current.group_selections, selection) if current else (selection,)),
        )

    for override in overrides:
        if override.action == DraftOverrideAction.EXCLUDE:
            plans.pop(override.sector_id, None)
            continue
        if override.sector_id not in applicable or override.template_version is None:
            continue
        assert override.template_version_id is not None
        sector = locked_sectors.get(override.sector_id, override.sector)
        template_version = locked_templates.get(
            override.template_version_id,
            override.template_version,
        )
        plans[override.sector_id] = ResolvedSectorPlan(
            sector=sector,
            template_version=template_version,
            is_required=override.is_required,
            blocks_process=override.blocks_process,
            sla_hours=(
                override.due_hours_override
                or template_version.default_due_hours
                or sector.default_due_hours
            ),
            group_selections=(),
            override=override,
        )
    return tuple(sorted(plans.values(), key=lambda plan: plan.sector.pk or 0))


def _effective_responsible_sector_ids(
    process: OffboardingProcess,
    sector_ids: set[int],
    *,
    at: datetime,
    lock: bool,
) -> set[int]:
    responsibilities = (
        SectorResponsible.objects.filter(
            sector_id__in=sector_ids,
            sector__is_active=True,
            user__is_active=True,
            is_active=True,
            valid_from__lte=at,
        )
        .filter(Q(valid_until__isnull=True) | Q(valid_until__gt=at))
        .order_by("sector_id", "user_id", "pk")
    )
    if lock:
        responsibilities = responsibilities.select_for_update()
    rows = list(responsibilities.values_list("sector_id", "user_id"))
    if lock:
        user_ids = sorted({user_id for _, user_id in rows})
        list(User.objects.select_for_update().filter(pk__in=user_ids).order_by("pk"))
    return {sector_id for sector_id, _ in rows}


def draft_blockers(
    process: OffboardingProcess,
    plans: tuple[ResolvedSectorPlan, ...],
    *,
    at: datetime | None = None,
    lock: bool = False,
) -> tuple[str, ...]:
    instant = at or timezone.now()
    blockers: list[str] = []
    if not process.selected_groups.exists():
        blockers.append("Selecione ao menos um grupo de validação.")
    if not plans or not any(plan.is_required for plan in plans):
        blockers.append("O rascunho precisa possuir ao menos um setor obrigatório.")
    required_sector_ids = {plan.sector.pk for plan in plans if plan.is_required}
    effective = _effective_responsible_sector_ids(
        process,
        required_sector_ids,
        at=instant,
        lock=lock,
    )
    for plan in plans:
        if not plan.sector.is_active:
            blockers.append(f"O setor {plan.sector.code} está inativo.")
        if not plan.template_version.template.is_active or plan.template_version.status not in {
            VersionStatus.PUBLISHED,
            VersionStatus.RETIRED,
        }:
            blockers.append(f"O setor {plan.sector.code} não possui template histórico válido.")
        if plan.is_required and plan.sector.pk not in effective:
            blockers.append(
                f"O setor obrigatório {plan.sector.code} não possui responsável vigente."
            )
    return tuple(blockers)


class GetDraftProcessContextService:
    def execute(self, actor: User, process_uuid: str) -> DraftProcessContext:
        try:
            process = (
                OffboardingProcess.objects.select_related(
                    "opened_by",
                    "employee_snapshot",
                    "started_by",
                )
                .prefetch_related("sector_tasks__checklist_items")
                .get(uuid=process_uuid)
            )
        except (ValueError, ValidationError) as exc:
            raise OffboardingProcess.DoesNotExist from exc
        _require_process_dp(actor, process)
        plans = resolve_draft_sector_plans(process)
        blockers = draft_blockers(process, plans) if process.status == ProcessStatus.DRAFT else ()
        return DraftProcessContext(
            process=process,
            plans=plans,
            blockers=blockers,
        )


def _start_request_hash(expected_version: int) -> str:
    canonical = json.dumps(
        {"expected_version": expected_version},
        separators=(",", ":"),
        sort_keys=True,
    ).encode()
    return hashlib.sha256(canonical).hexdigest()


def _process_due_at(process: OffboardingProcess) -> datetime:
    naive = datetime.combine(process.due_date, time.max)
    return timezone.make_aware(naive, timezone.get_current_timezone())


class StartOffboardingProcessService:
    @transaction.atomic
    def execute(
        self,
        command: StartOffboardingProcessCommand,
    ) -> StartOffboardingProcessResult:
        idempotency_key = command.idempotency_key.strip()
        if not idempotency_key:
            raise ValidationError({"idempotency_key": "Informe a chave de idempotência."})
        if len(idempotency_key) > 100:
            raise ValidationError(
                {"idempotency_key": "A chave de idempotência aceita até 100 caracteres."}
            )

        process = _lock_process(command.process_uuid)
        _require_process_dp(command.actor, process)
        request_hash = _start_request_hash(command.expected_version)
        previous_rows = list(
            ProcessActionIdempotency.objects.select_for_update()
            .filter(
                process=process,
                action=START_ACTION,
                idempotency_key=idempotency_key,
            )
            .order_by("pk")
        )
        previous = previous_rows[0] if previous_rows else None
        if previous is not None:
            actor = _lock_actor_and_dp_assignment(command.actor)
            _require_process_dp(actor, process)
            if previous.request_hash != request_hash or previous.actor_id != actor.pk:
                raise IdempotencyConflict(
                    "A chave de idempotência já foi usada com outro conteúdo."
                )
            tasks = tuple(
                ProcessSectorTask.objects.filter(process=process)
                .select_related("sector", "template_version")
                .order_by("sector_code_snapshot")
            )
            return StartOffboardingProcessResult(
                process=process,
                tasks=tasks,
                replayed=True,
            )

        if process.status != ProcessStatus.DRAFT:
            raise ValidationError("Somente um rascunho pode ser iniciado.")
        if process.version != command.expected_version:
            raise ValidationError("O processo foi alterado por outra sessão. Recarregue a página.")

        started_at = timezone.now()
        plans = resolve_draft_sector_plans(process, lock=True)
        blockers = draft_blockers(
            process,
            plans,
            at=started_at,
            lock=True,
        )
        if blockers:
            raise ValidationError({"start": list(blockers)})

        actor = _lock_actor_and_dp_assignment(command.actor)
        _require_process_dp(actor, process)
        task_rows: list[ProcessSectorTask] = []
        process_limit = _process_due_at(process)
        for plan in plans:
            due_at = min(
                process_limit,
                started_at + timedelta(hours=plan.sla_hours),
            )
            task = ProcessSectorTask.objects.create(
                process=process,
                sector=plan.sector,
                template_version=plan.template_version,
                status=SectorTaskStatus.PENDING,
                is_required=plan.is_required,
                blocks_process=plan.blocks_process,
                sector_code_snapshot=str(plan.sector.pk),
                sector_name_snapshot=plan.sector.name,
                template_code_snapshot=str(plan.template_version.template_id),
                template_version_snapshot=plan.template_version.version_number,
                sla_hours_snapshot=plan.sla_hours,
                due_at=due_at,
                started_at=started_at,
            )
            task_rows.append(task)
            for selection in plan.group_selections:
                ProcessTaskGroupSource.objects.create(
                    task=task,
                    selected_group=selection,
                )
            template_items = (
                ChecklistTemplateItem.objects.select_for_update()
                .filter(template_version=plan.template_version)
                .order_by("display_order", "pk")
            )
            for item in template_items:
                ProcessChecklistItem.objects.create(
                    task=task,
                    source_item=item,
                    code_snapshot=item.code,
                    question_snapshot=item.question,
                    response_type_snapshot=item.response_type,
                    is_required=item.is_required,
                    blocks_process=item.blocks_process,
                    requires_evidence=item.requires_evidence,
                    allows_pending=item.allows_pending,
                    display_order=item.display_order,
                    config_snapshot=copy.deepcopy(item.config),
                )

        process.status = ProcessStatus.STARTED
        process.started_at = started_at
        process.started_by = actor
        process.version += 1
        process.full_clean(exclude={"active_employee_key"})
        process.save(
            update_fields=(
                "status",
                "started_at",
                "started_by",
                "version",
            )
        )
        ProcessAuditEvent.objects.create(
            process=process,
            event_type=ProcessEventType.STARTED,
            actor=actor,
            description=PROCESS_STARTED_DESCRIPTION,
            data={
                "status": ProcessStatus.STARTED,
                "task_count": len(task_rows),
                "required_task_count": sum(task.is_required for task in task_rows),
                "group_version_ids": [
                    selection.group_version_id
                    for selection in process.selected_groups.all().order_by("group_version_id")
                ],
                "idempotency_key_hash": hashlib.sha256(idempotency_key.encode()).hexdigest(),
                "process_version": process.version,
            },
            correlation_id=correlation_id.get(),
        )
        ProcessActionIdempotency.objects.create(
            process=process,
            action=START_ACTION,
            idempotency_key=idempotency_key,
            request_hash=request_hash,
            response={
                "process_uuid": str(process.uuid),
                "status": process.status,
                "version": process.version,
                "task_count": len(task_rows),
            },
            actor=actor,
        )
        # Aviso na mesma transação do início (ADR-049): setor sem tarefa não
        # recebe nada e tarefa criada não fica sem aviso.
        for task in task_rows:
            notify_task_assigned(task)
        return StartOffboardingProcessResult(
            process=process,
            tasks=tuple(task_rows),
            replayed=False,
        )


@dataclass(frozen=True, slots=True)
class ChecklistAnswerValue:
    item_id: int
    value: Any


@dataclass(frozen=True, slots=True)
class StartSectorTaskCommand:
    actor: User
    task_id: int
    expected_version: int
    idempotency_key: str


@dataclass(frozen=True, slots=True)
class CompleteSectorTaskCommand:
    actor: User
    task_id: int
    expected_version: int
    idempotency_key: str
    answers: tuple[ChecklistAnswerValue, ...]
    notes: str = ""


@dataclass(frozen=True, slots=True)
class SectorTaskMutationResult:
    task: ProcessSectorTask
    replayed: bool


def sector_tasks_for_actor(actor: User) -> QuerySet[ProcessSectorTask]:
    """Return all tasks for SuperAdmin or those covered by responsibility."""

    if not actor.is_active:
        return ProcessSectorTask.objects.none()
    if has_global_authority(actor):
        return ProcessSectorTask.objects.all()
    instant = timezone.now()
    responsibility = SectorResponsible.objects.filter(
        sector_id=OuterRef("sector_id"),
        user=actor,
        is_active=True,
        valid_from__lte=instant,
    ).filter(Q(valid_until__isnull=True) | Q(valid_until__gt=instant))
    scope = SectorScope.objects.filter(sector_id=OuterRef("sector_id")).filter(
        Q(scope_type="GLOBAL")
        | Q(
            scope_type="COMPANY",
            company_code=OuterRef("process__company_code"),
        )
        | Q(
            scope_type="BRANCH",
            company_code=OuterRef("process__company_code"),
            branch_code=OuterRef("process__branch_code"),
        )
    )
    return (
        ProcessSectorTask.objects.filter(
            process__status__in=TASK_VISIBLE_PROCESS_STATUSES,
            sector__is_active=True,
        )
        .annotate(
            has_responsibility=Exists(responsibility),
            has_scope=Exists(scope),
        )
        .filter(has_responsibility=True, has_scope=True)
    )


def processes_for_actor(actor: User) -> QuerySet[OffboardingProcess]:
    """Return processes coordinated by the actor's current DP scopes."""

    if not actor.is_active:
        return OffboardingProcess.objects.none()
    if has_global_authority(actor):
        return OffboardingProcess.objects.all()

    assignments = active_assignments(actor).filter(
        role__code__in=PEOPLE_DEPARTMENT_ROLE_CODES,
    )
    scope_filter = Q(pk__in=[])
    for assignment in assignments.only(
        "scope_type",
        "company_code",
        "branch_code",
    ):
        if assignment.scope_type == "GLOBAL":
            return OffboardingProcess.objects.all()
        if assignment.scope_type == "COMPANY":
            scope_filter |= Q(company_code=assignment.company_code)
        elif assignment.scope_type == "BRANCH":
            scope_filter |= Q(
                company_code=assignment.company_code,
                branch_code=assignment.branch_code,
            )
    return OffboardingProcess.objects.filter(scope_filter)


def completed_processes_for_actor(actor: User) -> QuerySet[OffboardingProcess]:
    """Return formally closed processes or those with every sector task completed."""

    tasks = ProcessSectorTask.objects.filter(process_id=OuterRef("pk"))
    unfinished_tasks = tasks.filter(status__in=OPEN_TASK_STATUSES)
    last_task_completion = (
        tasks.filter(completed_at__isnull=False)
        .order_by("-completed_at", "-pk")
        .values("completed_at")[:1]
    )
    return (
        processes_for_actor(actor)
        .annotate(
            has_sector_tasks=Exists(tasks),
            has_unfinished_tasks=Exists(unfinished_tasks),
            completion_at=Subquery(last_task_completion),
        )
        .filter(
            Q(status__in=FORMALLY_ADVANCED_PROCESS_STATUSES)
            | Q(
                status=ProcessStatus.STARTED,
                has_sector_tasks=True,
                has_unfinished_tasks=False,
            )
        )
    )


def open_processes_for_actor(actor: User) -> QuerySet[OffboardingProcess]:
    """Return started processes with at least one unfinished sector task."""

    unfinished_tasks = ProcessSectorTask.objects.filter(
        process_id=OuterRef("pk"),
        status__in=OPEN_TASK_STATUSES,
    )
    return (
        processes_for_actor(actor)
        .annotate(has_unfinished_tasks=Exists(unfinished_tasks))
        .filter(
            status=ProcessStatus.STARTED,
            has_unfinished_tasks=True,
        )
    )


def _scope_covers_process(scope: SectorScope, process: OffboardingProcess) -> bool:
    return (
        scope.scope_type == "GLOBAL"
        or (scope.scope_type == "COMPANY" and scope.company_code == process.company_code)
        or (
            scope.scope_type == "BRANCH"
            and scope.company_code == process.company_code
            and scope.branch_code == process.branch_code
        )
    )


def lock_sector_task_and_authority(
    *,
    actor: User,
    task_id: int,
    at: datetime,
    allow_process_coordinator: bool = False,
    allowed_process_statuses: tuple[str, ...] = (ProcessStatus.STARTED,),
) -> tuple[User, OffboardingProcess, ProcessSectorTask]:
    try:
        process_id = ProcessSectorTask.objects.values_list("process_id", flat=True).get(pk=task_id)
    except ProcessSectorTask.DoesNotExist as exc:
        raise ProcessSectorTask.DoesNotExist from exc
    process = OffboardingProcess.objects.select_for_update().get(pk=process_id)
    task = ProcessSectorTask.objects.select_for_update().get(pk=task_id, process=process)
    sector = ValidationSector.objects.select_for_update().get(pk=task.sector_id)
    responsibilities = list(
        SectorResponsible.objects.select_for_update()
        .filter(
            sector=sector,
            user_id=actor.pk,
            is_active=True,
            valid_from__lte=at,
        )
        .filter(Q(valid_until__isnull=True) | Q(valid_until__gt=at))
        .order_by("pk")
    )
    try:
        locked_actor = User.objects.select_for_update().get(pk=actor.pk)
    except User.DoesNotExist as exc:
        raise PermissionDenied("O ator não está mais disponível.") from exc
    scopes = tuple(SectorScope.objects.filter(sector=sector).order_by("pk"))
    has_sector_authority = bool(responsibilities) and any(
        _scope_covers_process(scope, process) for scope in scopes
    )
    has_coordinator_authority = False
    if allow_process_coordinator and not has_global_authority(locked_actor):
        list(RoleAssignment.objects.select_for_update().filter(user=locked_actor).order_by("pk"))
        has_coordinator_authority = has_effective_role(
            locked_actor,
            PEOPLE_DEPARTMENT_ROLE_CODE,
            company_code=process.company_code,
            branch_code=process.branch_code,
        )
    has_task_authority = (
        has_global_authority(locked_actor) or has_sector_authority or has_coordinator_authority
    )
    if not locked_actor.is_active or not sector.is_active or not has_task_authority:
        raise PermissionDenied(
            "O ator não possui responsabilidade vigente pelo setor no escopo do processo."
        )
    if process.status not in allowed_process_statuses:
        if allowed_process_statuses == (ProcessStatus.STARTED,):
            raise ValidationError("A tarefa só pode ser movimentada em processo iniciado.")
        raise ValidationError("O processo não admite mais movimento nesta pendência.")
    return locked_actor, process, task


def _task_action(prefix: str, task_id: int) -> str:
    action = f"{prefix}:{task_id}"
    if len(action) > 30:
        raise ValidationError("O identificador da tarefa excede o contrato de idempotência.")
    return action


def _validated_idempotency_key(value: str) -> str:
    key = value.strip()
    if not key:
        raise ValidationError({"idempotency_key": "Informe a chave de idempotência."})
    if len(key) > 100:
        raise ValidationError(
            {"idempotency_key": "A chave de idempotência aceita até 100 caracteres."}
        )
    return key


def _canonical_hash(payload: dict[str, Any]) -> str:
    canonical = json.dumps(
        payload,
        separators=(",", ":"),
        sort_keys=True,
        ensure_ascii=False,
    ).encode()
    return hashlib.sha256(canonical).hexdigest()


def _task_idempotency_replay(
    *,
    process: OffboardingProcess,
    task: ProcessSectorTask,
    actor: User,
    action: str,
    key: str,
    request_hash: str,
) -> SectorTaskMutationResult | None:
    previous_rows = list(
        ProcessActionIdempotency.objects.select_for_update()
        .filter(process=process, action=action, idempotency_key=key)
        .order_by("pk")
    )
    if not previous_rows:
        return None
    previous = previous_rows[0]
    if previous.actor_id != actor.pk or previous.request_hash != request_hash:
        raise IdempotencyConflict("A chave de idempotência já foi usada com outro conteúdo.")
    task.refresh_from_db()
    return SectorTaskMutationResult(task=task, replayed=True)


def _record_task_idempotency(
    *,
    process: OffboardingProcess,
    task: ProcessSectorTask,
    actor: User,
    action: str,
    key: str,
    request_hash: str,
) -> None:
    ProcessActionIdempotency.objects.create(
        process=process,
        action=action,
        idempotency_key=key,
        request_hash=request_hash,
        response={
            "task_id": task.pk,
            "status": task.status,
            "version": task.version,
        },
        actor=actor,
    )


class StartSectorTaskService:
    @transaction.atomic
    def execute(self, command: StartSectorTaskCommand) -> SectorTaskMutationResult:
        key = _validated_idempotency_key(command.idempotency_key)
        action = _task_action("TSTART", command.task_id)
        request_hash = _canonical_hash(
            {
                "task_id": command.task_id,
                "expected_version": command.expected_version,
            }
        )
        actor, process, task = lock_sector_task_and_authority(
            actor=command.actor,
            task_id=command.task_id,
            at=timezone.now(),
        )
        replay = _task_idempotency_replay(
            process=process,
            task=task,
            actor=actor,
            action=action,
            key=key,
            request_hash=request_hash,
        )
        if replay is not None:
            return replay
        if task.status != SectorTaskStatus.PENDING:
            raise ValidationError("Somente uma tarefa pendente pode entrar em análise.")
        if task.version != command.expected_version:
            raise ValidationError("A tarefa foi alterada por outra sessão. Recarregue a página.")

        task.status = SectorTaskStatus.IN_ANALYSIS
        task.version += 1
        task.full_clean()
        task.save(update_fields=("status", "version"))
        ProcessAuditEvent.objects.create(
            process=process,
            event_type=ProcessEventType.SECTOR_TASK_STARTED,
            actor=actor,
            description=SECTOR_TASK_STARTED_DESCRIPTION,
            data={
                "task_id": task.pk,
                "sector_id": task.sector_id,
                "status": task.status,
                "task_version": task.version,
            },
            correlation_id=correlation_id.get(),
        )
        _record_task_idempotency(
            process=process,
            task=task,
            actor=actor,
            action=action,
            key=key,
            request_hash=request_hash,
        )
        return SectorTaskMutationResult(task=task, replayed=False)


def _choice_values(item: ProcessChecklistItem) -> tuple[str, ...]:
    choices = item.config_snapshot.get("choices")
    if not isinstance(choices, list) or any(not isinstance(value, str) for value in choices):
        raise ValidationError(
            {"answers": f"O item {item.pk} possui configuração histórica inválida."}
        )
    return tuple(value.strip() for value in choices)


def _validated_answer(item: ProcessChecklistItem, value: Any) -> Any:
    response_type = item.response_type_snapshot
    if response_type == ChecklistResponseType.FILE:
        raise ValidationError({"answers": f"O arquivo do item {item.pk} deve ser enviado antes."})
    if response_type == ChecklistResponseType.BOOLEAN:
        if type(value) is not bool:
            raise ValidationError({"answers": f"O item {item.pk} exige resposta sim/não."})
        return value
    if response_type == ChecklistResponseType.TEXT:
        if not isinstance(value, str) or not value.strip():
            raise ValidationError({"answers": f"O item {item.pk} exige texto não vazio."})
        return value.strip()
    if response_type == ChecklistResponseType.NUMBER:
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ValidationError({"answers": f"O item {item.pk} exige um número."})
        if isinstance(value, float) and not math.isfinite(value):
            raise ValidationError({"answers": f"O item {item.pk} exige um número finito."})
        return value
    if response_type == ChecklistResponseType.DATE:
        if not isinstance(value, str):
            raise ValidationError({"answers": f"O item {item.pk} exige uma data ISO."})
        try:
            parsed = date.fromisoformat(value)
        except ValueError as exc:
            raise ValidationError({"answers": f"O item {item.pk} exige uma data ISO."}) from exc
        if parsed.isoformat() != value:
            raise ValidationError({"answers": f"O item {item.pk} exige uma data ISO."})
        return value
    if response_type == ChecklistResponseType.SINGLE_CHOICE:
        choices = _choice_values(item)
        if not isinstance(value, str) or value not in choices:
            raise ValidationError({"answers": f"O item {item.pk} exige uma das opções publicadas."})
        return value
    if response_type == ChecklistResponseType.MULTIPLE_CHOICE:
        choices = _choice_values(item)
        if (
            not isinstance(value, list)
            or any(not isinstance(entry, str) for entry in value)
            or len(set(value)) != len(value)
            or any(entry not in choices for entry in value)
        ):
            raise ValidationError(
                {"answers": f"O item {item.pk} exige opções publicadas sem repetição."}
            )
        if item.is_required and not value:
            raise ValidationError({"answers": f"O item obrigatório {item.pk} exige resposta."})
        return value
    if response_type == ChecklistResponseType.CONFIRMATION:
        if value is not True:
            raise ValidationError({"answers": f"O item {item.pk} exige confirmação positiva."})
        return True
    raise ValidationError({"answers": f"O tipo histórico do item {item.pk} não é suportado."})


def _validated_answers(
    items: tuple[ProcessChecklistItem, ...],
    answers: tuple[ChecklistAnswerValue, ...],
) -> dict[int, Any]:
    from apps.evidence.models import Evidence

    answer_ids = [answer.item_id for answer in answers]
    if len(answer_ids) != len(set(answer_ids)):
        raise ValidationError({"answers": "Um item do checklist foi informado mais de uma vez."})
    items_by_id = {item.pk: item for item in items}
    unknown = set(answer_ids) - items_by_id.keys()
    if unknown:
        raise ValidationError({"answers": "Uma resposta não pertence à tarefa informada."})
    supplied = {answer.item_id: answer.value for answer in answers}
    evidence_item_ids = set(
        Evidence.objects.filter(
            checklist_item_id__in=items_by_id,
            is_active=True,
        ).values_list("checklist_item_id", flat=True)
    )
    for item in items:
        has_answer = item.pk in supplied and supplied[item.pk] is not None
        has_evidence = item.pk in evidence_item_ids
        if item.response_type_snapshot == ChecklistResponseType.FILE:
            if has_answer:
                raise ValidationError(
                    {"answers": f"O item de arquivo {item.pk} não aceita resposta JSON."}
                )
            if item.is_required and not has_evidence:
                raise ValidationError({"answers": f"O item obrigatório {item.pk} exige arquivo."})
            continue
        if item.is_required and not has_answer:
            raise ValidationError({"answers": f"O item obrigatório {item.pk} exige resposta."})
        if item.requires_evidence and (item.is_required or has_answer) and not has_evidence:
            raise ValidationError({"answers": f"O item {item.pk} exige evidência."})
    return {
        item_id: _validated_answer(items_by_id[item_id], value)
        for item_id, value in supplied.items()
        if value is not None
        and items_by_id[item_id].response_type_snapshot != ChecklistResponseType.FILE
    }


class CompleteSectorTaskService:
    @transaction.atomic
    def execute(self, command: CompleteSectorTaskCommand) -> SectorTaskMutationResult:
        key = _validated_idempotency_key(command.idempotency_key)
        notes = command.notes.strip()
        if len(notes) > 4000:
            raise ValidationError({"notes": "As observações aceitam até 4000 caracteres."})
        answer_payload = [
            {"item_id": answer.item_id, "value": answer.value}
            for answer in sorted(command.answers, key=lambda value: value.item_id)
        ]
        action = _task_action("TCOMP", command.task_id)
        request_hash = _canonical_hash(
            {
                "task_id": command.task_id,
                "expected_version": command.expected_version,
                "answers": answer_payload,
                "notes": notes,
            }
        )
        completed_at = timezone.now()
        actor, process, task = lock_sector_task_and_authority(
            actor=command.actor,
            task_id=command.task_id,
            at=completed_at,
        )
        replay = _task_idempotency_replay(
            process=process,
            task=task,
            actor=actor,
            action=action,
            key=key,
            request_hash=request_hash,
        )
        if replay is not None:
            return replay
        if task.status != SectorTaskStatus.IN_ANALYSIS:
            raise ValidationError("Somente uma tarefa em análise pode ser concluída.")
        if task.version != command.expected_version:
            raise ValidationError("A tarefa foi alterada por outra sessão. Recarregue a página.")

        items = tuple(
            ProcessChecklistItem.objects.select_for_update()
            .filter(task=task)
            .order_by("display_order", "pk")
        )
        from apps.pending_items.models import (
            BlockingLevel,
            PendingItem,
            unresolved_blocking_q,
        )

        unresolved_levels = set(
            PendingItem.objects.filter(unresolved_blocking_q(), task=task).values_list(
                "blocking_level", flat=True
            )
        )
        if BlockingLevel.BLOCKING in unresolved_levels:
            raise ValidationError("A tarefa possui pendência bloqueante ainda não regularizada.")
        if BlockingLevel.BLOCKING_UNTIL_DECISION in unresolved_levels:
            raise ValidationError(
                "A tarefa possui pendência de valor à espera da decisão sobre a pretensão."
            )
        normalized = _validated_answers(items, command.answers)
        for item in items:
            if item.pk not in normalized:
                continue
            # Oracle 19c validates JSONField with `IS JSON`, que não aceita um
            # escalar JSON no topo. O envelope mantém booleanos, números,
            # textos e datas dentro de um documento objeto compatível.
            item.response = {"value": normalized[item.pk]}
            item.answered_by = actor
            item.answered_at = completed_at
            item.full_clean(exclude={"config_snapshot"})
            item.save(update_fields=("response", "answered_by", "answered_at"))

        task.status = SectorTaskStatus.COMPLETED
        task.completed_at = completed_at
        task.completed_by = actor
        task.notes = notes
        task.version += 1
        task.full_clean()
        task.save(
            update_fields=(
                "status",
                "completed_at",
                "completed_by",
                "notes",
                "version",
            )
        )
        ProcessAuditEvent.objects.create(
            process=process,
            event_type=ProcessEventType.SECTOR_TASK_COMPLETED,
            actor=actor,
            description=SECTOR_TASK_COMPLETED_DESCRIPTION,
            data={
                "task_id": task.pk,
                "sector_id": task.sector_id,
                "status": task.status,
                "answered_item_ids": sorted(normalized),
                "answered_item_count": len(normalized),
                "task_version": task.version,
            },
            correlation_id=correlation_id.get(),
        )
        _record_task_idempotency(
            process=process,
            task=task,
            actor=actor,
            action=action,
            key=key,
            request_hash=request_hash,
        )
        return SectorTaskMutationResult(task=task, replayed=False)


@dataclass(frozen=True, slots=True)
class ReleaseProcessCommand:
    actor: User
    process_uuid: str
    expected_version: int
    idempotency_key: str
    notes: str = ""
    override_reason: str = ""


@dataclass(frozen=True, slots=True)
class RegisterTerminationProcessingCommand:
    actor: User
    process_uuid: str
    expected_version: int
    idempotency_key: str
    termination_reference: str
    processed_on: date
    notes: str = ""


@dataclass(frozen=True, slots=True)
class CloseProcessCommand:
    actor: User
    process_uuid: str
    expected_version: int
    idempotency_key: str
    notes: str = ""
    override_reason: str = ""


@dataclass(frozen=True, slots=True)
class ProcessTransitionResult:
    process: OffboardingProcess
    replayed: bool


def _validated_notes(value: str, field: str, *, required: bool = False) -> str:
    notes = value.strip()
    if required and not notes:
        raise ValidationError({field: "O texto é obrigatório."})
    if len(notes) > 1000:
        raise ValidationError({field: "O texto aceita até 1000 caracteres."})
    return notes


def _validate_blocker_override(
    *,
    actor: User,
    process: OffboardingProcess,
    blockers: tuple[str, ...],
    override_reason: str,
    field: str,
) -> None:
    """Aplicar a regra do override de impedimentos (ADR-054) a `override_reason`.

    O texto já chegou validado quanto à forma por `_validated_notes`; aqui só
    se decide se ele pode existir. Sem impedimento a justificativa não faz
    sentido e é recusada; com impedimento, só quem tem
    `offboarding.override_process_blockers` no escopo do processo passa, e só
    com justificativa — `DP` puro continua barrado pelos impedimentos, como
    antes.
    """

    if not blockers:
        if override_reason:
            raise ValidationError(
                {"override_reason": "A justificativa só é aceita quando há impedimento."}
            )
        return
    if not has_permission(
        actor,
        "offboarding.override_process_blockers",
        company_code=process.company_code,
        branch_code=process.branch_code,
    ):
        raise ValidationError({field: list(blockers)})
    if not override_reason:
        raise ValidationError(
            {"override_reason": "A justificativa do override de impedimentos é obrigatória."}
        )


def _lock_process_for_transition(
    actor: User,
    process_uuid: str,
) -> tuple[User, OffboardingProcess]:
    """Travar processo e ator, nessa ordem, e revalidar a autoridade depois."""

    process = _lock_process(process_uuid)
    locked_actor = _lock_actor_and_dp_assignment(actor)
    _require_process_dp(locked_actor, process)
    return locked_actor, process


def _process_idempotency_replay(
    *,
    process: OffboardingProcess,
    actor: User,
    action: str,
    key: str,
    request_hash: str,
) -> ProcessTransitionResult | None:
    previous_rows = list(
        ProcessActionIdempotency.objects.select_for_update()
        .filter(process=process, action=action, idempotency_key=key)
        .order_by("pk")
    )
    if not previous_rows:
        return None
    previous = previous_rows[0]
    if previous.actor_id != actor.pk or previous.request_hash != request_hash:
        raise IdempotencyConflict("A chave de idempotência já foi usada com outro conteúdo.")
    return ProcessTransitionResult(process=process, replayed=True)


def _record_process_idempotency(
    *,
    process: OffboardingProcess,
    actor: User,
    action: str,
    key: str,
    request_hash: str,
) -> None:
    ProcessActionIdempotency.objects.create(
        process=process,
        action=action,
        idempotency_key=key,
        request_hash=request_hash,
        response={
            "process_uuid": str(process.uuid),
            "status": process.status,
            "version": process.version,
        },
        actor=actor,
    )


class ReleaseProcessService:
    """Liberar o processo para rescisão (RF-029, RF-030, ADR-012).

    A prontidão é refeita aqui, sob lock: a tela pode ter lido um estado que já
    mudou, e é este cálculo — não o anterior — que decide.
    """

    @transaction.atomic
    def execute(self, command: ReleaseProcessCommand) -> ProcessTransitionResult:
        key = _validated_idempotency_key(command.idempotency_key)
        notes = _validated_notes(command.notes, "notes")
        override_reason = _validated_notes(command.override_reason, "override_reason")
        request_hash = _canonical_hash(
            {
                "expected_version": command.expected_version,
                "notes": notes,
                "override_reason": override_reason,
            }
        )
        actor, process = _lock_process_for_transition(command.actor, command.process_uuid)
        replay = _process_idempotency_replay(
            process=process,
            actor=actor,
            action=RELEASE_ACTION,
            key=key,
            request_hash=request_hash,
        )
        if replay is not None:
            return replay
        if process.status != ProcessStatus.STARTED:
            raise ValidationError("Somente um processo iniciado pode ser liberado para rescisão.")
        if process.version != command.expected_version:
            raise ValidationError("O processo foi alterado por outra sessão. Recarregue a página.")

        readiness = evaluate_process_readiness(process, lock=True)
        _validate_blocker_override(
            actor=actor,
            process=process,
            blockers=readiness.blockers,
            override_reason=override_reason,
            field="release",
        )

        released_at = timezone.now()
        process.status = ProcessStatus.RELEASED
        process.released_at = released_at
        process.released_by = actor
        process.release_notes = notes
        process.release_override_reason = override_reason
        process.version += 1
        process.full_clean(exclude={"active_employee_key"})
        process.save(
            update_fields=(
                "status",
                "released_at",
                "released_by",
                "release_notes",
                "release_override_reason",
                "version",
            )
        )
        ProcessAuditEvent.objects.create(
            process=process,
            event_type=ProcessEventType.RELEASED,
            actor=actor,
            description=PROCESS_RELEASED_DESCRIPTION,
            data={
                "status": process.status,
                "task_count": readiness.task_count,
                "required_task_count": readiness.required_task_count,
                # O que não impedia mas merecia conferência fica registrado: é
                # a prova de que o liberador viu o que estava aberto.
                "warnings": list(readiness.warnings),
                # Vazio na liberação comum; preenchido só quando o
                # `DP_GERENTE` ou o SuperAdmin liberou por cima de impedimento
                # (ADR-054) — a auditoria é a única evidência do rompimento.
                "overridden_blockers": list(readiness.blockers),
                "override_reason": override_reason,
                "process_version": process.version,
            },
            correlation_id=correlation_id.get(),
        )
        _record_process_idempotency(
            process=process,
            actor=actor,
            action=RELEASE_ACTION,
            key=key,
            request_hash=request_hash,
        )
        return ProcessTransitionResult(process=process, replayed=False)


class RegisterTerminationProcessingService:
    """Registrar o que o `DP` declara ter processado no Senior (ADR-051).

    O SGPD não lê nem escreve a rescisão: isto é conferência humana registrada,
    não integração.
    """

    @transaction.atomic
    def execute(self, command: RegisterTerminationProcessingCommand) -> ProcessTransitionResult:
        key = _validated_idempotency_key(command.idempotency_key)
        notes = _validated_notes(command.notes, "notes")
        reference = command.termination_reference.strip()
        if not reference:
            raise ValidationError(
                {"termination_reference": "Informe o número declarado da rescisão."}
            )
        if len(reference) > 60:
            raise ValidationError({"termination_reference": "O número aceita até 60 caracteres."})
        if command.processed_on > timezone.localdate():
            raise ValidationError({"processed_on": "A data do processamento não pode ser futura."})
        request_hash = _canonical_hash(
            {
                "expected_version": command.expected_version,
                "termination_reference": reference,
                "processed_on": command.processed_on.isoformat(),
                "notes": notes,
            }
        )
        actor, process = _lock_process_for_transition(command.actor, command.process_uuid)
        replay = _process_idempotency_replay(
            process=process,
            actor=actor,
            action=PROCESSING_ACTION,
            key=key,
            request_hash=request_hash,
        )
        if replay is not None:
            return replay
        if process.status != ProcessStatus.RELEASED:
            raise ValidationError(
                "Somente um processo liberado pode receber o registro do processamento."
            )
        if process.version != command.expected_version:
            raise ValidationError("O processo foi alterado por outra sessão. Recarregue a página.")
        assert process.released_at is not None
        if command.processed_on < timezone.localtime(process.released_at).date():
            raise ValidationError(
                {"processed_on": "O processamento não pode anteceder a liberação."}
            )

        process.status = ProcessStatus.PROCESSED
        process.termination_reference = reference
        process.termination_processed_on = command.processed_on
        process.processing_registered_at = timezone.now()
        process.processing_registered_by = actor
        process.processing_notes = notes
        process.version += 1
        process.full_clean(exclude={"active_employee_key"})
        process.save(
            update_fields=(
                "status",
                "termination_reference",
                "termination_processed_on",
                "processing_registered_at",
                "processing_registered_by",
                "processing_notes",
                "version",
            )
        )
        ProcessAuditEvent.objects.create(
            process=process,
            event_type=ProcessEventType.PROCESSING_REGISTERED,
            actor=actor,
            description=PROCESSING_REGISTERED_DESCRIPTION,
            data={
                "status": process.status,
                "termination_reference": reference,
                "processed_on": command.processed_on.isoformat(),
                "process_version": process.version,
            },
            correlation_id=correlation_id.get(),
        )
        _record_process_idempotency(
            process=process,
            actor=actor,
            action=PROCESSING_ACTION,
            key=key,
            request_hash=request_hash,
        )
        return ProcessTransitionResult(process=process, replayed=False)


class CloseProcessService:
    """Encerrar formalmente e liberar a chave do colaborador (ADR-051)."""

    @transaction.atomic
    def execute(self, command: CloseProcessCommand) -> ProcessTransitionResult:
        key = _validated_idempotency_key(command.idempotency_key)
        notes = _validated_notes(command.notes, "notes")
        override_reason = _validated_notes(command.override_reason, "override_reason")
        request_hash = _canonical_hash(
            {
                "expected_version": command.expected_version,
                "notes": notes,
                "override_reason": override_reason,
            }
        )
        actor, process = _lock_process_for_transition(command.actor, command.process_uuid)
        replay = _process_idempotency_replay(
            process=process,
            actor=actor,
            action=CLOSE_ACTION,
            key=key,
            request_hash=request_hash,
        )
        if replay is not None:
            return replay
        if process.status != ProcessStatus.PROCESSED:
            raise ValidationError("Somente um processo com rescisão processada pode ser encerrado.")
        if process.version != command.expected_version:
            raise ValidationError("O processo foi alterado por outra sessão. Recarregue a página.")
        blockers = closing_blockers(process, lock=True)
        _validate_blocker_override(
            actor=actor,
            process=process,
            blockers=blockers,
            override_reason=override_reason,
            field="close",
        )

        process.status = ProcessStatus.CLOSED
        process.closed_at = timezone.now()
        process.closed_by = actor
        process.closing_notes = notes
        process.closing_override_reason = override_reason
        # A chave só é liberada aqui e no cancelamento: é o que permite abrir um
        # processo novo para o mesmo colaborador.
        process.active_employee_key = None
        process.version += 1
        process.full_clean(exclude={"active_employee_key"})
        process.save(
            update_fields=(
                "status",
                "closed_at",
                "closed_by",
                "closing_notes",
                "closing_override_reason",
                "active_employee_key",
                "version",
            )
        )
        ProcessAuditEvent.objects.create(
            process=process,
            event_type=ProcessEventType.CLOSED,
            actor=actor,
            description=PROCESS_CLOSED_DESCRIPTION,
            data={
                "status": process.status,
                "employee_key_released": True,
                "overridden_blockers": list(blockers),
                "override_reason": override_reason,
                "process_version": process.version,
            },
            correlation_id=correlation_id.get(),
        )
        _record_process_idempotency(
            process=process,
            actor=actor,
            action=CLOSE_ACTION,
            key=key,
            request_hash=request_hash,
        )
        return ProcessTransitionResult(process=process, replayed=False)


@dataclass(frozen=True, slots=True)
class CancelProcessCommand:
    actor: User
    process_uuid: str
    expected_version: int
    idempotency_key: str
    reason: str


@dataclass(frozen=True, slots=True)
class ReopenProcessCommand:
    actor: User
    process_uuid: str
    expected_version: int
    idempotency_key: str
    reason: str
    #: Tarefas concluídas que voltam para análise. Vazio reabre só o processo,
    #: para corrigir a marca formal sem devolver trabalho ao setor.
    task_ids: tuple[int, ...] = ()


class CancelProcessService:
    """Cancelar o processo com justificativa (RF-031).

    O cancelamento é terminal (ADR-051): cancela as tarefas ainda abertas,
    libera a chave do colaborador e preserva integralmente pendências,
    evidências e trilha.
    """

    @transaction.atomic
    def execute(self, command: CancelProcessCommand) -> ProcessTransitionResult:
        key = _validated_idempotency_key(command.idempotency_key)
        reason = _validated_notes(command.reason, "reason", required=True)
        request_hash = _canonical_hash(
            {"expected_version": command.expected_version, "reason": reason}
        )
        actor, process = _lock_process_for_transition(command.actor, command.process_uuid)
        replay = _process_idempotency_replay(
            process=process,
            actor=actor,
            action=CANCEL_ACTION,
            key=key,
            request_hash=request_hash,
        )
        if replay is not None:
            return replay
        if process.status not in (ProcessStatus.DRAFT, ProcessStatus.STARTED):
            raise ValidationError("Somente um rascunho ou processo iniciado pode ser cancelado.")
        if process.version != command.expected_version:
            raise ValidationError("O processo foi alterado por outra sessão. Recarregue a página.")

        cancelled_at = timezone.now()
        open_tasks = list(
            ProcessSectorTask.objects.select_for_update()
            .filter(process=process, status__in=OPEN_TASK_STATUSES)
            .order_by("pk")
        )
        for task in open_tasks:
            task.status = SectorTaskStatus.CANCELLED
            task.version += 1
            task.full_clean()
            task.save(update_fields=("status", "version"))
            ProcessAuditEvent.objects.create(
                process=process,
                event_type=ProcessEventType.SECTOR_TASK_CANCELLED,
                actor=actor,
                description=SECTOR_TASK_CANCELLED_DESCRIPTION,
                data={
                    "task_id": task.pk,
                    "sector_id": task.sector_id,
                    "status": task.status,
                    "task_version": task.version,
                },
                correlation_id=correlation_id.get(),
            )

        process.status = ProcessStatus.CANCELLED
        process.cancelled_at = cancelled_at
        process.cancelled_by = actor
        process.cancellation_reason = reason
        process.active_employee_key = None
        process.version += 1
        process.full_clean(exclude={"active_employee_key"})
        process.save(
            update_fields=(
                "status",
                "cancelled_at",
                "cancelled_by",
                "cancellation_reason",
                "active_employee_key",
                "version",
            )
        )
        ProcessAuditEvent.objects.create(
            process=process,
            event_type=ProcessEventType.CANCELLED,
            actor=actor,
            description=PROCESS_CANCELLED_DESCRIPTION,
            data={
                "status": process.status,
                "reason": reason,
                "cancelled_task_ids": [task.pk for task in open_tasks],
                "employee_key_released": True,
                "process_version": process.version,
            },
            correlation_id=correlation_id.get(),
        )
        _record_process_idempotency(
            process=process,
            actor=actor,
            action=CANCEL_ACTION,
            key=key,
            request_hash=request_hash,
        )
        # Quem tinha tarefa aberta precisa parar; quem já concluiu não é
        # incomodado por um processo que morreu.
        for task in open_tasks:
            notify_process_cancelled(task)
        return ProcessTransitionResult(process=process, replayed=False)


class ReopenProcessService:
    """Reabrir processo liberado, processado ou encerrado (RF-032).

    A “permissão especial” é a autoridade global da ADR-044: o `DP` que liberou
    não desfaz o próprio ato sozinho (ADR-051). O cancelamento é terminal e não
    é alcançado por aqui.
    """

    @transaction.atomic
    def execute(self, command: ReopenProcessCommand) -> ProcessTransitionResult:
        key = _validated_idempotency_key(command.idempotency_key)
        reason = _validated_notes(command.reason, "reason", required=True)
        task_ids = tuple(sorted(set(command.task_ids)))
        request_hash = _canonical_hash(
            {
                "expected_version": command.expected_version,
                "reason": reason,
                "task_ids": list(task_ids),
            }
        )
        process = _lock_process(command.process_uuid)
        actor = _lock_actor(command.actor)
        if not has_global_authority(actor):
            raise PermissionDenied("A reabertura do processo é exclusiva do SuperAdmin.")
        replay = _process_idempotency_replay(
            process=process,
            actor=actor,
            action=REOPEN_ACTION,
            key=key,
            request_hash=request_hash,
        )
        if replay is not None:
            return replay
        if process.status not in FORMALLY_ADVANCED_PROCESS_STATUSES:
            raise ValidationError(
                "Somente um processo liberado, processado ou encerrado pode ser reaberto."
            )
        if process.version != command.expected_version:
            raise ValidationError("O processo foi alterado por outra sessão. Recarregue a página.")

        tasks = list(
            ProcessSectorTask.objects.select_for_update()
            .filter(process=process, pk__in=task_ids)
            .order_by("pk")
        )
        if len(tasks) != len(task_ids):
            raise ValidationError({"task_ids": "Uma das tarefas não pertence ao processo."})
        for task in tasks:
            if task.status != SectorTaskStatus.COMPLETED:
                raise ValidationError(
                    {"task_ids": f"A tarefa de {task.sector_name_snapshot} não está concluída."}
                )

        previous_state = {
            "status": process.status,
            "released_at": process.released_at.isoformat() if process.released_at else None,
            "released_by_id": process.released_by_id,
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
            "closed_at": process.closed_at.isoformat() if process.closed_at else None,
            "closed_by_id": process.closed_by_id,
        }
        # A trilha guarda o estado anterior (`WORKFLOWS.md` §8); a linha volta a
        # ser a de um processo iniciado, para que o ciclo formal possa ser
        # refeito por inteiro.
        process.status = ProcessStatus.STARTED
        process.released_at = None
        process.released_by = None
        process.release_notes = ""
        process.termination_reference = ""
        process.termination_processed_on = None
        process.processing_registered_at = None
        process.processing_registered_by = None
        process.processing_notes = ""
        process.closed_at = None
        process.closed_by = None
        process.closing_notes = ""
        # `not` e não `is None`: o Oracle guarda a chave liberada como NULL, mas
        # o backend do Django devolve `''` ao ler um `CharField`. Comparar com
        # `None` aqui nunca é verdadeiro no Oracle, e a reabertura devolveria o
        # processo à ativa sem retomar a chave — dois processos vivos para o
        # mesmo colaborador, com a unicidade do banco nunca consultada.
        if not process.active_employee_key:
            process.active_employee_key = _employee_key(
                process.company_code,
                process.branch_code,
                process.employee_type_code,
                process.employee_registration,
            )
        process.version += 1
        process.full_clean(exclude={"active_employee_key"})
        try:
            process.save(
                update_fields=(
                    "status",
                    "released_at",
                    "released_by",
                    "release_notes",
                    "termination_reference",
                    "termination_processed_on",
                    "processing_registered_at",
                    "processing_registered_by",
                    "processing_notes",
                    "closed_at",
                    "closed_by",
                    "closing_notes",
                    "active_employee_key",
                    "version",
                )
            )
        except IntegrityError as exc:
            # A unicidade do banco é a árbitra: outro processo pode ter sido
            # aberto para o mesmo colaborador depois do encerramento.
            raise ValidationError(
                "Já existe outro processo não encerrado para este colaborador."
            ) from exc

        reopening = (
            ProcessAuditEvent.objects.filter(
                process=process,
                event_type=ProcessEventType.REOPENED,
            ).count()
            + 1
        )
        for task in tasks:
            task.status = SectorTaskStatus.IN_ANALYSIS
            task.completed_at = None
            task.completed_by = None
            task.version += 1
            task.full_clean()
            task.save(update_fields=("status", "completed_at", "completed_by", "version"))
            ProcessAuditEvent.objects.create(
                process=process,
                event_type=ProcessEventType.SECTOR_TASK_REOPENED,
                actor=actor,
                description=SECTOR_TASK_REOPENED_DESCRIPTION,
                data={
                    "task_id": task.pk,
                    "sector_id": task.sector_id,
                    "status": task.status,
                    "task_version": task.version,
                },
                correlation_id=correlation_id.get(),
            )
        ProcessAuditEvent.objects.create(
            process=process,
            event_type=ProcessEventType.REOPENED,
            actor=actor,
            description=PROCESS_REOPENED_DESCRIPTION,
            data={
                "status": process.status,
                "reason": reason,
                "previous_state": previous_state,
                "reopened_task_ids": [task.pk for task in tasks],
                "reopening": reopening,
                "process_version": process.version,
            },
            correlation_id=correlation_id.get(),
        )
        _record_process_idempotency(
            process=process,
            actor=actor,
            action=REOPEN_ACTION,
            key=key,
            request_hash=request_hash,
        )
        for task in tasks:
            notify_process_reopened(task, reopening=reopening)
        return ProcessTransitionResult(process=process, replayed=False)
