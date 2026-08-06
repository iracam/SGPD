"""Runtime assíncrono: o que o worker garante e o que ele não pode quebrar (ADR-057).

O broker carrega o sinal de trabalho; a fila durável continua no Oracle. Estes
testes exercem exatamente a fronteira entre as duas coisas — o disparo imediato
acelera, e a ausência dele não perde mensagem.
"""

# ruff: noqa: F811

from __future__ import annotations

from typing import Any
from unittest import mock

import pytest
from django.core import mail
from django.db import transaction

from apps.accounts.models import User
from apps.notifications.models import Notification, NotificationEvent, NotificationStatus
from apps.notifications.tasks import dispatch_notification, dispatch_queue, scan_deadlines
from apps.offboarding.models import ProcessSectorTask
from tests.test_notifications import enqueue
from tests.test_offboarding_start import (  # noqa: F401
    actor,
    configured_draft,
    process,
    start,
)
from tests.test_offboarding_tasks import started_task

pytestmark = pytest.mark.django_db


def queued(task: ProcessSectorTask, recipient: User) -> Notification:
    result = enqueue(task, (recipient,))
    assert len(result.created) == 1
    return result.created[0]


def test_the_task_delivers_the_same_message_the_batch_would(actor: User, process: Any) -> None:
    task = started_task(actor, process)
    notification = queued(task, actor)

    assert dispatch_notification(notification.pk) == NotificationStatus.SENT

    notification.refresh_from_db()
    assert notification.status == NotificationStatus.SENT
    assert notification.sent_at is not None
    assert len(mail.outbox) == 1
    assert notification.attempts == 1


def test_running_the_same_task_twice_sends_once(actor: User, process: Any) -> None:
    """Reentrega do broker não pode virar e-mail duplicado.

    Com `acks_late` a tarefa volta para a fila quando o worker morre no meio, e
    esta é a propriedade que torna isso inofensivo: a segunda execução encontra
    a mensagem já entregue e não consome tentativa.
    """

    task = started_task(actor, process)
    notification = queued(task, actor)

    assert dispatch_notification(notification.pk) == NotificationStatus.SENT
    assert dispatch_notification(notification.pk) is None

    notification.refresh_from_db()
    assert notification.attempts == 1
    assert len(mail.outbox) == 1


def test_a_vanished_message_is_not_an_error(actor: User, process: Any) -> None:
    # A exclusão do processo leva a fila dele junto (ADR-056); a tarefa agendada
    # antes disso chega sem alvo.
    task = started_task(actor, process)
    notification = queued(task, actor)
    pk = notification.pk
    Notification.objects.filter(pk=pk).hard_delete()

    assert dispatch_notification(pk) is None
    assert mail.outbox == []


def test_the_batch_task_reports_what_it_did(actor: User, process: Any) -> None:
    task = started_task(actor, process)
    queued(task, actor)

    result = dispatch_queue()

    # O início do processo já enfileirou o aviso de tarefa atribuída, e o lote
    # despacha a fila inteira: o que se verifica é que ele fecha tudo o que
    # estava pendente, não um número escolhido a dedo.
    assert result["sent"] == Notification.objects.filter(status=NotificationStatus.SENT).count()
    assert result["failed"] == 0
    assert not Notification.objects.filter(status=NotificationStatus.PENDING).exists()


def test_the_scan_task_reports_what_it_queued(actor: User, process: Any) -> None:
    result = scan_deadlines()

    assert set(result) == {"queued", "tasks_scanned", "processes_scanned", "without_recipients"}
    assert result["queued"] >= 0


def test_a_broker_out_of_reach_does_not_break_the_domain(actor: User, process: Any) -> None:
    """O enfileiramento é do domínio; o disparo imediato é só aceleração.

    Se publicar no broker derrubasse a transação, o outbox teria trocado uma
    garantia por uma dependência — exatamente o que a ADR-057 recusou.
    """

    task = started_task(actor, process)

    with mock.patch.object(
        dispatch_notification,
        "delay",
        side_effect=OSError("broker fora do ar"),
    ):
        with transaction.atomic():
            result = enqueue(task, (actor,))
            # `on_commit` roda no fim do bloco; sem o `atomic` explícito, o
            # disparo aconteceria antes desta linha.
        assert len(result.created) == 1

    notification = result.created[0]
    notification.refresh_from_db()
    assert notification.status == NotificationStatus.PENDING
    assert mail.outbox == []


def test_the_message_leaves_right_after_the_commit(
    actor: User,
    process: Any,
    django_capture_on_commit_callbacks: Any,
) -> None:
    """O caminho que tira a latência do intervalo da varredura.

    Sob `django_db` a transação nunca confirma e os callbacks não disparam
    sozinhos; capturá-los é o que reproduz o commit real da requisição.
    """

    task = started_task(actor, process)

    with django_capture_on_commit_callbacks(execute=True) as callbacks:
        enqueue(task, (actor,))

    assert len(callbacks) == 1
    assert len(mail.outbox) == 1
    message = Notification.objects.get(recipient=actor, event=NotificationEvent.TASK_OVERDUE)
    assert message.status == NotificationStatus.SENT
    # O aviso do início ficou de fora: o `on_commit` dele foi registrado antes
    # da captura, e continua esperando o despacho.
    assert (
        Notification.objects.get(event=NotificationEvent.TASK_ASSIGNED).status
        == NotificationStatus.PENDING
    )


def test_a_rolled_back_fact_never_notifies(
    actor: User,
    process: Any,
    django_capture_on_commit_callbacks: Any,
) -> None:
    task = started_task(actor, process)

    with (
        django_capture_on_commit_callbacks(execute=True) as callbacks,
        pytest.raises(RuntimeError),
        transaction.atomic(),
    ):
        enqueue(task, (actor,))
        raise RuntimeError("o fato não se confirmou")

    assert callbacks == []
    assert mail.outbox == []
    assert not Notification.objects.filter(event=NotificationEvent.TASK_OVERDUE).exists()
