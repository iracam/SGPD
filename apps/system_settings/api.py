"""SuperAdmin-only LDAP configuration API."""

from __future__ import annotations

from datetime import datetime
from typing import Any, cast

from rest_framework.permissions import BasePermission, IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.models import User
from apps.integrations.active_directory.config import ActiveDirectoryConfig
from apps.integrations.active_directory.exceptions import (
    DirectoryConfigurationError,
    DirectoryContractError,
    DirectoryUnavailableError,
)
from config.api import api_error

from .certificates import validate_certificate_path
from .exceptions import CertificateValidationError
from .models import LdapConfiguration
from .serializers import LdapCertificateUploadSerializer, LdapConfigurationSerializer
from .services import (
    LdapConfigurationCommand,
    TestLdapConnectionService,
    UpdateLdapConfigurationService,
    UploadLdapCertificateCommand,
    UploadLdapCertificateService,
    ValidateLdapConfigurationService,
    ValidatePersistedCertificateService,
    current_persisted_configuration,
)


def _isoformat(value: datetime | None) -> str | None:
    return value.isoformat() if value is not None else None


class IsSuperAdmin(BasePermission):
    def has_permission(self, request: Request, view: APIView) -> bool:
        del view
        user = request.user
        return (
            isinstance(user, User)
            and user.is_authenticated
            and user.is_active
            and user.is_superuser
        )


class SuperAdminAPIView(APIView):
    permission_classes = [IsAuthenticated, IsSuperAdmin]

    def actor(self, request: Request) -> User:
        return cast(User, request.user)


def _certificate_payload(
    config: ActiveDirectoryConfig,
    record: LdapConfiguration | None,
) -> dict[str, Any]:
    configured = bool(config.tls_ca_cert_file)
    payload: dict[str, Any] = {
        "configured": configured,
        "source": (
            "database"
            if record is not None and record.certificate_file
            else ("environment" if configured else None)
        ),
        "original_name": (
            record.certificate_original_name
            if record is not None and record.certificate_file
            else None
        ),
        "sha256": record.certificate_sha256 if record is not None else None,
        "subject": record.certificate_subject if record is not None else None,
        "issuer": record.certificate_issuer if record is not None else None,
        "not_before": _isoformat(record.certificate_not_before) if record is not None else None,
        "not_after": _isoformat(record.certificate_not_after) if record is not None else None,
        "certificate_count": record.certificate_count if record is not None else 0,
        "valid": False,
        "errors": [],
    }
    if not configured:
        return payload
    try:
        info = validate_certificate_path(config.tls_ca_cert_file)
    except CertificateValidationError as exc:
        payload["errors"] = [str(exc)]
        return payload
    payload["valid"] = True
    if not payload["sha256"]:
        payload.update(
            {
                "sha256": info.sha256,
                "subject": info.subject,
                "issuer": info.issuer,
                "not_before": info.not_before.isoformat(),
                "not_after": info.not_after.isoformat(),
                "certificate_count": info.certificate_count,
            }
        )
    return payload


def ldap_configuration_payload() -> dict[str, Any]:
    config = ActiveDirectoryConfig.from_settings()
    record = current_persisted_configuration()
    return {
        "source": config.source,
        "version": record.version if record is not None else 0,
        "enabled": config.enabled,
        "authentication_enabled": config.authentication_enabled,
        "server_address": config.server_address,
        "use_tls": config.use_tls,
        "bind_dn": config.bind_dn,
        "bind_password_configured": bool(config.bind_password),
        "user_search_base": config.user_search_base,
        "group_search_base": config.group_search_base,
        "required_group_dn": config.required_group_dn,
        "tls_require_certificate": config.tls_require_certificate,
        "connect_timeout_seconds": config.connect_timeout_seconds,
        "receive_timeout_seconds": config.receive_timeout_seconds,
        "page_size": config.page_size,
        "result_limit": config.result_limit,
        "nested_group_search": config.nested_group_search,
        "local_superuser_fallback": config.local_superuser_fallback,
        "user_extra_filter": config.user_extra_filter,
        "secure_transport": config.secure_transport,
        "validation": {
            "valid": not config.validation_errors(),
            "errors": config.validation_errors(),
        },
        "certificate": _certificate_payload(config, record),
        "connection_test": {
            "tested_at": _isoformat(record.last_tested_at) if record is not None else None,
            "success": record.last_test_success if record is not None else None,
            "duration_ms": record.last_test_duration_ms if record is not None else None,
            "tested_by": (
                record.last_tested_by.username
                if record is not None and record.last_tested_by
                else None
            ),
        },
        "updated_at": _isoformat(record.updated_at) if record is not None else None,
        "updated_by": record.updated_by.username if record is not None else None,
    }


