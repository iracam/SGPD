"""Contract of the session-based authentication API consumed by the SPA."""

from __future__ import annotations

from typing import Any

import pytest
from django.contrib.auth.models import Permission
from django.core.cache import cache
from django.test import Client
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

PASSWORD = "Api-auth-test!2026"


@pytest.fixture(autouse=True)
def _clear_throttle_cache() -> None:
    # AnonRateThrottle counts through the cache; leaking counters between tests
    # would make unrelated cases fail with 429.
    cache.clear()


@pytest.fixture
def user() -> User:
    return User.objects.create_user(
        username="api.user",
        email="api.user@example.invalid",
        password=PASSWORD,
        first_name="Api",
        last_name="User",
    )


def _csrf_client() -> tuple[Client, str]:
    client = Client(enforce_csrf_checks=True)
    client.get(reverse("auth-api:csrf"))
    return client, client.cookies["csrftoken"].value


def _login(client: Client, token: str, username: str, password: str) -> Any:
    return client.post(
        reverse("auth-api:login"),
        data={"username": username, "password": password},
        content_type="application/json",
        headers={"x-csrftoken": token},
    )


def test_csrf_endpoint_issues_cookie_without_authentication() -> None:
    client = Client()

    response = client.get(reverse("auth-api:csrf"))

    assert response.status_code == 200
    assert "csrftoken" in response.cookies


def test_anonymous_request_receives_401_not_403() -> None:
    # SessionAuthentication publishes no WWW-Authenticate header, so DRF would
    # answer 403. The SPA needs 401 to tell "log in" from "not allowed".
    response = Client().get(reverse("auth-api:me"))

    assert response.status_code == 401
    assert response.json()["code"] == "not_authenticated"


def test_login_succeeds_and_is_audited(user: User) -> None:
    client, token = _csrf_client()

    response = _login(client, token, user.username, PASSWORD)

    body = response.json()
    assert response.status_code == 200
    assert body["username"] == user.username
    assert body["display_name"] == "Api User"
    assert body["must_change_password"] is False
    assert "password" not in body
    assert AccountAuditEvent.objects.filter(
        event_type=AccountEventType.LOGIN,
        actor=user,
    ).exists()


def test_login_with_wrong_password_returns_typed_401_and_is_audited(user: User) -> None:
    client, token = _csrf_client()

    response = _login(client, token, user.username, "senha-incorreta")

    assert response.status_code == 401
    assert response.json()["code"] == "invalid_credentials"
    assert AccountAuditEvent.objects.filter(
        event_type=AccountEventType.LOGIN_FAILED,
        actor__isnull=True,
    ).exists()


def test_login_without_csrf_token_is_rejected(user: User) -> None:
    client = Client(enforce_csrf_checks=True)
    client.get(reverse("auth-api:csrf"))

    response = client.post(
        reverse("auth-api:login"),
        data={"username": user.username, "password": PASSWORD},
        content_type="application/json",
    )

    assert response.status_code == 403
    assert response.json()["code"] == "permission_denied"


def test_inactive_user_cannot_log_in(user: User) -> None:
    user.is_active = False
    user.save(update_fields=("is_active",))
    client, token = _csrf_client()

    response = _login(client, token, user.username, PASSWORD)

    assert response.status_code == 401
    assert response.json()["code"] == "invalid_credentials"


def test_login_is_throttled_after_repeated_attempts(user: User) -> None:
    client, token = _csrf_client()

    statuses = [
        _login(client, token, user.username, "senha-incorreta").status_code for _ in range(11)
    ]

    assert statuses[0] == 401
    assert statuses[-1] == 429


def test_missing_credentials_return_field_details() -> None:
    client, token = _csrf_client()

    response = client.post(
        reverse("auth-api:login"),
        data={"username": "alguem"},
        content_type="application/json",
        headers={"x-csrftoken": token},
    )

    body = response.json()
    assert response.status_code == 400
    assert body["code"] == "validation_error"
    assert "password" in body["details"]


def test_logout_ends_session_and_is_audited(user: User) -> None:
    client = Client()
    client.force_login(user)

    response = client.post(reverse("auth-api:logout"))

    assert response.status_code == 204
    assert AccountAuditEvent.objects.filter(
        event_type=AccountEventType.LOGOUT,
        actor=user,
    ).exists()
    assert Client().get(reverse("auth-api:me")).status_code == 401


def test_me_returns_the_authenticated_user(user: User) -> None:
    client = Client()
    client.force_login(user)

    response = client.get(reverse("auth-api:me"))

    assert response.status_code == 200
    assert response.json()["id"] == user.pk


def test_change_password_clears_the_temporary_flag_and_keeps_session(user: User) -> None:
    user.must_change_password = True
    user.save(update_fields=("must_change_password",))
    client = Client()
    client.force_login(user)

    response = client.post(
        reverse("auth-api:change-password"),
        data={
            "old_password": PASSWORD,
            "new_password": "Nova-senha-api!2026",
            "new_password_confirm": "Nova-senha-api!2026",
        },
        content_type="application/json",
    )

    user.refresh_from_db()
    assert response.status_code == 200
    assert response.json()["must_change_password"] is False
    assert not user.must_change_password
    assert user.check_password("Nova-senha-api!2026")
    # The session survives the hash rotation.
    assert client.get(reverse("auth-api:me")).status_code == 200


