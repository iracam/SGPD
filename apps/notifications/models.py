"""Outbox transacional de notificações e histórico append-only de tentativas.

A fila vive no Oracle, na mesma transação do fato que a origina (ADR-049): quem
grava a mudança de domínio grava a mensagem, e o despacho acontece depois, fora
da requisição. A linha do outbox é o registro durável exigido pelo R07 — é dela
que saem o painel de falhas e o reprocessamento.
"""

from __future__ import annotations

import uuid
from typing import Any

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models


class NotificationEvent(models.TextChoices):
    """Fato que originou a mensagem.

    Os marcos de prazo seguem `WORKFLOWS.md` §7; os eventos de domínio são
    enfileirados pelos services que os produzem.
    """

    TASK_DUE_SOON = "TAREFA_A_VENCER", "Tarefa a vencer"
    TASK_DUE_IMMINENT = "TAREFA_VENCE_EM_BREVE", "Tarefa próxima do vencimento"
    TASK_OVERDUE = "TAREFA_VENCIDA", "Tarefa vencida"
    TASK_OVERDUE_CRITICAL = "TAREFA_VENCIDA_CRITICA", "Tarefa vencida em nível crítico"
    PROCESS_DUE_SOON = "PROCESSO_PROXIMO_LIMITE", "Processo próximo do limite"
    TASK_ASSIGNED = "TAREFA_ATRIBUIDA", "Tarefa atribuída ao setor"
    PENDING_BLOCKING_REGISTERED = "PENDENCIA_BLOQUEANTE", "Pendência bloqueante registrada"
    AMOUNT_AWAITING_DECISION = "VALOR_AGUARDA_DECISAO", "Valor aguardando decisão"
    AMOUNT_DECIDED = "VALOR_DECIDIDO", "Valor decidido"


class NotificationChannel(models.TextChoices):
    EMAIL = "EMAIL", "E-mail"


class NotificationStatus(models.TextChoices):
    PENDING = "PENDENTE", "Pendente"
    SENDING = "ENVIANDO", "Em envio"
    SENT = "ENVIADA", "Enviada"
    FAILED = "FALHA", "Falha"
    CANCELLED = "CANCELADA", "Cancelada"


#: Situações que ainda podem consumir uma tentativa de envio.
OPEN_STATUSES = frozenset({NotificationStatus.PENDING, NotificationStatus.SENDING})

#: Situações terminais: só o reprocessamento explícito as reabre.
TERMINAL_STATUSES = frozenset(
    {
        NotificationStatus.SENT,
        NotificationStatus.FAILED,
        NotificationStatus.CANCELLED,
    }
)


class NotificationQuerySet(models.QuerySet[Any]):
    def update(self, **kwargs: Any) -> int:
        raise ValidationError("Notificações devem ser alteradas pelos services de despacho.")

    def delete(self) -> tuple[int, dict[str, int]]:
        raise ValidationError("O histórico de notificações não pode ser excluído.")


