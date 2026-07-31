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
    ChecklistTemplateVersion,
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
    CreateValidationGroupVersionCommand,
    CreateValidationGroupVersionService,
    DeleteChecklistTemplateDraftCommand,
    DeleteChecklistTemplateDraftService,
    DeleteValidationGroupDraftCommand,
    DeleteValidationGroupDraftService,
    GroupSectorValue,
    PublishChecklistTemplateVersionCommand,
    PublishChecklistTemplateVersionService,
    PublishValidationGroupVersionCommand,
    PublishValidationGroupVersionService,
    UpdateChecklistTemplateDraftCommand,
    UpdateChecklistTemplateDraftService,
    UpdateValidationGroupDraftCommand,
    UpdateValidationGroupDraftService,
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
        question=f"{code}: os acessos foram encerrados?",
        response_type=ChecklistResponseType.BOOLEAN,
        is_required=True,
        blocks_process=True,
        requires_evidence=False,
        allows_pending=True,
        display_order=order,
        config={},
    )


def test_question_allows_only_automatic_code_fill_from_empty_database_value(
    actor: User,
) -> None:
    template = ChecklistTemplate.objects.create(
        code="FIXTURE",
        name="Template para compatibilidade Oracle",
    )
    version = ChecklistTemplateVersion.objects.create(
        template=template,
        version_number=1,
        created_by=actor,
    )
    question = ChecklistTemplateItem.objects.create(
        template_version=version,
        code="",
        question="Código automático foi preenchido?",
        response_type=ChecklistResponseType.BOOLEAN,
        display_order=1,
    )

    question.code = str(question.pk)
    question.save(update_fields=("code",))
    question.refresh_from_db()

    assert question.code == str(question.pk)


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
    checklist_item = version.items.get()
    assert checklist_item.code == str(checklist_item.pk)
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
    with pytest.raises(ValidationError, match="Somente versões de template em rascunho"):
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
    first_item = first.items.get()
    assert first_item.code == str(first_item.pk)
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


def test_group_draft_can_be_edited_in_place_and_is_audited(
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
            name="Grupo original",
            description="Antes da revisão.",
            sectors=(
                GroupSectorValue(
                    sector_id=sector.pk,
                    template_version_id=template_version.pk,
                    is_required=True,
                    blocks_process=True,
                    due_hours_override=None,
                    display_order=1,
                ),
            ),
        )
    )
    draft = group.versions.get()
    previous_rule = draft.sector_rules.get()

    updated = UpdateValidationGroupDraftService().execute(
        UpdateValidationGroupDraftCommand(
            actor=actor,
            version_id=draft.pk,
            expected_group_version=group.version,
            name="Grupo revisado",
            description="Pronto para publicação.",
            sectors=(
                GroupSectorValue(
                    sector_id=other.pk,
                    template_version_id=template_version.pk,
                    is_required=True,
                    blocks_process=False,
                    due_hours_override=8,
                    display_order=1,
                ),
            ),
        )
    )
    group.refresh_from_db()

    assert updated.pk == draft.pk
    assert group.name == "Grupo revisado"
    assert group.description == "Pronto para publicação."
    assert group.version == 2
    assert not draft.sector_rules.filter(pk=previous_rule.pk).exists()
    updated_rule = draft.sector_rules.get()
    assert updated_rule.sector_id == other.pk
    assert updated_rule.due_hours_override == 8
    event = WorkflowConfigurationAuditEvent.objects.get(event_type="GROUP_DRAFT_UPDATED")
    assert event.entity_id == draft.pk
    assert event.data["previous_rules"][0]["sector_id"] == sector.pk
    assert event.data["rules"][0]["sector_id"] == other.pk


