"""Versioned workflow configuration, authorization and publication."""

from __future__ import annotations

from typing import Any

import pytest
from django.contrib.auth.models import Permission
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import IntegrityError, connection
from django.db.migrations.executor import MigrationExecutor
from django.test import Client
from django.urls import reverse

from apps.accounts.models import User
from apps.sectors.models import ValidationSector
from apps.templates_engine.models import (
    ChecklistResponseType,
    ChecklistTemplate,
    ChecklistTemplateItem,
    VersionStatus,
    WorkflowConfigurationAuditEvent,
)
from apps.templates_engine.services import (
    ChecklistItemValue,
    CreateChecklistTemplateCommand,
    CreateChecklistTemplateService,
    CreateChecklistTemplateVersionCommand,
    CreateChecklistTemplateVersionService,
    CreateValidationGroupCommand,
    CreateValidationGroupService,
    GroupSectorValue,
    PublishChecklistTemplateVersionCommand,
    PublishChecklistTemplateVersionService,
    PublishValidationGroupVersionCommand,
    PublishValidationGroupVersionService,
    UpdateChecklistTemplateDraftCommand,
    UpdateChecklistTemplateDraftService,
)

pytestmark = pytest.mark.django_db

PASSWORD = "Workflow-config!2026"


@pytest.fixture
def actor() -> User:
    user = User.objects.create_user(
        username="config.workflow",
        email="config.workflow@example.invalid",
        password=PASSWORD,
        first_name="Configuração",
        last_name="Workflow",
    )
    permission = Permission.objects.get(
        content_type__app_label="templates_engine",
        codename="manage_workflow_configuration",
    )
    user.user_permissions.add(permission)
    return user


@pytest.fixture
def plain_user() -> User:
    return User.objects.create_user(
        username="sem.config.workflow",
        email="sem.config.workflow@example.invalid",
        password=PASSWORD,
        first_name="Sem",
        last_name="Permissão",
    )


@pytest.fixture
def sector() -> ValidationSector:
    return ValidationSector.objects.create(
        code="TECNOLOGIA",
        name="Tecnologia",
        default_due_hours=24,
    )


def item(code: str = "ACESSOS", order: int = 1) -> ChecklistItemValue:
    return ChecklistItemValue(
        code=code,
        question="Os acessos foram encerrados?",
        response_type=ChecklistResponseType.BOOLEAN,
        is_required=True,
        blocks_process=True,
        requires_evidence=False,
        allows_pending=True,
        display_order=order,
        config={},
    )


def template_command(actor: User) -> CreateChecklistTemplateCommand:
    return CreateChecklistTemplateCommand(
        actor=actor,
        name="Checklist de TI",
        description="Validações mínimas de TI.",
        default_due_hours=12,
        items=(item(),),
    )


def publish_template(actor: User) -> ChecklistTemplate:
    template = CreateChecklistTemplateService().execute(template_command(actor))
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


def test_service_requires_explicit_configuration_permission(
    plain_user: User,
) -> None:
    with pytest.raises(PermissionDenied, match="grupos e templates"):
        CreateChecklistTemplateService().execute(template_command(plain_user))

    assert not ChecklistTemplate.objects.exists()
    assert not WorkflowConfigurationAuditEvent.objects.exists()


def test_template_is_created_published_and_audited(
    actor: User,
) -> None:
    template = CreateChecklistTemplateService().execute(template_command(actor))
    version = template.versions.get()

    assert version.status == VersionStatus.DRAFT
    assert version.version_number == 1
    assert template.code == str(template.pk)
    assert version.items.get().code == "ACESSOS"
    assert WorkflowConfigurationAuditEvent.objects.count() == 2

    published = PublishChecklistTemplateVersionService().execute(
        PublishChecklistTemplateVersionCommand(
            actor=actor,
            version_id=version.pk,
            expected_template_version=template.version,
        )
    )
    template.refresh_from_db()

    assert published.status == VersionStatus.PUBLISHED
    assert template.current_version_id == published.pk
    assert template.version == 2
    assert WorkflowConfigurationAuditEvent.objects.count() == 3

    with pytest.raises(ValidationError, match="services auditados"):
        ChecklistTemplateItem.objects.update(question="Alterada")
    checklist_item = published.items.get()
    checklist_item.question = "Alterada"
    with pytest.raises(ValidationError, match="imutáveis"):
        checklist_item.save()
    with pytest.raises(ValidationError, match="não podem"):
        published.delete()


