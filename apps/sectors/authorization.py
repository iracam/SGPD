"""Operational authorization derived from explicit sector responsibility."""

from __future__ import annotations

from datetime import datetime

from django.db.models import Q, QuerySet
from django.utils import timezone

from apps.accounts.models import (
    RESPONSIBLE_SECTOR_ROLE_CODE,
    RoleAssignment,
    ScopeType,
    User,
)

from .models import SectorResponsible


def active_sector_responsibilities(
    user: User,
    *,
    sector_code: str | None = None,
    at: datetime | None = None,
) -> QuerySet[SectorResponsible]:
    """Return responsibility rows that are active and valid at the instant."""

    instant = at or timezone.now()
    responsibilities = SectorResponsible.objects.filter(
        user=user,
        user__is_active=True,
        sector__is_active=True,
        is_active=True,
        valid_from__lte=instant,
    ).filter(Q(valid_until__isnull=True) | Q(valid_until__gt=instant))
    if sector_code is not None:
        responsibilities = responsibilities.filter(sector__code=sector_code.strip().upper())
    return responsibilities


def _covers_organization(
    scope_type: str,
    scope_company_code: int | None,
    scope_branch_code: int | None,
    *,
    company_code: int,
    branch_code: int | None,
) -> bool:
    if scope_type == ScopeType.GLOBAL:
        return True
    if scope_type == ScopeType.COMPANY:
        return scope_company_code == company_code
    return (
        branch_code is not None
        and scope_type == ScopeType.BRANCH
        and scope_company_code == company_code
        and scope_branch_code == branch_code
    )


def _scopes_overlap(
    responsibility: SectorResponsible,
    assignment: RoleAssignment,
) -> bool:
    if responsibility.scope_type == ScopeType.GLOBAL or assignment.scope_type == ScopeType.GLOBAL:
        return True
    if responsibility.company_code != assignment.company_code:
        return False
    if responsibility.scope_type == ScopeType.COMPANY or assignment.scope_type == ScopeType.COMPANY:
        return True
    return responsibility.branch_code == assignment.branch_code


def has_sector_responsibility(
    user: User,
    sector_code: str,
    *,
    company_code: int | None = None,
    branch_code: int | None = None,
    at: datetime | None = None,
) -> bool:
    """Require both the fixed role and a matching sector association.

    SuperAdmin is deliberately not an implicit functional responsible.
    """

    if not user.is_authenticated or not user.is_active:
        return False
    if branch_code is not None and company_code is None:
        return False

    instant = at or timezone.now()
    responsibilities = list(
        active_sector_responsibilities(
            user,
            sector_code=sector_code,
            at=instant,
        ).select_related("sector", "user")
    )
    role_assignments = list(
        RoleAssignment.objects.filter(
            user=user,
            role__code=RESPONSIBLE_SECTOR_ROLE_CODE,
            role__is_active=True,
            is_active=True,
            valid_from__lte=instant,
        )
        .filter(Q(valid_until__isnull=True) | Q(valid_until__gt=instant))
        .select_related("role")
    )
    if company_code is not None:
        responsibilities = [
            responsibility
            for responsibility in responsibilities
            if _covers_organization(
                responsibility.scope_type,
                responsibility.company_code,
                responsibility.branch_code,
                company_code=company_code,
                branch_code=branch_code,
            )
        ]
        role_assignments = [
            assignment
            for assignment in role_assignments
            if _covers_organization(
                assignment.scope_type,
                assignment.company_code,
                assignment.branch_code,
                company_code=company_code,
                branch_code=branch_code,
            )
        ]

    return any(
        _scopes_overlap(responsibility, assignment)
        for responsibility in responsibilities
        for assignment in role_assignments
    )


def responsibility_is_effective(
    responsibility: SectorResponsible,
    *,
    at: datetime | None = None,
) -> bool:
    """Evaluate one configured row together with its fixed-role assignment."""

    instant = at or timezone.now()
    if not responsibility.is_effective(instant):
        return False
    prefetched = getattr(
        responsibility.user,
        "effective_responsible_role_assignments",
        None,
    )
    if prefetched is None:
        assignments = list(
            RoleAssignment.objects.filter(
                user=responsibility.user,
                role__code=RESPONSIBLE_SECTOR_ROLE_CODE,
                role__is_active=True,
                is_active=True,
                valid_from__lte=instant,
            )
            .filter(Q(valid_until__isnull=True) | Q(valid_until__gt=instant))
            .select_related("role")
        )
    else:
        assignments = prefetched
    return any(_scopes_overlap(responsibility, assignment) for assignment in assignments)
