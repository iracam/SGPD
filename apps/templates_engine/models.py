"""Immutable published workflow configuration."""

from __future__ import annotations

import uuid
from typing import Any

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models


class VersionStatus(models.TextChoices):
    DRAFT = "DRAFT", "Rascunho"
    PUBLISHED = "PUBLISHED", "Publicada"
    RETIRED = "RETIRED", "Substituída"


class ChecklistResponseType(models.TextChoices):
    BOOLEAN = "BOOLEAN", "Sim/Não"
    TEXT = "TEXT", "Texto"
    NUMBER = "NUMBER", "Número"
    DATE = "DATE", "Data"
    SINGLE_CHOICE = "SINGLE_CHOICE", "Seleção"
    MULTIPLE_CHOICE = "MULTIPLE_CHOICE", "Múltipla seleção"
    FILE = "FILE", "Arquivo"
    CONFIRMATION = "CONFIRMATION", "Confirmação obrigatória"


class WorkflowConfigurationEventType(models.TextChoices):
    TEMPLATE_CREATED = "TEMPLATE_CREATED", "Template criado"
    TEMPLATE_VERSION_CREATED = "TPL_VERSION_CREATED", "Versão de template criada"
    TEMPLATE_DRAFT_UPDATED = "TPL_DRAFT_UPDATED", "Rascunho de template alterado"
    TEMPLATE_PUBLISHED = "TEMPLATE_PUBLISHED", "Template publicado"
    GROUP_CREATED = "GROUP_CREATED", "Grupo criado"
    GROUP_VERSION_CREATED = "GROUP_VERSION_CREATED", "Versão de grupo criada"
    GROUP_DRAFT_UPDATED = "GROUP_DRAFT_UPDATED", "Rascunho de grupo alterado"
    GROUP_PUBLISHED = "GROUP_PUBLISHED", "Grupo publicado"
    RULE_CREATED = "APPLICAB_RULE_CREATED", "Regra de aplicabilidade criada"
    RULE_UPDATED = "APPLICAB_RULE_UPDATED", "Regra de aplicabilidade alterada"


class ProtectedConfigurationQuerySet(models.QuerySet[Any]):
    def update(self, **kwargs: Any) -> int:
        raise ValidationError("Configurações devem ser alteradas por services auditados.")

    def delete(self) -> tuple[int, dict[str, int]]:
        raise ValidationError("Configurações versionadas não podem ser excluídas.")


class ChecklistTemplate(models.Model):
    # O PK só existe após o primeiro INSERT; o service preenche este legado na mesma transação.
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
    current_version = models.ForeignKey(
        "ChecklistTemplateVersion",
        verbose_name="versão vigente",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="+",
    )
    created_at = models.DateTimeField("criado em", auto_now_add=True)
    updated_at = models.DateTimeField("atualizado em", auto_now=True)
    version = models.PositiveIntegerField("versão de concorrência", default=1)

    objects = ProtectedConfigurationQuerySet.as_manager()

    class Meta:
        db_table = "SGPD_CHECKLIST_TEMPLATE"
        ordering = ("name", "pk")
        verbose_name = "template de checklist"
        verbose_name_plural = "templates de checklist"
        constraints = [
            models.CheckConstraint(
                condition=models.Q(name__isnull=False, version__gt=0),
                name="SGPD_CK_TPL_REQUIRED",
            ),
        ]

    def clean(self) -> None:
        super().clean()
        self.name = self.name.strip()
        self.description = self.description.strip()
        if not self.name:
            raise ValidationError({"name": "O nome do template é obrigatório."})
        if self.current_version_id is not None:
            assert self.current_version is not None
            version_template_id = self.current_version.template_id
            if self.pk is None or version_template_id != self.pk:
                raise ValidationError(
                    {"current_version": "A versão vigente precisa pertencer ao template."}
                )

    def delete(self, *args: Any, **kwargs: Any) -> tuple[int, dict[str, int]]:
        raise ValidationError("Templates devem ser inativados, não excluídos.")


