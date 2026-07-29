"""Versioned workflow configuration, authorization and publication."""

from __future__ import annotations

from typing import Any

import pytest
from django.contrib.auth.models import Permission
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import IntegrityError
from django.test import Client
from django.urls import reverse

from apps.accounts.models import User
from apps.sectors.models import ValidationSector
from apps.templates_engine.models import (
    ChecklistResponseType,
    ChecklistTemplate,
    ChecklistTemplateItem,
    ValidationGroupSector,
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


def template_command(
    actor: User,
    sector: ValidationSector,
) -> CreateChecklistTemplateCommand:
    return CreateChecklistTemplateCommand(
        actor=actor,
        code="TI_DESLIGAMENTO",
        sector_id=sector.pk,
        name="Checklist de TI",
        description="Validações mínimas de TI.",
        default_due_hours=12,
        items=(item(),),
    )


def publish_template(actor: User, sector: ValidationSector) -> ChecklistTemplate:
    template = CreateChecklistTemplateService().execute(template_command(actor, sector))
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
    sector: ValidationSector,
) -> None:
    with pytest.raises(PermissionDenied, match="grupos e templates"):
        CreateChecklistTemplateService().execute(template_command(plain_user, sector))

    assert not ChecklistTemplate.objects.exists()
    assert not WorkflowConfigurationAuditEvent.objects.exists()


def test_template_is_created_published_and_audited(
    actor: User,
    sector: ValidationSector,
) -> None:
    template = CreateChecklistTemplateService().execute(template_command(actor, sector))
    version = template.versions.get()

    assert version.status == VersionStatus.DRAFT
    assert version.version_number == 1
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
    sector: ValidationSector,
) -> None:
    template = publish_template(actor, sector)
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
    template = publish_template(actor, sector)
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


def test_group_rejects_template_from_another_sector(
    actor: User,
    sector: ValidationSector,
) -> None:
    template = publish_template(actor, sector)
    template_version = template.current_version
    assert template_version is not None
    other = ValidationSector.objects.create(
        code="FINANCEIRO",
        name="Financeiro",
        default_due_hours=24,
    )

    with pytest.raises(ValidationError, match="mesmo setor"):
        CreateValidationGroupService().execute(
            CreateValidationGroupCommand(
                actor=actor,
                code="INVALIDO",
                name="Inválido",
                description="",
                sectors=(
                    GroupSectorValue(
                        sector_id=other.pk,
                        template_version_id=template_version.pk,
                        is_required=True,
                        blocks_process=True,
                        due_hours_override=None,
                        display_order=1,
                    ),
                ),
            )
        )

    assert not ValidationGroupSector.objects.filter(sector=other).exists()


def test_audit_failure_rolls_back_template(
    actor: User,
    sector: ValidationSector,
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
        CreateChecklistTemplateService().execute(template_command(actor, sector))

    assert not ChecklistTemplate.objects.exists()
    assert not ChecklistTemplateItem.objects.exists()


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
        "code": "TI_DESLIGAMENTO",
        "sector_id": sector.pk,
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
