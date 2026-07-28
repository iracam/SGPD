"""Authenticated HTTP endpoints for the Senior reference cascade."""

import logging
from collections.abc import Callable
from datetime import datetime
from typing import TypeVar

from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.status import (
    HTTP_200_OK,
    HTTP_400_BAD_REQUEST,
    HTTP_403_FORBIDDEN,
    HTTP_502_BAD_GATEWAY,
    HTTP_503_SERVICE_UNAVAILABLE,
)
from rest_framework.views import APIView

from apps.accounts.authorization import allowed_company_codes, has_permission
from apps.accounts.models import User

from .dto import Branch, Company, Employee, EmployeeType
from .exceptions import (
    SeniorContractError,
    SeniorQueryValidationError,
    SeniorUnavailableError,
)
from .permissions import SENIOR_REFERENCE_PERMISSION
from .repository import SeniorRepository

logger = logging.getLogger(__name__)
T = TypeVar("T")


def _integer_parameter(
    request: Request,
    name: str,
    *,
    default: int | None = None,
) -> int:
    raw_value = request.query_params.get(name)
    if raw_value is None:
        if default is not None:
            return default
        raise SeniorQueryValidationError(f"O parâmetro {name} é obrigatório.")
    try:
        return int(raw_value)
    except ValueError:
        raise SeniorQueryValidationError(f"O parâmetro {name} deve ser um inteiro.") from None


def _iso_datetime(value: datetime | None) -> str | None:
    return value.isoformat() if value is not None else None


def _company_payload(company: Company) -> dict[str, object]:
    return {"company": company.company}


def _branch_payload(branch: Branch) -> dict[str, object]:
    return {
        "company": branch.company,
        "branch": branch.branch,
        "legal_name": branch.legal_name,
    }


def _employee_type_payload(employee_type: EmployeeType) -> dict[str, object]:
    return {
        "employee_type": employee_type.employee_type,
        "description": employee_type.description,
    }


def _employee_payload(employee: Employee) -> dict[str, object]:
    return {
        "company": employee.company,
        "branch": employee.branch,
        "legal_name": employee.legal_name,
        "employee_type": employee.employee_type,
        "employee_type_description": employee.employee_type_description,
        "registration": employee.registration,
        "name": employee.name,
        "admission_date": _iso_datetime(employee.admission_date),
        "leave_code": employee.leave_code,
        "leave_description": employee.leave_description,
        "leave_date": _iso_datetime(employee.leave_date),
        "job_structure": employee.job_structure,
        "job_code": employee.job_code,
        "job_description": employee.job_description,
        "cost_center": employee.cost_center,
        "cost_center_description": employee.cost_center_description,
        "source_updated_at": _iso_datetime(employee.source_updated_at),
    }


class SeniorAPIView(APIView):
    """Translate repository outcomes without leaking Oracle details."""

    permission_classes = [IsAuthenticated]
    repository_class = SeniorRepository

    def _is_authorized(
        self,
        request: Request,
        *,
        company: int | None = None,
        branch: int | None = None,
    ) -> bool:
        if not isinstance(request.user, User):
            return False
        return has_permission(
            request.user,
            SENIOR_REFERENCE_PERMISSION,
            company_code=company,
            branch_code=branch,
        )

    def _forbidden(self) -> Response:
        return Response(
            {"detail": "Usuário sem permissão para este escopo cadastral."},
            status=HTTP_403_FORBIDDEN,
        )

    def _respond(
        self,
        *,
        operation: Callable[[], list[T]],
        payload: Callable[[T], dict[str, object]],
        offset: int,
        limit: int,
        result_filter: Callable[[T], bool] | None = None,
    ) -> Response:
        try:
            results = operation()
        except SeniorQueryValidationError as exc:
            return Response({"detail": str(exc)}, status=HTTP_400_BAD_REQUEST)
        except SeniorUnavailableError:
            return Response(
                {"detail": "Senior HCM indisponível para consulta."},
                status=HTTP_503_SERVICE_UNAVAILABLE,
            )
        except SeniorContractError:
            logger.exception("senior_api_contract_error")
            return Response(
                {"detail": "Resposta inválida da fonte cadastral."},
                status=HTTP_502_BAD_GATEWAY,
            )

        if result_filter is not None:
            results = [item for item in results if result_filter(item)]

        return Response(
            {
                "offset": offset,
                "limit": limit,
                "results": [payload(item) for item in results],
            },
            status=HTTP_200_OK,
        )


