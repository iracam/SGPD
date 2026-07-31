from __future__ import annotations

from collections.abc import Callable
from decimal import Decimal
from typing import Any, cast

from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404
from rest_framework import serializers
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
    AssessPendingAmountSerializer,
    ChangePendingStatusSerializer,
    ContestPendingAmountSerializer,
    CreatePendingItemSerializer,
    DecidePendingAmountSerializer,
    PendingQuerySerializer,
    RegisterPendingAmountSerializer,
)
from .services import (
    AddPendingCommentCommand,
    AddPendingCommentService,
    AssessPendingAmountCommand,
    AssessPendingAmountService,
    ChangePendingStatusCommand,
    ChangePendingStatusService,
    ContestPendingAmountCommand,
    ContestPendingAmountService,
    CreatePendingItemCommand,
    CreatePendingItemService,
    DecidePendingAmountCommand,
    DecidePendingAmountService,
    PendingLineValue,
    PendingMutationResult,
    RegisterPendingAmountCommand,
    RegisterPendingAmountService,
    can_analyse_amounts,
    pending_items_for_actor,
)


def amount_payload(pending_item: PendingItem) -> dict[str, Any] | None:
    """Pretensão e pareceres da pendência; `None` quando o valor nunca foi lançado."""

    amount = getattr(pending_item, "amount", None)
    if amount is None:
        return None
    return {
        "amount_informed": _money(amount.amount_informed),
        "amount_assessed": _money(amount.amount_assessed),
        "amount_contested": _money(amount.amount_contested),
        "amount_approved": _money(amount.amount_approved),
        "amount_processed": _money(amount.amount_processed),
        "currency": amount.currency,
        "justification": amount.justification,
        "informed_by": {
            "id": amount.informed_by_id,
            "username": amount.informed_by.username,
        },
        "informed_at": amount.informed_at.isoformat(),
        "approved_by": (
            {"id": amount.approved_by_id, "username": amount.approved_by.username}
            if amount.approved_by_id
            else None
        ),
        "approved_at": amount.approved_at.isoformat() if amount.approved_at else None,
        "version": amount.version,
        "decisions": [
            {
                "id": decision.pk,
                "decision": decision.decision,
                "opinion": decision.opinion,
                "decided_by": {
                    "id": decision.decided_by_id,
                    "username": decision.decided_by.username,
                },
                "decided_at": decision.decided_at.isoformat(),
                "segregation_override": decision.segregation_override,
            }
            for decision in pending_item.decisions.all()
        ],
    }


def _money(value: Decimal | None) -> str | None:
    return None if value is None else f"{value:.2f}"


def amount_analyst(actor: User) -> Callable[[PendingItem], bool]:
    """Memo por processo de quem apura e decide valor: a lista repete o mesmo processo."""

    cache: dict[int, bool] = {}

    def allows(pending_item: PendingItem) -> bool:
        process = pending_item.process
        if process.pk not in cache:
            cache[process.pk] = can_analyse_amounts(actor, process)
        return cache[process.pk]

    return allows


def pending_item_payload(
    pending_item: PendingItem,
    *,
    can_analyse_amount: bool = False,
) -> dict[str, Any]:
    return {
        "amount": amount_payload(pending_item),
        # Espelha no cliente a autorização que o service revalida sob lock
        # (ADR-044/ADR-048); a SPA não é barreira, só deixa de oferecer a ação.
        "can_analyse_amount": can_analyse_amount,
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
        .select_related(
            "process",
            "task",
            "checklist_item",
            "registered_by",
            "amount__informed_by",
            "amount__approved_by",
        )
        .prefetch_related("items", "comments__author", "decisions__decided_by")
    )


def _reloaded_payload(request: Request, result: PendingMutationResult) -> dict[str, Any]:
    """Reler a pendência pelo queryset autorizado, para responder o estado completo."""

    actor = cast(User, request.user)
    pending_item = get_object_or_404(_pending_queryset(actor), pk=result.pending_item.pk)
    payload = pending_item_payload(
        pending_item,
        can_analyse_amount=can_analyse_amounts(actor, pending_item.process),
    )
    payload["idempotency_replayed"] = result.replayed
    return payload


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
        allows = amount_analyst(cast(User, request.user))
        return Response(
            {"results": [pending_item_payload(row, can_analyse_amount=allows(row)) for row in rows]}
        )

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
        payload = _reloaded_payload(request, result)
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
        return Response(_reloaded_payload(request, result))


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
        return Response(_reloaded_payload(request, result))