class ChecklistTemplateVersion(models.Model):
    template = models.ForeignKey(
        ChecklistTemplate,
        verbose_name="template",
        on_delete=models.PROTECT,
        related_name="versions",
    )
    version_number = models.PositiveIntegerField("número da versão")
    status = models.CharField(
        "situação",
        max_length=12,
        choices=VersionStatus.choices,
        default=VersionStatus.DRAFT,
    )
    default_due_hours = models.PositiveIntegerField(
        "prazo padrão em horas",
        null=True,
        blank=True,
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name="criada por",
        on_delete=models.PROTECT,
        related_name="checklist_template_versions_created",
    )
    created_at = models.DateTimeField("criada em", auto_now_add=True)
    published_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name="publicada por",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="checklist_template_versions_published",
    )
    published_at = models.DateTimeField("publicada em", null=True, blank=True)

    objects = ProtectedConfigurationQuerySet.as_manager()

    class Meta:
        db_table = "SGPD_CHECKLIST_TEMPLATE_VER"
        ordering = ("template_id", "-version_number")
        verbose_name = "versão de template"
        verbose_name_plural = "versões de templates"
        constraints = [
            models.UniqueConstraint(
                fields=("template", "version_number"),
                name="SGPD_UQ_TPL_VERSION",
            ),
            models.CheckConstraint(
                condition=models.Q(version_number__gt=0)
                & (models.Q(default_due_hours__isnull=True) | models.Q(default_due_hours__gt=0)),
                name="SGPD_CK_TPL_VER_VALUES",
            ),
            models.CheckConstraint(
                condition=(
                    models.Q(
                        status=VersionStatus.DRAFT,
                        published_by__isnull=True,
                        published_at__isnull=True,
                    )
                    | models.Q(
                        status__in=(VersionStatus.PUBLISHED, VersionStatus.RETIRED),
                        published_by__isnull=False,
                        published_at__isnull=False,
                    )
                ),
                name="SGPD_CK_TPL_VER_LIFE",
            ),
        ]

    def save(self, *args: Any, **kwargs: Any) -> None:
        if self.pk is not None:
            persisted = type(self).objects.get(pk=self.pk)
            immutable_fields = (
                "template_id",
                "version_number",
                "created_by_id",
                "created_at",
            )
            if any(getattr(self, field) != getattr(persisted, field) for field in immutable_fields):
                raise ValidationError(
                    "O conteúdo de uma versão de template é imutável; crie outra versão."
                )
            if (
                self.default_due_hours != persisted.default_due_hours
                and persisted.status != VersionStatus.DRAFT
            ):
                raise ValidationError(
                    "O conteúdo de uma versão publicada é imutável; crie outra versão."
                )
        super().save(*args, **kwargs)

    def delete(self, *args: Any, **kwargs: Any) -> tuple[int, dict[str, int]]:
        raise ValidationError("Versões de template não podem ser excluídas.")


class ChecklistTemplateItem(models.Model):
    template_version = models.ForeignKey(
        ChecklistTemplateVersion,
        verbose_name="versão do template",
        on_delete=models.PROTECT,
        related_name="items",
    )
    # O PK só existe após o primeiro INSERT; o service preenche o código na mesma transação.
    code = models.CharField(  # noqa: DJ001
        "código técnico",
        max_length=50,
        null=True,
        editable=False,
    )
    question = models.TextField("pergunta")
    response_type = models.CharField(
        "tipo de resposta",
        max_length=20,
        choices=ChecklistResponseType.choices,
    )
    is_required = models.BooleanField("obrigatório", default=True)
    blocks_process = models.BooleanField("bloqueia o processo", default=False)
    requires_evidence = models.BooleanField("exige evidência", default=False)
    allows_pending = models.BooleanField("permite pendência", default=True)
    display_order = models.PositiveIntegerField("ordem de exibição")
    config = models.JSONField("configuração", default=dict, blank=True)

    objects = ProtectedConfigurationQuerySet.as_manager()

    class Meta:
        db_table = "SGPD_CHECKLIST_TEMPLATE_ITEM"
        ordering = ("template_version_id", "display_order", "id")
        verbose_name = "item de template"
        verbose_name_plural = "itens de template"
        constraints = [
            models.UniqueConstraint(
                fields=("template_version", "code"),
                name="SGPD_UQ_TPL_ITEM_CODE",
            ),
            models.UniqueConstraint(
                fields=("template_version", "display_order"),
                name="SGPD_UQ_TPL_ITEM_ORDER",
            ),
            models.CheckConstraint(
                condition=models.Q(
                    question__isnull=False,
                    response_type__isnull=False,
                    display_order__gt=0,
                ),
                name="SGPD_CK_TPL_ITEM_REQ",
            ),
        ]

    def save(self, *args: Any, **kwargs: Any) -> None:
        if self.pk is not None:
            persisted = type(self).objects.only("code").get(pk=self.pk)
            update_fields = kwargs.get("update_fields")
            is_automatic_code_fill = (
                persisted.code in (None, "")
                and self.code == str(self.pk)
                and update_fields is not None
                and set(update_fields) == {"code"}
            )
            if not is_automatic_code_fill:
                raise ValidationError(
                    "Perguntas versionadas são imutáveis por alteração direta; "
                    "use o service do rascunho."
                )
        super().save(*args, **kwargs)

    def clean(self) -> None:
        super().clean()
        self.question = self.question.strip()
        if not self.question:
            raise ValidationError({"question": "A pergunta é obrigatória."})
        if self.template_version.status != VersionStatus.DRAFT:
            raise ValidationError("Itens só podem ser criados em versão de template em rascunho.")
        choices = self.config.get("choices") if isinstance(self.config, dict) else None
        needs_choices = self.response_type in {
            ChecklistResponseType.SINGLE_CHOICE,
            ChecklistResponseType.MULTIPLE_CHOICE,
        }
        if needs_choices and (
            not isinstance(choices, list)
            or not choices
            or any(not isinstance(item, str) or not item.strip() for item in choices)
        ):
            raise ValidationError(
                {"config": "Tipos de seleção exigem uma lista não vazia de opções textuais."}
            )

    def delete(self, *args: Any, **kwargs: Any) -> tuple[int, dict[str, int]]:
        status = (
            ChecklistTemplateVersion.objects.only("status").get(pk=self.template_version_id).status
        )
        if status != VersionStatus.DRAFT:
            raise ValidationError("Itens publicados não podem ser excluídos.")
        return super().delete(*args, **kwargs)


