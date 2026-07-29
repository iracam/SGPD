from datetime import timedelta

import pytest
from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import PermissionDenied, ValidationError
from django.core.management import call_command
from django.db import connection
from django.utils import timezone

from apps.accounts.authorization import has_effective_role, has_permission
from apps.accounts.models import (
    PEOPLE_DEPARTMENT_ROLE_CODE,
    RESPONSIBLE_SECTOR_ROLE_CODE,
    AccountAuditEvent,
    AccountEventType,
    Role,
    ScopeType,
    User,
)
from apps.accounts.services import (
    LOCAL_USER_CREATION_REASON,
    ROLE_ASSIGNMENT_REASON,
    AssignRoleCommand,
    AssignRoleService,
    BootstrapIdentityAdminCommand,
    BootstrapIdentityAdminService,
    ChangeOwnPasswordCommand,
    ChangeOwnPasswordService,
    CreateUserCommand,
    CreateUserService,
    InitialRoleAssignmentCommand,
    LinkAdIdentityCommand,
    LinkAdIdentityService,
    RevokeRoleCommand,
    RevokeRoleService,
    UnlinkAdIdentityCommand,
    UnlinkAdIdentityService,
    UpdateUserCommand,
    UpdateUserService,
)

pytestmark = pytest.mark.django_db


@pytest.fixture
def actor() -> User:
    return User.objects.create_superuser(
        username="admin.identidade",
        email="admin.identidade@example.invalid",
        password="Admin-only-test-password!2026",
    )


def create_user(username: str) -> User:
    return User.objects.create_user(
        username=username,
        email=f"{username}@example.invalid",
        first_name="Usuário",
        last_name="Teste",
        password="Test-only-password!2026",
    )


def test_bootstrap_creates_single_audited_identity_admin() -> None:
    call_command("bootstrap_roles")

    user = BootstrapIdentityAdminService().execute(
        BootstrapIdentityAdminCommand(
            username="Primeiro.Admin",
            email="PRIMEIRO.ADMIN@example.invalid",
            first_name="Primeiro",
            last_name="Administrador",
            password="Bootstrap-admin-test!2026",
        )
    )

    assert user.username == "primeiro.admin"
    assert user.is_superuser
    assert user.is_staff
    assert not user.role_assignments.exists()
    assert list(Role.objects.filter(is_active=True).values_list("code", flat=True)) == ["DP"]
    assert AccountAuditEvent.objects.filter(
        event_type=AccountEventType.USER_CREATED,
        actor__isnull=True,
        target_user=user,
    ).exists()
    with pytest.raises(ValidationError, match="já foi concluído"):
        BootstrapIdentityAdminService().execute(
            BootstrapIdentityAdminCommand(
                username="segundo.admin",
                email="segundo.admin@example.invalid",
                first_name="Segundo",
                last_name="Administrador",
                password="Bootstrap-admin-test!2026",
            )
        )


def test_bootstrap_reconciles_the_fixed_role_catalog() -> None:
    call_command("bootstrap_roles")
    role = Role.objects.get(code="DP")
    assert list(role.permissions.values_list("codename", flat=True)) == ["query_senior_references"]
    extra = Permission.objects.get(
        content_type__app_label="accounts",
        codename="manage_users",
    )
    role.permissions.add(extra)
    role.name = "Nome divergente"
    role.description = "Descrição divergente"
    role.is_active = False
    role.save(update_fields=("name", "description", "is_active"))
    before = AccountAuditEvent.objects.count()

    call_command("bootstrap_roles")

    role.refresh_from_db()
    assert role.name == "Departamento Pessoal"
    assert role.is_active
    assert list(role.permissions.values_list("codename", flat=True)) == ["query_senior_references"]
    event = AccountAuditEvent.objects.filter(
        event_type=AccountEventType.ROLE_UPDATED,
        entity_type="ROLE",
        entity_id=str(role.pk),
    ).latest("occurred_at")
    assert event.changes["before"]["is_active"] is False
    assert event.changes["after"]["is_active"] is True
    assert event.changes["after"]["permissions"] == ["accounts.query_senior_references"]
    assert AccountAuditEvent.objects.count() == before + 1

    call_command("bootstrap_roles")
    assert AccountAuditEvent.objects.count() == before + 1


def test_fixed_role_model_accepts_dp_and_rejects_role_outside_catalog() -> None:
    Role(code="DP", name="Departamento Pessoal").full_clean()
    legacy = Role(code="FINANCEIRO", name="Financeiro")
    with pytest.raises(ValidationError, match="Somente o papel DP"):
        legacy.full_clean()

    assert not Role.objects.exists()
    assert not AccountAuditEvent.objects.exists()


