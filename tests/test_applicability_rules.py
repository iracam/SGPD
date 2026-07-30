"""Regras de aplicabilidade: sugestão por união, validade, autoria e API."""

from __future__ import annotations

from datetime import date, timedelta
from typing import Any

import pytest
from django.contrib.auth.models import Permission
from django.core.exceptions import PermissionDenied, ValidationError
from django.test import Client
from django.urls import reverse
from django.utils import timezone

from apps.accounts.models import (
    PEOPLE_DEPARTMENT_ROLE_CODE,
    Role,
    RoleAssignment,
    ScopeType,
    User,
    build_scope_key,
)
from apps.offboarding.models import EmployeeSnapshot, OffboardingProcess
from apps.templates_engine.models import (
    GroupApplicabilityRule,
    ValidationGroup,
    ValidationGroupVersion,
    WorkflowConfigurationAuditEvent,
    WorkflowConfigurationEventType,
)
from apps.templates_engine.services import (
    ApplicabilityRuleValue,
    CreateApplicabilityRuleCommand,
    CreateApplicabilityRuleService,
    UpdateApplicabilityRuleCommand,
    UpdateApplicabilityRuleService,
    resolve_applicable_group_versions,
)
from tests.test_offboarding_start import (
    create_published_group,
    create_published_template,
    create_sector,
)

pytestmark = pytest.mark.django_db

PASSWORD = "Applicability-rule!2026"

SNAPSHOT = {
    "company_code": 1,
    "branch_code": 2,
    "employee_type_code": 1,
    "job_structure_code": 1,
    "job_code": "DEV",
    "cost_center_code": "100",
}


@pytest.fixture
def actor() -> User:
    role = Role.objects.create(
        code=PEOPLE_DEPARTMENT_ROLE_CODE,
        name="Departamento Pessoal",
    )
    user = User.objects.create_user(
        username="dp.aplicabilidade",
        email="dp.aplicabilidade@example.invalid",
        password=PASSWORD,
        first_name="DP",
        last_name="Aplicabilidade",
    )
    RoleAssignment.objects.create(
        user=user,
        role=role,
        scope_type=ScopeType.GLOBAL,
        scope_key=build_scope_key(ScopeType.GLOBAL, None, None),
        valid_from=timezone.now() - timedelta(days=1),
        assigned_by=user,
    )
    user.user_permissions.add(
        Permission.objects.get(
            content_type__app_label="templates_engine",
            codename="manage_workflow_configuration",
        )
    )
    return user


@pytest.fixture
def plain_user() -> User:
    return User.objects.create_user(
        username="sem.aplicabilidade",
        email="sem.aplicabilidade@example.invalid",
        password=PASSWORD,
        first_name="Sem",
        last_name="Permissão",
    )


@pytest.fixture
def process(actor: User) -> OffboardingProcess:
    row = OffboardingProcess.objects.create(
        company_code=1,
        branch_code=2,
        employee_type_code=1,
        employee_registration=321,
        active_employee_key="1:2:1:321",
        opened_by=actor,
        planned_termination_date=date(2026, 8, 15),
        due_date=date(2026, 8, 14),
        reason="Reorganização.",
        priority="Alta",
    )
    EmployeeSnapshot.objects.create(
        process=row,
        company_code=1,
        branch_code=2,
        branch_legal_name="Empresa",
        employee_type_code=1,
        employee_type_description="Empregado",
        registration=321,
        employee_name="Pessoa",
        admission_date=date(2020, 1, 2),
        leave_code=1,
        leave_description="Trabalhando",
        job_structure_code=1,
        job_code="DEV",
        job_description="Desenvolvedor",
        cost_center_code="100",
        source_queried_at=timezone.now(),
    )
    return row


def published_group(actor: User, *, code: str = "PADRAO") -> ValidationGroupVersion:
    sector = create_sector(actor, code=f"SETOR_{code}")
    template = create_published_template(actor, sector)
    return create_published_group(actor, sector, template, code=code)


def rule_value(group_id: int, **overrides: Any) -> ApplicabilityRuleValue:
    base: dict[str, Any] = {
        "name": "Regra padrão",
        "priority": 100,
        "group_id": group_id,
        "company_code": None,
        "branch_code": None,
        "employee_type_code": None,
        "job_structure_code": None,
        "job_code": None,
        "cost_center_code": None,
        "is_active": True,
        "valid_from": None,
        "valid_to": None,
    }
    base.update(overrides)
    return ApplicabilityRuleValue(**base)