class ValidationGroup(models.Model):
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
    current_version = models.ForeignKey(
        "ValidationGroupVersion",
        verbose_name="versão vigente",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="+",
    )
    created_at = models.DateTimeField("criado em", auto_now_add=True)
    updated_at = models.DateTimeField("atualizado em", auto_now=True)
    version = models.PositiveIntegerField("versão de concorrência", default=1)

    objects = ProtectedConfigurationQuerySet.as_manager()

    class Meta:
        db_table = "SGPD_VALIDATION_GROUP"
        ordering = ("name", "pk")
        verbose_name = "grupo de validação"
        verbose_name_plural = "grupos de validação"
        permissions = [
            (
                "manage_workflow_configuration",
                "Pode criar e publicar grupos e templates",
            ),
        ]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(name__isnull=False, version__gt=0),
                name="SGPD_CK_GROUP_REQUIRED",
            ),
        ]

    def clean(self) -> None:
        super().clean()
        self.name = self.name.strip()
        self.description = self.description.strip()
        if not self.name:
            raise ValidationError({"name": "O nome do grupo é obrigatório."})
        if self.current_version_id is not None:
            assert self.current_version is not None
            version_group_id = self.current_version.group_id
            if self.pk is None or version_group_id != self.pk:
                raise ValidationError(
                    {"current_version": "A versão vigente precisa pertencer ao grupo."}
                )

    def delete(self, *args: Any, **kwargs: Any) -> tuple[int, dict[str, int]]:
        raise ValidationError("Grupos devem ser inativados, não excluídos.")


class ValidationGroupVersion(models.Model):
    group = models.ForeignKey(
        ValidationGroup,
        verbose_name="grupo",
        on_delete=models.PROTECT,
        related_name="versions",
    )
    version_number = models.PositiveIntegerField("número da versão")
    status = models.CharField(
        "situação",
        max_length=12,
        choices=VersionStatus.choices,
        default=VersionStatus.DRAFT,
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name="criada por",
        on_delete=models.PROTECT,
        related_name="validation_group_versions_created",
    )
    created_at = models.DateTimeField("criada em", auto_now_add=True)
    published_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name="publicada por",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="validation_group_versions_published",
    )
    published_at = models.DateTimeField("publicada em", null=True, blank=True)

    objects = ProtectedConfigurationQuerySet.as_manager()

    class Meta:
        db_table = "SGPD_VALIDATION_GROUP_VER"
        ordering = ("group_id", "-version_number")
        verbose_name = "versão de grupo"
        verbose_name_plural = "versões de grupos"
        constraints = [
            models.UniqueConstraint(
                fields=("group", "version_number"),
                name="SGPD_UQ_GROUP_VERSION",
            ),
            models.CheckConstraint(
                condition=models.Q(version_number__gt=0),
                name="SGPD_CK_GROUP_VER_NUM",
            ),
            models.CheckConstraint(
                condition=(
                    models.Q(
                        status=VersionStatus.DRAFT,
                        published_by__isnull=True,
                        published_at__isnull=True,
                    )
                    | models.Q(
                        status__in=(VersionStatus.PUBLISHED, VersionStatus.RETIRED),
                        published_by__isnull=False,
                        published_at__isnull=False,
                    )
                ),
                name="SGPD_CK_GROUP_VER_LIFE",
            ),
        ]

    def save(self, *args: Any, **kwargs: Any) -> None:
        if self.pk is not None:
            persisted = type(self).objects.get(pk=self.pk)
            immutable_fields = (
                "group_id",
                "version_number",
                "created_by_id",
                "created_at",
            )
            if any(getattr(self, field) != getattr(persisted, field) for field in immutable_fields):
                raise ValidationError(
                    "O conteúdo de uma versão de grupo é imutável; crie outra versão."
                )
        super().save(*args, **kwargs)

    def delete(self, *args: Any, **kwargs: Any) -> tuple[int, dict[str, int]]:
        raise ValidationError("Versões de grupo não podem ser excluídas.")


