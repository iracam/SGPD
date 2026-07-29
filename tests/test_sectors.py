"""Sector configuration services, authorization, audit and API contract."""

from __future__ import annotations

from typing import Any

import pytest
from django.contrib.auth.models import Permission
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import IntegrityError
from django.test import Client
from django.urls import reverse

from apps.accounts.models import Role, RoleAssignment, ScopeType, User, build_scope_key
from apps.sectors.models import (
    SectorAuditEvent,
    SectorEventType,
    SectorScope,
    ValidationSector,
)
from apps.sectors.services import (
    CreateSectorCommand,
    CreateSectorService,
    SectorScopeValue,
    UpdateSectorCommand,
    UpdateSectorService,
)

pytestmark = pytest.mark.django_db

PASSWORD = "Sectors-test-only!2026"


@pytest.fixture
def actor() -> User:
    return User.objects.create_superuser(
        username="setores.admin",
        email="setores.admin@example.invalid",
        password=PASSWORD,
        first_name="Setores",
        last_name="Admin",
    )


@pytest.fixture
def plain_user() -> User:
    return User.objects.create_user(
        username="setores.comum",
        email="setores.comum@example.invalid",
        password=PASSWORD,
        first_name="Setores",
        last_name="Comum",
    )


@pytest.fixture
def client_actor(actor: User) -> Client:
    client = Client()
    client.force_login(actor)
    return client


def scope(
    scope_type: ScopeType = ScopeType.GLOBAL,
    company_code: int | None = None,
    branch_code: int | None = None,
) -> SectorScopeValue:
    return SectorScopeValue(
        scope_type=scope_type,
        company_code=company_code,
        branch_code=branch_code,
    )


def create_command(
    actor: User,
    *,
    code: str = "patrimonio",
    name: str = "Patrimônio",
    scopes: tuple[SectorScopeValue, ...] | None = None,
    escalation_sector_id: int | None = None,
) -> CreateSectorCommand:
    return CreateSectorCommand(
        actor=actor,
        code=code,
        name=name,
        description="Valida bens e equipamentos.",
        default_due_hours=24,
        blocks_process=True,
        allows_amount=True,
        requires_evidence=False,
        escalation_sector_id=escalation_sector_id,
        scopes=scopes or (scope(),),
        reason="Configuração inicial homologada.",
    )


def update_command(
    actor: User,
    sector: ValidationSector,
    **overrides: Any,
) -> UpdateSectorCommand:
    values: dict[str, Any] = {
        "actor": actor,
        "sector_id": sector.pk,
        "expected_version": sector.version,
        "name": sector.name,
        "description": sector.description,
        "is_active": sector.is_active,
        "default_due_hours": sector.default_due_hours,
        "blocks_process": sector.blocks_process,
        "allows_amount": sector.allows_amount,
        "requires_evidence": sector.requires_evidence,
        "escalation_sector_id": sector.escalation_sector_id,
        "scopes": (scope(),),
        "reason": "Revisão funcional do setor.",
    }
    values.update(overrides)
    return UpdateSectorCommand(**values)


