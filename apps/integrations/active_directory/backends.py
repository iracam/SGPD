"""Local Django authentication with an explicit AD fallback boundary."""

from __future__ import annotations

from typing import Any

from django.contrib.auth.backends import ModelBackend
from django.db.models import Q
from django.http import HttpRequest

from apps.accounts.models import User

from .config import ActiveDirectoryConfig


class LocalAccountBackend(ModelBackend):
    """Keep local auth for unlinked users and a controlled superuser fallback."""

    def authenticate(
        self,
        request: HttpRequest | None,
        username: str | None = None,
        password: str | None = None,
        **kwargs: Any,
    ) -> User | None:
        config = ActiveDirectoryConfig.from_settings()
        lookup = username or kwargs.get(User.USERNAME_FIELD)
        if config.authentication_enabled and lookup:
            candidate = (
                User.objects.filter(
                    Q(username__iexact=str(lookup)) | Q(ad_username__iexact=str(lookup))
                )
                .order_by("pk")
                .first()
            )
            if candidate is not None and not config.allows_local_password(
                has_ad_link=candidate.has_ad_link,
                is_superuser=candidate.is_superuser,
            ):
                # A linked common account must not silently fall back to its
                # previous SGPD password when AD is unavailable or rejects it.
                return None
        return super().authenticate(
            request,
            username=username,
            password=password,
            **kwargs,
        )
