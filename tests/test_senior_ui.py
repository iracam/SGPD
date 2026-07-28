from datetime import datetime
from unittest.mock import Mock

import pytest
from django.contrib.auth.models import Permission
from django.test import Client
from django.urls import reverse

from apps.accounts.models import Role, RoleAssignment, ScopeType, User
from apps.integrations.senior.dto import Branch, Company, Employee, EmployeeType
from apps.integrations.senior.exceptions import SeniorUnavailableError
from apps.integrations.senior.repository import SeniorRepository
from apps.integrations.senior.views import (
    BranchOptionsView,
    EmployeeOptionsView,
    EmployeeTypeOptionsView,
    SeniorReferenceSelectionView,
)

pytestmark = pytest.mark.django_db


@pytest.fixture
def superuser() -> User:
    return User.objects.create_superuser(
        username="senior.ui.admin",
        email="senior.ui.admin@example.invalid",
        password="Senior-ui-admin-test!2026",
    )


def install_repository(
    monkeypatch: pytest.MonkeyPatch,
    view: type[SeniorReferenceSelectionView]
    | type[BranchOptionsView]
    | type[EmployeeTypeOptionsView]
    | type[EmployeeOptionsView],
    repository: Mock,
) -> None:
    monkeypatch.setattr(
        view,
        "repository_class",
        staticmethod(lambda: repository),
    )


def scoped_user(*, company: int, branch: int | None = None) -> User:
    user = User.objects.create_user(
        username=f"senior.escopo.{company}.{branch or 0}",
        email=f"senior.escopo.{company}.{branch or 0}@example.invalid",
        password="Senior-scoped-test!2026",
    )
    permission = Permission.objects.get(codename="query_senior_references")
    role = Role.objects.create(
        code=f"DP_UI_{company}_{branch or 0}",
        name="DP UI de teste",
    )
    role.permissions.add(permission)
    assignment = RoleAssignment(
        user=user,
        role=role,
        scope_type=ScopeType.BRANCH if branch is not None else ScopeType.COMPANY,
        company_code=company,
        branch_code=branch,
        scope_key=f"E:{company}:F:{branch}" if branch is not None else f"E:{company}",
        assigned_by=user,
    )
    assignment.full_clean()
    assignment.save()
    return user


