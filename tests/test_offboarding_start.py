"""Draft selection and idempotent generation of sector tasks."""

from __future__ import annotations

from datetime import date, timedelta
from typing import Any

import pytest
from django.contrib.auth.models import Permission
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import IntegrityError, connection
from django.test import Client
from django.test.utils import CaptureQueriesContext
from django.urls import reverse
from django.utils import timezone

from apps.accounts.models import (
    PEOPLE_DEPARTMENT_ROLE_CODE,
    Role,
    RoleAssignment,
    ScopeType,
    User,
    build_scope_key,
)
from apps.offboarding.models import (
    DraftOverrideAction,
    EmployeeSnapshot,
    OffboardingProcess,
    ProcessActionIdempotency,
    ProcessAuditEvent,
    ProcessChecklistItem,
    ProcessEventType,
    ProcessSectorTask,
    ProcessStatus,
)
from apps.offboarding.services import (
    DraftSectorOverrideValue,
    GetDraftProcessContextService,
    IdempotencyConflict,
    StartOffboardingProcessCommand,
    StartOffboardingProcessResult,
    StartOffboardingProcessService,
    UpdateDraftSelectionCommand,
    UpdateDraftSelectionService,
)
from apps.sectors.models import SectorResponsible, SectorScope, ValidationSector
from apps.templates_engine.models import (
    ChecklistResponseType,
    ChecklistTemplate,
    ValidationGroupVersion,
    VersionStatus,
)
from apps.templates_engine.services import (
    ChecklistItemValue,
    CreateChecklistTemplateCommand,
    CreateChecklistTemplateService,
    CreateValidationGroupCommand,
    CreateValidationGroupService,
    GroupSectorValue,
    PublishChecklistTemplateVersionCommand,
    PublishChecklistTemplateVersionService,
    PublishValidationGroupVersionCommand,
    PublishValidationGroupVersionService,
)

pytestmark = pytest.mark.django_db

PASSWORD = "Offboarding-start!2026"


@pytest.fixture
def actor() -> User:
    role = Role.objects.create(
        code=PEOPLE_DEPARTMENT_ROLE_CODE,
        name="Departamento Pessoal",
    )
    user = User.objects.create_user(
        username="dp.inicio",
        email="dp.inicio@example.invalid",
        password=PASSWORD,
        first_name="DP",
        last_name="Início",
    )
    RoleAssignment.objects.create(
        user=user,
        role=role,
        scope_type=ScopeType.GLOBAL,
        scope_key=build_scope_key(ScopeType.GLOBAL, None, None),
        valid_from=timezone.now() - timedelta(days=1),
        assigned_by=user,
    )
    permission = Permission.objects.get(
        content_type__app_label="templates_engine",
        codename="manage_workflow_configuration",
    )
    user.user_permissions.add(permission)
    return user


@pytest.fixture
def process(actor: User) -> OffboardingProcess:
    row = OffboardingProcess.objects.create(
        company_code=1,
        branch_code=2,
        employee_type_code=1,
        employee_registration=321,
        active_employee_key="1:2:1:321",
        opened_by=actor,
        planned_termination_date=date(2026, 8, 15),
        due_date=date(2026, 8, 14),
        reason="Reorganização.",
        priority="Alta",
    )
    EmployeeSnapshot.objects.create(
        process=row,
        company_code=1,
        branch_code=2,
        branch_legal_name="Empresa",
        employee_type_code=1,
        employee_type_description="Empregado",
        registration=321,
        employee_name="Pessoa",
        admission_date=date(2020, 1, 2),
        leave_code=1,
        leave_description="Trabalhando",
        job_structure_code=1,
        job_code="DEV",
        job_description="Desenvolvedor",
        cost_center_code="100",
        source_queried_at=timezone.now(),
    )
    return row


def create_sector(
    actor: User,
    *,
    code: str = "TECNOLOGIA",
    with_responsible: bool = True,
    company: int | None = None,
) -> ValidationSector:
    sector = ValidationSector.objects.create(
        code=code,
        name=code.title(),
        default_due_hours=24,
    )
    scope = SectorScope(
        sector=sector,
        scope_type=ScopeType.GLOBAL if company is None else ScopeType.COMPANY,
        company_code=company,
    )
    scope.full_clean()
    scope.save()
    if with_responsible:
        SectorResponsible.objects.create(
            sector=sector,
            user=actor,
            valid_from=timezone.now() - timedelta(hours=1),
            assigned_by=actor,
            updated_by=actor,
        )
    return sector


