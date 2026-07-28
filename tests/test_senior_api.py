from datetime import datetime
from unittest.mock import Mock

import pytest
from django.contrib.auth.models import Permission
from django.urls import reverse
from rest_framework.test import APIClient

from apps.accounts.models import Role, RoleAssignment, ScopeType, User
from apps.integrations.senior.api import (
    BranchListAPIView,
    CompanyListAPIView,
    EmployeeListAPIView,
    EmployeeTypeListAPIView,
)
from apps.integrations.senior.dto import Branch, Company, Employee, EmployeeType
from apps.integrations.senior.exceptions import (
    SeniorContractError,
    SeniorQueryValidationError,
    SeniorUnavailableError,
)
from apps.integrations.senior.repository import SeniorRepository


@pytest.fixture
def authenticated_client(db: None) -> APIClient:
    client = APIClient()
    user = User.objects.create_user(
        username="usuario.teste",
        email="usuario.teste@example.invalid",
        password="test-only-password",
        is_superuser=True,
    )
    client.force_authenticate(user=user)
    return client


def install_repository(
    monkeypatch: pytest.MonkeyPatch,
    view: type[CompanyListAPIView]
    | type[BranchListAPIView]
    | type[EmployeeTypeListAPIView]
    | type[EmployeeListAPIView],
    repository: Mock,
) -> None:
    monkeypatch.setattr(
        view,
        "repository_class",
        staticmethod(lambda: repository),
    )


def test_reference_endpoints_require_authentication() -> None:
    response = APIClient().get(reverse("senior:companies"))

    assert response.status_code == 403


@pytest.mark.django_db
def test_reference_endpoints_reject_authenticated_user_without_role() -> None:
    user = User.objects.create_user(
        username="sem.escopo",
        email="sem.escopo@example.invalid",
        password="No-scope-test!2026",
    )
    client = APIClient()
    client.force_authenticate(user=user)

    response = client.get(reverse("senior:companies"))

    assert response.status_code == 403
    assert response.json() == {"detail": "Usuário sem permissão para este escopo cadastral."}


