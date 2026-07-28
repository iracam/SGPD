"""Immutable values returned by Active Directory queries."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class DirectoryUser:
    identifier: str
    username: str
    user_principal_name: str | None
    first_name: str | None
    last_name: str | None
    display_name: str
    email: str | None
    distinguished_name: str

    @property
    def missing_import_fields(self) -> tuple[str, ...]:
        missing: list[str] = []
        if not self.username:
            missing.append("sAMAccountName")
        if not self.first_name:
            missing.append("givenName")
        if not self.last_name:
            missing.append("sn")
        if not self.email:
            missing.append("mail")
        return tuple(missing)

    @property
    def can_import(self) -> bool:
        return not self.missing_import_fields


@dataclass(frozen=True, slots=True)
class DirectoryGroup:
    distinguished_name: str
    name: str
    account_name: str | None
    description: str | None


@dataclass(frozen=True, slots=True)
class DirectoryProbe:
    user_search_base_source: str
    group_search_base_source: str
    secure_transport: bool
