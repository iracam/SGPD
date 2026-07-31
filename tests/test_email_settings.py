"""Central de configuração de e-mail e notificações (ADR-050)."""

# ruff: noqa: F811

from __future__ import annotations

import json
from typing import Any
from unittest import mock

import pytest
from django.core import mail
from django.core.exceptions import PermissionDenied, ValidationError
from django.test import Client
from django.urls import reverse

from apps.accounts.models import AccountAuditEvent, User
from apps.notifications.config import EmailConfig
from apps.notifications.mail import ConfiguredEmailBackend
from apps.notifications.models import Notification, NotificationStatus
from apps.notifications.services import (
    DispatchNotificationsCommand,
    DispatchNotificationsService,
)
from apps.system_settings.crypto import decrypt_secret
from apps.system_settings.email_services import (
    EMAIL_CONFIG_UPDATED,
    EMAIL_TEST_SENT,
    EmailConfigurationCommand,
    SendTestEmailService,
    UpdateEmailConfigurationService,
    ValidateEmailConfigurationService,
)
from apps.system_settings.models import EMAIL_CONFIGURATION_KEY, EmailConfiguration
from tests.test_offboarding_start import actor, process  # noqa: F401

pytestmark = pytest.mark.django_db

PASSWORD = "Central-Email!2026"


@pytest.fixture
def admin() -> User:
    return User.objects.create_superuser(
        username="super.email",
        email="super.email@example.invalid",
        password=PASSWORD,
    )


@pytest.fixture
def ordinary() -> User:
    return User.objects.create_user(
        username="comum.email",
        email="comum.email@example.invalid",
        password=PASSWORD,
    )


def command(actor: User, **overrides: Any) -> EmailConfigurationCommand:
    values: dict[str, Any] = {
        "actor": actor,
        "expected_version": 0,
        "enabled": True,
        "host": "smtp.office365.com",
        "port": 587,
        "use_tls": True,
        "username": "noreply@example.invalid",
        "password": "segredo-smtp",
        "timeout_seconds": 10,
        "default_from_email": "noreply@example.invalid",
        "base_url": "https://sgpd.example.invalid",
        "max_attempts": 5,
        "batch_size": 50,
        "stale_minutes": 15,
        "task_due_soon_hours": 48,
        "task_due_imminent_hours": 24,
        "task_critical_hours": 48,
        "process_due_soon_hours": 72,
    }
    values.update(overrides)
    return EmailConfigurationCommand(**values)


def logged(user: User) -> Client:
    client = Client()
    client.force_login(user)
    return client


def test_saved_configuration_replaces_the_environment_baseline(admin: User) -> None:
    UpdateEmailConfigurationService().execute(command(admin))

    config = EmailConfig.from_settings()

    assert config.source == "database"
    assert config.host == "smtp.office365.com"
    assert config.base_url == "https://sgpd.example.invalid"
    assert config.password == "segredo-smtp"
    assert EmailConfig.from_environment().host == "smtp.invalid"


def test_the_secret_is_encrypted_and_survives_a_save_without_password(admin: User) -> None:
    record = UpdateEmailConfigurationService().execute(command(admin))
    assert record.password_ciphertext
    assert "segredo-smtp" not in record.password_ciphertext
    assert decrypt_secret(record.password_ciphertext) == "segredo-smtp"

    UpdateEmailConfigurationService().execute(
        command(admin, expected_version=record.version, password="", host="smtp.novo.invalid")
    )

    config = EmailConfig.from_settings()
    assert config.host == "smtp.novo.invalid"
    assert config.password == "segredo-smtp"


def test_the_trail_records_the_change_without_the_secret(admin: User) -> None:
    UpdateEmailConfigurationService().execute(command(admin))

    event = AccountAuditEvent.objects.get(event_type=EMAIL_CONFIG_UPDATED)
    assert event.entity_id == EMAIL_CONFIGURATION_KEY
    assert event.changes["host"] == "smtp.office365.com"
    assert "password" in event.changes["changed_fields"]
    assert "segredo-smtp" not in json.dumps(event.changes)


def test_only_superadmin_administers_the_central(admin: User, ordinary: User) -> None:
    with pytest.raises(PermissionDenied):
        UpdateEmailConfigurationService().execute(command(ordinary))

    response = logged(ordinary).get(reverse("system-settings-api:email-configuration"))
    assert response.status_code == 403

    assert logged(admin).get(reverse("system-settings-api:email-configuration")).status_code == 200


def test_a_stale_version_loses_the_race(admin: User) -> None:
    record = UpdateEmailConfigurationService().execute(command(admin))

    with pytest.raises(ValidationError) as stale:
        UpdateEmailConfigurationService().execute(
            command(admin, expected_version=record.version - 1)
        )

    assert "outra sessão" in str(stale.value)


def test_enabling_without_server_or_sender_is_refused(admin: User) -> None:
    with pytest.raises(ValidationError):
        UpdateEmailConfigurationService().execute(command(admin, host=""))
    with pytest.raises(ValidationError):
        UpdateEmailConfigurationService().execute(command(admin, default_from_email=""))