class ValidationGroupSector(models.Model):
    group_version = models.ForeignKey(
        ValidationGroupVersion,
        verbose_name="versão do grupo",
        on_delete=models.PROTECT,
        related_name="sector_rules",
    )
    sector = models.ForeignKey(
        "sectors.ValidationSector",
        verbose_name="setor",
        on_delete=models.PROTECT,
        related_name="validation_group_rules",
    )
    template_version = models.ForeignKey(
        ChecklistTemplateVersion,
        verbose_name="versão do template",
        on_delete=models.PROTECT,
        related_name="validation_group_rules",
    )
    is_required = models.BooleanField("obrigatório", default=True)
    blocks_process = models.BooleanField("bloqueia o processo", default=True)
    due_hours_override = models.PositiveIntegerField(
        "prazo específico em horas",
        null=True,
        blank=True,
    )
    display_order = models.PositiveIntegerField("ordem de exibição")

    objects = ProtectedConfigurationQuerySet.as_manager()

    class Meta:
        db_table = "SGPD_VALIDATION_GROUP_SECTOR"
        ordering = ("group_version_id", "display_order", "id")
        verbose_name = "setor de grupo"
        verbose_name_plural = "setores de grupos"
        constraints = [
            models.UniqueConstraint(
                fields=("group_version", "sector"),
                name="SGPD_UQ_GROUP_SECTOR",
            ),
            models.UniqueConstraint(
                fields=("group_version", "display_order"),
                name="SGPD_UQ_GROUP_ORDER",
            ),
            models.CheckConstraint(
                condition=models.Q(display_order__gt=0)
                & (models.Q(due_hours_override__isnull=True) | models.Q(due_hours_override__gt=0)),
                name="SGPD_CK_GROUP_SECTOR_VAL",
            ),
        ]

    def save(self, *args: Any, **kwargs: Any) -> None:
        if self.pk is not None:
            raise ValidationError("Setores versionados são imutáveis; crie outra versão do grupo.")
        super().save(*args, **kwargs)

    def clean(self) -> None:
        super().clean()
        if self.group_version.status != VersionStatus.DRAFT:
            raise ValidationError("Setores só podem ser incluídos em versão de grupo em rascunho.")
        if self.template_version.status not in {
            VersionStatus.PUBLISHED,
            VersionStatus.RETIRED,
        }:
            raise ValidationError(
                {"template_version": "O template precisa possuir versão publicada."}
            )

    def delete(self, *args: Any, **kwargs: Any) -> tuple[int, dict[str, int]]:
        status = ValidationGroupVersion.objects.only("status").get(pk=self.group_version_id).status
        if status != VersionStatus.DRAFT:
            raise ValidationError("Relações de grupos publicados não podem ser excluídas.")
        return super().delete(*args, **kwargs)