class Notification(models.Model):
    """Uma mensagem para um destinatário, com o texto congelado na origem."""

    uuid = models.UUIDField("UUID", default=uuid.uuid4, unique=True, editable=False)
    event = models.CharField("evento", max_length=30, choices=NotificationEvent.choices)
    channel = models.CharField(
        "canal",
        max_length=20,
        choices=NotificationChannel.choices,
        default=NotificationChannel.EMAIL,
    )
    # A chave carrega evento, canal, alvo e destinatário. É ela que torna a
    # varredura idempotente: o mesmo marco varrido de novo colide e não duplica.
    dedup_key = models.CharField("chave de deduplicação", max_length=120)
    process = models.ForeignKey(
        "offboarding.OffboardingProcess",
        verbose_name="processo",
        on_delete=models.PROTECT,
        related_name="notifications",
        # `SGPD_IX_NOTIF_PROCESS` lidera por processo; o índice automático da FK
        # seria redundante no Oracle.
        db_index=False,
    )
    task = models.ForeignKey(
        "offboarding.ProcessSectorTask",
        verbose_name="tarefa",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="notifications",
    )
    sector = models.ForeignKey(
        "sectors.ValidationSector",
        verbose_name="setor",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="notifications",
    )
    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name="destinatário",
        on_delete=models.PROTECT,
        related_name="notifications",
    )
    # Endereço efetivamente usado no envio, congelado: o cadastro pode mudar
    # depois e a conferência precisa saber para onde a mensagem foi.
    recipient_email = models.EmailField("endereço do destinatário", max_length=254)
    subject = models.CharField("assunto", max_length=200)
    body = models.TextField("corpo")
    # Identificadores técnicos do que originou a mensagem. Sem nome, e-mail,
    # CPF ou valor: o corpo já é a única projeção legível (SECURITY.md §Dados).
    context = models.JSONField("contexto técnico", default=dict, blank=True)
    status = models.CharField(
        "situação",
        max_length=20,
        choices=NotificationStatus.choices,
        default=NotificationStatus.PENDING,
    )
    attempts = models.PositiveIntegerField("tentativas", default=0)
    max_attempts = models.PositiveIntegerField("tentativas máximas", default=5)
    next_attempt_at = models.DateTimeField("próxima tentativa em")
    last_error = models.TextField("último erro", blank=True)
    created_at = models.DateTimeField("criada em", auto_now_add=True)
    updated_at = models.DateTimeField("atualizada em", auto_now=True)
    sent_at = models.DateTimeField("enviada em", null=True, blank=True)
    correlation_id = models.CharField("correlation ID", max_length=64, blank=True)
    version = models.PositiveIntegerField("versão de concorrência", default=1)

    objects = NotificationQuerySet.as_manager()

    class Meta:
        db_table = "SGPD_NOTIFICATION"
        ordering = ("-created_at", "-id")
        verbose_name = "notificação"
        verbose_name_plural = "notificações"
        constraints = [
            models.UniqueConstraint(
                fields=("dedup_key",),
                name="SGPD_UQ_NOTIF_DEDUP",
            ),
            models.CheckConstraint(
                condition=models.Q(version__gt=0, max_attempts__gt=0),
                name="SGPD_CK_NOTIF_VALUES",
            ),
            # `sent_at` é anulável: a condição precisa admitir o ausente
            # explicitamente, porque o Oracle não avalia `NULL` em comparação
            # como verdadeiro e `full_clean()` acusaria violação (ADR-049 §Oracle).
            models.CheckConstraint(
                condition=(
                    models.Q(status=NotificationStatus.SENT, sent_at__isnull=False)
                    | (~models.Q(status=NotificationStatus.SENT) & models.Q(sent_at__isnull=True))
                ),
                name="SGPD_CK_NOTIF_SENT_AT",
            ),
        ]
        indexes = [
            models.Index(
                fields=("status", "next_attempt_at"),
                name="SGPD_IX_NOTIF_DISPATCH",
            ),
            models.Index(
                fields=("process", "status"),
                name="SGPD_IX_NOTIF_PROCESS",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.event} / {self.recipient_email} / {self.status}"

    def clean(self) -> None:
        super().clean()
        self.dedup_key = self.dedup_key.strip()
        self.subject = self.subject.strip()
        self.recipient_email = self.recipient_email.strip()
        if not self.dedup_key:
            raise ValidationError({"dedup_key": "A chave de deduplicação é obrigatória."})
        if not self.subject:
            raise ValidationError({"subject": "O assunto da notificação é obrigatório."})
        if not self.body.strip():
            raise ValidationError({"body": "O corpo da notificação é obrigatório."})
        if not self.recipient_email:
            raise ValidationError(
                {"recipient_email": "O destinatário não possui endereço de e-mail."}
            )
        task = self.task if self.task_id else None
        if task is not None and task.process_id != self.process_id:
            raise ValidationError({"task": "A tarefa não pertence ao processo informado."})

    def delete(self, *args: Any, **kwargs: Any) -> tuple[int, dict[str, int]]:
        raise ValidationError("Notificações não podem ser excluídas.")

    @property
    def attempts_exhausted(self) -> bool:
        return self.attempts >= self.max_attempts


class NotificationAttempt(models.Model):
    """Uma tentativa de entrega, aberta antes do envio e fechada depois dele.

    A linha nasce aberta e é fechada uma única vez pelo despachante, sob lock.
    Nada além do fechamento a altera e nenhuma tentativa é apagada: é o que
    permite distinguir “nunca tentou” de “tentou e o SMTP recusou”.
    """

    notification = models.ForeignKey(
        Notification,
        verbose_name="notificação",
        on_delete=models.PROTECT,
        related_name="delivery_attempts",
    )
    attempt_number = models.PositiveIntegerField("número da tentativa")
    started_at = models.DateTimeField("iniciada em", auto_now_add=True)
    finished_at = models.DateTimeField("finalizada em", null=True, blank=True)
    succeeded = models.BooleanField("bem-sucedida", null=True, blank=True)
    error = models.TextField("erro", blank=True)

    objects = NotificationQuerySet.as_manager()

    class Meta:
        db_table = "SGPD_NOTIFICATION_ATTEMPT"
        ordering = ("notification_id", "attempt_number")
        verbose_name = "tentativa de entrega"
        verbose_name_plural = "tentativas de entrega"
        constraints = [
            models.UniqueConstraint(
                fields=("notification", "attempt_number"),
                name="SGPD_UQ_NOTIF_ATTEMPT",
            ),
            models.CheckConstraint(
                condition=models.Q(attempt_number__gt=0),
                name="SGPD_CK_NOTIF_ATT_NUMBER",
            ),
            # Aberta ou fechada por inteiro: resultado e instante andam juntos.
            models.CheckConstraint(
                condition=(
                    models.Q(finished_at__isnull=True, succeeded__isnull=True)
                    | models.Q(finished_at__isnull=False, succeeded__isnull=False)
                ),
                name="SGPD_CK_NOTIF_ATT_CLOSED",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.notification_id} #{self.attempt_number}"

    def delete(self, *args: Any, **kwargs: Any) -> tuple[int, dict[str, int]]:
        raise ValidationError("Tentativas de entrega não podem ser excluídas.")
