"""Server-rendered HTMX cascade for Senior reference selection."""

from __future__ import annotations

import logging
from collections.abc import Callable
from typing import TypeVar

from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.http import HttpRequest, HttpResponse
from django.shortcuts import render
from django.utils.decorators import method_decorator
from django.views import View

from apps.accounts.authorization import allowed_company_codes, has_permission
from apps.accounts.models import User

from .exceptions import (
    SeniorContractError,
    SeniorQueryValidationError,
    SeniorUnavailableError,
)
from .permissions import SENIOR_REFERENCE_PERMISSION
from .repository import SeniorRepository

logger = logging.getLogger(__name__)
T = TypeVar("T")


def _positive_parameter(request: HttpRequest, name: str) -> int | None:
    raw_value = request.GET.get(name)
    if raw_value is None or not raw_value.strip():
        return None
    try:
        value = int(raw_value)
    except ValueError:
        raise SeniorQueryValidationError(f"O parâmetro {name} deve ser um inteiro.") from None
    if value <= 0:
        raise SeniorQueryValidationError(f"O parâmetro {name} deve ser um inteiro positivo.")
    return value


@method_decorator(login_required, name="dispatch")
class SeniorReferenceView(View):
    """Common authorization and safe error translation for HTML views."""

    repository_class = SeniorRepository

    def _user(self, request: HttpRequest) -> User:
        if not isinstance(request.user, User):
            raise PermissionDenied
        return request.user

    def _is_authorized(
        self,
        request: HttpRequest,
        *,
        company: int | None = None,
        branch: int | None = None,
    ) -> bool:
        return has_permission(
            self._user(request),
            SENIOR_REFERENCE_PERMISSION,
            company_code=company,
            branch_code=branch,
        )

    @staticmethod
    def _error_details(error: Exception) -> tuple[str, int]:
        if isinstance(error, SeniorQueryValidationError):
            return str(error), 400
        if isinstance(error, SeniorUnavailableError):
            return "Senior HCM indisponível para consulta.", 503
        if isinstance(error, SeniorContractError):
            logger.exception("senior_ui_contract_error")
            return "Resposta inválida da fonte cadastral.", 502
        raise error

    def _query(
        self,
        operation: Callable[[], T],
    ) -> tuple[T | None, tuple[str, int] | None]:
        try:
            return operation(), None
        except (
            SeniorQueryValidationError,
            SeniorUnavailableError,
            SeniorContractError,
        ) as error:
            return None, self._error_details(error)

    @staticmethod
    def _partial_error(
        request: HttpRequest,
        *,
        target_id: str,
        message: str,
        status: int,
    ) -> HttpResponse:
        return render(
            request,
            "senior/partials/error.html",
            {"target_id": target_id, "integration_error": message},
            status=status,
        )


class SeniorReferenceSelectionView(SeniorReferenceView):
    """Render the entry point and the companies allowed by the user's scope."""

    def get(self, request: HttpRequest) -> HttpResponse:
        allowed_companies = allowed_company_codes(
            self._user(request),
            SENIOR_REFERENCE_PERMISSION,
        )
        if allowed_companies == set():
            raise PermissionDenied

        companies, error = self._query(
            lambda: self.repository_class().list_companies(offset=0, limit=100)
        )
        if error is not None:
            message, status = error
            return render(
                request,
                "senior/selection.html",
                {"companies": [], "integration_error": message},
                status=status,
            )
        assert companies is not None
        if allowed_companies is not None:
            companies = [company for company in companies if company.company in allowed_companies]
        return render(
            request,
            "senior/selection.html",
            {"companies": companies},
        )


class BranchOptionsView(SeniorReferenceView):
    """Return the branch field and reset every downstream field."""

    def get(self, request: HttpRequest) -> HttpResponse:
        try:
            company = _positive_parameter(request, "company")
        except SeniorQueryValidationError as error:
            message, status = self._error_details(error)
            return self._partial_error(
                request,
                target_id="cascade-fields",
                message=message,
                status=status,
            )
        if company is None:
            return render(request, "senior/partials/cascade_fields.html")
        if not self._is_authorized(request, company=company):
            return self._partial_error(
                request,
                target_id="cascade-fields",
                message="Usuário sem permissão para esta empresa.",
                status=403,
            )

        branches, query_error = self._query(
            lambda: self.repository_class().list_branches(
                company=company,
                offset=0,
                limit=100,
            )
        )
        if query_error is not None:
            message, status = query_error
            return self._partial_error(
                request,
                target_id="cascade-fields",
                message=message,
                status=status,
            )
        return render(
            request,
            "senior/partials/cascade_fields.html",
            {"branches": branches},
        )


class EmployeeTypeOptionsView(SeniorReferenceView):
    """Return employee types and clear the employee field."""

    def get(self, request: HttpRequest) -> HttpResponse:
        try:
            company = _positive_parameter(request, "company")
            branch = _positive_parameter(request, "branch")
        except SeniorQueryValidationError as error:
            message, status = self._error_details(error)
            return self._partial_error(
                request,
                target_id="employee-and-types",
                message=message,
                status=status,
            )
        if company is None or branch is None:
            return render(request, "senior/partials/employee_and_types.html")
        if not self._is_authorized(request, company=company, branch=branch):
            return self._partial_error(
                request,
                target_id="employee-and-types",
                message="Usuário sem permissão para esta filial.",
                status=403,
            )

        employee_types, query_error = self._query(
            lambda: self.repository_class().list_employee_types(
                company=company,
                branch=branch,
                offset=0,
                limit=100,
            )
        )
        if query_error is not None:
            message, status = query_error
            return self._partial_error(
                request,
                target_id="employee-and-types",
                message=message,
                status=status,
            )
        return render(
            request,
            "senior/partials/employee_and_types.html",
            {"employee_types": employee_types},
        )


class EmployeeOptionsView(SeniorReferenceView):
    """Return eligible employees, optionally narrowed by name or registration."""

    def get(self, request: HttpRequest) -> HttpResponse:
        try:
            company = _positive_parameter(request, "company")
            branch = _positive_parameter(request, "branch")
            employee_type = _positive_parameter(request, "employee_type")
        except SeniorQueryValidationError as error:
            message, status = self._error_details(error)
            return self._partial_error(
                request,
                target_id="employee-field",
                message=message,
                status=status,
            )
        if company is None or branch is None or employee_type is None:
            return render(request, "senior/partials/employee_field.html")
        if not self._is_authorized(request, company=company, branch=branch):
            return self._partial_error(
                request,
                target_id="employee-field",
                message="Usuário sem permissão para esta filial.",
                status=403,
            )

        search = request.GET.get("q")
        employees, query_error = self._query(
            lambda: self.repository_class().list_employees(
                company=company,
                branch=branch,
                employee_type=employee_type,
                search=search,
                offset=0,
                limit=20,
            )
        )
        if query_error is not None:
            message, status = query_error
            return self._partial_error(
                request,
                target_id="employee-field",
                message=message,
                status=status,
            )
        return render(
            request,
            "senior/partials/employee_field.html",
            {"employees": employees, "query": (search or "").strip()},
        )
