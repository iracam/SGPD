"""Validation sectors, organizational coverage and append-only audit."""

from __future__ import annotations

import uuid
from typing import Any

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone

from apps.accounts.models import ScopeType, build_scope_key


class ValidationSectorQuerySet(models.QuerySet["ValidationSector"]):
    def update(self, **kwargs: Any) -> int:
        raise ValidationError("Setores devem ser alterados pelo service auditado.")

    def delete(self) -> tuple[int, dict[str, int]]:
        raise ValidationError("Setores devem ser inativados, não excluídos.")


class ValidationSector(models.Model):
    # O PK só existe após o primeiro INSERT; o service preenche o código na mesma transação.
    code = models.CharField(  # noqa: DJ001
        "código técnico",
        max_length=50,
        unique=True,
        null=True,
        editable=False,
    )
    name = models.CharField("nome", max_length=120)
    description = models.TextField("descrição", blank=True)
    is_active = models.BooleanField("ativo", default=True)
    default_due_hours = models.PositiveIntegerField("prazo padrão em horas")
    blocks_process = models.BooleanField("bloqueia o processo", default=True)
    allows_amount = models.BooleanField("permite lançar valores", default=False)
    requires_evidence = models.BooleanField("exige evidência", default=False)
    escalation_sector = models.ForeignKey(
        "self",
        verbose_name="setor de escalada",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="escalation_sources",
    )
    created_at = models.DateTimeField("criado em", auto_now_add=True)
    updated_at = models.DateTimeField("atualizado em", auto_now=True)
    version = models.PositiveIntegerField("versão de concorrência", default=1)

    objects = ValidationSectorQuerySet.as_manager()

    class Meta:
        db_table = "SGPD_VALIDATION_SECTOR"
        ordering = ("name", "pk")
        verbose_name = "setor de validação"
        verbose_name_plural = "setores de validação"
        permissions = [
            ("manage_sectors", "Pode criar e manter setores de validação"),
        ]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(
                    name__isnull=False,
                    default_due_hours__gt=0,
                ),
                name="SGPD_CK_SECTOR_REQUIRED",
            ),
            models.CheckConstraint(
                condition=models.Q(version__gt=0),
                name="SGPD_CK_SECTOR_VERSION",
            ),
        ]
        indexes = [
            models.Index(
                fields=("is_active", "code"),
                name="SGPD_IX_SECTOR_ACTIVE",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.code} — {self.name}"

    def clean(self) -> None:
        super().clean()
        self.name = self.name.strip()
        self.description = self.description.strip()
        if not self.name:
            raise ValidationError({"name": "O nome do setor é obrigatório."})
        if self.default_due_hours <= 0:
            raise ValidationError({"default_due_hours": "O prazo padrão deve ser maior que zero."})
        if self.pk is not None and self.escalation_sector_id == self.pk:
            raise ValidationError(
                {"escalation_sector_id": "O setor não pode escalar para ele próprio."}
            )

    def delete(self, *args: Any, **kwargs: Any) -> tuple[int, dict[str, int]]:
        raise ValidationError("Setores devem ser inativados, não excluídos.")


class SectorScope(models.Model):
    sector = models.ForeignKey(
        ValidationSector,
        verbose_name="setor",
        on_delete=models.PROTECT,
        related_name="scopes",
    )
    scope_type = models.CharField(
        "tipo de escopo",
        max_length=10,
        choices=ScopeType.choices,
    )
    company_code = models.PositiveIntegerField("código da empresa", null=True, blank=True)
    branch_code = models.PositiveIntegerField("código da filial", null=True, blank=True)
    scope_key = models.CharField("chave do escopo", max_length=64, editable=False)

    class Meta:
        db_table = "SGPD_SECTOR_SCOPE"
        ordering = ("sector_id", "scope_key")
        verbose_name = "escopo de setor"
        verbose_name_plural = "escopos de setores"
        constraints = [
            models.UniqueConstraint(
                fields=("sector", "scope_key"),
                name="SGPD_UQ_SECTOR_SCOPE",
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
                name="SGPD_CK_SECTOR_SCOPE",
            ),
            models.CheckConstraint(
                condition=models.Q(
                    scope_type__isnull=False,
                    scope_key__isnull=False,
                ),
                name="SGPD_CK_SECTOR_SCOPE_REQ",
            ),
            models.CheckConstraint(
                condition=(
                    (models.Q(company_code__isnull=True) | models.Q(company_code__gt=0))
                    & (models.Q(branch_code__isnull=True) | models.Q(branch_code__gt=0))
                ),
                name="SGPD_CK_SECTOR_CODES",
            ),
        ]
        indexes = [
            models.Index(
                fields=("company_code", "branch_code"),
                name="SGPD_IX_SECTOR_ORG",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.sector.code} / {self.scope_key}"

    def clean(self) -> None:
        super().clean()
        self.scope_key = build_scope_key(
            self.scope_type,
            self.company_code,
            self.branch_code,
        )


class SectorResponsibleQuerySet(models.QuerySet["SectorResponsible"]):
    def update(self, **kwargs: Any) -> int:
        raise ValidationError(
            "Responsabilidades de setor devem ser alteradas pelo service auditado."
        )

    def delete(self) -> tuple[int, dict[str, int]]:
        raise ValidationError("Responsabilidades de setor devem ser revogadas, não excluídas.")


class SectorResponsible(models.Model):
    sector = models.ForeignKey(
        ValidationSector,
        verbose_name="setor",
        on_delete=models.PROTECT,
        related_name="responsibles",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name="usuário",
        on_delete=models.PROTECT,
        related_name="sector_responsibilities",
    )
    valid_from = models.DateTimeField("válido desde", default=timezone.now)
    valid_until = models.DateTimeField("válido até", null=True, blank=True)
    is_active = models.BooleanField("ativo", default=True)
    assigned_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name="atribuído por",
        on_delete=models.PROTECT,
        related_name="sector_responsibilities_assigned",
    )
    assigned_at = models.DateTimeField("atribuído em", default=timezone.now)
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name="atualizado por",
        on_delete=models.PROTECT,
        related_name="sector_responsibilities_updated",
    )
    updated_at = models.DateTimeField("atualizado em", auto_now=True)
    revoked_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name="revogado por",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="sector_responsibilities_revoked",
    )
    revoked_at = models.DateTimeField("revogado em", null=True, blank=True)
    version = models.PositiveIntegerField("versão de concorrência", default=1)

    objects = SectorResponsibleQuerySet.as_manager()

    class Meta:
        db_table = "SGPD_SECTOR_RESPONSIBLE"
        ordering = ("sector__name", "sector_id", "user__username")
        verbose_name = "responsável de setor"
        verbose_name_plural = "responsáveis de setores"
        constraints = [
            models.UniqueConstraint(
                fields=("sector", "user"),
                name="SGPD_UQ_SECTOR_RESP_USER",
            ),
            models.CheckConstraint(
                condition=(
                    models.Q(valid_until__isnull=True)
                    | models.Q(valid_until__gt=models.F("valid_from"))
                ),
                name="SGPD_CK_SECTOR_RESP_VALID",
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
                name="SGPD_CK_SECTOR_RESP_REVOKE",
            ),
            models.CheckConstraint(
                condition=models.Q(
                    assigned_by__isnull=False,
                    updated_by__isnull=False,
                ),
                name="SGPD_CK_SECTOR_RESP_REQ",
            ),
            models.CheckConstraint(
                condition=models.Q(version__gt=0),
                name="SGPD_CK_SECTOR_RESP_VERSION",
            ),
        ]
        indexes = [
            models.Index(
                fields=("sector", "is_active", "valid_from"),
                name="SGPD_IX_RESP_SECTOR",
            ),
            models.Index(
                fields=("user", "is_active", "valid_from"),
                name="SGPD_IX_RESP_USER",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.sector.code} / {self.user}"

    def clean(self) -> None:
        super().clean()
        if self.valid_until is not None and self.valid_until <= self.valid_from:
            raise ValidationError({"valid_until": "A validade final deve ser posterior à inicial."})
        revocation_values = (
            self.revoked_at is not None,
            self.revoked_by_id is not None,
        )
        if any(revocation_values) and not all(revocation_values):
            raise ValidationError("A revogação exige data e responsável.")
        if self.is_active and any(revocation_values):
            raise ValidationError("Uma responsabilidade ativa não pode estar revogada.")
        if not self.is_active and not all(revocation_values):
            raise ValidationError("Uma responsabilidade inativa deve possuir revogação.")

    def is_effective(self, at: Any | None = None) -> bool:
        instant = at or timezone.now()
        return (
            self.is_active
            and self.user.is_active
            and self.sector.is_active
            and self.valid_from <= instant
            and (self.valid_until is None or self.valid_until > instant)
        )

    def delete(self, *args: Any, **kwargs: Any) -> tuple[int, dict[str, int]]:
        raise ValidationError("Responsabilidades de setor devem ser revogadas, não excluídas.")


class SectorEventType(models.TextChoices):
    CREATED = "SECTOR_CREATED", "Setor criado"
    UPDATED = "SECTOR_UPDATED", "Setor atualizado"
    ACTIVATED = "SECTOR_ACTIVATED", "Setor ativado"
    DEACTIVATED = "SECTOR_DEACTIVATED", "Setor inativado"
    RESPONSIBLE_ASSIGNED = (
        "SECTOR_RESPONSIBLE_ASSIGNED",
        "Responsável associado",
    )
    RESPONSIBLE_UPDATED = (
        "SECTOR_RESPONSIBLE_UPDATED",
        "Responsabilidade atualizada",
    )
    RESPONSIBLE_REVOKED = (
        "SECTOR_RESPONSIBLE_REVOKED",
        "Responsabilidade revogada",
    )


class SectorAuditEventQuerySet(models.QuerySet["SectorAuditEvent"]):
    def update(self, **kwargs: Any) -> int:
        raise ValidationError("Eventos de auditoria são imutáveis.")

    def delete(self) -> tuple[int, dict[str, int]]:
        raise ValidationError("Eventos de auditoria não podem ser excluídos.")


class SectorAuditEvent(models.Model):
    uuid = models.UUIDField("UUID", default=uuid.uuid4, unique=True, editable=False)
    event_type = models.CharField(
        "tipo do evento",
        max_length=30,
        choices=SectorEventType.choices,
    )
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name="ator",
        on_delete=models.PROTECT,
        related_name="sector_events_performed",
    )
    sector = models.ForeignKey(
        ValidationSector,
        verbose_name="setor",
        on_delete=models.PROTECT,
        related_name="audit_events",
    )
    occurred_at = models.DateTimeField("ocorrido em", auto_now_add=True)
    reason = models.TextField("justificativa")
    changes = models.JSONField("alterações", default=dict)
    correlation_id = models.CharField("correlation ID", max_length=64, default="-")

    objects = SectorAuditEventQuerySet.as_manager()

    class Meta:
        db_table = "SGPD_SECTOR_AUDIT"
        ordering = ("-occurred_at", "-id")
        verbose_name = "evento de auditoria de setor"
        verbose_name_plural = "eventos de auditoria de setores"
        constraints = [
            models.CheckConstraint(
                condition=models.Q(
                    event_type__isnull=False,
                    reason__isnull=False,
                    correlation_id__isnull=False,
                ),
                name="SGPD_CK_SECTOR_AUDIT_REQ",
            ),
        ]
        indexes = [
            models.Index(
                fields=("sector", "occurred_at"),
                name="SGPD_IX_SECTOR_AUDIT",
            ),
            models.Index(
                fields=("correlation_id",),
                name="SGPD_IX_SECTOR_CORR",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.event_type} / {self.sector.code}"

    def save(self, *args: Any, **kwargs: Any) -> None:
        if self.pk is not None:
            raise ValidationError("Eventos de auditoria são imutáveis.")
        super().save(*args, **kwargs)

    def delete(self, *args: Any, **kwargs: Any) -> tuple[int, dict[str, int]]:
        raise ValidationError("Eventos de auditoria não podem ser excluídos.")
