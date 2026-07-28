"""SuperAdmin-only use cases for LDAP configuration and validation."""

from __future__ import annotations

import hashlib
import hmac
import json
import time
import uuid
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import cast

from django.conf import settings
from django.core.exceptions import PermissionDenied, ValidationError
from django.core.files.base import ContentFile
from django.db import transaction
from django.utils import timezone

from apps.accounts.models import AccountAuditEvent, User
from apps.integrations.active_directory.client import ActiveDirectoryClient
from apps.integrations.active_directory.config import (
    ActiveDirectoryConfig,
    server_uri_from_address,
)
from apps.integrations.active_directory.exceptions import (
    ActiveDirectoryError,
    DirectoryConfigurationError,
)
from config.middleware import correlation_id

from .certificates import (
    CertificateBundleInfo,
    validate_certificate_bundle,
    validate_certificate_path,
)
from .crypto import decrypt_secret, encrypt_secret
from .exceptions import CertificateValidationError, ConfigurationSecretError
from .models import LDAP_CONFIGURATION_KEY, LdapConfiguration

LDAP_CONFIG_UPDATED = "LDAP_CONFIG_UPDATED"
LDAP_CERT_UPLOADED = "LDAP_CERT_UPLOADED"
LDAP_CONNECTION_TESTED = "LDAP_CONNECTION_TESTED"
LDAP_CONFIG_UPDATE_REASON = "Atualização da configuração LDAP pela central de configurações."
LDAP_CERT_UPLOAD_REASON = "Envio e validação da CA pela central de configurações."


def require_superadmin(actor: User) -> None:
    if not actor.is_authenticated or not actor.is_active or not actor.is_superuser:
        raise PermissionDenied("Somente SuperAdmin pode administrar configurações do sistema.")


def _record_event(
    *,
    event_type: str,
    actor: User,
    changes: dict[str, object],
    reason: str,
) -> AccountAuditEvent:
    return AccountAuditEvent.objects.create(
        event_type=event_type,
        actor=actor,
        target_user=None,
        entity_type="LDAP_CONFIGURATION",
        entity_id=LDAP_CONFIGURATION_KEY,
        reason=reason,
        changes=changes,
        correlation_id=correlation_id.get(),
    )


def _environment_values(actor: User) -> dict[str, object]:
    config = ActiveDirectoryConfig.from_environment()
    return {
        "key": LDAP_CONFIGURATION_KEY,
        "enabled": config.enabled,
        "authentication_enabled": config.authentication_enabled,
        "server_uri": config.server_uri,
        "bind_dn": config.bind_dn,
        "user_search_base": config.user_search_base,
        "group_search_base": config.group_search_base,
        "required_group_dn": config.required_group_dn,
        "start_tls": config.start_tls,
        "connect_timeout_seconds": config.connect_timeout_seconds,
        "receive_timeout_seconds": config.receive_timeout_seconds,
        "page_size": config.page_size,
        "result_limit": config.result_limit,
        "nested_group_search": config.nested_group_search,
        "local_superuser_fallback": config.local_superuser_fallback,
        "user_extra_filter": config.user_extra_filter,
        "version": 1,
        "updated_by": actor,
    }


def current_persisted_configuration() -> LdapConfiguration | None:
    try:
        return LdapConfiguration.objects.get(pk=LDAP_CONFIGURATION_KEY)
    except LdapConfiguration.DoesNotExist:
        return None


def _current_secret(record: LdapConfiguration | None) -> str:
    if record is not None and record.bind_password_ciphertext:
        return decrypt_secret(record.bind_password_ciphertext)
    return ActiveDirectoryConfig.from_environment().bind_password


def _certificate_path(record: LdapConfiguration | None) -> str:
    if record is not None and record.certificate_file:
        try:
            return cast(str, record.certificate_file.path)
        except (NotImplementedError, ValueError):
            return ""
    return ActiveDirectoryConfig.from_environment().tls_ca_cert_file


