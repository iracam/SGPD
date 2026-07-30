"""Opening an offboarding draft with scoped DP authorization and snapshot."""

from __future__ import annotations

from dataclasses import replace
from datetime import UTC, date, datetime, timedelta
from typing import Any, cast

import pytest
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import IntegrityError
from django.test import Client
from django.urls import reverse
from django.utils import timezone

from apps.accounts.models import (
    PEOPLE_DEPARTMENT_ROLE_CODE,
    Role,
    RoleAssignment,
    ScopeType,
    User,
    build_scope_key,
)
from apps.integrations.senior.dto import EmployeeDetail
from apps.integrations.senior.exceptions import SeniorUnavailableError
from apps.integrations.senior.repository import SeniorRepository
from apps.offboarding.api import ProcessListCreateView
from apps.offboarding.models import (
    EmployeeSnapshot,
    OffboardingProcess,
    ProcessAuditEvent,
    ProcessEventType,
    ProcessStatus,
)
from apps.offboarding.services import (
    OpenOffboardingProcessCommand,
    OpenOffboardingProcessService,
    processes_for_actor,
)
from apps.sectors.models import SectorResponsible, SectorScope, ValidationSector

pytestmark = pytest.mark.django_db

PASSWORD = "Offboarding-only!2026"


def employee_detail() -> EmployeeDetail:
    return EmployeeDetail(
        company=1,
        branch=2,
        legal_name="Empresa de Teste",
        employee_type=1,
        employee_type_description="Empregado",
        registration=123,
        name="Pessoa de Teste",
        admission_date=datetime(2020, 1, 2, tzinfo=UTC),
        leave_code=1,
        leave_description="Trabalhando",
        leave_date=None,
        job_structure=1,
        job_code="DEV",
        job_description="Desenvolvedor",
        cost_center="100",
        cost_center_description=None,
        source_updated_at=datetime(2026, 7, 27, 12, tzinfo=UTC),
        masked_cpf="***.456.***-**",
    )


class RepositoryStub:
    employee: EmployeeDetail | None = employee_detail()
    error: Exception | None = None
    calls = 0

    def get_employee(
        self,
        *,
        company: int,
        branch: int,
        employee_type: int,
        registration: int,
    ) -> EmployeeDetail | None:
        RepositoryStub.calls += 1
        if self.error is not None:
            raise self.error
        return self.employee


@pytest.fixture(autouse=True)
def reset_repository_stub() -> None:
    RepositoryStub.employee = employee_detail()
    RepositoryStub.error = None
    RepositoryStub.calls = 0


@pytest.fixture
def dp_role() -> Role:
    return Role.objects.create(
        code=PEOPLE_DEPARTMENT_ROLE_CODE,
        name="Departamento Pessoal",
    )


@pytest.fixture
def actor(dp_role: Role) -> User:
    user = User.objects.create_user(
        username="dp.operador",
        email="dp.operador@example.invalid",
        password=PASSWORD,
        first_name="Operador",
        last_name="DP",
    )
    RoleAssignment.objects.create(
        user=user,
        role=dp_role,
        scope_type=ScopeType.GLOBAL,
        scope_key=build_scope_key(ScopeType.GLOBAL, None, None),
        valid_from=timezone.now() - timedelta(days=1),
        assigned_by=user,
    )
    return user


@pytest.fixture
def actor_client(actor: User) -> Client:
    client = Client()
    client.force_login(actor)
    return client


def command(actor: User, **overrides: Any) -> OpenOffboardingProcessCommand:
    values: dict[str, Any] = {
        "actor": actor,
        "company_code": 1,
        "branch_code": 2,
        "employee_type_code": 1,
        "employee_registration": 123,
        "planned_termination_date": date(2026, 8, 15),
        "due_date": date(2026, 8, 14),
        "reason": "Reorganização da área.",
        "priority": "Alta",
        "notes": "Abertura controlada.",
    }
    values.update(overrides)
    return OpenOffboardingProcessCommand(**values)


