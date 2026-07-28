from __future__ import annotations

import uuid

import pytest
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import connection
from django.test import Client, override_settings
from django.urls import reverse
from django.utils import timezone
from django_auth_ldap.backend import LDAPBackend, ldap_error  # type: ignore[import-untyped]

from apps.accounts.models import AccountAuditEvent, AccountEventType, User
from apps.accounts.services import (
    DIRECTORY_IMPORT_REASON,
    ChangeOwnPasswordCommand,
    ChangeOwnPasswordService,
    CreateUserFromDirectoryCommand,
    CreateUserFromDirectoryService,
    LinkAdIdentityCommand,
    LinkDirectoryIdentityService,
    ResetPasswordCommand,
    ResetPasswordService,
)
from apps.integrations.active_directory.backends import LocalAccountBackend
from apps.integrations.active_directory.checks import active_directory_configuration_check
from apps.integrations.active_directory.client import (
    ActiveDirectoryClient,
    normalize_object_guid,
)
from apps.integrations.active_directory.config import ActiveDirectoryConfig
from apps.integrations.active_directory.dto import DirectoryGroup, DirectoryUser
from apps.integrations.active_directory.exceptions import (
    DirectoryConfigurationError,
    DirectoryUnavailableError,
)
from apps.integrations.active_directory.ldap_backend import ActiveDirectoryBackend

pytestmark = pytest.mark.django_db

IDENTIFIER = "0899b887-704b-4c59-ae09-3a678a4e02a1"


def directory_user(**overrides: object) -> DirectoryUser:
    values: dict[str, object] = {
        "identifier": IDENTIFIER,
        "username": "maria.silva",
        "user_principal_name": "maria.silva@example.internal",
        "first_name": "Maria",
        "last_name": "Silva",
        "display_name": "Maria Silva",
        "email": "maria.silva@example.internal",
        "distinguished_name": ("CN=Maria Silva,OU=Usuarios,DC=example,DC=internal"),
    }
    values.update(overrides)
    return DirectoryUser(**values)  # type: ignore[arg-type]


class FakeDirectory:
    def __init__(self, identity: DirectoryUser | None = None) -> None:
        self.identity = identity or directory_user()
        self.calls: list[str] = []

    def get_user(self, identifier: str) -> DirectoryUser:
        self.calls.append(identifier)
        return self.identity


@pytest.fixture
def admin() -> User:
    return User.objects.create_superuser(
        username="admin.ad",
        email="admin.ad@example.invalid",
        password="Admin-test!2026",
        first_name="Admin",
        last_name="AD",
    )


def test_object_guid_binary_is_normalized_with_active_directory_byte_order() -> None:
    expected = uuid.UUID(IDENTIFIER)

    assert normalize_object_guid(expected.bytes_le) == IDENTIFIER
    assert normalize_object_guid("{" + IDENTIFIER.upper() + "}") == IDENTIFIER


def test_configuration_requires_valid_uri_and_user_base_for_authentication() -> None:
    config = ActiveDirectoryConfig(
        enabled=True,
        authentication_enabled=True,
        server_uri="10.0.0.10",
        bind_dn="svc",
        bind_password="secret",
        user_search_base="",
        group_search_base="",
        required_group_dn="",
        start_tls=False,
        tls_require_certificate=True,
        tls_ca_cert_file="",
        connect_timeout_seconds=5,
        receive_timeout_seconds=10,
        page_size=100,
        result_limit=50,
        nested_group_search=True,
        local_superuser_fallback=True,
        user_extra_filter="",
    )

    errors = config.validation_errors()

    assert any("servidor LDAP" in error for error in errors)
    assert any("LDAP_USER_SEARCH_BASE" in error for error in errors)


def test_disabled_configuration_never_attempts_a_directory_connection() -> None:
    config = ActiveDirectoryConfig.from_settings()

    with pytest.raises(DirectoryConfigurationError, match="LDAP_ENABLED=false"):
        ActiveDirectoryClient(config).probe()


