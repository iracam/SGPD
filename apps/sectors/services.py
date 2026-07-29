"""Transactional use cases for functional sector configuration."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from django.core.exceptions import PermissionDenied, ValidationError
from django.db import IntegrityError, transaction
from django.utils import timezone

from apps.accounts.authorization import has_permission
from apps.accounts.models import (
    RESPONSIBLE_SECTOR_ROLE_CODE,
    RoleAssignment,
    ScopeType,
    User,
    build_scope_key,
)
from config.middleware import correlation_id

from .models import (
    SectorAuditEvent,
    SectorEventType,
    SectorResponsible,
    SectorScope,
    ValidationSector,
)

MANAGE_SECTORS_PERMISSION = "sectors.manage_sectors"


def _require_permission(actor: User) -> None:
    # Sector configuration may span companies. In this first slice the
    # administrative permission therefore requires an effective global grant.
    if not has_permission(actor, MANAGE_SECTORS_PERMISSION):
        raise PermissionDenied("O ator não possui permissão para manter setores.")


def _required_reason(reason: str) -> str:
    normalized = reason.strip()
    if not normalized:
        raise ValidationError({"reason": "A justificativa é obrigatória."})
    return normalized


@dataclass(frozen=True, slots=True)
class SectorScopeValue:
    scope_type: ScopeType
    company_code: int | None = None
    branch_code: int | None = None


def _normalize_scopes(scopes: tuple[SectorScopeValue, ...]) -> tuple[SectorScopeValue, ...]:
    if not scopes:
        raise ValidationError({"scopes": "Informe ao menos um escopo de atendimento."})

    by_key: dict[str, SectorScopeValue] = {}
    for scope in scopes:
        key = build_scope_key(scope.scope_type, scope.company_code, scope.branch_code)
        if key in by_key:
            raise ValidationError({"scopes": "O mesmo escopo foi informado mais de uma vez."})
        by_key[key] = scope

    if "*" in by_key and len(by_key) > 1:
        raise ValidationError(
            {"scopes": "O escopo global não pode ser combinado com empresa ou filial."}
        )

    company_scopes = {
        scope.company_code for scope in by_key.values() if scope.scope_type == ScopeType.COMPANY
    }
    if any(
        scope.scope_type == ScopeType.BRANCH and scope.company_code in company_scopes
        for scope in by_key.values()
    ):
        raise ValidationError(
            {"scopes": "Uma filial não deve ser repetida quando toda a empresa já é atendida."}
        )

    return tuple(by_key[key] for key in sorted(by_key))


def _scope_payload(scope: SectorScope | SectorScopeValue) -> dict[str, object]:
    return {
        "scope_type": scope.scope_type,
        "company_code": scope.company_code,
        "branch_code": scope.branch_code,
        "scope_key": build_scope_key(
            scope.scope_type,
            scope.company_code,
            scope.branch_code,
        ),
    }


def _sector_state(sector: ValidationSector) -> dict[str, object]:
    return {
        "code": sector.code,
        "name": sector.name,
        "description": sector.description,
        "is_active": sector.is_active,
        "default_due_hours": sector.default_due_hours,
        "blocks_process": sector.blocks_process,
        "allows_amount": sector.allows_amount,
        "requires_evidence": sector.requires_evidence,
        "escalation_sector_id": sector.escalation_sector_id,
        "scopes": [_scope_payload(scope) for scope in sector.scopes.all().order_by("scope_key")],
    }


def _write_scopes(
    sector: ValidationSector,
    scopes: tuple[SectorScopeValue, ...],
) -> None:
    sector.scopes.all().delete()
    for value in scopes:
        scope = SectorScope(
            sector=sector,
            scope_type=value.scope_type,
            company_code=value.company_code,
            branch_code=value.branch_code,
        )
        scope.full_clean()
        scope.save()
    prefetched = getattr(sector, "_prefetched_objects_cache", None)
    if prefetched is not None:
        prefetched.pop("scopes", None)


def _lock_sector_configuration() -> dict[int, ValidationSector]:
    """Serialize catalog mutations so escalation cycles cannot race."""
    sectors = ValidationSector.objects.select_for_update().prefetch_related("scopes").order_by("pk")
    return {sector.pk: sector for sector in sectors}


def _escalation_sector(
    escalation_sector_id: int | None,
    *,
    sectors_by_id: dict[int, ValidationSector],
    current_sector_id: int | None = None,
) -> ValidationSector | None:
    if escalation_sector_id is None:
        return None
    if current_sector_id is not None and escalation_sector_id == current_sector_id:
        raise ValidationError(
            {"escalation_sector_id": "O setor não pode escalar para ele próprio."}
        )
    try:
        escalation = sectors_by_id[escalation_sector_id]
    except KeyError as exc:
        raise ValidationError({"escalation_sector_id": "O setor de escalada não existe."}) from exc
    if not escalation.is_active:
        raise ValidationError({"escalation_sector_id": "O setor de escalada precisa estar ativo."})

    seen = {current_sector_id} if current_sector_id is not None else set()
    cursor: ValidationSector | None = escalation
    while cursor is not None:
        if cursor.pk in seen:
            raise ValidationError(
                {"escalation_sector_id": "A configuração criaria um ciclo de escalada."}
            )
        seen.add(cursor.pk)
        cursor = (
            sectors_by_id.get(cursor.escalation_sector_id)
            if cursor.escalation_sector_id is not None
            else None
        )
    return escalation


def _record_event(
    *,
    event_type: SectorEventType,
    actor: User,
    sector: ValidationSector,
    reason: str,
    changes: dict[str, object],
) -> SectorAuditEvent:
    return SectorAuditEvent.objects.create(
        event_type=event_type,
        actor=actor,
        sector=sector,
        reason=reason,
        changes=changes,
        correlation_id=correlation_id.get(),
    )


@dataclass(frozen=True, slots=True)
class CreateSectorCommand:
    actor: User
    code: str
    name: str
    description: str
    default_due_hours: int
    blocks_process: bool
    allows_amount: bool
    requires_evidence: bool
    escalation_sector_id: int | None
    scopes: tuple[SectorScopeValue, ...]
    reason: str


class CreateSectorService:
    @transaction.atomic
    def execute(self, command: CreateSectorCommand) -> ValidationSector:
        _require_permission(command.actor)
        reason = _required_reason(command.reason)
        scopes = _normalize_scopes(command.scopes)
        sectors_by_id = _lock_sector_configuration()
        escalation = _escalation_sector(
            command.escalation_sector_id,
            sectors_by_id=sectors_by_id,
        )
        sector = ValidationSector(
            code=command.code,
            name=command.name,
            description=command.description,
            default_due_hours=command.default_due_hours,
            blocks_process=command.blocks_process,
            allows_amount=command.allows_amount,
            requires_evidence=command.requires_evidence,
            escalation_sector=escalation,
        )
        sector.full_clean()
        try:
            sector.save()
        except IntegrityError as exc:
            raise ValidationError({"code": "Já existe um setor com este código."}) from exc
        _write_scopes(sector, scopes)
        _record_event(
            event_type=SectorEventType.CREATED,
            actor=command.actor,
            sector=sector,
            reason=reason,
            changes={"after": _sector_state(sector)},
        )
        return sector


@dataclass(frozen=True, slots=True)
class UpdateSectorCommand:
    actor: User
    sector_id: int
    expected_version: int
    name: str
    description: str
    is_active: bool
    default_due_hours: int
    blocks_process: bool
    allows_amount: bool
    requires_evidence: bool
    escalation_sector_id: int | None
    scopes: tuple[SectorScopeValue, ...]
    reason: str


class UpdateSectorService:
    @transaction.atomic
    def execute(self, command: UpdateSectorCommand) -> ValidationSector:
        _require_permission(command.actor)
        reason = _required_reason(command.reason)
        scopes = _normalize_scopes(command.scopes)
        sectors_by_id = _lock_sector_configuration()
        try:
            sector = sectors_by_id[command.sector_id]
        except KeyError as exc:
            raise ValidationSector.DoesNotExist from exc
        if sector.version != command.expected_version:
            raise ValidationError("O setor foi alterado por outra sessão. Recarregue a página.")
        if (
            sector.is_active
            and not command.is_active
            and sector.escalation_sources.filter(is_active=True).exists()
        ):
            raise ValidationError(
                {"is_active": "O setor é usado como destino de escalada por um setor ativo."}
            )

        before = _sector_state(sector)
        escalation = _escalation_sector(
            command.escalation_sector_id,
            sectors_by_id=sectors_by_id,
            current_sector_id=sector.pk,
        )
        sector.name = command.name
        sector.description = command.description
        sector.is_active = command.is_active
        sector.default_due_hours = command.default_due_hours
        sector.blocks_process = command.blocks_process
        sector.allows_amount = command.allows_amount
        sector.requires_evidence = command.requires_evidence
        sector.escalation_sector = escalation
        sector.version += 1
        sector.full_clean()
        sector.save(
            update_fields=(
                "name",
                "description",
                "is_active",
                "default_due_hours",
                "blocks_process",
                "allows_amount",
                "requires_evidence",
                "escalation_sector",
                "version",
                "updated_at",
            )
        )
        _write_scopes(sector, scopes)

        if before["is_active"] is True and not sector.is_active:
            event_type = SectorEventType.DEACTIVATED
        elif before["is_active"] is False and sector.is_active:
            event_type = SectorEventType.ACTIVATED
        else:
            event_type = SectorEventType.UPDATED
        _record_event(
            event_type=event_type,
            actor=command.actor,
            sector=sector,
            reason=reason,
            changes={"before": before, "after": _sector_state(sector)},
        )
        return sector


def _aware_instant(value: datetime | None, *, default_now: bool = False) -> datetime | None:
    if value is None:
        return timezone.now() if default_now else None
    if timezone.is_naive(value):
        return timezone.make_aware(value)
    return value


def _scope_covers(
    container_scope_type: str,
    container_company_code: int | None,
    container_branch_code: int | None,
    target: SectorScopeValue,
) -> bool:
    if container_scope_type == ScopeType.GLOBAL:
        return True
    if container_scope_type == ScopeType.COMPANY:
        return (
            target.scope_type in {ScopeType.COMPANY, ScopeType.BRANCH}
            and target.company_code == container_company_code
        )
    return (
        container_scope_type == ScopeType.BRANCH
        and target.scope_type == ScopeType.BRANCH
        and target.company_code == container_company_code
        and target.branch_code == container_branch_code
    )


def _responsibility_state(responsibility: SectorResponsible) -> dict[str, object]:
    return {
        "responsibility_id": responsibility.pk,
        "sector_id": responsibility.sector_id,
        "user_id": responsibility.user_id,
        "scope_type": responsibility.scope_type,
        "company_code": responsibility.company_code,
        "branch_code": responsibility.branch_code,
        "scope_key": responsibility.scope_key,
        "valid_from": responsibility.valid_from.isoformat(),
        "valid_until": (
            responsibility.valid_until.isoformat()
            if responsibility.valid_until is not None
            else None
        ),
        "is_active": responsibility.is_active,
        "version": responsibility.version,
    }


def _validate_responsibility_contract(
    *,
    sector_id: int,
    user_id: int,
    scope: SectorScopeValue,
    valid_from: datetime | None,
    valid_until: datetime | None,
) -> tuple[ValidationSector, User, datetime, datetime | None]:
    normalized_valid_from = _aware_instant(valid_from, default_now=True)
    normalized_valid_until = _aware_instant(valid_until)
    assert normalized_valid_from is not None
    if normalized_valid_until is not None and normalized_valid_until <= normalized_valid_from:
        raise ValidationError({"valid_until": "A validade final deve ser posterior à inicial."})

    sector = (
        ValidationSector.objects.select_for_update().prefetch_related("scopes").get(pk=sector_id)
    )
    user = User.objects.select_for_update().get(pk=user_id)
    if not sector.is_active:
        raise ValidationError({"sector_id": "O setor precisa estar ativo."})
    if not user.is_active:
        raise ValidationError({"user_id": "O usuário precisa estar ativo."})

    build_scope_key(scope.scope_type, scope.company_code, scope.branch_code)
    if not any(
        _scope_covers(
            sector_scope.scope_type,
            sector_scope.company_code,
            sector_scope.branch_code,
            scope,
        )
        for sector_scope in sector.scopes.all()
    ):
        raise ValidationError(
            {"scope_type": "O escopo do responsável excede o atendimento do setor."}
        )

    role_assignments = list(
        RoleAssignment.objects.select_for_update()
        .select_related("role")
        .filter(
            user=user,
            role__code=RESPONSIBLE_SECTOR_ROLE_CODE,
            role__is_active=True,
            is_active=True,
            valid_from__lte=normalized_valid_from,
        )
        .order_by("pk")
    )
    role_covers_responsibility = any(
        _scope_covers(
            assignment.scope_type,
            assignment.company_code,
            assignment.branch_code,
            scope,
        )
        and (
            assignment.valid_until is None
            or (
                normalized_valid_until is not None
                and assignment.valid_until >= normalized_valid_until
            )
        )
        for assignment in role_assignments
    )
    if not role_covers_responsibility:
        raise ValidationError(
            {
                "user_id": (
                    "O usuário precisa possuir o papel RESPONSAVEL_SETOR com "
                    "escopo e validade que cubram toda a responsabilidade."
                )
            }
        )
    return sector, user, normalized_valid_from, normalized_valid_until


@dataclass(frozen=True, slots=True)
class AssignSectorResponsibleCommand:
    actor: User
    sector_id: int
    user_id: int
    scope_type: ScopeType
    company_code: int | None
    branch_code: int | None
    valid_from: datetime | None
    valid_until: datetime | None
    reason: str


class AssignSectorResponsibleService:
    @transaction.atomic
    def execute(self, command: AssignSectorResponsibleCommand) -> SectorResponsible:
        _require_permission(command.actor)
        reason = _required_reason(command.reason)
        scope = SectorScopeValue(
            scope_type=command.scope_type,
            company_code=command.company_code,
            branch_code=command.branch_code,
        )
        sector, user, valid_from, valid_until = _validate_responsibility_contract(
            sector_id=command.sector_id,
            user_id=command.user_id,
            scope=scope,
            valid_from=command.valid_from,
            valid_until=command.valid_until,
        )
        scope_key = build_scope_key(
            scope.scope_type,
            scope.company_code,
            scope.branch_code,
        )
        try:
            responsibility = SectorResponsible.objects.select_for_update().get(
                sector=sector,
                user=user,
                scope_key=scope_key,
            )
        except SectorResponsible.DoesNotExist:
            responsibility = None

        before = _responsibility_state(responsibility) if responsibility is not None else None
        if responsibility is not None and responsibility.is_active:
            if (
                responsibility.valid_from == valid_from
                and responsibility.valid_until == valid_until
            ):
                return responsibility
            raise ValidationError(
                {
                    "user_id": (
                        "Este usuário já possui uma responsabilidade ativa para "
                        "o mesmo setor e escopo."
                    )
                }
            )

        now = timezone.now()
        if responsibility is None:
            responsibility = SectorResponsible(
                sector=sector,
                user=user,
                scope_type=scope.scope_type,
                company_code=scope.company_code,
                branch_code=scope.branch_code,
                scope_key=scope_key,
                valid_from=valid_from,
                valid_until=valid_until,
                assigned_by=command.actor,
                assigned_at=now,
                updated_by=command.actor,
            )
        else:
            responsibility.valid_from = valid_from
            responsibility.valid_until = valid_until
            responsibility.is_active = True
            responsibility.assigned_by = command.actor
            responsibility.assigned_at = now
            responsibility.updated_by = command.actor
            responsibility.revoked_by = None
            responsibility.revoked_at = None
            responsibility.version += 1

        responsibility.full_clean()
        try:
            with transaction.atomic():
                responsibility.save()
        except IntegrityError as exc:
            raise ValidationError(
                {
                    "user_id": (
                        "Este usuário já possui uma responsabilidade para o mesmo setor e escopo."
                    )
                }
            ) from exc
        _record_event(
            event_type=SectorEventType.RESPONSIBLE_ASSIGNED,
            actor=command.actor,
            sector=sector,
            reason=reason,
            changes={
                "before": before,
                "after": _responsibility_state(responsibility),
            },
        )
        return responsibility


@dataclass(frozen=True, slots=True)
class UpdateSectorResponsibleCommand:
    actor: User
    responsibility_id: int
    expected_version: int
    valid_from: datetime
    valid_until: datetime | None
    reason: str


class UpdateSectorResponsibleService:
    @transaction.atomic
    def execute(self, command: UpdateSectorResponsibleCommand) -> SectorResponsible:
        _require_permission(command.actor)
        reason = _required_reason(command.reason)
        current = SectorResponsible.objects.get(pk=command.responsibility_id)
        scope = SectorScopeValue(
            scope_type=ScopeType(current.scope_type),
            company_code=current.company_code,
            branch_code=current.branch_code,
        )
        sector, _user, valid_from, valid_until = _validate_responsibility_contract(
            sector_id=current.sector_id,
            user_id=current.user_id,
            scope=scope,
            valid_from=command.valid_from,
            valid_until=command.valid_until,
        )
        responsibility = SectorResponsible.objects.select_for_update().get(
            pk=command.responsibility_id
        )
        if responsibility.version != command.expected_version:
            raise ValidationError(
                "A responsabilidade foi alterada por outra sessão. Recarregue a página."
            )
        if not responsibility.is_active:
            raise ValidationError(
                "Uma responsabilidade revogada deve ser reativada por nova associação."
            )
        if responsibility.valid_from == valid_from and responsibility.valid_until == valid_until:
            return responsibility

        before = _responsibility_state(responsibility)
        responsibility.valid_from = valid_from
        responsibility.valid_until = valid_until
        responsibility.updated_by = command.actor
        responsibility.version += 1
        responsibility.full_clean()
        responsibility.save(
            update_fields=(
                "valid_from",
                "valid_until",
                "updated_by",
                "updated_at",
                "version",
            )
        )
        _record_event(
            event_type=SectorEventType.RESPONSIBLE_UPDATED,
            actor=command.actor,
            sector=sector,
            reason=reason,
            changes={
                "before": before,
                "after": _responsibility_state(responsibility),
            },
        )
        return responsibility


@dataclass(frozen=True, slots=True)
class RevokeSectorResponsibleCommand:
    actor: User
    responsibility_id: int
    expected_version: int
    reason: str


class RevokeSectorResponsibleService:
    @transaction.atomic
    def execute(self, command: RevokeSectorResponsibleCommand) -> SectorResponsible:
        _require_permission(command.actor)
        reason = _required_reason(command.reason)
        current = SectorResponsible.objects.get(pk=command.responsibility_id)
        sector = ValidationSector.objects.select_for_update().get(pk=current.sector_id)
        User.objects.select_for_update().get(pk=current.user_id)
        responsibility = SectorResponsible.objects.select_for_update().get(
            pk=command.responsibility_id
        )
        if not responsibility.is_active:
            return responsibility
        if responsibility.version != command.expected_version:
            raise ValidationError(
                "A responsabilidade foi alterada por outra sessão. Recarregue a página."
            )

        before = _responsibility_state(responsibility)
        responsibility.is_active = False
        responsibility.updated_by = command.actor
        responsibility.revoked_by = command.actor
        responsibility.revoked_at = timezone.now()
        responsibility.version += 1
        responsibility.full_clean()
        responsibility.save(
            update_fields=(
                "is_active",
                "updated_by",
                "updated_at",
                "revoked_by",
                "revoked_at",
                "version",
            )
        )
        _record_event(
            event_type=SectorEventType.RESPONSIBLE_REVOKED,
            actor=command.actor,
            sector=sector,
            reason=reason,
            changes={
                "before": before,
                "after": _responsibility_state(responsibility),
            },
        )
        return responsibility
