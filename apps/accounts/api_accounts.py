"""Account administration API.

Every endpoint is a thin shell: it validates shape, calls the service and
translates the result. The services revalidate authorization at their own
boundary (ADR-024), so this layer never becomes the only guard.
"""

from __future__ import annotations

import logging
from typing import Any, cast

from django.contrib.auth.models import Permission
from django.db.models import Count, Prefetch, Q, QuerySet
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework.permissions import BasePermission, IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.integrations.active_directory.config import ActiveDirectoryConfig
from apps.integrations.active_directory.exceptions import (
    DirectoryConfigurationError,
    DirectoryContractError,
    DirectoryIdentityNotFoundError,
    DirectoryUnavailableError,
)
from config.api import api_error

from .api import user_payload
from .authorization import has_global_authority, has_permission
from .models import (
    FUNCTIONAL_ROLE_CODES,
    AccountAuditEvent,
    Role,
    RoleAssignment,
    ScopeType,
    User,
)
from .serializers import (
    AdLinkSerializer,
    ResetPasswordSerializer,
    RoleAssignmentSerializer,
    UserCreateSerializer,
    UserUpdateSerializer,
    VersionSerializer,
)
from .services import (
    LINK_AD_IDENTITY_PERMISSION,
    MANAGE_USERS_PERMISSION,
    ROLE_AUTHORITY_MESSAGE,
    AssignRoleCommand,
    AssignRoleService,
    CreateUserCommand,
    CreateUserService,
    InitialRoleAssignmentCommand,
    LinkAdIdentityCommand,
    LinkAdIdentityService,
    LinkDirectoryIdentityService,
    ResetPasswordCommand,
    ResetPasswordService,
    RevokeRoleCommand,
    RevokeRoleService,
    UnlinkAdIdentityCommand,
    UnlinkAdIdentityService,
    UpdateUserCommand,
    UpdateUserService,
)

VIEW_ACCOUNT_AUDIT_PERMISSION = "accounts.view_account_audit"

DEFAULT_PAGE_SIZE = 50
MAX_PAGE_SIZE = 200

logger = logging.getLogger(__name__)


def _isoformat(value: Any) -> str | None:
    return value.isoformat() if value is not None else None


def permission_payload(permission: Permission) -> dict[str, Any]:
    return {
        "id": permission.pk,
        "codename": permission.codename,
        "name": permission.name,
    }


def user_detail_payload(user: User) -> dict[str, Any]:
    directory_config = ActiveDirectoryConfig.from_settings()
    payload = user_payload(user)
    payload.update(
        {
            "is_active": user.is_active,
            "version": user.version,
            "date_joined": _isoformat(user.date_joined),
            "last_login": _isoformat(user.last_login),
            "ad_identifier": user.ad_identifier or None,
            "ad_username": user.ad_username or None,
            "ad_linked_at": _isoformat(user.ad_linked_at),
            "ad_linked_by": (user.ad_linked_by.username if user.ad_linked_by else None),
            "ad_authentication_enabled": directory_config.authentication_enabled,
            "local_password_allowed": directory_config.allows_local_password(
                has_ad_link=user.has_ad_link,
                is_superuser=user.is_superuser,
            ),
            "sector_link_count": getattr(user, "sector_link_count", 0),
            "effective_sector_count": getattr(user, "effective_sector_count", 0),
        }
    )
    return payload


def _user_queryset(*, with_sector_links: bool = False) -> QuerySet[User]:
    now = timezone.now()
    queryset = User.objects.annotate(
        sector_link_count=Count(
            "sector_responsibilities",
            filter=Q(sector_responsibilities__is_active=True),
            distinct=True,
        ),
        effective_sector_count=Count(
            "sector_responsibilities",
            filter=(
                Q(is_active=True)
                & Q(sector_responsibilities__is_active=True)
                & Q(sector_responsibilities__sector__is_active=True)
                & Q(sector_responsibilities__valid_from__lte=now)
                & (
                    Q(sector_responsibilities__valid_until__isnull=True)
                    | Q(sector_responsibilities__valid_until__gt=now)
                )
            ),
            distinct=True,
        ),
    ).order_by("username")
    if with_sector_links:
        from apps.sectors.models import SectorResponsible

        queryset = queryset.prefetch_related(
            Prefetch(
                "sector_responsibilities",
                queryset=(
                    SectorResponsible.objects.filter(is_active=True)
                    .select_related("sector")
                    .prefetch_related("sector__scopes")
                    .order_by("sector__name", "sector_id")
                ),
                to_attr="active_sector_links",
            )
        )
    return queryset


