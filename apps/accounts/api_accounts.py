"""Account administration API.

Every endpoint is a thin shell: it validates shape, calls the service and
translates the result. The services revalidate authorization at their own
boundary (ADR-024), so this layer never becomes the only guard.
"""

from __future__ import annotations

from typing import Any, cast

from django.contrib.auth.models import Permission
from django.db.models import Q, QuerySet
from django.shortcuts import get_object_or_404
from rest_framework.permissions import BasePermission, IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from .api import user_payload
from .authorization import has_permission
from .models import (
    AccountAuditEvent,
    Role,
    RoleAssignment,
    ScopeType,
    User,
)
from .serializers import (
    AdLinkSerializer,
    ReasonSerializer,
    ReasonVersionSerializer,
    ResetPasswordSerializer,
    RoleAssignmentSerializer,
    RoleCreateSerializer,
    RoleUpdateSerializer,
    UserCreateSerializer,
    UserUpdateSerializer,
)
from .services import (
    LINK_AD_IDENTITY_PERMISSION,
    MANAGE_ROLES_PERMISSION,
    MANAGE_USERS_PERMISSION,
    AssignRoleCommand,
    AssignRoleService,
    CreateRoleCommand,
    CreateRoleService,
    CreateUserCommand,
    CreateUserService,
    LinkAdIdentityCommand,
    LinkAdIdentityService,
    ResetPasswordCommand,
    ResetPasswordService,
    RevokeRoleCommand,
    RevokeRoleService,
    UnlinkAdIdentityCommand,
    UnlinkAdIdentityService,
    UpdateRoleCommand,
    UpdateRoleService,
    UpdateUserCommand,
    UpdateUserService,
    assignable_permissions,
)

VIEW_ACCOUNT_AUDIT_PERMISSION = "accounts.view_account_audit"

DEFAULT_PAGE_SIZE = 50
MAX_PAGE_SIZE = 200


def _isoformat(value: Any) -> str | None:
    return value.isoformat() if value is not None else None


def permission_payload(permission: Permission) -> dict[str, Any]:
    return {
        "id": permission.pk,
        "codename": permission.codename,
        "name": permission.name,
    }


def user_detail_payload(user: User) -> dict[str, Any]:
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
        }
    )
    return payload


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
        "role": {"id": assignment.role_id, "code": assignment.role.code},
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
    """Re-check the view's declared permission on every request."""

    def has_permission(self, request: Request, view: APIView) -> bool:
        required = getattr(view, "required_permission", None)
        if required is None:
            return False
        user = request.user
        if not isinstance(user, User):
            return False
        return has_permission(user, required)


class AccountsAPIView(APIView):
    permission_classes = [IsAuthenticated, HasAccountPermission]
    required_permission: str

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
        users = User.objects.order_by("username")
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
        serializer = UserCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = cast(dict[str, Any], serializer.validated_data)

        user = CreateUserService().execute(
            CreateUserCommand(
                actor=self.actor(request),
                username=data["username"],
                email=data["email"],
                first_name=data["first_name"],
                last_name=data["last_name"],
                password=data["password"],
                must_change_password=data["must_change_password"],
                reason=data["reason"],
            )
        )
        return Response(user_detail_payload(user), status=201)


class UserDetailView(AccountsAPIView):
    required_permission = MANAGE_USERS_PERMISSION

    def get(self, request: Request, user_id: int) -> Response:
        user = get_object_or_404(User, pk=user_id)
        assignments = user.role_assignments.select_related(
            "role", "assigned_by", "revoked_by"
        ).order_by("-is_active", "role__code", "scope_key")
        payload = user_detail_payload(user)
        payload["role_assignments"] = [assignment_payload(item) for item in assignments]
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
                reason=data["reason"],
            )
        )
        return Response(user_detail_payload(user))


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
                reason=data["reason"],
            )
        )
        return Response(user_detail_payload(user))


