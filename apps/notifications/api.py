from __future__ import annotations

from typing import Any, cast

from django.db.models import Count
from django.shortcuts import get_object_or_404
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.models import User
from apps.offboarding.services import IdempotencyConflict
from config.api import api_error

from .models import Notification
from .operations import (
    ReprocessNotificationCommand,
    ReprocessNotificationService,
    notifications_for_actor,
)
from .serializers import NotificationQuerySerializer, ReprocessNotificationSerializer


def notification_payload(notification: Notification) -> dict[str, Any]:
    return {
        "uuid": str(notification.uuid),
        "event": notification.event,
        "channel": notification.channel,
        "status": notification.status,
        "subject": notification.subject,
        "body": notification.body,
        "process_uuid": str(notification.process.uuid),
        "process_ref": str(notification.process.uuid)[:8],
        "task_id": notification.task_id,
        "sector_name": notification.sector.name if notification.sector is not None else None,
        "recipient": {
            "id": notification.recipient_id,
            "username": notification.recipient.username,
            "email": notification.recipient_email,
        },
        "attempts": notification.attempts,
        "max_attempts": notification.max_attempts,
        "next_attempt_at": notification.next_attempt_at.isoformat(),
        "sent_at": notification.sent_at.isoformat() if notification.sent_at else None,
        "last_error": notification.last_error,
        "created_at": notification.created_at.isoformat(),
        "version": notification.version,
        "delivery_attempts": [
            {
                "attempt_number": attempt.attempt_number,
                "started_at": attempt.started_at.isoformat(),
                "finished_at": (attempt.finished_at.isoformat() if attempt.finished_at else None),
                "succeeded": attempt.succeeded,
                "error": attempt.error,
            }
            for attempt in notification.delivery_attempts.all()
        ],
    }


def _notification_queryset(actor: User) -> Any:
    return (
        notifications_for_actor(actor)
        .select_related("process", "sector", "recipient")
        .prefetch_related("delivery_attempts")
    )


class NotificationListView(APIView):
    """Fila de notificações do escopo do ator, com o resumo por situação."""

    permission_classes = [IsAuthenticated]

    def get(self, request: Request) -> Response:
        serializer = NotificationQuerySerializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)
        data = cast(dict[str, Any], serializer.validated_data)
        actor = cast(User, request.user)
        rows = _notification_queryset(actor)
        if data.get("process_uuid"):
            rows = rows.filter(process__uuid=data["process_uuid"])
        # O resumo conta a fila inteira do escopo: filtrar por situação e ainda
        # assim resumir só a situação escolhida esconderia o que interessa.
        summary = {
            row["status"]: row["total"] for row in rows.values("status").annotate(total=Count("pk"))
        }
        if data["status"]:
            rows = rows.filter(status=data["status"])
        if data["event"]:
            rows = rows.filter(event=data["event"])
        rows = rows.order_by("-created_at", "-pk")[: data["limit"]]
        return Response(
            {
                "results": [notification_payload(row) for row in rows],
                "summary": summary,
            }
        )


class NotificationReprocessView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request: Request, notification_uuid: str) -> Response:
        get_object_or_404(_notification_queryset(cast(User, request.user)), uuid=notification_uuid)
        serializer = ReprocessNotificationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = cast(dict[str, Any], serializer.validated_data)
        try:
            result = ReprocessNotificationService().execute(
                ReprocessNotificationCommand(
                    actor=cast(User, request.user),
                    notification_uuid=notification_uuid,
                    expected_version=data["expected_version"],
                    idempotency_key=request.headers.get("Idempotency-Key", ""),
                )
            )
        except IdempotencyConflict as exc:
            return api_error(code="idempotency_conflict", message=str(exc), status_code=409)
        notification = get_object_or_404(
            _notification_queryset(cast(User, request.user)),
            pk=result.notification.pk,
        )
        payload = notification_payload(notification)
        payload["idempotency_replayed"] = result.replayed
        return Response(payload)