def create_published_template(
    actor: User,
    sector: ValidationSector,
) -> ChecklistTemplate:
    template = CreateChecklistTemplateService().execute(
        CreateChecklistTemplateCommand(
            actor=actor,
            name=f"Template {sector.name}",
            description="",
            default_due_hours=12,
            items=(
                ChecklistItemValue(
                    question="A validação foi concluída?",
                    response_type=ChecklistResponseType.BOOLEAN,
                    is_required=True,
                    blocks_process=True,
                    requires_evidence=False,
                    allows_pending=True,
                    display_order=1,
                    config={},
                ),
            ),
        )
    )
    version = template.versions.get()
    PublishChecklistTemplateVersionService().execute(
        PublishChecklistTemplateVersionCommand(
            actor=actor,
            version_id=version.pk,
            expected_template_version=template.version,
        )
    )
    template.refresh_from_db()
    return template


def create_published_group(
    actor: User,
    sector: ValidationSector,
    template: ChecklistTemplate,
    *,
    code: str = "PADRAO",
    required: bool = True,
    blocks: bool = True,
) -> ValidationGroupVersion:
    template_version = template.current_version
    assert template_version is not None
    group = CreateValidationGroupService().execute(
        CreateValidationGroupCommand(
            actor=actor,
            name=f"Grupo {code}",
            description="",
            sectors=(
                GroupSectorValue(
                    sector_id=sector.pk,
                    template_version_id=template_version.pk,
                    is_required=required,
                    blocks_process=blocks,
                    due_hours_override=6,
                    display_order=1,
                ),
            ),
        )
    )
    version = group.versions.get()
    PublishValidationGroupVersionService().execute(
        PublishValidationGroupVersionCommand(
            actor=actor,
            version_id=version.pk,
            expected_group_version=group.version,
        )
    )
    version.refresh_from_db()
    return version


def select_group(
    actor: User,
    process: OffboardingProcess,
    group_version_id: int,
    *,
    overrides: tuple[DraftSectorOverrideValue, ...] = (),
) -> OffboardingProcess:
    return UpdateDraftSelectionService().execute(
        UpdateDraftSelectionCommand(
            actor=actor,
            process_uuid=str(process.uuid),
            expected_version=process.version,
            group_version_ids=(group_version_id,),
            overrides=overrides,
        )
    )


def start(
    actor: User,
    process: OffboardingProcess,
    *,
    key: str = "start-321",
    expected_version: int | None = None,
) -> StartOffboardingProcessResult:
    return StartOffboardingProcessService().execute(
        StartOffboardingProcessCommand(
            actor=actor,
            process_uuid=str(process.uuid),
            expected_version=expected_version or process.version,
            idempotency_key=key,
        )
    )


def configured_draft(
    actor: User,
    process: OffboardingProcess,
    *,
    with_responsible: bool = True,
) -> tuple[OffboardingProcess, ValidationSector]:
    sector = create_sector(actor, with_responsible=with_responsible)
    template = create_published_template(actor, sector)
    group = create_published_group(actor, sector, template)
    process = select_group(actor, process, group.pk)
    return process, sector


def test_start_generates_sector_task_and_historical_questions_once(
    actor: User,
    process: OffboardingProcess,
) -> None:
    process, sector = configured_draft(actor, process)

    result = start(actor, process)
    process.refresh_from_db()

    assert not result.replayed
    assert process.status == ProcessStatus.STARTED
    assert process.started_by == actor
    assert process.version == 3
    task = ProcessSectorTask.objects.get()
    assert task.sector == sector
    assert task.sector_code_snapshot == str(sector.pk)
    assert task.template_code_snapshot == str(task.template_version.template_id)
    assert task.template_version_snapshot == 1
    assert task.sla_hours_snapshot == 6
    assert task.is_required
    assert task.group_sources.count() == 1
    snapshot = ProcessChecklistItem.objects.get()
    assert snapshot.code_snapshot == str(snapshot.source_item_id)
    assert snapshot.question_snapshot == "A validação foi concluída?"
    assert ProcessActionIdempotency.objects.count() == 1
    assert (
        ProcessAuditEvent.objects.get(event_type=ProcessEventType.STARTED).data["task_count"] == 1
    )