class _PendingAmountView(APIView):
    """Eixo de valor: valida o contrato, delega ao service e devolve a pendência inteira.

    A autorização de quem apura e decide é da ADR-048 e vive nos services, sob
    lock; aqui ela só chega como resposta 403 com o motivo.
    """

    permission_classes = [IsAuthenticated]
    serializer_class: type[serializers.Serializer[dict[str, Any]]]

    def execute(
        self,
        *,
        actor: User,
        pending_uuid: str,
        key: str,
        data: dict[str, Any],
    ) -> PendingMutationResult:
        raise NotImplementedError

    def post(self, request: Request, pending_uuid: str) -> Response:
        actor = cast(User, request.user)
        get_object_or_404(_pending_queryset(actor), uuid=pending_uuid)
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            result = self.execute(
                actor=actor,
                pending_uuid=pending_uuid,
                key=request.headers.get("Idempotency-Key", ""),
                data=cast(dict[str, Any], serializer.validated_data),
            )
        except IdempotencyConflict as exc:
            return api_error(code="idempotency_conflict", message=str(exc), status_code=409)
        except PermissionDenied as exc:
            # A negativa do eixo de valor é regra de negócio legível — segregação
            # ou falta de DP no escopo —, e não uma sonda de existência.
            return api_error(code="permission_denied", message=str(exc), status_code=403)
        return Response(_reloaded_payload(request, result))


class PendingAmountRegisterView(_PendingAmountView):
    serializer_class = RegisterPendingAmountSerializer

    def execute(
        self,
        *,
        actor: User,
        pending_uuid: str,
        key: str,
        data: dict[str, Any],
    ) -> PendingMutationResult:
        return RegisterPendingAmountService().execute(
            RegisterPendingAmountCommand(
                actor=actor,
                pending_uuid=pending_uuid,
                expected_version=data["expected_version"],
                idempotency_key=key,
                amount_informed=data["amount_informed"],
                currency=data["currency"],
                justification=data["justification"],
            )
        )


class PendingAmountAssessView(_PendingAmountView):
    serializer_class = AssessPendingAmountSerializer

    def execute(
        self,
        *,
        actor: User,
        pending_uuid: str,
        key: str,
        data: dict[str, Any],
    ) -> PendingMutationResult:
        return AssessPendingAmountService().execute(
            AssessPendingAmountCommand(
                actor=actor,
                pending_uuid=pending_uuid,
                expected_version=data["expected_version"],
                idempotency_key=key,
                amount_assessed=data["amount_assessed"],
                justification=data["justification"],
            )
        )


class PendingAmountContestView(_PendingAmountView):
    serializer_class = ContestPendingAmountSerializer

    def execute(
        self,
        *,
        actor: User,
        pending_uuid: str,
        key: str,
        data: dict[str, Any],
    ) -> PendingMutationResult:
        return ContestPendingAmountService().execute(
            ContestPendingAmountCommand(
                actor=actor,
                pending_uuid=pending_uuid,
                expected_version=data["expected_version"],
                idempotency_key=key,
                amount_contested=data["amount_contested"],
                justification=data["justification"],
            )
        )


class PendingAmountDecideView(_PendingAmountView):
    serializer_class = DecidePendingAmountSerializer

    def execute(
        self,
        *,
        actor: User,
        pending_uuid: str,
        key: str,
        data: dict[str, Any],
    ) -> PendingMutationResult:
        return DecidePendingAmountService().execute(
            DecidePendingAmountCommand(
                actor=actor,
                pending_uuid=pending_uuid,
                expected_version=data["expected_version"],
                idempotency_key=key,
                decision=data["decision"],
                opinion=data["opinion"],
                amount_approved=data.get("amount_approved"),
            )
        )
