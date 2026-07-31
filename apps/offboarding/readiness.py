"""Situação funcional e prontidão do processo, calculadas na leitura (ADR-051).

Nada aqui grava: a situação funcional não é transição nem estado persistido. O
que bloqueia a liberação é a lista de impedimentos, refeita sob lock dentro do
service que libera — nenhuma tela pode liberar com base no que leu antes.
"""

from __future__ import annotations

from dataclasses import dataclass

from django.db import models

from apps.pending_items.models import (
    DECIDED_STATUSES,
    BlockingLevel,
    PendingAmount,
    PendingCategory,
    PendingItem,
    PendingStatus,
    unresolved_blocking_q,
)
from apps.templates_engine.models import ChecklistResponseType

from .models import (
    OPEN_TASK_STATUSES,
    OffboardingProcess,
    ProcessChecklistItem,
    ProcessSectorTask,
    ProcessStatus,
    SectorTaskStatus,
)


class ProcessSituation(models.TextChoices):
    """Onde o trabalho está, em oposição ao que já foi decidido.

    Os cinco primeiros valores são os estados derivados do `WORKFLOWS.md` §2 que
    a ADR-051 decidiu não persistir; os demais espelham o estado formal, para
    que a leitura tenha sempre uma única resposta.
    """

    DRAFT = "RASCUNHO", "Rascunho"
    IN_VALIDATION = "EM_VALIDACAO", "Em validação"
    WITH_PENDING_ITEMS = "COM_PENDENCIAS", "Com pendências"
    AWAITING_REGULARIZATION = "AGUARDANDO_REGULARIZACAO", "Aguardando regularização"
    AWAITING_DECISION = "AGUARDANDO_DECISAO", "Aguardando decisão"
    READY_FOR_REVIEW = "PRONTO_PARA_ANALISE_DP", "Pronto para análise do DP"
    RELEASED = "LIBERADO_PARA_RESCISAO", "Liberado para rescisão"
    PROCESSED = "RESCISAO_PROCESSADA", "Rescisão processada"
    CLOSED = "ENCERRADO", "Encerrado"
    CANCELLED = "CANCELADO", "Cancelado"


_FORMAL_SITUATION: dict[str, ProcessSituation] = {
    ProcessStatus.DRAFT: ProcessSituation.DRAFT,
    ProcessStatus.RELEASED: ProcessSituation.RELEASED,
    ProcessStatus.PROCESSED: ProcessSituation.PROCESSED,
    ProcessStatus.CLOSED: ProcessSituation.CLOSED,
    ProcessStatus.CANCELLED: ProcessSituation.CANCELLED,
}


#: Situações em que a pendência ainda está em curso. O encerramento formal exige
#: que nenhuma delas reste (`WORKFLOWS.md` §5): regularizada, decidida ou
#: encerrada, sim; em curso, não.
UNFINISHED_PENDING_STATUSES = frozenset(
    {
        PendingStatus.OPEN,
        PendingStatus.IN_REGULARIZATION,
        PendingStatus.SUBMITTED_FOR_REVIEW,
        PendingStatus.CONTESTED,
    }
)


@dataclass(frozen=True, slots=True)
class ProcessReadiness:
    """Leitura de prontidão: o que impede, o que apenas avisa e a contagem."""

    process: OffboardingProcess
    situation: str
    #: Impedimentos da liberação (RF-030). Vazio não significa liberado.
    blockers: tuple[str, ...]
    #: O que merece conferência mas não impede a liberação.
    warnings: tuple[str, ...]
    task_count: int
    required_task_count: int
    completed_task_count: int
    open_task_count: int
    blocking_pending_count: int
    open_pending_count: int
    undecided_amount_count: int

    @property
    def is_ready(self) -> bool:
        return not self.blockers


def _locked[M: models.Model](queryset: models.QuerySet[M], *, lock: bool) -> list[M]:
    # Sem paginação: o Oracle não combina FOR UPDATE com FETCH FIRST.
    if lock:
        queryset = queryset.select_for_update()
    return list(queryset.order_by("pk"))


def _checklist_inconsistencies(process: OffboardingProcess) -> list[str]:
    """Item obrigatório sem resposta ou sem evidência em tarefa já concluída.

    A conclusão valida isso, então uma ocorrência aqui significa que o dado
    mudou depois — é a “inconsistência crítica” do RF-030, não rotina.
    """

    from apps.evidence.models import Evidence

    items = list(
        ProcessChecklistItem.objects.filter(
            task__process=process,
            task__status=SectorTaskStatus.COMPLETED,
        )
        .filter(models.Q(is_required=True) | models.Q(requires_evidence=True))
        .select_related("task")
        .order_by("task__sector_code_snapshot", "display_order", "pk")
    )
    if not items:
        return []
    with_evidence = set(
        Evidence.objects.filter(
            checklist_item_id__in=[item.pk for item in items],
            is_active=True,
        ).values_list("checklist_item_id", flat=True)
    )
    problems: list[str] = []
    for item in items:
        is_file = item.response_type_snapshot == ChecklistResponseType.FILE
        answered = item.response is not None
        if item.is_required and not is_file and not answered:
            problems.append(
                f"O item obrigatório {item.code_snapshot} de {item.task.sector_name_snapshot} "
                "está sem resposta."
            )
        # A régua é a mesma de `_validated_answers`, e precisa ser: aqui se
        # procura divergência do que a conclusão validou, não uma exigência
        # própria. Item `FILE` só exige arquivo quando obrigatório; item comum
        # só exige evidência quando obrigatório ou efetivamente respondido —
        # item opcional deixado em branco é omissão legítima do setor, não
        # inconsistência.
        if is_file:
            needs_evidence = item.is_required
        else:
            needs_evidence = item.requires_evidence and (item.is_required or answered)
        if needs_evidence and item.pk not in with_evidence:
            problems.append(
                f"O item {item.code_snapshot} de {item.task.sector_name_snapshot} "
                "está sem a evidência exigida."
            )
    return problems


