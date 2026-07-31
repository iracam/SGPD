"""Offboarding drafts, immutable employee snapshots and append-only history."""

from __future__ import annotations

import uuid
from typing import Any

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models


class ProcessStatus(models.TextChoices):
    """Estado **formal** do processo: o que alguém decidiu, com data e ator.

    A situação funcional — em validação, com pendências, aguardando decisão,
    pronto para o DP — não mora aqui: é calculada na leitura sobre tarefas,
    pendências e pretensões, pela ADR-051.
    """

    DRAFT = "RASCUNHO", "Rascunho"
    STARTED = "INICIADO", "Iniciado"
    RELEASED = "LIBERADO_PARA_RESCISAO", "Liberado para rescisão"
    PROCESSED = "RESCISAO_PROCESSADA", "Rescisão processada"
    CLOSED = "ENCERRADO", "Encerrado"
    CANCELLED = "CANCELADO", "Cancelado"


#: Estados em que o processo já foi iniciado e, portanto, exige data e ator de
#: início. `CANCELADO` fica fora porque o rascunho também pode ser cancelado.
STARTED_PROCESS_STATUSES = (
    ProcessStatus.STARTED,
    ProcessStatus.RELEASED,
    ProcessStatus.PROCESSED,
    ProcessStatus.CLOSED,
)

#: Estados que encerram o ciclo e liberam a chave do colaborador.
TERMINAL_PROCESS_STATUSES = (ProcessStatus.CLOSED, ProcessStatus.CANCELLED)

#: Estados que ainda não receberam nenhuma marca formal da Fase 8.
UNRELEASED_PROCESS_STATUSES = (
    ProcessStatus.DRAFT,
    ProcessStatus.STARTED,
    ProcessStatus.CANCELLED,
)


class ProcessEventType(models.TextChoices):
    OPENED = "PROCESS_OPENED", "Processo aberto"
    DRAFT_SELECTION_UPDATED = "DRAFT_SELECTION_UPDATED", "Seleção do rascunho alterada"
    STARTED = "PROCESS_STARTED", "Processo iniciado"
    SECTOR_TASK_STARTED = "SECTOR_TASK_STARTED", "Tarefa de setor iniciada"
    SECTOR_TASK_COMPLETED = "SECTOR_TASK_COMPLETED", "Tarefa de setor concluída"
    SECTOR_TASK_CANCELLED = "SECTOR_TASK_CANCELLED", "Tarefa de setor cancelada"
    SECTOR_TASK_REOPENED = "SECTOR_TASK_REOPENED", "Tarefa de setor reaberta"
    RELEASED = "PROCESS_RELEASED", "Processo liberado para rescisão"
    PROCESSING_REGISTERED = "PROCESSING_REGISTERED", "Processamento da rescisão registrado"
    CLOSED = "PROCESS_CLOSED", "Processo encerrado"
    CANCELLED = "PROCESS_CANCELLED", "Processo cancelado"
    REOPENED = "PROCESS_REOPENED", "Processo reaberto"
    PENDING_CREATED = "PENDING_CREATED", "Pendência criada"
    PENDING_COMMENTED = "PENDING_COMMENTED", "Pendência comentada"
    PENDING_STATUS_CHANGED = "PENDING_STATUS_CHANGED", "Situação da pendência alterada"
    PENDING_AMOUNT_INFORMED = "PENDING_AMOUNT_INFORMED", "Valor informado"
    PENDING_AMOUNT_ASSESSED = "PENDING_AMOUNT_ASSESSED", "Valor apurado"
    PENDING_AMOUNT_CONTESTED = "PENDING_AMOUNT_CONTESTED", "Valor contestado"
    PENDING_AMOUNT_DECIDED = "PENDING_AMOUNT_DECIDED", "Valor decidido"
    NOTIFICATION_REPROCESSED = "NOTIFICATION_REPROCESSED", "Notificação reprocessada"
    EVIDENCE_UPLOADED = "EVIDENCE_UPLOADED", "Evidência enviada"
    EVIDENCE_DOWNLOADED = "EVIDENCE_DOWNLOADED", "Evidência baixada"


