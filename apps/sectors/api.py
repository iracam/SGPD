"""Functional configuration API for validation-sector aggregates."""

from __future__ import annotations

from typing import Any, cast

from django.db.models import Prefetch, Q, QuerySet
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework.permissions import BasePermission, IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.authorization import has_permission
from apps.accounts.models import ScopeType, User

from .authorization import responsibility_is_effective
from .models import SectorResponsible, SectorScope, ValidationSector
from .serializers import SectorCreateSerializer, SectorUpdateSerializer
from .services import (
    MANAGE_SECTORS_PERMISSION,
    CreateSectorCommand,
    CreateSectorService,
    SectorResponsibleValue,
    SectorScopeValue,
    UpdateSectorCommand,
    UpdateSectorService,
)

DEFAULT_PAGE_SIZE = 50
MAX_PAGE_SIZE = 200


def scope_payload(scope: SectorScope) -> dict[str, Any]:
    return {
        "scope_type": scope.scope_type,
        "company_code": scope.company_code,
        "branch_code": scope.branch_code,
        "scope_key": scope.scope_key,
    }


def responsible_payload(
    responsibility: SectorResponsible,
    *,
    inherited_scopes: list[dict[str, Any]],
) -> dict[str, Any]:
    user = responsibility.user
    now = timezone.now()
    is_effective = responsibility_is_effective(responsibility, at=now)
    return {
        "id": responsibility.pk,
        "user": {
            "id": user.pk,
            "username": user.username,
            "display_name": user.get_full_name().strip() or user.username,
            "email": user.email,
            "is_active": user.is_active,
        },
        "valid_from": responsibility.valid_from.isoformat(),
        "valid_until": (
            responsibility.valid_until.isoformat()
            if responsibility.valid_until is not None
            else None
        ),
        "is_active": responsibility.is_active,
        "is_effective": is_effective,
        "is_scheduled": (
            responsibility.is_active
            and user.is_active
            and responsibility.sector.is_active
            and responsibility.valid_from > now
        ),
        "inherited_scopes": inherited_scopes,
        "assigned_at": responsibility.assigned_at.isoformat(),
        "updated_at": responsibility.updated_at.isoformat(),
        "version": responsibility.version,
    }


def sector_payload(sector: ValidationSector) -> dict[str, Any]:
    scopes = [scope_payload(scope) for scope in sector.scopes.all().order_by("scope_key")]
    responsibilities = cast(
        list[SectorResponsible],
        getattr(sector, "active_responsibilities", []),
    )
    responsible_rows = [
        responsible_payload(item, inherited_scopes=scopes) for item in responsibilities
    ]
    effective_count = sum(1 for item in responsible_rows if item["is_effective"])
    scheduled_count = sum(1 for item in responsible_rows if item["is_scheduled"])
    return {
        "id": sector.pk,
        "code": sector.code,
        "name": sector.name,
        "description": sector.description,
        "is_active": sector.is_active,
        "default_due_hours": sector.default_due_hours,
        "blocks_process": sector.blocks_process,
        "allows_amount": sector.allows_amount,
        "requires_evidence": sector.requires_evidence,
        "escalation_sector": (
            {
                "id": sector.escalation_sector.pk,
                "code": sector.escalation_sector.code,
                "name": sector.escalation_sector.name,
            }
            if sector.escalation_sector is not None
            else None
        ),
        "scopes": scopes,
        "responsibles": responsible_rows,
        "effective_responsible_count": effective_count,
        "scheduled_responsible_count": scheduled_count,
        "has_effective_responsible": effective_count > 0,
        "version": sector.version,
        "created_at": sector.created_at.isoformat(),
        "updated_at": sector.updated_at.isoformat(),
    }


def _scope_values(data: list[dict[str, Any]]) -> tuple[SectorScopeValue, ...]:
    return tuple(
        SectorScopeValue(
            scope_type=ScopeType(item["scope_type"]),
            company_code=item.get("company_code"),
            branch_code=item.get("branch_code"),
        )
        for item in data
    )


def _responsible_values(
    data: list[dict[str, Any]],
) -> tuple[SectorResponsibleValue, ...]:
    return tuple(
        SectorResponsibleValue(
            user_id=item["user_id"],
            valid_from=item.get("valid_from"),
            valid_until=item.get("valid_until"),
        )
        for item in data
    )


