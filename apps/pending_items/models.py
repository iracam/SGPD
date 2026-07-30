"""Structured pending items, their lines and append-only comments."""

from __future__ import annotations

import uuid
from typing import Any

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models


class PendingCategory(models.TextChoices):
    MATERIAL = "MATERIAL", "Material"
    TOOL = "FERRAMENTA", "Ferramenta"
    EQUIPMENT = "EQUIPAMENTO", "Equipamento"
    DOCUMENT = "DOCUMENTO", "Documento"
    ACCESS = "ACESSO", "Acesso"
    EXAM = "EXAME", "Exame"
    ACTIVITY = "ATIVIDADE", "Atividade"
    VEHICLE = "VEICULO", "Veículo"
    ASSET = "PATRIMONIO", "Patrimônio"
    CONTRACT = "CONTRATO", "Contrato"
    OTHER = "OUTRO", "Outro"


class PendingStatus(models.TextChoices):
    OPEN = "ABERTA", "Aberta"
    IN_REGULARIZATION = "EM_REGULARIZACAO", "Em regularização"
    REGULARIZED = "REGULARIZADA", "Regularizada"
    CLOSED = "ENCERRADA", "Encerrada"


class BlockingLevel(models.TextChoices):
    INFORMATIONAL = "INFORMATIVA", "Informativa"
    NON_BLOCKING = "NAO_BLOQUEANTE", "Não bloqueante"
    BLOCKING = "BLOQUEANTE", "Bloqueante"


class ImmutableOperationalQuerySet(models.QuerySet[Any]):
    def update(self, **kwargs: Any) -> int:
        raise ValidationError("Pendências devem ser alteradas por services auditados.")

    def delete(self) -> tuple[int, dict[str, int]]:
        raise ValidationError("O histórico de pendências não pode ser excluído.")


class PendingItem(models.Model):
    uuid = models.UUIDField("UUID", default=uuid.uuid4, unique=True, editable=False)
    process = models.ForeignKey(
        "offboarding.OffboardingProcess",
        verbose_name="processo",
        on_delete=models.PROTECT,
        related_name="pending_items",
    )
    task = models.ForeignKey(
        "offboarding.ProcessSectorTask",
        verbose_name="tarefa",
        on_delete=models.PROTECT,
        related_name="pending_items",
    )
    checklist_item = models.ForeignKey(
        "offboarding.ProcessChecklistItem",
        verbose_name="item de checklist",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="pending_items",
    )
    category = models.CharField("categoria", max_length=20, choices=PendingCategory.choices)
    title = models.CharField("título", max_length=200)
    description = models.TextField("descrição")
    status = models.CharField(
        "situação",
        max_length=24,
        choices=PendingStatus.choices,
        default=PendingStatus.OPEN,
    )
    blocking_level = models.CharField(
        "classificação de bloqueio",
        max_length=20,
        choices=BlockingLevel.choices,
        default=BlockingLevel.BLOCKING,
    )
    identified_at = models.DateTimeField("identificada em", auto_now_add=True)
    regularization_due_at = models.DateTimeField(
        "limite de regularização",
        null=True,
        blank=True,
    )
    registered_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name="registrada por",
        on_delete=models.PROTECT,
        related_name="pending_items_registered",
    )
    updated_at = models.DateTimeField("atualizada em", auto_now=True)
    version = models.PositiveIntegerField("versão de concorrência", default=1)

    objects = ImmutableOperationalQuerySet.as_manager()

    class Meta:
        db_table = "SGPD_PENDING_ITEM"
        ordering = ("-identified_at", "-id")
        constraints = [
            models.CheckConstraint(
                condition=models.Q(version__gt=0),
                name="SGPD_CK_PENDING_VERSION",
            ),
        ]
        indexes = [
            models.Index(
                fields=("process", "status", "blocking_level"),
                name="SGPD_IX_PEND_PROC_STATUS",
            ),
            models.Index(
                fields=("task", "status"),
                name="SGPD_IX_PEND_TASK_STATUS",
            ),
        ]

    def clean(self) -> None:
        super().clean()
        self.title = self.title.strip()
        self.description = self.description.strip()
        if not self.title:
            raise ValidationError({"title": "O título da pendência é obrigatório."})
        if not self.description:
            raise ValidationError({"description": "A descrição da pendência é obrigatória."})
        if self.task_id and self.process_id and self.task.process_id != self.process_id:
            raise ValidationError({"task": "A tarefa não pertence ao processo informado."})
        checklist_item = self.checklist_item if self.checklist_item_id else None
        if checklist_item is not None and checklist_item.task_id != self.task_id:
            raise ValidationError(
                {"checklist_item": "O item de checklist não pertence à tarefa informada."}
            )

    def delete(self, *args: Any, **kwargs: Any) -> tuple[int, dict[str, int]]:
        raise ValidationError("Pendências não podem ser excluídas.")


