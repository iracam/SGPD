"""Private evidence metadata stored in Oracle; file bytes remain outside it."""

from __future__ import annotations

import uuid
from pathlib import Path
from typing import Any

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models

from apps.core.db import PurgeableQuerySet

from .storage import evidence_storage


class EvidenceClassification(models.TextChoices):
    INTERNAL = "INTERNA", "Interna"
    RESTRICTED = "RESTRITA", "Restrita"
    SENSITIVE = "SENSIVEL", "Sensível"


def evidence_upload_to(instance: Evidence, filename: str) -> str:
    suffix = Path(filename).suffix.lower()
    return f"{instance.uuid.hex[:2]}/{instance.uuid.hex}{suffix}"


class EvidenceQuerySet(PurgeableQuerySet["Evidence"]):
    def update(self, **kwargs: Any) -> int:
        raise ValidationError("Evidências devem ser alteradas por services auditados.")

    def delete(self) -> tuple[int, dict[str, int]]:
        raise ValidationError("Evidências não podem ser excluídas.")


class Evidence(models.Model):
    uuid = models.UUIDField("UUID", default=uuid.uuid4, unique=True, editable=False)
    process = models.ForeignKey(
        "offboarding.OffboardingProcess",
        verbose_name="processo",
        on_delete=models.PROTECT,
        related_name="evidences",
    )
    task = models.ForeignKey(
        "offboarding.ProcessSectorTask",
        verbose_name="tarefa",
        on_delete=models.PROTECT,
        related_name="evidences",
    )
    pending_item = models.ForeignKey(
        "pending_items.PendingItem",
        verbose_name="pendência",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="evidences",
    )
    checklist_item = models.ForeignKey(
        "offboarding.ProcessChecklistItem",
        verbose_name="item de checklist",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="evidences",
    )
    file = models.FileField(
        "arquivo privado",
        storage=evidence_storage,
        upload_to=evidence_upload_to,
        max_length=255,
    )
    original_name = models.CharField("nome original", max_length=255)
    mime_type = models.CharField("MIME type", max_length=120)
    size_bytes = models.PositiveBigIntegerField("tamanho em bytes")
    sha256 = models.CharField("hash SHA-256", max_length=64)
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name="enviada por",
        on_delete=models.PROTECT,
        related_name="evidences_uploaded",
    )
    uploaded_at = models.DateTimeField("enviada em", auto_now_add=True)
    classification = models.CharField(
        "classificação",
        max_length=12,
        choices=EvidenceClassification.choices,
        default=EvidenceClassification.RESTRICTED,
    )
    is_active = models.BooleanField("ativa", default=True)

    objects = EvidenceQuerySet.as_manager()

    class Meta:
        db_table = "SGPD_EVIDENCE"
        ordering = ("-uploaded_at", "-id")
        constraints = [
            models.CheckConstraint(
                condition=models.Q(size_bytes__gt=0),
                name="SGPD_CK_EVIDENCE_SIZE",
            ),
        ]
        indexes = [
            models.Index(fields=("process", "uploaded_at"), name="SGPD_IX_EVID_PROC_DATE"),
            models.Index(fields=("task", "uploaded_at"), name="SGPD_IX_EVID_TASK_DATE"),
            models.Index(fields=("sha256",), name="SGPD_IX_EVID_SHA256"),
        ]

    def clean(self) -> None:
        super().clean()
        self.original_name = Path(self.original_name).name.strip()
        self.mime_type = self.mime_type.strip().lower()
        if not self.original_name:
            raise ValidationError({"file": "O nome original do arquivo é obrigatório."})
        if self.task_id and self.process_id and self.task.process_id != self.process_id:
            raise ValidationError({"task": "A tarefa não pertence ao processo informado."})
        pending_item = self.pending_item if self.pending_item_id else None
        if pending_item is not None and pending_item.task_id != self.task_id:
            raise ValidationError({"pending_item": "A pendência não pertence à tarefa informada."})
        checklist_item = self.checklist_item if self.checklist_item_id else None
        if checklist_item is not None and checklist_item.task_id != self.task_id:
            raise ValidationError(
                {"checklist_item": "O item de checklist não pertence à tarefa informada."}
            )

    def delete(self, *args: Any, **kwargs: Any) -> tuple[int, dict[str, int]]:
        raise ValidationError("Evidências não podem ser excluídas.")
