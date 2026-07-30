"""Execution, checklist answers and completion of sector tasks."""

# ruff: noqa: F811

from __future__ import annotations

import json
from typing import Any

import pytest
from django.core.exceptions import PermissionDenied, ValidationError
from django.test import Client
from django.urls import reverse

from apps.accounts.models import ScopeType, User
from apps.offboarding.models import (
    ProcessActionIdempotency,
    ProcessAuditEvent,
    ProcessEventType,
    ProcessSectorTask,
    SectorTaskStatus,
)
from apps.offboarding.services import (
    ChecklistAnswerValue,
    CompleteSectorTaskCommand,
    CompleteSectorTaskService,
    IdempotencyConflict,
    StartSectorTaskCommand,
    StartSectorTaskService,
    sector_tasks_for_actor,
)
from apps.sectors.models import SectorScope
from apps.templates_engine.models import ChecklistResponseType
from tests.test_offboarding_start import (  # noqa: F401
    PASSWORD,
    actor,
    configured_draft,
    process,
    start,
)

pytestmark = pytest.mark.django_db


def started_task(actor: User, process: Any) -> ProcessSectorTask:
    process, _ = configured_draft(actor, process)
    result = start(actor, process)
    return result.tasks[0]


def start_task(
    actor: User,
    task: ProcessSectorTask,
    *,
    key: str = "task-start",
    expected_version: int | None = None,
) -> Any:
    return StartSectorTaskService().execute(
        StartSectorTaskCommand(
            actor=actor,
            task_id=task.pk,
            expected_version=expected_version or task.version,
            idempotency_key=key,
        )
    )


def complete_task(
    actor: User,
    task: ProcessSectorTask,
    *,
    key: str = "task-complete",
    expected_version: int | None = None,
    value: Any = True,
) -> Any:
    item = task.checklist_items.get()
    return CompleteSectorTaskService().execute(
        CompleteSectorTaskCommand(
            actor=actor,
            task_id=task.pk,
            expected_version=expected_version or task.version,
            idempotency_key=key,
            answers=(ChecklistAnswerValue(item_id=item.pk, value=value),),
            notes="Validação concluída.",
        )
    )


def post_json(
    client: Client,
    route_name: str,
    *,
    kwargs: dict[str, Any],
    payload: dict[str, Any],
    key: str,
) -> Any:
    return client.post(
        reverse(route_name, kwargs=kwargs),
        data=json.dumps(payload),
        content_type="application/json",
        HTTP_IDEMPOTENCY_KEY=key,
    )


def test_responsible_starts_answers_and_completes_task_idempotently(
    actor: User,
    process: Any,
) -> None:
    task = started_task(actor, process)
    original_start_version = task.version

    first_start = start_task(actor, task, expected_version=original_start_version)
    replay_start = start_task(actor, task, expected_version=original_start_version)
    task.refresh_from_db()

    assert not first_start.replayed
    assert replay_start.replayed
    assert task.status == SectorTaskStatus.IN_ANALYSIS
    assert task.version == original_start_version + 1

    original_complete_version = task.version
    first_complete = complete_task(
        actor,
        task,
        expected_version=original_complete_version,
    )
    replay_complete = complete_task(
        actor,
        task,
        expected_version=original_complete_version,
    )
    task.refresh_from_db()
    item = task.checklist_items.get()

    assert not first_complete.replayed
    assert replay_complete.replayed
    assert task.status == SectorTaskStatus.COMPLETED
    assert task.completed_by == actor
    assert task.completed_at is not None
    assert task.version == original_complete_version + 1
    assert item.response == {"value": True}
    assert item.answered_by == actor
    assert item.answered_at is not None
    assert (
        ProcessAuditEvent.objects.filter(event_type=ProcessEventType.SECTOR_TASK_STARTED).count()
        == 1
    )
    assert (
        ProcessAuditEvent.objects.filter(event_type=ProcessEventType.SECTOR_TASK_COMPLETED).count()
        == 1
    )
    assert ProcessActionIdempotency.objects.filter(action__startswith="TSTART:").count() == 1
    assert ProcessActionIdempotency.objects.filter(action__startswith="TCOMP:").count() == 1
    completed_event = ProcessAuditEvent.objects.get(
        event_type=ProcessEventType.SECTOR_TASK_COMPLETED
    )
    assert "answers" not in completed_event.data
    assert completed_event.data["answered_item_ids"] == [item.pk]


