"""Phase 5: pending items, private evidence and task-completion blockers."""

# ruff: noqa: F811

from __future__ import annotations

import hashlib
import json
from datetime import timedelta
from decimal import Decimal
from pathlib import Path
from typing import Any, cast

import pytest
from django.core.exceptions import PermissionDenied, ValidationError
from django.core.files.storage import FileSystemStorage
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db.models import QuerySet
from django.test import Client
from django.urls import reverse
from django.utils import timezone

from apps.accounts.models import Role, RoleAssignment, ScopeType, User, build_scope_key
from apps.evidence.models import Evidence
from apps.evidence.services import UploadEvidenceCommand, UploadEvidenceService
from apps.offboarding.models import ProcessAuditEvent, ProcessEventType, SectorTaskStatus
from apps.pending_items.models import (
    BlockingLevel,
    PendingCategory,
    PendingComment,
    PendingItem,
    PendingStatus,
)
from apps.pending_items.services import (
    AddPendingCommentCommand,
    AddPendingCommentService,
    ChangePendingStatusCommand,
    ChangePendingStatusService,
    CreatePendingItemCommand,
    CreatePendingItemService,
    PendingLineValue,
)
from tests.test_offboarding_start import (  # noqa: F401
    PASSWORD,
    actor,
    configured_draft,
    process,
    start,
)
from tests.test_offboarding_tasks import complete_task, start_task, started_task

pytestmark = pytest.mark.django_db

PNG_BYTES = b"\x89PNG\r\n\x1a\n" + b"private-evidence"


def create_pending(
    actor: User,
    task: Any,
    *,
    key: str = "pending-create",
    blocking_level: str = BlockingLevel.BLOCKING,
) -> Any:
    return CreatePendingItemService().execute(
        CreatePendingItemCommand(
            actor=actor,
            task_id=task.pk,
            expected_task_version=task.version,
            idempotency_key=key,
            category=PendingCategory.EQUIPMENT,
            title="Notebook não devolvido",
            description="Aguardar devolução do equipamento corporativo.",
            blocking_level=blocking_level,
            checklist_item_id=task.checklist_items.get().pk,
            items=(
                PendingLineValue(
                    description="Notebook Dell",
                    asset_tag="PAT-123",
                    serial_number="SN-ABC",
                    quantity=Decimal("1"),
                    unit="UN",
                ),
            ),
        )
    )


