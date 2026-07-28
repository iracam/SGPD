"""Read-only python-ldap client for Active Directory discovery."""

from __future__ import annotations

import logging
import time
import uuid
from collections.abc import Iterator
from contextlib import AbstractContextManager, contextmanager, suppress
from typing import Any

from config.middleware import correlation_id

from .config import ActiveDirectoryConfig
from .dto import DirectoryGroup, DirectoryProbe, DirectoryUser
from .exceptions import (
    DirectoryConfigurationError,
    DirectoryContractError,
    DirectoryIdentityNotFoundError,
    DirectoryUnavailableError,
)

logger = logging.getLogger(__name__)

ACTIVE_USER_FILTER = (
    "(&(objectCategory=person)(objectClass=user)(!(userAccountControl:1.2.840.113556.1.4.803:=2)))"
)
GROUP_FILTER = "(objectCategory=group)"
TRANSITIVE_MEMBERSHIP_RULE = "1.2.840.113556.1.4.1941"
USER_ATTRIBUTES = (
    "objectGUID",
    "sAMAccountName",
    "userPrincipalName",
    "givenName",
    "sn",
    "displayName",
    "mail",
    "distinguishedName",
)
GROUP_ATTRIBUTES = ("cn", "sAMAccountName", "description", "distinguishedName")


def _ldap_modules() -> tuple[Any, Any, Any]:
    try:
        import ldap  # type: ignore[import-untyped]
        from ldap.controls import SimplePagedResultsControl  # type: ignore[import-untyped]
        from ldap.filter import escape_filter_chars  # type: ignore[import-untyped]
    except ImportError as exc:
        raise DirectoryConfigurationError(
            "Instale django-auth-ldap 5.3.x e python-ldap 3.4.x com os "
            "cabeçalhos LDAP/SASL do sistema."
        ) from exc
    return ldap, SimplePagedResultsControl, escape_filter_chars


def _first(attributes: dict[str, list[bytes]], name: str) -> bytes | None:
    values = attributes.get(name) or attributes.get(name.lower()) or []
    return values[0] if values else None


def _text(value: bytes | None) -> str:
    if value is None:
        return ""
    try:
        return value.decode("utf-8").strip()
    except UnicodeDecodeError as exc:
        raise DirectoryContractError("O Active Directory retornou texto fora de UTF-8.") from exc


def normalize_object_guid(value: Any) -> str:
    """Convert AD's little-endian 16-byte objectGUID to canonical UUID text."""

    if isinstance(value, uuid.UUID):
        return str(value)
    if isinstance(value, bytes):
        if len(value) != 16:
            raise DirectoryContractError("O objectGUID retornado pelo AD é inválido.")
        return str(uuid.UUID(bytes_le=value))
    try:
        return str(uuid.UUID(str(value).strip().strip("{}")))
    except (AttributeError, ValueError) as exc:
        raise DirectoryContractError("O objectGUID retornado pelo AD é inválido.") from exc


def object_guid_filter_value(identifier: str) -> str:
    try:
        raw = uuid.UUID(identifier).bytes_le
    except ValueError as exc:
        raise DirectoryContractError("O identificador do AD é inválido.") from exc
    return "".join(f"\\{byte:02x}" for byte in raw)


