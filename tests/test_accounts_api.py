"""Contract of the account administration API.

Every endpoint carries a denial case: the API is now the only functional
surface, so authorization can no longer lean on what the interface renders.
"""

from __future__ import annotations

from typing import Any

import pytest
from django.contrib.auth.models import Permission
from django.test import Client, override_settings
from django.urls import reverse
from django.utils import timezone

from apps.accounts.models import (
    AccountAuditEvent,
    AccountEventType,
    Role,
    RoleAssignment,
    ScopeType,
    User,
)

pytestmark = pytest.mark.django_db

PASSWORD = "Accounts-api-test!2026"
TEMPORARY = "Temporaria-api-test!2026"

#: (url name, kwargs, method, minimal valid body) for every protected endpoint.
ENDPOINTS: list[tuple[str, dict[str, Any], str, dict[str, Any]]] = [
    ("accounts-api:user-list", {}, "get", {}),
    ("accounts-api:user-list", {}, "post", {}),
    ("accounts-api:user-detail", {"user_id": 1}, "get", {}),
    ("accounts-api:user-detail", {"user_id": 1}, "patch", {}),
    ("accounts-api:user-reset-password", {"user_id": 1}, "post", {}),
    ("accounts-api:user-assign-role", {"user_id": 1}, "post", {}),
    ("accounts-api:user-ad-link", {"user_id": 1}, "post", {}),
    ("accounts-api:user-ad-unlink", {"user_id": 1}, "post", {}),
    ("accounts-api:role-assignment-revoke", {"assignment_id": 1}, "post", {}),
    ("accounts-api:role-list", {}, "get", {}),
    ("accounts-api:role-list", {}, "post", {}),
    ("accounts-api:role-detail", {"role_id": 1}, "get", {}),
    ("accounts-api:role-detail", {"role_id": 1}, "patch", {}),
    ("accounts-api:permission-list", {}, "get", {}),
    ("accounts-api:audit-list", {}, "get", {}),
]


@pytest.fixture
def admin() -> User:
    return User.objects.create_superuser(
        username="api.admin",
        email="api.admin@example.invalid",
        password=PASSWORD,
        first_name="Api",
        last_name="Admin",
    )


@pytest.fixture
def plain_user() -> User:
    return User.objects.create_user(
        username="api.comum",
        email="api.comum@example.invalid",
        password=PASSWORD,
        first_name="Api",
        last_name="Comum",
    )


@pytest.fixture
def admin_client(admin: User) -> Client:
    client = Client()
    client.force_login(admin)
    return client


def _post(client: Client, name: str, body: dict[str, Any], **kwargs: Any) -> Any:
    return client.post(reverse(name, kwargs=kwargs), data=body, content_type="application/json")


def _patch(client: Client, name: str, body: dict[str, Any], **kwargs: Any) -> Any:
    return client.patch(reverse(name, kwargs=kwargs), data=body, content_type="application/json")


# --------------------------------------------------------------------------
# Authorization
# --------------------------------------------------------------------------


@pytest.mark.parametrize(("name", "kwargs", "method", "body"), ENDPOINTS)
def test_every_endpoint_rejects_anonymous_access(
    name: str,
    kwargs: dict[str, Any],
    method: str,
    body: dict[str, Any],
) -> None:
    client = Client()

    response = getattr(client, method)(
        reverse(name, kwargs=kwargs),
        data=body,
        content_type="application/json",
    )

    assert response.status_code == 401
    assert response.json()["code"] == "not_authenticated"


@pytest.mark.parametrize(("name", "kwargs", "method", "body"), ENDPOINTS)
def test_every_endpoint_rejects_user_without_permission(
    plain_user: User,
    name: str,
    kwargs: dict[str, Any],
    method: str,
    body: dict[str, Any],
) -> None:
    client = Client()
    client.force_login(plain_user)

    response = getattr(client, method)(
        reverse(name, kwargs=kwargs),
        data=body,
        content_type="application/json",
    )

    assert response.status_code == 403
    assert response.json()["code"] == "permission_denied"