def sector_link_payload(link: Any) -> dict[str, Any]:
    from apps.sectors.authorization import responsibility_is_effective

    return {
        "id": link.pk,
        "sector": {
            "id": link.sector_id,
            "code": link.sector.code,
            "name": link.sector.name,
            "is_active": link.sector.is_active,
        },
        "valid_from": _isoformat(link.valid_from),
        "valid_until": _isoformat(link.valid_until),
        "is_effective": responsibility_is_effective(link),
        "inherited_scopes": [
            {
                "scope_type": scope.scope_type,
                "company_code": scope.company_code,
                "branch_code": scope.branch_code,
                "scope_key": scope.scope_key,
            }
            for scope in link.sector.scopes.all().order_by("scope_key")
        ],
    }


def refreshed_user_payload(user: User) -> dict[str, Any]:
    return user_detail_payload(_user_queryset().get(pk=user.pk))


def role_payload(role: Role) -> dict[str, Any]:
    return {
        "id": role.pk,
        "code": role.code,
        "name": role.name,
        "description": role.description,
        "is_active": role.is_active,
        "version": role.version,
        "permissions": [permission_payload(item) for item in role.permissions.all()],
    }


def assignment_payload(assignment: RoleAssignment) -> dict[str, Any]:
    return {
        "id": assignment.pk,
        "user_id": assignment.user_id,
        "role": {
            "id": assignment.role_id,
            "code": assignment.role.code,
            "name": assignment.role.name,
        },
        "scope_type": assignment.scope_type,
        "company_code": assignment.company_code,
        "branch_code": assignment.branch_code,
        "scope_key": assignment.scope_key,
        "valid_from": _isoformat(assignment.valid_from),
        "valid_until": _isoformat(assignment.valid_until),
        "is_active": assignment.is_active,
        "assigned_by": (assignment.assigned_by.username if assignment.assigned_by else None),
        "assigned_at": _isoformat(assignment.assigned_at),
        "revoked_by": (assignment.revoked_by.username if assignment.revoked_by else None),
        "revoked_at": _isoformat(assignment.revoked_at),
    }


def audit_payload(event: AccountAuditEvent) -> dict[str, Any]:
    return {
        "uuid": str(event.uuid),
        "event_type": event.event_type,
        "actor": event.actor.username if event.actor else None,
        "target_user": event.target_user.username if event.target_user else None,
        "entity_type": event.entity_type,
        "entity_id": event.entity_id,
        "occurred_at": _isoformat(event.occurred_at),
        "reason": event.reason,
        "changes": event.changes,
        "correlation_id": event.correlation_id,
    }


class HasAccountPermission(BasePermission):
    """Re-check the view's declared authority on every request."""

    def has_permission(self, request: Request, view: APIView) -> bool:
        user = request.user
        if not isinstance(user, User):
            return False
        if getattr(view, "requires_global_authority", False):
            # Papel não se delega: quem atribui é o SuperAdmin e mais ninguém.
            # A mensagem é legível porque a barra é regra de negócio conhecida,
            # não sonda de existência do recurso.
            self.message = ROLE_AUTHORITY_MESSAGE
            return has_global_authority(user)
        required = getattr(view, "required_permission", None)
        if required is None:
            return False
        return has_permission(user, required)


class AccountsAPIView(APIView):
    permission_classes = [IsAuthenticated, HasAccountPermission]
    required_permission: str
    #: Quando verdadeiro, `required_permission` não é consultada: o endpoint
    #: exige a autoridade global do SuperAdmin.
    requires_global_authority: bool = False

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
        queryset: QuerySet[Any],
        payload: Any,
        *,
        offset: int,
        limit: int,
    ) -> Response:
        return Response(
            {
                "offset": offset,
                "limit": limit,
                "results": [payload(item) for item in queryset[offset : offset + limit]],
            }
        )