class CompanyListAPIView(SeniorAPIView):
    def get(self, request: Request) -> Response:
        try:
            offset = _integer_parameter(request, "offset", default=0)
            limit = _integer_parameter(request, "limit", default=50)
        except SeniorQueryValidationError as exc:
            return Response({"detail": str(exc)}, status=HTTP_400_BAD_REQUEST)

        user = request.user
        if not isinstance(user, User):
            return self._forbidden()
        allowed_companies = allowed_company_codes(user, SENIOR_REFERENCE_PERMISSION)
        if allowed_companies == set():
            return self._forbidden()

        repository = self.repository_class()
        return self._respond(
            operation=lambda: repository.list_companies(offset=offset, limit=limit),
            payload=_company_payload,
            offset=offset,
            limit=limit,
            result_filter=(
                None
                if allowed_companies is None
                else lambda company: company.company in allowed_companies
            ),
        )


class BranchListAPIView(SeniorAPIView):
    def get(self, request: Request) -> Response:
        try:
            company = _integer_parameter(request, "company")
            offset = _integer_parameter(request, "offset", default=0)
            limit = _integer_parameter(request, "limit", default=50)
        except SeniorQueryValidationError as exc:
            return Response({"detail": str(exc)}, status=HTTP_400_BAD_REQUEST)

        if not self._is_authorized(request, company=company):
            return self._forbidden()
        repository = self.repository_class()
        return self._respond(
            operation=lambda: repository.list_branches(
                company=company,
                offset=offset,
                limit=limit,
            ),
            payload=_branch_payload,
            offset=offset,
            limit=limit,
        )


class EmployeeTypeListAPIView(SeniorAPIView):
    def get(self, request: Request) -> Response:
        try:
            company = _integer_parameter(request, "company")
            branch = _integer_parameter(request, "branch")
            offset = _integer_parameter(request, "offset", default=0)
            limit = _integer_parameter(request, "limit", default=50)
        except SeniorQueryValidationError as exc:
            return Response({"detail": str(exc)}, status=HTTP_400_BAD_REQUEST)

        if not self._is_authorized(request, company=company, branch=branch):
            return self._forbidden()
        repository = self.repository_class()
        return self._respond(
            operation=lambda: repository.list_employee_types(
                company=company,
                branch=branch,
                offset=offset,
                limit=limit,
            ),
            payload=_employee_type_payload,
            offset=offset,
            limit=limit,
        )


class EmployeeListAPIView(SeniorAPIView):
    def get(self, request: Request) -> Response:
        try:
            company = _integer_parameter(request, "company")
            branch = _integer_parameter(request, "branch")
            employee_type = _integer_parameter(request, "employee_type")
            offset = _integer_parameter(request, "offset", default=0)
            limit = _integer_parameter(request, "limit", default=20)
        except SeniorQueryValidationError as exc:
            return Response({"detail": str(exc)}, status=HTTP_400_BAD_REQUEST)

        if not self._is_authorized(request, company=company, branch=branch):
            return self._forbidden()
        search = request.query_params.get("q")
        repository = self.repository_class()
        return self._respond(
            operation=lambda: repository.list_employees(
                company=company,
                branch=branch,
                employee_type=employee_type,
                search=search,
                offset=offset,
                limit=limit,
            ),
            payload=_employee_payload,
            offset=offset,
            limit=limit,
        )