def test_denied_request_produces_no_side_effect(plain_user: User) -> None:
    before = AccountAuditEvent.objects.count()
    client = Client()
    client.force_login(plain_user)

    response = _post(
        client,
        "accounts-api:user-list",
        {
            "username": "nao.criado",
            "first_name": "Nao",
            "last_name": "Criado",
            "email": "nao.criado@example.invalid",
            "password": TEMPORARY,
            "password_confirm": TEMPORARY,
            "reason": "Tentativa sem permissão.",
        },
    )

    assert response.status_code == 403
    assert not User.objects.filter(username="nao.criado").exists()
    assert AccountAuditEvent.objects.count() == before


def test_manage_users_does_not_grant_manage_roles(plain_user: User) -> None:
    plain_user.user_permissions.add(
        Permission.objects.get(content_type__app_label="accounts", codename="manage_users")
    )
    client = Client()
    client.force_login(plain_user)

    assert client.get(reverse("accounts-api:user-list")).status_code == 200
    assert client.get(reverse("accounts-api:role-list")).status_code == 403
    assert client.get(reverse("accounts-api:audit-list")).status_code == 403


def test_ad_link_requires_its_own_permission(plain_user: User, admin: User) -> None:
    plain_user.user_permissions.add(
        Permission.objects.get(content_type__app_label="accounts", codename="manage_users")
    )
    client = Client()
    client.force_login(plain_user)

    response = _post(
        client,
        "accounts-api:user-ad-link",
        {
            "version": admin.version,
            "identifier": "S-1-5-21-0001",
            "username": "api.admin",
            "reason": "Sem permissão de vínculo.",
        },
        user_id=admin.pk,
    )

    assert response.status_code == 403
    admin.refresh_from_db()
    assert admin.ad_identifier is None


# --------------------------------------------------------------------------
# Users
# --------------------------------------------------------------------------


def test_create_user_is_audited_and_omits_the_password(admin_client: Client) -> None:
    response = _post(
        admin_client,
        "accounts-api:user-list",
        {
            "username": "novo.api",
            "first_name": "Novo",
            "last_name": "Api",
            "email": "novo.api@example.invalid",
            "password": TEMPORARY,
            "password_confirm": TEMPORARY,
            "must_change_password": True,
            "reason": "Novo responsável de setor.",
        },
    )

    body = response.json()
    created = User.objects.get(username="novo.api")
    assert response.status_code == 201
    assert body["username"] == "novo.api"
    assert "password" not in body
    assert created.must_change_password
    assert AccountAuditEvent.objects.filter(
        event_type=AccountEventType.USER_CREATED,
        target_user=created,
    ).exists()


def test_create_user_rejects_mismatched_confirmation(admin_client: Client) -> None:
    response = _post(
        admin_client,
        "accounts-api:user-list",
        {
            "username": "nao.criado",
            "first_name": "Nao",
            "last_name": "Criado",
            "email": "nao.criado@example.invalid",
            "password": TEMPORARY,
            "password_confirm": "Outra-senha!2026",
            "reason": "Confirmação divergente.",
        },
    )

    assert response.status_code == 400
    assert "password_confirm" in response.json()["details"]
    assert not User.objects.filter(username="nao.criado").exists()


def test_create_user_requires_a_reason(admin_client: Client) -> None:
    response = _post(
        admin_client,
        "accounts-api:user-list",
        {
            "username": "sem.motivo",
            "first_name": "Sem",
            "last_name": "Motivo",
            "email": "sem.motivo@example.invalid",
            "password": TEMPORARY,
            "password_confirm": TEMPORARY,
        },
    )

    assert response.status_code == 400
    assert "reason" in response.json()["details"]


def test_duplicate_email_is_reported_per_field(admin_client: Client, plain_user: User) -> None:
    response = _post(
        admin_client,
        "accounts-api:user-list",
        {
            "username": "outro.login",
            "first_name": "Outro",
            "last_name": "Login",
            "email": plain_user.email,
            "password": TEMPORARY,
            "password_confirm": TEMPORARY,
            "reason": "E-mail já utilizado.",
        },
    )

    assert response.status_code == 400
    assert response.json()["code"] == "validation_error"


def test_user_list_filters_by_query(admin_client: Client, plain_user: User) -> None:
    response = admin_client.get(reverse("accounts-api:user-list"), {"q": "comum"})

    body = response.json()
    assert response.status_code == 200
    assert [item["username"] for item in body["results"]] == [plain_user.username]


def test_user_list_caps_the_page_size(admin_client: Client) -> None:
    response = admin_client.get(reverse("accounts-api:user-list"), {"limit": "5000"})

    assert response.status_code == 200
    assert response.json()["limit"] == 200


