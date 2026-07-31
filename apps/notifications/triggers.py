"""Gatilhos de domínio: que fato vira aviso e para quem (RF-027).

Cada função é chamada de dentro da transação do service que produziu o fato. É
aqui que mora a política de destinatário — o service de domínio decide o
domínio, não a lista de quem recebe.
"""

from __future__ import annotations

from django.utils import timezone

from apps.offboarding.models import ProcessSectorTask
from apps.pending_items.models import PendingItem

from .models import NotificationEvent
from .recipients import people_department_users, sector_responsibles
from .services import EnqueueNotificationCommand, EnqueueNotificationService


def notify_task_assigned(task: ProcessSectorTask) -> None:
    """Avisa o setor de que o processo iniciou e a tarefa nasceu."""

    EnqueueNotificationService().execute(
        EnqueueNotificationCommand(
            event=NotificationEvent.TASK_ASSIGNED,
            process=task.process,
            task=task,
            sector=task.sector,
            recipients=sector_responsibles(sector_id=task.sector_id, at=timezone.now()),
            context={"task_id": task.pk, "sector_id": task.sector_id},
        )
    )


def notify_blocking_pending(pending_item: PendingItem) -> None:
    """Avisa o `DP` do escopo de que uma pendência passou a travar a conclusão."""

    EnqueueNotificationService().execute(
        EnqueueNotificationCommand(
            event=NotificationEvent.PENDING_BLOCKING_REGISTERED,
            process=pending_item.process,
            task=pending_item.task,
            sector=pending_item.task.sector,
            recipients=people_department_users(
                process=pending_item.process,
                at=timezone.now(),
            ),
            scope=f"pi{pending_item.pk}",
            context={"pending_uuid": str(pending_item.uuid)},
        )
    )


def notify_amount_awaiting_decision(pending_item: PendingItem, *, amount_version: int) -> None:
    """Avisa o `DP` de que existe pretensão esperando decisão.

    A versão da pretensão entra na chave: depois de uma contestação a decisão
    volta a ser necessária e o aviso precisa poder sair de novo.
    """

    EnqueueNotificationService().execute(
        EnqueueNotificationCommand(
            event=NotificationEvent.AMOUNT_AWAITING_DECISION,
            process=pending_item.process,
            task=pending_item.task,
            sector=pending_item.task.sector,
            recipients=people_department_users(
                process=pending_item.process,
                at=timezone.now(),
            ),
            scope=f"pa{pending_item.pk}v{amount_version}",
            context={"pending_uuid": str(pending_item.uuid)},
        )
    )


def notify_amount_decided(pending_item: PendingItem, *, decision_id: int) -> None:
    """Avisa o setor que informou o valor de que a decisão saiu."""

    EnqueueNotificationService().execute(
        EnqueueNotificationCommand(
            event=NotificationEvent.AMOUNT_DECIDED,
            process=pending_item.process,
            task=pending_item.task,
            sector=pending_item.task.sector,
            recipients=sector_responsibles(
                sector_id=pending_item.task.sector_id,
                at=timezone.now(),
            ),
            scope=f"pd{decision_id}",
            context={"pending_uuid": str(pending_item.uuid)},
        )
    )