def create_rule(actor: User, group_id: int, **overrides: Any) -> GroupApplicabilityRule:
    return CreateApplicabilityRuleService().execute(
        CreateApplicabilityRuleCommand(actor=actor, value=rule_value(group_id, **overrides))
    )


def suggest(**overrides: Any) -> tuple[Any, ...]:
    payload: dict[str, Any] = dict(SNAPSHOT)
    payload.update(overrides)
    payload.setdefault("reference_date", timezone.localdate())
    return resolve_applicable_group_versions(**payload)


def test_rule_is_created_and_audited(actor: User) -> None:
    version = published_group(actor)

    rule = create_rule(actor, version.group_id, name="  Todos os desligamentos  ", company_code=1)

    assert rule.name == "Todos os desligamentos"
    assert rule.priority == 100
    assert rule.version == 1
    event = WorkflowConfigurationAuditEvent.objects.get(
        entity_type="GROUP_APPLICABILITY_RULE",
        entity_id=rule.pk,
    )
    assert event.event_type == WorkflowConfigurationEventType.RULE_CREATED
    assert event.actor_id == actor.pk
    assert event.data["company_code"] == 1
    assert event.data["group_id"] == version.group_id


def test_rule_service_requires_configuration_permission(actor: User, plain_user: User) -> None:
    version = published_group(actor)

    with pytest.raises(PermissionDenied):
        create_rule(plain_user, version.group_id)

    assert not GroupApplicabilityRule.objects.exists()


def test_rule_requires_active_group_with_published_version(actor: User) -> None:
    version = published_group(actor)
    unpublished = ValidationGroup.objects.create(name="Sem versão publicada")

    with pytest.raises(ValidationError) as unpublished_error:
        create_rule(actor, unpublished.pk)
    assert "group_id" in unpublished_error.value.message_dict

    group = ValidationGroup.objects.get(pk=version.group_id)
    group.is_active = False
    group.save(update_fields=("is_active",))
    with pytest.raises(ValidationError) as inactive_error:
        create_rule(actor, group.pk)
    assert "group_id" in inactive_error.value.message_dict

    with pytest.raises(ValidationError):
        create_rule(actor, 9_999_999)


def test_rule_rejects_branch_without_company_and_inverted_window(actor: User) -> None:
    version = published_group(actor)

    with pytest.raises(ValidationError) as branch_error:
        create_rule(actor, version.group_id, branch_code=2)
    assert "branch_code" in branch_error.value.message_dict

    with pytest.raises(ValidationError) as window_error:
        create_rule(
            actor,
            version.group_id,
            valid_from=date(2026, 5, 10),
            valid_to=date(2026, 5, 1),
        )
    assert "valid_to" in window_error.value.message_dict

    with pytest.raises(ValidationError):
        create_rule(actor, version.group_id, name="   ")

    assert not GroupApplicabilityRule.objects.exists()


def test_wildcard_rule_matches_every_snapshot(actor: User) -> None:
    version = published_group(actor)
    create_rule(actor, version.group_id, name="Sempre")

    matches = suggest()

    assert [match.group_version_id for match in matches] == [version.pk]
    assert matches[0].rule_name == "Sempre"

    other = suggest(company_code=9, branch_code=9, job_code="OUTRO", cost_center_code="999")
    assert [match.group_version_id for match in other] == [version.pk]


def test_every_field_must_match_when_the_rule_fills_it(actor: User) -> None:
    version = published_group(actor)
    create_rule(
        actor,
        version.group_id,
        company_code=1,
        branch_code=2,
        employee_type_code=1,
        job_structure_code=1,
        job_code="DEV",
        cost_center_code="100",
    )

    assert len(suggest()) == 1
    for field, divergent in (
        ("company_code", 7),
        ("branch_code", 7),
        ("employee_type_code", 7),
        ("job_structure_code", 7),
        ("job_code", "QA"),
        ("cost_center_code", "999"),
    ):
        assert suggest(**{field: divergent}) == (), field


