"""Offboarding drafts, immutable employee snapshots and append-only history."""

from __future__ import annotations

import uuid
from typing import Any

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models


class ProcessStatus(models.TextChoices):
    DRAFT = "RASCUNHO", "Rascunho"


class ProcessEventType(models.TextChoices):
    OPENED = "PROCESS_OPENED", "Processo aberto"


class OffboardingProcessQuerySet(models.QuerySet["OffboardingProcess"]):
    def update(self, **kwargs: Any) -> int:
        raise ValidationError("Processos devem ser alterados por services auditados.")

    def delete(self) -> tuple[int, dict[str, int]]:
        raise ValidationError("Processos demissionais não podem ser excluídos.")


class OffboardingProcess(models.Model):
    uuid = models.UUIDField("UUID", default=uuid.uuid4, unique=True, editable=False)
    status = models.CharField(
        "situação",
        max_length=30,
        choices=ProcessStatus.choices,
        default=ProcessStatus.DRAFT,
    )
    company_code = models.PositiveIntegerField("código da empresa")
    branch_code = models.PositiveIntegerField("código da filial")
    employee_type_code = models.PositiveIntegerField("tipo de colaborador")
    employee_registration = models.PositiveIntegerField("matrícula")
    active_employee_key = models.CharField(
        "chave do processo ativo",
        max_length=100,
        null=True,
        blank=True,
        unique=True,
        editable=False,
    )
    manager = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name="gestor imediato",
        on_delete=models.PROTECT,
        related_name="managed_offboarding_processes",
    )
    manager_name_snapshot = models.CharField("nome histórico do gestor", max_length=301)
    manager_email_snapshot = models.EmailField("e-mail histórico do gestor")
    opened_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name="aberto por",
        on_delete=models.PROTECT,
        related_name="opened_offboarding_processes",
        db_index=False,
    )
    opened_at = models.DateTimeField("aberto em", auto_now_add=True)
    planned_termination_date = models.DateField("data prevista de desligamento")
    due_date = models.DateField("data limite")
    reason = models.TextField("motivo")
    priority = models.CharField("prioridade", max_length=50)
    notes = models.TextField("observações", blank=True)
    version = models.PositiveIntegerField("versão de concorrência", default=1)

    objects = OffboardingProcessQuerySet.as_manager()

    class Meta:
        db_table = "SGPD_OFFBOARDING_PROCESS"
        ordering = ("-opened_at", "-id")
        verbose_name = "processo demissional"
        verbose_name_plural = "processos demissionais"
        constraints = [
            models.CheckConstraint(
                condition=models.Q(
                    status__isnull=False,
                    company_code__gt=0,
                    branch_code__gt=0,
                    employee_type_code__gt=0,
                    employee_registration__gt=0,
                    manager__isnull=False,
                    opened_by__isnull=False,
                    manager_name_snapshot__isnull=False,
                    manager_email_snapshot__isnull=False,
                    planned_termination_date__isnull=False,
                    due_date__isnull=False,
                    reason__isnull=False,
                    priority__isnull=False,
                ),
                name="SGPD_CK_PROCESS_REQUIRED",
            ),
            models.CheckConstraint(
                condition=models.Q(version__gt=0),
                name="SGPD_CK_PROCESS_VERSION",
            ),
        ]
        indexes = [
            models.Index(
                fields=("status", "due_date"),
                name="SGPD_IX_PROCESS_STATUS_DUE",
            ),
            models.Index(
                fields=(
                    "company_code",
                    "branch_code",
                    "employee_type_code",
                    "employee_registration",
                    "opened_at",
                ),
                name="SGPD_IX_PROCESS_EMP_OPEN",
            ),
            models.Index(
                fields=("opened_by", "opened_at"),
                name="SGPD_IX_PROCESS_OPENED_BY",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.uuid} / {self.employee_registration} / {self.status}"

    def clean(self) -> None:
        super().clean()
        self.manager_name_snapshot = self.manager_name_snapshot.strip()
        self.manager_email_snapshot = self.manager_email_snapshot.strip().lower()
        self.reason = self.reason.strip()
        self.priority = self.priority.strip()
        self.notes = self.notes.strip()
        if not self.manager_name_snapshot:
            raise ValidationError(
                {"manager_user_id": "O gestor precisa possuir nome completo cadastrado."}
            )
        if not self.manager_email_snapshot:
            raise ValidationError(
                {"manager_user_id": "O gestor precisa possuir e-mail cadastrado."}
            )
        if not self.reason:
            raise ValidationError({"reason": "O motivo é obrigatório."})
        if not self.priority:
            raise ValidationError({"priority": "A prioridade é obrigatória."})

    def delete(self, *args: Any, **kwargs: Any) -> tuple[int, dict[str, int]]:
        raise ValidationError("Processos demissionais não podem ser excluídos.")


class EmployeeSnapshotQuerySet(models.QuerySet["EmployeeSnapshot"]):
    def update(self, **kwargs: Any) -> int:
        raise ValidationError("O snapshot do colaborador é imutável.")

    def delete(self) -> tuple[int, dict[str, int]]:
        raise ValidationError("O snapshot do colaborador não pode ser excluído.")


class EmployeeSnapshot(models.Model):
    process = models.OneToOneField(
        OffboardingProcess,
        verbose_name="processo",
        on_delete=models.PROTECT,
        related_name="employee_snapshot",
    )
    company_code = models.PositiveIntegerField("código da empresa")
    branch_code = models.PositiveIntegerField("código da filial")
    branch_legal_name = models.CharField("razão social da filial", max_length=255)
    employee_type_code = models.PositiveIntegerField("tipo de colaborador")
    employee_type_description = models.CharField(
        "descrição do tipo de colaborador",
        max_length=255,
    )
    registration = models.PositiveIntegerField("matrícula")
    employee_name = models.CharField("nome do colaborador", max_length=255)
    masked_cpf = models.CharField(  # noqa: DJ001
        "CPF mascarado",
        max_length=20,
        null=True,
        blank=True,
    )
    admission_date = models.DateField("data de admissão")
    leave_code = models.PositiveIntegerField("código da situação")
    leave_description = models.CharField("descrição da situação", max_length=255)
    leave_date = models.DateField("data de afastamento", null=True, blank=True)
    job_structure_code = models.PositiveIntegerField("estrutura de cargos")
    job_code = models.CharField("código do cargo", max_length=50)
    job_description = models.CharField("descrição do cargo", max_length=255)
    cost_center_code = models.CharField("código do centro de custo", max_length=50)
    cost_center_description = models.CharField(  # noqa: DJ001
        "descrição do centro de custo",
        max_length=255,
        null=True,
        blank=True,
    )
    source_updated_at = models.DateTimeField(
        "origem atualizada em",
        null=True,
        blank=True,
    )
    source_queried_at = models.DateTimeField("origem consultada em")
    created_at = models.DateTimeField("criado em", auto_now_add=True)

    objects = EmployeeSnapshotQuerySet.as_manager()

    class Meta:
        db_table = "SGPD_EMPLOYEE_SNAPSHOT"
        verbose_name = "snapshot do colaborador"
        verbose_name_plural = "snapshots dos colaboradores"
        constraints = [
            models.CheckConstraint(
                condition=models.Q(
                    process__isnull=False,
                    company_code__gt=0,
                    branch_code__gt=0,
                    employee_type_code__gt=0,
                    registration__gt=0,
                    branch_legal_name__isnull=False,
                    employee_type_description__isnull=False,
                    employee_name__isnull=False,
                    admission_date__isnull=False,
                    leave_code__gt=0,
                    leave_description__isnull=False,
                    job_structure_code__gt=0,
                    job_code__isnull=False,
                    job_description__isnull=False,
                    cost_center_code__isnull=False,
                    source_queried_at__isnull=False,
                ),
                name="SGPD_CK_SNAPSHOT_REQUIRED",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.process.uuid} / {self.registration} / {self.employee_name}"

    def save(self, *args: Any, **kwargs: Any) -> None:
        if self.pk is not None:
            raise ValidationError("O snapshot do colaborador é imutável.")
        super().save(*args, **kwargs)

    def delete(self, *args: Any, **kwargs: Any) -> tuple[int, dict[str, int]]:
        raise ValidationError("O snapshot do colaborador não pode ser excluído.")


class ProcessAuditEventQuerySet(models.QuerySet["ProcessAuditEvent"]):
    def update(self, **kwargs: Any) -> int:
        raise ValidationError("Eventos do processo são imutáveis.")

    def delete(self) -> tuple[int, dict[str, int]]:
        raise ValidationError("Eventos do processo não podem ser excluídos.")


class ProcessAuditEvent(models.Model):
    uuid = models.UUIDField("UUID", default=uuid.uuid4, unique=True, editable=False)
    process = models.ForeignKey(
        OffboardingProcess,
        verbose_name="processo",
        on_delete=models.PROTECT,
        related_name="audit_events",
        db_index=False,
    )
    event_type = models.CharField(
        "tipo do evento",
        max_length=30,
        choices=ProcessEventType.choices,
    )
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name="ator",
        on_delete=models.PROTECT,
        related_name="offboarding_events_performed",
    )
    occurred_at = models.DateTimeField("ocorrido em", auto_now_add=True)
    description = models.TextField("descrição")
    data = models.JSONField("dados", default=dict)
    correlation_id = models.CharField("correlation ID", max_length=64, default="-")

    objects = ProcessAuditEventQuerySet.as_manager()

    class Meta:
        db_table = "SGPD_PROCESS_AUDIT"
        ordering = ("-occurred_at", "-id")
        verbose_name = "evento de processo"
        verbose_name_plural = "eventos de processos"
        constraints = [
            models.CheckConstraint(
                condition=models.Q(
                    process__isnull=False,
                    event_type__isnull=False,
                    actor__isnull=False,
                    description__isnull=False,
                    correlation_id__isnull=False,
                ),
                name="SGPD_CK_PROCESS_AUDIT_REQ",
            ),
        ]
        indexes = [
            models.Index(
                fields=("process", "occurred_at"),
                name="SGPD_IX_PROCESS_AUDIT_PROC",
            ),
            models.Index(
                fields=("correlation_id",),
                name="SGPD_IX_PROCESS_AUDIT_CORR",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.event_type} / {self.process.uuid}"

    def save(self, *args: Any, **kwargs: Any) -> None:
        if self.pk is not None:
            raise ValidationError("Eventos do processo são imutáveis.")
        super().save(*args, **kwargs)

    def delete(self, *args: Any, **kwargs: Any) -> tuple[int, dict[str, int]]:
        raise ValidationError("Eventos do processo não podem ser excluídos.")