def test_superadmin_reads_and_starts_any_process_without_dp_assignment(
    actor: User,
    process: OffboardingProcess,
) -> None:
    process, _ = configured_draft(actor, process)
    superadmin = User.objects.create_superuser(
        username="workflow.superadmin",
        email="workflow.superadmin@example.invalid",
        password=PASSWORD,
    )

    context = GetDraftProcessContextService().execute(superadmin, str(process.uuid))
    result = start(superadmin, process, key="superadmin-start")
    process.refresh_from_db()

    assert context.process == process
    assert len(result.tasks) == 1
    assert process.status == ProcessStatus.STARTED
    assert process.started_by == superadmin
    assert ProcessAuditEvent.objects.get(event_type=ProcessEventType.STARTED).actor == superadmin


def test_start_reuses_template_with_independent_snapshots_for_each_sector(
    actor: User,
    process: OffboardingProcess,
) -> None:
    technology = create_sector(actor)
    finance = create_sector(actor, code="FINANCEIRO")
    template = create_published_template(actor, technology)
    template_version = template.current_version
    assert template_version is not None
    group = CreateValidationGroupService().execute(
        CreateValidationGroupCommand(
            actor=actor,
            name="Validação multissetor",
            description="",
            sectors=(
                GroupSectorValue(
                    sector_id=technology.pk,
                    template_version_id=template_version.pk,
                    is_required=True,
                    blocks_process=True,
                    due_hours_override=6,
                    display_order=1,
                ),
                GroupSectorValue(
                    sector_id=finance.pk,
                    template_version_id=template_version.pk,
                    is_required=True,
                    blocks_process=False,
                    due_hours_override=10,
                    display_order=2,
                ),
            ),
        )
    )
    group_version = group.versions.get()
    PublishValidationGroupVersionService().execute(
        PublishValidationGroupVersionCommand(
            actor=actor,
            version_id=group_version.pk,
            expected_group_version=group.version,
        )
    )
    selected = select_group(actor, process, group_version.pk)

    result = start(actor, selected)

    assert len(result.tasks) == 2
    assert {task.sector_id for task in result.tasks} == {technology.pk, finance.pk}
    assert {task.template_version_id for task in result.tasks} == {template_version.pk}
    snapshots = list(ProcessChecklistItem.objects.order_by("task_id"))
    assert len(snapshots) == 2
    assert snapshots[0].task_id != snapshots[1].task_id
    assert {snapshot.question_snapshot for snapshot in snapshots} == {"A validação foi concluída?"}


def test_start_replay_is_idempotent_and_does_not_duplicate_audit(
    actor: User,
    process: OffboardingProcess,
) -> None:
    process, _ = configured_draft(actor, process)
    expected_version = process.version

    first = start(actor, process, expected_version=expected_version)
    second = start(actor, process, expected_version=expected_version)

    assert not first.replayed
    assert second.replayed
    assert ProcessSectorTask.objects.count() == 1
    assert ProcessChecklistItem.objects.count() == 1
    assert ProcessAuditEvent.objects.filter(event_type=ProcessEventType.STARTED).count() == 1
    assert ProcessActionIdempotency.objects.count() == 1


def test_idempotency_key_rejects_different_request(
    actor: User,
    process: OffboardingProcess,
) -> None:
    process, _ = configured_draft(actor, process)
    start(actor, process, key="same-key", expected_version=process.version)

    with pytest.raises(IdempotencyConflict, match="outro conteúdo"):
        start(actor, process, key="same-key", expected_version=999)


def test_required_sector_without_effective_responsible_blocks_and_rolls_back(
    actor: User,
    process: OffboardingProcess,
) -> None:
    process, _ = configured_draft(actor, process, with_responsible=False)

    with pytest.raises(ValidationError, match="não possui responsável vigente"):
        start(actor, process)

    process.refresh_from_db()
    assert process.status == ProcessStatus.DRAFT
    assert not ProcessSectorTask.objects.exists()
    assert not ProcessActionIdempotency.objects.exists()
    assert not ProcessAuditEvent.objects.filter(event_type=ProcessEventType.STARTED).exists()


