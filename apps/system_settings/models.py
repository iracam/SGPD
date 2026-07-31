"""Persisted LDAP configuration owned by the SGPD schema."""

from __future__ import annotations

from typing import Any

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models

from .storage import system_configuration_storage

LDAP_CONFIGURATION_KEY = "PRIMARY"


class LdapConfigurationQuerySet(models.QuerySet["LdapConfiguration"]):
    def update(self, **kwargs: Any) -> int:
        raise ValidationError("A configuração LDAP deve ser alterada pelo service auditado.")

    def delete(self) -> tuple[int, dict[str, int]]:
        raise ValidationError("A configuração LDAP deve ser atualizada, não excluída.")


class LdapConfiguration(models.Model):
    """Singleton configuration with optimistic concurrency and probe state."""

    key = models.CharField(
        "chave",
        max_length=16,
        primary_key=True,
        default=LDAP_CONFIGURATION_KEY,
        editable=False,
    )
    enabled = models.BooleanField("descoberta habilitada", default=False)
    authentication_enabled = models.BooleanField("autenticação habilitada", default=False)
    server_uri = models.CharField("URI do servidor", max_length=512, blank=True)
    bind_dn = models.CharField("identidade de bind", max_length=512, blank=True)
    bind_password_ciphertext = models.TextField(  # noqa: DJ001
        "senha de bind cifrada",
        null=True,
        blank=True,
        editable=False,
    )
    user_search_base = models.CharField("base de usuários", max_length=2000, blank=True)
    group_search_base = models.CharField("base de grupos", max_length=2000, blank=True)
    required_group_dn = models.CharField("grupo obrigatório", max_length=2000, blank=True)
    start_tls = models.BooleanField("usar StartTLS", default=False)
    connect_timeout_seconds = models.PositiveSmallIntegerField(
        "timeout de conexão em segundos",
        default=5,
    )
    receive_timeout_seconds = models.PositiveSmallIntegerField(
        "timeout de resposta em segundos",
        default=10,
    )
    page_size = models.PositiveSmallIntegerField("tamanho da página LDAP", default=100)
    result_limit = models.PositiveSmallIntegerField("limite de resultados", default=50)
    nested_group_search = models.BooleanField("buscar grupos aninhados", default=True)
    local_superuser_fallback = models.BooleanField(
        "preservar contingência local de SuperAdmin",
        default=True,
    )
    user_extra_filter = models.CharField(
        "filtro adicional de usuários",
        max_length=2000,
        blank=True,
    )

    certificate_file = models.FileField(
        "arquivo da CA",
        storage=system_configuration_storage,
        upload_to="ldap-ca/",
        max_length=255,
        null=True,
        blank=True,
    )
    certificate_original_name = models.CharField(
        "nome original da CA",
        max_length=255,
        blank=True,
    )
    certificate_sha256 = models.CharField("SHA-256 da CA", max_length=64, blank=True)
    certificate_subject = models.CharField("subject da CA", max_length=1024, blank=True)
    certificate_issuer = models.CharField("issuer da CA", max_length=1024, blank=True)
    certificate_not_before = models.DateTimeField("CA válida desde", null=True, blank=True)
    certificate_not_after = models.DateTimeField("CA válida até", null=True, blank=True)
    certificate_count = models.PositiveSmallIntegerField(
        "certificados no bundle",
        default=0,
    )
    certificate_uploaded_at = models.DateTimeField("CA enviada em", null=True, blank=True)
    certificate_uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name="CA enviada por",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="ldap_certificates_uploaded",
    )

    last_tested_at = models.DateTimeField("último teste em", null=True, blank=True)
    last_test_success = models.BooleanField("último teste passou", null=True, blank=True)
    last_test_fingerprint = models.CharField(
        "fingerprint da configuração testada",
        max_length=64,
        blank=True,
    )
    last_test_duration_ms = models.PositiveIntegerField(
        "duração do último teste em ms",
        null=True,
        blank=True,
    )
    last_tested_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name="último teste por",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="ldap_connections_tested",
    )

    version = models.PositiveIntegerField("versão de concorrência", default=1)
    updated_at = models.DateTimeField("atualizado em", auto_now=True)
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name="atualizado por",
        on_delete=models.PROTECT,
        related_name="ldap_configurations_updated",
    )

    objects = LdapConfigurationQuerySet.as_manager()

    class Meta:
        db_table = "SGPD_LDAP_CONFIG"
        verbose_name = "configuração LDAP"
        verbose_name_plural = "configurações LDAP"
        constraints = [
            models.CheckConstraint(
                condition=models.Q(version__gt=0),
                name="SGPD_CK_LDAP_VERSION",
            ),
            models.CheckConstraint(
                condition=models.Q(
                    connect_timeout_seconds__gt=0,
                    receive_timeout_seconds__gt=0,
                    page_size__gt=0,
                    result_limit__gt=0,
                ),
                name="SGPD_CK_LDAP_LIMITS",
            ),
        ]

    def save(self, *args: Any, **kwargs: Any) -> None:
        if self.pk and self.pk != LDAP_CONFIGURATION_KEY:
            raise ValidationError("A configuração LDAP deve usar a chave singleton PRIMARY.")
        super().save(*args, **kwargs)

    def delete(self, *args: Any, **kwargs: Any) -> tuple[int, dict[str, int]]:
        raise ValidationError("A configuração LDAP deve ser atualizada, não excluída.")

    def clean(self) -> None:
        super().clean()
        if self.key != LDAP_CONFIGURATION_KEY:
            raise ValidationError("A configuração LDAP deve usar a chave singleton PRIMARY.")
        if self.authentication_enabled and not self.enabled:
            raise ValidationError(
                {"authentication_enabled": "A autenticação exige a descoberta habilitada."}
            )
        certificate_values = (
            bool(self.certificate_file),
            bool(self.certificate_sha256),
            self.certificate_not_before is not None,
            self.certificate_not_after is not None,
            self.certificate_count > 0,
            self.certificate_uploaded_at is not None,
            self.certificate_uploaded_by_id is not None,
        )
        if any(certificate_values) and not all(certificate_values):
            raise ValidationError("Os metadados do certificado LDAP estão incompletos.")