def test_create_user_normalizes_identity_and_audits(actor: User) -> None:
    user = CreateUserService().execute(
        CreateUserCommand(
            actor=actor,
            username="Nova.Usuario",
            email="NOVA.USUARIO@EXAMPLE.INVALID",
            first_name="Nova",
            last_name="Usuária",
            password="Temporary-only!2026",
            must_change_password=True,
        )
    )

    assert user.username == "nova.usuario"
    assert user.email == "nova.usuario@example.invalid"
    assert user.must_change_password
    event = AccountAuditEvent.objects.get(event_type=AccountEventType.USER_CREATED)
    assert event.actor == actor
    assert event.target_user == user
    assert event.reason == LOCAL_USER_CREATION_REASON
    assert "password" not in event.changes


def test_create_user_rolls_back_when_password_is_invalid(actor: User) -> None:
    with pytest.raises(ValidationError):
        CreateUserService().execute(
            CreateUserCommand(
                actor=actor,
                username="usuario.fraco",
                email="usuario.fraco@example.invalid",
                first_name="Usuário",
                last_name="Fraco",
                password="123",
                must_change_password=True,
            )
        )

    assert not User.objects.filter(username="usuario.fraco").exists()
    assert not AccountAuditEvent.objects.exists()


def test_create_user_assigns_initial_role_in_the_same_transaction(actor: User) -> None:
    role = Role.objects.create(code="DP", name="Departamento Pessoal")

    user = CreateUserService().execute(
        CreateUserCommand(
            actor=actor,
            username="gestor.inicial",
            email="gestor.inicial@example.invalid",
            first_name="Gestor",
            last_name="Inicial",
            password="Temporary-only!2026",
            must_change_password=True,
            initial_role=InitialRoleAssignmentCommand(
                role_id=role.pk,
                scope_type=ScopeType.GLOBAL,
                company_code=None,
                branch_code=None,
                valid_from=None,
                valid_until=None,
            ),
        )
    )

    assignment = user.role_assignments.get()
    assert assignment.role == role
    assert assignment.scope_key == "*"
    assert assignment.assigned_by == actor
    assert AccountAuditEvent.objects.filter(
        event_type=AccountEventType.USER_CREATED,
        target_user=user,
    ).exists()
    assert AccountAuditEvent.objects.filter(
        event_type=AccountEventType.ROLE_ASSIGNED,
        target_user=user,
        reason=ROLE_ASSIGNMENT_REASON,
    ).exists()


def test_create_user_rolls_back_when_initial_role_is_inactive(actor: User) -> None:
    role = Role.objects.create(code="PAPEL_INATIVO", name="Papel inativo", is_active=False)

    with pytest.raises(ValidationError, match="papel inativo"):
        CreateUserService().execute(
            CreateUserCommand(
                actor=actor,
                username="papel.inativo",
                email="papel.inativo@example.invalid",
                first_name="Papel",
                last_name="Inativo",
                password="Temporary-only!2026",
                must_change_password=True,
                initial_role=InitialRoleAssignmentCommand(
                    role_id=role.pk,
                    scope_type=ScopeType.GLOBAL,
                    company_code=None,
                    branch_code=None,
                    valid_from=None,
                    valid_until=None,
                ),
            )
        )

    assert not User.objects.filter(username="papel.inativo").exists()
    assert not role.assignments.exists()
    assert not AccountAuditEvent.objects.exists()


def test_update_user_rejects_stale_version(actor: User) -> None:
    user = create_user("usuario.concorrente")

    with pytest.raises(ValidationError, match="outra sessão"):
        UpdateUserService().execute(
            UpdateUserCommand(
                actor=actor,
                user_id=user.pk,
                expected_version=user.version + 1,
                email=user.email,
                first_name="Nome",
                last_name="Atualizado",
                is_active=True,
            )
        )

    user.refresh_from_db()
    assert user.first_name == "Usuário"
    assert not AccountAuditEvent.objects.exists()


def test_actor_cannot_deactivate_own_account(actor: User) -> None:
    with pytest.raises(ValidationError, match="própria conta"):
        UpdateUserService().execute(
            UpdateUserCommand(
                actor=actor,
                user_id=actor.pk,
                expected_version=actor.version,
                email=actor.email,
                first_name=actor.first_name,
                last_name=actor.last_name,
                is_active=False,
            )
        )


def test_last_active_superuser_cannot_be_deactivated_by_another_manager() -> None:
    manager = create_user("gestor.identidade")
    manager.user_permissions.add(Permission.objects.get(codename="manage_users"))
    last_superuser = User.objects.create_superuser(
        username="ultimo.superusuario",
        email="ultimo.superusuario@example.invalid",
        password="Admin-only-test-password!2026",
    )

    with pytest.raises(ValidationError, match="último superusuário"):
        UpdateUserService().execute(
            UpdateUserCommand(
                actor=manager,
                user_id=last_superuser.pk,
                expected_version=last_superuser.version,
                email=last_superuser.email,
                first_name="Último",
                last_name="Superusuário",
                is_active=False,
            )
        )

    last_superuser.refresh_from_db()
    assert last_superuser.is_active
    assert not AccountAuditEvent.objects.exists()