def test_union_suggests_every_matching_group_and_priority_only_orders(actor: User) -> None:
    general = published_group(actor, code="GERAL")
    managers = published_group(actor, code="GESTORES")
    create_rule(actor, general.group_id, name="Padrão", priority=10, company_code=1)
    create_rule(actor, managers.group_id, name="Gestores", priority=90, job_code="DEV")

    matches = suggest()

    assert [match.rule_name for match in matches] == ["Gestores", "Padrão"]
    assert {match.group_version_id for match in matches} == {general.pk, managers.pk}


def test_repeated_rules_for_the_same_group_are_deduplicated(actor: User) -> None:
    version = published_group(actor)
    create_rule(actor, version.group_id, name="Por empresa", priority=50, company_code=1)
    create_rule(actor, version.group_id, name="Por cargo", priority=10, job_code="DEV")

    matches = suggest()

    assert [match.rule_name for match in matches] == ["Por empresa"]
    assert [match.group_version_id for match in matches] == [version.pk]


def test_inactive_rule_and_closed_window_are_ignored(actor: User) -> None:
    version = published_group(actor)
    today = timezone.localdate()
    create_rule(actor, version.group_id, name="Inativa", is_active=False)
    create_rule(
        actor,
        version.group_id,
        name="Encerrada",
        valid_to=today - timedelta(days=1),
    )
    create_rule(
        actor,
        version.group_id,
        name="Futura",
        valid_from=today + timedelta(days=1),
    )

    assert suggest() == ()

    create_rule(
        actor,
        version.group_id,
        name="Vigente",
        valid_from=today,
        valid_to=today,
    )
    assert [match.rule_name for match in suggest()] == ["Vigente"]


def test_suggestion_skips_group_deactivated_after_the_rule(actor: User) -> None:
    version = published_group(actor)
    create_rule(actor, version.group_id)

    group = ValidationGroup.objects.get(pk=version.group_id)
    group.is_active = False
    group.save(update_fields=("is_active",))

    assert suggest() == ()


def test_rule_update_rejects_stale_version_and_is_audited(actor: User) -> None:
    version = published_group(actor)
    rule = create_rule(actor, version.group_id, name="Original", company_code=1)

    with pytest.raises(ValidationError):
        UpdateApplicabilityRuleService().execute(
            UpdateApplicabilityRuleCommand(
                actor=actor,
                rule_id=rule.pk,
                expected_version=rule.version + 1,
                value=rule_value(version.group_id, name="Concorrente"),
            )
        )

    updated = UpdateApplicabilityRuleService().execute(
        UpdateApplicabilityRuleCommand(
            actor=actor,
            rule_id=rule.pk,
            expected_version=rule.version,
            value=rule_value(version.group_id, name="Corrigida", is_active=False),
        )
    )

    assert updated.name == "Corrigida"
    assert updated.is_active is False
    assert updated.version == 2
    event = WorkflowConfigurationAuditEvent.objects.get(
        event_type=WorkflowConfigurationEventType.RULE_UPDATED,
        entity_id=rule.pk,
    )
    assert event.data["previous"]["name"] == "Original"
    assert event.data["current"]["name"] == "Corrigida"
    assert event.data["previous"]["company_code"] == 1
    assert event.data["current"]["company_code"] is None
    assert suggest() == ()


def test_rule_update_rolls_back_when_audit_fails(actor: User, monkeypatch: Any) -> None:
    version = published_group(actor)
    rule = create_rule(actor, version.group_id, name="Original")

    def fail(*args: Any, **kwargs: Any) -> Any:
        raise RuntimeError("auditoria indisponível")

    monkeypatch.setattr(WorkflowConfigurationAuditEvent.objects, "create", fail)

    with pytest.raises(RuntimeError):
        UpdateApplicabilityRuleService().execute(
            UpdateApplicabilityRuleCommand(
                actor=actor,
                rule_id=rule.pk,
                expected_version=rule.version,
                value=rule_value(version.group_id, name="Perdida"),
            )
        )

    rule.refresh_from_db()
    assert rule.name == "Original"
    assert rule.version == 1


def test_rule_cannot_be_deleted(actor: User) -> None:
    version = published_group(actor)
    rule = create_rule(actor, version.group_id)

    with pytest.raises(ValidationError):
        rule.delete()

    assert GroupApplicabilityRule.objects.filter(pk=rule.pk).exists()


