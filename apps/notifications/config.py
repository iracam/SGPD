"""Configuração efetiva de e-mail e notificações.

Mesmo desenho da configuração LDAP (ADR-031): o `.env` é apenas o baseline do
primeiro boot; assim que o singleton existir, todo consumidor passa a ler o
banco. Nenhuma mutação de settings global e nenhum reinício — o backend de
e-mail é montado por envio.
"""

from __future__ import annotations

from dataclasses import dataclass

from django.apps import apps
from django.conf import settings
from django.core.exceptions import AppRegistryNotReady
from django.db import DatabaseError

#: Portas de submissão conhecidas; fora delas o administrador recebe aviso, não
#: recusa — pode existir relay interno em porta própria.
SUBMISSION_PORTS = (25, 465, 587, 2525)


def _int(name: str, default: int) -> int:
    try:
        return int(getattr(settings, name, default))
    except (TypeError, ValueError):
        return default


@dataclass(frozen=True, slots=True)
class EmailConfig:
    """Transporte SMTP, identidade do remetente e ritmo da fila."""

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
    source: str = "environment"
    version: int = 0
    storage_errors: tuple[str, ...] = ()

    @classmethod
    def from_environment(cls) -> EmailConfig:
        host = str(getattr(settings, "EMAIL_HOST", "")).strip()
        return cls(
            # Sem central preenchida, o envio só liga quando o `.env` traz
            # servidor e remetente: silêncio é melhor que erro a cada despacho.
            enabled=bool(host and str(getattr(settings, "DEFAULT_FROM_EMAIL", "")).strip()),
            host=host,
            port=_int("EMAIL_PORT", 587),
            use_tls=bool(getattr(settings, "EMAIL_USE_TLS", True)),
            username=str(getattr(settings, "EMAIL_HOST_USER", "")).strip(),
            password=str(getattr(settings, "EMAIL_HOST_PASSWORD", "")),
            timeout_seconds=_int("EMAIL_TIMEOUT_SECONDS", 10),
            default_from_email=str(getattr(settings, "DEFAULT_FROM_EMAIL", "")).strip(),
            base_url=str(getattr(settings, "SGPD_BASE_URL", "")).strip().rstrip("/"),
            max_attempts=_int("NOTIFICATION_MAX_ATTEMPTS", 5),
            batch_size=_int("NOTIFICATION_BATCH_SIZE", 50),
            stale_minutes=_int("NOTIFICATION_STALE_MINUTES", 15),
            task_due_soon_hours=_int("NOTIFICATION_TASK_DUE_SOON_HOURS", 48),
            task_due_imminent_hours=_int("NOTIFICATION_TASK_DUE_IMMINENT_HOURS", 24),
            task_critical_hours=_int("NOTIFICATION_TASK_CRITICAL_HOURS", 48),
            process_due_soon_hours=_int("NOTIFICATION_PROCESS_DUE_SOON_HOURS", 72),
        )

    @classmethod
    def from_settings(cls) -> EmailConfig:
        """Lê o singleton persistido, com o ambiente como baseline.

        A tolerância a banco ausente mantém migrations e primeiro boot
        operacionais antes de a tabela existir.
        """

        environment = cls.from_environment()
        if not apps.ready:
            return environment
        try:
            from apps.system_settings.crypto import decrypt_secret
            from apps.system_settings.exceptions import ConfigurationSecretError
            from apps.system_settings.models import (
                EMAIL_CONFIGURATION_KEY,
                EmailConfiguration,
            )

            persisted = EmailConfiguration.objects.get(pk=EMAIL_CONFIGURATION_KEY)
        except (AppRegistryNotReady, DatabaseError):
            return environment
        except EmailConfiguration.DoesNotExist:
            return environment

        storage_errors: list[str] = []
        try:
            password = (
                decrypt_secret(persisted.password_ciphertext)
                if persisted.password_ciphertext
                else environment.password
            )
        except ConfigurationSecretError as exc:
            password = ""
            storage_errors.append(str(exc))

        return cls(
            enabled=persisted.enabled,
            host=persisted.host.strip(),
            port=persisted.port,
            use_tls=persisted.use_tls,
            username=persisted.username.strip(),
            password=password,
            timeout_seconds=persisted.timeout_seconds,
            default_from_email=persisted.default_from_email.strip(),
            base_url=persisted.base_url.strip().rstrip("/"),
            max_attempts=persisted.max_attempts,
            batch_size=persisted.batch_size,
            stale_minutes=persisted.stale_minutes,
            task_due_soon_hours=persisted.task_due_soon_hours,
            task_due_imminent_hours=persisted.task_due_imminent_hours,
            task_critical_hours=persisted.task_critical_hours,
            process_due_soon_hours=persisted.process_due_soon_hours,
            source="database",
            version=persisted.version,
            storage_errors=tuple(storage_errors),
        )

    @property
    def secret_configured(self) -> bool:
        return bool(self.password)

    def validation_errors(self) -> list[str]:
        errors: list[str] = []
        if self.enabled:
            if not self.host:
                errors.append("Informe o servidor SMTP para habilitar o envio.")
            if not self.default_from_email:
                errors.append("Informe o remetente padrão para habilitar o envio.")
            if self.username and not self.password:
                errors.append("O usuário SMTP informado exige senha configurada.")
        if not 1 <= self.port <= 65535:
            errors.append("A porta SMTP deve estar entre 1 e 65535.")
        if self.default_from_email and "@" not in self.default_from_email:
            errors.append("O remetente padrão deve ser um endereço de e-mail.")
        if self.base_url and not self.base_url.startswith(("http://", "https://")):
            errors.append("A URL base deve começar com http:// ou https://.")
        errors.extend(self.storage_errors)
        return errors

    def warnings(self) -> list[str]:
        alerts: list[str] = []
        if not self.base_url:
            # Não impede o envio: o link sai relativo e a mensagem ainda serve.
            alerts.append(
                "Sem URL base os links das mensagens saem relativos e não são "
                "clicáveis no cliente de e-mail."
            )
        if self.enabled and not self.use_tls:
            alerts.append("Sem TLS, usuário e senha do SMTP trafegam sem criptografia.")
        if self.host and self.port not in SUBMISSION_PORTS:
            alerts.append(
                f"A porta {self.port} não é uma porta de submissão usual "
                f"({', '.join(str(port) for port in SUBMISSION_PORTS)})."
            )
        if self.enabled and not self.username:
            alerts.append("Sem usuário SMTP o envio depende de relay anônimo autorizado.")
        return alerts