def test_change_password_with_wrong_current_password_returns_field_error(user: User) -> None:
    client = Client()
    client.force_login(user)

    response = client.post(
        reverse("auth-api:change-password"),
        data={
            "old_password": "senha-incorreta",
            "new_password": "Nova-senha-api!2026",
            "new_password_confirm": "Nova-senha-api!2026",
        },
        content_type="application/json",
    )

    body = response.json()
    assert response.status_code == 400
    assert body["code"] == "validation_error"
    assert "old_password" in body["details"]


def test_change_password_rejects_mismatched_confirmation(user: User) -> None:
    client = Client()
    client.force_login(user)

    response = client.post(
        reverse("auth-api:change-password"),
        data={
            "old_password": PASSWORD,
            "new_password": "Nova-senha-api!2026",
            "new_password_confirm": "Outra-senha-api!2026",
        },
        content_type="application/json",
    )

    assert response.status_code == 400
    assert "new_password_confirm" in response.json()["details"]


def test_weak_new_password_is_reported_without_changing_it(user: User) -> None:
    client = Client()
    client.force_login(user)

    response = client.post(
        reverse("auth-api:change-password"),
        data={
            "old_password": PASSWORD,
            "new_password": "12345678",
            "new_password_confirm": "12345678",
        },
        content_type="application/json",
    )

    user.refresh_from_db()
    assert response.status_code == 400
    assert response.json()["code"] == "validation_error"
    assert user.check_password(PASSWORD)


def test_temporary_password_blocks_other_api_endpoints(user: User) -> None:
    user.must_change_password = True
    user.save(update_fields=("must_change_password",))
    client = Client()
    client.force_login(user)

    blocked = client.get(reverse("auth-api:context"))
    allowed = client.get(reverse("auth-api:me"))

    assert blocked.status_code == 403
    assert blocked.json()["code"] == "password_change_required"
    assert allowed.status_code == 200


def test_temporary_password_does_not_block_senior_references_after_change(user: User) -> None:
    user.must_change_password = True
    user.save(update_fields=("must_change_password",))
    client = Client()
    client.force_login(user)

    assert client.get(reverse("senior:companies")).status_code == 403

    client.post(
        reverse("auth-api:change-password"),
        data={
            "old_password": PASSWORD,
            "new_password": "Nova-senha-api!2026",
            "new_password_confirm": "Nova-senha-api!2026",
        },
        content_type="application/json",
    )

    # Still 403, but now for lacking the permission rather than the stale password.
    response = client.get(reverse("senior:companies"))
    assert response.status_code == 403
    assert response.json()["code"] != "password_change_required"


def test_context_reports_no_access_for_a_user_without_roles(user: User) -> None:
    client = Client()
    client.force_login(user)

    body = client.get(reverse("auth-api:context")).json()

    assert body["user"]["username"] == user.username
    assert body["roles"] == []
    assert body["scopes"]["assignments"] == []
    assert all(feature["can_view"] is False for feature in body["features"].values())


def test_context_exposes_company_scoped_permission(user: User) -> None:
    role = Role.objects.create(code="DP", name="Departamento Pessoal")
    role.permissions.add(
        Permission.objects.get(
            content_type__app_label="accounts",
            codename="query_senior_references",
        )
    )
    RoleAssignment.objects.create(
        user=user,
        role=role,
        scope_type=ScopeType.COMPANY,
        company_code=7,
        scope_key="COMPANY:7:-",
        valid_from=timezone.now(),
        assigned_by=user,
    )
    client = Client()
    client.force_login(user)

    body = client.get(reverse("auth-api:context")).json()

    assert body["roles"] == ["DP"]
    assert body["features"]["query_senior_references"]["can_view"] is True
    assert body["permissions"]["query_senior_references"]["companies"] == [7]
    assert body["features"]["manage_users"]["can_view"] is False
    assert body["scopes"]["assignments"][0]["company_code"] == 7


def test_context_reports_global_access_for_superuser() -> None:
    admin = User.objects.create_superuser(
        username="api.admin",
        email="api.admin@example.invalid",
        password=PASSWORD,
    )
    client = Client()
    client.force_login(admin)

    body = client.get(reverse("auth-api:context")).json()

    assert body["scopes"]["is_superuser"] is True
    assert all(feature["can_view"] is True for feature in body["features"].values())
    # None means every company, as opposed to an explicit list.
    assert body["permissions"]["manage_users"]["companies"] is None


def test_revoked_assignment_disappears_from_context(user: User) -> None:
    role = Role.objects.create(code="DP", name="Departamento Pessoal")
    role.permissions.add(
        Permission.objects.get(
            content_type__app_label="accounts",
            codename="view_account_audit",
        )
    )
    assignment = RoleAssignment.objects.create(
        user=user,
        role=role,
        scope_type=ScopeType.GLOBAL,
        scope_key="GLOBAL:-:-",
        valid_from=timezone.now(),
        assigned_by=user,
    )
    client = Client()
    client.force_login(user)

    granted = client.get(reverse("auth-api:context")).json()
    # SGPD_CK_ROLE_REVOKE requires the revocation trail alongside is_active.
    assignment.is_active = False
    assignment.revoked_by = user
    assignment.revoked_at = timezone.now()
    assignment.save(update_fields=("is_active", "revoked_by", "revoked_at"))
    revoked = client.get(reverse("auth-api:context")).json()

    assert granted["features"]["view_account_audit"]["can_view"] is True
    assert revoked["features"]["view_account_audit"]["can_view"] is False
    assert revoked["roles"] == []


def test_unknown_endpoint_under_api_returns_envelope(user: User) -> None:
    client = Client()
    client.force_login(user)

    response = client.delete(reverse("auth-api:me"))

    assert response.status_code == 405
    assert response.json()["code"] == "method_not_allowed"