class DraftOverrideAction(models.TextChoices):
    INCLUDE = "INCLUDE", "Incluir"
    EXCLUDE = "EXCLUDE", "Remover"


class SectorTaskStatus(models.TextChoices):
    PENDING = "PENDENTE", "Pendente"
    IN_ANALYSIS = "EM_ANALISE", "Em análise"
    COMPLETED = "CONCLUIDA", "Concluída"
    CANCELLED = "CANCELADA", "Cancelada"


#: Situações em que a tarefa ainda espera trabalho do setor.
OPEN_TASK_STATUSES = (SectorTaskStatus.PENDING, SectorTaskStatus.IN_ANALYSIS)


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
    opened_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name="aberto por",
        on_delete=models.PROTECT,
        related_name="opened_offboarding_processes",
        db_index=False,
    )
    opened_at = models.DateTimeField("aberto em", auto_now_add=True)
    started_at = models.DateTimeField("iniciado em", null=True, blank=True)
    started_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name="iniciado por",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="started_offboarding_processes",
    )
    planned_termination_date = models.DateField("data prevista de desligamento")
    due_date = models.DateField("data limite")
    reason = models.TextField("motivo")
    priority = models.CharField("prioridade", max_length=50)
    notes = models.TextField("observações", blank=True)
    released_at = models.DateTimeField("liberado em", null=True, blank=True)
    released_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name="liberado por",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="released_offboarding_processes",
    )
    release_notes = models.CharField("parecer da liberação", max_length=1000, blank=True)
    # Declaração do DP sobre o que foi processado no Senior HCM. O SGPD não lê
    # nem escreve a rescisão (ADR-020, ADR-051): isto é prova de conferência
    # humana, não espelho da fonte oficial.
    termination_reference = models.CharField(
        "número declarado da rescisão",
        max_length=60,
        blank=True,
    )
    termination_processed_on = models.DateField(
        "data declarada do processamento",
        null=True,
        blank=True,
    )
    processing_registered_at = models.DateTimeField(
        "processamento registrado em",
        null=True,
        blank=True,
    )
    processing_registered_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name="processamento registrado por",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="processed_offboarding_processes",
    )
    processing_notes = models.CharField(
        "observação do processamento",
        max_length=1000,
        blank=True,
    )
    closed_at = models.DateTimeField("encerrado em", null=True, blank=True)
    closed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name="encerrado por",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="closed_offboarding_processes",
    )
    closing_notes = models.CharField("observação do encerramento", max_length=1000, blank=True)
    cancelled_at = models.DateTimeField("cancelado em", null=True, blank=True)
    cancelled_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name="cancelado por",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="cancelled_offboarding_processes",
    )
    cancellation_reason = models.CharField(
        "motivo do cancelamento",
        max_length=1000,
        blank=True,
    )
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
                    opened_by__isnull=False,
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
            models.CheckConstraint(
                condition=(
                    models.Q(
                        status=ProcessStatus.DRAFT,
                        started_at__isnull=True,
                        started_by__isnull=True,
                    )
                    | models.Q(
                        status__in=STARTED_PROCESS_STATUSES,
                        started_at__isnull=False,
                        started_by__isnull=False,
                    )
                    # Cancelar alcança tanto o rascunho quanto o iniciado, então
                    # o par de início pode estar ausente ou presente — nunca pela
                    # metade.
                    | models.Q(
                        status=ProcessStatus.CANCELLED,
                        started_at__isnull=True,
                        started_by__isnull=True,
                    )
                    | models.Q(
                        status=ProcessStatus.CANCELLED,
                        started_at__isnull=False,
                        started_by__isnull=False,
                    )
                ),
                name="SGPD_CK_PROCESS_START",
            ),
            models.CheckConstraint(
                condition=(
                    models.Q(
                        status__in=UNRELEASED_PROCESS_STATUSES,
                        released_at__isnull=True,
                        released_by__isnull=True,
                        processing_registered_at__isnull=True,
                        processing_registered_by__isnull=True,
                        closed_at__isnull=True,
                        closed_by__isnull=True,
                    )
                    | models.Q(
                        status=ProcessStatus.RELEASED,
                        released_at__isnull=False,
                        released_by__isnull=False,
                        processing_registered_at__isnull=True,
                        processing_registered_by__isnull=True,
                        closed_at__isnull=True,
                        closed_by__isnull=True,
                    )
                    | models.Q(
                        status=ProcessStatus.PROCESSED,
                        released_at__isnull=False,
                        released_by__isnull=False,
                        processing_registered_at__isnull=False,
                        processing_registered_by__isnull=False,
                        termination_reference__isnull=False,
                        termination_processed_on__isnull=False,
                        closed_at__isnull=True,
                        closed_by__isnull=True,
                    )
                    | models.Q(
                        status=ProcessStatus.CLOSED,
                        released_at__isnull=False,
                        released_by__isnull=False,
                        processing_registered_at__isnull=False,
                        processing_registered_by__isnull=False,
                        closed_at__isnull=False,
                        closed_by__isnull=False,
                    )
                ),
                name="SGPD_CK_PROCESS_FORMAL",
            ),
            models.CheckConstraint(
                # O motivo entra somente no ramo do cancelamento: no Oracle a
                # string vazia é NULL, então exigir ausência dele nos demais
                # estados recusaria toda linha não cancelada no SQLite.
                condition=(
                    models.Q(
                        status__in=(
                            ProcessStatus.DRAFT,
                            *STARTED_PROCESS_STATUSES,
                        ),
                        cancelled_at__isnull=True,
                        cancelled_by__isnull=True,
                    )
                    | models.Q(
                        status=ProcessStatus.CANCELLED,
                        cancelled_at__isnull=False,
                        cancelled_by__isnull=False,
                        cancellation_reason__isnull=False,
                    )
                ),
                name="SGPD_CK_PROCESS_CANCEL",
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
        self.reason = self.reason.strip()
        self.priority = self.priority.strip()
        self.notes = self.notes.strip()
        if not self.reason:
            raise ValidationError({"reason": "O motivo é obrigatório."})
        if not self.priority:
            raise ValidationError({"priority": "A prioridade é obrigatória."})
        self.release_notes = self.release_notes.strip()
        self.processing_notes = self.processing_notes.strip()
        self.closing_notes = self.closing_notes.strip()
        self.cancellation_reason = self.cancellation_reason.strip()
        self.termination_reference = self.termination_reference.strip()
        started_values = (self.started_at is not None, self.started_by_id is not None)
        if any(started_values) and not all(started_values):
            raise ValidationError("O início exige data e ator.")
        if self.status == ProcessStatus.DRAFT and any(started_values):
            raise ValidationError("Um rascunho não pode possuir dados de início.")
        if self.status in STARTED_PROCESS_STATUSES and not all(started_values):
            raise ValidationError("Um processo iniciado exige data e ator.")
        self._clean_formal_marks()

    def _clean_formal_marks(self) -> None:
        """Cada marca formal exige data e ator, e só existe no estado que a produz."""

        marks = {
            "released": (self.released_at is not None, self.released_by_id is not None),
            "processing_registered": (
                self.processing_registered_at is not None,
                self.processing_registered_by_id is not None,
            ),
            "closed": (self.closed_at is not None, self.closed_by_id is not None),
            "cancelled": (self.cancelled_at is not None, self.cancelled_by_id is not None),
        }
        for name, values in marks.items():
            if any(values) and not all(values):
                raise ValidationError(f"A marca formal `{name}` exige data e ator.")
        has_release = all(marks["released"])
        has_processing = all(marks["processing_registered"])
        has_closing = all(marks["closed"])
        has_cancellation = all(marks["cancelled"])

        if self.status in UNRELEASED_PROCESS_STATUSES and (
            has_release or has_processing or has_closing
        ):
            raise ValidationError("O processo não liberado não pode possuir marcas de liberação.")
        if self.status == ProcessStatus.RELEASED and (
            not has_release or has_processing or has_closing
        ):
            raise ValidationError("A liberação exige data e ator e nada além dela.")
        if self.status == ProcessStatus.PROCESSED:
            if not has_release or not has_processing or has_closing:
                raise ValidationError("O processamento exige a liberação anterior e nada além.")
            if not self.termination_reference or self.termination_processed_on is None:
                raise ValidationError(
                    "O processamento exige o número declarado e a data da rescisão."
                )
        if self.status == ProcessStatus.CLOSED and not (
            has_release and has_processing and has_closing
        ):
            raise ValidationError("O encerramento exige liberação e processamento registrados.")
        if self.status == ProcessStatus.CANCELLED:
            if not has_cancellation:
                raise ValidationError("O cancelamento exige data e ator.")
            if not self.cancellation_reason:
                raise ValidationError({"cancellation_reason": "O motivo é obrigatório."})
        elif has_cancellation:
            raise ValidationError("Somente um processo cancelado possui marca de cancelamento.")

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
    branch_legal_name = models.CharField("nome da filial", max_length=255)
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


class ProcessValidationGroup(models.Model):
    process = models.ForeignKey(
        OffboardingProcess,
        verbose_name="processo",
        on_delete=models.PROTECT,
        related_name="selected_groups",
    )
    group_version = models.ForeignKey(
        "templates_engine.ValidationGroupVersion",
        verbose_name="versão do grupo",
        on_delete=models.PROTECT,
        related_name="process_selections",
    )
    selected_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name="selecionado por",
        on_delete=models.PROTECT,
        related_name="offboarding_groups_selected",
    )
    selected_at = models.DateTimeField("selecionado em", auto_now_add=True)

    class Meta:
        db_table = "SGPD_PROCESS_GROUP"
        ordering = ("process_id", "group_version_id")
        verbose_name = "grupo selecionado do processo"
        verbose_name_plural = "grupos selecionados dos processos"
        constraints = [
            models.UniqueConstraint(
                fields=("process", "group_version"),
                name="SGPD_UQ_PROCESS_GROUP",
            ),
        ]


