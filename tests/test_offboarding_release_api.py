"""Fase 8, fatia 4: o ciclo formal pela API."""

# ruff: noqa: F811

from __future__ import annotations

import json
from datetime import timedelta
from typing import Any

import pytest
from django.test import Client
from django.utils import timezone

from apps.accounts.models import User
from apps.offboarding.models import (
    OffboardingProcess,
    ProcessStatus,
    SectorTaskStatus,
)
from tests.test_offboarding_release import ready_process
from tests.test_offboarding_start import (  # noqa: F401
    PASSWORD,
    actor,
    process,
)
from tests.test_offboarding_tasks import complete_task, start_task, started_task

pytestmark = pytest.mark.django_db


def logged_client(user: User) -> Client:
    client = Client()
    assert client.login(username=user.username, password=PASSWORD)
    return client


def post(
    client: Client,
    process: OffboardingProcess,
    action: str,
    payload: dict[str, Any],
    *,
    key: str,
) -> Any:
    return client.post(
        f"/api/v1/processes/{process.uuid}/{action}/",
        data=json.dumps(payload),
        content_type="application/json",
        headers={"Idempotency-Key": key},
    )


def superadmin() -> User:
    return User.objects.create_superuser(
        username="super.ciclo",
        email="super.ciclo@example.invalid",
        password=PASSWORD,
    )


def test_readiness_reads_the_situation_and_the_blockers_without_deciding(
    actor: User,
    process: OffboardingProcess,
) -> None:
    started_task(actor, process)
    process.refresh_from_db()
    client = logged_client(actor)

    response = client.get(f"/api/v1/processes/{process.uuid}/readiness/")

    assert response.status_code == 200
    body = response.json()
    assert body["process"]["status"] == ProcessStatus.STARTED
    assert body["process"]["formal"]["released_at"] is None
    assert body["readiness"]["situation"] == "EM_VALIDACAO"
    assert body["readiness"]["is_ready"] is False
    assert any("não foi concluída" in blocker for blocker in body["readiness"]["blockers"])
    assert len(body["tasks"]) == 1
    # A leitura não muda nada: o estado formal continua sendo o do início.
    process.refresh_from_db()
    assert process.status == ProcessStatus.STARTED


def test_the_whole_formal_cycle_walks_through_the_api(
    actor: User,
    process: OffboardingProcess,
) -> None:
    process, _ = ready_process(actor, process)
    client = logged_client(actor)

    released = post(
        client,
        process,
        "release",
        {"expected_version": process.version, "notes": "Consolidado conferido."},
        key="api-release",
    )
    assert released.status_code == 200
    body = released.json()
    assert body["process"]["status"] == ProcessStatus.RELEASED
    assert body["process"]["formal"]["released_by"]["username"] == actor.username
    assert body["process"]["formal"]["release_notes"] == "Consolidado conferido."
    assert body["readiness"]["situation"] == "LIBERADO_PARA_RESCISAO"
    assert body["idempotency_replayed"] is False

    replay = post(
        client,
        process,
        "release",
        {"expected_version": process.version, "notes": "Consolidado conferido."},
        key="api-release",
    )
    assert replay.status_code == 200
    assert replay.json()["idempotency_replayed"] is True

    process.refresh_from_db()
    processed = post(
        client,
        process,
        "processing",
        {
            "expected_version": process.version,
            "termination_reference": "RES-2026-0777",
            "processed_on": timezone.localdate().isoformat(),
            "notes": "Rescisão processada no Senior.",
        },
        key="api-processing",
    )
    assert processed.status_code == 200
    marks = processed.json()["process"]["formal"]
    assert marks["termination_reference"] == "RES-2026-0777"
    assert marks["processing_registered_by"]["username"] == actor.username

    process.refresh_from_db()
    closed = post(
        client,
        process,
        "close",
        {"expected_version": process.version, "notes": "Encerramento formal."},
        key="api-close",
    )
    assert closed.status_code == 200
    assert closed.json()["process"]["status"] == ProcessStatus.CLOSED
    assert closed.json()["readiness"]["situation"] == "ENCERRADO"

    process.refresh_from_db()
    assert process.status == ProcessStatus.CLOSED
    assert process.active_employee_key is None