def test_published_group_cannot_be_edited_in_place(
    actor: User,
    sector: ValidationSector,
) -> None:
    template = publish_template(actor)
    template_version = template.current_version
    assert template_version is not None
    group = CreateValidationGroupService().execute(
        CreateValidationGroupCommand(
            actor=actor,
            name="Grupo publicado",
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
    group.refresh_from_db()

    with pytest.raises(ValidationError, match="Somente uma versão de grupo em rascunho"):
        UpdateValidationGroupDraftService().execute(
            UpdateValidationGroupDraftCommand(
                actor=actor,
                version_id=version.pk,
                expected_group_version=group.version,
                name="Não deve mudar",
                description="",
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

    group.refresh_from_db()
    assert group.name == "Grupo publicado"
    assert version.sector_rules.get().due_hours_override is None


def test_group_draft_update_rejects_stale_version_and_permission(
    actor: User,
    plain_user: User,
    sector: ValidationSector,
) -> None:
    template = publish_template(actor)
    template_version = template.current_version
    assert template_version is not None
    group = CreateValidationGroupService().execute(
        CreateValidationGroupCommand(
            actor=actor,
            name="Grupo protegido",
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
            ),
        )
    )
    draft = group.versions.get()

    def command(user: User, expected_version: int) -> UpdateValidationGroupDraftCommand:
        return UpdateValidationGroupDraftCommand(
            actor=user,
            version_id=draft.pk,
            expected_group_version=expected_version,
            name="Não deve mudar",
            description="",
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

    with pytest.raises(ValidationError, match="outra sessão"):
        UpdateValidationGroupDraftService().execute(command(actor, group.version + 1))
    with pytest.raises(PermissionDenied, match="grupos e templates"):
        UpdateValidationGroupDraftService().execute(command(plain_user, group.version))

    group.refresh_from_db()
    assert group.name == "Grupo protegido"
    assert draft.sector_rules.get().due_hours_override is None


def test_group_draft_update_rolls_back_when_audit_fails(
    actor: User,
    sector: ValidationSector,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    template = publish_template(actor)
    template_version = template.current_version
    assert template_version is not None
    group = CreateValidationGroupService().execute(
        CreateValidationGroupCommand(
            actor=actor,
            name="Grupo original",
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
            ),
        )
    )
    draft = group.versions.get()
    previous_rule = draft.sector_rules.get()

    def fail_create(**kwargs: Any) -> None:
        raise IntegrityError("audit unavailable")

    monkeypatch.setattr(WorkflowConfigurationAuditEvent.objects, "create", fail_create)
    with pytest.raises(IntegrityError, match="audit unavailable"):
        UpdateValidationGroupDraftService().execute(
            UpdateValidationGroupDraftCommand(
                actor=actor,
                version_id=draft.pk,
                expected_group_version=group.version,
                name="Não deve persistir",
                description="",
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

    group.refresh_from_db()
    assert group.name == "Grupo original"
    assert group.version == 1
    persisted_rule = draft.sector_rules.get()
    assert persisted_rule.pk == previous_rule.pk
    assert persisted_rule.due_hours_override is None


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
    previous_item = draft.items.get()

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
    updated_item = updated.items.get()
    assert updated_item.code == str(updated_item.pk)
    assert template.name == "Checklist corporativo"
    assert template.description == "Conteúdo revisado."
    assert template.version == 2
    event = WorkflowConfigurationAuditEvent.objects.get(event_type="TPL_DRAFT_UPDATED")
    assert event.entity_id == draft.pk
    assert event.data["previous_item_codes"] == [str(previous_item.pk)]
    assert event.data["item_codes"] == [str(updated_item.pk)]


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
    published_item = published.items.get()
    assert published_item.code == str(published_item.pk)


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
    draft_item = draft.items.get()
    assert draft_item.code == str(draft_item.pk)


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
    draft_item = draft.items.get()
    assert draft_item.code == str(draft_item.pk)


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


def test_template_draft_can_be_deleted_but_published_and_initial_cannot(
    actor: User,
) -> None:
    template = CreateChecklistTemplateService().execute(template_command(actor))
    initial_draft = template.versions.get()
    with pytest.raises(ValidationError, match="rascunho inicial"):
        DeleteChecklistTemplateDraftService().execute(
            DeleteChecklistTemplateDraftCommand(
                actor=actor,
                version_id=initial_draft.pk,
                expected_template_version=template.version,
            )
        )

    PublishChecklistTemplateVersionService().execute(
        PublishChecklistTemplateVersionCommand(
            actor=actor,
            version_id=initial_draft.pk,
            expected_template_version=template.version,
        )
    )
    template.refresh_from_db()
    with pytest.raises(ValidationError, match="rascunho pode ser excluída"):
        DeleteChecklistTemplateDraftService().execute(
            DeleteChecklistTemplateDraftCommand(
                actor=actor,
                version_id=initial_draft.pk,
                expected_template_version=template.version,
            )
        )

    draft = CreateChecklistTemplateVersionService().execute(
        CreateChecklistTemplateVersionCommand(
            actor=actor,
            template_id=template.pk,
            expected_version=template.version,
            default_due_hours=8,
            items=(item("VERSAO_2"),),
        )
    )
    template.refresh_from_db()
    expected_version_after_delete = template.version + 1

    DeleteChecklistTemplateDraftService().execute(
        DeleteChecklistTemplateDraftCommand(
            actor=actor,
            version_id=draft.pk,
            expected_template_version=template.version,
        )
    )
    template.refresh_from_db()

    assert not template.versions.filter(pk=draft.pk).exists()
    assert template.current_version_id == initial_draft.pk
    assert template.version == expected_version_after_delete
    assert WorkflowConfigurationAuditEvent.objects.filter(
        event_type="TPL_DRAFT_DELETED",
        entity_id=draft.pk,
    ).exists()


def test_group_draft_can_be_deleted_keeping_published_version(
    actor: User,
    sector: ValidationSector,
) -> None:
    template = publish_template(actor)
    template_version = template.current_version
    assert template_version is not None
    sector_value = GroupSectorValue(
        sector_id=sector.pk,
        template_version_id=template_version.pk,
        is_required=True,
        blocks_process=True,
        due_hours_override=None,
        display_order=1,
    )
    group = CreateValidationGroupService().execute(
        CreateValidationGroupCommand(
            actor=actor,
            name="Desligamento padrão",
            description="",
            sectors=(sector_value,),
        )
    )
    published = group.versions.get()
    with pytest.raises(ValidationError, match="rascunho inicial"):
        DeleteValidationGroupDraftService().execute(
            DeleteValidationGroupDraftCommand(
                actor=actor,
                version_id=published.pk,
                expected_group_version=group.version,
            )
        )
    PublishValidationGroupVersionService().execute(
        PublishValidationGroupVersionCommand(
            actor=actor,
            version_id=published.pk,
            expected_group_version=group.version,
        )
    )
    group.refresh_from_db()
    draft = CreateValidationGroupVersionService().execute(
        CreateValidationGroupVersionCommand(
            actor=actor,
            group_id=group.pk,
            expected_version=group.version,
            sectors=(sector_value,),
        )
    )
    group.refresh_from_db()

    DeleteValidationGroupDraftService().execute(
        DeleteValidationGroupDraftCommand(
            actor=actor,
            version_id=draft.pk,
            expected_group_version=group.version,
        )
    )
    group.refresh_from_db()

    assert not group.versions.filter(pk=draft.pk).exists()
    assert group.current_version_id == published.pk
    assert WorkflowConfigurationAuditEvent.objects.filter(
        event_type="GROUP_DRAFT_DELETED",
        entity_id=draft.pk,
    ).exists()


def test_group_allows_only_one_draft_per_group(
    actor: User,
    sector: ValidationSector,
) -> None:
    template = publish_template(actor)
    template_version = template.current_version
    assert template_version is not None
    sector_value = GroupSectorValue(
        sector_id=sector.pk,
        template_version_id=template_version.pk,
        is_required=True,
        blocks_process=True,
        due_hours_override=None,
        display_order=1,
    )
    group = CreateValidationGroupService().execute(
        CreateValidationGroupCommand(
            actor=actor,
            name="Desligamento padrão",
            description="",
            sectors=(sector_value,),
        )
    )
    PublishValidationGroupVersionService().execute(
        PublishValidationGroupVersionCommand(
            actor=actor,
            version_id=group.versions.get().pk,
            expected_group_version=group.version,
        )
    )
    group.refresh_from_db()
    CreateValidationGroupVersionService().execute(
        CreateValidationGroupVersionCommand(
            actor=actor,
            group_id=group.pk,
            expected_version=group.version,
            sectors=(sector_value,),
        )
    )
    group.refresh_from_db()

    with pytest.raises(ValidationError, match="já possui uma versão em rascunho"):
        CreateValidationGroupVersionService().execute(
            CreateValidationGroupVersionCommand(
                actor=actor,
                group_id=group.pk,
                expected_version=group.version,
                sectors=(sector_value,),
            )
        )

    assert group.versions.filter(status=VersionStatus.DRAFT).count() == 1


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
        (
            "put",
            "workflow-configuration-api:group-version-update",
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
    response_item = response.json()["versions"][0]["items"][0]
    assert response_item["code"] == str(response_item["id"])
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
    assert group_response.json()["code"] == str(group_response.json()["id"])
    assert group_response.json()["versions"][0]["sectors"][0]["sector"]["code"] == "TECNOLOGIA"
    assert (
        group_response.json()["versions"][0]["sectors"][0]["template_version"]["template_code"]
        == template.pk
    )
    group_id = group_response.json()["id"]
    group_version_id = group_response.json()["versions"][0]["id"]

    group_update = client.put(
        reverse(
            "workflow-configuration-api:group-version-update",
            kwargs={"version_id": group_version_id},
        ),
        data={
            "expected_version": group_response.json()["version"],
            "name": "Padrão revisado",
            "description": "Revisão antes da publicação.",
            "sectors": [
                {
                    "sector_id": sector.pk,
                    "template_version_id": template_version.pk,
                    "is_required": True,
                    "blocks_process": False,
                    "due_hours_override": 8,
                    "display_order": 1,
                }
            ],
        },
        content_type="application/json",
    )

    assert group_update.status_code == 200
    assert group_update.json()["id"] == group_id
    assert group_update.json()["name"] == "Padrão revisado"
    assert group_update.json()["version"] == 2
    assert group_update.json()["versions"][0]["sectors"][0]["blocks_process"] is False


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
    updated_item = update.json()["versions"][0]["items"][0]
    assert updated_item["code"] == str(updated_item["id"])

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
        MigrationExecutor(connection).migrate(
            [("templates_engine", "0004_use_automatic_group_and_question_codes")]
        )


@pytest.mark.django_db(transaction=True)
def test_group_and_question_code_migration_preserves_forward_and_rollback() -> None:
    previous = [("templates_engine", "0003_use_numeric_template_identifier_and_edit_drafts")]
    current = [("templates_engine", "0004_use_automatic_group_and_question_codes")]
    executor = MigrationExecutor(connection)
    executor.migrate(previous)
    old_apps = executor.loader.project_state(previous).apps
    user_model = old_apps.get_model("accounts", "User")
    template_model = old_apps.get_model("templates_engine", "ChecklistTemplate")
    version_model = old_apps.get_model("templates_engine", "ChecklistTemplateVersion")
    item_model = old_apps.get_model("templates_engine", "ChecklistTemplateItem")
    group_model = old_apps.get_model("templates_engine", "ValidationGroup")

    actor = user_model.objects.create(
        username="migration.workflow",
        email="migration.workflow@example.invalid",
    )
    template = template_model.objects.create(
        code="1",
        name="Template da migration",
        description="",
    )
    version = version_model.objects.create(
        template=template,
        version_number=1,
        created_by=actor,
    )
    legacy_item = item_model.objects.create(
        template_version=version,
        code="PERGUNTA_MANUAL",
        question="Pergunta existente?",
        response_type="BOOLEAN",
        display_order=1,
    )
    legacy_group = group_model.objects.create(
        code="GRUPO_MANUAL",
        name="Grupo existente",
        description="",
    )

    try:
        executor = MigrationExecutor(connection)
        executor.migrate(current)
        current_apps = executor.loader.project_state(current).apps
        current_item_model = current_apps.get_model(
            "templates_engine",
            "ChecklistTemplateItem",
        )
        current_group_model = current_apps.get_model(
            "templates_engine",
            "ValidationGroup",
        )
        assert current_item_model.objects.get(pk=legacy_item.pk).code == str(legacy_item.pk)
        assert current_group_model.objects.get(pk=legacy_group.pk).code == str(legacy_group.pk)

        executor = MigrationExecutor(connection)
        executor.migrate(previous)
        rollback_apps = executor.loader.project_state(previous).apps
        rollback_item_model = rollback_apps.get_model(
            "templates_engine",
            "ChecklistTemplateItem",
        )
        rollback_group_model = rollback_apps.get_model(
            "templates_engine",
            "ValidationGroup",
        )
        assert rollback_item_model.objects.get(pk=legacy_item.pk).code == str(legacy_item.pk)
        assert rollback_group_model.objects.get(pk=legacy_group.pk).code == str(legacy_group.pk)
    finally:
        MigrationExecutor(connection).migrate(current)
