"""Account-specific request guards."""

from __future__ import annotations

from collections.abc import Callable
from typing import cast

from django.http import HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import redirect
from django.urls import reverse

from apps.integrations.active_directory.config import ActiveDirectoryConfig

from .models import User

API_PREFIX = "/api/"
SPA_PASSWORD_PATH = "/fe/senha"


class PasswordChangeRequiredMiddleware:
    """Force temporary-password rotation without blocking operational endpoints.

    API callers receive a typed 403 and the SPA routes the user to the password
    screen. Direct browser navigation is redirected to the SPA route. Dropping
    the guard for ``/api/`` would silently remove the obligation to rotate a
    temporary password.
    """

    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]) -> None:
        self.get_response = get_response

    def _api_allowed_paths(self) -> set[str]:
        return {
            reverse("auth-api:csrf"),
            reverse("auth-api:me"),
            reverse("auth-api:logout"),
            reverse("auth-api:change-password"),
        }

    def __call__(self, request: HttpRequest) -> HttpResponse:
        user = cast(User, request.user)
        password_is_managed_by_ad = (
            user.is_authenticated
            and user.has_ad_link
            and ActiveDirectoryConfig.from_settings().authentication_enabled
            and not user.is_superuser
        )
        if user.is_authenticated and user.must_change_password and not password_is_managed_by_ad:
            path = request.path
            if path.startswith(API_PREFIX):
                if path not in self._api_allowed_paths():
                    return JsonResponse(
                        {
                            "code": "password_change_required",
                            "message": "Troque a senha temporária antes de continuar.",
                        },
                        status=403,
                    )
            else:
                if path != SPA_PASSWORD_PATH and not path.startswith(("/static/", "/health/")):
                    return redirect(SPA_PASSWORD_PATH)
        return self.get_response(request)