def test_account_services_reject_actor_without_required_permission() -> None:
    unauthorized_actor = create_user("sem.permissao")
    target = create_user("alvo.ad")

    with pytest.raises(PermissionDenied):
        CreateUserService().execute(
            CreateUserCommand(
                actor=unauthorized_actor,
                username="nao.criado",
                email="nao.criado@example.invalid",
                first_name="Não",
                last_name="Criado",
                password="Temporary-only!2026",
                must_change_password=True,
            )
        )
    with pytest.raises(PermissionDenied):
        LinkAdIdentityService().execute(
            LinkAdIdentityCommand(
                actor=unauthorized_actor,
                user_id=target.pk,
                expected_version=target.version,
                identifier="guid-nao-vinculado",
                username="nao.vinculado",
            )
        )

    assert not User.objects.filter(username="nao.criado").exists()
    assert not Role.objects.filter(code="SEM_PERMISSAO").exists()
    assert not AccountAuditEvent.objects.exists()


def test_permission_codename_from_another_app_does_not_authorize() -> None:
    user = create_user("permissao.colisao")
    foreign_content_type = ContentType.objects.get(app_label="auth", model="group")
    foreign_permission = Permission.objects.create(
        content_type=foreign_content_type,
        codename="manage_users",
        name="Colisão intencional para teste",
    )
    user.user_permissions.add(foreign_permission)

    assert not has_permission(user, "accounts.manage_users")


def test_ad_link_is_unique_normalized_and_audited(actor: User) -> None:
    first = create_user("primeiro.vinculo")
    second = create_user("segundo.vinculo")
    linked = LinkAdIdentityService().execute(
        LinkAdIdentityCommand(
            actor=actor,
            user_id=first.pk,
            expected_version=first.version,
            identifier=" Object-GUID-ABC ",
            username="DOMINIO\\Primeiro.Vinculo",
        )
    )

    assert linked.ad_identifier == "object-guid-abc"
    assert linked.ad_username == "dominio\\primeiro.vinculo"
    assert linked.ad_linked_by == actor
    with pytest.raises(ValidationError):
        LinkAdIdentityService().execute(
            LinkAdIdentityCommand(
                actor=actor,
                user_id=second.pk,
                expected_version=second.version,
                identifier="OBJECT-GUID-ABC",
                username="dominio\\outro",
            )
        )
    second.refresh_from_db()
    assert not second.has_ad_link
    assert AccountAuditEvent.objects.filter(event_type=AccountEventType.AD_LINKED).count() == 1


def test_ad_unlink_requires_current_version(actor: User) -> None:
    user = create_user("usuario.ad")
    user = LinkAdIdentityService().execute(
        LinkAdIdentityCommand(
            actor=actor,
            user_id=user.pk,
            expected_version=user.version,
            identifier="guid-unlink",
            username="usuario.ad",
        )
    )

    with pytest.raises(ValidationError, match="outra sessão"):
        UnlinkAdIdentityService().execute(
            UnlinkAdIdentityCommand(
                actor=actor,
                user_id=user.pk,
                expected_version=user.version - 1,
            )
        )
    user = UnlinkAdIdentityService().execute(
        UnlinkAdIdentityCommand(
            actor=actor,
            user_id=user.pk,
            expected_version=user.version,
        )
    )
    assert not user.has_ad_link
    assert AccountAuditEvent.objects.filter(event_type=AccountEventType.AD_UNLINKED).exists()


def test_role_assignment_enforces_organizational_scope(actor: User) -> None:
    permission = Permission.objects.get(codename="query_senior_references")
    role = Role.objects.create(
        code=PEOPLE_DEPARTMENT_ROLE_CODE,
        name="Departamento Pessoal",
    )
    role.permissions.add(permission)
    user = create_user("dp.empresa")
    assignment = AssignRoleService().execute(
        AssignRoleCommand(
            actor=actor,
            user_id=user.pk,
            role_id=role.pk,
            scope_type=ScopeType.COMPANY,
            company_code=1,
            branch_code=None,
            valid_from=timezone.now() - timedelta(minutes=1),
            valid_until=None,
        )
    )

    assert assignment.scope_key == "E:1"
    assert has_permission(
        user,
        "accounts.query_senior_references",
        company_code=1,
        branch_code=10,
    )
    assert not has_permission(
        user,
        "accounts.query_senior_references",
        company_code=2,
        branch_code=10,
    )
    assert not has_permission(user, "accounts.query_senior_references")
    assert has_effective_role(
        user,
        PEOPLE_DEPARTMENT_ROLE_CODE,
        company_code=1,
        branch_code=10,
    )
    assert not has_effective_role(
        user,
        PEOPLE_DEPARTMENT_ROLE_CODE,
        company_code=2,
        branch_code=10,
    )
    assert not has_effective_role(actor, PEOPLE_DEPARTMENT_ROLE_CODE)