def service(repository: RepositoryStub | None = None) -> OpenOffboardingProcessService:
    return OpenOffboardingProcessService(
        repository=cast(SeniorRepository, repository or RepositoryStub())
    )


def api_payload() -> dict[str, Any]:
    return {
        "company_code": 1,
        "branch_code": 2,
        "employee_type_code": 1,
        "employee_registration": 123,
        "planned_termination_date": "2026-08-15",
        "due_date": "2026-08-14",
        "reason": "Reorganização da área.",
        "priority": "Alta",
        "notes": "Abertura controlada.",
    }


def post_json(client: Client, payload: dict[str, Any]) -> Any:
    return client.post(
        reverse("offboarding-api:process-list"),
        data=payload,
        content_type="application/json",
    )


def test_open_process_creates_draft_immutable_snapshot_and_audit(
    actor: User,
) -> None:
    process = service().execute(command(actor))

    assert process.status == ProcessStatus.DRAFT
    assert process.active_employee_key == "1:2:1:123"
    assert process.opened_by == actor
    assert process.version == 1

    snapshot = process.employee_snapshot
    assert snapshot.employee_name == "Pessoa de Teste"
    assert snapshot.branch_legal_name == "Empresa de Teste"
    assert snapshot.masked_cpf == "***.456.***-**"
    assert snapshot.source_updated_at == datetime(2026, 7, 27, 12, tzinfo=UTC)

    event = ProcessAuditEvent.objects.get()
    assert event.event_type == ProcessEventType.OPENED
    assert event.actor == actor
    assert event.process == process
    assert event.data["employee_registration"] == 123
    assert "manager_user_id" not in event.data
    assert "employee_name" not in event.data
    assert "masked_cpf" not in event.data


def test_superadmin_opens_process_without_explicit_dp_assignment() -> None:
    superuser = User.objects.create_superuser(
        username="tecnico",
        email="tecnico@example.invalid",
        password=PASSWORD,
        first_name="Super",
        last_name="Admin",
    )

    process = service().execute(command(superuser))

    assert RepositoryStub.calls == 1
    assert process.opened_by == superuser
    assert process.status == ProcessStatus.DRAFT
    assert ProcessAuditEvent.objects.get(process=process).actor == superuser


def test_open_process_rejects_responsible_sector_without_dp() -> None:
    responsible = User.objects.create_user(
        username="responsavel.dp",
        email="responsavel.dp@example.invalid",
        password=PASSWORD,
        first_name="Responsável",
        last_name="Setor",
    )
    sector = ValidationSector.objects.create(
        code="TECNOLOGIA",
        name="Tecnologia",
        default_due_hours=24,
    )
    sector_scope = SectorScope(sector=sector, scope_type=ScopeType.GLOBAL)
    sector_scope.full_clean()
    sector_scope.save()
    SectorResponsible.objects.create(
        sector=sector,
        user=responsible,
        assigned_by=responsible,
        updated_by=responsible,
    )

    with pytest.raises(PermissionDenied, match="papel DP"):
        service().execute(command(responsible))

    assert RepositoryStub.calls == 0


def test_open_process_enforces_dp_company_and_branch_scope(
    dp_role: Role,
) -> None:
    scoped_actor = User.objects.create_user(
        username="dp.escopado",
        email="dp.escopado@example.invalid",
        password=PASSWORD,
        first_name="DP",
        last_name="Escopado",
    )
    RoleAssignment.objects.create(
        user=scoped_actor,
        role=dp_role,
        scope_type=ScopeType.BRANCH,
        company_code=1,
        branch_code=3,
        scope_key=build_scope_key(ScopeType.BRANCH, 1, 3),
        assigned_by=scoped_actor,
    )

    with pytest.raises(PermissionDenied, match="empresa e a filial"):
        service().execute(command(scoped_actor))

    assert RepositoryStub.calls == 0


