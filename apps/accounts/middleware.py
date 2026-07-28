"""Account-specific request guards."""

from __future__ import annotations

from collections.abc import Callable
from typing import cast

from django.http import HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import redirect
from django.urls import reverse

from .models import User

API_PREFIX = "/api/"


class PasswordChangeRequiredMiddleware:
    """Force temporary-password rotation without blocking operational endpoints.

    Server-side navigation is redirected. API callers cannot follow a redirect
    meaningfully, so they receive a typed 403 and the SPA routes the user to the
    password screen. Dropping the guard for ``/api/`` would silently remove the
    obligation to rotate a temporary password.
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
        if user.is_authenticated and user.must_change_password:
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
                allowed_paths = {
                    reverse("accounts:change-own-password"),
                    reverse("accounts:logout"),
                }
                if path not in allowed_paths and not path.startswith(("/static/", "/health/")):
                    return redirect("accounts:change-own-password")
        return self.get_response(request)
