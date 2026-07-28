"""django-auth-ldap backend constrained to pre-linked SGPD accounts."""

from __future__ import annotations

import logging
from types import SimpleNamespace
from typing import Any

import ldap  # type: ignore[import-untyped]
from django.http import HttpRequest
from django_auth_ldap.backend import (  # type: ignore[import-untyped]
    LDAPBackend,
    LDAPSettings,
    ldap_error,
)
from django_auth_ldap.config import LDAPSearch  # type: ignore[import-untyped]
from ldap.filter import escape_filter_chars  # type: ignore[import-untyped]

from apps.accounts.models import User
from config.middleware import correlation_id

from .client import (
    ACTIVE_USER_FILTER,
    TRANSITIVE_MEMBERSHIP_RULE,
    USER_ATTRIBUTES,
    normalize_object_guid,
)
from .config import ActiveDirectoryConfig
from .exceptions import DirectoryContractError, DirectoryUnavailableError

logger = logging.getLogger(__name__)


def _dynamic_ldap_settings(config: ActiveDirectoryConfig) -> SimpleNamespace:
    authentication_filter_parts = [
        ACTIVE_USER_FILTER,
        "(sAMAccountName=%(user)s)",
    ]
    if config.user_extra_filter:
        authentication_filter_parts.append(config.user_extra_filter)
    if config.required_group_dn:
        escaped_required_group = escape_filter_chars(config.required_group_dn)
        authentication_filter_parts.append(
            f"(memberOf:{TRANSITIVE_MEMBERSHIP_RULE}:={escaped_required_group})"
            if config.nested_group_search
            else f"(memberOf={escaped_required_group})"
        )

    connection_options = {
        ldap.OPT_REFERRALS: 0,
        ldap.OPT_NETWORK_TIMEOUT: config.connect_timeout_seconds,
        ldap.OPT_TIMEOUT: config.receive_timeout_seconds,
        ldap.OPT_X_TLS_REQUIRE_CERT: ldap.OPT_X_TLS_DEMAND,
        ldap.OPT_X_TLS_NEWCTX: 0,
    }
    if config.tls_ca_cert_file:
        connection_options[ldap.OPT_X_TLS_CACERTFILE] = config.tls_ca_cert_file

    values = dict(LDAPSettings.defaults)
    values.update(
        {
            "SERVER_URI": config.server_uri,
            "START_TLS": config.start_tls,
            "BIND_DN": config.bind_dn,
            "BIND_PASSWORD": config.bind_password,
            "USER_SEARCH": LDAPSearch(
                config.user_search_base,
                ldap.SCOPE_SUBTREE,
                f"(&{''.join(authentication_filter_parts)})",
            ),
            "USER_ATTRLIST": list(USER_ATTRIBUTES),
            "NO_NEW_USERS": True,
            "ALWAYS_UPDATE_USER": False,
            "PERMIT_EMPTY_PASSWORD": False,
            "FIND_GROUP_PERMS": False,
            "MIRROR_GROUPS": False,
            "CONNECTION_OPTIONS": connection_options,
        }
    )
    return SimpleNamespace(**values)


class ActiveDirectoryBackend(LDAPBackend):  # type: ignore[misc]
    """Authenticate in AD without automatic local provisioning or authorization."""

    def authenticate(
        self,
        request: HttpRequest | None,
        username: str | None = None,
        password: str | None = None,
        **kwargs: Any,
    ) -> User | None:
        config = ActiveDirectoryConfig.from_settings()
        if not config.authentication_enabled or not username or not password:
            return None
        config.require_valid()
        candidate = (
            User.objects.filter(
                ad_username__iexact=username,
                is_active=True,
            )
            .exclude(ad_identifier__isnull=True)
            .order_by("pk")
            .first()
        )
        if candidate is None:
            # Valid AD credentials alone never create an SGPD account.
            return None
        if candidate.is_superuser and config.local_superuser_fallback:
            # The contingency identity is deliberately local. Skipping the AD
            # request keeps it usable even during a directory outage.
            return None
        # Django instantiates authentication backends per authenticate() call.
        # Building the settings on this instance makes a saved SuperAdmin
        # configuration effective on the next login without mutating globals.
        self._settings = _dynamic_ldap_settings(config)
        user = super().authenticate(
            request,
            username=username,
            password=password,
            **kwargs,
        )
        if not isinstance(user, User) or user.pk != candidate.pk:
            return None
        return user

    def get_or_build_user(self, username: str, ldap_user: Any) -> tuple[User, bool]:
        try:
            identifier = normalize_object_guid(ldap_user.attrs["objectGUID"][0])
            return User.objects.get(
                ad_identifier=identifier,
                is_active=True,
            ), False
        except (KeyError, IndexError, TypeError, User.DoesNotExist):
            # AUTH_LDAP_NO_NEW_USERS rejects this unsaved sentinel.
            return User(username=username.lower()), True
        except DirectoryContractError:
            return User(username=username.lower()), True

    def get_user(self, user_id: int) -> User | None:
        try:
            return User.objects.get(pk=user_id, is_active=True)
        except User.DoesNotExist:
            return None


def _raise_ldap_unavailable(
    sender: type[ActiveDirectoryBackend],
    *,
    context: str,
    exception: Exception,
    **kwargs: Any,
) -> None:
    del sender, context, exception, kwargs
    logger.warning(
        "active_directory_authentication_unavailable",
        extra={"correlation_id": correlation_id.get()},
    )
    raise DirectoryUnavailableError("O Active Directory está indisponível ou recusou a conexão.")


ldap_error.connect(
    _raise_ldap_unavailable,
    sender=ActiveDirectoryBackend,
    weak=False,
    dispatch_uid="sgpd.active_directory.raise_unavailable",
)