def test_user_detail_includes_role_assignments(admin_client: Client, plain_user: User) -> None:
    role = Role.objects.create(code="DP_API", name="DP API")
    RoleAssignment.objects.create(
        user=plain_user,
        role=role,
        scope_type=ScopeType.GLOBAL,
        scope_key="GLOBAL:-:-",
        valid_from=timezone.now(),
        assigned_by=plain_user,
    )

    body = admin_client.get(
        reverse("accounts-api:user-detail", kwargs={"user_id": plain_user.pk})
    ).json()

    assert body["role_assignments"][0]["role"]["code"] == "DP_API"


def test_unknown_user_returns_404(admin_client: Client) -> None:
    response = admin_client.get(reverse("accounts-api:user-detail", kwargs={"user_id": 999999}))

    assert response.status_code == 404
    assert response.json()["code"] == "not_found"


def test_stale_version_rejects_concurrent_update(admin_client: Client, plain_user: User) -> None:
    response = _patch(
        admin_client,
        "accounts-api:user-detail",
        {
            "version": plain_user.version + 5,
            "first_name": "Alterado",
            "last_name": "Comum",
            "email": plain_user.email,
            "is_active": True,
            "reason": "Versão desatualizada.",
        },
        user_id=plain_user.pk,
    )

    plain_user.refresh_from_db()
    assert response.status_code == 400
    assert plain_user.first_name != "Alterado"


def test_update_user_bumps_the_version(admin_client: Client, plain_user: User) -> None:
    response = _patch(
        admin_client,
        "accounts-api:user-detail",
        {
            "version": plain_user.version,
            "first_name": "Renomeado",
            "last_name": "Comum",
            "email": plain_user.email,
            "is_active": True,
            "reason": "Correção de nome.",
        },
        user_id=plain_user.pk,
    )

    body = response.json()
    previous_version = plain_user.version
    plain_user.refresh_from_db()
    assert response.status_code == 200
    assert body["first_name"] == "Renomeado"
    assert plain_user.version > previous_version
    assert body["version"] == plain_user.version


def test_last_active_superuser_cannot_be_deactivated(admin_client: Client, admin: User) -> None:
    response = _patch(
        admin_client,
        "accounts-api:user-detail",
        {
            "version": admin.version,
            "first_name": admin.first_name,
            "last_name": admin.last_name,
            "email": admin.email,
            "is_active": False,
            "reason": "Tentativa de desativar o último superusuário.",
        },
        user_id=admin.pk,
    )

    admin.refresh_from_db()
    assert response.status_code == 400
    assert admin.is_active


def test_reset_password_sets_a_temporary_credential(
    admin_client: Client,
    plain_user: User,
) -> None:
    response = _post(
        admin_client,
        "accounts-api:user-reset-password",
        {
            "password": "Redefinida-api!2026",
            "password_confirm": "Redefinida-api!2026",
            "must_change_password": True,
            "reason": "Usuário perdeu a senha.",
        },
        user_id=plain_user.pk,
    )

    plain_user.refresh_from_db()
    assert response.status_code == 200
    assert plain_user.must_change_password
    assert plain_user.check_password("Redefinida-api!2026")
    assert AccountAuditEvent.objects.filter(
        event_type=AccountEventType.PASSWORD_RESET,
        target_user=plain_user,
    ).exists()


@override_settings(
    LDAP_AUTHENTICATION_ENABLED=True,
    LDAP_LOCAL_SUPERUSER_FALLBACK=True,
)
def test_linked_user_exposes_policy_and_rejects_local_password_reset(
    admin_client: Client,
    admin: User,
    plain_user: User,
) -> None:
    plain_user.ad_identifier = "linked-user-guid"
    plain_user.ad_username = "api.comum.ad"
    plain_user.ad_linked_at = timezone.now()
    plain_user.ad_linked_by = admin
    plain_user.save(
        update_fields=(
            "ad_identifier",
            "ad_username",
            "ad_linked_at",
            "ad_linked_by",
        )
    )

    detail = admin_client.get(
        reverse("accounts-api:user-detail", kwargs={"user_id": plain_user.pk})
    )
    response = _post(
        admin_client,
        "accounts-api:user-reset-password",
        {
            "password": "Must-not-be-saved!2026",
            "password_confirm": "Must-not-be-saved!2026",
            "must_change_password": False,
            "reason": "Tentativa incompatível com a política AD.",
        },
        user_id=plain_user.pk,
    )

    plain_user.refresh_from_db()
    assert detail.status_code == 200
    assert detail.json()["ad_authentication_enabled"]
    assert not detail.json()["local_password_allowed"]
    assert response.status_code == 400
    assert "Active Directory" in response.json()["details"]["password"][0]
    assert plain_user.check_password(PASSWORD)
    assert not AccountAuditEvent.objects.filter(
        event_type=AccountEventType.PASSWORD_RESET,
        target_user=plain_user,
    ).exists()


