"""Operational authorization derived from effective sector links."""

from __future__ import annotations

from datetime import datetime

from django.db.models import Q, QuerySet
from django.utils import timezone

from apps.accounts.authorization import has_global_authority
from apps.accounts.models import ScopeType, User

from .models import SectorResponsible


def active_sector_responsibilities(
    user: User,
    sector_code: str | None = None,
    *,
    at: datetime | None = None,
) -> QuerySet[SectorResponsible]:
    """Return links effective for the user at the requested instant."""

    instant = at or timezone.now()
    responsibilities = (
        SectorResponsible.objects.filter(
            user=user,
            user__is_active=True,
            sector__is_active=True,
            is_active=True,
            valid_from__lte=instant,
        )
        .filter(Q(valid_until__isnull=True) | Q(valid_until__gt=instant))
        .select_related("sector", "user")
        .prefetch_related("sector__scopes")
    )
    if sector_code is not None:
        responsibilities = responsibilities.filter(sector__code=sector_code.strip().upper())
    return responsibilities


def has_sector_responsibility(
    user: User,
    sector_code: str,
    *,
    company_code: int | None = None,
    branch_code: int | None = None,
    at: datetime | None = None,
) -> bool:
    """Check global authority or responsibility and its inherited scope."""

    if not user.is_active:
        return False
    if has_global_authority(user):
        return True

    responsibilities = active_sector_responsibilities(
        user,
        sector_code,
        at=at,
    )
    if company_code is None and branch_code is None:
        return responsibilities.exists()
    if company_code is None:
        return False

    scope_filter = Q(sector__scopes__scope_type=ScopeType.GLOBAL) | Q(
        sector__scopes__scope_type=ScopeType.COMPANY,
        sector__scopes__company_code=company_code,
    )
    if branch_code is not None:
        scope_filter |= Q(
            sector__scopes__scope_type=ScopeType.BRANCH,
            sector__scopes__company_code=company_code,
            sector__scopes__branch_code=branch_code,
        )
    return responsibilities.filter(scope_filter).exists()


def responsibility_is_effective(
    responsibility: SectorResponsible,
    *,
    at: datetime | None = None,
) -> bool:
    """Expose the model validity rule for API payloads and domain checks."""

    return responsibility.is_effective(at)
