"""Sector-responsibility aggregate, derived authorization and API contract."""

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

from apps.accounts.models import ScopeType, User
from apps.sectors.authorization import has_sector_responsibility
from apps.sectors.models import (
    SectorAuditEvent,
    SectorEventType,
    SectorResponsible,
    ValidationSector,
)
from apps.sectors.services import (
    CreateSectorCommand,
    CreateSectorService,
    SectorResponsibleValue,
    SectorScopeValue,
    UpdateSectorCommand,
    UpdateSectorService,
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
def second_user() -> User:
    return User.objects.create_user(
        username="responsaveis.segundo",
        email="responsaveis.segundo@example.invalid",
        password=PASSWORD,
        first_name="Segundo",
        last_name="Responsável",
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
    return SectorScopeValue(scope_type, company_code, branch_code)


def responsible(
    user: User,
    *,
    valid_from: Any | None = None,
    valid_until: Any | None = None,
) -> SectorResponsibleValue:
    return SectorResponsibleValue(
        user_id=user.pk,
        valid_from=valid_from,
        valid_until=valid_until,
    )


def create_command(
    actor: User,
    *,
    scopes: tuple[SectorScopeValue, ...] = (SectorScopeValue(ScopeType.GLOBAL),),
    responsibles: tuple[SectorResponsibleValue, ...] = (),
) -> CreateSectorCommand:
    return CreateSectorCommand(
        actor=actor,
        name="Tecnologia",
        description="Valida acessos e equipamentos.",
        default_due_hours=24,
        blocks_process=True,
        allows_amount=False,
        requires_evidence=False,
        escalation_sector_id=None,
        scopes=scopes,
        responsibles=responsibles,
    )


def update_command(
    actor: User,
    sector: ValidationSector,
    *,
    scopes: tuple[SectorScopeValue, ...],
    responsibles: tuple[SectorResponsibleValue, ...],
) -> UpdateSectorCommand:
    return UpdateSectorCommand(
        actor=actor,
        sector_id=sector.pk,
        expected_version=sector.version,
        name=sector.name,
        description=sector.description,
        is_active=sector.is_active,
        default_due_hours=sector.default_due_hours,
        blocks_process=sector.blocks_process,
        allows_amount=sector.allows_amount,
        requires_evidence=sector.requires_evidence,
        escalation_sector_id=sector.escalation_sector_id,
        scopes=scopes,
        responsibles=responsibles,
    )


def api_payload(*users: User) -> dict[str, Any]:
    return {
        "name": "Tecnologia",
        "description": "Valida acessos e equipamentos.",
        "default_due_hours": 24,
        "blocks_process": True,
        "allows_amount": False,
        "requires_evidence": False,
        "escalation_sector_id": None,
        "scopes": [
            {
                "scope_type": ScopeType.COMPANY,
                "company_code": 7,
                "branch_code": None,
            }
        ],
        "responsibles": [{"user_id": user.pk, "valid_until": None} for user in users],
    }


def post_json(client: Client, name: str, payload: dict[str, Any]) -> Any:
    return client.post(
        reverse(name),
        data=payload,
        content_type="application/json",
    )


def test_sector_create_designates_multiple_users_without_assignable_role(
    actor: User,
    plain_user: User,
    second_user: User,
) -> None:
    sector = CreateSectorService().execute(
        create_command(
            actor,
            scopes=(scope(ScopeType.COMPANY, 7),),
            responsibles=(responsible(plain_user), responsible(second_user)),
        )
    )

    links = list(sector.responsibles.select_related("user").order_by("user_id"))
    assert [link.user_id for link in links] == sorted([plain_user.pk, second_user.pk])
    assert all(link.is_active for link in links)
    assert not plain_user.role_assignments.exists()
    sector_code = sector.code
    assert sector_code is not None
    assert has_sector_responsibility(plain_user, sector_code, company_code=7)
    assert not has_sector_responsibility(plain_user, sector_code, company_code=8)
    assert (
        SectorAuditEvent.objects.filter(event_type=SectorEventType.RESPONSIBLE_ASSIGNED).count()
        == 2
    )


def test_future_link_is_scheduled_but_not_effective(
    actor: User,
    plain_user: User,
) -> None:
    future = timezone.now() + timedelta(days=1)
    sector = CreateSectorService().execute(
        create_command(
            actor,
            responsibles=(responsible(plain_user, valid_from=future),),
        )
    )

    sector_code = sector.code
    assert sector_code is not None
    assert not has_sector_responsibility(plain_user, sector_code)
    assert has_sector_responsibility(
        plain_user,
        sector_code,
        at=future + timedelta(seconds=1),
    )


def test_update_synchronizes_validity_and_logically_revokes_omitted_link(
    actor: User,
    plain_user: User,
    second_user: User,
) -> None:
    sector = CreateSectorService().execute(
        create_command(actor, responsibles=(responsible(plain_user),))
    )
    first_link = SectorResponsible.objects.get(sector=sector, user=plain_user)
    end = timezone.now() + timedelta(days=30)

    updated = UpdateSectorService().execute(
        update_command(
            actor,
            sector,
            scopes=(scope(),),
            responsibles=(responsible(second_user, valid_until=end),),
        )
    )

    first_link.refresh_from_db()
    second_link = SectorResponsible.objects.get(sector=sector, user=second_user)
    assert updated.version == 2
    assert not first_link.is_active
    assert first_link.revoked_by == actor
    assert second_link.valid_until == end
    assert SectorAuditEvent.objects.filter(event_type=SectorEventType.RESPONSIBLE_REVOKED).exists()


def test_duplicate_or_inactive_responsible_rolls_back_aggregate(
    actor: User,
    plain_user: User,
) -> None:
    with pytest.raises(ValidationError, match="mais de uma vez"):
        CreateSectorService().execute(
            create_command(
                actor,
                responsibles=(responsible(plain_user), responsible(plain_user)),
            )
        )
    assert not ValidationSector.objects.exists()

    plain_user.is_active = False
    plain_user.save(update_fields=("is_active",))
    with pytest.raises(ValidationError, match="precisa estar ativo"):
        CreateSectorService().execute(
            create_command(actor, responsibles=(responsible(plain_user),))
        )
    assert not ValidationSector.objects.exists()
    assert not SectorResponsible.objects.exists()


def test_aggregate_requires_manage_sectors_permission(
    plain_user: User,
) -> None:
    with pytest.raises(PermissionDenied):
        CreateSectorService().execute(create_command(plain_user))

    permission = Permission.objects.get(
        content_type__app_label="sectors",
        codename="manage_sectors",
    )
    plain_user.user_permissions.add(permission)
    sector = CreateSectorService().execute(create_command(plain_user))
    assert sector.pk is not None


def test_audit_failure_rolls_back_responsibility_and_sector(
    actor: User,
    plain_user: User,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fail_create(**kwargs: Any) -> None:
        raise IntegrityError("audit unavailable")

    monkeypatch.setattr(SectorAuditEvent.objects, "create", fail_create)
    with pytest.raises(IntegrityError, match="audit unavailable"):
        CreateSectorService().execute(
            create_command(actor, responsibles=(responsible(plain_user),))
        )

    assert not ValidationSector.objects.exists()
    assert not SectorResponsible.objects.exists()


def test_responsibility_cannot_be_deleted_or_bulk_updated(
    actor: User,
    plain_user: User,
) -> None:
    sector = CreateSectorService().execute(
        create_command(actor, responsibles=(responsible(plain_user),))
    )
    link = SectorResponsible.objects.get(sector=sector, user=plain_user)

    with pytest.raises(ValidationError, match="revogadas"):
        link.delete()
    with pytest.raises(ValidationError, match="service auditado"):
        SectorResponsible.objects.update(is_active=False)
    with pytest.raises(ValidationError, match="revogadas"):
        SectorResponsible.objects.all().delete()


@pytest.mark.parametrize(
    ("name", "method"),
    [
        ("sectors-api:sector-list", "post"),
        ("sectors-api:responsible-candidates", "get"),
    ],
)
def test_responsibility_aggregate_api_rejects_anonymous(
    name: str,
    method: str,
) -> None:
    response = getattr(Client(), method)(
        reverse(name),
        data={},
        content_type="application/json",
    )
    assert response.status_code == 401


def test_sector_api_persists_nested_links_and_exposes_indicators(
    client_actor: Client,
    plain_user: User,
    second_user: User,
) -> None:
    response = post_json(
        client_actor,
        "sectors-api:sector-list",
        api_payload(plain_user, second_user),
    )

    assert response.status_code == 201
    created = response.json()
    assert len(created["responsibles"]) == 2
    assert created["effective_responsible_count"] == 2
    assert created["has_effective_responsible"]
    assert created["responsibles"][0]["inherited_scopes"][0]["scope_key"] == "E:7"

    list_response = client_actor.get(reverse("sectors-api:sector-list"))
    assert list_response.json()["results"][0]["has_effective_responsible"]

    candidate_response = client_actor.get(
        reverse("sectors-api:responsible-candidates"),
        {"limit": 200},
    )
    candidate_ids = {item["id"] for item in candidate_response.json()["results"]}
    assert {plain_user.pk, second_user.pk} <= candidate_ids

    update_payload = api_payload(plain_user)
    update_payload.update(
        {
            "version": created["version"],
            "is_active": True,
        }
    )
    update_response = client_actor.patch(
        reverse(
            "sectors-api:sector-detail",
            kwargs={"sector_id": created["id"]},
        ),
        data=update_payload,
        content_type="application/json",
    )
    assert update_response.status_code == 200
    assert update_response.json()["effective_responsible_count"] == 1
    assert not SectorResponsible.objects.get(
        sector_id=created["id"],
        user=second_user,
    ).is_active


def test_user_list_detail_and_auth_context_expose_derived_sector_link(
    actor: User,
    client_actor: Client,
    plain_user: User,
) -> None:
    sector = CreateSectorService().execute(
        create_command(
            actor,
            scopes=(scope(ScopeType.BRANCH, 7, 2),),
            responsibles=(responsible(plain_user),),
        )
    )

    user_list = client_actor.get(
        reverse("accounts-api:user-list"),
        {"q": plain_user.username},
    ).json()["results"][0]
    assert user_list["sector_link_count"] == 1
    assert user_list["effective_sector_count"] == 1

    detail = client_actor.get(
        reverse(
            "accounts-api:user-detail",
            kwargs={"user_id": plain_user.pk},
        )
    ).json()
    assert detail["sector_responsibilities"][0]["sector"]["code"] == sector.code
    assert detail["sector_responsibilities"][0]["inherited_scopes"][0]["scope_key"] == "F:7:2"

    responsible_client = Client()
    responsible_client.force_login(plain_user)
    context = responsible_client.get(reverse("auth-api:context")).json()
    assert "RESPONSAVEL_SETOR" in context["roles"]
    derived = next(
        item for item in context["scopes"]["assignments"] if item["role"] == "RESPONSAVEL_SETOR"
    )
    assert derived["source"] == "SECTOR_RESPONSIBILITY"
    assert derived["sector"] == sector.code
    assert derived["company_code"] == 7
    assert derived["branch_code"] == 2


def test_removed_standalone_responsibility_endpoint_returns_404(
    client_actor: Client,
) -> None:
    response = client_actor.get("/api/v1/sector-responsibilities/")
    assert response.status_code == 404
