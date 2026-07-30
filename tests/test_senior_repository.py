from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from datetime import datetime
from pathlib import Path
from typing import Any, cast

import pytest
from django.db import DatabaseError
from django.db.backends.base.base import BaseDatabaseWrapper

from apps.integrations.senior import queries
from apps.integrations.senior.dto import EmployeeDetail
from apps.integrations.senior.exceptions import (
    SeniorContractError,
    SeniorQueryValidationError,
    SeniorUnavailableError,
)
from apps.integrations.senior.repository import SeniorRepository


class FakeRawConnection:
    call_timeout = 25


class FakeCursor:
    def __init__(
        self,
        *,
        columns: Sequence[str],
        rows: Sequence[Sequence[object]],
        execute_error: DatabaseError | None = None,
    ) -> None:
        self.description = [(column,) for column in columns]
        self.rows = list(rows)
        self.execute_error = execute_error
        self.executions: list[tuple[str, Mapping[str, Any]]] = []
        self.fetchmany_size: int | None = None
        self.timeout_during_execute: int | None = None
        self.raw_connection: FakeRawConnection | None = None

    def __enter__(self) -> FakeCursor:
        return self

    def __exit__(self, *_args: object) -> None:
        return None

    def execute(self, sql: str, params: Mapping[str, Any]) -> None:
        self.executions.append((sql, params))
        if self.raw_connection is not None:
            self.timeout_during_execute = self.raw_connection.call_timeout
        if self.execute_error is not None:
            raise self.execute_error

    def fetchall(self) -> list[Sequence[object]]:
        return self.rows

    def fetchmany(self, size: int) -> list[Sequence[object]]:
        self.fetchmany_size = size
        return self.rows[:size]


class FakeConnection:
    def __init__(self, cursor: FakeCursor) -> None:
        self.connection = FakeRawConnection()
        self._cursor = cursor
        cursor.raw_connection = self.connection

    def cursor(self) -> FakeCursor:
        return self._cursor


def repository(cursor: FakeCursor) -> SeniorRepository:
    connection = cast(BaseDatabaseWrapper, FakeConnection(cursor))
    return SeniorRepository(connection=connection, timeout_ms=5_000, max_page_size=100)


def employee_columns(*, detail: bool = False) -> list[str]:
    columns = [
        "EMPRESA",
        "FILIAL",
        "NOME_FILIAL",
        "TIPO_COLABORADOR",
        "DESCRICAO_TIPO_COLABORADOR",
        "MATRICULA",
        "FUNCIONARIO",
    ]
    if detail:
        columns.append("CPF_MASCARADO")
    return columns + [
        "DATA_ADMISSAO",
        "CODIGO_AFASTAMENTO",
        "DESCRICAO_AFASTAMENTO",
        "DATA_AFASTAMENTO",
        "ESTRUTURA_CARGOS",
        "CODIGO_CARGO",
        "DESCRICAO_CARGO",
        "CENTRO_CUSTO",
        "DESCRICAO_CENTRO_CUSTO",
        "ORIGEM_ATUALIZADA_EM",
    ]


def employee_row(*, detail: bool = False) -> list[object]:
    row: list[object] = [
        1,
        2,
        "Empresa de Teste",
        1,
        "Empregado",
        123,
        "Pessoa de Teste",
    ]
    if detail:
        row.append("***.***.***-00")
    return row + [
        datetime(2020, 1, 2),
        1,
        "Trabalhando",
        None,
        1,
        "DEV",
        "Desenvolvedor",
        "100",
        None,
        datetime(2026, 7, 27, 12, 0),
    ]


def test_list_branches_uses_bind_variables_and_restores_timeout() -> None:
    cursor = FakeCursor(
        columns=["EMPRESA", "FILIAL", "NOME_FILIAL"],
        rows=[(1, 2, "Empresa de Teste")],
    )
    result = repository(cursor).list_branches(company=1, offset=10, limit=20)

    assert result[0].legal_name == "Empresa de Teste"
    assert cursor.executions[0][1] == {
        "empresa": 1,
        "offset": 10,
        "limite": 20,
    }
    assert cursor.timeout_during_execute == 5_000
    assert cursor.raw_connection is not None
    assert cursor.raw_connection.call_timeout == 25


def test_employee_list_does_not_return_cpf() -> None:
    cursor = FakeCursor(
        columns=employee_columns(),
        rows=[employee_row()],
    )
    result = repository(cursor).list_employees(
        company=1,
        branch=2,
        employee_type=1,
        search="  Pessoa  ",
    )

    assert result[0].registration == 123
    assert result[0].cost_center_description is None
    assert cursor.executions[0][1]["busca"] == "Pessoa"
    assert "NUMCPF" not in cursor.executions[0][0].upper()


