from __future__ import annotations

from typing import Any, cast

from django.http import FileResponse
from django.shortcuts import get_object_or_404
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.models import User
from apps.offboarding.services import IdempotencyConflict
from config.api import api_error

from .models import Evidence
from .serializers import EvidenceQuerySerializer, UploadEvidenceSerializer
from .services import (
    RegisterEvidenceDownloadService,
    UploadEvidenceCommand,
    UploadEvidenceService,
    evidences_for_actor,
    open_evidence_file,
)


def evidence_payload(evidence: Evidence) -> dict[str, Any]:
    pending_item = evidence.pending_item if evidence.pending_item_id is not None else None
    return {
        "uuid": str(evidence.uuid),
        "process_uuid": str(evidence.process.uuid),
        "task_id": evidence.task_id,
        "pending_uuid": str(pending_item.uuid) if pending_item is not None else None,
        "checklist_item_id": evidence.checklist_item_id,
        "original_name": evidence.original_name,
        "mime_type": evidence.mime_type,
        "size_bytes": evidence.size_bytes,
        "sha256": evidence.sha256,
        "uploaded_by": {
            "id": evidence.uploaded_by_id,
            "username": evidence.uploaded_by.username,
        },
        "uploaded_at": evidence.uploaded_at.isoformat(),
        "classification": evidence.classification,
        "download_url": f"/api/v1/evidence/{evidence.uuid}/download/",
    }


def _evidence_queryset(actor: User) -> Any:
    return (
        evidences_for_actor(actor)
        .filter(is_active=True)
        .select_related("process", "task", "pending_item", "uploaded_by")
    )


class EvidenceListUploadView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request: Request) -> Response:
        serializer = EvidenceQuerySerializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)
        data = cast(dict[str, Any], serializer.validated_data)
        rows = _evidence_queryset(cast(User, request.user))
        if data.get("task_id"):
            rows = rows.filter(task_id=data["task_id"])
        if data.get("process_uuid"):
            rows = rows.filter(process__uuid=data["process_uuid"])
        return Response({"results": [evidence_payload(row) for row in rows]})

    def post(self, request: Request) -> Response:
        serializer = UploadEvidenceSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = cast(dict[str, Any], serializer.validated_data)
        try:
            result = UploadEvidenceService().execute(
                UploadEvidenceCommand(
                    actor=cast(User, request.user),
                    task_id=data["task_id"],
                    expected_task_version=data["expected_task_version"],
                    idempotency_key=request.headers.get("Idempotency-Key", ""),
                    pending_uuid=(str(data["pending_uuid"]) if data.get("pending_uuid") else None),
                    checklist_item_id=data.get("checklist_item_id"),
                    classification=data["classification"],
                    uploaded_file=data["file"],
                )
            )
        except IdempotencyConflict as exc:
            return api_error(code="idempotency_conflict", message=str(exc), status_code=409)
        evidence = get_object_or_404(
            _evidence_queryset(cast(User, request.user)),
            pk=result.evidence.pk,
        )
        payload = evidence_payload(evidence)
        payload["idempotency_replayed"] = result.replayed
        return Response(payload, status=200 if result.replayed else 201)


class EvidenceDownloadView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request: Request, evidence_uuid: str) -> FileResponse:
        get_object_or_404(
            _evidence_queryset(cast(User, request.user)),
            uuid=evidence_uuid,
        )
        evidence = RegisterEvidenceDownloadService().execute(
            actor=cast(User, request.user),
            evidence_uuid=evidence_uuid,
        )
        return FileResponse(
            open_evidence_file(evidence),
            as_attachment=True,
            filename=evidence.original_name,
            content_type=evidence.mime_type,
        )
