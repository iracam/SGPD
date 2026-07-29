"""Sector-responsibility services, authorization, audit and API contract."""

from __future__ import annotations

from datetime import timedelta
from typing import Any

import pytest
from django.contrib.auth.models import Permission
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import IntegrityError
from django.test import Client
from django.urls import reverse
from django.utils import timezone

from apps.accounts.models import (
    RESPONSIBLE_SECTOR_ROLE_CODE,
    Role,
    RoleAssignment,
    ScopeType,
    User,
    build_scope_key,
)
from apps.sectors.authorization import has_sector_responsibility
from apps.sectors.models import (
    SectorAuditEvent,
    SectorEventType,
    SectorResponsible,
    SectorScope,
    ValidationSector,
)
from apps.sectors.services import (
    AssignSectorResponsibleCommand,
    AssignSectorResponsibleService,
    RevokeSectorResponsibleCommand,
    RevokeSectorResponsibleService,
    UpdateSectorResponsibleCommand,
    UpdateSectorResponsibleService,
)

pytestmark = pytest.mark.django_db

PASSWORD = "Sector-responsibles-only!2026"


@pytest.fixture
def actor() -> User:
    return User.objects.create_superuser(
        username="responsaveis.admin",
        email="responsaveis.admin@example.invalid",
        password=PASSWORD,
        first_name="Responsáveis",
        last_name="Admin",
    )


@pytest.fixture
def plain_user() -> User:
    return User.objects.create_user(
        username="responsaveis.comum",
        email="responsaveis.comum@example.invalid",
        password=PASSWORD,
        first_name="Responsáveis",
        last_name="Comum",
    )


@pytest.fixture
def role() -> Role:
    return Role.objects.create(
        code=RESPONSIBLE_SECTOR_ROLE_CODE,
        name="Responsável de setor",
    )


@pytest.fixture
def responsible_user(actor: User, role: Role) -> User:
    user = User.objects.create_user(
        username="maria.responsavel",
        email="maria.responsavel@example.invalid",
        password=PASSWORD,
        first_name="Maria",
        last_name="Responsável",
    )
    RoleAssignment.objects.create(
        user=user,
        role=role,
        scope_type=ScopeType.GLOBAL,
        scope_key=build_scope_key(ScopeType.GLOBAL, None, None),
        valid_from=timezone.now() - timedelta(days=1),
        assigned_by=actor,
    )
    return user


@pytest.fixture
def sector() -> ValidationSector:
    current = ValidationSector.objects.create(
        code="TECNOLOGIA",
        name="Tecnologia",
        description="Valida acessos e equipamentos.",
        default_due_hours=24,
        blocks_process=True,
        allows_amount=False,
        requires_evidence=False,
    )
    scope = SectorScope(
        sector=current,
        scope_type=ScopeType.GLOBAL,
    )
    scope.full_clean()
    scope.save()
    return current


@pytest.fixture
def client_actor(actor: User) -> Client:
    client = Client()
    client.force_login(actor)
    return client


def assign_command(
    actor: User,
    sector: ValidationSector,
    user: User,
    **overrides: Any,
) -> AssignSectorResponsibleCommand:
    values: dict[str, Any] = {
        "actor": actor,
        "sector_id": sector.pk,
        "user_id": user.pk,
        "scope_type": ScopeType.GLOBAL,
        "company_code": None,
        "branch_code": None,
        "valid_from": timezone.now(),
        "valid_until": None,
        "reason": "Associação funcional homologada.",
    }
    values.update(overrides)
    return AssignSectorResponsibleCommand(**values)


def api_payload(
    sector: ValidationSector,
    user: User,
    *,
    valid_from: Any | None = None,
) -> dict[str, Any]:
    return {
        "sector_id": sector.pk,
        "user_id": user.pk,
        "scope_type": ScopeType.GLOBAL,
        "company_code": None,
        "branch_code": None,
        "valid_from": (valid_from or timezone.now()).isoformat(),
        "valid_until": None,
        "reason": "Associação funcional homologada.",
    }


def post_json(client: Client, name: str, payload: dict[str, Any], **kwargs: Any) -> Any:
    return client.post(
        reverse(name, kwargs=kwargs),
        data=payload,
        content_type="application/json",
    )


def patch_json(client: Client, name: str, payload: dict[str, Any], **kwargs: Any) -> Any:
    return client.patch(
        reverse(name, kwargs=kwargs),
        data=payload,
        content_type="application/json",
    )