def api_payload(*, code: str = "patrimonio") -> dict[str, Any]:
    return {
        "code": code,
        "name": "Patrimônio",
        "description": "Valida bens e equipamentos.",
        "default_due_hours": 24,
        "blocks_process": True,
        "allows_amount": True,
        "requires_evidence": False,
        "escalation_sector_id": None,
        "scopes": [
            {
                "scope_type": ScopeType.COMPANY,
                "company_code": 7,
                "branch_code": None,
            }
        ],
        "reason": "Configuração inicial homologada.",
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


def test_create_sector_normalizes_scopes_and_audits(actor: User) -> None:
    sector = CreateSectorService().execute(
        create_command(
            actor,
            scopes=(
                scope(ScopeType.BRANCH, 7, 2),
                scope(ScopeType.COMPANY, 8),
            ),
        )
    )

    assert sector.code == "PATRIMONIO"
    assert sector.version == 1
    assert list(sector.scopes.values_list("scope_key", flat=True)) == ["E:8", "F:7:2"]
    event = SectorAuditEvent.objects.get()
    assert event.event_type == SectorEventType.CREATED
    assert event.actor == actor
    assert event.changes["after"]["scopes"] == [
        {
            "scope_type": ScopeType.COMPANY,
            "company_code": 8,
            "branch_code": None,
            "scope_key": "E:8",
        },
        {
            "scope_type": ScopeType.BRANCH,
            "company_code": 7,
            "branch_code": 2,
            "scope_key": "F:7:2",
        },
    ]


def test_sector_service_requires_global_manage_permission(plain_user: User) -> None:
    permission = Permission.objects.get(
        content_type__app_label="sectors",
        codename="manage_sectors",
    )
    role = Role.objects.create(code="RESPONSAVEL_SETOR", name="Responsável de setor")
    role.permissions.add(permission)
    RoleAssignment.objects.create(
        user=plain_user,
        role=role,
        scope_type=ScopeType.COMPANY,
        company_code=7,
        scope_key=build_scope_key(ScopeType.COMPANY, 7, None),
        assigned_by=plain_user,
    )

    with pytest.raises(PermissionDenied):
        CreateSectorService().execute(create_command(plain_user))

    plain_user.user_permissions.add(permission)
    sector = CreateSectorService().execute(
        create_command(plain_user, code="seguranca", name="Segurança")
    )
    assert sector.pk is not None


@pytest.mark.parametrize(
    ("scopes", "message"),
    [
        ((), "ao menos um escopo"),
        ((scope(), scope(ScopeType.COMPANY, 7)), "global não pode"),
        (
            (scope(ScopeType.COMPANY, 7), scope(ScopeType.BRANCH, 7, 1)),
            "toda a empresa",
        ),
        ((scope(ScopeType.COMPANY, 7), scope(ScopeType.COMPANY, 7)), "mais de uma vez"),
    ],
)
def test_create_sector_rejects_ambiguous_scope_combinations(
    actor: User,
    scopes: tuple[SectorScopeValue, ...],
    message: str,
) -> None:
    command = create_command(actor)
    command = CreateSectorCommand(
        **{
            **{field: getattr(command, field) for field in command.__dataclass_fields__},
            "scopes": scopes,
        }
    )

    with pytest.raises(ValidationError, match=message):
        CreateSectorService().execute(command)

    assert not ValidationSector.objects.exists()
    assert not SectorAuditEvent.objects.exists()


def test_update_sector_replaces_scopes_and_records_before_after(actor: User) -> None:
    sector = CreateSectorService().execute(create_command(actor))

    updated = UpdateSectorService().execute(
        update_command(
            actor,
            sector,
            name="Patrimônio corporativo",
            default_due_hours=48,
            scopes=(scope(ScopeType.BRANCH, 7, 3),),
        )
    )

    assert updated.version == 2
    assert updated.name == "Patrimônio corporativo"
    assert list(updated.scopes.values_list("scope_key", flat=True)) == ["F:7:3"]
    event = SectorAuditEvent.objects.filter(event_type=SectorEventType.UPDATED).get()
    assert event.changes["before"]["scopes"][0]["scope_key"] == "*"
    assert event.changes["after"]["scopes"][0]["scope_key"] == "F:7:3"


def test_update_sector_rejects_stale_version_without_partial_change(actor: User) -> None:
    sector = CreateSectorService().execute(create_command(actor))

    with pytest.raises(ValidationError, match="outra sessão"):
        UpdateSectorService().execute(
            update_command(
                actor,
                sector,
                expected_version=sector.version + 1,
                name="Não deve persistir",
            )
        )

    sector.refresh_from_db()
    assert sector.name == "Patrimônio"
    assert SectorAuditEvent.objects.count() == 1


def test_deactivation_is_audited_and_physical_delete_is_blocked(actor: User) -> None:
    sector = CreateSectorService().execute(create_command(actor))

    updated = UpdateSectorService().execute(update_command(actor, sector, is_active=False))

    assert not updated.is_active
    assert SectorAuditEvent.objects.filter(event_type=SectorEventType.DEACTIVATED).exists()
    with pytest.raises(ValidationError, match="inativados"):
        updated.delete()
    with pytest.raises(ValidationError, match="inativados"):
        ValidationSector.objects.all().delete()


def test_cannot_deactivate_an_active_escalation_target(actor: User) -> None:
    escalation = CreateSectorService().execute(
        create_command(actor, code="coordenacao", name="Coordenação")
    )
    CreateSectorService().execute(
        create_command(
            actor,
            code="patrimonio",
            name="Patrimônio",
            escalation_sector_id=escalation.pk,
        )
    )

    with pytest.raises(ValidationError, match="destino de escalada"):
        UpdateSectorService().execute(update_command(actor, escalation, is_active=False))


def test_escalation_cycle_is_rejected(actor: User) -> None:
    first = CreateSectorService().execute(create_command(actor, code="primeiro", name="Primeiro"))
    second = CreateSectorService().execute(
        create_command(
            actor,
            code="segundo",
            name="Segundo",
            escalation_sector_id=first.pk,
        )
    )

    with pytest.raises(ValidationError, match="ciclo"):
        UpdateSectorService().execute(
            update_command(
                actor,
                first,
                escalation_sector_id=second.pk,
            )
        )


def test_audit_failure_rolls_back_sector_creation(
    actor: User,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fail_create(**kwargs: Any) -> None:
        raise IntegrityError("audit unavailable")

    monkeypatch.setattr(SectorAuditEvent.objects, "create", fail_create)

    with pytest.raises(IntegrityError, match="audit unavailable"):
        CreateSectorService().execute(create_command(actor))

    assert not ValidationSector.objects.exists()
    assert not SectorScope.objects.exists()


def test_sector_audit_is_append_only(actor: User) -> None:
    CreateSectorService().execute(create_command(actor))
    event = SectorAuditEvent.objects.get()

    event.reason = "Tentativa de alteração."
    with pytest.raises(ValidationError, match="imutáveis"):
        event.save()
    with pytest.raises(ValidationError, match="imutáveis"):
        SectorAuditEvent.objects.update(reason="Tentativa em lote.")
    with pytest.raises(ValidationError, match="não podem"):
        SectorAuditEvent.objects.all().delete()


@pytest.mark.parametrize(
    ("name", "kwargs", "method"),
    [
        ("sectors-api:sector-list", {}, "get"),
        ("sectors-api:sector-list", {}, "post"),
        ("sectors-api:sector-detail", {"sector_id": 1}, "get"),
        ("sectors-api:sector-detail", {"sector_id": 1}, "patch"),
    ],
)
def test_sector_api_rejects_anonymous(
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
        ("sectors-api:sector-list", {}, "get"),
        ("sectors-api:sector-list", {}, "post"),
        ("sectors-api:sector-detail", {"sector_id": 1}, "get"),
        ("sectors-api:sector-detail", {"sector_id": 1}, "patch"),
    ],
)
def test_sector_api_rejects_user_without_permission(
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


def test_sector_api_create_list_detail_and_update(client_actor: Client) -> None:
    create_response = post_json(
        client_actor,
        "sectors-api:sector-list",
        api_payload(),
    )

    assert create_response.status_code == 201
    created = create_response.json()
    assert created["code"] == "PATRIMONIO"
    assert created["scopes"][0]["scope_key"] == "E:7"

    query_params: dict[str, str | int] = {"q": "patri", "limit": 200}
    list_response = client_actor.get(
        reverse("sectors-api:sector-list"),
        query_params,
    )
    assert list_response.status_code == 200
    assert [item["id"] for item in list_response.json()["results"]] == [created["id"]]

    detail_response = client_actor.get(
        reverse("sectors-api:sector-detail", kwargs={"sector_id": created["id"]})
    )
    assert detail_response.status_code == 200

    update_payload = {
        **api_payload(),
        "version": created["version"],
        "name": "Patrimônio atualizado",
        "is_active": False,
        "scopes": [
            {
                "scope_type": ScopeType.BRANCH,
                "company_code": 7,
                "branch_code": 2,
            }
        ],
        "reason": "Atualização homologada.",
    }
    update_payload.pop("code")
    update_response = patch_json(
        client_actor,
        "sectors-api:sector-detail",
        update_payload,
        sector_id=created["id"],
    )

    assert update_response.status_code == 200
    updated = update_response.json()
    assert updated["name"] == "Patrimônio atualizado"
    assert not updated["is_active"]
    assert updated["version"] == 2
    assert updated["scopes"][0]["scope_key"] == "F:7:2"


def test_sector_api_returns_field_errors_for_invalid_scope(client_actor: Client) -> None:
    payload = api_payload()
    payload["scopes"] = [
        {
            "scope_type": ScopeType.BRANCH,
            "company_code": 7,
            "branch_code": None,
        }
    ]

    response = post_json(client_actor, "sectors-api:sector-list", payload)

    assert response.status_code == 400
    assert response.json()["code"] == "validation_error"
    assert "scopes" in response.json()["details"]
    assert not ValidationSector.objects.exists()


def test_sector_api_rejects_method_without_delete_surface(
    actor: User,
    client_actor: Client,
) -> None:
    sector = CreateSectorService().execute(create_command(actor))

    response = client_actor.delete(
        reverse("sectors-api:sector-detail", kwargs={"sector_id": sector.pk})
    )

    assert response.status_code == 405
    assert ValidationSector.objects.filter(pk=sector.pk).exists()
