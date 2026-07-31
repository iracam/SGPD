"""Casos de uso de configuração de e-mail, exclusivos de SuperAdmin (ADR-050).

Módulo separado do LDAP porque são dois módulos da central, não um só: o que
compartilham — autoridade, cifra do segredo, versão otimista e auditoria — vem
de `services.py` e de `crypto.py`.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from django.core.exceptions import ValidationError
from django.core.mail import EmailMessage, get_connection
from django.db import transaction
from django.utils import timezone

from apps.accounts.models import AccountAuditEvent, User
from apps.notifications.config import EmailConfig
from config.middleware import correlation_id

from .crypto import decrypt_secret, encrypt_secret
from .exceptions import ConfigurationSecretError
from .models import EMAIL_CONFIGURATION_KEY, EmailConfiguration
from .services import require_superadmin

EMAIL_CONFIG_UPDATED = "EMAIL_CONFIG_UPDATED"
EMAIL_TEST_SENT = "EMAIL_TEST_SENT"
EMAIL_CONFIG_UPDATE_REASON = "Atualização da configuração de e-mail pela central de configurações."
EMAIL_TEST_REASON = "Envio de mensagem de prova pela central de configurações."

TEST_SUBJECT = "SGPD / DesligaFlow — mensagem de prova"
TEST_BODY = (
    "Esta é uma mensagem de prova do SGPD / DesligaFlow.\n\n"
    "Se você a recebeu, o transporte SMTP configurado na central está entregando.\n"
    "Nenhum dado de processo é enviado nesta mensagem.\n"
)

#: Campos comparados para descobrir o que mudou. A senha é tratada à parte:
#: ela nunca entra na trilha, nem como valor nem como ciphertext.
COMPARED_FIELDS: tuple[str, ...] = (
    "enabled",
    "host",
    "port",
    "use_tls",
    "username",
    "timeout_seconds",
    "default_from_email",
    "base_url",
    "max_attempts",
    "batch_size",
    "stale_minutes",
    "task_due_soon_hours",
    "task_due_imminent_hours",
    "task_critical_hours",
    "process_due_soon_hours",
)


@dataclass(frozen=True, slots=True)
class EmailConfigurationCommand:
    actor: User
    expected_version: int
    enabled: bool
    host: str
    port: int
    use_tls: bool
    username: str
    password: str
    timeout_seconds: int
    default_from_email: str
    base_url: str
    max_attempts: int
    batch_size: int
    stale_minutes: int
    task_due_soon_hours: int
    task_due_imminent_hours: int
    task_critical_hours: int
    process_due_soon_hours: int


@dataclass(frozen=True, slots=True)
class EmailTestResult:
    recipient: str
    tested_at: datetime


def current_persisted_email_configuration() -> EmailConfiguration | None:
    try:
        return EmailConfiguration.objects.get(pk=EMAIL_CONFIGURATION_KEY)
    except EmailConfiguration.DoesNotExist:
        return None


def _record_event(*, event_type: str, actor: User, changes: dict[str, object], reason: str) -> None:
    AccountAuditEvent.objects.create(
        event_type=event_type,
        actor=actor,
        target_user=None,
        entity_type="EMAIL_CONFIGURATION",
        entity_id=EMAIL_CONFIGURATION_KEY,
        reason=reason,
        changes=changes,
        correlation_id=correlation_id.get(),
    )


def _current_secret(record: EmailConfiguration | None) -> str:
    if record is not None and record.password_ciphertext:
        return decrypt_secret(record.password_ciphertext)
    return EmailConfig.from_environment().password


def _candidate(
    command: EmailConfigurationCommand, record: EmailConfiguration | None
) -> EmailConfig:
    environment = EmailConfig.from_environment()
    return EmailConfig(
        enabled=command.enabled,
        host=command.host.strip(),
        port=command.port,
        use_tls=command.use_tls,
        username=command.username.strip(),
        # Campo em branco preserva o segredo vigente: a SPA nunca recebe a senha
        # de volta e não teria como reenviá-la.
        password=command.password or _current_secret(record),
        timeout_seconds=command.timeout_seconds,
        default_from_email=command.default_from_email.strip(),
        base_url=command.base_url.strip().rstrip("/"),
        max_attempts=command.max_attempts,
        batch_size=command.batch_size,
        stale_minutes=command.stale_minutes,
        task_due_soon_hours=command.task_due_soon_hours,
        task_due_imminent_hours=command.task_due_imminent_hours,
        task_critical_hours=command.task_critical_hours,
        process_due_soon_hours=command.process_due_soon_hours,
        source="candidate",
        version=command.expected_version,
        storage_errors=environment.storage_errors,
    )


class ValidateEmailConfigurationService:
    def execute(self, command: EmailConfigurationCommand) -> tuple[list[str], list[str]]:
        require_superadmin(command.actor)
        record = current_persisted_email_configuration()
        try:
            candidate = _candidate(command, record)
        except ConfigurationSecretError as exc:
            return [str(exc)], []
        return candidate.validation_errors(), candidate.warnings()


class UpdateEmailConfigurationService:
    @transaction.atomic
    def execute(self, command: EmailConfigurationCommand) -> EmailConfiguration:
        require_superadmin(command.actor)

        record: EmailConfiguration | None = None
        try:
            persisted = EmailConfiguration.objects.select_for_update().get(
                pk=EMAIL_CONFIGURATION_KEY
            )
        except EmailConfiguration.DoesNotExist:
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

        values = {
            "enabled": candidate.enabled,
            "host": candidate.host,
            "port": candidate.port,
            "use_tls": candidate.use_tls,
            "username": candidate.username,
            "timeout_seconds": candidate.timeout_seconds,
            "default_from_email": candidate.default_from_email,
            "base_url": candidate.base_url,
            "max_attempts": candidate.max_attempts,
            "batch_size": candidate.batch_size,
            "stale_minutes": candidate.stale_minutes,
            "task_due_soon_hours": candidate.task_due_soon_hours,
            "task_due_imminent_hours": candidate.task_due_imminent_hours,
            "task_critical_hours": candidate.task_critical_hours,
            "process_due_soon_hours": candidate.process_due_soon_hours,
        }
        if record is None:
            previous_version = 0
            record = EmailConfiguration(key=EMAIL_CONFIGURATION_KEY, updated_by=command.actor)
            changed_fields: list[str] = list(COMPARED_FIELDS)
        else:
            previous_version = record.version
            changed_fields = [
                field for field in COMPARED_FIELDS if getattr(record, field) != values[field]
            ]
        if command.password:
            changed_fields.append("password")

        for field, value in values.items():
            setattr(record, field, value)
        if command.password:
            record.password_ciphertext = encrypt_secret(command.password)
        record.updated_by = command.actor
        record.version = previous_version + 1
        record.full_clean()
        record.save()
        _record_event(
            event_type=EMAIL_CONFIG_UPDATED,
            actor=command.actor,
            reason=EMAIL_CONFIG_UPDATE_REASON,
            changes={
                # Servidor, porta e remetente entram na trilha porque redirecionar
                # o e-mail do sistema é ato relevante; a senha nunca entra.
                "changed_fields": sorted(set(changed_fields)),
                "enabled": record.enabled,
                "host": record.host,
                "port": record.port,
                "use_tls": record.use_tls,
                "default_from_email": record.default_from_email,
                "version_before": previous_version,
                "version_after": record.version,
            },
        )
        return record


class SendTestEmailService:
    """Envia uma mensagem de prova ao próprio SuperAdmin que pediu o teste.

    O destinatário não é escolhido pelo request: a central não é ferramenta de
    envio de mensagem para terceiros.
    """

    def execute(self, actor: User) -> EmailTestResult:
        require_superadmin(actor)
        recipient = (actor.email or "").strip()
        if not recipient:
            raise ValidationError(
                {"recipient": "Cadastre um e-mail na sua conta para receber a prova."}
            )
        config = EmailConfig.from_settings()
        errors = config.validation_errors()
        if errors:
            raise ValidationError({"non_field_errors": errors})
        if not config.enabled:
            raise ValidationError(
                {"enabled": "Habilite o envio antes de testar o transporte SMTP."}
            )

        tested_at = timezone.now()
        error = ""
        try:
            # Sem fixar o backend: quem decide o transporte é `EMAIL_BACKEND`,
            # que em produção é o backend dinâmico e nos testes é o de memória.
            # Fixar o SMTP aqui faria a suíte abrir conexão viva com o servidor
            # real gravado na central.
            connection = get_connection(
                host=config.host,
                port=config.port,
                username=config.username or None,
                password=config.password or None,
                use_tls=config.use_tls,
                timeout=config.timeout_seconds,
                fail_silently=False,
            )
            EmailMessage(
                subject=TEST_SUBJECT,
                body=TEST_BODY,
                from_email=config.default_from_email,
                to=[recipient],
                connection=connection,
            ).send(fail_silently=False)
        except Exception as failure:
            error = f"{type(failure).__name__}: {failure}"[:1000]

        self._record_probe(
            actor=actor,
            recipient=recipient,
            tested_at=tested_at,
            error=error,
        )
        if error:
            raise ValidationError({"non_field_errors": [error]})
        return EmailTestResult(recipient=recipient, tested_at=tested_at)

    @transaction.atomic
    def _record_probe(
        self,
        *,
        actor: User,
        recipient: str,
        tested_at: datetime,
        error: str,
    ) -> None:
        record = current_persisted_email_configuration()
        if record is not None:
            locked = EmailConfiguration.objects.select_for_update().get(pk=EMAIL_CONFIGURATION_KEY)
            locked.last_tested_at = tested_at
            locked.last_test_success = not error
            locked.last_test_recipient = recipient
            locked.last_test_error = error
            locked.last_tested_by = actor
            locked.save(
                update_fields=(
                    "last_tested_at",
                    "last_test_success",
                    "last_test_recipient",
                    "last_test_error",
                    "last_tested_by",
                    "updated_at",
                )
            )
        _record_event(
            event_type=EMAIL_TEST_SENT,
            actor=actor,
            reason=EMAIL_TEST_REASON,
            changes={
                "recipient": recipient,
                "success": not error,
                "error": error,
            },
        )