def test_open_process_rechecks_role_after_senior_query(
    actor: User,
) -> None:
    assignment = RoleAssignment.objects.get(user=actor)

    class RevokingRepository(RepositoryStub):
        def get_employee(self, **kwargs: Any) -> EmployeeDetail | None:
            assignment.is_active = False
            assignment.revoked_by = actor
            assignment.revoked_at = timezone.now()
            assignment.save(update_fields=("is_active", "revoked_by", "revoked_at"))
            return super().get_employee(**kwargs)

    with pytest.raises(PermissionDenied, match="papel DP"):
        service(RevokingRepository()).execute(command(actor))

    assert RepositoryStub.calls == 1
    assert not OffboardingProcess.objects.exists()
    assert not ProcessAuditEvent.objects.exists()


def test_open_process_rejects_stale_or_ineligible_employee(
    actor: User,
) -> None:
    repository = RepositoryStub()
    repository.employee = None

    with pytest.raises(ValidationError, match="deixou de ser elegível"):
        service(repository).execute(command(actor))

    assert not OffboardingProcess.objects.exists()


def test_open_process_prevents_duplicate_active_employee(
    actor: User,
) -> None:
    first = service().execute(command(actor))

    with pytest.raises(ValidationError, match="Já existe um processo"):
        service().execute(command(actor))

    assert OffboardingProcess.objects.get() == first
    assert EmployeeSnapshot.objects.count() == 1
    assert ProcessAuditEvent.objects.count() == 1