def _sector_queryset() -> QuerySet[ValidationSector]:
    active_responsibilities = (
        SectorResponsible.objects.filter(is_active=True)
        .select_related("user", "sector")
        .order_by("user__username")
    )
    return (
        ValidationSector.objects.select_related("escalation_sector")
        .prefetch_related(
            "scopes",
            Prefetch(
                "responsibles",
                queryset=active_responsibilities,
                to_attr="active_responsibilities",
            ),
        )
        .order_by("name", "pk")
    )


class HasSectorPermission(BasePermission):
    def has_permission(self, request: Request, view: APIView) -> bool:
        user = request.user
        return isinstance(user, User) and has_permission(user, MANAGE_SECTORS_PERMISSION)


class SectorsAPIView(APIView):
    permission_classes = [IsAuthenticated, HasSectorPermission]

    def actor(self, request: Request) -> User:
        return cast(User, request.user)

    def page(self, request: Request) -> tuple[int, int]:
        try:
            offset = max(0, int(request.query_params.get("offset", 0)))
            limit = int(request.query_params.get("limit", DEFAULT_PAGE_SIZE))
        except ValueError:
            offset, limit = 0, DEFAULT_PAGE_SIZE
        return offset, max(1, min(limit, MAX_PAGE_SIZE))

    def paginated(
        self,
        queryset: QuerySet[ValidationSector],
        *,
        offset: int,
        limit: int,
    ) -> Response:
        return Response(
            {
                "offset": offset,
                "limit": limit,
                "results": [sector_payload(item) for item in queryset[offset : offset + limit]],
            }
        )


class SectorListCreateView(SectorsAPIView):
    def get(self, request: Request) -> Response:
        offset, limit = self.page(request)
        sectors = _sector_queryset()
        query = request.query_params.get("q", "").strip()[:100]
        if query:
            sectors = sectors.filter(Q(code__icontains=query) | Q(name__icontains=query))
        active = request.query_params.get("is_active")
        if active in {"true", "false"}:
            sectors = sectors.filter(is_active=active == "true")
        return self.paginated(sectors, offset=offset, limit=limit)

    def post(self, request: Request) -> Response:
        serializer = SectorCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = cast(dict[str, Any], serializer.validated_data)
        sector = CreateSectorService().execute(
            CreateSectorCommand(
                actor=self.actor(request),
                name=data["name"],
                description=data["description"],
                default_due_hours=data["default_due_hours"],
                blocks_process=data["blocks_process"],
                allows_amount=data["allows_amount"],
                requires_evidence=data["requires_evidence"],
                escalation_sector_id=data.get("escalation_sector_id"),
                scopes=_scope_values(data["scopes"]),
                responsibles=_responsible_values(data["responsibles"]),
            )
        )
        return Response(sector_payload(_sector_queryset().get(pk=sector.pk)), status=201)


class SectorDetailView(SectorsAPIView):
    def get(self, request: Request, sector_id: int) -> Response:
        sector = get_object_or_404(_sector_queryset(), pk=sector_id)
        return Response(sector_payload(sector))

    def patch(self, request: Request, sector_id: int) -> Response:
        get_object_or_404(ValidationSector, pk=sector_id)
        serializer = SectorUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = cast(dict[str, Any], serializer.validated_data)
        sector = UpdateSectorService().execute(
            UpdateSectorCommand(
                actor=self.actor(request),
                sector_id=sector_id,
                expected_version=data["version"],
                name=data["name"],
                description=data["description"],
                is_active=data["is_active"],
                default_due_hours=data["default_due_hours"],
                blocks_process=data["blocks_process"],
                allows_amount=data["allows_amount"],
                requires_evidence=data["requires_evidence"],
                escalation_sector_id=data.get("escalation_sector_id"),
                scopes=_scope_values(data["scopes"]),
                responsibles=_responsible_values(data["responsibles"]),
            )
        )
        return Response(sector_payload(_sector_queryset().get(pk=sector.pk)))


def candidate_payload(user: User) -> dict[str, Any]:
    return {
        "id": user.pk,
        "username": user.username,
        "display_name": user.get_full_name().strip() or user.username,
        "email": user.email,
        "is_active": user.is_active,
    }


class SectorResponsibleCandidatesView(SectorsAPIView):
    def get(self, request: Request) -> Response:
        offset, limit = self.page(request)
        users = User.objects.filter(is_active=True).order_by("username")
        query = request.query_params.get("q", "").strip()[:100]
        if query:
            users = users.filter(
                Q(username__icontains=query)
                | Q(first_name__icontains=query)
                | Q(last_name__icontains=query)
                | Q(email__icontains=query)
            )
        return Response(
            {
                "offset": offset,
                "limit": limit,
                "results": [candidate_payload(item) for item in users[offset : offset + limit]],
            }
        )