def employee() -> Employee:
    return Employee(
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


def test_selection_requires_login() -> None:
    response = Client().get(reverse("senior-ui:selection"))

    assert response.status_code == 302
    assert reverse("accounts:login") in response["Location"]


def test_selection_rejects_user_without_reference_scope() -> None:
    user = User.objects.create_user(
        username="senior.ui.sem.escopo",
        email="senior.ui.sem.escopo@example.invalid",
        password="Senior-no-scope-test!2026",
    )
    client = Client()
    client.force_login(user)

    response = client.get(reverse("senior-ui:selection"))

    assert response.status_code == 403


def test_selection_filters_companies_and_uses_only_local_htmx(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    user = scoped_user(company=1)
    repository = Mock(spec=SeniorRepository)
    repository.list_companies.return_value = [
        Company(company=1),
        Company(company=2),
    ]
    install_repository(monkeypatch, SeniorReferenceSelectionView, repository)
    client = Client()
    client.force_login(user)

    response = client.get(reverse("senior-ui:selection"))
    content = response.content.decode()

    assert response.status_code == 200
    assert "Empresa 1" in content
    assert "Empresa 2" not in content
    assert "/static/vendor/htmx/htmx-2.0.10.min.js" in content
    assert "https://" not in content
    repository.list_companies.assert_called_once_with(offset=0, limit=100)


def test_blank_company_resets_cascade_without_querying_senior(
    superuser: User,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repository = Mock(spec=SeniorRepository)
    install_repository(monkeypatch, BranchOptionsView, repository)
    client = Client()
    client.force_login(superuser)

    response = client.get(reverse("senior-ui:branches"), {"company": ""})

    assert response.status_code == 200
    assert "Selecione primeiro a empresa" in response.content.decode()
    repository.list_branches.assert_not_called()


def test_branch_options_reject_company_outside_scope_before_query(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    user = scoped_user(company=1)
    repository = Mock(spec=SeniorRepository)
    install_repository(monkeypatch, BranchOptionsView, repository)
    client = Client()
    client.force_login(user)

    response = client.get(reverse("senior-ui:branches"), {"company": 2})

    assert response.status_code == 403
    assert "sem permissão para esta empresa" in response.content.decode()
    repository.list_branches.assert_not_called()


def test_branch_options_render_authorized_results_and_reset_downstream(
    superuser: User,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repository = Mock(spec=SeniorRepository)
    repository.list_branches.return_value = [
        Branch(company=1, branch=2, legal_name="Empresa de Teste")
    ]
    install_repository(monkeypatch, BranchOptionsView, repository)
    client = Client()
    client.force_login(superuser)

    response = client.get(reverse("senior-ui:branches"), {"company": 1})
    content = response.content.decode()

    assert response.status_code == 200
    assert "2 — Empresa de Teste" in content
    assert "Selecione primeiro a filial" in content
    assert "Selecione primeiro o tipo de colaborador" in content
    repository.list_branches.assert_called_once_with(
        company=1,
        offset=0,
        limit=100,
    )


def test_employee_types_require_authorized_branch_scope(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    user = scoped_user(company=1, branch=2)
    repository = Mock(spec=SeniorRepository)
    install_repository(monkeypatch, EmployeeTypeOptionsView, repository)
    client = Client()
    client.force_login(user)

    forbidden = client.get(
        reverse("senior-ui:employee-types"),
        {"company": 1, "branch": 3},
    )

    assert forbidden.status_code == 403
    repository.list_employee_types.assert_not_called()

    repository.list_employee_types.return_value = [
        EmployeeType(employee_type=1, description="Empregado")
    ]
    allowed = client.get(
        reverse("senior-ui:employee-types"),
        {"company": 1, "branch": 2},
    )

    assert allowed.status_code == 200
    assert "1 — Empregado" in allowed.content.decode()


def test_employee_search_uses_full_cascade_and_does_not_expose_cpf(
    superuser: User,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repository = Mock(spec=SeniorRepository)
    repository.list_employees.return_value = [employee()]
    install_repository(monkeypatch, EmployeeOptionsView, repository)
    client = Client()
    client.force_login(superuser)

    response = client.get(
        reverse("senior-ui:employees"),
        {
            "company": "1",
            "branch": "2",
            "employee_type": "1",
            "q": "Pessoa",
        },
    )
    content = response.content.decode()

    assert response.status_code == 200
    assert "123 — Pessoa de Teste — Desenvolvedor" in content
    assert "cpf" not in content.lower()
    repository.list_employees.assert_called_once_with(
        company=1,
        branch=2,
        employee_type=1,
        search="Pessoa",
        offset=0,
        limit=20,
    )


def test_invalid_parameter_and_unavailability_are_safe_htmx_errors(
    superuser: User,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repository = Mock(spec=SeniorRepository)
    install_repository(monkeypatch, BranchOptionsView, repository)
    client = Client()
    client.force_login(superuser)

    invalid = client.get(reverse("senior-ui:branches"), {"company": "inválida"})

    assert invalid.status_code == 400
    assert "deve ser um inteiro" in invalid.content.decode()
    repository.list_branches.assert_not_called()

    repository.list_branches.side_effect = SeniorUnavailableError("detalhe do banco")
    unavailable = client.get(reverse("senior-ui:branches"), {"company": 1})

    assert unavailable.status_code == 503
    assert "Senior HCM indisponível para consulta." in unavailable.content.decode()
    assert "detalhe do banco" not in unavailable.content.decode()
