from __future__ import annotations

from typing import Any, cast

from django.shortcuts import get_object_or_404
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.models import User
from apps.offboarding.services import IdempotencyConflict
from config.api import api_error

from .models import PendingItem
from .serializers import (
    AddPendingCommentSerializer,
    ChangePendingStatusSerializer,
    CreatePendingItemSerializer,
    PendingQuerySerializer,
)
from .services import (
    AddPendingCommentCommand,
    AddPendingCommentService,
    ChangePendingStatusCommand,
    ChangePendingStatusService,
    CreatePendingItemCommand,
    CreatePendingItemService,
    PendingLineValue,
    pending_items_for_actor,
)


def pending_item_payload(pending_item: PendingItem) -> dict[str, Any]:
    return {
        "uuid": str(pending_item.uuid),
        "process_uuid": str(pending_item.process.uuid),
        "task_id": pending_item.task_id,
        "checklist_item_id": pending_item.checklist_item_id,
        "category": pending_item.category,
        "title": pending_item.title,
        "description": pending_item.description,
        "status": pending_item.status,
        "blocking_level": pending_item.blocking_level,
        "identified_at": pending_item.identified_at.isoformat(),
        "regularization_due_at": (
            pending_item.regularization_due_at.isoformat()
            if pending_item.regularization_due_at
            else None
        ),
        "registered_by": {
            "id": pending_item.registered_by_id,
            "username": pending_item.registered_by.username,
        },
        "version": pending_item.version,
        "items": [
            {
                "id": item.pk,
                "code": item.code,
                "description": item.description,
                "asset_tag": item.asset_tag,
                "serial_number": item.serial_number,
                "quantity": str(item.quantity),
                "unit": item.unit,
                "item_condition": item.item_condition,
                "extra_data": item.extra_data,
            }
            for item in pending_item.items.all()
        ],
        "comments": [
            {
                "id": comment.pk,
                "author": {
                    "id": comment.author_id,
                    "username": comment.author.username,
                },
                "text": comment.text,
                "created_at": comment.created_at.isoformat(),
            }
            for comment in pending_item.comments.all()
        ],
    }


def _pending_queryset(actor: User) -> Any:
    return (
        pending_items_for_actor(actor)
        .select_related("process", "task", "checklist_item", "registered_by")
        .prefetch_related("items", "comments__author")
    )


class PendingItemListCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request: Request) -> Response:
        serializer = PendingQuerySerializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)
        data = cast(dict[str, Any], serializer.validated_data)
        rows = _pending_queryset(cast(User, request.user))
        if data.get("task_id"):
            rows = rows.filter(task_id=data["task_id"])
        if data.get("process_uuid"):
            rows = rows.filter(process__uuid=data["process_uuid"])
        if data["status"]:
            rows = rows.filter(status=data["status"])
        return Response({"results": [pending_item_payload(row) for row in rows]})

    def post(self, request: Request) -> Response:
        serializer = CreatePendingItemSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = cast(dict[str, Any], serializer.validated_data)
        try:
            result = CreatePendingItemService().execute(
                CreatePendingItemCommand(
                    actor=cast(User, request.user),
                    task_id=data["task_id"],
                    expected_task_version=data["expected_task_version"],
                    idempotency_key=request.headers.get("Idempotency-Key", ""),
                    checklist_item_id=data.get("checklist_item_id"),
                    category=data["category"],
                    title=data["title"],
                    description=data["description"],
                    blocking_level=data["blocking_level"],
                    regularization_due_at=data.get("regularization_due_at"),
                    items=tuple(PendingLineValue(**item) for item in data["items"]),
                )
            )
        except IdempotencyConflict as exc:
            return api_error(code="idempotency_conflict", message=str(exc), status_code=409)
        pending_item = get_object_or_404(
            _pending_queryset(cast(User, request.user)),
            pk=result.pending_item.pk,
        )
        payload = pending_item_payload(pending_item)
        payload["idempotency_replayed"] = result.replayed
        return Response(payload, status=200 if result.replayed else 201)


class PendingStatusView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request: Request, pending_uuid: str) -> Response:
        get_object_or_404(_pending_queryset(cast(User, request.user)), uuid=pending_uuid)
        serializer = ChangePendingStatusSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = cast(dict[str, Any], serializer.validated_data)
        try:
            result = ChangePendingStatusService().execute(
                ChangePendingStatusCommand(
                    actor=cast(User, request.user),
                    pending_uuid=pending_uuid,
                    expected_version=data["expected_version"],
                    idempotency_key=request.headers.get("Idempotency-Key", ""),
                    status=data["status"],
                    comment=data["comment"],
                )
            )
        except IdempotencyConflict as exc:
            return api_error(code="idempotency_conflict", message=str(exc), status_code=409)
        pending_item = get_object_or_404(
            _pending_queryset(cast(User, request.user)),
            pk=result.pending_item.pk,
        )
        payload = pending_item_payload(pending_item)
        payload["idempotency_replayed"] = result.replayed
        return Response(payload)


class PendingCommentView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request: Request, pending_uuid: str) -> Response:
        get_object_or_404(_pending_queryset(cast(User, request.user)), uuid=pending_uuid)
        serializer = AddPendingCommentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = cast(dict[str, Any], serializer.validated_data)
        try:
            result = AddPendingCommentService().execute(
                AddPendingCommentCommand(
                    actor=cast(User, request.user),
                    pending_uuid=pending_uuid,
                    expected_version=data["expected_version"],
                    idempotency_key=request.headers.get("Idempotency-Key", ""),
                    comment=data["comment"],
                )
            )
        except IdempotencyConflict as exc:
            return api_error(code="idempotency_conflict", message=str(exc), status_code=409)
        pending_item = get_object_or_404(
            _pending_queryset(cast(User, request.user)),
            pk=result.pending_item.pk,
        )
        payload = pending_item_payload(pending_item)
        payload["idempotency_replayed"] = result.replayed
        return Response(payload)
