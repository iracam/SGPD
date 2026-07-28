from __future__ import annotations

import os
from datetime import timedelta
from pathlib import Path

import pytest
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID
from django.contrib.auth.models import Permission
from django.core.exceptions import PermissionDenied, ValidationError
from django.core.files.storage import FileSystemStorage
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, override_settings
from django.urls import reverse
from django.utils import timezone

from apps.accounts.models import AccountAuditEvent, User
from apps.integrations.active_directory.client import ActiveDirectoryClient
from apps.integrations.active_directory.config import ActiveDirectoryConfig
from apps.integrations.active_directory.dto import DirectoryProbe
from apps.system_settings.models import LdapConfiguration
from apps.system_settings.services import (
    LDAP_CERT_UPLOAD_REASON,
    LDAP_CERT_UPLOADED,
    LDAP_CONFIG_UPDATE_REASON,
    LDAP_CONFIG_UPDATED,
    LDAP_CONNECTION_TESTED,
    LdapConfigurationCommand,
    TestLdapConnectionService,
    UpdateLdapConfigurationService,
    UploadLdapCertificateCommand,
    UploadLdapCertificateService,
)

pytestmark = pytest.mark.django_db


@pytest.fixture
def admin() -> User:
    return User.objects.create_superuser(
        username="superadmin",
        email="superadmin@example.invalid",
        password="SuperAdmin-test!2026",
        first_name="Super",
        last_name="Admin",
    )


@pytest.fixture
def ordinary_admin() -> User:
    user = User.objects.create_user(
        username="administrador.funcional",
        email="administrador.funcional@example.invalid",
        password="Ordinary-admin!2026",
        first_name="Administrador",
        last_name="Funcional",
        is_staff=True,
    )
    user.user_permissions.set(Permission.objects.filter(content_type__app_label="accounts"))
    return user


def configuration_payload(
    *,
    version: int = 0,
    authentication_enabled: bool = False,
    bind_password: str = "Bind-password!2026",
    use_tls: bool = True,
) -> dict[str, object]:
    return {
        "version": version,
        "enabled": True,
        "authentication_enabled": authentication_enabled,
        "server_address": "dc01.example.internal",
        "use_tls": use_tls,
        "bind_dn": "svc.sgpd@example.internal",
        "bind_password": bind_password,
        "user_search_base": "OU=Usuarios,DC=example,DC=internal",
        "group_search_base": "OU=Grupos,DC=example,DC=internal",
        "required_group_dn": "CN=SGPD,OU=Grupos,DC=example,DC=internal",
        "connect_timeout_seconds": 5,
        "receive_timeout_seconds": 10,
        "page_size": 100,
        "result_limit": 50,
        "nested_group_search": True,
        "local_superuser_fallback": True,
        "user_extra_filter": "",
    }


def ca_certificate(*, is_ca: bool = True, expired: bool = False) -> bytes:
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    subject = issuer = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "SGPD Test CA")])
    now = timezone.now()
    not_before = now - timedelta(days=30)
    not_after = now - timedelta(days=1) if expired else now + timedelta(days=365)
    certificate = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(issuer)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(not_before)
        .not_valid_after(not_after)
        .add_extension(x509.BasicConstraints(ca=is_ca, path_length=None), critical=True)
        .sign(key, hashes.SHA256())
    )
    return certificate.public_bytes(serialization.Encoding.PEM)