def test_new_template_version_retires_previous_without_changing_items(
    actor: User,
) -> None:
    template = publish_template(actor)
    first = template.current_version
    assert first is not None

    second = CreateChecklistTemplateVersionService().execute(
        CreateChecklistTemplateVersionCommand(
            actor=actor,
            template_id=template.pk,
            expected_version=template.version,
            default_due_hours=8,
            items=(item("ACESSOS_V2"),),
        )
    )
    template.refresh_from_db()
    published = PublishChecklistTemplateVersionService().execute(
        PublishChecklistTemplateVersionCommand(
            actor=actor,
            version_id=second.pk,
            expected_template_version=template.version,
        )
    )
    first.refresh_from_db()
    template.refresh_from_db()

    assert first.status == VersionStatus.RETIRED
    assert first.items.get().code == "ACESSOS"
    assert published.status == VersionStatus.PUBLISHED
    assert template.current_version_id == second.pk


def test_group_pins_published_template_version(
    actor: User,
    sector: ValidationSector,
) -> None:
    template = publish_template(actor)
    template_version = template.current_version
    assert template_version is not None

    group = CreateValidationGroupService().execute(
        CreateValidationGroupCommand(
            actor=actor,
            code="PADRAO",
            name="Desligamento padrão",
            description="Grupo mínimo.",
            sectors=(
                GroupSectorValue(
                    sector_id=sector.pk,
                    template_version_id=template_version.pk,
                    is_required=True,
                    blocks_process=True,
                    due_hours_override=6,
                    display_order=1,
                ),
            ),
        )
    )
    group_version = group.versions.get()
    rule = group_version.sector_rules.get()

    assert rule.template_version == template_version
    assert group_version.status == VersionStatus.DRAFT

    published = PublishValidationGroupVersionService().execute(
        PublishValidationGroupVersionCommand(
            actor=actor,
            version_id=group_version.pk,
            expected_group_version=group.version,
        )
    )
    group.refresh_from_db()

    assert published.status == VersionStatus.PUBLISHED
    assert group.current_version_id == published.pk


def test_group_reuses_the_same_template_in_multiple_sectors(
    actor: User,
    sector: ValidationSector,
) -> None:
    template = publish_template(actor)
    template_version = template.current_version
    assert template_version is not None
    other = ValidationSector.objects.create(
        code="FINANCEIRO",
        name="Financeiro",
        default_due_hours=24,
    )

    group = CreateValidationGroupService().execute(
        CreateValidationGroupCommand(
            actor=actor,
            code="COMPARTILHADO",
            name="Template compartilhado",
            description="",
            sectors=(
                GroupSectorValue(
                    sector_id=sector.pk,
                    template_version_id=template_version.pk,
                    is_required=True,
                    blocks_process=True,
                    due_hours_override=None,
                    display_order=1,
                ),
                GroupSectorValue(
                    sector_id=other.pk,
                    template_version_id=template_version.pk,
                    is_required=True,
                    blocks_process=False,
                    due_hours_override=8,
                    display_order=2,
                ),
            ),
        )
    )

    rules = list(group.versions.get().sector_rules.order_by("display_order"))
    assert [rule.sector_id for rule in rules] == [sector.pk, other.pk]
    assert {rule.template_version_id for rule in rules} == {template_version.pk}