def test_assign_responsible_is_versioned_and_audited(
    actor: User,
    sector: ValidationSector,
    responsible_user: User,
) -> None:
    responsibility = AssignSectorResponsibleService().execute(
        assign_command(actor, sector, responsible_user)
    )

    assert responsibility.scope_key == "*"
    assert responsibility.version == 1
    assert responsibility.is_active
    assert responsibility.assigned_by == actor
    event = SectorAuditEvent.objects.get(event_type=SectorEventType.RESPONSIBLE_ASSIGNED)
    assert event.actor == actor
    assert event.sector == sector
    assert event.changes["after"]["user_id"] == responsible_user.pk
    assert "coordinator" not in event.changes["after"]


def test_assignment_requires_manage_sector_permission(
    plain_user: User,
    sector: ValidationSector,
    responsible_user: User,
) -> None:
    with pytest.raises(PermissionDenied):
        AssignSectorResponsibleService().execute(
            assign_command(plain_user, sector, responsible_user)
        )

    permission = Permission.objects.get(
        content_type__app_label="sectors",
        codename="manage_sectors",
    )
    plain_user.user_permissions.add(permission)
    responsibility = AssignSectorResponsibleService().execute(
        assign_command(plain_user, sector, responsible_user)
    )
    assert responsibility.pk is not None


def test_assignment_rejects_user_without_fixed_role(
    actor: User,
    sector: ValidationSector,
    plain_user: User,
) -> None:
    dp_role = Role.objects.create(code="DP", name="Departamento Pessoal")
    RoleAssignment.objects.create(
        user=plain_user,
        role=dp_role,
        scope_type=ScopeType.GLOBAL,
        scope_key=build_scope_key(ScopeType.GLOBAL, None, None),
        valid_from=timezone.now() - timedelta(days=1),
        assigned_by=actor,
    )

    with pytest.raises(ValidationError, match="RESPONSAVEL_SETOR"):
        AssignSectorResponsibleService().execute(assign_command(actor, sector, plain_user))

    assert not SectorResponsible.objects.exists()


def test_assignment_rejects_inactive_user_or_sector(
    actor: User,
    sector: ValidationSector,
    responsible_user: User,
) -> None:
    responsible_user.is_active = False
    responsible_user.save(update_fields=("is_active",))
    with pytest.raises(ValidationError, match="usuário precisa estar ativo"):
        AssignSectorResponsibleService().execute(assign_command(actor, sector, responsible_user))

    responsible_user.is_active = True
    responsible_user.save(update_fields=("is_active",))
    sector.is_active = False
    sector.save(update_fields=("is_active",))
    with pytest.raises(ValidationError, match="setor precisa estar ativo"):
        AssignSectorResponsibleService().execute(assign_command(actor, sector, responsible_user))


def test_assignment_scope_must_fit_sector_coverage(
    actor: User,
    sector: ValidationSector,
    responsible_user: User,
) -> None:
    sector.scopes.all().delete()
    company_scope = SectorScope(
        sector=sector,
        scope_type=ScopeType.COMPANY,
        company_code=7,
    )
    company_scope.full_clean()
    company_scope.save()

    with pytest.raises(ValidationError, match="excede o atendimento do setor"):
        AssignSectorResponsibleService().execute(
            assign_command(
                actor,
                sector,
                responsible_user,
                scope_type=ScopeType.COMPANY,
                company_code=8,
            )
        )


def test_assignment_scope_and_validity_must_fit_role(
    actor: User,
    sector: ValidationSector,
    responsible_user: User,
) -> None:
    assignment = RoleAssignment.objects.get(user=responsible_user)
    assignment.scope_type = ScopeType.COMPANY
    assignment.company_code = 7
    assignment.scope_key = build_scope_key(ScopeType.COMPANY, 7, None)
    assignment.valid_until = timezone.now() + timedelta(days=1)
    assignment.full_clean()
    assignment.save(
        update_fields=(
            "scope_type",
            "company_code",
            "scope_key",
            "valid_until",
        )
    )

    with pytest.raises(ValidationError, match="escopo e validade"):
        AssignSectorResponsibleService().execute(
            assign_command(
                actor,
                sector,
                responsible_user,
                scope_type=ScopeType.COMPANY,
                company_code=8,
            )
        )
    with pytest.raises(ValidationError, match="escopo e validade"):
        AssignSectorResponsibleService().execute(
            assign_command(
                actor,
                sector,
                responsible_user,
                scope_type=ScopeType.COMPANY,
                company_code=7,
                valid_until=timezone.now() + timedelta(days=2),
            )
        )


def test_identical_assignment_is_idempotent(
    actor: User,
    sector: ValidationSector,
    responsible_user: User,
) -> None:
    valid_from = timezone.now()
    command = assign_command(
        actor,
        sector,
        responsible_user,
        valid_from=valid_from,
    )

    first = AssignSectorResponsibleService().execute(command)
    second = AssignSectorResponsibleService().execute(command)

    assert second.pk == first.pk
    assert SectorResponsible.objects.count() == 1
    assert (
        SectorAuditEvent.objects.filter(event_type=SectorEventType.RESPONSIBLE_ASSIGNED).count()
        == 1
    )


