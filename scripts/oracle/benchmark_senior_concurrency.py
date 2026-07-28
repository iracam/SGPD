"""Bounded read-only concurrency benchmark for the Senior employee query."""

from __future__ import annotations

import argparse
import logging
import os
import sys
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict, dataclass
from math import ceil
from pathlib import Path
from statistics import median
from time import monotonic

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.development")

import django  # noqa: E402

django.setup()

from django.db import close_old_connections, connections  # noqa: E402

from apps.integrations.senior.repository import SeniorRepository  # noqa: E402


@dataclass(frozen=True, slots=True)
class WorkerResult:
    durations_ms: tuple[float, ...]
    row_counts: tuple[int, ...]
    errors: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class BenchmarkResult:
    concurrency: int
    requests: int
    successes: int
    errors: int
    elapsed_ms: float
    throughput_per_second: float
    p50_ms: float
    p95_ms: float
    max_ms: float
    min_rows: int
    max_rows: int


def _positive_int(value: str) -> int:
    parsed = int(value)
    if parsed <= 0:
        raise argparse.ArgumentTypeError("o valor deve ser maior que zero")
    return parsed


def _concurrency_levels(value: str) -> tuple[int, ...]:
    levels = tuple(_positive_int(item.strip()) for item in value.split(",") if item.strip())
    if not levels:
        raise argparse.ArgumentTypeError("informe ao menos um nível de concorrência")
    return levels


def _percentile(values: list[float], percentile: float) -> float:
    ordered = sorted(values)
    index = max(0, ceil(percentile * len(ordered)) - 1)
    return ordered[index]


def _probe_key() -> tuple[int, int, int]:
    repository = SeniorRepository()
    companies = repository.list_companies(offset=0, limit=1)
    if not companies:
        raise RuntimeError("Nenhuma empresa elegível foi encontrada.")
    company = companies[0].company
    branches = repository.list_branches(company=company, offset=0, limit=1)
    if not branches:
        raise RuntimeError("Nenhuma filial elegível foi encontrada.")
    branch = branches[0].branch
    employee_types = repository.list_employee_types(
        company=company,
        branch=branch,
        offset=0,
        limit=1,
    )
    if not employee_types:
        raise RuntimeError("Nenhum tipo de colaborador elegível foi encontrado.")
    return company, branch, employee_types[0].employee_type


def _worker(
    *,
    company: int,
    branch: int,
    employee_type: int,
    requests: int,
) -> WorkerResult:
    close_old_connections()
    repository = SeniorRepository()
    durations: list[float] = []
    row_counts: list[int] = []
    errors: list[str] = []
    try:
        for _ in range(requests):
            started_at = monotonic()
            try:
                rows = repository.list_employees(
                    company=company,
                    branch=branch,
                    employee_type=employee_type,
                    offset=0,
                    limit=20,
                )
            except Exception as exc:  # noqa: BLE001 - benchmark must aggregate failures.
                errors.append(type(exc).__name__)
            else:
                durations.append((monotonic() - started_at) * 1000)
                row_counts.append(len(rows))
    finally:
        connections["default"].close()
    return WorkerResult(
        durations_ms=tuple(durations),
        row_counts=tuple(row_counts),
        errors=tuple(errors),
    )


def _run_level(
    *,
    concurrency: int,
    requests_per_worker: int,
    company: int,
    branch: int,
    employee_type: int,
) -> BenchmarkResult:
    started_at = monotonic()
    with ThreadPoolExecutor(max_workers=concurrency) as executor:
        futures = [
            executor.submit(
                _worker,
                company=company,
                branch=branch,
                employee_type=employee_type,
                requests=requests_per_worker,
            )
            for _ in range(concurrency)
        ]
        worker_results = [future.result() for future in futures]
    elapsed_ms = (monotonic() - started_at) * 1000

    durations = [duration for result in worker_results for duration in result.durations_ms]
    row_counts = [row_count for result in worker_results for row_count in result.row_counts]
    errors = [error for result in worker_results for error in result.errors]
    if not durations:
        raise RuntimeError("Todas as consultas falharam: " + ", ".join(sorted(set(errors))))

    return BenchmarkResult(
        concurrency=concurrency,
        requests=concurrency * requests_per_worker,
        successes=len(durations),
        errors=len(errors),
        elapsed_ms=round(elapsed_ms, 2),
        throughput_per_second=round(len(durations) / (elapsed_ms / 1000), 2),
        p50_ms=round(median(durations), 2),
        p95_ms=round(_percentile(durations, 0.95), 2),
        max_ms=round(max(durations), 2),
        min_rows=min(row_counts),
        max_rows=max(row_counts),
    )


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Mede a consulta read-only de colaboradores sob concorrência controlada."
    )
    parser.add_argument(
        "--concurrency",
        type=_concurrency_levels,
        default=(1, 5, 10),
        help="níveis separados por vírgula; padrão: 1,5,10",
    )
    parser.add_argument(
        "--requests-per-worker",
        type=_positive_int,
        default=5,
        help="consultas sequenciais por conexão; padrão: 5",
    )
    args = parser.parse_args()

    logging.getLogger("apps.integrations.senior.repository").setLevel(logging.WARNING)
    company, branch, employee_type = _probe_key()
    connections["default"].close()

    had_errors = False
    for concurrency in args.concurrency:
        result = _run_level(
            concurrency=concurrency,
            requests_per_worker=args.requests_per_worker,
            company=company,
            branch=branch,
            employee_type=employee_type,
        )
        had_errors = had_errors or result.errors > 0
        print(asdict(result))
    return 1 if had_errors else 0


if __name__ == "__main__":
    sys.exit(main())