def test_validation_separates_what_blocks_from_what_only_warns(admin: User) -> None:
    errors, warnings = ValidateEmailConfigurationService().execute(
        command(admin, base_url="", use_tls=False, port=9999)
    )

    assert errors == []
    assert any("URL base" in warning for warning in warnings)
    assert any("sem criptografia" in warning for warning in warnings)
    assert any("submissão usual" in warning for warning in warnings)

    blocked, _ = ValidateEmailConfigurationService().execute(
        command(admin, base_url="sgpd.example.invalid")
    )
    assert any("http://" in error for error in blocked)


def test_the_api_never_returns_the_password(admin: User) -> None:
    client = logged(admin)
    payload = {**_api_payload(), "version": 0}

    saved = client.put(
        reverse("system-settings-api:email-configuration"),
        data=json.dumps(payload),
        content_type="application/json",
    )

    assert saved.status_code == 200
    body = saved.json()
    assert body["password_configured"] is True
    assert "password" not in body
    assert "segredo-smtp" not in json.dumps(body)
    assert body["source"] == "database"
    assert body["version"] == 1


def _api_payload(**overrides: Any) -> dict[str, Any]:
    values: dict[str, Any] = {
        "enabled": True,
        "host": "smtp.office365.com",
        "port": 587,
        "use_tls": True,
        "username": "noreply@example.invalid",
        "password": "segredo-smtp",
        "timeout_seconds": 10,
        "default_from_email": "noreply@example.invalid",
        "base_url": "https://sgpd.example.invalid",
        "max_attempts": 5,
        "batch_size": 50,
        "stale_minutes": 15,
        "task_due_soon_hours": 48,
        "task_due_imminent_hours": 24,
        "task_critical_hours": 48,
        "process_due_soon_hours": 72,
    }
    values.update(overrides)
    return values


def test_the_final_reminder_cannot_be_farther_from_the_deadline_than_the_first(
    admin: User,
) -> None:
    response = logged(admin).put(
        reverse("system-settings-api:email-configuration"),
        data=json.dumps({**_api_payload(task_due_imminent_hours=72), "version": 0}),
        content_type="application/json",
    )

    assert response.status_code == 400
    assert "task_due_imminent_hours" in response.json()["details"]


def test_the_proof_message_goes_to_the_superadmin_and_records_the_probe(admin: User) -> None:
    UpdateEmailConfigurationService().execute(command(admin))

    result = SendTestEmailService().execute(admin)

    assert result.recipient == admin.email
    assert len(mail.outbox) == 1
    assert mail.outbox[0].to == [admin.email]
    assert "prova" in mail.outbox[0].subject

    record = EmailConfiguration.objects.get(pk=EMAIL_CONFIGURATION_KEY)
    assert record.last_test_success is True
    assert record.last_test_recipient == admin.email
    assert record.last_tested_by == admin
    assert AccountAuditEvent.objects.filter(event_type=EMAIL_TEST_SENT).count() == 1


def test_a_refused_proof_is_recorded_as_failure_and_surfaces_the_reason(admin: User) -> None:
    UpdateEmailConfigurationService().execute(command(admin))

    with (
        mock.patch(
            "django.core.mail.EmailMessage.send",
            side_effect=OSError("connection refused"),
        ),
        pytest.raises(ValidationError) as refused,
    ):
        SendTestEmailService().execute(admin)

    assert "connection refused" in str(refused.value)
    record = EmailConfiguration.objects.get(pk=EMAIL_CONFIGURATION_KEY)
    assert record.last_test_success is False
    assert "connection refused" in record.last_test_error


def test_disabled_delivery_holds_the_queue_without_losing_anything(
    admin: User,
    actor: User,
    process: Any,
) -> None:
    from tests.test_notifications import enqueue
    from tests.test_offboarding_tasks import started_task

    task = started_task(actor, process)
    enqueue(task, (actor,))
    UpdateEmailConfigurationService().execute(command(admin, enabled=False))

    result = DispatchNotificationsService().execute(DispatchNotificationsCommand())

    assert result.disabled is True and result.sent == 0
    assert mail.outbox == []
    assert set(Notification.objects.values_list("status", flat=True)) == {
        NotificationStatus.PENDING
    }

    record = EmailConfiguration.objects.get(pk=EMAIL_CONFIGURATION_KEY)
    UpdateEmailConfigurationService().execute(
        command(admin, expected_version=record.version, enabled=True, password="")
    )

    assert DispatchNotificationsService().execute(DispatchNotificationsCommand()).sent == 2


def test_the_backend_builds_the_connection_from_the_saved_configuration(admin: User) -> None:
    UpdateEmailConfigurationService().execute(
        command(admin, host="smtp.central.invalid", port=2525, use_tls=False, timeout_seconds=7)
    )

    backend = ConfiguredEmailBackend()

    assert backend.host == "smtp.central.invalid"
    assert backend.port == 2525
    assert backend.use_tls is False
    assert backend.timeout == 7
    assert backend.username == "noreply@example.invalid"
    assert backend.password == "segredo-smtp"

    # Quem passa parâmetro explícito continua vencendo — é como a prova da
    # central testa valores candidatos.
    explicit = ConfiguredEmailBackend(host="smtp.outro.invalid")
    assert explicit.host == "smtp.outro.invalid"
