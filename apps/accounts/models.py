"""SGPD-owned identities, roles, organizational scopes and account audit."""

from __future__ import annotations

import uuid
from typing import Any

from django.conf import settings
from django.contrib.auth.models import AbstractUser, Permission
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone

RESPONSIBLE_SECTOR_ROLE_CODE = "RESPONSAVEL_SETOR"
PEOPLE_DEPARTMENT_ROLE_CODE = "DP"
PEOPLE_DEPARTMENT_MANAGER_ROLE_CODE = "DP_GERENTE"
WORKFLOW_CONFIG_ADMIN_ROLE_CODE = "GRUPOS_TEMPLATE_ADMIN"
SECTORS_ADMIN_ROLE_CODE = "SETORES_ADMIN"
USERS_ADMIN_ROLE_CODE = "USUARIOS_ADMIN"

# Responsabilidade de setor é derivada do vínculo vigente com o setor; os cinco
# códigos abaixo são o catálogo fixo dos papéis atribuíveis.
FUNCTIONAL_ROLE_CODES = (
    PEOPLE_DEPARTMENT_ROLE_CODE,
    PEOPLE_DEPARTMENT_MANAGER_ROLE_CODE,
    WORKFLOW_CONFIG_ADMIN_ROLE_CODE,
    SECTORS_ADMIN_ROLE_CODE,
    USERS_ADMIN_ROLE_CODE,
)

# Os três papéis administrativos só existem em escopo global: `has_permission()`
# consultado sem empresa e sem filial já exige atribuição global, então escopo
# por empresa seria promessa que a autorização não cumpre.
GLOBAL_ONLY_ROLE_CODES = (
    WORKFLOW_CONFIG_ADMIN_ROLE_CODE,
    SECTORS_ADMIN_ROLE_CODE,
    USERS_ADMIN_ROLE_CODE,
)

# `DP_GERENTE` é superconjunto de `DP`: onde uma regra exige o `DP` vigente no
# escopo, o gerente também satisfaz. A implicação vive aqui e é consultada por
# `role_codes_satisfying()`; nenhum ponto deve comparar o código diretamente.
ROLE_IMPLICATIONS: dict[str, tuple[str, ...]] = {
    PEOPLE_DEPARTMENT_ROLE_CODE: (
        PEOPLE_DEPARTMENT_ROLE_CODE,
        PEOPLE_DEPARTMENT_MANAGER_ROLE_CODE,
    ),
}


def role_codes_satisfying(role_code: str) -> tuple[str, ...]:
    """Códigos de papel que satisfazem a exigência de `role_code`."""

    normalized = role_code.strip().upper()
    return ROLE_IMPLICATIONS.get(normalized, (normalized,))


#: Atalho para os pontos que consultam a atribuição de `DP` por queryset.
PEOPLE_DEPARTMENT_ROLE_CODES = role_codes_satisfying(PEOPLE_DEPARTMENT_ROLE_CODE)