@pytest.mark.parametrize(
    ("response_type", "config", "value", "stored"),
    [
        (ChecklistResponseType.TEXT, {}, "  conferido  ", "conferido"),
        (ChecklistResponseType.NUMBER, {}, 12.5, 12.5),
        (ChecklistResponseType.DATE, {}, "2026-07-29", "2026-07-29"),
        (
            ChecklistResponseType.SINGLE_CHOICE,
            {"choices": ["Sim", "Não"]},
            "Sim",
            "Sim",
        ),
        (
            ChecklistResponseType.MULTIPLE_CHOICE,
            {"choices": ["A", "B", "C"]},
            ["A", "C"],
            ["A", "C"],
        ),
        (ChecklistResponseType.CONFIRMATION, {}, True, True),
    ],
)
def test_complete_validates_and_normalizes_supported_answer_types(
    actor: User,
    process: Any,
    response_type: str,
    config: dict[str, Any],
    value: Any,
    stored: Any,
) -> None:
    task = started_task(actor, process)
    start_task(actor, task)
    task.refresh_from_db()
    item = task.checklist_items.get()
    item.response_type_snapshot = response_type
    item.config_snapshot = config
    item.save(update_fields=("response_type_snapshot", "config_snapshot"))

    complete_task(actor, task, value=value)

    item.refresh_from_db()
    assert item.response == {"value": stored}


def test_superadmin_has_all_tasks_and_can_mutate_without_sector_link(
    actor: User,
    process: Any,
) -> None:
    task = started_task(actor, process)
    outsider = User.objects.create_user(
        username="fora.setor",
        email="fora.setor@example.invalid",
        password=PASSWORD,
        first_name="Fora",
        last_name="Setor",
        is_superuser=True,
    )

    assert list(sector_tasks_for_actor(outsider)) == [task]
    start_task(outsider, task)
    task.refresh_from_db()
    assert task.status == SectorTaskStatus.IN_ANALYSIS
    assert (
        ProcessAuditEvent.objects.get(event_type=ProcessEventType.SECTOR_TASK_STARTED).actor
        == outsider
    )


def test_task_authority_is_removed_when_current_sector_link_is_revoked(
    actor: User,
    process: Any,
) -> None:
    task = started_task(actor, process)
    assert "SELECT DISTINCT" not in str(sector_tasks_for_actor(actor).query).upper()

    responsibility = task.sector.responsibles.get(user=actor)
    responsibility.is_active = False
    responsibility.revoked_by = actor
    responsibility.revoked_at = responsibility.updated_at
    responsibility.save(
        update_fields=("is_active", "revoked_by", "revoked_at"),
    )
    assert list(sector_tasks_for_actor(actor)) == []
    with pytest.raises(PermissionDenied, match="responsabilidade vigente"):
        start_task(actor, task)


def test_scope_change_immediately_removes_task_authority(
    actor: User,
    process: Any,
) -> None:
    task = started_task(actor, process)
    SectorScope.objects.filter(sector=task.sector).delete()
    scope = SectorScope(
        sector=task.sector,
        scope_type=ScopeType.COMPANY,
        company_code=999,
    )
    scope.full_clean()
    scope.save()

    assert list(sector_tasks_for_actor(actor)) == []
    with pytest.raises(PermissionDenied, match="responsabilidade vigente"):
        start_task(actor, task)


def test_complete_rejects_invalid_state_missing_answer_and_stale_version(
    actor: User,
    process: Any,
) -> None:
    task = started_task(actor, process)
    item = task.checklist_items.get()

    with pytest.raises(ValidationError, match="em análise"):
        CompleteSectorTaskService().execute(
            CompleteSectorTaskCommand(
                actor=actor,
                task_id=task.pk,
                expected_version=task.version,
                idempotency_key="complete-before-start",
                answers=(ChecklistAnswerValue(item_id=item.pk, value=True),),
            )
        )
    with pytest.raises(ValidationError, match="outra sessão"):
        start_task(actor, task, expected_version=999)

    start_task(actor, task)
    task.refresh_from_db()
    with pytest.raises(ValidationError, match="exige resposta"):
        CompleteSectorTaskService().execute(
            CompleteSectorTaskCommand(
                actor=actor,
                task_id=task.pk,
                expected_version=task.version,
                idempotency_key="complete-missing-answer",
                answers=(),
            )
        )
    task.refresh_from_db()
    item.refresh_from_db()
    assert task.status == SectorTaskStatus.IN_ANALYSIS
    assert item.response is None
    assert not ProcessAuditEvent.objects.filter(
        event_type=ProcessEventType.SECTOR_TASK_COMPLETED
    ).exists()


def test_complete_rejects_evidence_until_its_domain_is_available(
    actor: User,
    process: Any,
) -> None:
    task = started_task(actor, process)
    start_task(actor, task)
    task.refresh_from_db()
    item = task.checklist_items.get()
    item.requires_evidence = True
    item.save(update_fields=("requires_evidence",))

    with pytest.raises(ValidationError, match="exige evidência"):
        complete_task(actor, task)

    task.refresh_from_db()
    assert task.status == SectorTaskStatus.IN_ANALYSIS
    assert task.completed_at is None


def test_task_idempotency_rejects_divergent_content(
    actor: User,
    process: Any,
) -> None:
    task = started_task(actor, process)
    expected_version = task.version
    start_task(actor, task, key="same-task-key", expected_version=expected_version)

    with pytest.raises(IdempotencyConflict, match="outro conteúdo"):
        start_task(actor, task, key="same-task-key", expected_version=999)