def test_release_is_refused_with_blockers_a_stale_version_and_a_reused_key(
    actor: User,
    process: OffboardingProcess,
) -> None:
    task = started_task(actor, process)
    process.refresh_from_db()
    client = logged_client(actor)

    blocked = post(
        client,
        process,
        "release",
        {"expected_version": process.version},
        key="api-release-bloqueado",
    )
    assert blocked.status_code == 400
    assert "release" in blocked.json()["details"]

    stale = post(
        client,
        process,
        "release",
        {"expected_version": process.version + 5},
        key="api-release-versao",
    )
    assert stale.status_code == 400

    start_task(actor, task)
    task.refresh_from_db()
    complete_task(actor, task)
    process.refresh_from_db()

    ok = post(
        client,
        process,
        "release",
        {"expected_version": process.version},
        key="api-release-conflito",
    )
    assert ok.status_code == 200

    process.refresh_from_db()
    conflict = post(
        client,
        process,
        "release",
        {"expected_version": process.version, "notes": "Outro parecer."},
        key="api-release-conflito",
    )
    assert conflict.status_code == 409
    assert conflict.json()["code"] == "idempotency_conflict"


def test_processing_refuses_a_future_date_by_contract_of_the_service(
    actor: User,
    process: OffboardingProcess,
) -> None:
    process, _ = ready_process(actor, process)
    client = logged_client(actor)
    post(client, process, "release", {"expected_version": process.version}, key="api-rel")
    process.refresh_from_db()

    response = post(
        client,
        process,
        "processing",
        {
            "expected_version": process.version,
            "termination_reference": "RES-2026-0001",
            "processed_on": (timezone.localdate() + timedelta(days=1)).isoformat(),
        },
        key="api-processing-futuro",
    )

    assert response.status_code == 400
    assert "processed_on" in response.json()["details"]


def test_cancel_needs_a_reason_and_moves_the_process_to_the_cancelled_list(
    actor: User,
    process: OffboardingProcess,
) -> None:
    task = started_task(actor, process)
    process.refresh_from_db()
    client = logged_client(actor)

    without_reason = post(
        client,
        process,
        "cancel",
        {"expected_version": process.version},
        key="api-cancel-sem-motivo",
    )
    assert without_reason.status_code == 400
    assert "reason" in without_reason.json()["details"]

    cancelled = post(
        client,
        process,
        "cancel",
        {"expected_version": process.version, "reason": "Colaborador desistiu."},
        key="api-cancel",
    )
    assert cancelled.status_code == 200
    body = cancelled.json()
    assert body["process"]["status"] == ProcessStatus.CANCELLED
    assert body["process"]["formal"]["cancellation_reason"] == "Colaborador desistiu."
    assert body["process"]["formal"]["cancelled_by"]["username"] == actor.username
    assert body["readiness"]["situation"] == "CANCELADO"
    assert body["tasks"][0]["status"] == SectorTaskStatus.CANCELLED
    assert task.pk == body["tasks"][0]["id"]

    # O hub alcança o cancelado pelo filtro de estado: ele não está em aberto
    # nem entre os concluídos.
    listed = client.get("/api/v1/processes/?status=CANCELADO")
    assert [row["uuid"] for row in listed.json()["results"]] == [str(process.uuid)]
    assert client.get("/api/v1/processes/?open=true").json()["results"] == []
    assert client.get("/api/v1/processes/?completed=true").json()["results"] == []


def test_reopen_answers_403_to_the_dp_and_returns_the_task_for_the_superadmin(
    actor: User,
    process: OffboardingProcess,
) -> None:
    process, task = ready_process(actor, process)
    client = logged_client(actor)
    post(client, process, "release", {"expected_version": process.version}, key="api-rel")
    process.refresh_from_db()

    denied = post(
        client,
        process,
        "reopen",
        {"expected_version": process.version, "reason": "Rescisão anulada."},
        key="api-reopen-dp",
    )
    assert denied.status_code == 403
    assert "SuperAdmin" in denied.json()["message"]

    admin_client = logged_client(superadmin())
    reopened = post(
        admin_client,
        process,
        "reopen",
        {
            "expected_version": process.version,
            "reason": "Rescisão anulada pelo Jurídico.",
            "task_ids": [task.pk],
        },
        key="api-reopen",
    )

    assert reopened.status_code == 200
    body = reopened.json()
    assert body["process"]["status"] == ProcessStatus.STARTED
    assert body["process"]["formal"]["released_at"] is None
    assert body["tasks"][0]["status"] == SectorTaskStatus.IN_ANALYSIS
    assert body["readiness"]["situation"] == "EM_VALIDACAO"


def test_the_formal_cycle_is_out_of_reach_for_who_has_no_dp_role(
    actor: User,
    process: OffboardingProcess,
) -> None:
    process, _ = ready_process(actor, process)
    responsible = User.objects.create_user(
        username="responsavel.ciclo",
        email="responsavel.ciclo@example.invalid",
        password=PASSWORD,
    )
    client = logged_client(responsible)

    assert client.get(f"/api/v1/processes/{process.uuid}/readiness/").status_code == 403
    assert (
        post(
            client,
            process,
            "release",
            {"expected_version": process.version},
            key="api-release-setor",
        ).status_code
        == 403
    )

    process.refresh_from_db()
    assert process.status == ProcessStatus.STARTED
