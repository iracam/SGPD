"""Transactional use cases for functional sector configuration."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from django.core.exceptions import PermissionDenied, ValidationError
from django.db import IntegrityError, transaction
from django.utils import timezone

from apps.accounts.authorization import has_permission
from apps.accounts.models import ScopeType, User, build_scope_key
from config.middleware import correlation_id

from .models import (
    SectorAuditEvent,
    SectorEventType,
    SectorResponsible,
    SectorScope,
    ValidationSector,
)

MANAGE_SECTORS_PERMISSION = "sectors.manage_sectors"
SECTOR_CREATION_REASON = "Cadastro explícito de setor de validação no SGPD."
SECTOR_UPDATE_REASON = "Alteração explícita de setor de validação no SGPD."
SECTOR_ACTIVATION_REASON = "Ativação explícita de setor de validação no SGPD."
SECTOR_DEACTIVATION_REASON = "Inativação explícita de setor de validação no SGPD."
RESPONSIBLE_ASSIGNMENT_REASON = "Designação explícita de responsável no cadastro do setor."
RESPONSIBLE_UPDATE_REASON = "Alteração explícita da validade do responsável no setor."
RESPONSIBLE_REVOCATION_REASON = "Revogação explícita de responsável no cadastro do setor."


def _require_permission(actor: User) -> None:
    # A configuração pode abranger múltiplas empresas e, por isso, exige a
    # concessão administrativa global.
    if not has_permission(actor, MANAGE_SECTORS_PERMISSION):
        raise PermissionDenied("O ator não possui permissão para manter setores.")


@dataclass(frozen=True, slots=True)
class SectorScopeValue:
    scope_type: ScopeType
    company_code: int | None = None
    branch_code: int | None = None


@dataclass(frozen=True, slots=True)
class SectorResponsibleValue:
    user_id: int
    valid_from: datetime | None = None
    valid_until: datetime | None = None


def _aware_instant(value: datetime | None, *, default_now: bool = False) -> datetime | None:
    if value is None:
        return timezone.now() if default_now else None
    if timezone.is_naive(value):
        return timezone.make_aware(value)
    return value


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


def _normalize_responsibles(
    values: tuple[SectorResponsibleValue, ...],
) -> tuple[SectorResponsibleValue, ...]:
    by_user: dict[int, SectorResponsibleValue] = {}
    for index, value in enumerate(values):
        if value.user_id <= 0:
            raise ValidationError(
                {f"responsibles.{index}.user_id": "Selecione um usuário responsável."}
            )
        if value.user_id in by_user:
            raise ValidationError(
                {"responsibles": "O mesmo usuário foi informado mais de uma vez."}
            )
        valid_from = _aware_instant(value.valid_from, default_now=True)
        valid_until = _aware_instant(value.valid_until)
        assert valid_from is not None
        if valid_until is not None and valid_until <= valid_from:
            raise ValidationError(
                {
                    f"responsibles.{index}.valid_until": (
                        "A validade final deve ser posterior à inicial."
                    )
                }
            )
        by_user[value.user_id] = SectorResponsibleValue(
            user_id=value.user_id,
            valid_from=valid_from,
            valid_until=valid_until,
        )
    return tuple(by_user[user_id] for user_id in sorted(by_user))


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


def _responsibility_state(responsibility: SectorResponsible) -> dict[str, object]:
    return {
        "responsibility_id": responsibility.pk,
        "sector_id": responsibility.sector_id,
        "user_id": responsibility.user_id,
        "valid_from": responsibility.valid_from.isoformat(),
        "valid_until": (
            responsibility.valid_until.isoformat()
            if responsibility.valid_until is not None
            else None
        ),
        "is_active": responsibility.is_active,
        "version": responsibility.version,
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
        "responsibles": [
            _responsibility_state(item)
            for item in sector.responsibles.filter(is_active=True).order_by("user_id")
        ],
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
    sectors = (
        ValidationSector.objects.select_for_update()
        .prefetch_related("scopes", "responsibles")
        .order_by("pk")
    )
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


def _save_responsibility(
    responsibility: SectorResponsible,
    *,
    update_fields: tuple[str, ...] | None = None,
) -> None:
    responsibility.full_clean()
    try:
        with transaction.atomic():
            if update_fields is None:
                responsibility.save()
            else:
                responsibility.save(update_fields=update_fields)
    except IntegrityError as exc:
        raise ValidationError(
            {"responsibles": "O usuário já está vinculado a este setor."}
        ) from exc


def _sync_responsibles(
    *,
    sector: ValidationSector,
    actor: User,
    desired: tuple[SectorResponsibleValue, ...],
) -> None:
    normalized = _normalize_responsibles(desired)
    desired_by_user = {value.user_id: value for value in normalized}

    existing = list(
        SectorResponsible.objects.select_for_update()
        .filter(sector=sector)
        .select_related("user")
        .order_by("user_id")
    )
    existing_by_user = {item.user_id: item for item in existing}

    selected_users = {
        user.pk: user
        for user in User.objects.select_for_update().filter(pk__in=desired_by_user).order_by("pk")
    }
    missing_user_ids = sorted(desired_by_user.keys() - selected_users.keys())
    if missing_user_ids:
        raise ValidationError(
            {"responsibles": f"Usuário responsável inexistente: {missing_user_ids[0]}."}
        )
    inactive_user_ids = sorted(
        user_id for user_id, user in selected_users.items() if not user.is_active
    )
    if inactive_user_ids:
        raise ValidationError(
            {"responsibles": f"O usuário {inactive_user_ids[0]} precisa estar ativo."}
        )

    now = timezone.now()
    for value in normalized:
        valid_from = value.valid_from
        assert valid_from is not None
        responsibility = existing_by_user.get(value.user_id)
        before = _responsibility_state(responsibility) if responsibility is not None else None

        if responsibility is None:
            responsibility = SectorResponsible(
                sector=sector,
                user=selected_users[value.user_id],
                valid_from=valid_from,
                valid_until=value.valid_until,
                assigned_by=actor,
                assigned_at=now,
                updated_by=actor,
            )
            _save_responsibility(responsibility)
            event_type = SectorEventType.RESPONSIBLE_ASSIGNED
            reason = RESPONSIBLE_ASSIGNMENT_REASON
        elif not responsibility.is_active:
            responsibility.valid_from = valid_from
            responsibility.valid_until = value.valid_until
            responsibility.is_active = True
            responsibility.assigned_by = actor
            responsibility.assigned_at = now
            responsibility.updated_by = actor
            responsibility.revoked_by = None
            responsibility.revoked_at = None
            responsibility.version += 1
            _save_responsibility(
                responsibility,
                update_fields=(
                    "valid_from",
                    "valid_until",
                    "is_active",
                    "assigned_by",
                    "assigned_at",
                    "updated_by",
                    "updated_at",
                    "revoked_by",
                    "revoked_at",
                    "version",
                ),
            )
            event_type = SectorEventType.RESPONSIBLE_ASSIGNED
            reason = RESPONSIBLE_ASSIGNMENT_REASON
        elif (
            responsibility.valid_from != valid_from
            or responsibility.valid_until != value.valid_until
        ):
            responsibility.valid_from = valid_from
            responsibility.valid_until = value.valid_until
            responsibility.updated_by = actor
            responsibility.version += 1
            _save_responsibility(
                responsibility,
                update_fields=(
                    "valid_from",
                    "valid_until",
                    "updated_by",
                    "updated_at",
                    "version",
                ),
            )
            event_type = SectorEventType.RESPONSIBLE_UPDATED
            reason = RESPONSIBLE_UPDATE_REASON
        else:
            continue

        _record_event(
            event_type=event_type,
            actor=actor,
            sector=sector,
            reason=reason,
            changes={
                "before": before,
                "after": _responsibility_state(responsibility),
            },
        )

    for responsibility in existing:
        if not responsibility.is_active or responsibility.user_id in desired_by_user:
            continue
        before = _responsibility_state(responsibility)
        responsibility.is_active = False
        responsibility.updated_by = actor
        responsibility.revoked_by = actor
        responsibility.revoked_at = now
        responsibility.version += 1
        _save_responsibility(
            responsibility,
            update_fields=(
                "is_active",
                "updated_by",
                "updated_at",
                "revoked_by",
                "revoked_at",
                "version",
            ),
        )
        _record_event(
            event_type=SectorEventType.RESPONSIBLE_REVOKED,
            actor=actor,
            sector=sector,
            reason=RESPONSIBLE_REVOCATION_REASON,
            changes={
                "before": before,
                "after": _responsibility_state(responsibility),
            },
        )

    prefetched = getattr(sector, "_prefetched_objects_cache", None)
    if prefetched is not None:
        prefetched.pop("responsibles", None)


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
    responsibles: tuple[SectorResponsibleValue, ...]


class CreateSectorService:
    @transaction.atomic
    def execute(self, command: CreateSectorCommand) -> ValidationSector:
        _require_permission(command.actor)
        scopes = _normalize_scopes(command.scopes)
        responsibles = _normalize_responsibles(command.responsibles)
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
        _sync_responsibles(
            sector=sector,
            actor=command.actor,
            desired=responsibles,
        )
        _record_event(
            event_type=SectorEventType.CREATED,
            actor=command.actor,
            sector=sector,
            reason=SECTOR_CREATION_REASON,
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
    responsibles: tuple[SectorResponsibleValue, ...]


class UpdateSectorService:
    @transaction.atomic
    def execute(self, command: UpdateSectorCommand) -> ValidationSector:
        _require_permission(command.actor)
        scopes = _normalize_scopes(command.scopes)
        responsibles = _normalize_responsibles(command.responsibles)
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
        _sync_responsibles(
            sector=sector,
            actor=command.actor,
            desired=responsibles,
        )

        if before["is_active"] is True and not sector.is_active:
            event_type = SectorEventType.DEACTIVATED
            reason = SECTOR_DEACTIVATION_REASON
        elif before["is_active"] is False and sector.is_active:
            event_type = SectorEventType.ACTIVATED
            reason = SECTOR_ACTIVATION_REASON
        else:
            event_type = SectorEventType.UPDATED
            reason = SECTOR_UPDATE_REASON
        _record_event(
            event_type=event_type,
            actor=command.actor,
            sector=sector,
            reason=reason,
            changes={"before": before, "after": _sector_state(sector)},
        )
        return sector
