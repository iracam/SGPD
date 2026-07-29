"""Functional configuration API for validation sectors."""

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
from apps.accounts.models import (
    RESPONSIBLE_SECTOR_ROLE_CODE,
    RoleAssignment,
    ScopeType,
    User,
)

from .authorization import responsibility_is_effective
from .models import SectorResponsible, SectorScope, ValidationSector
from .serializers import (
    SectorCreateSerializer,
    SectorResponsibleAssignSerializer,
    SectorResponsibleRevokeSerializer,
    SectorResponsibleUpdateSerializer,
    SectorUpdateSerializer,
)
from .services import (
    MANAGE_SECTORS_PERMISSION,
    AssignSectorResponsibleCommand,
    AssignSectorResponsibleService,
    CreateSectorCommand,
    CreateSectorService,
    RevokeSectorResponsibleCommand,
    RevokeSectorResponsibleService,
    SectorScopeValue,
    UpdateSectorCommand,
    UpdateSectorResponsibleCommand,
    UpdateSectorResponsibleService,
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


def sector_payload(sector: ValidationSector) -> dict[str, Any]:
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
        "scopes": [scope_payload(scope) for scope in sector.scopes.all().order_by("scope_key")],
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
        sectors = ValidationSector.objects.select_related("escalation_sector").prefetch_related(
            "scopes"
        )
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
                code=data["code"],
                name=data["name"],
                description=data["description"],
                default_due_hours=data["default_due_hours"],
                blocks_process=data["blocks_process"],
                allows_amount=data["allows_amount"],
                requires_evidence=data["requires_evidence"],
                escalation_sector_id=data.get("escalation_sector_id"),
                scopes=_scope_values(data["scopes"]),
                reason=data["reason"],
            )
        )
        sector = (
            ValidationSector.objects.select_related("escalation_sector")
            .prefetch_related("scopes")
            .get(pk=sector.pk)
        )
        return Response(sector_payload(sector), status=201)


class SectorDetailView(SectorsAPIView):
    def get(self, request: Request, sector_id: int) -> Response:
        sector = get_object_or_404(
            ValidationSector.objects.select_related("escalation_sector").prefetch_related("scopes"),
            pk=sector_id,
        )
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
                reason=data["reason"],
            )
        )
        sector = (
            ValidationSector.objects.select_related("escalation_sector")
            .prefetch_related("scopes")
            .get(pk=sector.pk)
        )
        return Response(sector_payload(sector))


def responsible_payload(responsibility: SectorResponsible) -> dict[str, Any]:
    user = responsibility.user
    sector = responsibility.sector
    return {
        "id": responsibility.pk,
        "sector": {
            "id": sector.pk,
            "code": sector.code,
            "name": sector.name,
            "is_active": sector.is_active,
        },
        "user": {
            "id": user.pk,
            "username": user.username,
            "display_name": user.get_full_name().strip() or user.username,
            "email": user.email,
            "is_active": user.is_active,
        },
        "scope_type": responsibility.scope_type,
        "company_code": responsibility.company_code,
        "branch_code": responsibility.branch_code,
        "scope_key": responsibility.scope_key,
        "valid_from": responsibility.valid_from.isoformat(),
        "valid_until": (
            responsibility.valid_until.isoformat()
            if responsibility.valid_until is not None
            else None
        ),
        "is_active": responsibility.is_active,
        "is_effective": responsibility_is_effective(responsibility),
        "assigned_at": responsibility.assigned_at.isoformat(),
        "updated_at": responsibility.updated_at.isoformat(),
        "revoked_at": (
            responsibility.revoked_at.isoformat() if responsibility.revoked_at is not None else None
        ),
        "version": responsibility.version,
    }


def _responsibility_queryset() -> QuerySet[SectorResponsible]:
    now = timezone.now()
    effective_roles = (
        RoleAssignment.objects.filter(
            role__code=RESPONSIBLE_SECTOR_ROLE_CODE,
            role__is_active=True,
            is_active=True,
            valid_from__lte=now,
        )
        .filter(Q(valid_until__isnull=True) | Q(valid_until__gt=now))
        .select_related("role")
        .order_by("scope_key")
    )
    return SectorResponsible.objects.select_related(
        "sector",
        "user",
        "assigned_by",
        "updated_by",
        "revoked_by",
    ).prefetch_related(
        Prefetch(
            "user__role_assignments",
            queryset=effective_roles,
            to_attr="effective_responsible_role_assignments",
        )
    )