class ProcessSectorOverride(models.Model):
    process = models.ForeignKey(
        OffboardingProcess,
        verbose_name="processo",
        on_delete=models.PROTECT,
        related_name="sector_overrides",
    )
    sector = models.ForeignKey(
        "sectors.ValidationSector",
        verbose_name="setor",
        on_delete=models.PROTECT,
        related_name="process_overrides",
    )
    action = models.CharField(
        "ação",
        max_length=10,
        choices=DraftOverrideAction.choices,
    )
    template_version = models.ForeignKey(
        "templates_engine.ChecklistTemplateVersion",
        verbose_name="versão do template",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="process_overrides",
    )
    is_required = models.BooleanField("obrigatório", default=True)
    blocks_process = models.BooleanField("bloqueia o processo", default=True)
    due_hours_override = models.PositiveIntegerField(
        "prazo específico em horas",
        null=True,
        blank=True,
    )
    reason = models.TextField("justificativa")
    changed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name="alterado por",
        on_delete=models.PROTECT,
        related_name="offboarding_sector_overrides",
    )
    changed_at = models.DateTimeField("alterado em", auto_now_add=True)

    class Meta:
        db_table = "SGPD_PROCESS_SECTOR_OVERRIDE"
        ordering = ("process_id", "sector_id")
        verbose_name = "ajuste manual de setor"
        verbose_name_plural = "ajustes manuais de setores"
        constraints = [
            models.UniqueConstraint(
                fields=("process", "sector"),
                name="SGPD_UQ_PROCESS_OVERRIDE",
            ),
            models.CheckConstraint(
                condition=(
                    models.Q(
                        action=DraftOverrideAction.INCLUDE,
                        template_version__isnull=False,
                    )
                    | models.Q(
                        action=DraftOverrideAction.EXCLUDE,
                        template_version__isnull=True,
                    )
                ),
                name="SGPD_CK_PROCESS_OVERRIDE",
            ),
            models.CheckConstraint(
                condition=(
                    models.Q(due_hours_override__isnull=True) | models.Q(due_hours_override__gt=0)
                ),
                name="SGPD_CK_PROC_OVERRIDE_DUE",
            ),
        ]

    def clean(self) -> None:
        super().clean()
        self.reason = self.reason.strip()
        if not self.reason:
            raise ValidationError({"reason": "A justificativa do ajuste é obrigatória."})
        if self.action == DraftOverrideAction.INCLUDE:
            if self.template_version_id is None:
                raise ValidationError(
                    {"template_version": "A inclusão exige uma versão de template."}
                )
        elif self.template_version_id is not None:
            raise ValidationError({"template_version": "A remoção não deve informar um template."})


