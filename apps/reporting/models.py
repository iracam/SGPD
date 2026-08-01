"""Trilha das exportações (RF-036, `SECURITY.md` §6).

O app é de leitura; esta é a única tabela que ele possui, e existe por um
motivo só: exportar leva dado pessoal para fora do sistema, e a LGPD exige
auditoria de acesso. Vale a mesma regra do download de evidência — o ato é
registrado antes de o arquivo sair.

A trilha é append-only, como as demais do projeto: não se altera nem se apaga.
"""

from __future__ import annotations

import uuid
from typing import Any

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models


class ExportDataset(models.TextChoices):
    PROCESSES = "PROCESSOS", "Processos"
    TASKS = "TAREFAS", "Tarefas de setor"
    PENDING_ITEMS = "PENDENCIAS", "Pendências e valores"


class ReportExportQuerySet(models.QuerySet["ReportExport"]):
    def update(self, **kwargs: Any) -> int:
        raise ValidationError("A trilha de exportações é imutável.")

    def delete(self) -> tuple[int, dict[str, int]]:
        raise ValidationError("A trilha de exportações não pode ser excluída.")


class ReportExport(models.Model):
    uuid = models.UUIDField("UUID", default=uuid.uuid4, unique=True, editable=False)
    dataset = models.CharField("conjunto", max_length=20, choices=ExportDataset.choices)
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name="ator",
        on_delete=models.PROTECT,
        related_name="report_exports",
        # `SGPD_IX_EXPORT_ACTOR` já lidera por ator; o índice automático da FK
        # seria redundante no Oracle, como na fila de notificações.
        db_index=False,
    )
    period_start = models.DateField("início do período")
    period_end = models.DateField("fim do período")
    row_count = models.PositiveIntegerField("linhas exportadas")
    exported_at = models.DateTimeField("exportado em", auto_now_add=True)
    correlation_id = models.CharField("correlation ID", max_length=64, default="-")

    objects = ReportExportQuerySet.as_manager()

    class Meta:
        db_table = "SGPD_REPORT_EXPORT"
        ordering = ("-exported_at", "-id")
        verbose_name = "exportação de relatório"
        verbose_name_plural = "exportações de relatórios"
        constraints = [
            models.CheckConstraint(
                condition=models.Q(period_start__lte=models.F("period_end")),
                name="SGPD_CK_EXPORT_PERIOD",
            ),
            # No Oracle a string vazia é gravada como NULL: sem esta condição,
            # conjunto em branco passaria pela coluna `NOT NULL` que o Django
            # nem chega a criar.
            models.CheckConstraint(
                condition=models.Q(dataset__isnull=False, correlation_id__isnull=False),
                name="SGPD_CK_EXPORT_REQUIRED",
            ),
        ]
        indexes = [
            models.Index(fields=("actor", "exported_at"), name="SGPD_IX_EXPORT_ACTOR"),
        ]

    def __str__(self) -> str:
        return f"{self.dataset} / {self.actor_id} / {self.row_count}"

    def save(self, *args: Any, **kwargs: Any) -> None:
        if self.pk is not None:
            raise ValidationError("A trilha de exportações é imutável.")
        super().save(*args, **kwargs)

    def delete(self, *args: Any, **kwargs: Any) -> tuple[int, dict[str, int]]:
        raise ValidationError("A trilha de exportações não pode ser excluída.")