class SectorResponsibleListCreateView(SectorsAPIView):
    def get(self, request: Request) -> Response:
        offset, limit = self.page(request)
        responsibilities = _responsibility_queryset()
        sector_id = request.query_params.get("sector")
        user_id = request.query_params.get("user")
        if sector_id and sector_id.isdigit():
            responsibilities = responsibilities.filter(sector_id=int(sector_id))
        if user_id and user_id.isdigit():
            responsibilities = responsibilities.filter(user_id=int(user_id))
        active = request.query_params.get("is_active")
        if active in {"true", "false"}:
            responsibilities = responsibilities.filter(is_active=active == "true")
        results = responsibilities[offset : offset + limit]
        return Response(
            {
                "offset": offset,
                "limit": limit,
                "results": [responsible_payload(item) for item in results],
            }
        )

    def post(self, request: Request) -> Response:
        serializer = SectorResponsibleAssignSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = cast(dict[str, Any], serializer.validated_data)
        responsibility = AssignSectorResponsibleService().execute(
            AssignSectorResponsibleCommand(
                actor=self.actor(request),
                sector_id=data["sector_id"],
                user_id=data["user_id"],
                scope_type=ScopeType(data["scope_type"]),
                company_code=data.get("company_code"),
                branch_code=data.get("branch_code"),
                valid_from=data.get("valid_from"),
                valid_until=data.get("valid_until"),
                reason=data["reason"],
            )
        )
        responsibility = _responsibility_queryset().get(pk=responsibility.pk)
        return Response(responsible_payload(responsibility), status=201)


class SectorResponsibleDetailView(SectorsAPIView):
    def get(self, request: Request, responsibility_id: int) -> Response:
        responsibility = get_object_or_404(
            _responsibility_queryset(),
            pk=responsibility_id,
        )
        return Response(responsible_payload(responsibility))

    def patch(self, request: Request, responsibility_id: int) -> Response:
        get_object_or_404(SectorResponsible, pk=responsibility_id)
        serializer = SectorResponsibleUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = cast(dict[str, Any], serializer.validated_data)
        responsibility = UpdateSectorResponsibleService().execute(
            UpdateSectorResponsibleCommand(
                actor=self.actor(request),
                responsibility_id=responsibility_id,
                expected_version=data["version"],
                valid_from=data["valid_from"],
                valid_until=data.get("valid_until"),
                reason=data["reason"],
            )
        )
        responsibility = _responsibility_queryset().get(pk=responsibility.pk)
        return Response(responsible_payload(responsibility))


class SectorResponsibleRevokeView(SectorsAPIView):
    def post(self, request: Request, responsibility_id: int) -> Response:
        get_object_or_404(SectorResponsible, pk=responsibility_id)
        serializer = SectorResponsibleRevokeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = cast(dict[str, Any], serializer.validated_data)
        responsibility = RevokeSectorResponsibleService().execute(
            RevokeSectorResponsibleCommand(
                actor=self.actor(request),
                responsibility_id=responsibility_id,
                expected_version=data["version"],
                reason=data["reason"],
            )
        )
        responsibility = _responsibility_queryset().get(pk=responsibility.pk)
        return Response(responsible_payload(responsibility))


def candidate_payload(user: User) -> dict[str, Any]:
    assignments = cast(
        list[RoleAssignment],
        getattr(user, "responsible_role_assignments", []),
    )
    return {
        "id": user.pk,
        "username": user.username,
        "display_name": user.get_full_name().strip() or user.username,
        "email": user.email,
        "role_scopes": [
            {
                "scope_type": assignment.scope_type,
                "company_code": assignment.company_code,
                "branch_code": assignment.branch_code,
                "scope_key": assignment.scope_key,
                "valid_from": assignment.valid_from.isoformat(),
                "valid_until": (
                    assignment.valid_until.isoformat()
                    if assignment.valid_until is not None
                    else None
                ),
            }
            for assignment in assignments
        ],
    }


class SectorResponsibleCandidatesView(SectorsAPIView):
    def get(self, request: Request) -> Response:
        offset, limit = self.page(request)
        now = timezone.now()
        role_assignments = (
            RoleAssignment.objects.filter(
                role__code=RESPONSIBLE_SECTOR_ROLE_CODE,
                role__is_active=True,
                is_active=True,
                valid_from__lte=now,
            )
            .filter(Q(valid_until__isnull=True) | Q(valid_until__gt=now))
            .select_related("role")
            .order_by("scope_key")
        )
        users = (
            User.objects.filter(
                is_active=True,
                pk__in=role_assignments.values("user_id"),
            )
            .prefetch_related(
                Prefetch(
                    "role_assignments",
                    queryset=role_assignments,
                    to_attr="responsible_role_assignments",
                )
            )
            .order_by("username")
        )
        query = request.query_params.get("q", "").strip()[:100]
        if query:
            users = users.filter(
                Q(username__icontains=query)
                | Q(first_name__icontains=query)
                | Q(last_name__icontains=query)
                | Q(email__icontains=query)
            )
        results = users[offset : offset + limit]
        return Response(
            {
                "offset": offset,
                "limit": limit,
                "results": [candidate_payload(user) for user in results],
            }
        )