@dataclass(frozen=True, slots=True)
class LdapConfigurationCommand:
    actor: User
    expected_version: int
    enabled: bool
    authentication_enabled: bool
    server_address: str
    use_tls: bool
    bind_dn: str
    bind_password: str
    user_search_base: str
    group_search_base: str
    required_group_dn: str
    connect_timeout_seconds: int
    receive_timeout_seconds: int
    page_size: int
    result_limit: int
    nested_group_search: bool
    local_superuser_fallback: bool
    user_extra_filter: str


def _candidate(
    command: LdapConfigurationCommand,
    record: LdapConfiguration | None,
) -> ActiveDirectoryConfig:
    bind_password = command.bind_password or _current_secret(record)
    return ActiveDirectoryConfig(
        enabled=command.enabled,
        authentication_enabled=command.authentication_enabled,
        server_uri=server_uri_from_address(
            command.server_address,
            use_tls=command.use_tls,
        ),
        bind_dn=command.bind_dn.strip(),
        bind_password=bind_password,
        user_search_base=command.user_search_base.strip(),
        group_search_base=command.group_search_base.strip(),
        required_group_dn=command.required_group_dn.strip(),
        start_tls=False,
        tls_require_certificate=True,
        tls_ca_cert_file=_certificate_path(record),
        connect_timeout_seconds=command.connect_timeout_seconds,
        receive_timeout_seconds=command.receive_timeout_seconds,
        page_size=command.page_size,
        result_limit=command.result_limit,
        nested_group_search=command.nested_group_search,
        local_superuser_fallback=command.local_superuser_fallback,
        user_extra_filter=command.user_extra_filter.strip(),
        source="candidate",
        version=command.expected_version,
    )