def test_audit_failure_rolls_back_template(
    actor: User,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fail_create(**kwargs: Any) -> None:
        raise IntegrityError("audit unavailable")

    monkeypatch.setattr(
        WorkflowConfigurationAuditEvent.objects,
        "create",
        fail_create,
    )

    with pytest.raises(IntegrityError, match="audit unavailable"):
        CreateChecklistTemplateService().execute(template_command(actor))

    assert not ChecklistTemplate.objects.exists()
    assert not ChecklistTemplateItem.objects.exists()


def test_draft_can_be_edited_in_place_and_is_audited(
    actor: User,
) -> None:
    template = CreateChecklistTemplateService().execute(template_command(actor))
    draft = template.versions.get()

    updated = UpdateChecklistTemplateDraftService().execute(
        UpdateChecklistTemplateDraftCommand(
            actor=actor,
            version_id=draft.pk,
            expected_template_version=template.version,
            name="Checklist corporativo",
            description="Conteúdo revisado.",
            default_due_hours=18,
            items=(item("EQUIPAMENTOS"),),
        )
    )
    template.refresh_from_db()

    assert updated.pk == draft.pk
    assert updated.default_due_hours == 18
    assert list(updated.items.values_list("code", flat=True)) == ["EQUIPAMENTOS"]
    assert template.name == "Checklist corporativo"
    assert template.description == "Conteúdo revisado."
    assert template.version == 2
    event = WorkflowConfigurationAuditEvent.objects.get(event_type="TPL_DRAFT_UPDATED")
    assert event.entity_id == draft.pk
    assert event.data["previous_item_codes"] == ["ACESSOS"]
    assert event.data["item_codes"] == ["EQUIPAMENTOS"]


def test_published_template_requires_a_new_draft_before_editing(
    actor: User,
) -> None:
    template = publish_template(actor)
    published = template.current_version
    assert published is not None

    with pytest.raises(ValidationError, match="Somente uma versão em rascunho"):
        UpdateChecklistTemplateDraftService().execute(
            UpdateChecklistTemplateDraftCommand(
                actor=actor,
                version_id=published.pk,
                expected_template_version=template.version,
                name="Não deve mudar",
                description="",
                default_due_hours=6,
                items=(item("ALTERADO"),),
            )
        )

    template.refresh_from_db()
    published.refresh_from_db()
    assert template.name == "Checklist de TI"
    assert published.default_due_hours == 12
    assert published.items.get().code == "ACESSOS"


def test_draft_update_rejects_stale_version_and_permission(
    actor: User,
    plain_user: User,
) -> None:
    template = CreateChecklistTemplateService().execute(template_command(actor))
    draft = template.versions.get()
    command = UpdateChecklistTemplateDraftCommand(
        actor=actor,
        version_id=draft.pk,
        expected_template_version=template.version + 1,
        name="Não deve mudar",
        description="",
        default_due_hours=6,
        items=(item("ALTERADO"),),
    )

    with pytest.raises(ValidationError, match="outra sessão"):
        UpdateChecklistTemplateDraftService().execute(command)
    with pytest.raises(PermissionDenied, match="grupos e templates"):
        UpdateChecklistTemplateDraftService().execute(
            UpdateChecklistTemplateDraftCommand(
                actor=plain_user,
                version_id=draft.pk,
                expected_template_version=template.version,
                name="Não deve mudar",
                description="",
                default_due_hours=6,
                items=(item("ALTERADO"),),
            )
        )

    template.refresh_from_db()
    assert template.name == "Checklist de TI"
    assert draft.items.get().code == "ACESSOS"


def test_draft_update_rolls_back_when_audit_fails(
    actor: User,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    template = CreateChecklistTemplateService().execute(template_command(actor))
    draft = template.versions.get()

    def fail_create(**kwargs: Any) -> None:
        raise IntegrityError("audit unavailable")

    monkeypatch.setattr(WorkflowConfigurationAuditEvent.objects, "create", fail_create)
    with pytest.raises(IntegrityError, match="audit unavailable"):
        UpdateChecklistTemplateDraftService().execute(
            UpdateChecklistTemplateDraftCommand(
                actor=actor,
                version_id=draft.pk,
                expected_template_version=template.version,
                name="Não deve persistir",
                description="",
                default_due_hours=6,
                items=(item("ALTERADO"),),
            )
        )

    template.refresh_from_db()
    draft.refresh_from_db()
    assert template.name == "Checklist de TI"
    assert template.version == 1
    assert draft.default_due_hours == 12
    assert draft.items.get().code == "ACESSOS"


def test_template_allows_only_one_draft_per_template(
    actor: User,
) -> None:
    template = publish_template(actor)
    CreateChecklistTemplateVersionService().execute(
        CreateChecklistTemplateVersionCommand(
            actor=actor,
            template_id=template.pk,
            expected_version=template.version,
            default_due_hours=8,
            items=(item("VERSAO_2"),),
        )
    )
    template.refresh_from_db()

    with pytest.raises(ValidationError, match="já possui uma versão em rascunho"):
        CreateChecklistTemplateVersionService().execute(
            CreateChecklistTemplateVersionCommand(
                actor=actor,
                template_id=template.pk,
                expected_version=template.version,
                default_due_hours=4,
                items=(item("VERSAO_3"),),
            )
        )

    assert template.versions.filter(status=VersionStatus.DRAFT).count() == 1


@pytest.mark.parametrize(
    ("method", "route_name", "kwargs"),
    [
        ("get", "workflow-configuration-api:sector-list", {}),
        ("get", "workflow-configuration-api:template-list", {}),
        ("post", "workflow-configuration-api:template-list", {}),
        (
            "post",
            "workflow-configuration-api:template-version-create",
            {"template_id": 999},
        ),
        (
            "post",
            "workflow-configuration-api:template-version-publish",
            {"version_id": 999},
        ),
        (
            "put",
            "workflow-configuration-api:template-version-update",
            {"version_id": 999},
        ),
        ("get", "workflow-configuration-api:group-list", {}),
        ("post", "workflow-configuration-api:group-list", {}),
        (
            "post",
            "workflow-configuration-api:group-version-create",
            {"group_id": 999},
        ),
        (
            "post",
            "workflow-configuration-api:group-version-publish",
            {"version_id": 999},
        ),
    ],
)
def test_configuration_endpoints_reject_anonymous_and_unauthorized(
    method: str,
    route_name: str,
    kwargs: dict[str, int],
    plain_user: User,
) -> None:
    url = reverse(route_name, kwargs=kwargs)
    anonymous = Client()
    denied = Client()
    denied.force_login(plain_user)

    anonymous_response = getattr(anonymous, method)(
        url,
        data={},
        content_type="application/json",
    )
    denied_response = getattr(denied, method)(
        url,
        data={},
        content_type="application/json",
    )

    assert anonymous_response.status_code == 401
    assert denied_response.status_code == 403


def test_template_and_group_api_create_versioned_configuration(
    actor: User,
    sector: ValidationSector,
) -> None:
    client = Client()
    client.force_login(actor)
    template_payload = {
        "code": "CODIGO_MANUAL_IGNORADO",
        "name": "Checklist de TI",
        "description": "",
        "default_due_hours": 12,
        "items": [
            {
                "code": "ACESSOS",
                "question": "Os acessos foram encerrados?",
                "response_type": "BOOLEAN",
                "is_required": True,
                "blocks_process": True,
                "requires_evidence": False,
                "allows_pending": True,
                "display_order": 1,
                "config": {},
            }
        ],
    }
    response = client.post(
        reverse("workflow-configuration-api:template-list"),
        data=template_payload,
        content_type="application/json",
    )

    assert response.status_code == 201
    assert "sector" not in response.json()
    assert response.json()["code"] == response.json()["id"]
    assert isinstance(response.json()["code"], int)
    assert response.json()["versions"][0]["status"] == VersionStatus.DRAFT
    template = ChecklistTemplate.objects.get()
    template_version = template.versions.get()
    publish = client.post(
        reverse(
            "workflow-configuration-api:template-version-publish",
            kwargs={"version_id": template_version.pk},
        ),
        data={"expected_version": template.version},
        content_type="application/json",
    )
    assert publish.status_code == 200

    group_response = client.post(
        reverse("workflow-configuration-api:group-list"),
        data={
            "code": "PADRAO",
            "name": "Padrão",
            "description": "",
            "sectors": [
                {
                    "sector_id": sector.pk,
                    "template_version_id": template_version.pk,
                    "is_required": True,
                    "blocks_process": True,
                    "due_hours_override": None,
                    "display_order": 1,
                }
            ],
        },
        content_type="application/json",
    )

    assert group_response.status_code == 201
    assert group_response.json()["versions"][0]["sectors"][0]["sector"]["code"] == "TECNOLOGIA"
    assert (
        group_response.json()["versions"][0]["sectors"][0]["template_version"]["template_code"]
        == template.pk
    )


def test_template_api_updates_draft_and_searches_by_name(
    actor: User,
) -> None:
    client = Client()
    client.force_login(actor)
    template = CreateChecklistTemplateService().execute(template_command(actor))
    draft = template.versions.get()
    other = CreateChecklistTemplateService().execute(
        CreateChecklistTemplateCommand(
            actor=actor,
            name="Checklist financeiro",
            description="",
            default_due_hours=24,
            items=(item("FINANCEIRO"),),
        )
    )

    update = client.put(
        reverse(
            "workflow-configuration-api:template-version-update",
            kwargs={"version_id": draft.pk},
        ),
        data={
            "expected_version": template.version,
            "name": "Checklist de tecnologia revisado",
            "description": "Revisão.",
            "default_due_hours": 8,
            "items": [
                {
                    "code": "ACESSOS_V2",
                    "question": "Os acessos foram revisados?",
                    "response_type": "BOOLEAN",
                    "is_required": True,
                    "blocks_process": True,
                    "requires_evidence": False,
                    "allows_pending": True,
                    "display_order": 1,
                    "config": {},
                }
            ],
        },
        content_type="application/json",
    )
    assert update.status_code == 200
    assert update.json()["id"] == template.pk
    assert update.json()["code"] == template.pk
    assert update.json()["name"] == "Checklist de tecnologia revisado"
    assert update.json()["versions"][0]["items"][0]["code"] == "ACESSOS_V2"

    search = client.get(
        reverse("workflow-configuration-api:template-list"),
        {"q": "TECNOLOGIA"},
    )
    assert search.status_code == 200
    assert [row["id"] for row in search.json()["results"]] == [template.pk]
    assert other.pk not in [row["id"] for row in search.json()["results"]]


@pytest.mark.django_db(transaction=True)
def test_numeric_template_identifier_migration_preserves_forward_and_rollback() -> None:
    previous = [("templates_engine", "0002_make_templates_sector_neutral")]
    current = [("templates_engine", "0003_use_numeric_template_identifier_and_edit_drafts")]
    executor = MigrationExecutor(connection)
    executor.migrate(previous)
    old_apps = executor.loader.project_state(previous).apps
    old_template_model = old_apps.get_model("templates_engine", "ChecklistTemplate")
    legacy = old_template_model.objects.create(
        code="CODIGO_MANUAL",
        name="Template existente",
        description="",
    )

    try:
        executor = MigrationExecutor(connection)
        executor.migrate(current)
        current_apps = executor.loader.project_state(current).apps
        current_template_model = current_apps.get_model(
            "templates_engine",
            "ChecklistTemplate",
        )
        normalized = current_template_model.objects.get(pk=legacy.pk)
        assert normalized.code == str(legacy.pk)

        rollback_pk = legacy.pk + 100
        current_template_model.objects.create(
            id=rollback_pk,
            code=str(rollback_pk),
            name="Template criado depois",
            description="",
        )
        executor = MigrationExecutor(connection)
        executor.migrate(previous)
        rollback_apps = executor.loader.project_state(previous).apps
        rollback_template_model = rollback_apps.get_model(
            "templates_engine",
            "ChecklistTemplate",
        )
        assert rollback_template_model.objects.get(pk=legacy.pk).code == str(legacy.pk)
        assert rollback_template_model.objects.get(pk=rollback_pk).code == str(rollback_pk)
    finally:
        MigrationExecutor(connection).migrate(current)