def test_audit_failure_rolls_back_process_and_snapshot(
    actor: User,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fail_create(**kwargs: Any) -> None:
        raise IntegrityError("audit unavailable")

    monkeypatch.setattr(ProcessAuditEvent.objects, "create", fail_create)

    with pytest.raises(IntegrityError, match="audit unavailable"):
        service().execute(command(actor))

    assert not OffboardingProcess.objects.exists()
    assert not EmployeeSnapshot.objects.exists()


def test_snapshot_and_audit_are_append_only(actor: User) -> None:
    process = service().execute(command(actor))
    snapshot = process.employee_snapshot
    event = ProcessAuditEvent.objects.get()

    snapshot.employee_name = "Nome alterado"
    with pytest.raises(ValidationError, match="imutável"):
        snapshot.save()
    with pytest.raises(ValidationError, match="imutável"):
        EmployeeSnapshot.objects.update(employee_name="Nome alterado")
    with pytest.raises(ValidationError, match="não pode"):
        EmployeeSnapshot.objects.all().delete()

    event.description = "Alterado"
    with pytest.raises(ValidationError, match="imutáveis"):
        event.save()
    with pytest.raises(ValidationError, match="imutáveis"):
        ProcessAuditEvent.objects.update(description="Alterado")
    with pytest.raises(ValidationError, match="não podem"):
        ProcessAuditEvent.objects.all().delete()
    with pytest.raises(ValidationError, match="não podem"):
        OffboardingProcess.objects.all().delete()


def test_open_process_api_rejects_anonymous() -> None:
    response = post_json(Client(), api_payload())

    assert response.status_code == 401
    assert response.json()["code"] == "not_authenticated"
    assert not OffboardingProcess.objects.exists()


def test_open_process_api_uses_service_authorization() -> None:
    plain_user = User.objects.create_user(
        username="sem.dp",
        email="sem.dp@example.invalid",
        password=PASSWORD,
        first_name="Sem",
        last_name="DP",
    )
    client = Client()
    client.force_login(plain_user)
    response = post_json(client, api_payload())

    assert response.status_code == 403
    assert response.json()["code"] == "permission_denied"
    assert RepositoryStub.calls == 0
    assert not OffboardingProcess.objects.exists()


def test_open_process_api_creates_snapshot_without_exposing_cpf(
    actor_client: Client,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(ProcessListCreateView, "repository_class", RepositoryStub)

    response = post_json(actor_client, api_payload())

    assert response.status_code == 201
    payload = response.json()
    assert payload["status"] == ProcessStatus.DRAFT
    assert payload["employee_snapshot"]["employee_name"] == "Pessoa de Teste"
    assert "manager" not in payload
    assert "masked_cpf" not in payload["employee_snapshot"]
    assert "cpf" not in str(payload).lower()
    assert "active_employee_key" not in payload


def test_open_process_api_translates_senior_unavailability(
    actor_client: Client,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    RepositoryStub.error = SeniorUnavailableError("ORA-00000")
    monkeypatch.setattr(ProcessListCreateView, "repository_class", RepositoryStub)

    response = post_json(actor_client, api_payload())

    assert response.status_code == 503
    assert response.json() == {
        "code": "senior_unavailable",
        "message": "Senior HCM indisponível para abrir o processo.",
    }
    assert "ORA-00000" not in str(response.json())
    assert not OffboardingProcess.objects.exists()


def test_open_process_api_validates_incomplete_data(
    actor_client: Client,
) -> None:
    payload = api_payload()
    payload.pop("reason")

    response = post_json(actor_client, payload)

    assert response.status_code == 400
    assert response.json()["code"] == "validation_error"
    assert "reason" in response.json()["details"]
    assert RepositoryStub.calls == 0


def test_process_api_lists_newest_drafts_first(
    actor_client: Client,
    actor: User,
) -> None:
    first = service().execute(command(actor))
    RepositoryStub.employee = replace(employee_detail(), registration=124)
    second = service().execute(command(actor, employee_registration=124))
    url = reverse("offboarding-api:process-list")

    response = actor_client.get(url, {"status": ProcessStatus.DRAFT})

    assert response.status_code == 200
    assert [row["uuid"] for row in response.json()["results"]] == [
        str(second.uuid),
        str(first.uuid),
    ]
    assert response.json()["results"][0]["employee_snapshot"]["employee_name"] == "Pessoa de Teste"
    assert "cpf" not in str(response.json()).lower()


def test_process_list_respects_dp_scope_and_superadmin_authority(
    actor: User,
    dp_role: Role,
) -> None:
    process = service().execute(command(actor))
    scoped = User.objects.create_user(
        username="dp.outro.escopo",
        email="dp.outro.escopo@example.invalid",
        password=PASSWORD,
        first_name="DP",
        last_name="Outro escopo",
    )
    assignment = RoleAssignment.objects.create(
        user=scoped,
        role=dp_role,
        scope_type=ScopeType.BRANCH,
        company_code=9,
        branch_code=9,
        scope_key=build_scope_key(ScopeType.BRANCH, 9, 9),
        assigned_by=actor,
    )
    superadmin = User.objects.create_superuser(
        username="processos.superadmin",
        email="processos.superadmin@example.invalid",
        password=PASSWORD,
    )

    assert list(processes_for_actor(scoped)) == []
    assignment.company_code = 1
    assignment.branch_code = 2
    assignment.scope_key = build_scope_key(ScopeType.BRANCH, 1, 2)
    assignment.save(update_fields=("company_code", "branch_code", "scope_key"))
    assert list(processes_for_actor(scoped)) == [process]
    assert list(processes_for_actor(superadmin)) == [process]


def test_process_api_rejects_anonymous_user_without_dp_and_delete(
    actor_client: Client,
) -> None:
    url = reverse("offboarding-api:process-list")
    plain_user = User.objects.create_user(
        username="sem.lista.processos",
        email="sem.lista.processos@example.invalid",
        password=PASSWORD,
    )
    plain_client = Client()
    plain_client.force_login(plain_user)

    assert Client().get(url).status_code == 401
    assert plain_client.get(url).status_code == 403
    assert actor_client.delete(url).status_code == 405


def test_process_api_rejects_combined_status_and_completed_filters(
    actor_client: Client,
) -> None:
    response = actor_client.get(
        reverse("offboarding-api:process-list"),
        {"status": ProcessStatus.DRAFT, "completed": "true"},
    )

    assert response.status_code == 400
    assert response.json()["code"] == "validation_error"