def test_user_filter_uses_exactly_the_required_group_from_configuration() -> None:
    config = ActiveDirectoryConfig(
        enabled=True,
        authentication_enabled=False,
        server_uri="ldaps://dc01.example.internal:636",
        bind_dn="svc.sgpd@example.internal",
        bind_password="secret",
        user_search_base="OU=Usuarios,DC=example,DC=internal",
        group_search_base="OU=Grupos,DC=example,DC=internal",
        required_group_dn="CN=SGPD,OU=Grupos,DC=example,DC=internal",
        start_tls=False,
        tls_require_certificate=True,
        tls_ca_cert_file="",
        connect_timeout_seconds=5,
        receive_timeout_seconds=10,
        page_size=100,
        result_limit=50,
        nested_group_search=True,
        local_superuser_fallback=True,
        user_extra_filter="",
    )

    search_filter = ActiveDirectoryClient(config)._user_filter(  # noqa: SLF001
        "(sAMAccountName=*maria*)",
    )

    assert "CN=SGPD,OU=Grupos,DC=example,DC=internal" in search_filter
    assert "CN=Financeiro,OU=Grupos,DC=example,DC=internal" not in search_filter


@pytest.mark.parametrize(
    ("debug", "authentication_enabled"),
    [
        (False, False),
        (False, True),
        (True, False),
        (True, True),
    ],
)
def test_plain_ldap_is_valid_for_discovery_and_authentication_with_warning_status(
    debug: bool,
    authentication_enabled: bool,
) -> None:
    with override_settings(
        DEBUG=debug,
        LDAP_ENABLED=True,
        LDAP_AUTHENTICATION_ENABLED=authentication_enabled,
        LDAP_SERVER_URI="ldap://ad.bsa.local:389",
        LDAP_BIND_DN="svc.sgpd@bsa.local",
        LDAP_BIND_PASSWORD="secret",
        LDAP_USER_SEARCH_BASE="OU=Usuarios,DC=bsa,DC=local",
        LDAP_START_TLS=False,
        # A política de certificado é irrelevante enquanto o transporte é
        # explicitamente LDAP simples.
        LDAP_TLS_REQUIRE_CERTIFICATE=False,
    ):
        config = ActiveDirectoryConfig.from_settings()
        status = ActiveDirectoryClient(config).status()

    assert not config.validation_errors()
    assert status["insecure_transport"]
    assert not status["secure_transport"]


@override_settings(
    LDAP_ENABLED=True,
    LDAP_AUTHENTICATION_ENABLED=True,
    LDAP_SERVER_URI="ldap://ad.bsa.local:389",
    LDAP_BIND_DN="svc.sgpd@bsa.local",
    LDAP_BIND_PASSWORD="secret",
    LDAP_USER_SEARCH_BASE="OU=Usuarios,DC=bsa,DC=local",
    LDAP_START_TLS=False,
    LDAP_TLS_REQUIRE_CERTIFICATE=True,
)
def test_plain_ldap_emits_permanent_warning_for_discovery_and_authentication() -> None:
    messages = active_directory_configuration_check()

    assert len(messages) == 1
    assert messages[0].id == "sgpd.AD900"
    assert "descoberta e autenticação" in str(messages[0].msg)
    assert "credencial técnica" in str(messages[0].msg)
    assert "senhas dos usuários" in str(messages[0].msg)
    assert "sem criptografia" in str(messages[0].msg)


def test_create_user_from_directory_is_linked_unusable_and_audited(admin: User) -> None:
    directory = FakeDirectory()

    user = CreateUserFromDirectoryService(directory).execute(
        CreateUserFromDirectoryCommand(
            actor=admin,
            identifier=IDENTIFIER,
        )
    )

    assert user.username == "maria.silva"
    assert user.email == "maria.silva@example.internal"
    assert user.ad_identifier == IDENTIFIER
    assert user.ad_username == "maria.silva"
    assert user.ad_linked_by == admin
    assert not user.has_usable_password()
    assert not user.must_change_password
    created_event = AccountAuditEvent.objects.get(
        event_type=AccountEventType.USER_CREATED,
        target_user=user,
    )
    assert created_event.reason == DIRECTORY_IMPORT_REASON
    assert AccountAuditEvent.objects.filter(
        event_type=AccountEventType.AD_LINKED,
        target_user=user,
    ).exists()