def test_sector_responsible_role_cannot_be_assigned(actor: User) -> None:
    responsible_role = Role.objects.create(
        code=RESPONSIBLE_SECTOR_ROLE_CODE,
        name="Responsável de setor",
        is_active=False,
    )
    user = create_user("dp.responsavel")

    with pytest.raises(ValidationError, match="papel inativo"):
        AssignRoleService().execute(
            AssignRoleCommand(
                actor=actor,
                user_id=user.pk,
                role_id=responsible_role.pk,
                scope_type=ScopeType.GLOBAL,
                company_code=None,
                branch_code=None,
                valid_from=None,
                valid_until=None,
            )
        )

    assert not user.role_assignments.exists()


def test_role_assignment_is_idempotent_and_revocable(actor: User) -> None:
    role = Role.objects.create(code="DP", name="Departamento Pessoal")
    user = create_user("auditor.teste")
    command = AssignRoleCommand(
        actor=actor,
        user_id=user.pk,
        role_id=role.pk,
        scope_type=ScopeType.GLOBAL,
        company_code=None,
        branch_code=None,
        valid_from=None,
        valid_until=None,
    )

    first = AssignRoleService().execute(command)
    second = AssignRoleService().execute(command)
    assert first.pk == second.pk
    assert AccountAuditEvent.objects.filter(event_type=AccountEventType.ROLE_ASSIGNED).count() == 1

    revoked = RevokeRoleService().execute(
        RevokeRoleCommand(
            actor=actor,
            assignment_id=first.pk,
        )
    )
    assert not revoked.is_active
    assert revoked.revoked_by == actor

    reactivated = AssignRoleService().execute(command)
    assert reactivated.pk == first.pk
    assert reactivated.is_active
    assert reactivated.revoked_by is None
    assert reactivated.revoked_at is None
    events = AccountAuditEvent.objects.filter(event_type=AccountEventType.ROLE_ASSIGNED)
    assert events.count() == 2
    assert set(events.values_list("reason", flat=True)) == {ROLE_ASSIGNMENT_REASON}


def test_role_assignment_avoids_for_update_with_limit_on_oracle(
    actor: User,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(connection.features, "has_select_for_update", True)
    monkeypatch.setattr(
        connection.features,
        "supports_select_for_update_with_limit",
        False,
    )
    monkeypatch.setattr(connection.ops, "for_update_sql", lambda **_kwargs: "")
    role = Role.objects.create(code="DP", name="Departamento Pessoal")
    user = create_user("oracle.lock")

    assignment = AssignRoleService().execute(
        AssignRoleCommand(
            actor=actor,
            user_id=user.pk,
            role_id=role.pk,
            scope_type=ScopeType.GLOBAL,
            company_code=None,
            branch_code=None,
            valid_from=None,
            valid_until=None,
        )
    )

    assert assignment.scope_key == "*"


def test_own_password_change_clears_temporary_flag() -> None:
    user = User.objects.create_user(
        username="troca.senha",
        email="troca.senha@example.invalid",
        password="Old-test-password!2026",
        must_change_password=True,
    )

    changed = ChangeOwnPasswordService().execute(
        ChangeOwnPasswordCommand(
            user_id=user.pk,
            current_password="Old-test-password!2026",
            new_password="New-test-password!2026",
        )
    )

    assert changed.check_password("New-test-password!2026")
    assert not changed.must_change_password
    assert AccountAuditEvent.objects.filter(event_type=AccountEventType.PASSWORD_CHANGED).exists()


def test_account_audit_event_cannot_be_changed_or_deleted(actor: User) -> None:
    event = AccountAuditEvent.objects.create(
        event_type=AccountEventType.USER_UPDATED,
        actor=actor,
        target_user=actor,
        entity_type="USER",
        entity_id=str(actor.pk),
        reason="Teste de imutabilidade.",
        changes={},
    )

    event.reason = "Alterado"
    with pytest.raises(ValidationError, match="imutáveis"):
        event.save()
    with pytest.raises(ValidationError, match="não podem ser excluídos"):
        event.delete()
    with pytest.raises(ValidationError, match="imutáveis"):
        AccountAuditEvent.objects.filter(pk=event.pk).update(reason="Alterado em lote")
    with pytest.raises(ValidationError, match="não podem ser excluídos"):
        AccountAuditEvent.objects.filter(pk=event.pk).delete()

    event.refresh_from_db()
    assert event.reason == "Teste de imutabilidade."