class UserListCreateView(AccountsAPIView):
    required_permission = MANAGE_USERS_PERMISSION

    def get(self, request: Request) -> Response:
        offset, limit = self.page(request)
        users = _user_queryset()
        query = request.query_params.get("q", "").strip()
        if query:
            users = users.filter(
                Q(username__icontains=query)
                | Q(first_name__icontains=query)
                | Q(last_name__icontains=query)
                | Q(email__icontains=query)
            )
        return self.paginated(users, user_detail_payload, offset=offset, limit=limit)

    def post(self, request: Request) -> Response:
        actor = self.actor(request)
        initial_role_requested = (
            isinstance(request.data, dict) and request.data.get("initial_role") is not None
        )
        logger.info(
            "account_user_creation_requested",
            extra={
                "event_type": "USER_CREATION_REQUESTED",
                "actor_id": actor.pk,
                "initial_role_requested": initial_role_requested,
                "outcome": "received",
            },
        )
        serializer = UserCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = cast(dict[str, Any], serializer.validated_data)
        initial_role_data = data.get("initial_role")
        initial_role = None
        if initial_role_data is not None:
            initial_role = InitialRoleAssignmentCommand(
                role_id=initial_role_data["role_id"],
                scope_type=ScopeType(initial_role_data["scope_type"]),
                company_code=initial_role_data.get("company_code"),
                branch_code=initial_role_data.get("branch_code"),
                valid_from=initial_role_data.get("valid_from"),
                valid_until=initial_role_data.get("valid_until"),
            )

        user = CreateUserService().execute(
            CreateUserCommand(
                actor=actor,
                username=data["username"],
                email=data["email"],
                first_name=data["first_name"],
                last_name=data["last_name"],
                password=data["password"],
                must_change_password=data["must_change_password"],
                initial_role=initial_role,
            )
        )
        logger.info(
            "account_user_creation_completed",
            extra={
                "event_type": "USER_CREATED",
                "actor_id": actor.pk,
                "target_user_id": user.pk,
                "role_id": initial_role.role_id if initial_role is not None else None,
                "scope_type": (initial_role.scope_type if initial_role is not None else None),
                "initial_role_requested": initial_role is not None,
                "outcome": "completed",
            },
        )
        return Response(refreshed_user_payload(user), status=201)


class UserDetailView(AccountsAPIView):
    required_permission = MANAGE_USERS_PERMISSION

    def get(self, request: Request, user_id: int) -> Response:
        user = get_object_or_404(_user_queryset(with_sector_links=True), pk=user_id)
        assignments = user.role_assignments.select_related(
            "role", "assigned_by", "revoked_by"
        ).order_by("-is_active", "role__code", "scope_key")
        payload = user_detail_payload(user)
        payload["role_assignments"] = [assignment_payload(item) for item in assignments]
        payload["sector_responsibilities"] = [
            sector_link_payload(item)
            for item in cast(list[Any], getattr(user, "active_sector_links", []))
        ]
        return Response(payload)

    def patch(self, request: Request, user_id: int) -> Response:
        get_object_or_404(User, pk=user_id)
        serializer = UserUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = cast(dict[str, Any], serializer.validated_data)

        user = UpdateUserService().execute(
            UpdateUserCommand(
                actor=self.actor(request),
                user_id=user_id,
                expected_version=data["version"],
                email=data["email"],
                first_name=data["first_name"],
                last_name=data["last_name"],
                is_active=data["is_active"],
            )
        )
        return Response(refreshed_user_payload(user))


class UserResetPasswordView(AccountsAPIView):
    required_permission = MANAGE_USERS_PERMISSION

    def post(self, request: Request, user_id: int) -> Response:
        get_object_or_404(User, pk=user_id)
        serializer = ResetPasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = cast(dict[str, Any], serializer.validated_data)

        user = ResetPasswordService().execute(
            ResetPasswordCommand(
                actor=self.actor(request),
                user_id=user_id,
                password=data["password"],
                must_change_password=data["must_change_password"],
            )
        )
        return Response(refreshed_user_payload(user))


class UserRoleAssignmentView(AccountsAPIView):
    requires_global_authority = True

    def post(self, request: Request, user_id: int) -> Response:
        actor = self.actor(request)
        logger.info(
            "account_role_assignment_requested",
            extra={
                "event_type": "ROLE_ASSIGNMENT_REQUESTED",
                "actor_id": actor.pk,
                "target_user_id": user_id,
                "outcome": "received",
            },
        )
        get_object_or_404(User, pk=user_id)
        serializer = RoleAssignmentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = cast(dict[str, Any], serializer.validated_data)
        get_object_or_404(Role, pk=data["role_id"])

        assignment = AssignRoleService().execute(
            AssignRoleCommand(
                actor=actor,
                user_id=user_id,
                role_id=data["role_id"],
                scope_type=ScopeType(data["scope_type"]),
                company_code=data.get("company_code"),
                branch_code=data.get("branch_code"),
                valid_from=data.get("valid_from"),
                valid_until=data.get("valid_until"),
            )
        )
        logger.info(
            "account_role_assignment_completed",
            extra={
                "event_type": "ROLE_ASSIGNED",
                "actor_id": actor.pk,
                "target_user_id": user_id,
                "role_id": assignment.role_id,
                "assignment_id": assignment.pk,
                "scope_type": assignment.scope_type,
                "scope_key": assignment.scope_key,
                "outcome": "completed",
            },
        )
        return Response(assignment_payload(assignment), status=201)


