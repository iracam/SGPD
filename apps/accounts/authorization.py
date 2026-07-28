"""Explicit role-and-scope authorization for SGPD use cases."""

from __future__ import annotations

from django.db.models import Q, QuerySet
from django.utils import timezone

from .models import RoleAssignment, ScopeType, User


def _permission_parts(permission: str) -> tuple[str, str]:
    app_label, separator, codename = permission.partition(".")
    if not separator:
        return "accounts", app_label
    return app_label, codename


def active_assignments(user: User) -> QuerySet[RoleAssignment]:
    """Single definition of "assigned, not revoked and valid right now"."""

    now = timezone.now()
    return RoleAssignment.objects.filter(
        user=user,
        user__is_active=True,
        role__is_active=True,
        is_active=True,
        valid_from__lte=now,
    ).filter(Q(valid_until__isnull=True) | Q(valid_until__gt=now))


def effective_assignments(user: User, permission: str) -> QuerySet[RoleAssignment]:
    app_label, codename = _permission_parts(permission)
    return active_assignments(user).filter(
        role__permissions__content_type__app_label=app_label,
        role__permissions__codename=codename,
    )


def has_permission(
    user: User,
    permission: str,
    *,
    company_code: int | None = None,
    branch_code: int | None = None,
) -> bool:
    if not user.is_authenticated or not user.is_active:
        return False
    if user.is_superuser:
        return True

    app_label, codename = _permission_parts(permission)
    if user.user_permissions.filter(
        content_type__app_label=app_label,
        codename=codename,
    ).exists():
        return True

    assignments = effective_assignments(user, permission)
    if company_code is None:
        return assignments.filter(scope_type=ScopeType.GLOBAL).exists()
    if branch_code is None:
        return assignments.filter(
            Q(scope_type=ScopeType.GLOBAL)
            | Q(scope_type=ScopeType.COMPANY, company_code=company_code)
        ).exists()
    return assignments.filter(
        Q(scope_type=ScopeType.GLOBAL)
        | Q(scope_type=ScopeType.COMPANY, company_code=company_code)
        | Q(
            scope_type=ScopeType.BRANCH,
            company_code=company_code,
            branch_code=branch_code,
        )
    ).exists()


def allowed_company_codes(user: User, permission: str) -> set[int] | None:
    """Return None for global access, otherwise the explicit allowed companies."""

    if not user.is_authenticated or not user.is_active:
        return set()
    if user.is_superuser:
        return None
    app_label, codename = _permission_parts(permission)
    if user.user_permissions.filter(
        content_type__app_label=app_label,
        codename=codename,
    ).exists():
        return None
    assignments = effective_assignments(user, permission)
    if assignments.filter(scope_type=ScopeType.GLOBAL).exists():
        return None
    company_codes = assignments.exclude(company_code__isnull=True).values_list(
        "company_code",
        flat=True,
    )
    return {company_code for company_code in company_codes if company_code is not None}
