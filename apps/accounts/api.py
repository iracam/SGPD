"""Session-based authentication and authorization context for the SPA.

Authentication uses the Django session with CSRF protection on a single origin
(ADR-026). No token is issued and nothing about the session is exposed to
client-side storage.
"""

from __future__ import annotations

from typing import Any, cast

from django.contrib.auth import authenticate, update_session_auth_hash
from django.contrib.auth import login as django_login
from django.contrib.auth import logout as django_logout
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import ensure_csrf_cookie
from rest_framework.authentication import SessionAuthentication
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.throttling import AnonRateThrottle
from rest_framework.views import APIView

from apps.integrations.senior.permissions import SENIOR_REFERENCE_PERMISSION
from config.api import api_error

from .authorization import active_assignments, allowed_company_codes
from .models import AccountEventType, User
from .serializers import ChangeOwnPasswordSerializer, LoginSerializer
from .services import (
    ChangeOwnPasswordCommand,
    ChangeOwnPasswordService,
    record_authentication_event,
)

#: Permissions the SPA may gate navigation on. The key is the codename, which is
#: what the client uses; authorization itself is always re-evaluated server-side.
DELEGABLE_PERMISSIONS: tuple[str, ...] = (
    "accounts.manage_users",
    "accounts.manage_roles",
    "accounts.link_ad_identity",
    "accounts.view_account_audit",
    SENIOR_REFERENCE_PERMISSION,
)


def user_payload(user: User) -> dict[str, Any]:
    return {
        "id": user.pk,
        "username": user.username,
        "email": user.email,
        "first_name": user.first_name,
        "last_name": user.last_name,
        "display_name": user.get_full_name().strip() or user.username,
        "must_change_password": user.must_change_password,
        "is_superuser": user.is_superuser,
    }


def _codename(permission: str) -> str:
    _, _, codename = permission.partition(".")
    return codename or permission


def authorization_context(user: User) -> dict[str, Any]:
    """Describe what the user may reach, so the SPA can shape its navigation."""

    permissions: dict[str, Any] = {}
    features: dict[str, Any] = {}
    for permission in DELEGABLE_PERMISSIONS:
        companies = allowed_company_codes(user, permission)
        granted = companies != set()
        key = _codename(permission)
        permissions[key] = {
            "granted": granted,
            # None means every company; a list means exactly those.
            "companies": None if companies is None else sorted(companies),
        }
        features[key] = {"can_view": granted}

    assignments = (
        active_assignments(user).select_related("role").order_by("role__code", "scope_key")
    )
    scopes = [
        {
            "role": assignment.role.code,
            "scope_type": assignment.scope_type,
            "company_code": assignment.company_code,
            "branch_code": assignment.branch_code,
            "valid_until": (
                assignment.valid_until.isoformat() if assignment.valid_until is not None else None
            ),
        }
        for assignment in assignments
    ]

    return {
        "user": user_payload(user),
        "roles": sorted({scope["role"] for scope in scopes if isinstance(scope["role"], str)}),
        "permissions": permissions,
        "scopes": {"is_superuser": user.is_superuser, "assignments": scopes},
        "features": features,
        "meta": {"policy": "session", "server_time": timezone.now().isoformat()},
    }


class LoginRateThrottle(AnonRateThrottle):
    scope = "login"


@method_decorator(ensure_csrf_cookie, name="dispatch")
class CsrfView(APIView):
    """Hand the SPA a CSRF cookie before it can submit anything."""

    authentication_classes: list[type[SessionAuthentication]] = []
    permission_classes = [AllowAny]

    def get(self, request: Request) -> Response:
        return Response({"detail": "Cookie CSRF emitido."})


class LoginView(APIView):
    authentication_classes = [SessionAuthentication]
    permission_classes = [AllowAny]
    throttle_classes = [LoginRateThrottle]

    def post(self, request: Request) -> Response:
        # DRF only enforces CSRF once a session user exists, so an anonymous
        # login POST would otherwise be unprotected against login CSRF.
        SessionAuthentication().enforce_csrf(request)

        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        credentials = cast(dict[str, str], serializer.validated_data)

        user = authenticate(
            request._request,
            username=credentials["username"],
            password=credentials["password"],
        )
        if not isinstance(user, User):
            record_authentication_event(
                event_type=AccountEventType.LOGIN_FAILED,
                user=None,
                reason="Tentativa de autenticação pela API rejeitada.",
            )
            return api_error(
                code="invalid_credentials",
                message="Usuário ou senha inválidos.",
                status_code=401,
            )

        django_login(request._request, user)
        record_authentication_event(
            event_type=AccountEventType.LOGIN,
            user=user,
            reason="Autenticação local concluída pela API.",
        )
        return Response(user_payload(user))


class LogoutView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request: Request) -> Response:
        user = cast(User, request.user)
        record_authentication_event(
            event_type=AccountEventType.LOGOUT,
            user=user,
            reason="Encerramento explícito da sessão pela API.",
        )
        django_logout(request._request)
        return Response(status=204)


class CurrentUserView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request: Request) -> Response:
        return Response(user_payload(cast(User, request.user)))


class AuthorizationContextView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request: Request) -> Response:
        return Response(authorization_context(cast(User, request.user)))


class ChangeOwnPasswordView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request: Request) -> Response:
        serializer = ChangeOwnPasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        payload = cast(dict[str, str], serializer.validated_data)

        user = ChangeOwnPasswordService().execute(
            ChangeOwnPasswordCommand(
                user_id=cast(User, request.user).pk,
                current_password=payload["old_password"],
                new_password=payload["new_password"],
            )
        )
        # Keep the session alive; the password hash the session was signed with
        # has just changed.
        update_session_auth_hash(request._request, user)
        return Response(user_payload(user))