def configure_evidence_storage(path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    storage = FileSystemStorage(
        location=path,
        base_url=None,
        file_permissions_mode=0o600,
        directory_permissions_mode=0o700,
    )
    monkeypatch.setattr(Evidence._meta.get_field("file"), "storage", storage)


def upload_evidence(
    actor: User,
    task: Any,
    *,
    key: str = "evidence-upload",
    pending_uuid: str | None = None,
    checklist_item_id: int | None = None,
) -> Any:
    return UploadEvidenceService().execute(
        UploadEvidenceCommand(
            actor=actor,
            task_id=task.pk,
            expected_task_version=task.version,
            idempotency_key=key,
            pending_uuid=pending_uuid,
            checklist_item_id=checklist_item_id,
            classification="RESTRITA",
            uploaded_file=SimpleUploadedFile(
                "comprovante.png",
                PNG_BYTES,
                content_type="image/png",
            ),
        )
    )


def test_pending_item_lifecycle_is_idempotent_versioned_and_audited(
    actor: User,
    process: Any,
) -> None:
    task = started_task(actor, process)
    start_task(actor, task)
    task.refresh_from_db()

    created = create_pending(actor, task)
    replay = create_pending(actor, task)
    pending_item = created.pending_item

    assert not created.replayed
    assert replay.replayed
    assert replay.pending_item.pk == pending_item.pk
    assert pending_item.items.get().asset_tag == "PAT-123"
    assert (
        ProcessAuditEvent.objects.filter(event_type=ProcessEventType.PENDING_CREATED).count() == 1
    )

    commented = AddPendingCommentService().execute(
        AddPendingCommentCommand(
            actor=actor,
            pending_uuid=str(pending_item.uuid),
            expected_version=pending_item.version,
            idempotency_key="pending-comment",
            comment="Colaborador avisado.",
        )
    )
    transitioned = ChangePendingStatusService().execute(
        ChangePendingStatusCommand(
            actor=actor,
            pending_uuid=str(pending_item.uuid),
            expected_version=commented.pending_item.version,
            idempotency_key="pending-regularization",
            status=PendingStatus.IN_REGULARIZATION,
            comment="Devolução agendada.",
        )
    )

    assert transitioned.pending_item.status == PendingStatus.IN_REGULARIZATION
    assert transitioned.pending_item.version == 3
    assert list(transitioned.pending_item.comments.values_list("text", flat=True)) == [
        "Colaborador avisado.",
        "Devolução agendada.",
    ]
    assert (
        ProcessAuditEvent.objects.filter(event_type=ProcessEventType.PENDING_COMMENTED).count() == 1
    )
    assert (
        ProcessAuditEvent.objects.filter(event_type=ProcessEventType.PENDING_STATUS_CHANGED).count()
        == 1
    )


def test_locked_phase_five_replays_never_use_first_with_implicit_limit(
    actor: User,
    process: Any,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    configure_evidence_storage(tmp_path, monkeypatch)
    original_first = QuerySet.first

    def reject_locked_first(queryset: QuerySet[Any]) -> Any:
        if queryset.query.select_for_update:
            raise AssertionError("select_for_update não pode usar LIMIT implícito no Oracle.")
        return original_first(queryset)

    monkeypatch.setattr(QuerySet, "first", reject_locked_first)
    task = started_task(actor, process)
    start_task(actor, task)
    task.refresh_from_db()

    create_pending(actor, task, key="oracle-pending-replay")
    create_pending(actor, task, key="oracle-pending-replay")
    upload_evidence(actor, task, key="oracle-evidence-replay")
    replay = upload_evidence(actor, task, key="oracle-evidence-replay")

    assert replay.replayed


def test_pending_item_rejects_wrong_state_stale_version_and_unrelated_actor(
    actor: User,
    process: Any,
) -> None:
    task = started_task(actor, process)
    with pytest.raises(ValidationError, match="em análise"):
        create_pending(actor, task)

    start_task(actor, task)
    task.refresh_from_db()
    pending_item = create_pending(actor, task).pending_item
    with pytest.raises(ValidationError, match="outra sessão"):
        AddPendingCommentService().execute(
            AddPendingCommentCommand(
                actor=actor,
                pending_uuid=str(pending_item.uuid),
                expected_version=99,
                idempotency_key="stale-comment",
                comment="Comentário.",
            )
        )

    outsider = User.objects.create_user(
        username="sem-pendencia",
        email="sem-pendencia@example.invalid",
        password=PASSWORD,
    )
    with pytest.raises(PermissionDenied, match="responsabilidade vigente"):
        AddPendingCommentService().execute(
            AddPendingCommentCommand(
                actor=outsider,
                pending_uuid=str(pending_item.uuid),
                expected_version=pending_item.version,
                idempotency_key="unauthorized-comment",
                comment="Não autorizado.",
            )
        )


def test_dp_and_superadmin_operate_without_sector_link(
    actor: User,
    process: Any,
) -> None:
    task = started_task(actor, process)
    start_task(actor, task)
    task.refresh_from_db()
    role = Role.objects.get(code="DP")
    dp = User.objects.create_user(
        username="dp-sem-setor",
        email="dp-sem-setor@example.invalid",
        password=PASSWORD,
    )
    RoleAssignment.objects.create(
        user=dp,
        role=role,
        scope_type=ScopeType.GLOBAL,
        scope_key=build_scope_key(ScopeType.GLOBAL, None, None),
        valid_from=timezone.now() - timedelta(hours=1),
        assigned_by=actor,
    )
    pending_item = create_pending(dp, task, key="dp-create").pending_item

    superadmin = User.objects.create_superuser(
        username="super-fase-cinco",
        email="super-fase-cinco@example.invalid",
        password=PASSWORD,
    )
    result = AddPendingCommentService().execute(
        AddPendingCommentCommand(
            actor=superadmin,
            pending_uuid=str(pending_item.uuid),
            expected_version=pending_item.version,
            idempotency_key="super-comment",
            comment="Revisão global.",
        )
    )

    assert result.pending_item.comments.get().author == superadmin


def test_pending_audit_failure_rolls_back_parent_lines_and_idempotency(
    actor: User,
    process: Any,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    task = started_task(actor, process)
    start_task(actor, task)
    task.refresh_from_db()

    def fail_audit(**kwargs: Any) -> None:
        raise RuntimeError("audit unavailable")

    monkeypatch.setattr(ProcessAuditEvent.objects, "create", fail_audit)
    with pytest.raises(RuntimeError, match="audit unavailable"):
        create_pending(actor, task)

    assert not PendingItem.objects.exists()
    assert not PendingComment.objects.exists()


def test_blocking_pending_prevents_completion_until_regularized(
    actor: User,
    process: Any,
) -> None:
    task = started_task(actor, process)
    start_task(actor, task)
    task.refresh_from_db()
    pending_item = create_pending(actor, task).pending_item

    with pytest.raises(ValidationError, match="pendência bloqueante"):
        complete_task(actor, task)

    for status, key in (
        (PendingStatus.IN_REGULARIZATION, "status-in-progress"),
        (PendingStatus.REGULARIZED, "status-regularized"),
    ):
        pending_item = (
            ChangePendingStatusService()
            .execute(
                ChangePendingStatusCommand(
                    actor=actor,
                    pending_uuid=str(pending_item.uuid),
                    expected_version=pending_item.version,
                    idempotency_key=key,
                    status=status,
                    comment=f"Transição para {status}.",
                )
            )
            .pending_item
        )

    result = complete_task(actor, task)
    assert result.task.status == SectorTaskStatus.COMPLETED


def test_private_evidence_hash_download_and_required_item_completion(
    actor: User,
    process: Any,
    client: Client,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    configure_evidence_storage(tmp_path, monkeypatch)
    task = started_task(actor, process)
    start_task(actor, task)
    task.refresh_from_db()
    checklist_item = task.checklist_items.get()
    checklist_item.requires_evidence = True
    checklist_item.save(update_fields=("requires_evidence",))

    with pytest.raises(ValidationError, match="exige evidência"):
        complete_task(actor, task)

    first = upload_evidence(
        actor,
        task,
        checklist_item_id=checklist_item.pk,
    )
    replay = upload_evidence(
        actor,
        task,
        checklist_item_id=checklist_item.pk,
    )
    evidence = first.evidence
    assert not first.replayed
    assert replay.replayed
    assert evidence.sha256 == hashlib.sha256(PNG_BYTES).hexdigest()
    assert (tmp_path / evidence.file.name).exists()
    assert str(tmp_path) not in evidence.file.name

    complete_task(actor, task)
    client.force_login(actor)
    download = client.get(
        reverse("evidence-api:evidence-download", kwargs={"evidence_uuid": evidence.uuid})
    )
    assert download.status_code == 200
    assert download["Content-Type"] == "image/png"
    assert b"".join(cast(Any, download).streaming_content) == PNG_BYTES
    assert (
        ProcessAuditEvent.objects.filter(event_type=ProcessEventType.EVIDENCE_DOWNLOADED).count()
        == 1
    )


def test_evidence_audit_failure_removes_private_file_and_database_row(
    actor: User,
    process: Any,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    configure_evidence_storage(tmp_path, monkeypatch)
    task = started_task(actor, process)
    start_task(actor, task)
    task.refresh_from_db()

    def fail_audit(**kwargs: Any) -> None:
        raise RuntimeError("audit unavailable")

    monkeypatch.setattr(ProcessAuditEvent.objects, "create", fail_audit)
    with pytest.raises(RuntimeError, match="audit unavailable"):
        upload_evidence(actor, task)

    assert not Evidence.objects.exists()
    assert not list(tmp_path.rglob("*.png"))


def test_phase_five_api_keeps_storage_private_and_denies_unrelated_user(
    actor: User,
    process: Any,
    client: Client,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    configure_evidence_storage(tmp_path, monkeypatch)
    task = started_task(actor, process)
    start_task(actor, task)
    task.refresh_from_db()
    client.force_login(actor)

    pending_response = client.post(
        reverse("pending-items-api:pending-list"),
        data=json.dumps(
            {
                "task_id": task.pk,
                "expected_task_version": task.version,
                "category": "DOCUMENTO",
                "title": "Documento pendente",
                "description": "Aguardar comprovante.",
                "blocking_level": "NAO_BLOQUEANTE",
                "items": [],
            }
        ),
        content_type="application/json",
        HTTP_IDEMPOTENCY_KEY="api-pending",
    )
    assert pending_response.status_code == 201
    assert pending_response.json()["status"] == "ABERTA"

    upload = client.post(
        reverse("evidence-api:evidence-list"),
        data={
            "task_id": task.pk,
            "expected_task_version": task.version,
            "pending_uuid": pending_response.json()["uuid"],
            "classification": "RESTRITA",
            "file": SimpleUploadedFile(
                "prova.png",
                PNG_BYTES,
                content_type="image/png",
            ),
        },
        HTTP_IDEMPOTENCY_KEY="api-evidence",
    )
    assert upload.status_code == 201
    body = upload.json()
    assert "file" not in body
    assert "path" not in body
    assert str(tmp_path) not in upload.content.decode()

    outsider = User.objects.create_user(
        username="fora-fase-cinco",
        email="fora-fase-cinco@example.invalid",
        password=PASSWORD,
    )
    client.force_login(outsider)
    assert (
        client.get(
            reverse(
                "evidence-api:evidence-download",
                kwargs={"evidence_uuid": body["uuid"]},
            )
        ).status_code
        == 404
    )