def _command(data: dict[str, Any], actor: User) -> LdapConfigurationCommand:
    return LdapConfigurationCommand(
        actor=actor,
        expected_version=data["version"],
        enabled=data["enabled"],
        authentication_enabled=data["authentication_enabled"],
        server_address=data["server_address"],
        use_tls=data["use_tls"],
        bind_dn=data["bind_dn"],
        bind_password=data.get("bind_password", ""),
        user_search_base=data["user_search_base"],
        group_search_base=data["group_search_base"],
        required_group_dn=data["required_group_dn"],
        connect_timeout_seconds=data["connect_timeout_seconds"],
        receive_timeout_seconds=data["receive_timeout_seconds"],
        page_size=data["page_size"],
        result_limit=data["result_limit"],
        nested_group_search=data["nested_group_search"],
        local_superuser_fallback=data["local_superuser_fallback"],
        user_extra_filter=data["user_extra_filter"],
    )


class LdapConfigurationView(SuperAdminAPIView):
    def get(self, request: Request) -> Response:
        del request
        return Response(ldap_configuration_payload())

    def put(self, request: Request) -> Response:
        serializer = LdapConfigurationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = cast(dict[str, Any], serializer.validated_data)
        UpdateLdapConfigurationService().execute(_command(data, self.actor(request)))
        return Response(ldap_configuration_payload())


class LdapConfigurationValidationView(SuperAdminAPIView):
    def post(self, request: Request) -> Response:
        serializer = LdapConfigurationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = cast(dict[str, Any], serializer.validated_data)
        errors = ValidateLdapConfigurationService().execute(_command(data, self.actor(request)))
        return Response({"valid": not errors, "errors": errors})


class LdapCertificateUploadView(SuperAdminAPIView):
    def post(self, request: Request) -> Response:
        serializer = LdapCertificateUploadSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = cast(dict[str, Any], serializer.validated_data)
        uploaded_file = data["certificate"]
        UploadLdapCertificateService().execute(
            UploadLdapCertificateCommand(
                actor=self.actor(request),
                expected_version=data["version"],
                original_name=uploaded_file.name,
                content=uploaded_file.read(),
            )
        )
        return Response(ldap_configuration_payload(), status=201)


class LdapCertificateValidationView(SuperAdminAPIView):
    def post(self, request: Request) -> Response:
        result = ValidatePersistedCertificateService().execute(self.actor(request))
        return Response(
            {
                "valid": True,
                "source": result.source,
                "sha256": result.info.sha256,
                "subject": result.info.subject,
                "issuer": result.info.issuer,
                "not_before": result.info.not_before.isoformat(),
                "not_after": result.info.not_after.isoformat(),
                "certificate_count": result.info.certificate_count,
            }
        )


class LdapConnectionTestView(SuperAdminAPIView):
    def post(self, request: Request) -> Response:
        try:
            result = TestLdapConnectionService().execute(self.actor(request))
        except DirectoryConfigurationError as exc:
            return api_error(
                code="ldap_configuration_invalid",
                message=str(exc),
                status_code=400,
            )
        except DirectoryUnavailableError:
            return api_error(
                code="directory_unavailable",
                message="O Active Directory está indisponível ou recusou a conexão.",
                status_code=503,
            )
        except DirectoryContractError as exc:
            return api_error(
                code="directory_contract_error",
                message=str(exc),
                status_code=502,
            )
        except CertificateValidationError as exc:
            return api_error(
                code="ldap_certificate_invalid",
                message=str(exc),
                status_code=400,
            )
        return Response(
            {
                "success": True,
                "secure_transport": result.secure_transport,
                "user_search_base_source": result.user_search_base_source,
                "group_search_base_source": result.group_search_base_source,
                "duration_ms": result.duration_ms,
                "tested_at": result.tested_at.isoformat(),
            }
        )