def configuration_fingerprint(
    config: ActiveDirectoryConfig,
    *,
    certificate_sha256: str = "",
) -> str:
    fingerprint_key = hashlib.sha256(
        f"{settings.SECRET_KEY}:sgpd-ldap-fingerprint-v1".encode()
    ).digest()
    payload = {
        "server_uri": config.server_uri,
        "bind_dn": config.bind_dn,
        "bind_password_hmac": hmac.new(
            fingerprint_key,
            config.bind_password.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest(),
        "user_search_base": config.user_search_base,
        "group_search_base": config.group_search_base,
        "required_group_dn": config.required_group_dn,
        "start_tls": config.start_tls,
        "tls_require_certificate": (
            config.tls_require_certificate if config.secure_transport else False
        ),
        "tls_ca_certificate_sha256": (certificate_sha256 if config.secure_transport else ""),
        "connect_timeout_seconds": config.connect_timeout_seconds,
        "receive_timeout_seconds": config.receive_timeout_seconds,
        "page_size": config.page_size,
        "result_limit": config.result_limit,
        "nested_group_search": config.nested_group_search,
        "user_extra_filter": config.user_extra_filter,
    }
    serialized = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(serialized).hexdigest()


def _certificate_sha256(record: LdapConfiguration | None, path: str) -> str:
    if record is not None and record.certificate_sha256:
        return record.certificate_sha256
    if not path:
        return ""
    try:
        return validate_certificate_path(path).sha256
    except CertificateValidationError:
        return ""


class ValidateLdapConfigurationService:
    def execute(self, command: LdapConfigurationCommand) -> list[str]:
        require_superadmin(command.actor)
        record = current_persisted_configuration()
        try:
            config = _candidate(command, record)
        except ConfigurationSecretError as exc:
            return [str(exc)]
        errors = config.validation_errors()
        if config.secure_transport and config.tls_ca_cert_file:
            try:
                validate_certificate_path(config.tls_ca_cert_file)
            except CertificateValidationError as exc:
                errors.append(str(exc))
        return errors


class UpdateLdapConfigurationService:
    @transaction.atomic
    def execute(self, command: LdapConfigurationCommand) -> LdapConfiguration:
        require_superadmin(command.actor)

        record: LdapConfiguration | None = None
        try:
            persisted = LdapConfiguration.objects.select_for_update().get(pk=LDAP_CONFIGURATION_KEY)
        except LdapConfiguration.DoesNotExist:
            if command.expected_version != 0:
                raise ValidationError(
                    {"version": "A configuração foi criada ou alterada por outra sessão."}
                ) from None
        else:
            if persisted.version != command.expected_version:
                raise ValidationError({"version": "A configuração foi alterada por outra sessão."})
            record = persisted

        candidate = _candidate(command, record)
        errors = candidate.validation_errors()
        if errors:
            raise ValidationError({"non_field_errors": errors})

        certificate_path = candidate.tls_ca_cert_file
        certificate_sha256 = _certificate_sha256(record, certificate_path)
        fingerprint = configuration_fingerprint(
            candidate,
            certificate_sha256=certificate_sha256,
        )

        if command.authentication_enabled:
            if not command.local_superuser_fallback:
                raise ValidationError(
                    {
                        "local_superuser_fallback": (
                            "A autenticação AD exige contingência local de SuperAdmin."
                        )
                    }
                )
            superusers = list(
                User.objects.select_for_update()
                .filter(is_superuser=True, is_active=True)
                .order_by("pk")
            )
            if not any(user.has_usable_password() for user in superusers):
                raise ValidationError(
                    "É necessário preservar ao menos um SuperAdmin ativo "
                    "com senha local utilizável."
                )
            if candidate.secure_transport and not certificate_path:
                raise ValidationError(
                    {
                        "authentication_enabled": (
                            "Envie e valide a CA antes de ativar o login AD com TLS."
                        )
                    }
                )
            if candidate.secure_transport:
                try:
                    certificate_info = validate_certificate_path(certificate_path)
                except CertificateValidationError as exc:
                    raise ValidationError({"certificate": str(exc)}) from exc
                if certificate_sha256 and certificate_info.sha256 != certificate_sha256:
                    raise ValidationError(
                        {"certificate": "O arquivo da CA não corresponde ao hash registrado."}
                    )
            if (
                record is None
                or record.last_test_success is not True
                or record.last_test_fingerprint != fingerprint
            ):
                raise ValidationError(
                    {
                        "authentication_enabled": (
                            "Teste com sucesso esta mesma configuração antes de ativar o login AD."
                        )
                    }
                )

        changed_fields: list[str] = []
        if record is None:
            record = LdapConfiguration(**_environment_values(command.actor))
            previous_version = 0
            changed_fields = [
                "enabled",
                "authentication_enabled",
                "server_address",
                "bind_dn",
                "search_bases",
                "group_filter",
                "use_tls",
                "timeouts",
                "limits",
                "fallback",
            ]
        else:
            previous_version = record.version
            candidate_values = {
                "enabled": command.enabled,
                "authentication_enabled": command.authentication_enabled,
                "server_uri": candidate.server_uri,
                "bind_dn": command.bind_dn.strip(),
                "user_search_base": command.user_search_base.strip(),
                "group_search_base": command.group_search_base.strip(),
                "required_group_dn": command.required_group_dn.strip(),
                "start_tls": candidate.start_tls,
                "connect_timeout_seconds": command.connect_timeout_seconds,
                "receive_timeout_seconds": command.receive_timeout_seconds,
                "page_size": command.page_size,
                "result_limit": command.result_limit,
                "nested_group_search": command.nested_group_search,
                "local_superuser_fallback": command.local_superuser_fallback,
                "user_extra_filter": command.user_extra_filter.strip(),
            }
            for field_name, value in candidate_values.items():
                if getattr(record, field_name) != value:
                    changed_fields.append(field_name)
            if command.bind_password:
                changed_fields.append("bind_password")

        record.enabled = command.enabled
        record.authentication_enabled = command.authentication_enabled
        record.server_uri = candidate.server_uri
        record.bind_dn = command.bind_dn.strip()
        record.user_search_base = command.user_search_base.strip()
        record.group_search_base = command.group_search_base.strip()
        record.required_group_dn = command.required_group_dn.strip()
        record.start_tls = candidate.start_tls
        record.connect_timeout_seconds = command.connect_timeout_seconds
        record.receive_timeout_seconds = command.receive_timeout_seconds
        record.page_size = command.page_size
        record.result_limit = command.result_limit
        record.nested_group_search = command.nested_group_search
        record.local_superuser_fallback = command.local_superuser_fallback
        record.user_extra_filter = command.user_extra_filter.strip()
        if command.bind_password:
            record.bind_password_ciphertext = encrypt_secret(command.bind_password)
        record.updated_by = command.actor
        record.version = previous_version + 1

        if record.last_test_fingerprint != fingerprint:
            record.last_tested_at = None
            record.last_test_success = None
            record.last_test_fingerprint = ""
            record.last_test_duration_ms = None
            record.last_tested_by = None

        record.full_clean()
        record.save()
        _record_event(
            event_type=LDAP_CONFIG_UPDATED,
            actor=command.actor,
            reason=LDAP_CONFIG_UPDATE_REASON,
            changes={
                "changed_fields": sorted(set(changed_fields)),
                "enabled": record.enabled,
                "authentication_enabled": record.authentication_enabled,
                "secure_transport": candidate.secure_transport,
                "version_before": previous_version,
                "version_after": record.version,
            },
        )
        return record


@dataclass(frozen=True, slots=True)
class UploadLdapCertificateCommand:
    actor: User
    expected_version: int
    original_name: str
    content: bytes


class UploadLdapCertificateService:
    @transaction.atomic
    def execute(self, command: UploadLdapCertificateCommand) -> LdapConfiguration:
        require_superadmin(command.actor)
        try:
            bundle = validate_certificate_bundle(command.content)
        except CertificateValidationError as exc:
            raise ValidationError({"certificate": str(exc)}) from exc

        try:
            record = LdapConfiguration.objects.select_for_update().get(pk=LDAP_CONFIGURATION_KEY)
        except LdapConfiguration.DoesNotExist:
            if command.expected_version != 0:
                raise ValidationError(
                    {"version": "A configuração foi criada ou alterada por outra sessão."}
                ) from None
            record = LdapConfiguration(**_environment_values(command.actor))
            previous_version = 0
        else:
            if record.version != command.expected_version:
                raise ValidationError({"version": "A configuração foi alterada por outra sessão."})
            previous_version = record.version

        old_name = record.certificate_file.name if record.certificate_file else ""
        new_name = ""
        certificate_affects_transport = bool(
            record.start_tls or record.server_uri.strip().lower().startswith("ldaps://")
        )
        authentication_disabled = record.authentication_enabled and certificate_affects_transport
        try:
            record.certificate_file.save(
                f"{uuid.uuid4()}.pem",
                ContentFile(bundle.pem_bytes),
                save=False,
            )
            new_name = record.certificate_file.name
            record.certificate_original_name = Path(command.original_name).name[:255]
            record.certificate_sha256 = bundle.sha256
            record.certificate_subject = bundle.subject[:1024]
            record.certificate_issuer = bundle.issuer[:1024]
            record.certificate_not_before = bundle.not_before
            record.certificate_not_after = bundle.not_after
            record.certificate_count = bundle.certificate_count
            record.certificate_uploaded_at = timezone.now()
            record.certificate_uploaded_by = command.actor
            # A CA só pertence ao contrato quando TLS está ativo. Em LDAP
            # simples, sua manutenção não interfere no probe nem no login.
            if certificate_affects_transport:
                record.authentication_enabled = False
                record.last_tested_at = None
                record.last_test_success = None
                record.last_test_fingerprint = ""
                record.last_test_duration_ms = None
                record.last_tested_by = None
            record.updated_by = command.actor
            record.version = previous_version + 1
            record.full_clean()
            record.save()
            _record_event(
                event_type=LDAP_CERT_UPLOADED,
                actor=command.actor,
                reason=LDAP_CERT_UPLOAD_REASON,
                changes={
                    "sha256": bundle.sha256,
                    "certificate_count": bundle.certificate_count,
                    "not_after": bundle.not_after.isoformat(),
                    "authentication_disabled": authentication_disabled,
                    "version_before": previous_version,
                    "version_after": record.version,
                },
            )
        except Exception:
            if new_name:
                record.certificate_file.storage.delete(new_name)
            raise

        if old_name and old_name != new_name:
            transaction.on_commit(lambda: record.certificate_file.storage.delete(old_name))
        return record


@dataclass(frozen=True, slots=True)
class CertificateValidationResult:
    info: CertificateBundleInfo
    source: str


class ValidatePersistedCertificateService:
    def execute(self, actor: User) -> CertificateValidationResult:
        require_superadmin(actor)
        record = current_persisted_configuration()
        path = _certificate_path(record)
        if not path:
            raise ValidationError({"certificate": "Nenhum certificado LDAP foi configurado."})
        try:
            info = validate_certificate_path(path)
        except CertificateValidationError as exc:
            raise ValidationError({"certificate": str(exc)}) from exc
        if (
            record is not None
            and record.certificate_sha256
            and record.certificate_sha256 != info.sha256
        ):
            raise ValidationError(
                {"certificate": "O arquivo da CA não corresponde ao hash registrado."}
            )
        return CertificateValidationResult(
            info=info,
            source="database" if record is not None and record.certificate_file else "environment",
        )


@dataclass(frozen=True, slots=True)
class ConnectionTestResult:
    secure_transport: bool
    user_search_base_source: str
    group_search_base_source: str
    duration_ms: int
    tested_at: datetime


class TestLdapConnectionService:
    def execute(self, actor: User) -> ConnectionTestResult:
        require_superadmin(actor)
        config = ActiveDirectoryConfig.from_settings()
        record = current_persisted_configuration()
        if record is not None and record.version != config.version:
            raise DirectoryConfigurationError(
                "A configuração LDAP mudou durante a preparação do teste. "
                "Recarregue a página e tente novamente."
            )
        certificate_sha256 = _certificate_sha256(record, config.tls_ca_cert_file)
        fingerprint = configuration_fingerprint(
            config,
            certificate_sha256=certificate_sha256,
        )
        started = time.monotonic()
        tested_at = timezone.now()
        try:
            if config.secure_transport and config.tls_ca_cert_file:
                validate_certificate_path(config.tls_ca_cert_file)
            probe = ActiveDirectoryClient(config).probe()
        except (ActiveDirectoryError, CertificateValidationError) as exc:
            duration_ms = max(0, round((time.monotonic() - started) * 1000))
            self._record_result(
                actor=actor,
                record=record,
                success=False,
                fingerprint=fingerprint,
                duration_ms=duration_ms,
                tested_at=tested_at,
                error_code=type(exc).__name__,
                secure_transport=config.secure_transport,
            )
            raise

        duration_ms = max(0, round((time.monotonic() - started) * 1000))
        recorded = self._record_result(
            actor=actor,
            record=record,
            success=True,
            fingerprint=fingerprint,
            duration_ms=duration_ms,
            tested_at=tested_at,
            error_code="",
            secure_transport=config.secure_transport,
        )
        if not recorded:
            raise DirectoryConfigurationError(
                "A configuração LDAP mudou durante o teste. "
                "Recarregue a página e execute a conexão novamente."
            )
        return ConnectionTestResult(
            secure_transport=probe.secure_transport,
            user_search_base_source=probe.user_search_base_source,
            group_search_base_source=probe.group_search_base_source,
            duration_ms=duration_ms,
            tested_at=tested_at,
        )

    @transaction.atomic
    def _record_result(
        self,
        *,
        actor: User,
        record: LdapConfiguration | None,
        success: bool,
        fingerprint: str,
        duration_ms: int,
        tested_at: datetime,
        error_code: str,
        secure_transport: bool,
    ) -> bool:
        stale_configuration = False
        if record is not None:
            locked = LdapConfiguration.objects.select_for_update().get(pk=record.pk)
            stale_configuration = locked.version != record.version
            if not stale_configuration:
                locked.last_tested_at = tested_at
                locked.last_test_success = success
                locked.last_test_fingerprint = fingerprint
                locked.last_test_duration_ms = duration_ms
                locked.last_tested_by = actor
                locked.save(
                    update_fields=(
                        "last_tested_at",
                        "last_test_success",
                        "last_test_fingerprint",
                        "last_test_duration_ms",
                        "last_tested_by",
                    )
                )
        _record_event(
            event_type=LDAP_CONNECTION_TESTED,
            actor=actor,
            reason="Teste explícito da conexão LDAP pela área de configurações.",
            changes={
                "success": success,
                "secure_transport": secure_transport,
                "duration_ms": duration_ms,
                "error_code": error_code,
                "stale_configuration": stale_configuration,
            },
        )
        return not stale_configuration