def test_group_sector_outside_process_scope_is_not_generated(
    actor: User,
    process: OffboardingProcess,
) -> None:
    sector = create_sector(actor, company=99)
    template = create_published_template(actor, sector)
    group = create_published_group(actor, sector, template)
    process = select_group(actor, process, group.pk)

    with pytest.raises(ValidationError, match="ao menos um setor obrigatório"):
        start(actor, process)

    assert not ProcessSectorTask.objects.exists()


def test_start_revalidates_dp_scope_and_optimistic_version(
    actor: User,
    process: OffboardingProcess,
) -> None:
    process, _ = configured_draft(actor, process)
    assignment = RoleAssignment.objects.get(user=actor)
    assignment.is_active = False
    assignment.revoked_by = actor
    assignment.revoked_at = timezone.now()
    assignment.save(update_fields=("is_active", "revoked_by", "revoked_at"))

    with pytest.raises(PermissionDenied, match="papel DP"):
        start(actor, process)

    assignment.is_active = True
    assignment.revoked_by = None
    assignment.revoked_at = None
    assignment.save(update_fields=("is_active", "revoked_by", "revoked_at"))
    with pytest.raises(ValidationError, match="outra sessão"):
        start(actor, process, expected_version=process.version + 1)
    assert not ProcessSectorTask.objects.exists()


