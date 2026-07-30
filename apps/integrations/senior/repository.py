"""Parametrized, read-only access to the Senior HCM contract."""

import logging
from collections.abc import Callable, Iterator, Mapping, Sequence
from contextlib import contextmanager
from dataclasses import asdict
from datetime import datetime
from decimal import Decimal
from time import monotonic
from typing import Any, TypeVar

from django.conf import settings
from django.db import DatabaseError, connections
from django.db.backends.base.base import BaseDatabaseWrapper
from django.db.backends.utils import CursorWrapper

from . import queries
from .dto import Branch, Company, Employee, EmployeeDetail, EmployeeType
from .exceptions import (
    SeniorContractError,
    SeniorQueryValidationError,
    SeniorUnavailableError,
)

logger = logging.getLogger(__name__)
T = TypeVar("T")
ABSOLUTE_MAX_PAGE_SIZE = 100


class SeniorRepository:
    """Query the homologated VETORH objects without Django models."""

    def __init__(
        self,
        *,
        connection: BaseDatabaseWrapper | None = None,
        timeout_ms: int | None = None,
        max_page_size: int | None = None,
    ) -> None:
        self._connection = connection or connections["default"]
        selected_timeout = settings.SENIOR_QUERY_TIMEOUT_MS if timeout_ms is None else timeout_ms
        selected_page_size = (
            settings.SENIOR_QUERY_MAX_PAGE_SIZE if max_page_size is None else max_page_size
        )
        self._timeout_ms = self._positive_integer(selected_timeout, "timeout_ms")
        self._max_page_size = self._positive_integer(
            selected_page_size,
            "max_page_size",
        )
        if self._max_page_size > ABSOLUTE_MAX_PAGE_SIZE:
            raise SeniorQueryValidationError(
                f"max_page_size deve ser menor ou igual a {ABSOLUTE_MAX_PAGE_SIZE}."
            )

    def list_companies(self, *, offset: int = 0, limit: int = 50) -> list[Company]:
        pagination = self._pagination(offset=offset, limit=limit)
        return self._query_many(
            name="list_companies",
            sql=queries.LIST_COMPANIES,
            params=pagination,
            factory=lambda row: Company(
                company=self._integer(row, "EMPRESA"),
                legal_name=self._text(row, "RAZAO_SOCIAL"),
            ),
        )

    def list_branches(
        self,
        *,
        company: int,
        offset: int = 0,
        limit: int = 50,
    ) -> list[Branch]:
        params = {
            "empresa": self._positive_integer(company, "company"),
            **self._pagination(offset=offset, limit=limit),
        }
        return self._query_many(
            name="list_branches",
            sql=queries.LIST_BRANCHES,
            params=params,
            factory=lambda row: Branch(
                company=self._integer(row, "EMPRESA"),
                branch=self._integer(row, "FILIAL"),
                legal_name=self._text(row, "NOME_FILIAL"),
            ),
        )

    def list_employee_types(
        self,
        *,
        company: int,
        branch: int,
        offset: int = 0,
        limit: int = 50,
    ) -> list[EmployeeType]:
        params = {
            "empresa": self._positive_integer(company, "company"),
            "filial": self._positive_integer(branch, "branch"),
            **self._pagination(offset=offset, limit=limit),
        }
        return self._query_many(
            name="list_employee_types",
            sql=queries.LIST_EMPLOYEE_TYPES,
            params=params,
            factory=lambda row: EmployeeType(
                employee_type=self._integer(row, "TIPO_COLABORADOR"),
                description=self._text(row, "DESCRICAO_TIPO_COLABORADOR"),
            ),
        )

    def list_employees(
        self,
        *,
        company: int,
        branch: int,
        employee_type: int,
        search: str | None = None,
        offset: int = 0,
        limit: int = 20,
    ) -> list[Employee]:
        params: dict[str, Any] = {
            "empresa": self._positive_integer(company, "company"),
            "filial": self._positive_integer(branch, "branch"),
            "tipo_colaborador": self._positive_integer(
                employee_type,
                "employee_type",
            ),
            "busca": self._search(search),
            **self._pagination(offset=offset, limit=limit),
        }
        return self._query_many(
            name="list_employees",
            sql=queries.LIST_EMPLOYEES,
            params=params,
            factory=self._employee,
        )

    def get_employee(
        self,
        *,
        company: int,
        branch: int,
        employee_type: int,
        registration: int,
    ) -> EmployeeDetail | None:
        params = {
            "empresa": self._positive_integer(company, "company"),
            "filial": self._positive_integer(branch, "branch"),
            "tipo_colaborador": self._positive_integer(
                employee_type,
                "employee_type",
            ),
            "matricula": self._positive_integer(registration, "registration"),
        }
        rows = self._execute(
            name="get_employee",
            sql=queries.GET_EMPLOYEE,
            params=params,
            fetch_limit=2,
        )
        if len(rows) > 1:
            logger.error(
                "senior_query_contract_error",
                extra={"query_name": "get_employee", "row_count": len(rows)},
            )
            raise SeniorContractError("O Senior retornou mais de um colaborador para a chave.")
        return self._employee_detail(rows[0]) if rows else None

    def _query_many(
        self,
        *,
        name: str,
        sql: str,
        params: Mapping[str, Any],
        factory: Callable[[Mapping[str, object]], T],
    ) -> list[T]:
        return [factory(row) for row in self._execute(name=name, sql=sql, params=params)]

    def _execute(
        self,
        *,
        name: str,
        sql: str,
        params: Mapping[str, Any],
        fetch_limit: int | None = None,
    ) -> list[dict[str, object]]:
        started_at = monotonic()
        try:
            with self._connection.cursor() as cursor, self._query_timeout():
                cursor.execute(sql, params)
                raw_rows = cursor.fetchmany(fetch_limit) if fetch_limit else cursor.fetchall()
                rows = self._rows_as_mappings(cursor, raw_rows)
        except DatabaseError:
            logger.exception(
                "senior_query_failed",
                extra={
                    "query_name": name,
                    "elapsed_ms": round((monotonic() - started_at) * 1000, 2),
                },
            )
            raise SeniorUnavailableError("Não foi possível consultar o Senior HCM.") from None

        logger.info(
            "senior_query_completed",
            extra={
                "query_name": name,
                "elapsed_ms": round((monotonic() - started_at) * 1000, 2),
                "row_count": len(rows),
            },
        )
        return rows

    @contextmanager
    def _query_timeout(self) -> Iterator[None]:
        raw_connection = self._connection.connection
        if raw_connection is None or not hasattr(raw_connection, "call_timeout"):
            yield
            return

        previous_timeout = raw_connection.call_timeout
        raw_connection.call_timeout = self._timeout_ms
        try:
            yield
        finally:
            raw_connection.call_timeout = previous_timeout

    @staticmethod
    def _rows_as_mappings(
        cursor: CursorWrapper,
        rows: Sequence[Sequence[object]],
    ) -> list[dict[str, object]]:
        if cursor.description is None:
            raise SeniorContractError("A consulta Senior não retornou metadados.")
        columns = [column[0].upper() for column in cursor.description]
        return [dict(zip(columns, row, strict=True)) for row in rows]

    def _pagination(self, *, offset: int, limit: int) -> dict[str, int]:
        valid_offset = self._non_negative_integer(offset, "offset")
        valid_limit = self._positive_integer(limit, "limit")
        if valid_limit > self._max_page_size:
            raise SeniorQueryValidationError(
                f"limit deve ser menor ou igual a {self._max_page_size}."
            )
        return {"offset": valid_offset, "limite": valid_limit}

    @staticmethod
    def _search(search: str | None) -> str | None:
        if search is None:
            return None
        if not isinstance(search, str):
            raise SeniorQueryValidationError("search deve ser texto.")
        normalized = search.strip()
        if not normalized:
            return None
        if len(normalized) > 100:
            raise SeniorQueryValidationError("search deve ter no máximo 100 caracteres.")
        return normalized

    @staticmethod
    def _positive_integer(value: int, name: str) -> int:
        if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
            raise SeniorQueryValidationError(f"{name} deve ser um inteiro positivo.")
        return value

    @staticmethod
    def _non_negative_integer(value: int, name: str) -> int:
        if isinstance(value, bool) or not isinstance(value, int) or value < 0:
            raise SeniorQueryValidationError(f"{name} deve ser um inteiro não negativo.")
        return value

    @staticmethod
    def _value(row: Mapping[str, object], column: str) -> object:
        try:
            return row[column]
        except KeyError:
            raise SeniorContractError(
                f"A coluna esperada {column} não foi retornada pelo Senior."
            ) from None

    @classmethod
    def _integer(cls, row: Mapping[str, object], column: str) -> int:
        value = cls._value(row, column)
        if isinstance(value, int) and not isinstance(value, bool):
            return value
        if isinstance(value, Decimal) and value == value.to_integral_value():
            return int(value)
        raise SeniorContractError(f"A coluna {column} não contém um número válido.")

    @classmethod
    def _text(cls, row: Mapping[str, object], column: str) -> str:
        value = cls._value(row, column)
        if not isinstance(value, str):
            raise SeniorContractError(f"A coluna {column} não contém texto válido.")
        return value

    @classmethod
    def _optional_text(cls, row: Mapping[str, object], column: str) -> str | None:
        value = cls._value(row, column)
        if value is None:
            return None
        if not isinstance(value, str):
            raise SeniorContractError(f"A coluna {column} não contém texto válido.")
        return value

    @classmethod
    def _datetime(
        cls,
        row: Mapping[str, object],
        column: str,
        *,
        optional: bool = False,
    ) -> datetime | None:
        value = cls._value(row, column)
        if optional and value is None:
            return None
        if not isinstance(value, datetime):
            raise SeniorContractError(f"A coluna {column} não contém data válida.")
        return value

    @classmethod
    def _employee(cls, row: Mapping[str, object]) -> Employee:
        admission_date = cls._datetime(row, "DATA_ADMISSAO")
        if admission_date is None:
            raise SeniorContractError("A data de admissão não pode ser nula.")
        return Employee(
            company=cls._integer(row, "EMPRESA"),
            branch=cls._integer(row, "FILIAL"),
            legal_name=cls._text(row, "NOME_FILIAL"),
            employee_type=cls._integer(row, "TIPO_COLABORADOR"),
            employee_type_description=cls._text(
                row,
                "DESCRICAO_TIPO_COLABORADOR",
            ),
            registration=cls._integer(row, "MATRICULA"),
            name=cls._text(row, "FUNCIONARIO"),
            admission_date=admission_date,
            leave_code=cls._integer(row, "CODIGO_AFASTAMENTO"),
            leave_description=cls._text(row, "DESCRICAO_AFASTAMENTO"),
            leave_date=cls._datetime(row, "DATA_AFASTAMENTO", optional=True),
            job_structure=cls._integer(row, "ESTRUTURA_CARGOS"),
            job_code=cls._text(row, "CODIGO_CARGO"),
            job_description=cls._text(row, "DESCRICAO_CARGO"),
            cost_center=cls._text(row, "CENTRO_CUSTO"),
            cost_center_description=cls._optional_text(
                row,
                "DESCRICAO_CENTRO_CUSTO",
            ),
            source_updated_at=cls._datetime(
                row,
                "ORIGEM_ATUALIZADA_EM",
                optional=True,
            ),
        )

    @classmethod
    def _employee_detail(cls, row: Mapping[str, object]) -> EmployeeDetail:
        employee = cls._employee(row)
        return EmployeeDetail(
            **asdict(employee),
            masked_cpf=cls._optional_text(row, "CPF_MASCARADO"),
        )
