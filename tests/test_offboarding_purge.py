"""ADR-056: exclusão definitiva do processo não encerrado, com lápide.

É a única operação do sistema que destrói dado. Os testes cobrem o que o
`AGENTS.md` §11 exige de regra crítica — caminho feliz, negação, estado
inválido, concorrência, idempotência, rollback, trilha e dados incompletos — e
mais uma pergunta que só existe aqui: o que sobrevive à exclusão.
"""

# ruff: noqa: F811

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
from django.core.exceptions import PermissionDenied, ValidationError
from django.test import Client

from apps.accounts.models import User
from apps.evidence.models import Evidence
from apps.notifications.models import Notification
from apps.offboarding.models import (
    EmployeeSnapshot,
    OffboardingProcess,
    ProcessActionIdempotency,
    ProcessAuditEvent,
    ProcessChecklistItem,
    ProcessPurgeRecord,
    ProcessSectorTask,
    ProcessStatus,
    ProcessValidationGroup,
)
from apps.offboarding.services import (
    IdempotencyConflict,
    PurgeOffboardingProcessService,
    PurgeProcessCommand,
    purge_preview,
)
from apps.pending_items.models import BlockingLevel, PendingComment, PendingItem
from tests.test_offboarding_cancel_reopen import cancel
from tests.test_offboarding_release import (
    close,
    manager_coordinator,
    ready_process,
    register_processing,
    release,
)
from tests.test_offboarding_start import (  # noqa: F401
    PASSWORD,
    actor,
    configured_draft,
    process,
    start,
)
from tests.test_offboarding_tasks import complete_task, start_task, started_task
from tests.test_pending_items_evidence import (
    configure_evidence_storage,
    create_pending,
    upload_evidence,
)

pytestmark = pytest.mark.django_db


def purge(
    actor: User,
    process: OffboardingProcess,
    *,
    key: str = "purge-1",
    expected_version: int | None = None,
    reason: str = "Processo aberto por engano para a matrícula errada.",
) -> Any:
    return PurgeOffboardingProcessService().execute(
        PurgeProcessCommand(
            actor=actor,
            process_uuid=str(process.uuid),
            expected_version=(
                expected_version if expected_version is not None else process.version
            ),
            idempotency_key=key,
            reason=reason,
        )
    )