class ActiveDirectoryClient:
    """Small adapter around python-ldap with no AD writes or auto-provisioning."""

    def __init__(self, config: ActiveDirectoryConfig | None = None) -> None:
        self.config = config or ActiveDirectoryConfig.from_settings()

    def status(self) -> dict[str, bool | list[str]]:
        errors = self.config.validation_errors()
        return {
            "enabled": self.config.enabled,
            "authentication_enabled": self.config.authentication_enabled,
            "configured": self.config.enabled and not errors,
            "secure_transport": self.config.secure_transport,
            "insecure_transport": self.config.enabled and not self.config.secure_transport,
            "user_search_base_configured": bool(self.config.user_search_base),
            "group_search_base_configured": bool(self.config.group_search_base),
            "required_group_configured": bool(self.config.required_group_dn),
            "errors": errors,
        }

    def probe(self) -> DirectoryProbe:
        self.config.require_valid()
        with self._service_connection() as connection:
            self._default_naming_context(connection)
        return DirectoryProbe(
            user_search_base_source=("configured" if self.config.user_search_base else "root_dse"),
            group_search_base_source=(
                "configured" if self.config.group_search_base else "root_dse"
            ),
            secure_transport=self.config.secure_transport,
        )

    def search_users(
        self,
        query: str,
        *,
        limit: int | None = None,
    ) -> list[DirectoryUser]:
        _, _, escape_filter_chars = _ldap_modules()
        normalized_query = query.strip()
        if len(normalized_query) < 2:
            raise DirectoryContractError("Informe ao menos dois caracteres para a busca.")
        effective_limit = self._limit(limit)
        escaped_query = escape_filter_chars(normalized_query)
        query_filter = (
            "(|"
            f"(sAMAccountName=*{escaped_query}*)"
            f"(userPrincipalName=*{escaped_query}*)"
            f"(displayName=*{escaped_query}*)"
            f"(mail=*{escaped_query}*)"
            ")"
        )
        search_filter = self._user_filter(query_filter)

        started = time.monotonic()
        with self._service_connection() as connection:
            base = self._user_base(connection)
            rows = [
                self._directory_user(dn, attributes)
                for dn, attributes in self._paged_entries(
                    connection,
                    base=base,
                    search_filter=search_filter,
                    attributes=USER_ATTRIBUTES,
                    limit=effective_limit,
                )
            ]
        self._log_query("search_users", started, len(rows))
        return sorted(rows, key=lambda item: (item.display_name.casefold(), item.username))

    def search_groups(
        self,
        query: str,
        *,
        limit: int | None = None,
    ) -> list[DirectoryGroup]:
        _, _, escape_filter_chars = _ldap_modules()
        normalized_query = query.strip()
        if len(normalized_query) < 2:
            raise DirectoryContractError("Informe ao menos dois caracteres para a busca.")
        effective_limit = self._limit(limit)
        escaped_query = escape_filter_chars(normalized_query)
        search_filter = (
            f"(&{GROUP_FILTER}"
            "(|"
            f"(cn=*{escaped_query}*)"
            f"(sAMAccountName=*{escaped_query}*)"
            f"(description=*{escaped_query}*)"
            ")"
            ")"
        )

        started = time.monotonic()
        with self._service_connection() as connection:
            base = self._group_base(connection)
            rows = [
                self._directory_group(dn, attributes)
                for dn, attributes in self._paged_entries(
                    connection,
                    base=base,
                    search_filter=search_filter,
                    attributes=GROUP_ATTRIBUTES,
                    limit=effective_limit,
                )
            ]
        self._log_query("search_groups", started, len(rows))
        return sorted(rows, key=lambda item: item.name.casefold())

    def get_user(self, identifier: str) -> DirectoryUser:
        canonical_identifier = normalize_object_guid(identifier)
        exact_filter = f"(objectGUID={object_guid_filter_value(canonical_identifier)})"
        search_filter = self._user_filter(exact_filter)

        started = time.monotonic()
        with self._service_connection() as connection:
            base = self._user_base(connection)
            entries = list(
                self._paged_entries(
                    connection,
                    base=base,
                    search_filter=search_filter,
                    attributes=USER_ATTRIBUTES,
                    limit=2,
                )
            )
        self._log_query("get_user", started, len(entries))
        if not entries:
            raise DirectoryIdentityNotFoundError(
                "A identidade não existe, está inativa ou está fora do filtro autorizado."
            )
        if len(entries) != 1:
            raise DirectoryContractError("O identificador do AD não retornou uma identidade única.")
        return self._directory_user(*entries[0])

    def _limit(self, requested: int | None) -> int:
        if requested is None:
            return self.config.result_limit
        return max(1, min(requested, self.config.result_limit))

    def _user_filter(self, extra_filter: str) -> str:
        _, _, escape_filter_chars = _ldap_modules()
        parts = [ACTIVE_USER_FILTER, extra_filter]
        if self.config.user_extra_filter:
            parts.append(self.config.user_extra_filter)
        if self.config.required_group_dn:
            escaped_group = escape_filter_chars(self.config.required_group_dn)
            if self.config.nested_group_search:
                parts.append(f"(memberOf:{TRANSITIVE_MEMBERSHIP_RULE}:={escaped_group})")
            else:
                parts.append(f"(memberOf={escaped_group})")
        return f"(&{''.join(parts)})"

    @contextmanager
    def _connection(self, user: str, password: str) -> Iterator[Any]:
        self.config.require_valid()
        ldap, _, _ = _ldap_modules()
        connection = None
        try:
            connection = ldap.initialize(self.config.server_uri, bytes_mode=False)
            connection.protocol_version = ldap.VERSION3
            connection.set_option(ldap.OPT_REFERRALS, 0)
            connection.set_option(
                ldap.OPT_NETWORK_TIMEOUT,
                self.config.connect_timeout_seconds,
            )
            connection.set_option(
                ldap.OPT_TIMEOUT,
                self.config.receive_timeout_seconds,
            )
            connection.set_option(
                ldap.OPT_X_TLS_REQUIRE_CERT,
                (
                    ldap.OPT_X_TLS_DEMAND
                    if self.config.tls_require_certificate
                    else ldap.OPT_X_TLS_NEVER
                ),
            )
            if self.config.tls_ca_cert_file:
                connection.set_option(
                    ldap.OPT_X_TLS_CACERTFILE,
                    self.config.tls_ca_cert_file,
                )
            connection.set_option(ldap.OPT_X_TLS_NEWCTX, 0)
            if self.config.start_tls:
                connection.start_tls_s()
            connection.simple_bind_s(user, password)
            yield connection
        except ldap.LDAPError as exc:
            raise DirectoryUnavailableError(
                "O Active Directory está indisponível ou recusou a conexão."
            ) from exc
        finally:
            if connection is not None:
                with suppress(ldap.LDAPError):
                    connection.unbind_s()

    def _service_connection(self) -> AbstractContextManager[Any]:
        return self._connection(self.config.bind_dn, self.config.bind_password)

    def _default_naming_context(self, connection: Any) -> str:
        ldap, _, _ = _ldap_modules()
        try:
            entries = connection.search_s(
                "",
                ldap.SCOPE_BASE,
                "(objectClass=*)",
                ["defaultNamingContext"],
            )
        except ldap.LDAPError as exc:
            raise DirectoryUnavailableError(
                "Não foi possível descobrir a base padrão do Active Directory."
            ) from exc
        if len(entries) != 1:
            raise DirectoryContractError(
                "O RootDSE não retornou defaultNamingContext de forma única."
            )
        naming_context = _text(_first(entries[0][1], "defaultNamingContext"))
        if not naming_context:
            raise DirectoryContractError("O RootDSE não informou defaultNamingContext.")
        return naming_context

    def _user_base(self, connection: Any) -> str:
        return self.config.user_search_base or self._default_naming_context(connection)

    def _group_base(self, connection: Any) -> str:
        return self.config.group_search_base or self._default_naming_context(connection)

    def _paged_entries(
        self,
        connection: Any,
        *,
        base: str,
        search_filter: str,
        attributes: tuple[str, ...],
        limit: int,
    ) -> Iterator[tuple[str, dict[str, list[bytes]]]]:
        ldap, SimplePagedResultsControl, _ = _ldap_modules()
        page_control = SimplePagedResultsControl(
            criticality=True,
            size=min(self.config.page_size, limit),
            cookie=b"",
        )
        yielded = 0
        try:
            while yielded < limit:
                message_id = connection.search_ext(
                    base,
                    ldap.SCOPE_SUBTREE,
                    search_filter,
                    list(attributes),
                    serverctrls=[page_control],
                    timeout=self.config.receive_timeout_seconds,
                    sizelimit=0,
                )
                _, rows, _, controls = connection.result3(
                    message_id,
                    timeout=self.config.receive_timeout_seconds,
                )
                for dn, values in rows:
                    if dn is None:
                        continue
                    yield str(dn), values
                    yielded += 1
                    if yielded >= limit:
                        return
                response_control = next(
                    (
                        control
                        for control in controls
                        if control.controlType == page_control.controlType
                    ),
                    None,
                )
                cookie = response_control.cookie if response_control is not None else b""
                if not cookie:
                    return
                page_control.cookie = cookie
        except ldap.LDAPError as exc:
            raise DirectoryUnavailableError(
                "A consulta ao Active Directory não pôde ser concluída."
            ) from exc

    def _directory_user(
        self,
        dn: str,
        attributes: dict[str, list[bytes]],
    ) -> DirectoryUser:
        identifier = normalize_object_guid(_first(attributes, "objectGUID"))
        username = _text(_first(attributes, "sAMAccountName")).lower()
        distinguished_name = _text(_first(attributes, "distinguishedName")) or dn
        if not username or not distinguished_name:
            raise DirectoryContractError(
                "A identidade do AD não possui sAMAccountName ou distinguishedName."
            )
        first_name = _text(_first(attributes, "givenName")) or None
        last_name = _text(_first(attributes, "sn")) or None
        display_name = (
            _text(_first(attributes, "displayName"))
            or " ".join(item for item in (first_name, last_name) if item)
            or username
        )
        email = _text(_first(attributes, "mail")).lower() or None
        principal = _text(_first(attributes, "userPrincipalName")).lower() or None
        return DirectoryUser(
            identifier=identifier,
            username=username,
            user_principal_name=principal,
            first_name=first_name,
            last_name=last_name,
            display_name=display_name,
            email=email,
            distinguished_name=distinguished_name,
        )

    def _directory_group(
        self,
        dn: str,
        attributes: dict[str, list[bytes]],
    ) -> DirectoryGroup:
        distinguished_name = _text(_first(attributes, "distinguishedName")) or dn
        name = _text(_first(attributes, "cn"))
        if not distinguished_name or not name:
            raise DirectoryContractError("O grupo do AD não possui cn ou distinguishedName.")
        return DirectoryGroup(
            distinguished_name=distinguished_name,
            name=name,
            account_name=_text(_first(attributes, "sAMAccountName")) or None,
            description=_text(_first(attributes, "description")) or None,
        )

    def _log_query(self, operation: str, started: float, row_count: int) -> None:
        logger.info(
            "active_directory_query",
            extra={
                "operation": operation,
                "duration_ms": round((time.monotonic() - started) * 1000, 2),
                "row_count": row_count,
                "correlation_id": correlation_id.get(),
            },
        )