class UserRoleAssignmentView(AccountsAPIView):
    required_permission = MANAGE_ROLES_PERMISSION

    def post(self, request: Request, user_id: int) -> Response:
        get_object_or_404(User, pk=user_id)
        serializer = RoleAssignmentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = cast(dict[str, Any], serializer.validated_data)
        get_object_or_404(Role, pk=data["role_id"])

        assignment = AssignRoleService().execute(
            AssignRoleCommand(
                actor=self.actor(request),
                user_id=user_id,
                role_id=data["role_id"],
                scope_type=ScopeType(data["scope_type"]),
                company_code=data.get("company_code"),
                branch_code=data.get("branch_code"),
                valid_from=data.get("valid_from"),
                valid_until=data.get("valid_until"),
                reason=data["reason"],
            )
        )
        return Response(assignment_payload(assignment), status=201)


class RoleAssignmentRevokeView(AccountsAPIView):
    required_permission = MANAGE_ROLES_PERMISSION

    def post(self, request: Request, assignment_id: int) -> Response:
        get_object_or_404(RoleAssignment, pk=assignment_id)
        serializer = ReasonSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = cast(dict[str, Any], serializer.validated_data)

        assignment = RevokeRoleService().execute(
            RevokeRoleCommand(
                actor=self.actor(request),
                assignment_id=assignment_id,
                reason=data["reason"],
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

        user = LinkAdIdentityService().execute(
            LinkAdIdentityCommand(
                actor=self.actor(request),
                user_id=user_id,
                expected_version=data["version"],
                identifier=data["identifier"],
                username=data["username"],
                reason=data["reason"],
            )
        )
        return Response(user_detail_payload(user))


class UserAdUnlinkView(AccountsAPIView):
    required_permission = LINK_AD_IDENTITY_PERMISSION

    def post(self, request: Request, user_id: int) -> Response:
        get_object_or_404(User, pk=user_id)
        serializer = ReasonVersionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = cast(dict[str, Any], serializer.validated_data)

        user = UnlinkAdIdentityService().execute(
            UnlinkAdIdentityCommand(
                actor=self.actor(request),
                user_id=user_id,
                expected_version=data["version"],
                reason=data["reason"],
            )
        )
        return Response(user_detail_payload(user))


class RoleListCreateView(AccountsAPIView):
    required_permission = MANAGE_ROLES_PERMISSION

    def get(self, request: Request) -> Response:
        offset, limit = self.page(request)
        roles = Role.objects.prefetch_related("permissions").order_by("code")
        return self.paginated(roles, role_payload, offset=offset, limit=limit)

    def post(self, request: Request) -> Response:
        serializer = RoleCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = cast(dict[str, Any], serializer.validated_data)

        role = CreateRoleService().execute(
            CreateRoleCommand(
                actor=self.actor(request),
                code=data["code"],
                name=data["name"],
                description=data["description"],
                permission_ids=tuple(data["permission_ids"]),
                reason=data["reason"],
            )
        )
        return Response(role_payload(role), status=201)


class RoleDetailView(AccountsAPIView):
    required_permission = MANAGE_ROLES_PERMISSION

    def get(self, request: Request, role_id: int) -> Response:
        role = get_object_or_404(Role.objects.prefetch_related("permissions"), pk=role_id)
        return Response(role_payload(role))

    def patch(self, request: Request, role_id: int) -> Response:
        get_object_or_404(Role, pk=role_id)
        serializer = RoleUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = cast(dict[str, Any], serializer.validated_data)

        role = UpdateRoleService().execute(
            UpdateRoleCommand(
                actor=self.actor(request),
                role_id=role_id,
                expected_version=data["version"],
                name=data["name"],
                description=data["description"],
                is_active=data["is_active"],
                permission_ids=tuple(data["permission_ids"]),
                reason=data["reason"],
            )
        )
        return Response(role_payload(role))


class PermissionListView(AccountsAPIView):
    required_permission = MANAGE_ROLES_PERMISSION

    def get(self, request: Request) -> Response:
        permissions = assignable_permissions().order_by("codename")
        return Response({"results": [permission_payload(item) for item in permissions]})


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