def test_create_user_from_directory_is_idempotent_by_object_guid(admin: User) -> None:
    directory = FakeDirectory()
    command = CreateUserFromDirectoryCommand(
        actor=admin,
        identifier=IDENTIFIER,
    )

    first = CreateUserFromDirectoryService(directory).execute(command)
    second = CreateUserFromDirectoryService(directory).execute(command)

    assert second.pk == first.pk
    assert User.objects.filter(ad_identifier=IDENTIFIER).count() == 1
    assert (
        AccountAuditEvent.objects.filter(
            event_type=AccountEventType.USER_CREATED,
            target_user=first,
        ).count()
        == 1
    )


def test_create_user_from_directory_avoids_for_update_with_limit_on_oracle(
    admin: User,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Reproduce Oracle's relevant compiler capabilities while keeping SQLite's
    # execution syntax for this isolated test. A first()/exists() after
    # select_for_update() raises NotSupportedError under these feature flags.
    monkeypatch.setattr(connection.features, "has_select_for_update", True)
    monkeypatch.setattr(
        connection.features,
        "supports_select_for_update_with_limit",
        False,
    )
    monkeypatch.setattr(connection.ops, "for_update_sql", lambda **_kwargs: "")

    user = CreateUserFromDirectoryService(FakeDirectory()).execute(
        CreateUserFromDirectoryCommand(
            actor=admin,
            identifier=IDENTIFIER,
        )
    )

    assert user.ad_identifier == IDENTIFIER


def test_create_user_from_directory_rejects_local_username_collision(admin: User) -> None:
    User.objects.create_user(
        username="maria.silva",
        email="outra@example.invalid",
        password="Local-test!2026",
    )

    with pytest.raises(ValidationError, match="mesmo login"):
        CreateUserFromDirectoryService(FakeDirectory()).execute(
            CreateUserFromDirectoryCommand(
                actor=admin,
                identifier=IDENTIFIER,
            )
        )

    assert not User.objects.filter(ad_identifier=IDENTIFIER).exists()
    assert not AccountAuditEvent.objects.filter(event_type=AccountEventType.AD_LINKED).exists()


def test_create_user_from_directory_requires_both_permissions() -> None:
    actor = User.objects.create_user(
        username="sem.permissao",
        email="sem.permissao@example.invalid",
        password="No-permission!2026",
    )

    with pytest.raises(PermissionDenied):
        CreateUserFromDirectoryService(FakeDirectory()).execute(
            CreateUserFromDirectoryCommand(
                actor=actor,
                identifier=IDENTIFIER,
            )
        )


def test_link_existing_user_revalidates_identity_and_ignores_submitted_username(
    admin: User,
) -> None:
    user = User.objects.create_user(
        username="conta.local",
        email="conta.local@example.invalid",
        password="Local-password!2026",
        first_name="Conta",
        last_name="Local",
    )

    linked = LinkDirectoryIdentityService(FakeDirectory()).execute(
        LinkAdIdentityCommand(
            actor=admin,
            user_id=user.pk,
            expected_version=user.version,
            identifier=IDENTIFIER,
            username="valor.adulterado",
            reason="Identidade confirmada no diretório.",
        )
    )

    assert linked.ad_identifier == IDENTIFIER
    assert linked.ad_username == "maria.silva"


@override_settings(
    LDAP_AUTHENTICATION_ENABLED=True,
    LDAP_LOCAL_SUPERUSER_FALLBACK=True,
)
def test_linked_common_user_cannot_fall_back_to_local_password() -> None:
    linker = User.objects.create_superuser(
        username="linker",
        email="linker@example.invalid",
        password="Linker-password!2026",
    )
    user = User.objects.create_user(
        username="conta.local",
        email="conta.local@example.invalid",
        password="Local-password!2026",
    )
    user.ad_identifier = IDENTIFIER
    user.ad_username = "maria.silva"
    user.ad_linked_at = timezone.now()
    user.ad_linked_by = linker
    user.save(
        update_fields=(
            "ad_identifier",
            "ad_username",
            "ad_linked_at",
            "ad_linked_by",
        )
    )

    authenticated = LocalAccountBackend().authenticate(
        None,
        username=user.username,
        password="Local-password!2026",
    )

    assert authenticated is None


@override_settings(LDAP_AUTHENTICATION_ENABLED=True)
def test_linked_common_user_cannot_change_local_password(admin: User) -> None:
    user = User.objects.create_user(
        username="conta.vinculada",
        email="conta.vinculada@example.invalid",
        password="Local-password!2026",
        first_name="Conta",
        last_name="Vinculada",
    )
    user.ad_identifier = IDENTIFIER
    user.ad_username = "maria.silva"
    user.ad_linked_at = timezone.now()
    user.ad_linked_by = admin
    user.save(
        update_fields=(
            "ad_identifier",
            "ad_username",
            "ad_linked_at",
            "ad_linked_by",
        )
    )

    with pytest.raises(ValidationError, match="Active Directory"):
        ChangeOwnPasswordService().execute(
            ChangeOwnPasswordCommand(
                user_id=user.pk,
                current_password="Local-password!2026",
                new_password="Changed-password!2026",
            )
        )

    user.refresh_from_db()
    assert user.check_password("Local-password!2026")


@override_settings(LDAP_AUTHENTICATION_ENABLED=False)
def test_imported_user_can_receive_and_use_local_password_while_ad_login_is_off(
    admin: User,
) -> None:
    user = CreateUserFromDirectoryService(FakeDirectory()).execute(
        CreateUserFromDirectoryCommand(actor=admin, identifier=IDENTIFIER)
    )
    admin_client = Client()
    admin_client.force_login(admin)

    reset_response = admin_client.post(
        reverse("accounts-api:user-reset-password", kwargs={"user_id": user.pk}),
        data={
            "password": "Temporary-local!2026",
            "password_confirm": "Temporary-local!2026",
            "must_change_password": False,
            "reason": "Teste local enquanto o login AD está desligado.",
        },
        content_type="application/json",
    )
    login_client = Client(enforce_csrf_checks=True)
    login_client.get(reverse("auth-api:csrf"))
    login_response = login_client.post(
        reverse("auth-api:login"),
        data={"username": user.username, "password": "Temporary-local!2026"},
        content_type="application/json",
        headers={"x-csrftoken": login_client.cookies["csrftoken"].value},
    )

    assert reset_response.status_code == 200
    assert login_response.status_code == 200
    assert login_response.json()["username"] == user.username


@override_settings(
    LDAP_AUTHENTICATION_ENABLED=True,
    LDAP_LOCAL_SUPERUSER_FALLBACK=True,
)
def test_admin_cannot_reset_linked_common_user_password_when_ad_login_is_on(
    admin: User,
) -> None:
    user = CreateUserFromDirectoryService(FakeDirectory()).execute(
        CreateUserFromDirectoryCommand(actor=admin, identifier=IDENTIFIER)
    )
    previous_version = user.version

    with pytest.raises(ValidationError, match="Active Directory"):
        ResetPasswordService().execute(
            ResetPasswordCommand(
                actor=admin,
                user_id=user.pk,
                password="Must-not-be-saved!2026",
                must_change_password=False,
                reason="Tentativa incompatível com a política AD.",
            )
        )

    user.refresh_from_db()
    assert user.version == previous_version
    assert not user.has_usable_password()
    assert not AccountAuditEvent.objects.filter(
        event_type=AccountEventType.PASSWORD_RESET,
        target_user=user,
    ).exists()


@override_settings(
    LDAP_AUTHENTICATION_ENABLED=True,
    LDAP_LOCAL_SUPERUSER_FALLBACK=True,
)
def test_linked_superuser_password_reset_remains_available_for_fallback(
    admin: User,
) -> None:
    admin.ad_identifier = IDENTIFIER
    admin.ad_username = "admin.ad"
    admin.ad_linked_at = timezone.now()
    admin.ad_linked_by = admin
    admin.save(
        update_fields=(
            "ad_identifier",
            "ad_username",
            "ad_linked_at",
            "ad_linked_by",
        )
    )

    ResetPasswordService().execute(
        ResetPasswordCommand(
            actor=admin,
            user_id=admin.pk,
            password="Fallback-updated!2026",
            must_change_password=False,
            reason="Rotação da credencial de contingência.",
        )
    )

    admin.refresh_from_db()
    assert admin.check_password("Fallback-updated!2026")


@override_settings(
    LDAP_AUTHENTICATION_ENABLED=True,
    LDAP_LOCAL_SUPERUSER_FALLBACK=False,
)
def test_linked_superuser_password_reset_is_blocked_when_fallback_is_off(
    admin: User,
) -> None:
    admin.ad_identifier = IDENTIFIER
    admin.ad_username = "admin.ad"
    admin.ad_linked_at = timezone.now()
    admin.ad_linked_by = admin
    admin.save(
        update_fields=(
            "ad_identifier",
            "ad_username",
            "ad_linked_at",
            "ad_linked_by",
        )
    )

    with pytest.raises(ValidationError, match="Active Directory"):
        ResetPasswordService().execute(
            ResetPasswordCommand(
                actor=admin,
                user_id=admin.pk,
                password="Must-not-be-saved!2026",
                must_change_password=False,
                reason="Fallback desativado.",
            )
        )


@override_settings(
    LDAP_AUTHENTICATION_ENABLED=True,
    LDAP_LOCAL_SUPERUSER_FALLBACK=True,
)
def test_unlinked_local_user_and_superuser_contingency_still_authenticate() -> None:
    local = User.objects.create_user(
        username="somente.local",
        email="somente.local@example.invalid",
        password="Local-password!2026",
    )
    admin = User.objects.create_superuser(
        username="contingencia",
        email="contingencia@example.invalid",
        password="Contingency-password!2026",
    )
    admin.ad_identifier = IDENTIFIER
    admin.ad_username = "admin.ad"
    admin.ad_linked_at = timezone.now()
    admin.ad_linked_by = admin
    admin.save(
        update_fields=(
            "ad_identifier",
            "ad_username",
            "ad_linked_at",
            "ad_linked_by",
        )
    )

    assert (
        LocalAccountBackend().authenticate(
            None,
            username=local.username,
            password="Local-password!2026",
        )
        == local
    )
    assert (
        LocalAccountBackend().authenticate(
            None,
            username=admin.username,
            password="Contingency-password!2026",
        )
        == admin
    )


@override_settings(
    LDAP_AUTHENTICATION_ENABLED=True,
    LDAP_ENABLED=True,
    LDAP_SERVER_URI="ldaps://dc01.example.internal:636",
    LDAP_BIND_DN="svc.sgpd@example.internal",
    LDAP_BIND_PASSWORD="secret",
    LDAP_USER_SEARCH_BASE="OU=Usuarios,DC=example,DC=internal",
    LDAP_START_TLS=False,
    LDAP_TLS_REQUIRE_CERTIFICATE=True,
    LDAP_LOCAL_SUPERUSER_FALLBACK=True,
)
def test_superuser_contingency_skips_active_directory(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    admin = User.objects.create_superuser(
        username="contingencia.ad",
        email="contingencia.ad@example.invalid",
        password="Contingency-password!2026",
    )
    admin.ad_identifier = IDENTIFIER
    admin.ad_username = "contingencia.ad"
    admin.ad_linked_at = timezone.now()
    admin.ad_linked_by = admin
    admin.save(
        update_fields=(
            "ad_identifier",
            "ad_username",
            "ad_linked_at",
            "ad_linked_by",
        )
    )
    called = False

    def unexpected_authenticate(*args: object, **kwargs: object) -> None:
        nonlocal called
        called = True

    monkeypatch.setattr(LDAPBackend, "authenticate", unexpected_authenticate)

    assert (
        ActiveDirectoryBackend().authenticate(
            None,
            username=admin.username,
            password="Contingency-password!2026",
        )
        is None
    )
    assert not called
    assert (
        LocalAccountBackend().authenticate(
            None,
            username=admin.username,
            password="Contingency-password!2026",
        )
        == admin
    )


def test_django_auth_ldap_backend_resolves_local_user_by_object_guid(admin: User) -> None:
    identity = directory_user()
    linked = User.objects.create_user(
        username="conta.sgpd",
        email="conta.sgpd@example.invalid",
        password="Not-used!2026",
        ad_identifier=identity.identifier,
        ad_username=identity.username,
        ad_linked_at=timezone.now(),
        ad_linked_by=admin,
    )
    ldap_user = type(
        "FakeLdapUser",
        (),
        {"attrs": {"objectGUID": [uuid.UUID(IDENTIFIER).bytes_le]}},
    )()

    resolved, built = ActiveDirectoryBackend().get_or_build_user(
        identity.username,
        ldap_user,
    )

    assert resolved == linked
    assert not built


def test_django_auth_ldap_backend_never_builds_from_unknown_valid_credentials() -> None:
    unknown = uuid.uuid4()
    ldap_user = type(
        "FakeLdapUser",
        (),
        {"attrs": {"objectGUID": [unknown.bytes_le]}},
    )()

    resolved, built = ActiveDirectoryBackend().get_or_build_user(
        "nao.provisionado",
        ldap_user,
    )

    assert built
    assert resolved.pk is None
    assert resolved.username == "nao.provisionado"


@override_settings(
    LDAP_AUTHENTICATION_ENABLED=True,
    LDAP_ENABLED=True,
    LDAP_SERVER_URI="ldaps://dc01.example.internal:636",
    LDAP_BIND_DN="svc.sgpd@example.internal",
    LDAP_BIND_PASSWORD="secret",
    LDAP_USER_SEARCH_BASE="OU=Usuarios,DC=example,DC=internal",
    LDAP_START_TLS=False,
    LDAP_TLS_REQUIRE_CERTIFICATE=True,
)
def test_django_auth_ldap_backend_does_not_query_ad_for_unlinked_login(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    called = False

    def unexpected_authenticate(*args: object, **kwargs: object) -> None:
        nonlocal called
        called = True

    monkeypatch.setattr(LDAPBackend, "authenticate", unexpected_authenticate)

    result = ActiveDirectoryBackend().authenticate(
        None,
        username="desconhecido",
        password="qualquer",
    )

    assert result is None
    assert not called


@override_settings(
    LDAP_AUTHENTICATION_ENABLED=True,
    LDAP_ENABLED=True,
    LDAP_SERVER_URI="ldaps://dc01.example.internal:636",
    LDAP_BIND_DN="svc.sgpd@example.internal",
    LDAP_BIND_PASSWORD="secret",
    LDAP_USER_SEARCH_BASE="OU=Usuarios,DC=example,DC=internal",
    LDAP_START_TLS=False,
    LDAP_TLS_REQUIRE_CERTIFICATE=True,
)
def test_django_auth_ldap_backend_accepts_matching_prelinked_user(
    admin: User,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    linked = User.objects.create_user(
        username="conta.sgpd",
        email="conta.sgpd@example.invalid",
        password="Not-used!2026",
        first_name="Conta",
        last_name="SGPD",
        ad_identifier=IDENTIFIER,
        ad_username="maria.silva",
        ad_linked_at=timezone.now(),
        ad_linked_by=admin,
    )
    monkeypatch.setattr(
        LDAPBackend,
        "authenticate",
        lambda self, request, username=None, password=None, **kwargs: linked,
    )

    authenticated = ActiveDirectoryBackend().authenticate(
        None,
        username="maria.silva",
        password="credencial-ad",
    )

    assert authenticated == linked


def test_django_auth_ldap_error_is_exposed_as_directory_unavailable() -> None:
    with pytest.raises(DirectoryUnavailableError):
        ldap_error.send(
            sender=ActiveDirectoryBackend,
            context="authenticate",
            user=None,
            request=None,
            exception=RuntimeError("driver detail must not escape"),
        )


def test_directory_user_search_api_ignores_extra_group_and_returns_link_state(
    admin: User,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    identity = directory_user()
    linked = User.objects.create_user(
        username=identity.username,
        email=identity.email,
        password="Not-used!2026",
        ad_identifier=identity.identifier,
        ad_username=identity.username,
        ad_linked_at=admin.date_joined,
        ad_linked_by=admin,
    )
    monkeypatch.setattr(
        ActiveDirectoryClient,
        "search_users",
        lambda self, query, limit=None: [identity],
    )
    client = Client()
    client.force_login(admin)

    response = client.get(
        reverse("accounts-api:directory-user-search"),
        {"q": "maria", "group_dn": "CN=SGPD,OU=Grupos,DC=example,DC=internal"},
    )

    assert response.status_code == 200
    item = response.json()["results"][0]
    assert item["identifier"] == IDENTIFIER
    assert item["local_user"] == {"id": linked.pk, "username": linked.username}
    assert not item["can_import"]


def test_directory_search_requires_two_characters(admin: User) -> None:
    client = Client()
    client.force_login(admin)

    response = client.get(
        reverse("accounts-api:directory-user-search"),
        {"q": "m"},
    )

    assert response.status_code == 400
    assert response.json()["code"] == "validation_error"


def test_directory_group_search_api(
    admin: User,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    group = DirectoryGroup(
        distinguished_name="CN=SGPD,OU=Grupos,DC=example,DC=internal",
        name="SGPD",
        account_name="SGPD",
        description="Acesso ao SGPD",
    )
    monkeypatch.setattr(
        ActiveDirectoryClient,
        "search_groups",
        lambda self, query, limit=None: [group],
    )
    client = Client()
    client.force_login(admin)

    response = client.get(
        reverse("accounts-api:directory-group-search"),
        {"q": "sg"},
    )

    assert response.status_code == 200
    assert response.json()["results"][0]["name"] == "SGPD"


def test_directory_create_api_provisions_verified_identity(
    admin: User,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        ActiveDirectoryClient,
        "get_user",
        lambda self, identifier: directory_user(),
    )
    client = Client()
    client.force_login(admin)

    response = client.post(
        reverse("accounts-api:directory-user-create"),
        data={"identifier": IDENTIFIER},
        content_type="application/json",
    )

    assert response.status_code == 201
    assert response.json()["ad_identifier"] == IDENTIFIER
    assert not User.objects.get(pk=response.json()["id"]).has_usable_password()
    assert AccountAuditEvent.objects.filter(
        event_type=AccountEventType.USER_CREATED,
        target_user_id=response.json()["id"],
        reason=DIRECTORY_IMPORT_REASON,
    ).exists()


@pytest.mark.parametrize(
    ("route_name", "method", "route_data", "payload"),
    [
        ("accounts-api:directory-status", "get", {}, {}),
        ("accounts-api:directory-user-search", "get", {}, {"q": "maria"}),
        ("accounts-api:directory-group-search", "get", {}, {"q": "sg"}),
        (
            "accounts-api:directory-user-create",
            "post",
            {},
            {"identifier": IDENTIFIER},
        ),
    ],
)
def test_directory_endpoints_deny_user_without_permission(
    route_name: str,
    method: str,
    route_data: dict[str, int],
    payload: dict[str, str],
) -> None:
    user = User.objects.create_user(
        username="comum",
        email="comum@example.invalid",
        password="Common-test!2026",
    )
    client = Client()
    client.force_login(user)

    url = reverse(route_name, kwargs=route_data)
    response = (
        client.post(url, data=payload, content_type="application/json")
        if method == "post"
        else client.get(url, data=payload)
    )

    assert response.status_code == 403
