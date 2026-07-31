"""Varredura dos marcos de prazo (WORKFLOWS.md §7, RF-028).

A varredura não decide nada de domínio: ela lê prazos e enfileira avisos. Cada
marco dispara uma única vez por tarefa e destinatário, garantido pela chave de
deduplicação — rodar a varredura de dez em dez minutos ou uma vez por dia muda
a latência do aviso, nunca a quantidade.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, time, timedelta

from django.conf import settings
from django.db import transaction
from django.db.models import QuerySet
from django.utils import timezone

from apps.accounts.models import User
from apps.offboarding.models import (
    OffboardingProcess,
    ProcessSectorTask,
    ProcessStatus,
    SectorTaskStatus,
)

from .models import NotificationEvent
from .recipients import people_department_users, sector_responsibles
from .services import EnqueueNotificationCommand, EnqueueNotificationService

logger = logging.getLogger(__name__)

#: Situações em que a tarefa ainda espera alguém.
OPEN_TASK_STATUSES = (SectorTaskStatus.PENDING, SectorTaskStatus.IN_ANALYSIS)


@dataclass(frozen=True, slots=True)
class ScanDeadlinesCommand:
    at: datetime | None = None


@dataclass(frozen=True, slots=True)
class ScanDeadlinesResult:
    queued: int
    tasks_scanned: int
    processes_scanned: int
    #: Marcos que não encontraram ninguém para avisar — setor sem responsável
    #: vigente ou processo sem `DP` no escopo.
    without_recipients: int


def _milestone_instants(task: ProcessSectorTask) -> tuple[tuple[str, datetime], ...]:
    """Instante a partir do qual cada marco da tarefa passa a valer."""

    due_at = task.due_at
    return (
        (
            NotificationEvent.TASK_DUE_SOON,
            due_at - timedelta(hours=settings.NOTIFICATION_TASK_DUE_SOON_HOURS),
        ),
        (
            NotificationEvent.TASK_DUE_IMMINENT,
            due_at - timedelta(hours=settings.NOTIFICATION_TASK_DUE_IMMINENT_HOURS),
        ),
        (NotificationEvent.TASK_OVERDUE, due_at),
        (
            NotificationEvent.TASK_OVERDUE_CRITICAL,
            due_at + timedelta(hours=settings.NOTIFICATION_TASK_CRITICAL_HOURS),
        ),
    )


def processes_with_open_tasks() -> QuerySet[OffboardingProcess]:
    """Processos iniciados com ao menos uma tarefa em aberto.

    Sem `distinct()`: o processo carrega `reason` e `notes` como NCLOB e o
    Oracle recusa `SELECT DISTINCT` sobre LOB com `ORA-00932`. A subconsulta
    resolve a duplicidade do join antes de projetar as colunas.
    """

    return OffboardingProcess.objects.filter(
        status=ProcessStatus.STARTED,
        pk__in=ProcessSectorTask.objects.filter(status__in=OPEN_TASK_STATUSES).values("process_id"),
    ).order_by("due_date", "pk")


def _process_deadline(process: OffboardingProcess) -> datetime:
    """Fim do dia da data limite, no fuso da aplicação."""

    return timezone.make_aware(datetime.combine(process.due_date, time.max))


class ScanDeadlinesService:
    """Enfileira lembrete, atraso e escalada conforme o relógio."""

    def __init__(self) -> None:
        self._enqueue = EnqueueNotificationService()
        self._sector_cache: dict[int, tuple[User, ...]] = {}
        self._dp_cache: dict[tuple[int, int], tuple[User, ...]] = {}

    def execute(self, command: ScanDeadlinesCommand) -> ScanDeadlinesResult:
        now = command.at or timezone.now()
        queued = 0
        without_recipients = 0
        tasks = (
            ProcessSectorTask.objects.filter(
                process__status=ProcessStatus.STARTED,
                status__in=OPEN_TASK_STATUSES,
            )
            .select_related("process", "sector", "sector__escalation_sector")
            .order_by("due_at", "pk")
        )
        tasks_scanned = 0
        for task in tasks:
            tasks_scanned += 1
            for event, instant in _milestone_instants(task):
                if now < instant:
                    continue
                recipients = self._task_recipients(task, event=event, at=now)
                if not recipients:
                    without_recipients += 1
                    logger.warning(
                        "notification.milestone_without_recipients",
                        extra={"task_id": task.pk, "event": event},
                    )
                    continue
                # Uma transação por marco: a falha de um aviso não pode levar
                # embora os que já foram enfileirados na mesma varredura.
                with transaction.atomic():
                    result = self._enqueue.execute(
                        EnqueueNotificationCommand(
                            event=event,
                            process=task.process,
                            task=task,
                            sector=task.sector,
                            recipients=recipients,
                            context={"task_id": task.pk, "sector_id": task.sector_id},
                        )
                    )
                queued += len(result.created)

        processes_scanned, process_queued, process_without = self._scan_processes(now)
        return ScanDeadlinesResult(
            queued=queued + process_queued,
            tasks_scanned=tasks_scanned,
            processes_scanned=processes_scanned,
            without_recipients=without_recipients + process_without,
        )

    def _scan_processes(self, now: datetime) -> tuple[int, int, int]:
        horizon = timedelta(hours=settings.NOTIFICATION_PROCESS_DUE_SOON_HOURS)
        processes = processes_with_open_tasks()
        scanned = queued = without_recipients = 0
        for process in processes:
            scanned += 1
            if now < _process_deadline(process) - horizon:
                continue
            recipients = self._people_department(process, at=now)
            if not recipients:
                without_recipients += 1
                logger.warning(
                    "notification.process_deadline_without_recipients",
                    extra={"process_id": process.pk},
                )
                continue
            open_task_count = process.sector_tasks.filter(status__in=OPEN_TASK_STATUSES).count()
            with transaction.atomic():
                result = self._enqueue.execute(
                    EnqueueNotificationCommand(
                        event=NotificationEvent.PROCESS_DUE_SOON,
                        process=process,
                        recipients=recipients,
                        context={"open_task_count": open_task_count},
                    )
                )
            queued += len(result.created)
        return scanned, queued, without_recipients

    def _task_recipients(
        self,
        task: ProcessSectorTask,
        *,
        event: str,
        at: datetime,
    ) -> tuple[User, ...]:
        recipients: list[User] = list(self._responsibles(task.sector_id, at=at))
        if event in {NotificationEvent.TASK_OVERDUE, NotificationEvent.TASK_OVERDUE_CRITICAL}:
            recipients.extend(self._people_department(task.process, at=at))
        if event == NotificationEvent.TASK_OVERDUE_CRITICAL:
            escalation_id = task.sector.escalation_sector_id
            if escalation_id is not None:
                recipients.extend(self._responsibles(escalation_id, at=at))
        return tuple(recipients)

    def _responsibles(self, sector_id: int, *, at: datetime) -> tuple[User, ...]:
        if sector_id not in self._sector_cache:
            self._sector_cache[sector_id] = sector_responsibles(sector_id=sector_id, at=at)
        return self._sector_cache[sector_id]

    def _people_department(
        self,
        process: OffboardingProcess,
        *,
        at: datetime,
    ) -> tuple[User, ...]:
        scope = (process.company_code, process.branch_code)
        if scope not in self._dp_cache:
            self._dp_cache[scope] = people_department_users(process=process, at=at)
        return self._dp_cache[scope]