@pytest.mark.django_db
def test_company_endpoint_filters_results_by_role_scope(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    user = User.objects.create_user(
        username="dp.empresa.um",
        email="dp.empresa.um@example.invalid",
        password="Scoped-dp-test!2026",
    )
    permission = Permission.objects.get(codename="query_senior_references")
    role = Role.objects.create(code="DP_TESTE", name="DP de teste")
    role.permissions.add(permission)
    assignment = RoleAssignment(
        user=user,
        role=role,
        scope_type=ScopeType.COMPANY,
        company_code=1,
        scope_key="E:1",
        assigned_by=user,
    )
    assignment.full_clean()
    assignment.save()
    repository = Mock(spec=SeniorRepository)
    repository.list_companies.return_value = [Company(company=1), Company(company=2)]
    install_repository(monkeypatch, CompanyListAPIView, repository)
    client = APIClient()
    client.force_authenticate(user=user)

    response = client.get(reverse("senior:companies"))

    assert response.status_code == 200
    assert response.json()["results"] == [{"company": 1}]


@pytest.mark.django_db
def test_branch_endpoint_rejects_company_outside_role_scope(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    user = User.objects.create_user(
        username="dp.empresa.restrita",
        email="dp.empresa.restrita@example.invalid",
        password="Restricted-dp-test!2026",
    )
    permission = Permission.objects.get(codename="query_senior_references")
    role = Role.objects.create(code="DP_RESTRITO", name="DP restrito")
    role.permissions.add(permission)
    assignment = RoleAssignment(
        user=user,
        role=role,
        scope_type=ScopeType.COMPANY,
        company_code=1,
        scope_key="E:1",
        assigned_by=user,
    )
    assignment.full_clean()
    assignment.save()
    repository = Mock(spec=SeniorRepository)
    install_repository(monkeypatch, BranchListAPIView, repository)
    client = APIClient()
    client.force_authenticate(user=user)

    response = client.get(reverse("senior:branches"), {"company": 2})

    assert response.status_code == 403
    repository.list_branches.assert_not_called()


def test_company_endpoint_returns_paginated_contract(
    authenticated_client: APIClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repository = Mock(spec=SeniorRepository)
    repository.list_companies.return_value = [Company(company=1)]
    install_repository(monkeypatch, CompanyListAPIView, repository)

    response = authenticated_client.get(
        reverse("senior:companies"),
        {"offset": 5, "limit": 10},
        HTTP_X_CORRELATION_ID="api-test",
    )

    assert response.status_code == 200
    assert response.json() == {
        "offset": 5,
        "limit": 10,
        "results": [{"company": 1}],
    }
    assert response["X-Correlation-ID"] == "api-test"
    repository.list_companies.assert_called_once_with(offset=5, limit=10)


def test_branch_endpoint_requires_company_before_repository(
    authenticated_client: APIClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repository = Mock(spec=SeniorRepository)
    install_repository(monkeypatch, BranchListAPIView, repository)

    response = authenticated_client.get(reverse("senior:branches"))

    assert response.status_code == 400
    assert response.json() == {"detail": "O parâmetro company é obrigatório."}
    repository.list_branches.assert_not_called()


def test_branch_endpoint_passes_cascade_filter(
    authenticated_client: APIClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repository = Mock(spec=SeniorRepository)
    repository.list_branches.return_value = [
        Branch(company=1, branch=2, legal_name="Empresa de Teste")
    ]
    install_repository(monkeypatch, BranchListAPIView, repository)

    response = authenticated_client.get(
        reverse("senior:branches"),
        {"company": 1},
    )

    assert response.status_code == 200
    assert response.json()["results"] == [
        {"company": 1, "branch": 2, "legal_name": "Empresa de Teste"}
    ]
    repository.list_branches.assert_called_once_with(
        company=1,
        offset=0,
        limit=50,
    )


def test_employee_type_endpoint_rejects_non_integer_parameter(
    authenticated_client: APIClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repository = Mock(spec=SeniorRepository)
    install_repository(monkeypatch, EmployeeTypeListAPIView, repository)

    response = authenticated_client.get(
        reverse("senior:employee-types"),
        {"company": "invalid", "branch": "2"},
    )

    assert response.status_code == 400
    assert response.json() == {"detail": "O parâmetro company deve ser um inteiro."}
    repository.list_employee_types.assert_not_called()


def test_employee_type_endpoint_returns_results(
    authenticated_client: APIClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repository = Mock(spec=SeniorRepository)
    repository.list_employee_types.return_value = [
        EmployeeType(employee_type=1, description="Empregado")
    ]
    install_repository(monkeypatch, EmployeeTypeListAPIView, repository)

    response = authenticated_client.get(
        reverse("senior:employee-types"),
        {"company": 1, "branch": 2},
    )

    assert response.status_code == 200
    assert response.json()["results"] == [{"employee_type": 1, "description": "Empregado"}]


def test_employee_endpoint_omits_cpf_and_uses_all_filters(
    authenticated_client: APIClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repository = Mock(spec=SeniorRepository)
    repository.list_employees.return_value = [
        Employee(
            company=1,
            branch=2,
            legal_name="Empresa de Teste",
            employee_type=1,
            employee_type_description="Empregado",
            registration=123,
            name="Pessoa de Teste",
            admission_date=datetime(2020, 1, 2),
            leave_code=1,
            leave_description="Trabalhando",
            leave_date=None,
            job_structure=1,
            job_code="DEV",
            job_description="Desenvolvedor",
            cost_center="100",
            cost_center_description=None,
            source_updated_at=datetime(2026, 7, 27, 12, 0),
        )
    ]
    install_repository(monkeypatch, EmployeeListAPIView, repository)

    response = authenticated_client.get(
        reverse("senior:employees"),
        {
            "company": "1",
            "branch": "2",
            "employee_type": "1",
            "q": "Pessoa",
        },
    )

    assert response.status_code == 200
    payload = response.json()["results"][0]
    assert payload["registration"] == 123
    assert payload["source_updated_at"] == "2026-07-27T12:00:00"
    assert "cpf" not in payload
    assert "masked_cpf" not in payload
    repository.list_employees.assert_called_once_with(
        company=1,
        branch=2,
        employee_type=1,
        search="Pessoa",
        offset=0,
        limit=20,
    )


@pytest.mark.parametrize(
    ("error", "status", "detail"),
    [
        (
            SeniorQueryValidationError("limit inválido"),
            400,
            "limit inválido",
        ),
        (
            SeniorUnavailableError("database detail"),
            503,
            "Senior HCM indisponível para consulta.",
        ),
        (
            SeniorContractError("column detail"),
            502,
            "Resposta inválida da fonte cadastral.",
        ),
    ],
)
def test_endpoint_translates_repository_errors(
    authenticated_client: APIClient,
    monkeypatch: pytest.MonkeyPatch,
    error: Exception,
    status: int,
    detail: str,
) -> None:
    repository = Mock(spec=SeniorRepository)
    repository.list_companies.side_effect = error
    install_repository(monkeypatch, CompanyListAPIView, repository)

    response = authenticated_client.get(reverse("senior:companies"))

    assert response.status_code == status
    assert response.json() == {"detail": detail}
