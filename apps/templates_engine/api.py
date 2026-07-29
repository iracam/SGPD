"""API for creating and publishing workflow configuration."""

from __future__ import annotations

from typing import Any, cast

from django.db.models import QuerySet
from django.shortcuts import get_object_or_404
from rest_framework.permissions import BasePermission, IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.authorization import has_permission
from apps.accounts.models import User
from apps.sectors.models import ValidationSector

from .models import (
    ChecklistTemplate,
    ChecklistTemplateItem,
    ChecklistTemplateVersion,
    ValidationGroup,
    ValidationGroupSector,
    ValidationGroupVersion,
)
from .serializers import (
    ChecklistTemplateCreateSerializer,
    ChecklistTemplateDraftUpdateSerializer,
    ChecklistVersionSerializer,
    PublishVersionSerializer,
    ValidationGroupCreateSerializer,
    ValidationGroupVersionSerializer,
)
from .services import (
    MANAGE_WORKFLOW_CONFIGURATION_PERMISSION,
    ChecklistItemValue,
    CreateChecklistTemplateCommand,
    CreateChecklistTemplateService,
    CreateChecklistTemplateVersionCommand,
    CreateChecklistTemplateVersionService,
    CreateValidationGroupCommand,
    CreateValidationGroupService,
    CreateValidationGroupVersionCommand,
    CreateValidationGroupVersionService,
    GroupSectorValue,
    PublishChecklistTemplateVersionCommand,
    PublishChecklistTemplateVersionService,
    PublishValidationGroupVersionCommand,
    PublishValidationGroupVersionService,
    UpdateChecklistTemplateDraftCommand,
    UpdateChecklistTemplateDraftService,
)

DEFAULT_PAGE_SIZE = 50
MAX_PAGE_SIZE = 200


def template_item_payload(item: ChecklistTemplateItem) -> dict[str, Any]:
    return {
        "id": item.pk,
        "code": item.code,
        "question": item.question,
        "response_type": item.response_type,
        "is_required": item.is_required,
        "blocks_process": item.blocks_process,
        "requires_evidence": item.requires_evidence,
        "allows_pending": item.allows_pending,
        "display_order": item.display_order,
        "config": item.config,
    }


def template_version_payload(
    version: ChecklistTemplateVersion,
) -> dict[str, Any]:
    return {
        "id": version.pk,
        "version_number": version.version_number,
        "status": version.status,
        "default_due_hours": version.default_due_hours,
        "created_at": version.created_at.isoformat(),
        "published_at": (
            version.published_at.isoformat() if version.published_at is not None else None
        ),
        "items": [
            template_item_payload(item) for item in version.items.all().order_by("display_order")
        ],
    }


def template_payload(template: ChecklistTemplate) -> dict[str, Any]:
    return {
        "id": template.pk,
        "code": template.pk,
        "name": template.name,
        "description": template.description,
        "is_active": template.is_active,
        "current_version_id": template.current_version_id,
        "version": template.version,
        "versions": [
            template_version_payload(version)
            for version in template.versions.all().order_by("-version_number")
        ],
    }


def group_rule_payload(rule: ValidationGroupSector) -> dict[str, Any]:
    return {
        "id": rule.pk,
        "sector": {
            "id": rule.sector_id,
            "code": rule.sector.code,
            "name": rule.sector.name,
        },
        "template_version": {
            "id": rule.template_version_id,
            "template_id": rule.template_version.template_id,
            "template_code": rule.template_version.template_id,
            "version_number": rule.template_version.version_number,
            "status": rule.template_version.status,
        },
        "is_required": rule.is_required,
        "blocks_process": rule.blocks_process,
        "due_hours_override": rule.due_hours_override,
        "display_order": rule.display_order,
    }


def group_version_payload(version: ValidationGroupVersion) -> dict[str, Any]:
    return {
        "id": version.pk,
        "version_number": version.version_number,
        "status": version.status,
        "created_at": version.created_at.isoformat(),
        "published_at": (
            version.published_at.isoformat() if version.published_at is not None else None
        ),
        "sectors": [
            group_rule_payload(rule)
            for rule in version.sector_rules.all().order_by("display_order")
        ],
    }