def test_employee_detail_returns_only_masked_cpf() -> None:
    cursor = FakeCursor(
        columns=employee_columns(detail=True),
        rows=[employee_row(detail=True)],
    )
    result = repository(cursor).get_employee(
        company=1,
        branch=2,
        employee_type=1,
        registration=123,
    )

    assert isinstance(result, EmployeeDetail)
    assert result.masked_cpf == "***.***.***-00"
    assert cursor.fetchmany_size == 2


def test_employee_detail_rejects_duplicate_contract_key() -> None:
    row = employee_row(detail=True)
    cursor = FakeCursor(
        columns=employee_columns(detail=True),
        rows=[row, row],
    )

    with pytest.raises(SeniorContractError):
        repository(cursor).get_employee(
            company=1,
            branch=2,
            employee_type=1,
            registration=123,
        )


@pytest.mark.parametrize(
    ("method", "kwargs"),
    [
        ("list_companies", {"offset": -1}),
        ("list_companies", {"limit": 0}),
        ("list_companies", {"limit": 101}),
        ("list_branches", {"company": 0}),
        (
            "list_employees",
            {
                "company": 1,
                "branch": 1,
                "employee_type": 1,
                "search": "x" * 101,
            },
        ),
    ],
)
def test_invalid_arguments_do_not_reach_oracle(
    method: str,
    kwargs: dict[str, object],
) -> None:
    cursor = FakeCursor(columns=[], rows=[])
    target = getattr(repository(cursor), method)

    with pytest.raises(SeniorQueryValidationError):
        target(**kwargs)

    assert cursor.executions == []


def test_repository_does_not_allow_configured_limit_above_contract() -> None:
    cursor = FakeCursor(columns=[], rows=[])
    connection = cast(BaseDatabaseWrapper, FakeConnection(cursor))

    with pytest.raises(SeniorQueryValidationError, match="max_page_size"):
        SeniorRepository(connection=connection, max_page_size=101)


def test_database_error_becomes_safe_integration_error_and_restores_timeout() -> None:
    cursor = FakeCursor(
        columns=["EMPRESA"],
        rows=[],
        execute_error=DatabaseError("sensitive database detail"),
    )

    with pytest.raises(
        SeniorUnavailableError,
        match="Não foi possível consultar o Senior HCM.",
    ):
        repository(cursor).list_companies()

    assert cursor.raw_connection is not None
    assert cursor.raw_connection.call_timeout == 25


def test_missing_contract_column_is_rejected() -> None:
    cursor = FakeCursor(columns=["OUTRA_COLUNA"], rows=[(1,)])

    with pytest.raises(SeniorContractError, match="EMPRESA"):
        repository(cursor).list_companies()


def test_runtime_queries_are_select_only_and_keep_active_rule() -> None:
    for sql in queries.ALL_QUERIES.values():
        normalized = sql.strip().upper()
        assert normalized.startswith("SELECT")
        assert "SITAFA <> 7" in normalized
        assert not any(
            statement in normalized
            for statement in ("INSERT ", "UPDATE ", "DELETE ", "MERGE ", "ALTER ")
        )


def test_runtime_sql_matches_the_homologated_document() -> None:
    contract_path = (
        Path(__file__).resolve().parents[1]
        / "docs"
        / "SGPD"
        / "sql"
        / "senior_reference_queries.sql"
    )
    contract = contract_path.read_text(encoding="utf-8")
    documented: dict[str, str] = {}
    sections = re.split(r"^-- name: ([a-z_]+)$", contract, flags=re.MULTILINE)
    for index in range(1, len(sections), 2):
        name = sections[index]
        body = sections[index + 1].split(";", maxsplit=1)[0]
        documented[name] = "\n".join(
            line for line in body.splitlines() if not line.startswith("--")
        )

    pairs = {
        "listar_empresas": queries.LIST_COMPANIES,
        "listar_filiais": queries.LIST_BRANCHES,
        "listar_tipos_colaborador": queries.LIST_EMPLOYEE_TYPES,
        "listar_colaboradores": queries.LIST_EMPLOYEES,
        "obter_colaborador": queries.GET_EMPLOYEE,
    }
    for name, runtime_sql in pairs.items():
        assert " ".join(documented[name].split()) == " ".join(runtime_sql.split())