def test_update_requires_current_version_and_audits_before_after(
    actor: User,
    sector: ValidationSector,
    responsible_user: User,
) -> None:
    responsibility = AssignSectorResponsibleService().execute(
        assign_command(actor, sector, responsible_user)
    )
    new_end = timezone.now() + timedelta(days=30)

    with pytest.raises(ValidationError, match="outra sessão"):
        UpdateSectorResponsibleService().execute(
            UpdateSectorResponsibleCommand(
                actor=actor,
                responsibility_id=responsibility.pk,
                expected_version=responsibility.version + 1,
                valid_from=responsibility.valid_from,
                valid_until=new_end,
                reason="Tentativa obsoleta.",
            )
        )

    updated = UpdateSectorResponsibleService().execute(
        UpdateSectorResponsibleCommand(
            actor=actor,
            responsibility_id=responsibility.pk,
            expected_version=responsibility.version,
            valid_from=responsibility.valid_from,
            valid_until=new_end,
            reason="Validade revisada.",
        )
    )
    assert updated.version == 2
    event = SectorAuditEvent.objects.get(event_type=SectorEventType.RESPONSIBLE_UPDATED)
    assert event.changes["before"]["valid_until"] is None
    assert event.changes["after"]["valid_until"] == new_end.isoformat()


def test_revoke_is_logical_audited_and_reactivation_reuses_row(
    actor: User,
    sector: ValidationSector,
    responsible_user: User,
) -> None:
    responsibility = AssignSectorResponsibleService().execute(
        assign_command(actor, sector, responsible_user)
    )
    revoked = RevokeSectorResponsibleService().execute(
        RevokeSectorResponsibleCommand(
            actor=actor,
            responsibility_id=responsibility.pk,
            expected_version=responsibility.version,
            reason="Responsável substituído.",
        )
    )

    assert not revoked.is_active
    assert revoked.version == 2
    assert revoked.revoked_by == actor
    assert SectorAuditEvent.objects.filter(event_type=SectorEventType.RESPONSIBLE_REVOKED).exists()

    reactivated = AssignSectorResponsibleService().execute(
        assign_command(
            actor,
            sector,
            responsible_user,
            valid_from=timezone.now() + timedelta(minutes=1),
        )
    )
    assert reactivated.pk == responsibility.pk
    assert reactivated.is_active
    assert reactivated.version == 3
    assert reactivated.revoked_at is None


def test_responsibility_cannot_be_deleted_or_bulk_updated(
    actor: User,
    sector: ValidationSector,
    responsible_user: User,
) -> None:
    responsibility = AssignSectorResponsibleService().execute(
        assign_command(actor, sector, responsible_user)
    )

    with pytest.raises(ValidationError, match="revogadas"):
        responsibility.delete()
    with pytest.raises(ValidationError, match="service auditado"):
        SectorResponsible.objects.update(is_active=False)
    with pytest.raises(ValidationError, match="revogadas"):
        SectorResponsible.objects.all().delete()