def group_payload(group: ValidationGroup) -> dict[str, Any]:
    return {
        "id": group.pk,
        "code": group.code,
        "name": group.name,
        "description": group.description,
        "is_active": group.is_active,
        "current_version_id": group.current_version_id,
        "version": group.version,
        "versions": [
            group_version_payload(version)
            for version in group.versions.all().order_by("-version_number")
        ],
    }


def template_queryset() -> QuerySet[ChecklistTemplate]:
    return (
        ChecklistTemplate.objects.select_related("current_version")
        .prefetch_related("versions__items")
        .order_by("name", "pk")
    )


def group_queryset() -> QuerySet[ValidationGroup]:
    return (
        ValidationGroup.objects.select_related("current_version")
        .prefetch_related(
            "versions__sector_rules__sector",
            "versions__sector_rules__template_version__template",
        )
        .order_by("code")
    )


def _items(data: list[dict[str, Any]]) -> tuple[ChecklistItemValue, ...]:
    return tuple(
        ChecklistItemValue(
            code=item["code"],
            question=item["question"],
            response_type=item["response_type"],
            is_required=item["is_required"],
            blocks_process=item["blocks_process"],
            requires_evidence=item["requires_evidence"],
            allows_pending=item["allows_pending"],
            display_order=item["display_order"],
            config=item["config"],
        )
        for item in data
    )


def _group_sectors(data: list[dict[str, Any]]) -> tuple[GroupSectorValue, ...]:
    return tuple(
        GroupSectorValue(
            sector_id=item["sector_id"],
            template_version_id=item["template_version_id"],
            is_required=item["is_required"],
            blocks_process=item["blocks_process"],
            due_hours_override=item.get("due_hours_override"),
            display_order=item["display_order"],
        )
        for item in data
    )


class HasWorkflowConfigurationPermission(BasePermission):
    def has_permission(self, request: Request, view: APIView) -> bool:
        user = request.user
        return isinstance(user, User) and has_permission(
            user,
            MANAGE_WORKFLOW_CONFIGURATION_PERMISSION,
        )


class WorkflowConfigurationAPIView(APIView):
    permission_classes = [IsAuthenticated, HasWorkflowConfigurationPermission]

    def actor(self, request: Request) -> User:
        return cast(User, request.user)

    def page(self, request: Request) -> tuple[int, int]:
        try:
            offset = max(0, int(request.query_params.get("offset", 0)))
            limit = int(request.query_params.get("limit", DEFAULT_PAGE_SIZE))
        except ValueError:
            offset, limit = 0, DEFAULT_PAGE_SIZE
        return offset, max(1, min(limit, MAX_PAGE_SIZE))


class WorkflowSectorListView(WorkflowConfigurationAPIView):
    def get(self, request: Request) -> Response:
        sectors = ValidationSector.objects.filter(is_active=True).order_by("code")
        return Response(
            {
                "results": [
                    {
                        "id": sector.pk,
                        "code": sector.code,
                        "name": sector.name,
                        "default_due_hours": sector.default_due_hours,
                    }
                    for sector in sectors
                ]
            }
        )


class ChecklistTemplateListCreateView(WorkflowConfigurationAPIView):
    def get(self, request: Request) -> Response:
        offset, limit = self.page(request)
        templates = template_queryset()
        query = request.query_params.get("q", "").strip()
        if query:
            templates = templates.filter(name__icontains=query[:120])
        return Response(
            {
                "offset": offset,
                "limit": limit,
                "results": [template_payload(item) for item in templates[offset : offset + limit]],
            }
        )

    def post(self, request: Request) -> Response:
        serializer = ChecklistTemplateCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = cast(dict[str, Any], serializer.validated_data)
        template = CreateChecklistTemplateService().execute(
            CreateChecklistTemplateCommand(
                actor=self.actor(request),
                name=data["name"],
                description=data["description"],
                default_due_hours=data.get("default_due_hours"),
                items=_items(data["items"]),
            )
        )
        return Response(
            template_payload(template_queryset().get(pk=template.pk)),
            status=201,
        )