class ProcessSectorTask(models.Model):
    process = models.ForeignKey(
        OffboardingProcess,
        verbose_name="processo",
        on_delete=models.PROTECT,
        related_name="sector_tasks",
    )
    sector = models.ForeignKey(
        "sectors.ValidationSector",
        verbose_name="setor",
        on_delete=models.PROTECT,
        related_name="process_tasks",
    )
    template_version = models.ForeignKey(
        "templates_engine.ChecklistTemplateVersion",
        verbose_name="versão do template",
        on_delete=models.PROTECT,
        related_name="process_tasks",
    )
    status = models.CharField(
        "situação",
        max_length=30,
        choices=SectorTaskStatus.choices,
        default=SectorTaskStatus.PENDING,
    )
    is_required = models.BooleanField("obrigatório")
    blocks_process = models.BooleanField("bloqueia o processo")
    sector_code_snapshot = models.CharField("código histórico do setor", max_length=50)
    sector_name_snapshot = models.CharField("nome histórico do setor", max_length=120)
    template_code_snapshot = models.CharField("código histórico do template", max_length=50)
    template_version_snapshot = models.PositiveIntegerField("versão histórica do template")
    sla_hours_snapshot = models.PositiveIntegerField("SLA histórico em horas")
    due_at = models.DateTimeField("data limite")
    started_at = models.DateTimeField("iniciada em")
    completed_at = models.DateTimeField("concluída em", null=True, blank=True)
    completed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name="concluída por",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="offboarding_tasks_completed",
    )
    notes = models.TextField("observações", blank=True)
    version = models.PositiveIntegerField("versão de concorrência", default=1)

    class Meta:
        db_table = "SGPD_PROCESS_SECTOR_TASK"
        ordering = ("process_id", "due_at", "sector_code_snapshot")
        verbose_name = "tarefa de setor"
        verbose_name_plural = "tarefas de setores"
        constraints = [
            models.UniqueConstraint(
                fields=("process", "sector"),
                name="SGPD_UQ_PROCESS_TASK",
            ),
            models.CheckConstraint(
                condition=models.Q(
                    template_version_snapshot__gt=0,
                    sla_hours_snapshot__gt=0,
                    version__gt=0,
                ),
                name="SGPD_CK_PROCESS_TASK_VALUES",
            ),
        ]
        indexes = [
            models.Index(
                fields=("sector", "status", "due_at"),
                name="SGPD_IX_TASK_SECTOR_STATUS",
            ),
            models.Index(
                fields=("process", "status"),
                name="SGPD_IX_TASK_PROCESS_STATUS",
            ),
        ]