class RoleAssignmentRevokeView(AccountsAPIView):
    requires_global_authority = True

    def post(self, request: Request, assignment_id: int) -> Response:
        get_object_or_404(RoleAssignment, pk=assignment_id)

        assignment = RevokeRoleService().execute(
            RevokeRoleCommand(
                actor=self.actor(request),
                assignment_id=assignment_id,
            )
        )
        return Response(assignment_payload(assignment))


class UserAdLinkView(AccountsAPIView):
    required_permission = LINK_AD_IDENTITY_PERMISSION

    def post(self, request: Request, user_id: int) -> Response:
        get_object_or_404(User, pk=user_id)
        serializer = AdLinkSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = cast(dict[str, Any], serializer.validated_data)

        command = LinkAdIdentityCommand(
            actor=self.actor(request),
            user_id=user_id,
            expected_version=data["version"],
            identifier=data["identifier"],
            username=data["username"],
        )
        try:
            if ActiveDirectoryConfig.from_settings().enabled:
                user = LinkDirectoryIdentityService().execute(command)
            else:
                user = LinkAdIdentityService().execute(command)
        except DirectoryConfigurationError as exc:
            return api_error(
                code="directory_not_configured",
                message=str(exc),
                status_code=503,
            )
        except DirectoryUnavailableError:
            return api_error(
                code="directory_unavailable",
                message="O Active Directory está indisponível. Tente novamente mais tarde.",
                status_code=503,
            )
        except DirectoryIdentityNotFoundError as exc:
            return api_error(
                code="directory_identity_not_found",
                message=str(exc),
                status_code=404,
            )
        except DirectoryContractError as exc:
            return api_error(
                code="directory_contract_error",
                message=str(exc),
                status_code=502,
            )
        return Response(refreshed_user_payload(user))


class UserAdUnlinkView(AccountsAPIView):
    required_permission = LINK_AD_IDENTITY_PERMISSION

    def post(self, request: Request, user_id: int) -> Response:
        get_object_or_404(User, pk=user_id)
        serializer = VersionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = cast(dict[str, Any], serializer.validated_data)

        user = UnlinkAdIdentityService().execute(
            UnlinkAdIdentityCommand(
                actor=self.actor(request),
                user_id=user_id,
                expected_version=data["version"],
            )
        )
        return Response(refreshed_user_payload(user))


class RoleListView(AccountsAPIView):
    # Ler o catálogo só serve para atribuir; segue a mesma barra do ato.
    requires_global_authority = True

    def get(self, request: Request) -> Response:
        offset, limit = self.page(request)
        roles = Role.objects.filter(
            code__in=FUNCTIONAL_ROLE_CODES,
            is_active=True,
        ).prefetch_related("permissions")
        return self.paginated(roles, role_payload, offset=offset, limit=limit)


class RoleDetailView(AccountsAPIView):
    requires_global_authority = True

    def get(self, request: Request, role_id: int) -> Response:
        role = get_object_or_404(
            Role.objects.prefetch_related("permissions"),
            pk=role_id,
            code__in=FUNCTIONAL_ROLE_CODES,
            is_active=True,
        )
        return Response(role_payload(role))


class AuditListView(AccountsAPIView):
    required_permission = VIEW_ACCOUNT_AUDIT_PERMISSION

    def get(self, request: Request) -> Response:
        offset, limit = self.page(request)
        events = AccountAuditEvent.objects.select_related("actor", "target_user")
        target_user = request.query_params.get("target_user")
        if target_user:
            try:
                events = events.filter(target_user_id=int(target_user))
            except ValueError:
                events = events.none()
        event_type = request.query_params.get("event_type")
        if event_type:
            events = events.filter(event_type=event_type)
        return self.paginated(events, audit_payload, offset=offset, limit=limit)