def worked_process(
    actor: User,
    process: OffboardingProcess,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> tuple[OffboardingProcess, Any]:
    """Processo com trabalho de verdade: tarefa concluída, pendência e evidência."""

    configure_evidence_storage(tmp_path, monkeypatch)
    task = started_task(actor, process)
    start_task(actor, task)
    task.refresh_from_db()
    # Não bloqueante de propósito: o que interessa aqui é existir pendência, e
    # a bloqueante impediria concluir a tarefa em alguns dos cenários.
    create_pending(actor, task, blocking_level=BlockingLevel.NON_BLOCKING)
    task.refresh_from_db()
    upload_evidence(actor, task)
    task.refresh_from_db()
    process.refresh_from_db()
    return process, task


def logged_client(user: User) -> Client:
    client = Client()
    assert client.login(username=user.username, password=PASSWORD)
    return client


def test_purge_destroys_every_row_and_leaves_the_tombstone(
    actor: User,
    process: OffboardingProcess,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    django_capture_on_commit_callbacks: Any,
) -> None:
    """Caminho feliz: some tudo do processo, sobra o relato do que sumiu."""

    process, task = worked_process(actor, process, tmp_path, monkeypatch)
    complete_task(actor, task)
    process.refresh_from_db()
    manager = manager_coordinator(actor)
    process_pk = process.pk
    process_uuid = process.uuid
    evidence_name = Evidence.objects.get(process=process).file.name
    assert (tmp_path / evidence_name).exists()
    audit_count = ProcessAuditEvent.objects.filter(process=process).count()
    assert audit_count > 0
    # Sem isto, a asserção de "não existe mais" abaixo passaria vazia — e a
    # notificação é o caso menos óbvio, por vir de outro app.
    assert Notification.objects.filter(process=process).exists()

    # O arquivo é removido em `on_commit`; sem capturar o callback, o teste
    # jamais veria a remoção acontecer dentro da transação do pytest.
    with django_capture_on_commit_callbacks(execute=True):
        result = purge(manager, process, reason="Processo duplicado do mesmo colaborador.")

    assert not result.replayed
    assert not OffboardingProcess.objects.filter(pk=process_pk).exists()
    assert not EmployeeSnapshot.objects.filter(process_id=process_pk).exists()
    assert not ProcessSectorTask.objects.filter(process_id=process_pk).exists()
    assert not ProcessChecklistItem.objects.filter(task__process_id=process_pk).exists()
    assert not ProcessValidationGroup.objects.filter(process_id=process_pk).exists()
    assert not ProcessActionIdempotency.objects.filter(process_id=process_pk).exists()
    assert not ProcessAuditEvent.objects.filter(process_id=process_pk).exists()
    assert not PendingItem.objects.filter(process_id=process_pk).exists()
    assert not PendingComment.objects.filter(pending_item__process_id=process_pk).exists()
    assert not Evidence.objects.filter(process_id=process_pk).exists()
    assert not Notification.objects.filter(process_id=process_pk).exists()
    # O arquivo sai do disco depois do commit, não antes.
    assert not (tmp_path / evidence_name).exists()

    record = ProcessPurgeRecord.objects.get()
    assert record.process_uuid == process_uuid
    assert record.purged_by == manager
    assert record.reason == "Processo duplicado do mesmo colaborador."
    assert record.had_material_history
    assert record.employee_name
    assert record.deleted_counts["completed_tasks"] == 1
    assert record.deleted_counts["pending_items"] == 1
    assert record.deleted_counts["evidences"] == 1
    assert record.deleted_counts["audit_events"] == audit_count
    assert record.evidence_files == [evidence_name]
    # A trilha inteira sobrevive dentro da lápide.
    assert len(record.audit_trail) == audit_count
    assert {event["event_type"] for event in record.audit_trail} >= {
        "PROCESS_STARTED",
        "SECTOR_TASK_COMPLETED",
        "PENDING_CREATED",
        "EVIDENCE_UPLOADED",
    }
    assert all(event["actor"] for event in record.audit_trail)


def test_plain_dp_purges_a_draft_that_never_produced_anything(
    actor: User,
    process: OffboardingProcess,
) -> None:
    """Rascunho abandonado é o lixo mais comum; o `DP` apaga sem pedir a gerência."""

    assert process.status == ProcessStatus.DRAFT

    purge(actor, process, reason="Rascunho aberto por engano.")

    assert not OffboardingProcess.objects.filter(pk=process.pk).exists()
    assert ProcessPurgeRecord.objects.get().had_material_history is False


def test_plain_dp_cannot_purge_a_process_with_registered_work(
    actor: User,
    process: OffboardingProcess,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Com pendência e evidência gravadas, excluir passa a ser ato da gerência."""

    process, _task = worked_process(actor, process, tmp_path, monkeypatch)

    with pytest.raises(PermissionDenied, match="gerência do Departamento"):
        purge(actor, process)

    assert OffboardingProcess.objects.filter(pk=process.pk).exists()
    assert not ProcessPurgeRecord.objects.exists()


def test_closed_process_is_never_purged(
    actor: User,
    process: OffboardingProcess,
) -> None:
    """A fronteira da ADR-056: encerrado não se apaga, só se cancela."""

    process, _ = ready_process(actor, process)
    release(actor, process)
    process.refresh_from_db()
    register_processing(actor, process)
    process.refresh_from_db()
    close(actor, process)
    process.refresh_from_db()
    manager = manager_coordinator(actor)

    with pytest.raises(ValidationError, match="encerrado não pode ser excluído"):
        purge(manager, process)

    assert OffboardingProcess.objects.filter(pk=process.pk).exists()


def test_cancelled_process_can_be_purged(
    actor: User,
    process: OffboardingProcess,
) -> None:
    """Cancelado sem serventia é exatamente o que não deve poluir a base."""

    started_task(actor, process)
    process.refresh_from_db()
    cancel(actor, process)
    process.refresh_from_db()
    assert process.status == ProcessStatus.CANCELLED

    purge(actor, process, reason="Cancelado por engano; o processo bom é outro.")

    assert not OffboardingProcess.objects.filter(pk=process.pk).exists()
    assert ProcessPurgeRecord.objects.get().process_status == ProcessStatus.CANCELLED


def test_purge_refuses_a_stale_version(
    actor: User,
    process: OffboardingProcess,
) -> None:
    with pytest.raises(ValidationError, match="alterado por outra sessão"):
        purge(actor, process, expected_version=process.version + 1)

    assert OffboardingProcess.objects.filter(pk=process.pk).exists()


def test_purge_replay_returns_the_same_tombstone(
    actor: User,
    process: OffboardingProcess,
) -> None:
    """O replay não pode 404: a lápide é o registro de idempotência."""

    first = purge(actor, process, key="purge-replay")
    second = purge(actor, process, key="purge-replay")

    assert not first.replayed
    assert second.replayed
    assert second.record.pk == first.record.pk
    assert ProcessPurgeRecord.objects.count() == 1


def test_purge_with_another_key_conflicts_instead_of_pretending(
    actor: User,
    process: OffboardingProcess,
) -> None:
    purge(actor, process, key="purge-original")

    with pytest.raises(IdempotencyConflict):
        purge(actor, process, key="purge-outra-chave")


def test_purge_requires_a_reason(
    actor: User,
    process: OffboardingProcess,
) -> None:
    with pytest.raises(ValidationError):
        purge(actor, process, reason="   ")

    assert OffboardingProcess.objects.filter(pk=process.pk).exists()
    assert not ProcessPurgeRecord.objects.exists()


def test_a_failure_mid_purge_rolls_back_everything_including_the_file(
    actor: User,
    process: OffboardingProcess,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Nada pode sumir pela metade — e o arquivo só cai depois do commit."""

    process, _task = worked_process(actor, process, tmp_path, monkeypatch)
    manager = manager_coordinator(actor)
    evidence_name = Evidence.objects.get(process=process).file.name

    def explode(_process: OffboardingProcess) -> None:
        raise RuntimeError("falha no meio da exclusão")

    monkeypatch.setattr("apps.offboarding.services._delete_process_rows", explode)

    with pytest.raises(RuntimeError):
        purge(manager, process)

    assert OffboardingProcess.objects.filter(pk=process.pk).exists()
    assert Evidence.objects.filter(process=process).exists()
    assert PendingItem.objects.filter(process=process).exists()
    assert not ProcessPurgeRecord.objects.exists()
    assert (tmp_path / evidence_name).exists()


def test_sector_responsible_without_dp_cannot_purge(
    actor: User,
    process: OffboardingProcess,
) -> None:
    responsible = User.objects.create_user(
        username="responsavel.purga",
        email="responsavel.purga@example.invalid",
        password=PASSWORD,
    )

    with pytest.raises(PermissionDenied, match="papel DP"):
        purge(responsible, process)

    assert OffboardingProcess.objects.filter(pk=process.pk).exists()


def test_preview_counts_what_will_be_destroyed_and_refuses_when_it_must(
    actor: User,
    process: OffboardingProcess,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    process, task = worked_process(actor, process, tmp_path, monkeypatch)
    complete_task(actor, task)
    process.refresh_from_db()

    plain = purge_preview(actor, process)
    assert plain.counts["completed_tasks"] == 1
    assert plain.counts["pending_items"] == 1
    assert plain.counts["evidences"] == 1
    assert plain.had_material_history
    assert plain.requires_override
    assert not plain.can_purge
    assert "gerência" in plain.refusal

    managed = purge_preview(manager_coordinator(actor), process)
    assert managed.can_purge
    assert managed.refusal == ""


def test_purge_api_previews_then_deletes_and_replays(
    actor: User,
    process: OffboardingProcess,
) -> None:
    client = logged_client(actor)
    url = f"/api/v1/processes/{process.uuid}/purge/"

    preview = client.get(url)
    assert preview.status_code == 200
    assert preview.json()["can_purge"] is True
    assert preview.json()["counts"]["tasks"] == 0

    payload = {"expected_version": process.version, "reason": "Rascunho errado."}
    response = client.post(
        url,
        data=json.dumps(payload),
        content_type="application/json",
        headers={"Idempotency-Key": "api-purge-1"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["process_uuid"] == str(process.uuid)
    assert body["idempotency_replayed"] is False
    assert not OffboardingProcess.objects.filter(pk=process.pk).exists()

    replay = client.post(
        url,
        data=json.dumps(payload),
        content_type="application/json",
        headers={"Idempotency-Key": "api-purge-1"},
    )
    assert replay.status_code == 200
    assert replay.json()["idempotency_replayed"] is True

    # A prévia do que não existe mais é 404, não 500.
    assert client.get(url).status_code == 404


def test_purge_api_refuses_the_plain_dp_with_403(
    actor: User,
    process: OffboardingProcess,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    process, _task = worked_process(actor, process, tmp_path, monkeypatch)
    client = logged_client(actor)
    url = f"/api/v1/processes/{process.uuid}/purge/"

    preview = client.get(url)
    assert preview.status_code == 200
    assert preview.json()["can_purge"] is False
    assert preview.json()["requires_override"] is True

    response = client.post(
        url,
        data=json.dumps({"expected_version": process.version, "reason": "Não deveria passar."}),
        content_type="application/json",
        headers={"Idempotency-Key": "api-purge-403"},
    )
    assert response.status_code == 403
    assert response.json()["code"] == "permission_denied"
    assert OffboardingProcess.objects.filter(pk=process.pk).exists()


def test_purge_api_requires_the_reason(
    actor: User,
    process: OffboardingProcess,
) -> None:
    client = logged_client(actor)

    response = client.post(
        f"/api/v1/processes/{process.uuid}/purge/",
        data=json.dumps({"expected_version": process.version}),
        content_type="application/json",
        headers={"Idempotency-Key": "api-purge-sem-motivo"},
    )

    assert response.status_code == 400
    assert response.json()["code"] == "validation_error"
    assert OffboardingProcess.objects.filter(pk=process.pk).exists()