def test_draft_exposes_suggestion_limited_to_available_groups(
    actor: User,
    process: OffboardingProcess,
) -> None:
    available = published_group(actor, code="DISPONIVEL")
    out_of_scope_sector = create_sector(actor, code="FORA_ESCOPO", company=99)
    out_of_scope_template = create_published_template(actor, out_of_scope_sector)
    out_of_scope = create_published_group(
        actor,
        out_of_scope_sector,
        out_of_scope_template,
        code="FORA",
    )
    create_rule(actor, available.group_id, name="Disponível", company_code=1)
    create_rule(actor, out_of_scope.group_id, name="Fora do escopo", company_code=1)

    client = Client()
    client.force_login(actor)
    response = client.get(
        reverse("offboarding-api:process-draft", kwargs={"process_uuid": process.uuid})
    )

    assert response.status_code == 200
    suggestion = response.json()["applicability_suggestion"]
    assert suggestion["group_version_ids"] == [available.pk]
    assert [match["rule_name"] for match in suggestion["matches"]] == ["Disponível"]
    assert suggestion["matches"][0]["group_name"]


def test_draft_without_any_rule_suggests_nothing(
    actor: User,
    process: OffboardingProcess,
) -> None:
    published_group(actor)

    client = Client()
    client.force_login(actor)
    response = client.get(
        reverse("offboarding-api:process-draft", kwargs={"process_uuid": process.uuid})
    )

    assert response.status_code == 200
    assert response.json()["applicability_suggestion"] == {
        "group_version_ids": [],
        "matches": [],
    }


def test_rule_endpoints_reject_anonymous_and_unauthorized(
    actor: User,
    plain_user: User,
) -> None:
    version = published_group(actor)
    rule = create_rule(actor, version.group_id)
    list_url = reverse("workflow-configuration-api:applicability-rule-list")
    detail_url = reverse(
        "workflow-configuration-api:applicability-rule-update",
        kwargs={"rule_id": rule.pk},
    )

    anonymous = Client()
    assert anonymous.get(list_url).status_code in {401, 403}
    assert anonymous.post(list_url, {}, content_type="application/json").status_code in {401, 403}

    client = Client()
    client.force_login(plain_user)
    assert client.get(list_url).status_code == 403
    assert client.put(detail_url, {}, content_type="application/json").status_code == 403


def test_rule_api_creates_lists_and_updates(actor: User) -> None:
    version = published_group(actor)
    client = Client()
    client.force_login(actor)
    list_url = reverse("workflow-configuration-api:applicability-rule-list")

    created = client.post(
        list_url,
        {
            "name": "Gestores da matriz",
            "priority": 90,
            "group_id": version.group_id,
            "company_code": 1,
            "job_code": " DEV ",
            "cost_center_code": "",
        },
        content_type="application/json",
    )

    assert created.status_code == 201
    body = created.json()
    assert body["job_code"] == "DEV"
    assert body["cost_center_code"] is None
    assert body["is_active"] is True
    assert body["version"] == 1
    assert body["group"]["id"] == version.group_id

    listed = client.get(list_url)
    assert listed.status_code == 200
    assert [row["name"] for row in listed.json()["results"]] == ["Gestores da matriz"]

    detail_url = reverse(
        "workflow-configuration-api:applicability-rule-update",
        kwargs={"rule_id": body["id"]},
    )
    updated = client.put(
        detail_url,
        {
            "expected_version": body["version"],
            "name": "Gestores da matriz",
            "priority": 90,
            "group_id": version.group_id,
            "company_code": 1,
            "is_active": False,
        },
        content_type="application/json",
    )

    assert updated.status_code == 200
    assert updated.json()["is_active"] is False
    assert updated.json()["version"] == 2

    stale = client.put(
        detail_url,
        {
            "expected_version": body["version"],
            "name": "Gestores da matriz",
            "priority": 90,
            "group_id": version.group_id,
            "is_active": False,
        },
        content_type="application/json",
    )
    assert stale.status_code == 400


def test_rule_api_rejects_incomplete_payload(actor: User) -> None:
    client = Client()
    client.force_login(actor)

    response = client.post(
        reverse("workflow-configuration-api:applicability-rule-list"),
        {"priority": 10},
        content_type="application/json",
    )

    assert response.status_code == 400
    assert not GroupApplicabilityRule.objects.exists()