class GroupApplicabilityRule(models.Model):
    """Sugere um grupo quando o snapshot do processo casa com os filtros.

    Campo nulo é curinga. A regra não é versionada: ela aponta para o cabeçalho
    do grupo e a sugestão resolve a versão publicada vigente no momento da
    consulta. O processo continua preservando a versão que o DP selecionou.
    """

    name = models.CharField("nome", max_length=120)
    priority = models.PositiveIntegerField("prioridade", default=100)
    group = models.ForeignKey(
        ValidationGroup,
        verbose_name="grupo sugerido",
        on_delete=models.PROTECT,
        related_name="applicability_rules",
    )
    company_code = models.PositiveIntegerField("código da empresa", null=True, blank=True)
    branch_code = models.PositiveIntegerField("código da filial", null=True, blank=True)
    employee_type_code = models.PositiveIntegerField("tipo de colaborador", null=True, blank=True)
    job_structure_code = models.PositiveIntegerField("estrutura de cargos", null=True, blank=True)
    job_code = models.CharField(  # noqa: DJ001
        "código do cargo",
        max_length=50,
        null=True,
        blank=True,
    )
    cost_center_code = models.CharField(  # noqa: DJ001
        "código do centro de custo",
        max_length=50,
        null=True,
        blank=True,
    )
    is_active = models.BooleanField("ativa", default=True)
    valid_from = models.DateField("válida de", null=True, blank=True)
    valid_to = models.DateField("válida até", null=True, blank=True)
    created_at = models.DateTimeField("criada em", auto_now_add=True)
    updated_at = models.DateTimeField("atualizada em", auto_now=True)
    version = models.PositiveIntegerField("versão de concorrência", default=1)

    objects = ProtectedConfigurationQuerySet.as_manager()

    class Meta:
        db_table = "SGPD_GROUP_APPLICAB_RULE"
        ordering = ("-priority", "name", "pk")
        verbose_name = "regra de aplicabilidade"
        verbose_name_plural = "regras de aplicabilidade"
        constraints = [
            models.CheckConstraint(
                condition=models.Q(name__isnull=False, priority__gt=0, version__gt=0),
                name="SGPD_CK_APPLICAB_RULE_REQ",
            ),
            models.CheckConstraint(
                condition=models.Q(valid_from__isnull=True)
                | models.Q(valid_to__isnull=True)
                | models.Q(valid_to__gte=models.F("valid_from")),
                name="SGPD_CK_APPLICAB_RULE_WIN",
            ),
            models.CheckConstraint(
                condition=models.Q(branch_code__isnull=True) | models.Q(company_code__isnull=False),
                name="SGPD_CK_APPLICAB_RULE_BRA",
            ),
        ]
        indexes = [
            models.Index(
                fields=("is_active", "company_code", "branch_code"),
                name="SGPD_IX_APPLICAB_RULE_HIT",
            ),
        ]

    def clean(self) -> None:
        super().clean()
        self.name = self.name.strip()
        if not self.name:
            raise ValidationError({"name": "O nome da regra é obrigatório."})
        self.job_code = (self.job_code or "").strip() or None
        self.cost_center_code = (self.cost_center_code or "").strip() or None
        if self.branch_code is not None and self.company_code is None:
            raise ValidationError(
                {"branch_code": "A filial exige a empresa correspondente na mesma regra."}
            )
        if (
            self.valid_from is not None
            and self.valid_to is not None
            and self.valid_to < self.valid_from
        ):
            raise ValidationError({"valid_to": "O fim da validade não pode anteceder o início."})

    def delete(self, *args: Any, **kwargs: Any) -> tuple[int, dict[str, int]]:
        raise ValidationError("Regras de aplicabilidade devem ser inativadas, não excluídas.")


class WorkflowConfigurationAuditEvent(models.Model):
    uuid = models.UUIDField("UUID", default=uuid.uuid4, unique=True, editable=False)
    event_type = models.CharField(
        "tipo do evento",
        max_length=30,
        choices=WorkflowConfigurationEventType.choices,
    )
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name="ator",
        on_delete=models.PROTECT,
        related_name="workflow_configuration_events_performed",
    )
    entity_type = models.CharField("tipo de entidade", max_length=30)
    entity_id = models.PositiveIntegerField("ID da entidade")
    occurred_at = models.DateTimeField("ocorrido em", auto_now_add=True)
    data = models.JSONField("dados", default=dict)
    correlation_id = models.CharField("correlation ID", max_length=64, default="-")

    objects = ProtectedConfigurationQuerySet.as_manager()

    class Meta:
        db_table = "SGPD_WORKFLOW_CONFIG_AUDIT"
        ordering = ("-occurred_at", "-id")
        verbose_name = "evento de configuração do workflow"
        verbose_name_plural = "eventos de configuração do workflow"
        constraints = [
            models.CheckConstraint(
                condition=models.Q(
                    event_type__isnull=False,
                    actor__isnull=False,
                    entity_type__isnull=False,
                    entity_id__gt=0,
                    correlation_id__isnull=False,
                ),
                name="SGPD_CK_WF_CFG_AUDIT_REQ",
            ),
        ]
        indexes = [
            models.Index(
                fields=("entity_type", "entity_id", "occurred_at"),
                name="SGPD_IX_WF_CFG_ENTITY",
            ),
            models.Index(
                fields=("correlation_id",),
                name="SGPD_IX_WF_CFG_CORR",
            ),
        ]

    def save(self, *args: Any, **kwargs: Any) -> None:
        if self.pk is not None:
            raise ValidationError("Eventos de configuração são imutáveis.")
        super().save(*args, **kwargs)

    def delete(self, *args: Any, **kwargs: Any) -> tuple[int, dict[str, int]]:
        raise ValidationError("Eventos de configuração não podem ser excluídos.")