class ChecklistTemplateVersionCreateView(WorkflowConfigurationAPIView):
    def post(self, request: Request, template_id: int) -> Response:
        get_object_or_404(ChecklistTemplate, pk=template_id)
        serializer = ChecklistVersionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = cast(dict[str, Any], serializer.validated_data)
        if "expected_version" not in data:
            from rest_framework import serializers

            raise serializers.ValidationError({"expected_version": "Este campo é obrigatório."})
        version = CreateChecklistTemplateVersionService().execute(
            CreateChecklistTemplateVersionCommand(
                actor=self.actor(request),
                template_id=template_id,
                expected_version=data["expected_version"],
                default_due_hours=data.get("default_due_hours"),
                items=_items(data["items"]),
            )
        )
        return Response(template_version_payload(version), status=201)


class ChecklistTemplateDraftUpdateView(WorkflowConfigurationAPIView):
    def put(self, request: Request, version_id: int) -> Response:
        get_object_or_404(ChecklistTemplateVersion, pk=version_id)
        serializer = ChecklistTemplateDraftUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = cast(dict[str, Any], serializer.validated_data)
        version = UpdateChecklistTemplateDraftService().execute(
            UpdateChecklistTemplateDraftCommand(
                actor=self.actor(request),
                version_id=version_id,
                expected_template_version=data["expected_version"],
                name=data["name"],
                description=data["description"],
                default_due_hours=data.get("default_due_hours"),
                items=_items(data["items"]),
            )
        )
        return Response(
            template_payload(template_queryset().get(pk=version.template_id)),
        )


class ChecklistTemplatePublishView(WorkflowConfigurationAPIView):
    def post(self, request: Request, version_id: int) -> Response:
        get_object_or_404(ChecklistTemplateVersion, pk=version_id)
        serializer = PublishVersionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = cast(dict[str, Any], serializer.validated_data)
        version = PublishChecklistTemplateVersionService().execute(
            PublishChecklistTemplateVersionCommand(
                actor=self.actor(request),
                version_id=version_id,
                expected_template_version=data["expected_version"],
            )
        )
        return Response(template_version_payload(version))


class ValidationGroupListCreateView(WorkflowConfigurationAPIView):
    def get(self, request: Request) -> Response:
        offset, limit = self.page(request)
        groups = group_queryset()
        return Response(
            {
                "offset": offset,
                "limit": limit,
                "results": [group_payload(item) for item in groups[offset : offset + limit]],
            }
        )

    def post(self, request: Request) -> Response:
        serializer = ValidationGroupCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = cast(dict[str, Any], serializer.validated_data)
        group = CreateValidationGroupService().execute(
            CreateValidationGroupCommand(
                actor=self.actor(request),
                code=data["code"],
                name=data["name"],
                description=data["description"],
                sectors=_group_sectors(data["sectors"]),
            )
        )
        return Response(group_payload(group_queryset().get(pk=group.pk)), status=201)


class ValidationGroupVersionCreateView(WorkflowConfigurationAPIView):
    def post(self, request: Request, group_id: int) -> Response:
        get_object_or_404(ValidationGroup, pk=group_id)
        serializer = ValidationGroupVersionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = cast(dict[str, Any], serializer.validated_data)
        if "expected_version" not in data:
            from rest_framework import serializers

            raise serializers.ValidationError({"expected_version": "Este campo é obrigatório."})
        version = CreateValidationGroupVersionService().execute(
            CreateValidationGroupVersionCommand(
                actor=self.actor(request),
                group_id=group_id,
                expected_version=data["expected_version"],
                sectors=_group_sectors(data["sectors"]),
            )
        )
        return Response(group_version_payload(version), status=201)


class ValidationGroupPublishView(WorkflowConfigurationAPIView):
    def post(self, request: Request, version_id: int) -> Response:
        get_object_or_404(ValidationGroupVersion, pk=version_id)
        serializer = PublishVersionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = cast(dict[str, Any], serializer.validated_data)
        version = PublishValidationGroupVersionService().execute(
            PublishValidationGroupVersionCommand(
                actor=self.actor(request),
                version_id=version_id,
                expected_group_version=data["expected_version"],
            )
        )
        return Response(group_version_payload(version))
