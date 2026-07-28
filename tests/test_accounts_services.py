from datetime import timedelta

import pytest
from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import PermissionDenied, ValidationError
from django.core.management import call_command
from django.utils import timezone

from apps.accounts.authorization import has_permission
from apps.accounts.models import (
    AccountAuditEvent,
    AccountEventType,
    Role,
    ScopeType,
    User,
)
from apps.accounts.services import (
    AssignRoleCommand,
    AssignRoleService,
    BootstrapIdentityAdminCommand,
    BootstrapIdentityAdminService,
    ChangeOwnPasswordCommand,
    ChangeOwnPasswordService,
    CreateRoleCommand,
    CreateRoleService,
    CreateUserCommand,
    CreateUserService,
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
    assert user.role_assignments.get().role.code == "ADMIN_IDENTIDADE"
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
            reason="Admissão no SGPD.",
        )
    )

    assert user.username == "nova.usuario"
    assert user.email == "nova.usuario@example.invalid"
    assert user.must_change_password
    event = AccountAuditEvent.objects.get(event_type=AccountEventType.USER_CREATED)
    assert event.actor == actor
    assert event.target_user == user
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
                reason="Teste de rollback.",
            )
        )

    assert not User.objects.filter(username="usuario.fraco").exists()
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
                reason="Atualização concorrente.",
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
                reason="Teste de bloqueio.",
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
                reason="Teste da garantia de acesso administrativo.",
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
                reason="Tentativa sem permissão.",
            )
        )
    with pytest.raises(PermissionDenied):
        CreateRoleService().execute(
            CreateRoleCommand(
                actor=unauthorized_actor,
                code="SEM_PERMISSAO",
                name="Não criado",
                description="",
                permission_ids=(),
                reason="Tentativa sem permissão.",
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
                reason="Tentativa sem permissão.",
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
            reason="Identidade conferida no diretório.",
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
                reason="Tentativa duplicada.",
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
            reason="Vínculo inicial.",
        )
    )

    with pytest.raises(ValidationError, match="outra sessão"):
        UnlinkAdIdentityService().execute(
            UnlinkAdIdentityCommand(
                actor=actor,
                user_id=user.pk,
                expected_version=user.version - 1,
                reason="Versão obsoleta.",
            )
        )
    user = UnlinkAdIdentityService().execute(
        UnlinkAdIdentityCommand(
            actor=actor,
            user_id=user.pk,
            expected_version=user.version,
            reason="Identidade substituída.",
        )
    )
    assert not user.has_ad_link
    assert AccountAuditEvent.objects.filter(event_type=AccountEventType.AD_UNLINKED).exists()


def test_role_assignment_enforces_organizational_scope(actor: User) -> None:
    permission = Permission.objects.get(codename="query_senior_references")
    role = CreateRoleService().execute(
        CreateRoleCommand(
            actor=actor,
            code="dp_empresa",
            name="DP por empresa",
            description="Acesso cadastral limitado.",
            permission_ids=(permission.pk,),
            reason="Matriz de acesso.",
        )
    )
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
            reason="Responsabilidade pela empresa 1.",
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


def test_role_assignment_is_idempotent_and_revocable(actor: User) -> None:
    role = Role.objects.create(code="AUDITOR_TESTE", name="Auditor de teste")
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
        reason="Atribuição de auditoria.",
    )

    first = AssignRoleService().execute(command)
    second = AssignRoleService().execute(command)
    assert first.pk == second.pk
    assert AccountAuditEvent.objects.filter(event_type=AccountEventType.ROLE_ASSIGNED).count() == 1

    revoked = RevokeRoleService().execute(
        RevokeRoleCommand(
            actor=actor,
            assignment_id=first.pk,
            reason="Fim da responsabilidade.",
        )
    )
    assert not revoked.is_active
    assert revoked.revoked_by == actor


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