def use_private_storage(path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    storage = FileSystemStorage(
        location=path,
        base_url=None,
        file_permissions_mode=0o600,
        directory_permissions_mode=0o700,
    )
    field = LdapConfiguration._meta.get_field("certificate_file")
    monkeypatch.setattr(field, "storage", storage)


@pytest.mark.parametrize(
    ("route_name", "method"),
    [
        ("system-settings-api:ldap-configuration", "get"),
        ("system-settings-api:ldap-configuration", "put"),
        ("system-settings-api:ldap-configuration-validate", "post"),
        ("system-settings-api:ldap-certificate-upload", "post"),
        ("system-settings-api:ldap-certificate-validate", "post"),
        ("system-settings-api:ldap-connection-test", "post"),
    ],
)
def test_configuration_endpoints_deny_non_superadmin_even_with_permissions(
    ordinary_admin: User,
    route_name: str,
    method: str,
) -> None:
    client = Client()
    client.force_login(ordinary_admin)
    url = reverse(route_name)

    if method == "get":
        response = client.get(url)
    elif method == "put":
        response = client.put(
            url,
            data=configuration_payload(),
            content_type="application/json",
        )
    else:
        response = client.post(url, data={}, content_type="application/json")

    assert response.status_code == 403
    assert not LdapConfiguration.objects.exists()
    assert not AccountAuditEvent.objects.filter(entity_type="LDAP_CONFIGURATION").exists()


def test_configuration_endpoint_requires_authentication() -> None:
    response = Client().get(reverse("system-settings-api:ldap-configuration"))

    assert response.status_code == 401


@override_settings(
    LDAP_ENABLED=True,
    LDAP_SERVER_URI="ldaps://environment.example.internal:636",
    LDAP_BIND_DN="svc.environment@example.internal",
    LDAP_BIND_PASSWORD="environment-secret",
)
def test_get_uses_environment_baseline_without_exposing_password(admin: User) -> None:
    client = Client()
    client.force_login(admin)

    response = client.get(reverse("system-settings-api:ldap-configuration"))

    assert response.status_code == 200
    body = response.json()
    assert body["source"] == "environment"
    assert body["version"] == 0
    assert body["server_address"] == "environment.example.internal"
    assert body["use_tls"] is True
    assert body["bind_password_configured"]
    assert "environment-secret" not in response.content.decode()
    assert "bind_password" not in body


@override_settings(
    LDAP_ENABLED=True,
    LDAP_SERVER_ADDRESS="plain.example.internal",
    LDAP_USE_TLS=False,
    LDAP_SERVER_URI="ldaps://legacy.example.internal:636",
    LDAP_BIND_DN="svc.environment@example.internal",
    LDAP_BIND_PASSWORD="environment-secret",
)
def test_environment_address_and_tls_choice_override_legacy_uri(admin: User) -> None:
    client = Client()
    client.force_login(admin)

    response = client.get(reverse("system-settings-api:ldap-configuration"))

    assert response.status_code == 200
    assert response.json()["server_address"] == "plain.example.internal"
    assert response.json()["use_tls"] is False
    assert response.json()["secure_transport"] is False


def test_update_persists_encrypted_secret_and_audit(admin: User) -> None:
    client = Client()
    client.force_login(admin)
    payload = configuration_payload()

    response = client.put(
        reverse("system-settings-api:ldap-configuration"),
        data=payload,
        content_type="application/json",
    )

    assert response.status_code == 200
    assert response.json()["source"] == "database"
    assert response.json()["version"] == 1
    assert response.json()["server_address"] == "dc01.example.internal"
    assert response.json()["use_tls"] is True
    assert "Bind-password!2026" not in response.content.decode()
    record = LdapConfiguration.objects.get()
    assert record.server_uri == "ldaps://dc01.example.internal"
    assert record.start_tls is False
    assert record.bind_password_ciphertext
    assert "Bind-password!2026" not in record.bind_password_ciphertext
    effective = ActiveDirectoryConfig.from_settings()
    assert effective.bind_password == "Bind-password!2026"
    event = AccountAuditEvent.objects.get(event_type=LDAP_CONFIG_UPDATED)
    assert event.actor == admin
    assert event.reason == LDAP_CONFIG_UPDATE_REASON
    assert "bind_password" not in str(event.changes)


def test_update_rejects_stale_version_without_mutation_or_audit(admin: User) -> None:
    client = Client()
    client.force_login(admin)
    url = reverse("system-settings-api:ldap-configuration")
    first = client.put(
        url,
        data=configuration_payload(),
        content_type="application/json",
    )
    event_count = AccountAuditEvent.objects.filter(event_type=LDAP_CONFIG_UPDATED).count()

    stale_payload = configuration_payload(version=0)
    stale_payload["server_address"] = "other.example.internal"
    response = client.put(url, data=stale_payload, content_type="application/json")

    assert first.status_code == 200
    assert response.status_code == 400
    assert LdapConfiguration.objects.get().server_uri == "ldaps://dc01.example.internal"
    assert AccountAuditEvent.objects.filter(event_type=LDAP_CONFIG_UPDATED).count() == event_count


def test_configuration_rejects_bulk_update_and_delete(admin: User) -> None:
    client = Client()
    client.force_login(admin)
    response = client.put(
        reverse("system-settings-api:ldap-configuration"),
        data=configuration_payload(),
        content_type="application/json",
    )

    assert response.status_code == 200
    with pytest.raises(ValidationError, match="service auditado"):
        LdapConfiguration.objects.update(enabled=False)
    with pytest.raises(ValidationError, match="não excluída"):
        LdapConfiguration.objects.all().delete()


def test_direct_service_rejects_non_superadmin(ordinary_admin: User) -> None:
    payload = configuration_payload()
    with pytest.raises(PermissionDenied, match="SuperAdmin"):
        UpdateLdapConfigurationService().execute(
            LdapConfigurationCommand(
                actor=ordinary_admin,
                expected_version=0,
                enabled=True,
                authentication_enabled=False,
                server_address=str(payload["server_address"]),
                use_tls=bool(payload["use_tls"]),
                bind_dn=str(payload["bind_dn"]),
                bind_password=str(payload["bind_password"]),
                user_search_base=str(payload["user_search_base"]),
                group_search_base=str(payload["group_search_base"]),
                required_group_dn=str(payload["required_group_dn"]),
                connect_timeout_seconds=5,
                receive_timeout_seconds=10,
                page_size=100,
                result_limit=50,
                nested_group_search=True,
                local_superuser_fallback=True,
                user_extra_filter="",
            )
        )


def test_validate_candidate_does_not_persist(admin: User) -> None:
    client = Client()
    client.force_login(admin)

    response = client.post(
        reverse("system-settings-api:ldap-configuration-validate"),
        data=configuration_payload(),
        content_type="application/json",
    )

    assert response.status_code == 200
    assert response.json() == {"valid": True, "errors": []}
    assert not LdapConfiguration.objects.exists()
    assert not AccountAuditEvent.objects.filter(entity_type="LDAP_CONFIGURATION").exists()


def test_server_address_rejects_manual_ldap_scheme(admin: User) -> None:
    client = Client()
    client.force_login(admin)
    payload = configuration_payload()
    payload["server_address"] = "ldaps://dc01.example.internal:636"

    response = client.put(
        reverse("system-settings-api:ldap-configuration"),
        data=payload,
        content_type="application/json",
    )

    assert response.status_code == 400
    assert "protocolo é automático" in str(response.json())
    assert not LdapConfiguration.objects.exists()


def test_tls_authentication_cannot_be_enabled_without_certificate_and_probe(
    admin: User,
) -> None:
    client = Client()
    client.force_login(admin)
    payload = configuration_payload(authentication_enabled=True)

    response = client.put(
        reverse("system-settings-api:ldap-configuration"),
        data=payload,
        content_type="application/json",
    )

    assert response.status_code == 400
    assert "certificate" in str(response.json()).lower() or "ca" in str(response.json()).lower()
    assert not LdapConfiguration.objects.exists()


def test_plain_ldap_probe_allows_authentication_without_certificate(
    admin: User,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client = Client()
    client.force_login(admin)
    config_url = reverse("system-settings-api:ldap-configuration")
    saved = client.put(
        config_url,
        data=configuration_payload(use_tls=False),
        content_type="application/json",
    )
    monkeypatch.setattr(
        ActiveDirectoryClient,
        "probe",
        lambda self: DirectoryProbe(
            user_search_base_source="configured",
            group_search_base_source="configured",
            secure_transport=False,
        ),
    )

    tested = client.post(
        reverse("system-settings-api:ldap-connection-test"),
        data={},
        content_type="application/json",
    )
    activation_payload = configuration_payload(
        version=saved.json()["version"],
        authentication_enabled=True,
        bind_password="",
        use_tls=False,
    )
    activated = client.put(
        config_url,
        data=activation_payload,
        content_type="application/json",
    )

    assert saved.status_code == 200
    assert saved.json()["server_address"] == "dc01.example.internal"
    assert saved.json()["use_tls"] is False
    assert tested.status_code == 200
    assert tested.json()["secure_transport"] is False
    assert activated.status_code == 200
    assert activated.json()["authentication_enabled"] is True
    assert activated.json()["secure_transport"] is False
    assert not activated.json()["certificate"]["configured"]
    assert LdapConfiguration.objects.get().server_uri == "ldap://dc01.example.internal"


def test_certificate_upload_and_validation_are_private(
    admin: User,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    use_private_storage(tmp_path, monkeypatch)
    client = Client()
    client.force_login(admin)
    config_response = client.put(
        reverse("system-settings-api:ldap-configuration"),
        data=configuration_payload(),
        content_type="application/json",
    )
    certificate = SimpleUploadedFile(
        "corporate-ca.pem",
        ca_certificate(),
        content_type="application/x-pem-file",
    )

    upload = client.post(
        reverse("system-settings-api:ldap-certificate-upload"),
        data={
            "version": config_response.json()["version"],
            "certificate": certificate,
        },
    )
    validation = client.post(
        reverse("system-settings-api:ldap-certificate-validate"),
        data={},
        content_type="application/json",
    )

    assert upload.status_code == 201
    body = upload.json()
    assert body["certificate"]["valid"]
    assert body["certificate"]["original_name"] == "corporate-ca.pem"
    assert "ldap-ca/" not in upload.content.decode()
    assert str(tmp_path) not in upload.content.decode()
    assert validation.status_code == 200
    assert validation.json()["valid"]
    record = LdapConfiguration.objects.get()
    stored_path = tmp_path / record.certificate_file.name
    assert stored_path.exists()
    assert os.stat(stored_path).st_mode & 0o777 == 0o600
    event = AccountAuditEvent.objects.get(event_type=LDAP_CERT_UPLOADED)
    assert event.reason == LDAP_CERT_UPLOAD_REASON


def test_certificate_replacement_disables_active_authentication_until_new_probe(
    admin: User,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    use_private_storage(tmp_path, monkeypatch)
    record = LdapConfiguration.objects.create(
        key="PRIMARY",
        enabled=True,
        authentication_enabled=True,
        server_uri="ldaps://dc01.example.internal:636",
        bind_dn="svc.sgpd@example.internal",
        bind_password_ciphertext="not-read-during-upload",
        user_search_base="OU=Usuarios,DC=example,DC=internal",
        local_superuser_fallback=True,
        updated_by=admin,
    )

    updated = UploadLdapCertificateService().execute(
        UploadLdapCertificateCommand(
            actor=admin,
            expected_version=record.version,
            original_name="new-ca.pem",
            content=ca_certificate(),
        )
    )

    assert updated.authentication_enabled is False
    assert updated.last_test_success is None
    event = AccountAuditEvent.objects.get(event_type=LDAP_CERT_UPLOADED)
    assert event.changes["authentication_disabled"] is True


def test_certificate_upload_does_not_change_plain_ldap_authentication_or_probe(
    admin: User,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    use_private_storage(tmp_path, monkeypatch)
    tested_at = timezone.now()
    record = LdapConfiguration.objects.create(
        key="PRIMARY",
        enabled=True,
        authentication_enabled=True,
        server_uri="ldap://dc01.example.internal:389",
        bind_dn="svc.sgpd@example.internal",
        bind_password_ciphertext="not-read-during-upload",
        user_search_base="OU=Usuarios,DC=example,DC=internal",
        local_superuser_fallback=True,
        last_tested_at=tested_at,
        last_test_success=True,
        last_test_fingerprint="a" * 64,
        last_test_duration_ms=10,
        last_tested_by=admin,
        updated_by=admin,
    )

    updated = UploadLdapCertificateService().execute(
        UploadLdapCertificateCommand(
            actor=admin,
            expected_version=record.version,
            original_name="future-ca.pem",
            content=ca_certificate(),
        )
    )

    assert updated.authentication_enabled is True
    assert updated.last_tested_at == tested_at
    assert updated.last_test_success is True
    assert updated.last_test_fingerprint == "a" * 64
    event = AccountAuditEvent.objects.get(event_type=LDAP_CERT_UPLOADED)
    assert event.changes["authentication_disabled"] is False


def test_certificate_upload_accepts_der_ca(
    admin: User,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    use_private_storage(tmp_path, monkeypatch)
    der_certificate = x509.load_pem_x509_certificate(ca_certificate()).public_bytes(
        serialization.Encoding.DER
    )

    record = UploadLdapCertificateService().execute(
        UploadLdapCertificateCommand(
            actor=admin,
            expected_version=0,
            original_name="corporate-ca.cer",
            content=der_certificate,
        )
    )

    assert record.certificate_original_name == "corporate-ca.cer"
    stored = (tmp_path / record.certificate_file.name).read_bytes()
    assert stored.startswith(b"-----BEGIN CERTIFICATE-----")


def test_certificate_file_is_removed_when_audit_fails(
    admin: User,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    use_private_storage(tmp_path, monkeypatch)

    def fail_audit(**kwargs: object) -> None:
        del kwargs
        raise RuntimeError("audit unavailable")

    monkeypatch.setattr("apps.system_settings.services._record_event", fail_audit)

    with pytest.raises(RuntimeError, match="audit unavailable"):
        UploadLdapCertificateService().execute(
            UploadLdapCertificateCommand(
                actor=admin,
                expected_version=0,
                original_name="ca.pem",
                content=ca_certificate(),
            )
        )

    assert not LdapConfiguration.objects.exists()
    assert not any(path.is_file() for path in tmp_path.rglob("*"))


def test_probe_result_does_not_overwrite_a_newer_configuration(
    admin: User,
) -> None:
    client = Client()
    client.force_login(admin)
    first = client.put(
        reverse("system-settings-api:ldap-configuration"),
        data=configuration_payload(),
        content_type="application/json",
    )
    stale_record = LdapConfiguration.objects.get()
    newer_payload = configuration_payload(version=first.json()["version"], bind_password="")
    newer_payload["server_address"] = "dc02.example.internal"
    second = client.put(
        reverse("system-settings-api:ldap-configuration"),
        data=newer_payload,
        content_type="application/json",
    )

    recorded = TestLdapConnectionService()._record_result(
        actor=admin,
        record=stale_record,
        success=True,
        fingerprint="a" * 64,
        duration_ms=10,
        tested_at=timezone.now(),
        error_code="",
        secure_transport=True,
    )

    assert second.status_code == 200
    assert recorded is False
    current = LdapConfiguration.objects.get()
    assert current.version == second.json()["version"]
    assert current.last_test_success is None
    event = AccountAuditEvent.objects.filter(event_type=LDAP_CONNECTION_TESTED).latest("pk")
    assert event.changes["stale_configuration"] is True


@pytest.mark.parametrize(
    "certificate",
    [
        b"not-a-certificate",
        ca_certificate(is_ca=False),
        ca_certificate(expired=True),
    ],
)
def test_certificate_upload_rejects_invalid_content(
    admin: User,
    tmp_path: Path,
    certificate: bytes,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    use_private_storage(tmp_path, monkeypatch)
    client = Client()
    client.force_login(admin)

    response = client.post(
        reverse("system-settings-api:ldap-certificate-upload"),
        data={
            "version": 0,
            "certificate": SimpleUploadedFile("invalid.pem", certificate),
        },
    )

    assert response.status_code == 400
    assert not LdapConfiguration.objects.exists()
    assert not list(tmp_path.rglob("*"))


def test_successful_probe_allows_authentication_activation(
    admin: User,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    use_private_storage(tmp_path, monkeypatch)
    client = Client()
    client.force_login(admin)
    config_url = reverse("system-settings-api:ldap-configuration")
    saved = client.put(
        config_url,
        data=configuration_payload(),
        content_type="application/json",
    )

    uploaded = client.post(
        reverse("system-settings-api:ldap-certificate-upload"),
        data={
            "version": saved.json()["version"],
            "certificate": SimpleUploadedFile("ca.pem", ca_certificate()),
        },
    )
    monkeypatch.setattr(
        ActiveDirectoryClient,
        "probe",
        lambda self: DirectoryProbe(
            user_search_base_source="configured",
            group_search_base_source="configured",
            secure_transport=True,
        ),
    )
    tested = client.post(
        reverse("system-settings-api:ldap-connection-test"),
        data={},
        content_type="application/json",
    )
    activation_payload = configuration_payload(
        version=uploaded.json()["version"],
        authentication_enabled=True,
        bind_password="",
    )
    activated = client.put(
        config_url,
        data=activation_payload,
        content_type="application/json",
    )

    assert tested.status_code == 200
    assert tested.json()["success"]
    assert activated.status_code == 200
    assert activated.json()["authentication_enabled"]
    assert AccountAuditEvent.objects.filter(event_type=LDAP_CONNECTION_TESTED).exists()
    assert LdapConfiguration.objects.get().last_test_success is True
