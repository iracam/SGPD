"""Private evidence upload, authorization and audit services."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, BinaryIO, cast

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import UploadedFile
from django.db import transaction
from django.db.models import Q, QuerySet
from django.utils import timezone

from apps.accounts.models import User
from apps.offboarding.models import (
    OffboardingProcess,
    ProcessActionIdempotency,
    ProcessAuditEvent,
    ProcessChecklistItem,
    ProcessEventType,
    SectorTaskStatus,
)
from apps.offboarding.services import (
    IdempotencyConflict,
    lock_sector_task_and_authority,
    processes_for_actor,
    sector_tasks_for_actor,
)
from apps.pending_items.models import PendingItem
from config.middleware import correlation_id

from .models import Evidence, EvidenceClassification

EVIDENCE_UPLOADED_DESCRIPTION = "Upload privado e idempotente de evidência."
EVIDENCE_DOWNLOADED_DESCRIPTION = "Download autorizado de evidência privada."

ALLOWED_FILE_TYPES: dict[str, frozenset[str]] = {
    ".pdf": frozenset({"application/pdf"}),
    ".png": frozenset({"image/png"}),
    ".jpg": frozenset({"image/jpeg"}),
    ".jpeg": frozenset({"image/jpeg"}),
}
FILE_SIGNATURES: dict[str, tuple[bytes, ...]] = {
    ".pdf": (b"%PDF-",),
    ".png": (b"\x89PNG\r\n\x1a\n",),
    ".jpg": (b"\xff\xd8\xff",),
    ".jpeg": (b"\xff\xd8\xff",),
}


@dataclass(frozen=True, slots=True)
class UploadEvidenceCommand:
    actor: User
    task_id: int
    expected_task_version: int
    idempotency_key: str
    uploaded_file: UploadedFile
    classification: str
    pending_uuid: str | None = None
    checklist_item_id: int | None = None


@dataclass(frozen=True, slots=True)
class EvidenceMutationResult:
    evidence: Evidence
    replayed: bool


def evidences_for_actor(actor: User) -> QuerySet[Evidence]:
    if not actor.is_active:
        return Evidence.objects.none()
    return Evidence.objects.filter(
        Q(task_id__in=sector_tasks_for_actor(actor).values("pk"))
        | Q(process_id__in=processes_for_actor(actor).values("pk"))
    )


def _validated_key(value: str) -> str:
    key = value.strip()
    if not key:
        raise ValidationError({"idempotency_key": "Informe a chave de idempotência."})
    if len(key) > 100:
        raise ValidationError(
            {"idempotency_key": "A chave de idempotência aceita até 100 caracteres."}
        )
    return key


def _canonical_hash(payload: dict[str, Any]) -> str:
    return hashlib.sha256(
        json.dumps(payload, separators=(",", ":"), sort_keys=True, ensure_ascii=False).encode()
    ).hexdigest()


def _file_hash(uploaded_file: UploadedFile) -> str:
    digest = hashlib.sha256()
    for chunk in uploaded_file.chunks():
        digest.update(chunk)
    uploaded_file.seek(0)
    return digest.hexdigest()


def _validated_file(uploaded_file: UploadedFile) -> tuple[str, str, int, str]:
    original_name = Path(uploaded_file.name or "").name.strip()
    if not original_name or len(original_name) > 255:
        raise ValidationError({"file": "O nome do arquivo é inválido."})
    size = uploaded_file.size
    if size is None:
        raise ValidationError({"file": "Não foi possível determinar o tamanho do arquivo."})
    max_size = settings.EVIDENCE_MAX_UPLOAD_BYTES
    if size <= 0:
        raise ValidationError({"file": "O arquivo enviado está vazio."})
    if size > max_size:
        raise ValidationError(
            {"file": f"O arquivo excede o limite de {max_size // (1024 * 1024)} MiB."}
        )
    extension = Path(original_name).suffix.lower()
    mime_type = (uploaded_file.content_type or "").split(";", maxsplit=1)[0].strip().lower()
    if extension not in ALLOWED_FILE_TYPES or mime_type not in ALLOWED_FILE_TYPES[extension]:
        raise ValidationError(
            {"file": "Envie um arquivo PDF, PNG ou JPEG com tipo de conteúdo compatível."}
        )
    header = uploaded_file.read(8)
    uploaded_file.seek(0)
    if not any(header.startswith(signature) for signature in FILE_SIGNATURES[extension]):
        raise ValidationError({"file": "O conteúdo do arquivo não corresponde à extensão."})
    return original_name, mime_type, size, _file_hash(uploaded_file)


def _action(task_id: int) -> str:
    action = f"EVID:{task_id}"
    if len(action) > 30:
        raise ValidationError("O identificador da tarefa excede o contrato de idempotência.")
    return action


def _replay(
    *,
    process: OffboardingProcess,
    actor: User,
    action: str,
    key: str,
    request_hash: str,
) -> EvidenceMutationResult | None:
    previous_rows = list(
        ProcessActionIdempotency.objects.select_for_update().filter(
            process=process, action=action, idempotency_key=key
        )
    )
    if not previous_rows:
        return None
    previous = previous_rows[0]
    if previous.actor_id != actor.pk or previous.request_hash != request_hash:
        raise IdempotencyConflict("A chave de idempotência já foi usada com outro conteúdo.")
    evidence = Evidence.objects.get(uuid=previous.response["evidence_uuid"])
    return EvidenceMutationResult(evidence=evidence, replayed=True)


class UploadEvidenceService:
    def execute(self, command: UploadEvidenceCommand) -> EvidenceMutationResult:
        key = _validated_key(command.idempotency_key)
        original_name, mime_type, size, sha256 = _validated_file(command.uploaded_file)
        request_hash = _canonical_hash(
            {
                "task_id": command.task_id,
                "expected_task_version": command.expected_task_version,
                "pending_uuid": command.pending_uuid,
                "checklist_item_id": command.checklist_item_id,
                "classification": command.classification,
                "original_name": original_name,
                "mime_type": mime_type,
                "size": size,
                "sha256": sha256,
            }
        )
        storage_name: str | None = None
        try:
            with transaction.atomic():
                actor, process, task = lock_sector_task_and_authority(
                    actor=command.actor,
                    task_id=command.task_id,
                    at=timezone.now(),
                    allow_process_coordinator=True,
                )
                action = _action(task.pk)
                replay = _replay(
                    process=process,
                    actor=actor,
                    action=action,
                    key=key,
                    request_hash=request_hash,
                )
                if replay is not None:
                    return replay
                if task.status != SectorTaskStatus.IN_ANALYSIS:
                    raise ValidationError(
                        "Evidências só podem ser enviadas para tarefa em análise."
                    )
                if task.version != command.expected_task_version:
                    raise ValidationError(
                        "A tarefa foi alterada por outra sessão. Recarregue a página."
                    )
                if command.classification not in EvidenceClassification.values:
                    raise ValidationError({"classification": "A classificação é inválida."})

                pending_item = None
                if command.pending_uuid:
                    pending_item = PendingItem.objects.select_for_update().get(
                        uuid=command.pending_uuid,
                        task=task,
                    )
                checklist_item = None
                if command.checklist_item_id is not None:
                    checklist_item = ProcessChecklistItem.objects.select_for_update().get(
                        pk=command.checklist_item_id,
                        task=task,
                    )
                evidence = Evidence(
                    process=process,
                    task=task,
                    pending_item=pending_item,
                    checklist_item=checklist_item,
                    original_name=original_name,
                    mime_type=mime_type,
                    size_bytes=size,
                    sha256=sha256,
                    uploaded_by=actor,
                    classification=command.classification,
                )
                evidence.file.save(original_name, command.uploaded_file, save=False)
                storage_name = evidence.file.name
                evidence.full_clean()
                evidence.save()
                ProcessAuditEvent.objects.create(
                    process=process,
                    event_type=ProcessEventType.EVIDENCE_UPLOADED,
                    actor=actor,
                    description=EVIDENCE_UPLOADED_DESCRIPTION,
                    data={
                        "evidence_uuid": str(evidence.uuid),
                        "task_id": task.pk,
                        "sector_id": task.sector_id,
                        "pending_uuid": (
                            str(pending_item.uuid) if pending_item is not None else None
                        ),
                        "checklist_item_id": command.checklist_item_id,
                        "classification": evidence.classification,
                        "size_bytes": evidence.size_bytes,
                        "sha256": evidence.sha256,
                    },
                    correlation_id=correlation_id.get(),
                )
                ProcessActionIdempotency.objects.create(
                    process=process,
                    action=action,
                    idempotency_key=key,
                    request_hash=request_hash,
                    response={
                        "evidence_uuid": str(evidence.uuid),
                        "task_id": task.pk,
                    },
                    actor=actor,
                )
                return EvidenceMutationResult(evidence=evidence, replayed=False)
        except Exception:
            if storage_name:
                Evidence._meta.get_field("file").storage.delete(storage_name)
            raise


class RegisterEvidenceDownloadService:
    @transaction.atomic
    def execute(self, *, actor: User, evidence_uuid: str) -> Evidence:
        task_id = Evidence.objects.values_list("task_id", flat=True).get(uuid=evidence_uuid)
        locked_actor, process, task = lock_sector_task_and_authority(
            actor=actor,
            task_id=task_id,
            at=timezone.now(),
            allow_process_coordinator=True,
        )
        evidence = Evidence.objects.select_for_update().get(
            uuid=evidence_uuid,
            task=task,
            is_active=True,
        )
        ProcessAuditEvent.objects.create(
            process=process,
            event_type=ProcessEventType.EVIDENCE_DOWNLOADED,
            actor=locked_actor,
            description=EVIDENCE_DOWNLOADED_DESCRIPTION,
            data={
                "evidence_uuid": str(evidence.uuid),
                "task_id": task.pk,
                "classification": evidence.classification,
                "sha256": evidence.sha256,
            },
            correlation_id=correlation_id.get(),
        )
        return evidence


def open_evidence_file(evidence: Evidence) -> BinaryIO:
    return cast(BinaryIO, evidence.file.storage.open(evidence.file.name, "rb"))
