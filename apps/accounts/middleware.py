"""Account-specific request guards."""

from __future__ import annotations

from collections.abc import Callable
from typing import cast

from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect
from django.urls import reverse

from .models import User


class PasswordChangeRequiredMiddleware:
    """Force temporary-password rotation without blocking operational endpoints."""

    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]) -> None:
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        user = cast(User, request.user)
        if user.is_authenticated and user.must_change_password:
            allowed_paths = {
                reverse("accounts:change-own-password"),
                reverse("accounts:logout"),
            }
            if request.path not in allowed_paths and not request.path.startswith(
                ("/static/", "/health/")
            ):
                return redirect("accounts:change-own-password")
        return self.get_response(request)