class User(AbstractUser):
    email = models.EmailField("e-mail", unique=True)
    must_change_password = models.BooleanField(
        "deve alterar a senha no próximo acesso",
        default=False,
    )
    ad_identifier = models.CharField(
        "identificador imutável no AD",
        max_length=255,
        unique=True,
        null=True,
        blank=True,
    )
    # Nullable by design so the four AD-link fields share one cross-database state.
    ad_username = models.CharField(  # noqa: DJ001
        "usuário no AD",
        max_length=150,
        null=True,
        blank=True,
    )
    ad_linked_at = models.DateTimeField("vinculado ao AD em", null=True, blank=True)
    ad_linked_by = models.ForeignKey(
        "self",
        verbose_name="vinculado ao AD por",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="ad_links_performed",
    )
    version = models.PositiveIntegerField("versão de concorrência", default=1)

    REQUIRED_FIELDS = ["email", "first_name", "last_name"]

    class Meta:
        db_table = "SGPD_USER"
        verbose_name = "usuário"
        verbose_name_plural = "usuários"
        constraints = [
            models.CheckConstraint(
                condition=models.Q(
                    username__isnull=False,
                    password__isnull=False,
                    first_name__isnull=False,
                    last_name__isnull=False,
                    email__isnull=False,
                ),
                name="SGPD_CK_USER_REQUIRED",
            ),
            models.CheckConstraint(
                condition=(
                    models.Q(
                        ad_identifier__isnull=True,
                        ad_username__isnull=True,
                        ad_linked_at__isnull=True,
                        ad_linked_by__isnull=True,
                    )
                    | models.Q(
                        ad_identifier__isnull=False,
                        ad_username__isnull=False,
                        ad_linked_at__isnull=False,
                        ad_linked_by__isnull=False,
                    )
                ),
                name="SGPD_CK_USER_AD_LINK",
            ),
            models.CheckConstraint(
                condition=models.Q(version__gt=0),
                name="SGPD_CK_USER_VERSION",
            ),
        ]
        permissions = [
            ("manage_users", "Pode criar e manter usuários"),
            ("manage_roles", "Pode criar e manter papéis e permissões"),
            ("link_ad_identity", "Pode vincular e desvincular identidades do AD"),
            ("view_account_audit", "Pode consultar a auditoria de contas"),
            ("query_senior_references", "Pode consultar referências do Senior"),
        ]

    def clean(self) -> None:
        super().clean()
        self.email = self.email.strip().lower()
        self.username = self.username.strip().lower()
        self.first_name = self.first_name.strip()
        self.last_name = self.last_name.strip()
        if not self.first_name:
            raise ValidationError({"first_name": "O nome é obrigatório."})
        if not self.last_name:
            raise ValidationError({"last_name": "O sobrenome é obrigatório."})
        if self.ad_identifier:
            self.ad_identifier = self.ad_identifier.strip().casefold()
        else:
            self.ad_identifier = None
        if self.ad_username:
            self.ad_username = self.ad_username.strip().lower()
        else:
            self.ad_username = None

        link_values = (
            bool(self.ad_identifier),
            bool(self.ad_username),
            self.ad_linked_at is not None,
            self.ad_linked_by_id is not None,
        )
        if any(link_values) and not all(link_values):
            raise ValidationError("O vínculo AD exige identificador, usuário, data e responsável.")

    @property
    def has_ad_link(self) -> bool:
        # Oracle represents an empty character value as NULL and Django may
        # materialize that value as an empty string for this field.
        return bool(self.ad_identifier)

    def __str__(self) -> str:
        return self.get_full_name() or self.username


