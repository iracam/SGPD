"""Typed Active Directory configuration loaded from Django settings."""

from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import urlparse

from django.apps import apps
from django.conf import settings
from django.core.exceptions import AppRegistryNotReady
from django.db import DatabaseError


def _address_from_uri(server_uri: str, *, start_tls: bool = False) -> str:
    """Project a legacy LDAP URI as the scheme-free value edited by the SPA."""

    value = server_uri.strip()
    if not value:
        return ""
    parsed = urlparse(value)
    if parsed.scheme.lower() not in {"ldap", "ldaps"} or not parsed.hostname:
        return value
    host = f"[{parsed.hostname}]" if ":" in parsed.hostname else parsed.hostname
    try:
        port = parsed.port
    except ValueError:
        return value
    default_port = 636 if parsed.scheme.lower() == "ldaps" else 389
    if start_tls:
        default_port = 389
    return f"{host}:{port}" if port is not None and port != default_port else host


def _uri_from_address(server_address: str, *, use_tls: bool) -> str:
    """Build the effective LDAP URI without asking the administrator for a scheme."""

    value = server_address.strip()
    if not value:
        return ""
    if "://" in value:
        return value
    return f"{'ldaps' if use_tls else 'ldap'}://{value}"


@dataclass(frozen=True, slots=True)
class ActiveDirectoryConfig:
    enabled: bool
    authentication_enabled: bool
    server_uri: str
    bind_dn: str
    bind_password: str
    user_search_base: str
    group_search_base: str
    required_group_dn: str
    start_tls: bool
    tls_require_certificate: bool
    tls_ca_cert_file: str
    connect_timeout_seconds: int
    receive_timeout_seconds: int
    page_size: int
    result_limit: int
    nested_group_search: bool
    local_superuser_fallback: bool
    user_extra_filter: str
    source: str = "environment"
    version: int = 0
    storage_errors: tuple[str, ...] = ()

    @classmethod
    def from_environment(cls) -> ActiveDirectoryConfig:
        server_address = str(getattr(settings, "LDAP_SERVER_ADDRESS", "")).strip()
        if server_address:
            server_uri = _uri_from_address(
                server_address,
                use_tls=bool(getattr(settings, "LDAP_USE_TLS", True)),
            )
            start_tls = False
        else:
            # Compatibilidade de implantação: o baseline antigo aceitava URI
            # completa e StartTLS. A central sempre persiste a escolha simples.
            server_uri = str(getattr(settings, "LDAP_SERVER_URI", "")).strip()
            start_tls = bool(getattr(settings, "LDAP_START_TLS", False))
        return cls(
            enabled=bool(getattr(settings, "LDAP_ENABLED", False)),
            authentication_enabled=bool(getattr(settings, "LDAP_AUTHENTICATION_ENABLED", False)),
            server_uri=server_uri,
            bind_dn=str(getattr(settings, "LDAP_BIND_DN", "")).strip(),
            bind_password=str(getattr(settings, "LDAP_BIND_PASSWORD", "")),
            user_search_base=str(getattr(settings, "LDAP_USER_SEARCH_BASE", "")).strip(),
            group_search_base=str(getattr(settings, "LDAP_GROUP_SEARCH_BASE", "")).strip(),
            required_group_dn=str(getattr(settings, "LDAP_REQUIRED_GROUP_DN", "")).strip(),
            start_tls=start_tls,
            tls_require_certificate=bool(getattr(settings, "LDAP_TLS_REQUIRE_CERTIFICATE", True)),
            tls_ca_cert_file=str(getattr(settings, "LDAP_TLS_CA_CERT_FILE", "")).strip(),
            connect_timeout_seconds=int(getattr(settings, "LDAP_CONNECT_TIMEOUT_SECONDS", 5)),
            receive_timeout_seconds=int(getattr(settings, "LDAP_RECEIVE_TIMEOUT_SECONDS", 10)),
            page_size=int(getattr(settings, "LDAP_PAGE_SIZE", 100)),
            result_limit=int(getattr(settings, "LDAP_RESULT_LIMIT", 50)),
            nested_group_search=bool(getattr(settings, "LDAP_NESTED_GROUP_SEARCH", True)),
            local_superuser_fallback=bool(getattr(settings, "LDAP_LOCAL_SUPERUSER_FALLBACK", True)),
            user_extra_filter=str(getattr(settings, "LDAP_USER_EXTRA_FILTER", "")).strip(),
        )

    @classmethod
    def from_settings(cls) -> ActiveDirectoryConfig:
        """Load the persisted singleton, falling back to the environment baseline.

        The fallback keeps migrations and first boot operational before the new
        table exists. Once a row is saved, all LDAP consumers use it dynamically.
        """

        environment = cls.from_environment()
        if not apps.ready:
            return environment
        try:
            from apps.system_settings.crypto import decrypt_secret
            from apps.system_settings.exceptions import ConfigurationSecretError
            from apps.system_settings.models import LDAP_CONFIGURATION_KEY, LdapConfiguration

            persisted = LdapConfiguration.objects.get(pk=LDAP_CONFIGURATION_KEY)
        except (AppRegistryNotReady, DatabaseError):
            return environment
        except LdapConfiguration.DoesNotExist:
            return environment

        storage_errors: list[str] = []
        try:
            bind_password = (
                decrypt_secret(persisted.bind_password_ciphertext)
                if persisted.bind_password_ciphertext
                else environment.bind_password
            )
        except ConfigurationSecretError as exc:
            bind_password = ""
            storage_errors.append(str(exc))

        tls_ca_cert_file = environment.tls_ca_cert_file
        if persisted.certificate_file:
            try:
                tls_ca_cert_file = persisted.certificate_file.path
            except (NotImplementedError, ValueError):
                tls_ca_cert_file = ""
                storage_errors.append(
                    "O certificado LDAP armazenado não possui um caminho privado utilizável."
                )

        return cls(
            enabled=persisted.enabled,
            authentication_enabled=persisted.authentication_enabled,
            server_uri=persisted.server_uri.strip(),
            bind_dn=persisted.bind_dn.strip(),
            bind_password=bind_password,
            user_search_base=persisted.user_search_base.strip(),
            group_search_base=persisted.group_search_base.strip(),
            required_group_dn=persisted.required_group_dn.strip(),
            start_tls=persisted.start_tls,
            tls_require_certificate=True,
            tls_ca_cert_file=tls_ca_cert_file,
            connect_timeout_seconds=persisted.connect_timeout_seconds,
            receive_timeout_seconds=persisted.receive_timeout_seconds,
            page_size=persisted.page_size,
            result_limit=persisted.result_limit,
            nested_group_search=persisted.nested_group_search,
            local_superuser_fallback=persisted.local_superuser_fallback,
            user_extra_filter=persisted.user_extra_filter.strip(),
            source="database",
            version=persisted.version,
            storage_errors=tuple(storage_errors),
        )

    @property
    def parsed_uri(self):  # type: ignore[no-untyped-def]
        return urlparse(self.server_uri)

    @property
    def secure_transport(self) -> bool:
        return self.parsed_uri.scheme.lower() == "ldaps" or self.start_tls

    @property
    def server_address(self) -> str:
        return _address_from_uri(self.server_uri, start_tls=self.start_tls)

    @property
    def use_tls(self) -> bool:
        return self.secure_transport

    def allows_local_password(self, *, has_ad_link: bool, is_superuser: bool) -> bool:
        """Apply the same local-password boundary in auth, services and UI."""

        if not self.authentication_enabled or not has_ad_link:
            return True
        return is_superuser and self.local_superuser_fallback

    def validation_errors(self) -> list[str]:
        errors: list[str] = list(self.storage_errors)
        if self.authentication_enabled and not self.enabled:
            errors.append("LDAP_AUTHENTICATION_ENABLED exige LDAP_ENABLED=true.")
        if not self.enabled:
            return errors

        parsed = self.parsed_uri
        if parsed.scheme.lower() not in {"ldap", "ldaps"} or not parsed.hostname:
            errors.append("O servidor LDAP deve conter um host e, opcionalmente, a porta.")
        if parsed.path not in {"", "/"} or parsed.query or parsed.fragment:
            errors.append("O servidor LDAP não deve conter caminho, query ou fragmento.")
        try:
            _ = parsed.port
        except ValueError:
            errors.append("A porta do servidor LDAP é inválida.")
        if not self.bind_dn:
            errors.append("LDAP_BIND_DN é obrigatório.")
        if not self.bind_password:
            errors.append("LDAP_BIND_PASSWORD é obrigatório.")
        if self.authentication_enabled and not self.user_search_base:
            errors.append("LDAP_USER_SEARCH_BASE é obrigatório para ativar a autenticação.")
        if self.secure_transport and not self.tls_require_certificate:
            errors.append("LDAP_TLS_REQUIRE_CERTIFICATE deve permanecer true.")
        if self.start_tls and parsed.scheme.lower() == "ldaps":
            errors.append("Não combine LDAPS com LDAP_START_TLS=true.")
        if parsed.username or parsed.password:
            errors.append("O servidor LDAP não deve conter credenciais.")
        if self.connect_timeout_seconds < 1:
            errors.append("LDAP_CONNECT_TIMEOUT_SECONDS deve ser positivo.")
        if self.receive_timeout_seconds < 1:
            errors.append("LDAP_RECEIVE_TIMEOUT_SECONDS deve ser positivo.")
        if not 1 <= self.page_size <= 1000:
            errors.append("LDAP_PAGE_SIZE deve estar entre 1 e 1000.")
        if not 1 <= self.result_limit <= 200:
            errors.append("LDAP_RESULT_LIMIT deve estar entre 1 e 200.")
        if self.user_extra_filter and not (
            self.user_extra_filter.startswith("(") and self.user_extra_filter.endswith(")")
        ):
            errors.append("LDAP_USER_EXTRA_FILTER deve ser um filtro LDAP entre parênteses.")
        return errors

    def require_valid(self) -> None:
        if not self.enabled:
            from .exceptions import DirectoryConfigurationError

            raise DirectoryConfigurationError(
                "A integração está desativada por LDAP_ENABLED=false."
            )
        errors = self.validation_errors()
        if errors:
            from .exceptions import DirectoryConfigurationError

            raise DirectoryConfigurationError(" ".join(errors))


def server_uri_from_address(server_address: str, *, use_tls: bool) -> str:
    return _uri_from_address(server_address, use_tls=use_tls)