# --------------------------------------------------------------------------
# Roles and assignments
# --------------------------------------------------------------------------


def test_create_role_with_delegable_permissions(admin_client: Client) -> None:
    permission = Permission.objects.get(
        content_type__app_label="accounts",
        codename="view_account_audit",
    )

    response = _post(
        admin_client,
        "accounts-api:role-list",
        {
            "code": "auditor_api",
            "name": "Auditor API",
            "description": "Somente leitura da auditoria.",
            "permission_ids": [permission.pk],
            "reason": "Novo papel de auditoria.",
        },
    )

    body = response.json()
    assert response.status_code == 201
    assert body["code"] == "AUDITOR_API"
    assert [item["codename"] for item in body["permissions"]] == ["view_account_audit"]


def test_non_delegable_permission_is_rejected(admin_client: Client) -> None:
    permission = Permission.objects.filter(content_type__app_label="auth").first()
    assert permission is not None

    response = _post(
        admin_client,
        "accounts-api:role-list",
        {
            "code": "papel_invalido",
            "name": "Papel inválido",
            "permission_ids": [permission.pk],
            "reason": "Permissão fora do catálogo.",
        },
    )

    assert response.status_code == 400
    assert not Role.objects.filter(code="PAPEL_INVALIDO").exists()


def test_permission_catalog_lists_only_delegable_entries(admin_client: Client) -> None:
    body = admin_client.get(reverse("accounts-api:permission-list")).json()

    assert {item["codename"] for item in body["results"]} == {
        "manage_users",
        "manage_roles",
        "link_ad_identity",
        "view_account_audit",
        "query_senior_references",
    }


def test_assign_role_with_company_scope(admin_client: Client, plain_user: User) -> None:
    role = Role.objects.create(code="DP_ESCOPO", name="DP com escopo")

    response = _post(
        admin_client,
        "accounts-api:user-assign-role",
        {
            "role_id": role.pk,
            "scope_type": ScopeType.COMPANY.value,
            "company_code": 7,
            "reason": "Responsável pela empresa 7.",
        },
        user_id=plain_user.pk,
    )

    body = response.json()
    assert response.status_code == 201
    assert body["company_code"] == 7
    assert body["is_active"] is True
    assert AccountAuditEvent.objects.filter(event_type=AccountEventType.ROLE_ASSIGNED).exists()


@pytest.mark.parametrize(
    ("scope_type", "company_code", "branch_code", "field"),
    [
        (ScopeType.GLOBAL.value, 7, None, "scope_type"),
        (ScopeType.COMPANY.value, None, None, "company_code"),
        (ScopeType.BRANCH.value, 7, None, "branch_code"),
    ],
)
def test_inconsistent_scope_is_rejected_per_field(
    admin_client: Client,
    plain_user: User,
    scope_type: str,
    company_code: int | None,
    branch_code: int | None,
    field: str,
) -> None:
    role = Role.objects.create(code="DP_ESCOPO_INVALIDO", name="Escopo inválido")

    response = _post(
        admin_client,
        "accounts-api:user-assign-role",
        {
            "role_id": role.pk,
            "scope_type": scope_type,
            "company_code": company_code,
            "branch_code": branch_code,
            "reason": "Escopo inconsistente.",
        },
        user_id=plain_user.pk,
    )

    assert response.status_code == 400
    assert field in response.json()["details"]
    assert not RoleAssignment.objects.exists()