class ProcessTaskGroupSource(models.Model):
    task = models.ForeignKey(
        ProcessSectorTask,
        verbose_name="tarefa",
        on_delete=models.PROTECT,
        related_name="group_sources",
    )
    selected_group = models.ForeignKey(
        ProcessValidationGroup,
        verbose_name="grupo selecionado",
        on_delete=models.PROTECT,
        related_name="generated_tasks",
    )

    class Meta:
        db_table = "SGPD_TASK_GROUP_SOURCE"
        ordering = ("task_id", "selected_group_id")
        verbose_name = "origem de grupo da tarefa"
        verbose_name_plural = "origens de grupo das tarefas"
        constraints = [
            models.UniqueConstraint(
                fields=("task", "selected_group"),
                name="SGPD_UQ_TASK_GROUP_SOURCE",
            ),
        ]


class ProcessChecklistItem(models.Model):
    task = models.ForeignKey(
        ProcessSectorTask,
        verbose_name="tarefa",
        on_delete=models.PROTECT,
        related_name="checklist_items",
    )
    source_item = models.ForeignKey(
        "templates_engine.ChecklistTemplateItem",
        verbose_name="item de origem",
        on_delete=models.PROTECT,
        related_name="process_snapshots",
    )
    code_snapshot = models.CharField("código histórico", max_length=50)
    question_snapshot = models.TextField("pergunta histórica")
    response_type_snapshot = models.CharField("tipo histórico de resposta", max_length=20)
    is_required = models.BooleanField("obrigatório")
    blocks_process = models.BooleanField("bloqueia o processo")
    requires_evidence = models.BooleanField("exige evidência")
    allows_pending = models.BooleanField("permite pendência")
    display_order = models.PositiveIntegerField("ordem de exibição")
    config_snapshot = models.JSONField("configuração histórica", default=dict)
    response = models.JSONField("resposta", null=True, blank=True)
    answered_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name="respondido por",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="offboarding_checklist_answers",
    )
    answered_at = models.DateTimeField("respondido em", null=True, blank=True)

    class Meta:
        db_table = "SGPD_PROCESS_CHECKLIST_ITEM"
        ordering = ("task_id", "display_order", "id")
        verbose_name = "item de checklist do processo"
        verbose_name_plural = "itens de checklist dos processos"
        constraints = [
            models.UniqueConstraint(
                fields=("task", "source_item"),
                name="SGPD_UQ_PROCESS_ITEM_SOURCE",
            ),
            models.UniqueConstraint(
                fields=("task", "display_order"),
                name="SGPD_UQ_PROCESS_ITEM_ORDER",
            ),
            models.CheckConstraint(
                condition=models.Q(display_order__gt=0),
                name="SGPD_CK_PROCESS_ITEM_ORDER",
            ),
        ]


class ProcessActionIdempotency(models.Model):
    process = models.ForeignKey(
        OffboardingProcess,
        verbose_name="processo",
        on_delete=models.PROTECT,
        related_name="idempotency_records",
    )
    action = models.CharField("ação", max_length=30)
    idempotency_key = models.CharField("chave de idempotência", max_length=100)
    request_hash = models.CharField("hash da requisição", max_length=64)
    response = models.JSONField("resposta", default=dict)
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name="ator",
        on_delete=models.PROTECT,
        related_name="offboarding_idempotent_actions",
    )
    completed_at = models.DateTimeField("concluída em", auto_now_add=True)

    class Meta:
        db_table = "SGPD_PROCESS_IDEMPOTENCY"
        ordering = ("-completed_at", "-id")
        verbose_name = "registro de idempotência do processo"
        verbose_name_plural = "registros de idempotência dos processos"
        constraints = [
            models.UniqueConstraint(
                fields=("process", "action", "idempotency_key"),
                name="SGPD_UQ_PROCESS_IDEMPOTENCY",
            ),
        ]


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