def test_audit_failure_rolls_back_assignment(
    actor: User,
    sector: ValidationSector,
    responsible_user: User,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fail_create(**kwargs: Any) -> None:
        raise IntegrityError("audit unavailable")

    monkeypatch.setattr(SectorAuditEvent.objects, "create", fail_create)

    with pytest.raises(IntegrityError, match="audit unavailable"):
        AssignSectorResponsibleService().execute(assign_command(actor, sector, responsible_user))

    assert not SectorResponsible.objects.exists()


def test_operational_authorization_requires_role_responsibility_and_scope(
    actor: User,
    sector: ValidationSector,
    responsible_user: User,
) -> None:
    AssignSectorResponsibleService().execute(
        assign_command(
            actor,
            sector,
            responsible_user,
            scope_type=ScopeType.COMPANY,
            company_code=7,
        )
    )

    assert has_sector_responsibility(
        responsible_user,
        sector.code,
        company_code=7,
    )
    assert not has_sector_responsibility(
        responsible_user,
        sector.code,
        company_code=8,
    )
    assert not has_sector_responsibility(actor, sector.code)

    role_assignment = RoleAssignment.objects.get(user=responsible_user)
    role_assignment.is_active = False
    role_assignment.revoked_by = actor
    role_assignment.revoked_at = timezone.now()
    role_assignment.full_clean()
    role_assignment.save(update_fields=("is_active", "revoked_by", "revoked_at"))
    assert not has_sector_responsibility(
        responsible_user,
        sector.code,
        company_code=7,
    )


@pytest.mark.parametrize(
    ("name", "kwargs", "method"),
    [
        ("sector-responsibilities-api:responsibility-list", {}, "get"),
        ("sector-responsibilities-api:responsibility-list", {}, "post"),
        ("sector-responsibilities-api:responsibility-candidates", {}, "get"),
        (
            "sector-responsibilities-api:responsibility-detail",
            {"responsibility_id": 1},
            "get",
        ),
        (
            "sector-responsibilities-api:responsibility-detail",
            {"responsibility_id": 1},
            "patch",
        ),
        (
            "sector-responsibilities-api:responsibility-revoke",
            {"responsibility_id": 1},
            "post",
        ),
    ],
)
def test_responsibility_api_rejects_anonymous(
    name: str,
    kwargs: dict[str, Any],
    method: str,
) -> None:
    response = getattr(Client(), method)(
        reverse(name, kwargs=kwargs),
        data={},
        content_type="application/json",
    )

    assert response.status_code == 401
    assert response.json()["code"] == "not_authenticated"


@pytest.mark.parametrize(
    ("name", "kwargs", "method"),
    [
        ("sector-responsibilities-api:responsibility-list", {}, "get"),
        ("sector-responsibilities-api:responsibility-list", {}, "post"),
        ("sector-responsibilities-api:responsibility-candidates", {}, "get"),
        (
            "sector-responsibilities-api:responsibility-detail",
            {"responsibility_id": 1},
            "get",
        ),
        (
            "sector-responsibilities-api:responsibility-detail",
            {"responsibility_id": 1},
            "patch",
        ),
        (
            "sector-responsibilities-api:responsibility-revoke",
            {"responsibility_id": 1},
            "post",
        ),
    ],
)
def test_responsibility_api_rejects_user_without_permission(
    plain_user: User,
    name: str,
    kwargs: dict[str, Any],
    method: str,
) -> None:
    client = Client()
    client.force_login(plain_user)

    response = getattr(client, method)(
        reverse(name, kwargs=kwargs),
        data={},
        content_type="application/json",
    )

    assert response.status_code == 403
    assert response.json()["code"] == "permission_denied"


def test_responsibility_api_assign_list_update_revoke_and_candidates(
    client_actor: Client,
    sector: ValidationSector,
    responsible_user: User,
    plain_user: User,
) -> None:
    valid_from = timezone.now()
    create_response = post_json(
        client_actor,
        "sector-responsibilities-api:responsibility-list",
        api_payload(sector, responsible_user, valid_from=valid_from),
    )
    assert create_response.status_code == 201
    created = create_response.json()
    assert created["sector"]["code"] == sector.code
    assert created["user"]["email"] == responsible_user.email
    assert created["scope_key"] == "*"
    assert created["is_effective"]

    list_response = client_actor.get(
        reverse("sector-responsibilities-api:responsibility-list"),
        {"sector": sector.pk, "limit": 200},
    )
    assert list_response.status_code == 200
    assert [item["id"] for item in list_response.json()["results"]] == [created["id"]]

    candidate_response = client_actor.get(
        reverse("sector-responsibilities-api:responsibility-candidates"),
        {"limit": 200},
    )
    candidate_ids = {item["id"] for item in candidate_response.json()["results"]}
    assert responsible_user.pk in candidate_ids
    assert plain_user.pk not in candidate_ids

    new_end = timezone.now() + timedelta(days=30)
    update_response = patch_json(
        client_actor,
        "sector-responsibilities-api:responsibility-detail",
        {
            "version": created["version"],
            "valid_from": created["valid_from"],
            "valid_until": new_end.isoformat(),
            "reason": "Validade revisada.",
        },
        responsibility_id=created["id"],
    )
    assert update_response.status_code == 200
    updated = update_response.json()
    assert updated["version"] == 2
    assert updated["valid_until"] == new_end.isoformat()

    revoke_response = post_json(
        client_actor,
        "sector-responsibilities-api:responsibility-revoke",
        {
            "version": updated["version"],
            "reason": "Responsável substituído.",
        },
        responsibility_id=created["id"],
    )
    assert revoke_response.status_code == 200
    assert not revoke_response.json()["is_active"]
    assert revoke_response.json()["version"] == 3


def test_responsibility_api_rejects_delete_surface(
    client_actor: Client,
    actor: User,
    sector: ValidationSector,
    responsible_user: User,
) -> None:
    responsibility = AssignSectorResponsibleService().execute(
        assign_command(actor, sector, responsible_user)
    )

    response = client_actor.delete(
        reverse(
            "sector-responsibilities-api:responsibility-detail",
            kwargs={"responsibility_id": responsibility.pk},
        )
    )

    assert response.status_code == 405
    assert SectorResponsible.objects.filter(pk=responsibility.pk).exists()