EMAIL_CONFIGURATION_KEY = "PRIMARY"


class EmailConfigurationQuerySet(models.QuerySet["EmailConfiguration"]):
    def update(self, **kwargs: Any) -> int:
        raise ValidationError("A configuração de e-mail deve ser alterada pelo service auditado.")

    def delete(self) -> tuple[int, dict[str, int]]:
        raise ValidationError("A configuração de e-mail deve ser atualizada, não excluída.")


class EmailConfiguration(models.Model):
    """Transporte SMTP, remetente e ritmo da fila de notificações (ADR-050)."""

    key = models.CharField(
        "chave",
        max_length=16,
        primary_key=True,
        default=EMAIL_CONFIGURATION_KEY,
        editable=False,
    )
    enabled = models.BooleanField("envio habilitado", default=False)
    host = models.CharField("servidor SMTP", max_length=255, blank=True)
    port = models.PositiveIntegerField("porta", default=587)
    use_tls = models.BooleanField("usar TLS/STARTTLS", default=True)
    username = models.CharField("usuário SMTP", max_length=255, blank=True)
    password_ciphertext = models.TextField(  # noqa: DJ001
        "senha SMTP cifrada",
        null=True,
        blank=True,
        editable=False,
    )
    timeout_seconds = models.PositiveSmallIntegerField("timeout em segundos", default=10)
    default_from_email = models.CharField("remetente padrão", max_length=254, blank=True)
    # Compõe os links das mensagens. Vazio produz link relativo, que o cliente
    # de e-mail não torna clicável.
    base_url = models.CharField("URL base da aplicação", max_length=255, blank=True)

    max_attempts = models.PositiveSmallIntegerField("tentativas máximas", default=5)
    batch_size = models.PositiveSmallIntegerField("mensagens por despacho", default=50)
    stale_minutes = models.PositiveSmallIntegerField("minutos para reabrir envio", default=15)

    task_due_soon_hours = models.PositiveSmallIntegerField(
        "horas do primeiro lembrete",
        default=48,
    )
    task_due_imminent_hours = models.PositiveSmallIntegerField(
        "horas do lembrete final",
        default=24,
    )
    task_critical_hours = models.PositiveSmallIntegerField(
        "horas para o atraso crítico",
        default=48,
    )
    process_due_soon_hours = models.PositiveSmallIntegerField(
        "horas do alerta do processo",
        default=72,
    )

    last_tested_at = models.DateTimeField("último teste em", null=True, blank=True)
    last_test_success = models.BooleanField("último teste passou", null=True, blank=True)
    last_test_recipient = models.CharField("destinatário do teste", max_length=254, blank=True)
    last_test_error = models.TextField("erro do último teste", blank=True)
    last_tested_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name="último teste por",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="email_configurations_tested",
    )

    version = models.PositiveIntegerField("versão de concorrência", default=1)
    updated_at = models.DateTimeField("atualizado em", auto_now=True)
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name="atualizado por",
        on_delete=models.PROTECT,
        related_name="email_configurations_updated",
    )

    objects = EmailConfigurationQuerySet.as_manager()

    class Meta:
        db_table = "SGPD_EMAIL_CONFIG"
        verbose_name = "configuração de e-mail"
        verbose_name_plural = "configurações de e-mail"
        constraints = [
            models.CheckConstraint(
                condition=models.Q(version__gt=0),
                name="SGPD_CK_EMAIL_VERSION",
            ),
            models.CheckConstraint(
                condition=models.Q(port__gte=1, port__lte=65535),
                name="SGPD_CK_EMAIL_PORT",
            ),
            models.CheckConstraint(
                condition=models.Q(
                    timeout_seconds__gt=0,
                    max_attempts__gt=0,
                    batch_size__gt=0,
                    stale_minutes__gt=0,
                ),
                name="SGPD_CK_EMAIL_QUEUE",
            ),
            models.CheckConstraint(
                condition=models.Q(
                    task_due_soon_hours__gt=0,
                    task_due_imminent_hours__gt=0,
                    task_critical_hours__gt=0,
                    process_due_soon_hours__gt=0,
                ),
                name="SGPD_CK_EMAIL_MILESTONES",
            ),
        ]

    def save(self, *args: Any, **kwargs: Any) -> None:
        if self.pk and self.pk != EMAIL_CONFIGURATION_KEY:
            raise ValidationError("A configuração de e-mail deve usar a chave singleton PRIMARY.")
        super().save(*args, **kwargs)

    def delete(self, *args: Any, **kwargs: Any) -> tuple[int, dict[str, int]]:
        raise ValidationError("A configuração de e-mail deve ser atualizada, não excluída.")

    def clean(self) -> None:
        super().clean()
        if self.key != EMAIL_CONFIGURATION_KEY:
            raise ValidationError("A configuração de e-mail deve usar a chave singleton PRIMARY.")
        self.host = self.host.strip()
        self.username = self.username.strip()
        self.default_from_email = self.default_from_email.strip()
        self.base_url = self.base_url.strip().rstrip("/")
        if self.enabled and not self.host:
            raise ValidationError({"host": "Informe o servidor SMTP para habilitar o envio."})
        if self.enabled and not self.default_from_email:
            raise ValidationError(
                {"default_from_email": "Informe o remetente padrão para habilitar o envio."}
            )
        if self.task_due_imminent_hours >= self.task_due_soon_hours:
            raise ValidationError(
                {
                    "task_due_imminent_hours": (
                        "O lembrete final precisa ser mais próximo do prazo que o primeiro."
                    )
                }
            )
