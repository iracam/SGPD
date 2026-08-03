"""Quem recebe cada aviso.

Não há dono individual de tarefa: a responsabilidade é do setor e todos os
responsáveis vigentes têm a mesma autoridade (ADR-038). Por isso todo lembrete
de tarefa vai para o conjunto inteiro — quem agir primeiro resolve, e os demais
observam o novo estado.
"""

from __future__ import annotations

from datetime import datetime

from django.db.models import Q

from apps.accounts.models import PEOPLE_DEPARTMENT_ROLE_CODES, ScopeType, User
from apps.offboarding.models import OffboardingProcess


def sector_responsibles(*, sector_id: int, at: datetime) -> tuple[User, ...]:
    """Responsáveis vigentes de um setor ativo, na mesma definição dos services."""

    return tuple(
        User.objects.filter(
            is_active=True,
            sector_responsibilities__sector_id=sector_id,
            sector_responsibilities__sector__is_active=True,
            sector_responsibilities__is_active=True,
            sector_responsibilities__valid_from__lte=at,
        )
        .filter(
            Q(sector_responsibilities__valid_until__isnull=True)
            | Q(sector_responsibilities__valid_until__gt=at)
        )
        .order_by("pk")
        .distinct()
    )


def people_department_users(*, process: OffboardingProcess, at: datetime) -> tuple[User, ...]:
    """Usuários com `DP` vigente cujo escopo alcança o processo.

    SuperAdmin não entra por autoridade global: ele enxerga tudo, mas receber
    todo atraso do sistema não é visibilidade, é ruído. Quem precisa ser avisado
    é quem responde pelo escopo.
    """

    return tuple(
        User.objects.filter(
            is_active=True,
            role_assignments__role__code__in=PEOPLE_DEPARTMENT_ROLE_CODES,
            role_assignments__role__is_active=True,
            role_assignments__is_active=True,
            role_assignments__valid_from__lte=at,
        )
        .filter(
            Q(role_assignments__valid_until__isnull=True) | Q(role_assignments__valid_until__gt=at)
        )
        .filter(
            Q(role_assignments__scope_type=ScopeType.GLOBAL)
            | Q(
                role_assignments__scope_type=ScopeType.COMPANY,
                role_assignments__company_code=process.company_code,
            )
            | Q(
                role_assignments__scope_type=ScopeType.BRANCH,
                role_assignments__company_code=process.company_code,
                role_assignments__branch_code=process.branch_code,
            )
        )
        .order_by("pk")
        .distinct()
    )
