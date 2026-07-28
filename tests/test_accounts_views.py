import pytest
from django.core.management import call_command
from django.test import Client
from django.urls import reverse

from apps.accounts.models import AccountAuditEvent, AccountEventType, Role, User

pytestmark = pytest.mark.django_db


@pytest.fixture
def admin() -> User:
    return User.objects.create_superuser(
        username="admin.web",
        email="admin.web@example.invalid",
        password="Admin-web-test!2026",
    )


def test_user_list_requires_login() -> None:
    response = Client().get(reverse("accounts:user-list"))

    assert response.status_code == 302
    assert reverse("accounts:login") in response["Location"]


def test_user_without_permission_receives_403() -> None:
    user = User.objects.create_user(
        username="sem.permissao",
        email="sem.permissao@example.invalid",
        password="No-permission-test!2026",
    )
    client = Client()
    client.force_login(user)

    response = client.get(reverse("accounts:user-list"))

    assert response.status_code == 403


def test_admin_creates_user_through_audited_view(admin: User) -> None:
    client = Client()
    client.force_login(admin)

    response = client.post(
        reverse("accounts:user-create"),
        {
            "username": "novo.web",
            "first_name": "Novo",
            "last_name": "Web",
            "email": "novo.web@example.invalid",
            "password1": "Temporary-web-test!2026",
            "password2": "Temporary-web-test!2026",
            "must_change_password": "on",
            "reason": "Novo responsável de setor.",
        },
    )

    created = User.objects.get(username="novo.web")
    assert response.status_code == 302
    assert response["Location"] == reverse("accounts:user-detail", args=(created.pk,))
    assert created.must_change_password
    assert AccountAuditEvent.objects.filter(target_user=created).exists()


def test_temporary_password_forces_change_before_other_pages() -> None:
    user = User.objects.create_user(
        username="senha.temporaria",
        email="senha.temporaria@example.invalid",
        password="Temporary-login-test!2026",
        must_change_password=True,
    )
    client = Client()
    client.force_login(user)

    response = client.get(reverse("accounts:home"))

    assert response.status_code == 302
    assert response["Location"] == reverse("accounts:change-own-password")


def test_login_failure_success_and_logout_are_audited() -> None:
    user = User.objects.create_user(
        username="auditoria.login",
        email="auditoria.login@example.invalid",
        password="Login-audit-test!2026",
    )
    client = Client()

    failed = client.post(
        reverse("accounts:login"),
        {"username": user.username, "password": "senha-incorreta"},
    )
    succeeded = client.post(
        reverse("accounts:login"),
        {"username": user.username, "password": "Login-audit-test!2026"},
    )
    logged_out = client.post(reverse("accounts:logout"))

    assert failed.status_code == 200
    assert succeeded.status_code == 302
    assert logged_out.status_code == 302
    assert AccountAuditEvent.objects.filter(
        event_type=AccountEventType.LOGIN_FAILED,
        actor__isnull=True,
    ).exists()
    assert AccountAuditEvent.objects.filter(
        event_type=AccountEventType.LOGIN,
        actor=user,
    ).exists()
    assert AccountAuditEvent.objects.filter(
        event_type=AccountEventType.LOGOUT,
        actor=user,
    ).exists()


def test_bootstrap_roles_is_idempotent() -> None:
    call_command("bootstrap_roles")
    initial_roles = Role.objects.count()
    initial_events = AccountAuditEvent.objects.count()

    call_command("bootstrap_roles")

    assert initial_roles == 9
    assert Role.objects.count() == initial_roles
    assert AccountAuditEvent.objects.count() == initial_events
    assert (
        Role.objects.get(code="DP").permissions.filter(codename="query_senior_references").exists()
    )