def test_revoke_role_keeps_the_trail(admin_client: Client, plain_user: User, admin: User) -> None:
    role = Role.objects.create(code="DP_REVOGAR", name="DP a revogar")
    assignment = RoleAssignment.objects.create(
        user=plain_user,
        role=role,
        scope_type=ScopeType.GLOBAL,
        scope_key="GLOBAL:-:-",
        valid_from=timezone.now(),
        assigned_by=admin,
    )

    response = _post(
        admin_client,
        "accounts-api:role-assignment-revoke",
        {"reason": "Mudança de setor."},
        assignment_id=assignment.pk,
    )

    body = response.json()
    assignment.refresh_from_db()
    assert response.status_code == 200
    assert body["is_active"] is False
    assert body["revoked_by"] == admin.username
    assert assignment.revoked_at is not None


def test_role_cannot_be_assigned_to_an_inactive_user(
    admin_client: Client,
    plain_user: User,
) -> None:
    plain_user.is_active = False
    plain_user.save(update_fields=("is_active",))
    role = Role.objects.create(code="DP_INATIVO", name="DP inativo")

    response = _post(
        admin_client,
        "accounts-api:user-assign-role",
        {
            "role_id": role.pk,
            "scope_type": ScopeType.GLOBAL.value,
            "reason": "Usuário inativo.",
        },
        user_id=plain_user.pk,
    )

    assert response.status_code == 400
    assert not RoleAssignment.objects.exists()


# --------------------------------------------------------------------------
# AD link
# --------------------------------------------------------------------------


def test_ad_link_and_unlink_are_audited(admin_client: Client, plain_user: User) -> None:
    linked = _post(
        admin_client,
        "accounts-api:user-ad-link",
        {
            "version": plain_user.version,
            "identifier": "S-1-5-21-1234",
            "username": "api.comum",
            "reason": "Identidade confirmada pela Infraestrutura.",
        },
        user_id=plain_user.pk,
    )
    plain_user.refresh_from_db()

    unlinked = _post(
        admin_client,
        "accounts-api:user-ad-unlink",
        {"version": plain_user.version, "reason": "Conta corporativa encerrada."},
        user_id=plain_user.pk,
    )
    plain_user.refresh_from_db()

    assert linked.status_code == 200
    assert linked.json()["ad_username"] == "api.comum"
    assert unlinked.status_code == 200
    assert plain_user.ad_identifier is None
    assert AccountAuditEvent.objects.filter(event_type=AccountEventType.AD_LINKED).exists()
    assert AccountAuditEvent.objects.filter(event_type=AccountEventType.AD_UNLINKED).exists()


def test_ad_identifier_cannot_be_shared_by_two_accounts(
    admin_client: Client,
    plain_user: User,
    admin: User,
) -> None:
    _post(
        admin_client,
        "accounts-api:user-ad-link",
        {
            "version": plain_user.version,
            "identifier": "S-1-5-21-9999",
            "username": "api.comum",
            "reason": "Primeiro vínculo.",
        },
        user_id=plain_user.pk,
    )

    response = _post(
        admin_client,
        "accounts-api:user-ad-link",
        {
            "version": admin.version,
            "identifier": "S-1-5-21-9999",
            "username": "api.admin",
            "reason": "Vínculo duplicado.",
        },
        user_id=admin.pk,
    )

    admin.refresh_from_db()
    assert response.status_code == 400
    assert admin.ad_identifier is None


# --------------------------------------------------------------------------
# Audit
# --------------------------------------------------------------------------


def test_audit_is_readable_and_filterable(admin_client: Client, plain_user: User) -> None:
    _post(
        admin_client,
        "accounts-api:user-reset-password",
        {
            "password": "Auditada-api!2026",
            "password_confirm": "Auditada-api!2026",
            "reason": "Gerar evento de auditoria.",
        },
        user_id=plain_user.pk,
    )

    body = admin_client.get(
        reverse("accounts-api:audit-list"),
        {
            "target_user": str(plain_user.pk),
            "event_type": AccountEventType.PASSWORD_RESET.value,
        },
    ).json()

    assert len(body["results"]) == 1
    event = body["results"][0]
    assert event["target_user"] == plain_user.username
    assert event["event_type"] == AccountEventType.PASSWORD_RESET.value
    assert event["reason"] == "Gerar evento de auditoria."


def test_audit_endpoint_is_read_only(admin_client: Client) -> None:
    response = admin_client.post(
        reverse("accounts-api:audit-list"),
        data={},
        content_type="application/json",
    )

    assert response.status_code == 405
    assert response.json()["code"] == "method_not_allowed"