def test_start_audit_failure_rolls_back_tasks_status_and_idempotency(
    actor: User,
    process: OffboardingProcess,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    process, _ = configured_draft(actor, process)
    original_create = ProcessAuditEvent.objects.create

    def fail_started(**kwargs: Any) -> Any:
        if kwargs.get("event_type") == ProcessEventType.STARTED:
            raise IntegrityError("audit unavailable")
        return original_create(**kwargs)

    monkeypatch.setattr(ProcessAuditEvent.objects, "create", fail_started)

    with pytest.raises(IntegrityError, match="audit unavailable"):
        start(actor, process)

    process.refresh_from_db()
    assert process.status == ProcessStatus.DRAFT
    assert not ProcessSectorTask.objects.exists()
    assert not ProcessActionIdempotency.objects.exists()


def test_overlapping_groups_merge_stricter_rule_and_conflicting_template_fails(
    actor: User,
    process: OffboardingProcess,
) -> None:
    sector = create_sector(actor)
    first_template = create_published_template(actor, sector)
    first_group = create_published_group(
        actor,
        sector,
        first_template,
        code="PADRAO",
        blocks=False,
    )
    second_group = create_published_group(
        actor,
        sector,
        first_template,
        code="CRITICO",
        required=True,
    )
    selected = UpdateDraftSelectionService().execute(
        UpdateDraftSelectionCommand(
            actor=actor,
            process_uuid=str(process.uuid),
            expected_version=process.version,
            group_version_ids=(first_group.pk, second_group.pk),
        )
    )
    result = start(actor, selected)
    assert result.tasks[0].is_required
    assert result.tasks[0].blocks_process
    assert result.tasks[0].group_sources.count() == 2

    other_process = OffboardingProcess.objects.create(
        company_code=1,
        branch_code=2,
        employee_type_code=1,
        employee_registration=999,
        active_employee_key="1:2:1:999",
        opened_by=actor,
        planned_termination_date=process.planned_termination_date,
        due_date=process.due_date,
        reason="Outro.",
        priority="Alta",
    )
    second_template = create_published_template(
        actor,
        sector,
    )
    conflicting = create_published_group(
        actor,
        sector,
        second_template,
        code="ALTERNATIVO",
    )
    other_process = UpdateDraftSelectionService().execute(
        UpdateDraftSelectionCommand(
            actor=actor,
            process_uuid=str(other_process.uuid),
            expected_version=other_process.version,
            group_version_ids=(first_group.pk, conflicting.pk),
        )
    )
    with pytest.raises(ValidationError, match="templates diferentes"):
        start(actor, other_process)
    assert ProcessSectorTask.objects.filter(process=other_process).count() == 0


def test_manual_exclusion_requires_reason_and_can_replace_group_sector(
    actor: User,
    process: OffboardingProcess,
) -> None:
    sector = create_sector(actor)
    template = create_published_template(actor, sector)
    group = create_published_group(actor, sector, template)

    with pytest.raises(ValidationError, match="justificativa"):
        select_group(
            actor,
            process,
            group.pk,
            overrides=(
                DraftSectorOverrideValue(
                    sector_id=sector.pk,
                    action=DraftOverrideAction.EXCLUDE,
                    reason=" ",
                ),
            ),
        )

    process = select_group(
        actor,
        process,
        group.pk,
        overrides=(
            DraftSectorOverrideValue(
                sector_id=sector.pk,
                action=DraftOverrideAction.EXCLUDE,
                reason="Setor não participa deste caso.",
            ),
        ),
    )
    with pytest.raises(ValidationError, match="ao menos um setor obrigatório"):
        start(actor, process)
    assert not ProcessSectorTask.objects.exists()


def test_draft_and_start_api_authorize_validate_and_replay(
    actor: User,
    process: OffboardingProcess,
) -> None:
    process, _ = configured_draft(actor, process)
    client = Client()
    client.force_login(actor)
    detail_url = reverse(
        "offboarding-api:process-draft",
        kwargs={"process_uuid": process.uuid},
    )
    start_url = reverse(
        "offboarding-api:process-start",
        kwargs={"process_uuid": process.uuid},
    )

    with CaptureQueriesContext(connection) as queries:
        detail = client.get(detail_url)
    assert detail.status_code == 200
    assert detail.json()["selection"]["blockers"] == []
    assert detail.json()["selection"]["resolved_sectors"][0]["code"] == "TECNOLOGIA"
    group_queries = [
        query["sql"].upper()
        for query in queries.captured_queries
        if "SGPD_VALIDATION_GROUP_VER" in query["sql"].upper()
    ]
    assert group_queries
    assert all("SELECT DISTINCT" not in query for query in group_queries)

    missing_key = client.post(
        start_url,
        data={"expected_version": process.version},
        content_type="application/json",
    )
    assert missing_key.status_code == 400
    first = client.post(
        start_url,
        data={"expected_version": process.version},
        content_type="application/json",
        HTTP_IDEMPOTENCY_KEY="api-start",
    )
    replay = client.post(
        start_url,
        data={"expected_version": process.version},
        content_type="application/json",
        HTTP_IDEMPOTENCY_KEY="api-start",
    )
    conflict = client.post(
        start_url,
        data={"expected_version": 999},
        content_type="application/json",
        HTTP_IDEMPOTENCY_KEY="api-start",
    )

    assert first.status_code == 200
    assert not first.json()["idempotency_replayed"]
    assert replay.status_code == 200
    assert replay.json()["idempotency_replayed"]
    assert conflict.status_code == 409
    assert conflict.json()["code"] == "idempotency_conflict"


def test_draft_endpoints_reject_anonymous_and_non_dp(
    process: OffboardingProcess,
) -> None:
    plain = User.objects.create_user(
        username="sem.dp.inicio",
        email="sem.dp.inicio@example.invalid",
        password=PASSWORD,
    )
    denied = Client()
    denied.force_login(plain)
    urls = (
        reverse(
            "offboarding-api:process-draft",
            kwargs={"process_uuid": process.uuid},
        ),
        reverse(
            "offboarding-api:process-draft-selection",
            kwargs={"process_uuid": process.uuid},
        ),
        reverse(
            "offboarding-api:process-start",
            kwargs={"process_uuid": process.uuid},
        ),
    )

    assert Client().get(urls[0]).status_code == 401
    assert denied.get(urls[0]).status_code == 403
    assert (
        denied.put(
            urls[1],
            data={"expected_version": 1, "group_version_ids": [999]},
            content_type="application/json",
        ).status_code
        == 403
    )
    assert (
        denied.post(
            urls[2],
            data={"expected_version": 1},
            content_type="application/json",
            HTTP_IDEMPOTENCY_KEY="denied",
        ).status_code
        == 403
    )


def test_only_current_published_group_can_be_newly_selected(
    actor: User,
    process: OffboardingProcess,
) -> None:
    sector = create_sector(actor)
    template = create_published_template(actor, sector)
    group_version = create_published_group(actor, sector, template)
    assert group_version.status == VersionStatus.PUBLISHED
    group_version.status = VersionStatus.RETIRED
    group_version.save(update_fields=("status",))

    with pytest.raises(ValidationError, match="vigente publicada"):
        select_group(actor, process, group_version.pk)