def evaluate_process_readiness(
    process: OffboardingProcess,
    *,
    lock: bool = False,
) -> ProcessReadiness:
    """Calcular situação funcional, impedimentos e contagens do processo."""

    # Sem `select_related` nas consultas travadas: `FOR UPDATE` sobre junção é
    # exatamente a classe de detalhe que só aparece no Oracle. O nome do setor
    # vem do mapa de tarefas e a existência da pretensão, de uma consulta
    # própria.
    tasks = _locked(ProcessSectorTask.objects.filter(process=process), lock=lock)
    pending_items = _locked(PendingItem.objects.filter(process=process), lock=lock)
    sector_names = {task.pk: task.sector_name_snapshot for task in tasks}
    with_amount = set(
        PendingAmount.objects.filter(pending_item__process=process).values_list(
            "pending_item_id",
            flat=True,
        )
    )

    open_tasks = [task for task in tasks if task.status in OPEN_TASK_STATUSES]
    required_open = [task for task in open_tasks if task.is_required]
    completed = [task for task in tasks if task.status == SectorTaskStatus.COMPLETED]

    unresolved_blocking = set(
        PendingItem.objects.filter(unresolved_blocking_q(), process=process).values_list(
            "pk", flat=True
        )
    )
    undecided_amounts = [
        item
        for item in pending_items
        if item.category == PendingCategory.VALUE
        and item.pk in with_amount
        and item.status not in DECIDED_STATUSES
    ]
    open_pending = [
        item
        for item in pending_items
        if item.status in {PendingStatus.OPEN, PendingStatus.IN_REGULARIZATION}
    ]

    blockers: list[str] = []
    warnings: list[str] = []
    if not tasks:
        blockers.append("O processo não possui tarefas de setor.")
    for task in sorted(required_open, key=lambda row: row.sector_name_snapshot):
        blockers.append(f"A tarefa obrigatória de {task.sector_name_snapshot} não foi concluída.")
    for task in sorted(open_tasks, key=lambda row: row.sector_name_snapshot):
        if not task.is_required:
            warnings.append(f"A tarefa opcional de {task.sector_name_snapshot} segue em aberto.")
    for item in pending_items:
        if item.pk not in unresolved_blocking:
            continue
        sector = sector_names.get(item.task_id, "setor desconhecido")
        if item.blocking_level == BlockingLevel.BLOCKING_UNTIL_DECISION:
            blockers.append(
                f"A pendência {item.title} de {sector} aguarda a decisão sobre a pretensão."
            )
        else:
            blockers.append(
                f"A pendência bloqueante {item.title} de {sector} não foi regularizada."
            )
    for item in undecided_amounts:
        if item.pk in unresolved_blocking:
            # Já contada acima pela classificação de bloqueio; repetir seria
            # dizer duas vezes a mesma coisa a quem confere.
            continue
        sector = sector_names.get(item.task_id, "setor desconhecido")
        blockers.append(f"A pretensão de {sector} em {item.title} ainda não foi decidida.")
    for item in open_pending:
        if item.pk in unresolved_blocking:
            continue
        sector = sector_names.get(item.task_id, "setor desconhecido")
        warnings.append(f"A pendência {item.title} de {sector} continua aberta.")
    blockers.extend(_checklist_inconsistencies(process))

    situation = _FORMAL_SITUATION.get(process.status)
    if situation is None:
        if not blockers:
            situation = ProcessSituation.READY_FOR_REVIEW
        elif undecided_amounts:
            situation = ProcessSituation.AWAITING_DECISION
        elif any(item.status == PendingStatus.IN_REGULARIZATION for item in pending_items):
            situation = ProcessSituation.AWAITING_REGULARIZATION
        elif open_pending:
            situation = ProcessSituation.WITH_PENDING_ITEMS
        else:
            situation = ProcessSituation.IN_VALIDATION

    return ProcessReadiness(
        process=process,
        situation=situation,
        blockers=tuple(blockers),
        warnings=tuple(warnings),
        task_count=len(tasks),
        required_task_count=sum(1 for task in tasks if task.is_required),
        completed_task_count=len(completed),
        open_task_count=len(open_tasks),
        blocking_pending_count=len(unresolved_blocking),
        open_pending_count=len(open_pending),
        undecided_amount_count=len(undecided_amounts),
    )


def closing_blockers(process: OffboardingProcess, *, lock: bool = False) -> tuple[str, ...]:
    """Pendências ainda em curso, que impedem o encerramento formal."""

    tasks = _locked(ProcessSectorTask.objects.filter(process=process), lock=lock)
    sector_names = {task.pk: task.sector_name_snapshot for task in tasks}
    unfinished = _locked(
        PendingItem.objects.filter(
            process=process,
            status__in=UNFINISHED_PENDING_STATUSES,
        ),
        lock=lock,
    )
    return tuple(
        f"A pendência {item.title} de {sector_names.get(item.task_id, 'setor desconhecido')} "
        f"continua em curso ({PendingStatus(item.status).label.lower()})."
        for item in unfinished
    )
