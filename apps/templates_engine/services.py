"""Transactional services for versioned workflow configuration."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, cast

from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.utils import timezone

from apps.accounts.authorization import has_permission
from apps.accounts.models import User
from apps.sectors.models import ValidationSector
from config.middleware import correlation_id

from .models import (
    ChecklistResponseType,
    ChecklistTemplate,
    ChecklistTemplateItem,
    ChecklistTemplateVersion,
    ValidationGroup,
    ValidationGroupSector,
    ValidationGroupVersion,
    VersionStatus,
    WorkflowConfigurationAuditEvent,
    WorkflowConfigurationEventType,
)

MANAGE_WORKFLOW_CONFIGURATION_PERMISSION = "templates_engine.manage_workflow_configuration"


def _require_permission(actor: User) -> None:
    if not has_permission(actor, MANAGE_WORKFLOW_CONFIGURATION_PERMISSION):
        raise PermissionDenied("O ator não possui permissão para manter grupos e templates.")


def _required_text(value: str, field: str, message: str) -> str:
    normalized = value.strip()
    if not normalized:
        raise ValidationError({field: message})
    return normalized


def _audit(
    *,
    event_type: WorkflowConfigurationEventType,
    actor: User,
    entity_type: str,
    entity_id: int,
    data: dict[str, Any],
) -> None:
    WorkflowConfigurationAuditEvent.objects.create(
        event_type=event_type,
        actor=actor,
        entity_type=entity_type,
        entity_id=entity_id,
        data=data,
        correlation_id=correlation_id.get(),
    )


@dataclass(frozen=True, slots=True)
class ChecklistItemValue:
    question: str
    response_type: ChecklistResponseType
    is_required: bool
    blocks_process: bool
    requires_evidence: bool
    allows_pending: bool
    display_order: int
    config: dict[str, Any]


def _normalize_items(
    items: tuple[ChecklistItemValue, ...],
) -> tuple[ChecklistItemValue, ...]:
    if not items:
        raise ValidationError({"items": "Informe ao menos uma pergunta."})
    orders: set[int] = set()
    normalized: list[ChecklistItemValue] = []
    for index, item in enumerate(items):
        question = item.question.strip()
        if not question:
            raise ValidationError({f"items.{index}.question": "A pergunta é obrigatória."})
        if item.display_order <= 0:
            raise ValidationError(
                {f"items.{index}.display_order": "A ordem deve ser maior que zero."}
            )
        if item.display_order in orders:
            raise ValidationError({"items": f"A ordem {item.display_order} foi repetida."})
        orders.add(item.display_order)
        normalized.append(
            ChecklistItemValue(
                question=question,
                response_type=item.response_type,
                is_required=item.is_required,
                blocks_process=item.blocks_process,
                requires_evidence=item.requires_evidence,
                allows_pending=item.allows_pending,
                display_order=item.display_order,
                config=item.config,
            )
        )
    return tuple(sorted(normalized, key=lambda item: item.display_order))


def _validate_default_due_hours(default_due_hours: int | None) -> None:
    if default_due_hours is not None and default_due_hours <= 0:
        raise ValidationError({"default_due_hours": "O prazo do template deve ser maior que zero."})


def _create_template_items(
    *,
    version: ChecklistTemplateVersion,
    items: tuple[ChecklistItemValue, ...],
) -> tuple[ChecklistTemplateItem, ...]:
    created: list[ChecklistTemplateItem] = []
    for value in items:
        item = ChecklistTemplateItem(
            template_version=version,
            question=value.question,
            response_type=value.response_type,
            is_required=value.is_required,
            blocks_process=value.blocks_process,
            requires_evidence=value.requires_evidence,
            allows_pending=value.allows_pending,
            display_order=value.display_order,
            config=value.config,
        )
        item.full_clean()
        item.save()
        item.code = str(item.pk)
        item.full_clean()
        item.save(update_fields=("code",))
        created.append(item)
    return tuple(created)


def _create_template_version(
    *,
    template: ChecklistTemplate,
    actor: User,
    default_due_hours: int | None,
    items: tuple[ChecklistItemValue, ...],
) -> ChecklistTemplateVersion:
    normalized_items = _normalize_items(items)
    _validate_default_due_hours(default_due_hours)
    versions = list(
        ChecklistTemplateVersion.objects.select_for_update()
        .filter(template=template)
        .order_by("version_number")
    )
    version = ChecklistTemplateVersion.objects.create(
        template=template,
        version_number=(versions[-1].version_number + 1 if versions else 1),
        default_due_hours=default_due_hours,
        created_by=actor,
    )
    _create_template_items(version=version, items=normalized_items)
    _audit(
        event_type=WorkflowConfigurationEventType.TEMPLATE_VERSION_CREATED,
        actor=actor,
        entity_type="CHECKLIST_TEMPLATE_VERSION",
        entity_id=version.pk,
        data={
            "template_id": template.pk,
            "version_number": version.version_number,
            "item_count": len(normalized_items),
        },
    )
    return version


@dataclass(frozen=True, slots=True)
class CreateChecklistTemplateCommand:
    actor: User
    name: str
    description: str
    default_due_hours: int | None
    items: tuple[ChecklistItemValue, ...]


class CreateChecklistTemplateService:
    @transaction.atomic
    def execute(
        self,
        command: CreateChecklistTemplateCommand,
    ) -> ChecklistTemplate:
        _require_permission(command.actor)
        name = _required_text(
            command.name,
            "name",
            "O nome do template é obrigatório.",
        )
        template = ChecklistTemplate(
            name=name,
            description=command.description.strip(),
        )
        template.full_clean()
        template.save()
        template.code = str(template.pk)
        template.full_clean()
        template.save(update_fields=("code",))
        version = _create_template_version(
            template=template,
            actor=command.actor,
            default_due_hours=command.default_due_hours,
            items=command.items,
        )
        _audit(
            event_type=WorkflowConfigurationEventType.TEMPLATE_CREATED,
            actor=command.actor,
            entity_type="CHECKLIST_TEMPLATE",
            entity_id=template.pk,
            data={
                "template_id": template.pk,
                "initial_version_id": version.pk,
            },
        )
        return template


@dataclass(frozen=True, slots=True)
class UpdateChecklistTemplateDraftCommand:
    actor: User
    version_id: int
    expected_template_version: int
    name: str
    description: str
    default_due_hours: int | None
    items: tuple[ChecklistItemValue, ...]


class UpdateChecklistTemplateDraftService:
    @transaction.atomic
    def execute(
        self,
        command: UpdateChecklistTemplateDraftCommand,
    ) -> ChecklistTemplateVersion:
        _require_permission(command.actor)
        name = _required_text(command.name, "name", "O nome do template é obrigatório.")
        description = command.description.strip()
        normalized_items = _normalize_items(command.items)
        _validate_default_due_hours(command.default_due_hours)
        try:
            template_id = ChecklistTemplateVersion.objects.values_list(
                "template_id",
                flat=True,
            ).get(pk=command.version_id)
        except ChecklistTemplateVersion.DoesNotExist as exc:
            raise ChecklistTemplateVersion.DoesNotExist from exc

        template = ChecklistTemplate.objects.select_for_update().get(pk=template_id)
        versions: list[ChecklistTemplateVersion] = list(
            ChecklistTemplateVersion.objects.select_for_update()
            .filter(template=template)
            .order_by("pk")
        )
        version = next(
            (row for row in versions if row.pk == command.version_id),
            None,
        )
        if version is None:
            raise ChecklistTemplateVersion.DoesNotExist
        if template.version != command.expected_template_version:
            raise ValidationError("O template foi alterado por outra sessão. Recarregue a página.")
        if not template.is_active:
            raise ValidationError("O template precisa estar ativo.")
        if version.status != VersionStatus.DRAFT:
            raise ValidationError(
                "Somente uma versão em rascunho pode ser editada; crie uma nova versão."
            )

        persisted_items = list(
            ChecklistTemplateItem.objects.select_for_update()
            .filter(template_version=version)
            .order_by("display_order", "pk")
        )
        previous_name = template.name
        previous_description = template.description
        previous_due_hours = version.default_due_hours
        previous_codes = [item.code for item in persisted_items]
        for persisted_item in persisted_items:
            persisted_item.delete()

        version.default_due_hours = command.default_due_hours
        version.full_clean()
        version.save(update_fields=("default_due_hours",))
        created_items = _create_template_items(version=version, items=normalized_items)

        template.name = name
        template.description = description
        template.version += 1
        template.full_clean()
        template.save(update_fields=("name", "description", "version", "updated_at"))
        _audit(
            event_type=WorkflowConfigurationEventType.TEMPLATE_DRAFT_UPDATED,
            actor=command.actor,
            entity_type="CHECKLIST_TEMPLATE_VERSION",
            entity_id=version.pk,
            data={
                "template_id": template.pk,
                "version_number": version.version_number,
                "previous_name": previous_name,
                "name": template.name,
                "description_changed": previous_description != template.description,
                "previous_default_due_hours": previous_due_hours,
                "default_due_hours": version.default_due_hours,
                "previous_item_codes": previous_codes,
                "item_codes": [item.code for item in created_items],
                "item_count": len(normalized_items),
                "template_version": template.version,
            },
        )
        return version


@dataclass(frozen=True, slots=True)
class CreateChecklistTemplateVersionCommand:
    actor: User
    template_id: int
    expected_version: int
    default_due_hours: int | None
    items: tuple[ChecklistItemValue, ...]


class CreateChecklistTemplateVersionService:
    @transaction.atomic
    def execute(
        self,
        command: CreateChecklistTemplateVersionCommand,
    ) -> ChecklistTemplateVersion:
        _require_permission(command.actor)
        try:
            template = ChecklistTemplate.objects.select_for_update().get(pk=command.template_id)
        except ChecklistTemplate.DoesNotExist as exc:
            raise ChecklistTemplate.DoesNotExist from exc
        if template.version != command.expected_version:
            raise ValidationError("O template foi alterado por outra sessão. Recarregue a página.")
        if not template.is_active:
            raise ValidationError("O template precisa estar ativo.")
        draft_versions = list(
            ChecklistTemplateVersion.objects.select_for_update()
            .filter(template=template, status=VersionStatus.DRAFT)
            .order_by("pk")
        )
        if draft_versions:
            raise ValidationError(
                "O template já possui uma versão em rascunho. Edite-a antes de criar outra."
            )
        version = _create_template_version(
            template=template,
            actor=command.actor,
            default_due_hours=command.default_due_hours,
            items=command.items,
        )
        template.version += 1
        template.save(update_fields=("version", "updated_at"))
        return version


@dataclass(frozen=True, slots=True)
class PublishChecklistTemplateVersionCommand:
    actor: User
    version_id: int
    expected_template_version: int


class PublishChecklistTemplateVersionService:
    @transaction.atomic
    def execute(
        self,
        command: PublishChecklistTemplateVersionCommand,
    ) -> ChecklistTemplateVersion:
        _require_permission(command.actor)
        try:
            template_id = ChecklistTemplateVersion.objects.values_list(
                "template_id",
                flat=True,
            ).get(pk=command.version_id)
        except ChecklistTemplateVersion.DoesNotExist as exc:
            raise ChecklistTemplateVersion.DoesNotExist from exc
        template = ChecklistTemplate.objects.select_for_update().get(pk=template_id)
        all_versions = list(
            ChecklistTemplateVersion.objects.select_for_update()
            .filter(template=template)
            .order_by("pk")
        )
        version = next(
            (row for row in all_versions if row.pk == command.version_id),
            None,
        )
        if version is None:
            raise ChecklistTemplateVersion.DoesNotExist
        items = list(version.items.select_for_update().order_by("display_order"))
        if template.version != command.expected_template_version:
            raise ValidationError("O template foi alterado por outra sessão. Recarregue a página.")
        if version.status != VersionStatus.DRAFT:
            raise ValidationError("Somente uma versão em rascunho pode ser publicada.")
        if not template.is_active:
            raise ValidationError("O template precisa estar ativo.")
        if not items:
            raise ValidationError("A versão precisa possuir ao menos uma pergunta.")
        now = timezone.now()
        for previous in all_versions:
            if previous.status != VersionStatus.PUBLISHED:
                continue
            previous.status = VersionStatus.RETIRED
            previous.save(update_fields=("status",))
        version.status = VersionStatus.PUBLISHED
        version.published_by = command.actor
        version.published_at = now
        version.full_clean()
        version.save(update_fields=("status", "published_by", "published_at"))
        template.current_version = version
        template.version += 1
        template.full_clean()
        template.save(update_fields=("current_version", "version", "updated_at"))
        _audit(
            event_type=WorkflowConfigurationEventType.TEMPLATE_PUBLISHED,
            actor=command.actor,
            entity_type="CHECKLIST_TEMPLATE_VERSION",
            entity_id=version.pk,
            data={
                "template_id": template.pk,
                "version_number": version.version_number,
            },
        )
        return cast(ChecklistTemplateVersion, version)


@dataclass(frozen=True, slots=True)
class GroupSectorValue:
    sector_id: int
    template_version_id: int
    is_required: bool
    blocks_process: bool
    due_hours_override: int | None
    display_order: int


def _normalize_group_sectors(
    sectors: tuple[GroupSectorValue, ...],
) -> tuple[GroupSectorValue, ...]:
    if not sectors:
        raise ValidationError({"sectors": "Informe ao menos um setor."})
    sector_ids: set[int] = set()
    orders: set[int] = set()
    normalized: list[GroupSectorValue] = []
    for index, value in enumerate(sectors):
        if value.sector_id in sector_ids:
            raise ValidationError({"sectors": "O mesmo setor foi informado mais de uma vez."})
        if value.display_order <= 0 or value.display_order in orders:
            raise ValidationError(
                {f"sectors.{index}.display_order": "Informe uma ordem positiva e única."}
            )
        if value.due_hours_override is not None and value.due_hours_override <= 0:
            raise ValidationError(
                {
                    f"sectors.{index}.due_hours_override": (
                        "O prazo específico deve ser maior que zero."
                    )
                }
            )
        sector_ids.add(value.sector_id)
        orders.add(value.display_order)
        normalized.append(value)
    if not any(value.is_required for value in normalized):
        raise ValidationError({"sectors": "Informe ao menos um setor obrigatório."})
    return tuple(sorted(normalized, key=lambda value: value.display_order))


def _create_group_version(
    *,
    group: ValidationGroup,
    actor: User,
    sectors: tuple[GroupSectorValue, ...],
) -> ValidationGroupVersion:
    normalized = _normalize_group_sectors(sectors)
    sector_ids = {value.sector_id for value in normalized}
    template_version_ids = {value.template_version_id for value in normalized}
    locked_sectors = {
        sector.pk: sector
        for sector in ValidationSector.objects.select_for_update()
        .filter(pk__in=sector_ids)
        .order_by("pk")
    }
    template_versions = {
        version.pk: version
        for version in ChecklistTemplateVersion.objects.select_for_update()
        .filter(pk__in=template_version_ids)
        .select_related("template")
        .order_by("pk")
    }
    if locked_sectors.keys() != sector_ids:
        raise ValidationError({"sectors": "Um dos setores informados não existe."})
    if template_versions.keys() != template_version_ids:
        raise ValidationError({"sectors": "Uma das versões de template não existe."})
    versions = list(
        ValidationGroupVersion.objects.select_for_update()
        .filter(group=group)
        .order_by("version_number")
    )
    version = ValidationGroupVersion.objects.create(
        group=group,
        version_number=(versions[-1].version_number + 1 if versions else 1),
        created_by=actor,
    )
    for value in normalized:
        sector = locked_sectors[value.sector_id]
        template_version = template_versions[value.template_version_id]
        if not sector.is_active:
            raise ValidationError({"sectors": f"O setor {sector.code} está inativo."})
        rule = ValidationGroupSector(
            group_version=version,
            sector=sector,
            template_version=template_version,
            is_required=value.is_required,
            blocks_process=value.blocks_process,
            due_hours_override=value.due_hours_override,
            display_order=value.display_order,
        )
        rule.full_clean()
        rule.save()
    _audit(
        event_type=WorkflowConfigurationEventType.GROUP_VERSION_CREATED,
        actor=actor,
        entity_type="VALIDATION_GROUP_VERSION",
        entity_id=version.pk,
        data={
            "group_id": group.pk,
            "version_number": version.version_number,
            "sector_count": len(normalized),
        },
    )
    return version


@dataclass(frozen=True, slots=True)
class CreateValidationGroupCommand:
    actor: User
    name: str
    description: str
    sectors: tuple[GroupSectorValue, ...]


class CreateValidationGroupService:
    @transaction.atomic
    def execute(self, command: CreateValidationGroupCommand) -> ValidationGroup:
        _require_permission(command.actor)
        name = _required_text(
            command.name,
            "name",
            "O nome do grupo é obrigatório.",
        )
        group = ValidationGroup(
            name=name,
            description=command.description.strip(),
        )
        group.full_clean()
        group.save()
        group.code = str(group.pk)
        group.full_clean()
        group.save(update_fields=("code",))
        version = _create_group_version(
            group=group,
            actor=command.actor,
            sectors=command.sectors,
        )
        _audit(
            event_type=WorkflowConfigurationEventType.GROUP_CREATED,
            actor=command.actor,
            entity_type="VALIDATION_GROUP",
            entity_id=group.pk,
            data={"group_id": group.pk, "initial_version_id": version.pk},
        )
        return group


@dataclass(frozen=True, slots=True)
class UpdateValidationGroupDraftCommand:
    actor: User
    version_id: int
    expected_group_version: int
    name: str
    description: str
    sectors: tuple[GroupSectorValue, ...]


class UpdateValidationGroupDraftService:
    @transaction.atomic
    def execute(
        self,
        command: UpdateValidationGroupDraftCommand,
    ) -> ValidationGroupVersion:
        _require_permission(command.actor)
        name = _required_text(command.name, "name", "O nome do grupo é obrigatório.")
        description = command.description.strip()
        normalized_sectors = _normalize_group_sectors(command.sectors)
        try:
            group_id = ValidationGroupVersion.objects.values_list(
                "group_id",
                flat=True,
            ).get(pk=command.version_id)
        except ValidationGroupVersion.DoesNotExist as exc:
            raise ValidationGroupVersion.DoesNotExist from exc

        group = ValidationGroup.objects.select_for_update().get(pk=group_id)
        versions: list[ValidationGroupVersion] = list(
            ValidationGroupVersion.objects.select_for_update().filter(group=group).order_by("pk")
        )
        version = next(
            (row for row in versions if row.pk == command.version_id),
            None,
        )
        if version is None:
            raise ValidationGroupVersion.DoesNotExist
        if group.version != command.expected_group_version:
            raise ValidationError("O grupo foi alterado por outra sessão. Recarregue a página.")
        if not group.is_active:
            raise ValidationError("O grupo precisa estar ativo.")
        if version.status != VersionStatus.DRAFT:
            raise ValidationError(
                "Somente uma versão de grupo em rascunho pode ser editada; crie uma nova versão."
            )

        persisted_rules = list(
            ValidationGroupSector.objects.select_for_update()
            .filter(group_version=version)
            .select_related("sector", "template_version__template")
            .order_by("display_order", "pk")
        )
        sector_ids = {value.sector_id for value in normalized_sectors}
        template_version_ids = {value.template_version_id for value in normalized_sectors}
        locked_sectors = {
            sector.pk: sector
            for sector in ValidationSector.objects.select_for_update()
            .filter(pk__in=sector_ids)
            .order_by("pk")
        }
        template_versions = {
            template_version.pk: template_version
            for template_version in ChecklistTemplateVersion.objects.select_for_update()
            .filter(pk__in=template_version_ids)
            .select_related("template")
            .order_by("pk")
        }
        if locked_sectors.keys() != sector_ids:
            raise ValidationError({"sectors": "Um dos setores informados não existe."})
        if template_versions.keys() != template_version_ids:
            raise ValidationError({"sectors": "Uma das versões de template não existe."})

        previous_name = group.name
        previous_description = group.description
        previous_rules = [
            {
                "sector_id": rule.sector_id,
                "template_version_id": rule.template_version_id,
                "is_required": rule.is_required,
                "blocks_process": rule.blocks_process,
                "due_hours_override": rule.due_hours_override,
                "display_order": rule.display_order,
            }
            for rule in persisted_rules
        ]
        for persisted_rule in persisted_rules:
            persisted_rule.delete()
        for value in normalized_sectors:
            sector = locked_sectors[value.sector_id]
            template_version = template_versions[value.template_version_id]
            if not sector.is_active:
                raise ValidationError({"sectors": f"O setor {sector.code} está inativo."})
            rule = ValidationGroupSector(
                group_version=version,
                sector=sector,
                template_version=template_version,
                is_required=value.is_required,
                blocks_process=value.blocks_process,
                due_hours_override=value.due_hours_override,
                display_order=value.display_order,
            )
            rule.full_clean()
            rule.save()

        group.name = name
        group.description = description
        group.version += 1
        group.full_clean()
        group.save(update_fields=("name", "description", "version", "updated_at"))
        _audit(
            event_type=WorkflowConfigurationEventType.GROUP_DRAFT_UPDATED,
            actor=command.actor,
            entity_type="VALIDATION_GROUP_VERSION",
            entity_id=version.pk,
            data={
                "group_id": group.pk,
                "version_number": version.version_number,
                "previous_name": previous_name,
                "name": group.name,
                "description_changed": previous_description != group.description,
                "previous_rules": previous_rules,
                "rules": [
                    {
                        "sector_id": value.sector_id,
                        "template_version_id": value.template_version_id,
                        "is_required": value.is_required,
                        "blocks_process": value.blocks_process,
                        "due_hours_override": value.due_hours_override,
                        "display_order": value.display_order,
                    }
                    for value in normalized_sectors
                ],
                "group_version": group.version,
            },
        )
        return version


@dataclass(frozen=True, slots=True)
class CreateValidationGroupVersionCommand:
    actor: User
    group_id: int
    expected_version: int
    sectors: tuple[GroupSectorValue, ...]


class CreateValidationGroupVersionService:
    @transaction.atomic
    def execute(
        self,
        command: CreateValidationGroupVersionCommand,
    ) -> ValidationGroupVersion:
        _require_permission(command.actor)
        try:
            group = ValidationGroup.objects.select_for_update().get(pk=command.group_id)
        except ValidationGroup.DoesNotExist as exc:
            raise ValidationGroup.DoesNotExist from exc
        if group.version != command.expected_version:
            raise ValidationError("O grupo foi alterado por outra sessão. Recarregue a página.")
        if not group.is_active:
            raise ValidationError("O grupo precisa estar ativo.")
        version = _create_group_version(
            group=group,
            actor=command.actor,
            sectors=command.sectors,
        )
        group.version += 1
        group.save(update_fields=("version", "updated_at"))
        return version


@dataclass(frozen=True, slots=True)
class PublishValidationGroupVersionCommand:
    actor: User
    version_id: int
    expected_group_version: int


class PublishValidationGroupVersionService:
    @transaction.atomic
    def execute(
        self,
        command: PublishValidationGroupVersionCommand,
    ) -> ValidationGroupVersion:
        _require_permission(command.actor)
        try:
            version = (
                ValidationGroupVersion.objects.select_for_update()
                .select_related("group")
                .get(pk=command.version_id)
            )
        except ValidationGroupVersion.DoesNotExist as exc:
            raise ValidationGroupVersion.DoesNotExist from exc
        group = ValidationGroup.objects.select_for_update().get(pk=version.group_id)
        all_versions = list(
            ValidationGroupVersion.objects.select_for_update()
            .filter(group=group)
            .order_by("version_number")
        )
        rules = list(
            version.sector_rules.select_for_update()
            .select_related("sector", "template_version__template")
            .order_by("display_order")
        )
        if group.version != command.expected_group_version:
            raise ValidationError("O grupo foi alterado por outra sessão. Recarregue a página.")
        if version.status != VersionStatus.DRAFT:
            raise ValidationError("Somente uma versão em rascunho pode ser publicada.")
        if not group.is_active:
            raise ValidationError("O grupo precisa estar ativo.")
        if not rules or not any(rule.is_required for rule in rules):
            raise ValidationError("O grupo precisa possuir ao menos um setor obrigatório.")
        for rule in rules:
            if not rule.sector.is_active:
                raise ValidationError(f"O setor {rule.sector.code} está inativo.")
            if not rule.template_version.template.is_active:
                raise ValidationError(f"O template do setor {rule.sector.code} está inativo.")
            if rule.template_version.status not in {
                VersionStatus.PUBLISHED,
                VersionStatus.RETIRED,
            }:
                raise ValidationError(f"O template do setor {rule.sector.code} não está publicado.")
        now = timezone.now()
        for previous in all_versions:
            if previous.status != VersionStatus.PUBLISHED:
                continue
            previous.status = VersionStatus.RETIRED
            previous.save(update_fields=("status",))
        version.status = VersionStatus.PUBLISHED
        version.published_by = command.actor
        version.published_at = now
        version.full_clean()
        version.save(update_fields=("status", "published_by", "published_at"))
        group.current_version = version
        group.version += 1
        group.full_clean()
        group.save(update_fields=("current_version", "version", "updated_at"))
        _audit(
            event_type=WorkflowConfigurationEventType.GROUP_PUBLISHED,
            actor=command.actor,
            entity_type="VALIDATION_GROUP_VERSION",
            entity_id=version.pk,
            data={"group_id": group.pk, "version_number": version.version_number},
        )
        return cast(ValidationGroupVersion, version)
