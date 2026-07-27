"""Immutable values returned by the Senior HCM repository."""

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True, slots=True)
class Company:
    company: int


@dataclass(frozen=True, slots=True)
class Branch:
    company: int
    branch: int
    legal_name: str


@dataclass(frozen=True, slots=True)
class EmployeeType:
    employee_type: int
    description: str


@dataclass(frozen=True, slots=True)
class Employee:
    company: int
    branch: int
    legal_name: str
    employee_type: int
    employee_type_description: str
    registration: int
    name: str
    admission_date: datetime
    leave_code: int
    leave_description: str
    leave_date: datetime | None
    job_structure: int
    job_code: str
    job_description: str
    cost_center: str
    cost_center_description: str | None
    source_updated_at: datetime | None


@dataclass(frozen=True, slots=True)
class EmployeeDetail(Employee):
    masked_cpf: str | None