class PendingItemLine(models.Model):
    pending_item = models.ForeignKey(
        PendingItem,
        verbose_name="pendência",
        on_delete=models.PROTECT,
        related_name="items",
    )
    code = models.CharField("código do item", max_length=80, blank=True)
    description = models.CharField("descrição", max_length=500)
    asset_tag = models.CharField("patrimônio", max_length=100, blank=True)
    serial_number = models.CharField("número de série", max_length=120, blank=True)
    quantity = models.DecimalField("quantidade", max_digits=12, decimal_places=3, default=1)
    unit = models.CharField("unidade", max_length=30, default="UN")
    item_condition = models.CharField("estado do item", max_length=120, blank=True)
    extra_data = models.JSONField("dados adicionais", default=dict, blank=True)

    objects = ImmutableOperationalQuerySet.as_manager()

    class Meta:
        db_table = "SGPD_PENDING_ITEM_LINE"
        ordering = ("pending_item_id", "id")
        constraints = [
            models.CheckConstraint(
                condition=models.Q(quantity__gt=0),
                name="SGPD_CK_PEND_LINE_QTY",
            ),
        ]

    def clean(self) -> None:
        super().clean()
        self.code = self.code.strip()
        self.description = self.description.strip()
        self.asset_tag = self.asset_tag.strip()
        self.serial_number = self.serial_number.strip()
        self.unit = self.unit.strip().upper()
        self.item_condition = self.item_condition.strip()
        if not self.description:
            raise ValidationError({"description": "A descrição do item é obrigatória."})
        if not self.unit:
            raise ValidationError({"unit": "A unidade do item é obrigatória."})

    def delete(self, *args: Any, **kwargs: Any) -> tuple[int, dict[str, int]]:
        raise ValidationError("Itens de pendência não podem ser excluídos.")


class PendingComment(models.Model):
    pending_item = models.ForeignKey(
        PendingItem,
        verbose_name="pendência",
        on_delete=models.PROTECT,
        related_name="comments",
    )
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name="autor",
        on_delete=models.PROTECT,
        related_name="pending_comments_authored",
    )
    text = models.TextField("comentário")
    created_at = models.DateTimeField("criado em", auto_now_add=True)

    objects = ImmutableOperationalQuerySet.as_manager()

    class Meta:
        db_table = "SGPD_PENDING_COMMENT"
        ordering = ("created_at", "id")

    def save(self, *args: Any, **kwargs: Any) -> None:
        if self.pk is not None:
            raise ValidationError("Comentários de pendência são imutáveis.")
        super().save(*args, **kwargs)

    def delete(self, *args: Any, **kwargs: Any) -> tuple[int, dict[str, int]]:
        raise ValidationError("Comentários de pendência não podem ser excluídos.")

    def clean(self) -> None:
        super().clean()
        self.text = self.text.strip()
        if not self.text:
            raise ValidationError({"comment": "O comentário é obrigatório."})