class Role(models.Model):
    code = models.CharField("código", max_length=50, unique=True)
    name = models.CharField("nome", max_length=120)
    description = models.TextField("descrição", blank=True)
    is_active = models.BooleanField("ativo", default=True)
    permissions = models.ManyToManyField(
        Permission,
        verbose_name="permissões",
        blank=True,
        related_name="sgpd_roles",
    )
    created_at = models.DateTimeField("criado em", auto_now_add=True)
    updated_at = models.DateTimeField("atualizado em", auto_now=True)
    version = models.PositiveIntegerField("versão de concorrência", default=1)

    class Meta:
        db_table = "SGPD_ROLE"
        ordering = ("code",)
        verbose_name = "papel"
        verbose_name_plural = "papéis"
        constraints = [
            models.CheckConstraint(
                condition=models.Q(code__isnull=False, name__isnull=False),
                name="SGPD_CK_ROLE_REQUIRED",
            ),
            models.CheckConstraint(
                condition=(models.Q(code__in=FUNCTIONAL_ROLE_CODES) | models.Q(is_active=False)),
                name="SGPD_CK_ROLE_ACTIVE_CODE",
            ),
            models.CheckConstraint(
                condition=models.Q(version__gt=0),
                name="SGPD_CK_ROLE_VERSION",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.code} — {self.name}"

    def clean(self) -> None:
        super().clean()
        self.code = self.code.strip().upper()
        self.name = self.name.strip()
        if not self.code:
            raise ValidationError({"code": "O código do papel é obrigatório."})
        if not self.name:
            raise ValidationError({"name": "O nome do papel é obrigatório."})
        if self.is_active and self.code not in FUNCTIONAL_ROLE_CODES:
            raise ValidationError(
                {"is_active": "Somente os papéis do catálogo funcional podem permanecer ativos."}
            )


class ScopeType(models.TextChoices):
    GLOBAL = "GLOBAL", "Global"
    COMPANY = "COMPANY", "Empresa"
    BRANCH = "BRANCH", "Filial"


def build_scope_key(
    scope_type: str,
    company_code: int | None,
    branch_code: int | None,
) -> str:
    if scope_type == ScopeType.GLOBAL:
        if company_code is not None or branch_code is not None:
            raise ValidationError("O escopo global não aceita empresa ou filial.")
        return "*"
    if scope_type == ScopeType.COMPANY:
        if company_code is None or branch_code is not None:
            raise ValidationError("O escopo de empresa exige somente a empresa.")
        return f"E:{company_code}"
    if scope_type == ScopeType.BRANCH:
        if company_code is None or branch_code is None:
            raise ValidationError("O escopo de filial exige empresa e filial.")
        return f"F:{company_code}:{branch_code}"
    raise ValidationError("Tipo de escopo inválido.")


class RoleAssignmentQuerySet(models.QuerySet["RoleAssignment"]):
    def delete(self) -> tuple[int, dict[str, int]]:
        raise ValidationError("Atribuições de papel devem ser revogadas, não excluídas.")


class RoleAssignment(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name="usuário",
        on_delete=models.PROTECT,
        related_name="role_assignments",
        db_index=False,
    )
    role = models.ForeignKey(
        Role,
        verbose_name="papel",
        on_delete=models.PROTECT,
        related_name="assignments",
    )
    scope_type = models.CharField(
        "tipo de escopo",
        max_length=10,
        choices=ScopeType.choices,
        default=ScopeType.GLOBAL,
    )
    company_code = models.PositiveIntegerField("código da empresa", null=True, blank=True)
    branch_code = models.PositiveIntegerField("código da filial", null=True, blank=True)
    scope_key = models.CharField("chave do escopo", max_length=64, editable=False)
    valid_from = models.DateTimeField("válido desde", default=timezone.now)
    valid_until = models.DateTimeField("válido até", null=True, blank=True)
    is_active = models.BooleanField("ativo", default=True)
    assigned_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name="atribuído por",
        on_delete=models.PROTECT,
        related_name="role_assignments_performed",
    )
    assigned_at = models.DateTimeField("atribuído em", auto_now_add=True)
    revoked_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name="revogado por",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="role_revocations_performed",
    )
    revoked_at = models.DateTimeField("revogado em", null=True, blank=True)

    objects = RoleAssignmentQuerySet.as_manager()

    class Meta:
        db_table = "SGPD_ROLE_ASSIGN"
        ordering = ("user_id", "role__code", "scope_key")
        verbose_name = "atribuição de papel"
        verbose_name_plural = "atribuições de papéis"
        constraints = [
            models.UniqueConstraint(
                fields=("user", "role", "scope_key"),
                name="SGPD_UQ_ROLE_SCOPE",
            ),
            models.CheckConstraint(
                condition=(
                    models.Q(
                        scope_type=ScopeType.GLOBAL,
                        company_code__isnull=True,
                        branch_code__isnull=True,
                    )
                    | models.Q(
                        scope_type=ScopeType.COMPANY,
                        company_code__isnull=False,
                        branch_code__isnull=True,
                    )
                    | models.Q(
                        scope_type=ScopeType.BRANCH,
                        company_code__isnull=False,
                        branch_code__isnull=False,
                    )
                ),
                name="SGPD_CK_ROLE_SCOPE",
            ),
            models.CheckConstraint(
                condition=(
                    models.Q(valid_until__isnull=True)
                    | models.Q(valid_until__gt=models.F("valid_from"))
                ),
                name="SGPD_CK_ROLE_VALID",
            ),
            models.CheckConstraint(
                condition=(
                    models.Q(
                        is_active=True,
                        revoked_at__isnull=True,
                        revoked_by__isnull=True,
                    )
                    | models.Q(
                        is_active=False,
                        revoked_at__isnull=False,
                        revoked_by__isnull=False,
                    )
                ),
                name="SGPD_CK_ROLE_REVOKE",
            ),
            models.CheckConstraint(
                condition=models.Q(
                    scope_type__isnull=False,
                    scope_key__isnull=False,
                ),
                name="SGPD_CK_ASSIGN_REQUIRED",
            ),
            models.CheckConstraint(
                condition=(
                    (models.Q(company_code__isnull=True) | models.Q(company_code__gt=0))
                    & (models.Q(branch_code__isnull=True) | models.Q(branch_code__gt=0))
                ),
                name="SGPD_CK_ROLE_CODES",
            ),
        ]
        indexes = [
            models.Index(
                fields=("user", "is_active", "valid_from"),
                name="SGPD_IX_ROLE_USER",
            ),
            models.Index(
                fields=("company_code", "branch_code", "is_active"),
                name="SGPD_IX_ROLE_ORG",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.user} / {self.role.code} / {self.scope_key}"

    def clean(self) -> None:
        super().clean()
        self.scope_key = build_scope_key(
            self.scope_type,
            self.company_code,
            self.branch_code,
        )
        if self.valid_until is not None and self.valid_until <= self.valid_from:
            raise ValidationError({"valid_until": "A validade final deve ser posterior à inicial."})
        revocation_values = (
            self.revoked_at is not None,
            self.revoked_by_id is not None,
        )
        if any(revocation_values) and not all(revocation_values):
            raise ValidationError("A revogação exige data e responsável.")
        if self.is_active and any(revocation_values):
            raise ValidationError("Uma atribuição ativa não pode estar revogada.")

    def is_effective(self, at: Any | None = None) -> bool:
        instant = at or timezone.now()
        return (
            self.is_active
            and self.valid_from <= instant
            and (self.valid_until is None or self.valid_until > instant)
        )

    def delete(self, *args: Any, **kwargs: Any) -> tuple[int, dict[str, int]]:
        raise ValidationError("Atribuições de papel devem ser revogadas, não excluídas.")


class AccountEventType(models.TextChoices):
    LOGIN = "LOGIN", "Login realizado"
    LOGOUT = "LOGOUT", "Logout realizado"
    LOGIN_FAILED = "LOGIN_FAILED", "Falha de autenticação"
    USER_CREATED = "USER_CREATED", "Usuário criado"
    USER_UPDATED = "USER_UPDATED", "Usuário atualizado"
    USER_ACTIVATED = "USER_ACTIVATED", "Usuário ativado"
    USER_DEACTIVATED = "USER_DEACTIVATED", "Usuário desativado"
    PASSWORD_CHANGED = "PASSWORD_CHANGED", "Senha alterada pelo usuário"
    PASSWORD_RESET = "PASSWORD_RESET", "Senha redefinida"
    ROLE_CREATED = "ROLE_CREATED", "Papel criado"
    ROLE_UPDATED = "ROLE_UPDATED", "Papel atualizado"
    ROLE_ASSIGNED = "ROLE_ASSIGNED", "Papel atribuído"
    ROLE_REVOKED = "ROLE_REVOKED", "Papel revogado"
    AD_LINKED = "AD_LINKED", "Identidade AD vinculada"
    AD_UNLINKED = "AD_UNLINKED", "Identidade AD desvinculada"
    LDAP_CONFIG_UPDATED = "LDAP_CONFIG_UPDATED", "Configuração LDAP atualizada"
    LDAP_CERT_UPLOADED = "LDAP_CERT_UPLOADED", "Certificado LDAP enviado"
    LDAP_CONNECTION_TESTED = "LDAP_CONNECTION_TESTED", "Conexão LDAP testada"
    EMAIL_CONFIG_UPDATED = "EMAIL_CONFIG_UPDATED", "Configuração de e-mail atualizada"
    EMAIL_TEST_SENT = "EMAIL_TEST_SENT", "Mensagem de prova de e-mail enviada"


class AccountAuditEventQuerySet(models.QuerySet["AccountAuditEvent"]):
    def update(self, **kwargs: Any) -> int:
        raise ValidationError("Eventos de auditoria são imutáveis.")

    def delete(self) -> tuple[int, dict[str, int]]:
        raise ValidationError("Eventos de auditoria não podem ser excluídos.")


class AccountAuditEvent(models.Model):
    uuid = models.UUIDField("UUID", default=uuid.uuid4, unique=True, editable=False)
    event_type = models.CharField(
        "tipo do evento",
        max_length=30,
        choices=AccountEventType.choices,
    )
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name="ator",
        null=True,
        on_delete=models.PROTECT,
        related_name="account_events_performed",
    )
    target_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name="usuário afetado",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="account_audit_events",
        db_index=False,
    )
    entity_type = models.CharField("tipo da entidade", max_length=30)
    entity_id = models.CharField("identificador da entidade", max_length=64)
    occurred_at = models.DateTimeField("ocorrido em", auto_now_add=True)
    reason = models.TextField("justificativa")
    changes = models.JSONField("alterações", default=dict)
    correlation_id = models.CharField("correlation ID", max_length=64, default="-")

    objects = AccountAuditEventQuerySet.as_manager()

    class Meta:
        db_table = "SGPD_ACCOUNT_AUDIT"
        ordering = ("-occurred_at", "-id")
        verbose_name = "evento de auditoria de conta"
        verbose_name_plural = "eventos de auditoria de contas"
        constraints = [
            models.CheckConstraint(
                condition=models.Q(
                    event_type__isnull=False,
                    entity_type__isnull=False,
                    entity_id__isnull=False,
                    reason__isnull=False,
                    correlation_id__isnull=False,
                ),
                name="SGPD_CK_AUDIT_REQUIRED",
            ),
        ]
        indexes = [
            models.Index(
                fields=("target_user", "occurred_at"),
                name="SGPD_IX_AUDIT_USER",
            ),
            models.Index(
                fields=("correlation_id",),
                name="SGPD_IX_AUDIT_CORR",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.event_type} / {self.entity_type}:{self.entity_id}"

    def save(self, *args: Any, **kwargs: Any) -> None:
        if self.pk is not None:
            raise ValidationError("Eventos de auditoria são imutáveis.")
        super().save(*args, **kwargs)

    def delete(self, *args: Any, **kwargs: Any) -> tuple[int, dict[str, int]]:
        raise ValidationError("Eventos de auditoria não podem ser excluídos.")