def test_audit_failure_rolls_back_task_transition(
    actor: User,
    process: Any,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    task = started_task(actor, process)

    def fail_audit(**kwargs: Any) -> None:
        raise RuntimeError("audit unavailable")

    monkeypatch.setattr(ProcessAuditEvent.objects, "create", fail_audit)
    with pytest.raises(RuntimeError, match="audit unavailable"):
        start_task(actor, task, key="rollback-audit")

    task.refresh_from_db()
    assert task.status == SectorTaskStatus.PENDING
    assert task.version == 1
    assert not ProcessActionIdempotency.objects.filter(action__startswith="TSTART:").exists()


def test_task_api_lists_starts_and_completes_only_authorized_task(
    actor: User,
    process: Any,
    client: Client,
) -> None:
    task = started_task(actor, process)
    client.force_login(actor)

    listing = client.get(reverse("offboarding-task-api:task-list"))
    assert listing.status_code == 200
    assert [row["id"] for row in listing.json()["results"]] == [task.pk]
    item_id = listing.json()["results"][0]["checklist_items"][0]["id"]

    start_response = post_json(
        client,
        "offboarding-task-api:task-start",
        kwargs={"task_id": task.pk},
        payload={"expected_version": task.version},
        key="api-task-start",
    )
    assert start_response.status_code == 200
    assert start_response.json()["status"] == SectorTaskStatus.IN_ANALYSIS
    assert not start_response.json()["idempotency_replayed"]

    complete_response = post_json(
        client,
        "offboarding-task-api:task-complete",
        kwargs={"task_id": task.pk},
        payload={
            "expected_version": start_response.json()["version"],
            "answers": [{"item_id": item_id, "value": True}],
            "notes": "Tudo validado.",
        },
        key="api-task-complete",
    )
    assert complete_response.status_code == 200
    assert complete_response.json()["status"] == SectorTaskStatus.COMPLETED
    assert complete_response.json()["checklist_items"][0]["response"] is True


def test_process_api_classifies_all_sector_tasks_completed(
    actor: User,
    process: Any,
    client: Client,
) -> None:
    task = started_task(actor, process)
    client.force_login(actor)
    route = reverse("offboarding-api:process-list")

    before = client.get(route, {"completed": "true"})
    assert before.status_code == 200
    assert before.json()["results"] == []
    open_before = client.get(route, {"open": "true"})
    assert open_before.status_code == 200
    assert [row["uuid"] for row in open_before.json()["results"]] == [str(process.uuid)]

    start_task(actor, task)
    task.refresh_from_db()
    complete_task(actor, task)

    after = client.get(route, {"completed": "true"})
    assert after.status_code == 200
    assert [row["uuid"] for row in after.json()["results"]] == [str(process.uuid)]
    assert after.json()["results"][0]["completion_at"] is not None
    open_after = client.get(route, {"open": "true"})
    assert open_after.status_code == 200
    assert open_after.json()["results"] == []

    conflicting = client.get(route, {"open": "true", "completed": "true"})
    assert conflicting.status_code == 400

    tasks_route = reverse(
        "offboarding-api:process-tasks",
        kwargs={"process_uuid": process.uuid},
    )
    tasks = client.get(tasks_route, {"status": SectorTaskStatus.COMPLETED})
    assert tasks.status_code == 200
    assert [row["id"] for row in tasks.json()["results"]] == [task.pk]
    assert tasks.json()["results"][0]["sector"]["name"] == task.sector_name_snapshot

    unauthorized = User.objects.create_user(
        username="sem.dp.process.tasks",
        email="sem.dp.process.tasks@example.invalid",
        password=PASSWORD,
    )
    client.force_login(unauthorized)
    assert client.get(tasks_route).status_code == 403

    superadmin = User.objects.create_superuser(
        username="super.process.tasks",
        email="super.process.tasks@example.invalid",
        password=PASSWORD,
    )
    client.force_login(superadmin)
    assert client.get(tasks_route).status_code == 200


def test_superadmin_api_lists_any_task_without_sector_link(
    actor: User,
    process: Any,
    client: Client,
) -> None:
    task = started_task(actor, process)
    superadmin = User.objects.create_superuser(
        username="tarefas.superadmin",
        email="tarefas.superadmin@example.invalid",
        password=PASSWORD,
    )
    client.force_login(superadmin)

    listing = client.get(reverse("offboarding-task-api:task-list"))
    detail = client.get(reverse("offboarding-task-api:task-detail", kwargs={"task_id": task.pk}))

    assert listing.status_code == 200
    assert [row["id"] for row in listing.json()["results"]] == [task.pk]
    assert detail.status_code == 200
    assert detail.json()["id"] == task.pk


def test_task_api_rejects_anonymous_and_unrelated_user(
    actor: User,
    process: Any,
    client: Client,
) -> None:
    task = started_task(actor, process)
    route = reverse("offboarding-task-api:task-detail", kwargs={"task_id": task.pk})

    assert client.get(route).status_code == 401

    outsider = User.objects.create_user(
        username="sem.tarefa",
        email="sem.tarefa@example.invalid",
        password=PASSWORD,
    )
    client.force_login(outsider)
    assert client.get(route).status_code == 404
