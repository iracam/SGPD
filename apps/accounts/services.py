"""Transactional use cases for SGPD account administration."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import datetime
from typing import Protocol

from django.contrib.auth.models import Permission
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import IntegrityError, transaction
from django.db.models import QuerySet
from django.utils import timezone

from apps.integrations.active_directory.client import ActiveDirectoryClient
from apps.integrations.active_directory.config import ActiveDirectoryConfig
from apps.integrations.active_directory.dto import DirectoryUser
from config.middleware import correlation_id

from .authorization import has_permission
from .models import (
    AccountAuditEvent,
    AccountEventType,
    Role,
    RoleAssignment,
    ScopeType,
    User,
    build_scope_key,
)

MANAGE_USERS_PERMISSION = "accounts.manage_users"
MANAGE_ROLES_PERMISSION = "accounts.manage_roles"
LINK_AD_IDENTITY_PERMISSION = "accounts.link_ad_identity"
LOCAL_USER_CREATION_REASON = "Criação explícita de conta local no SGPD."
ROLE_ASSIGNMENT_REASON = "Designação explícita de papel no SGPD."
DIRECTORY_IMPORT_REASON = "Criação explícita de conta local a partir do Active Directory."

ASSIGNABLE_PERMISSION_CODENAMES = frozenset(
    {
        "manage_users",
        "manage_roles",
        "link_ad_identity",
        "view_account_audit",
        "query_senior_references",
    }
)


def _require_permission(actor: User, permission: str) -> None:
    if not has_permission(actor, permission):
        raise PermissionDenied("O ator não possui permissão para executar esta operação.")


def _required_reason(reason: str) -> str:
    normalized = reason.strip()
    if not normalized:
        raise ValidationError({"reason": "A justificativa é obrigatória."})
    return normalized


def _record_event(
    *,
    event_type: AccountEventType,
    actor: User | None,
    entity_type: str,
    entity_id: int | str,
    reason: str,
    changes: dict[str, object],
    target_user: User | None = None,
) -> AccountAuditEvent:
    return AccountAuditEvent.objects.create(
        event_type=event_type,
        actor=actor,
        target_user=target_user,
        entity_type=entity_type,
        entity_id=str(entity_id),
        reason=reason,
        changes=changes,
        correlation_id=correlation_id.get(),
    )


def record_authentication_event(
    *,
    event_type: AccountEventType,
    user: User | None,
    reason: str,
) -> AccountAuditEvent:
    if event_type not in {
        AccountEventType.LOGIN,
        AccountEventType.LOGOUT,
        AccountEventType.LOGIN_FAILED,
    }:
        raise ValidationError("Tipo de evento de autenticação inválido.")
    return _record_event(
        event_type=event_type,
        actor=user,
        target_user=user,
        entity_type="AUTHENTICATION",
        entity_id=user.pk if user is not None else "-",
        reason=reason,
        changes={},
    )


def _permissions(permission_ids: Iterable[int]) -> list[Permission]:
    ids = set(permission_ids)
    permissions = list(
        Permission.objects.filter(
            pk__in=ids,
            content_type__app_label="accounts",
        ).select_related("content_type")
    )
    if len(permissions) != len(ids):
        raise ValidationError({"permissions": "Uma ou mais permissões são inválidas."})
    if any(
        permission.codename not in ASSIGNABLE_PERMISSION_CODENAMES for permission in permissions
    ):
        raise ValidationError({"permissions": "A seleção contém uma permissão não delegável."})
    return permissions


def assignable_permissions() -> QuerySet[Permission]:
    """Return the deliberately small permission catalog exposed to role managers."""

    return Permission.objects.filter(
        content_type__app_label="accounts",
        codename__in=ASSIGNABLE_PERMISSION_CODENAMES,
    ).select_related("content_type")


@dataclass(frozen=True, slots=True)
class InitialRoleAssignmentCommand:
    role_id: int
    scope_type: ScopeType
    company_code: int | None
    branch_code: int | None
    valid_from: datetime | None
    valid_until: datetime | None


@dataclass(frozen=True, slots=True)
class CreateUserCommand:
    actor: User
    username: str
    email: str
    first_name: str
    last_name: str
    password: str
    must_change_password: bool
    initial_role: InitialRoleAssignmentCommand | None = None


class CreateUserService:
    @transaction.atomic
    def execute(self, command: CreateUserCommand) -> User:
        _require_permission(command.actor, MANAGE_USERS_PERMISSION)
        user = User(
            username=command.username,
            email=command.email,
            first_name=command.first_name.strip(),
            last_name=command.last_name.strip(),
            must_change_password=command.must_change_password,
            is_active=True,
        )
        user.clean()
        validate_password(command.password, user)
        user.set_password(command.password)
        try:
            user.full_clean()
            user.save()
        except IntegrityError as exc:
            raise ValidationError(
                "Já existe um usuário com o login, e-mail ou identidade informada."
            ) from exc

        _record_event(
            event_type=AccountEventType.USER_CREATED,
            actor=command.actor,
            target_user=user,
            entity_type="USER",
            entity_id=user.pk,
            reason=LOCAL_USER_CREATION_REASON,
            changes={
                "username": user.username,
                "email": user.email,
                "is_active": user.is_active,
                "must_change_password": user.must_change_password,
            },
        )
        if command.initial_role is not None:
            initial_role = command.initial_role
            AssignRoleService().execute(
                AssignRoleCommand(
                    actor=command.actor,
                    user_id=user.pk,
                    role_id=initial_role.role_id,
                    scope_type=initial_role.scope_type,
                    company_code=initial_role.company_code,
                    branch_code=initial_role.branch_code,
                    valid_from=initial_role.valid_from,
                    valid_until=initial_role.valid_until,
                )
            )
        return user


@dataclass(frozen=True, slots=True)
class BootstrapIdentityAdminCommand:
    username: str
    email: str
    first_name: str
    last_name: str
    password: str


class BootstrapIdentityAdminService:
    """Create the single initial administrator without a pre-existing actor."""

    @transaction.atomic
    def execute(self, command: BootstrapIdentityAdminCommand) -> User:
        try:
            role = Role.objects.select_for_update().get(
                code="ADMIN_IDENTIDADE",
                is_active=True,
            )
        except Role.DoesNotExist as exc:
            raise ValidationError(
                "O papel ADMIN_IDENTIDADE não existe ou está inativo. "
                "Execute bootstrap_roles antes deste comando."
            ) from exc
        # The role row serializes concurrent bootstrap attempts even while the
        # user table is empty and therefore has no row that could be locked.
        if User.objects.filter(is_superuser=True).exists():
            raise ValidationError("O bootstrap já foi concluído.")
        user = User(
            username=command.username,
            email=command.email,
            first_name=command.first_name,
            last_name=command.last_name,
            is_active=True,
            is_staff=True,
            is_superuser=True,
            must_change_password=False,
        )
        user.clean()
        validate_password(command.password, user)
        user.set_password(command.password)
        try:
            user.full_clean()
            user.save()
        except IntegrityError as exc:
            raise ValidationError("Já existe um usuário com o login ou e-mail informado.") from exc

        _record_event(
            event_type=AccountEventType.USER_CREATED,
            actor=None,
            target_user=user,
            entity_type="USER",
            entity_id=user.pk,
            reason="Bootstrap explícito da primeira conta administrativa.",
            changes={
                "username": user.username,
                "email": user.email,
                "is_active": True,
                "is_staff": True,
                "is_superuser": True,
            },
        )
        assignment = RoleAssignment(
            user=user,
            role=role,
            scope_type=ScopeType.GLOBAL,
            company_code=None,
            branch_code=None,
            scope_key="*",
            assigned_by=user,
        )
        assignment.full_clean()
        assignment.save()
        _record_event(
            event_type=AccountEventType.ROLE_ASSIGNED,
            actor=user,
            target_user=user,
            entity_type="ROLE_ASSIGNMENT",
            entity_id=assignment.pk,
            reason="Papel global atribuído durante o bootstrap administrativo.",
            changes={"role": role.code, "scope": "*"},
        )
        return user


@dataclass(frozen=True, slots=True)
class UpdateUserCommand:
    actor: User
    user_id: int
    expected_version: int
    email: str
    first_name: str
    last_name: str
    is_active: bool
    reason: str


class UpdateUserService:
    @transaction.atomic
    def execute(self, command: UpdateUserCommand) -> User:
        _require_permission(command.actor, MANAGE_USERS_PERMISSION)
        reason = _required_reason(command.reason)
        active_superuser_ids: set[int] = set()
        if not command.is_active:
            # Every deactivation follows the same lock order. This serializes
            # concurrent attempts to deactivate distinct superusers.
            active_superuser_ids = set(
                User.objects.select_for_update()
                .filter(is_superuser=True, is_active=True)
                .order_by("pk")
                .values_list("pk", flat=True)
            )
        user = User.objects.select_for_update().get(pk=command.user_id)
        if user.version != command.expected_version:
            raise ValidationError("O usuário foi alterado por outra sessão. Recarregue a página.")
        if user.pk == command.actor.pk and not command.is_active:
            raise ValidationError("Um administrador não pode desativar a própria conta.")
        if (
            user.is_superuser
            and user.is_active
            and not command.is_active
            and active_superuser_ids == {user.pk}
        ):
            raise ValidationError("O último superusuário ativo não pode ser desativado.")

        before = {
            "email": user.email,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "is_active": user.is_active,
        }
        was_active = user.is_active
        user.email = command.email
        user.first_name = command.first_name.strip()
        user.last_name = command.last_name.strip()
        user.is_active = command.is_active
        user.version += 1
        try:
            user.full_clean()
            user.save(
                update_fields=(
                    "email",
                    "first_name",
                    "last_name",
                    "is_active",
                    "version",
                )
            )
        except IntegrityError as exc:
            raise ValidationError("O e-mail informado já está em uso.") from exc

        event_type = AccountEventType.USER_UPDATED
        if was_active and not user.is_active:
            event_type = AccountEventType.USER_DEACTIVATED
        elif not was_active and user.is_active:
            event_type = AccountEventType.USER_ACTIVATED
        _record_event(
            event_type=event_type,
            actor=command.actor,
            target_user=user,
            entity_type="USER",
            entity_id=user.pk,
            reason=reason,
            changes={
                "before": before,
                "after": {
                    "email": user.email,
                    "first_name": user.first_name,
                    "last_name": user.last_name,
                    "is_active": user.is_active,
                },
            },
        )
        return user


@dataclass(frozen=True, slots=True)
class ResetPasswordCommand:
    actor: User
    user_id: int
    password: str
    must_change_password: bool
    reason: str


class ResetPasswordService:
    @transaction.atomic
    def execute(self, command: ResetPasswordCommand) -> User:
        _require_permission(command.actor, MANAGE_USERS_PERMISSION)
        reason = _required_reason(command.reason)
        user = User.objects.select_for_update().get(pk=command.user_id)
        config = ActiveDirectoryConfig.from_settings()
        if not config.allows_local_password(
            has_ad_link=user.has_ad_link,
            is_superuser=user.is_superuser,
        ):
            raise ValidationError(
                {"password": "A senha desta conta é gerenciada pelo Active Directory."}
            )
        validate_password(command.password, user)
        user.set_password(command.password)
        user.must_change_password = command.must_change_password
        user.version += 1
        user.save(update_fields=("password", "must_change_password", "version"))
        _record_event(
            event_type=AccountEventType.PASSWORD_RESET,
            actor=command.actor,
            target_user=user,
            entity_type="USER",
            entity_id=user.pk,
            reason=reason,
            changes={"must_change_password": user.must_change_password},
        )
        return user


@dataclass(frozen=True, slots=True)
class ChangeOwnPasswordCommand:
    user_id: int
    current_password: str
    new_password: str
    reason: str = "Alteração de senha pelo próprio usuário."


class ChangeOwnPasswordService:
    @transaction.atomic
    def execute(self, command: ChangeOwnPasswordCommand) -> User:
        user = User.objects.select_for_update().get(pk=command.user_id)
        config = ActiveDirectoryConfig.from_settings()
        if not config.allows_local_password(
            has_ad_link=user.has_ad_link,
            is_superuser=user.is_superuser,
        ):
            raise ValidationError(
                {"old_password": "A senha desta conta é gerenciada pelo Active Directory."}
            )
        if not user.check_password(command.current_password):
            raise ValidationError({"old_password": "A senha atual está incorreta."})
        validate_password(command.new_password, user)
        user.set_password(command.new_password)
        user.must_change_password = False
        user.version += 1
        user.save(update_fields=("password", "must_change_password", "version"))
        _record_event(
            event_type=AccountEventType.PASSWORD_CHANGED,
            actor=user,
            target_user=user,
            entity_type="USER",
            entity_id=user.pk,
            reason=command.reason,
            changes={"must_change_password": False},
        )
        return user


@dataclass(frozen=True, slots=True)
class CreateRoleCommand:
    actor: User
    code: str
    name: str
    description: str
    permission_ids: tuple[int, ...]
    reason: str


class CreateRoleService:
    @transaction.atomic
    def execute(self, command: CreateRoleCommand) -> Role:
        _require_permission(command.actor, MANAGE_ROLES_PERMISSION)
        reason = _required_reason(command.reason)
        permissions = _permissions(command.permission_ids)
        role = Role(
            code=command.code,
            name=command.name,
            description=command.description.strip(),
        )
        role.full_clean()
        try:
            role.save()
        except IntegrityError as exc:
            raise ValidationError({"code": "Já existe um papel com este código."}) from exc
        role.permissions.set(permissions)
        _record_event(
            event_type=AccountEventType.ROLE_CREATED,
            actor=command.actor,
            entity_type="ROLE",
            entity_id=role.pk,
            reason=reason,
            changes={
                "code": role.code,
                "name": role.name,
                "permissions": sorted(permission.codename for permission in permissions),
            },
        )
        return role


@dataclass(frozen=True, slots=True)
class UpdateRoleCommand:
    actor: User
    role_id: int
    expected_version: int
    name: str
    description: str
    is_active: bool
    permission_ids: tuple[int, ...]
    reason: str


class UpdateRoleService:
    @transaction.atomic
    def execute(self, command: UpdateRoleCommand) -> Role:
        _require_permission(command.actor, MANAGE_ROLES_PERMISSION)
        reason = _required_reason(command.reason)
        permissions = _permissions(command.permission_ids)
        role = (
            Role.objects.select_for_update().prefetch_related("permissions").get(pk=command.role_id)
        )
        if role.version != command.expected_version:
            raise ValidationError("O papel foi alterado por outra sessão. Recarregue a página.")
        before = {
            "name": role.name,
            "description": role.description,
            "is_active": role.is_active,
            "permissions": sorted(role.permissions.values_list("codename", flat=True)),
        }
        role.name = command.name
        role.description = command.description.strip()
        role.is_active = command.is_active
        role.version += 1
        role.full_clean()
        role.save(update_fields=("name", "description", "is_active", "version", "updated_at"))
        role.permissions.set(permissions)
        _record_event(
            event_type=AccountEventType.ROLE_UPDATED,
            actor=command.actor,
            entity_type="ROLE",
            entity_id=role.pk,
            reason=reason,
            changes={
                "before": before,
                "after": {
                    "name": role.name,
                    "description": role.description,
                    "is_active": role.is_active,
                    "permissions": sorted(permission.codename for permission in permissions),
                },
            },
        )
        return role


@dataclass(frozen=True, slots=True)
class AssignRoleCommand:
    actor: User
    user_id: int
    role_id: int
    scope_type: ScopeType
    company_code: int | None
    branch_code: int | None
    valid_from: datetime | None
    valid_until: datetime | None


class AssignRoleService:
    @transaction.atomic
    def execute(self, command: AssignRoleCommand) -> RoleAssignment:
        _require_permission(command.actor, MANAGE_ROLES_PERMISSION)
        user = User.objects.select_for_update().get(pk=command.user_id)
        role = Role.objects.select_for_update().get(pk=command.role_id)
        if not user.is_active:
            raise ValidationError("Não é possível atribuir papel a um usuário inativo.")
        if not role.is_active:
            raise ValidationError("Não é possível atribuir um papel inativo.")

        scope_key = build_scope_key(
            command.scope_type,
            command.company_code,
            command.branch_code,
        )
        try:
            assignment = RoleAssignment.objects.select_for_update().get(
                user=user,
                role=role,
                scope_key=scope_key,
            )
        except RoleAssignment.DoesNotExist:
            assignment = None
        if assignment is None:
            assignment = RoleAssignment(
                user=user,
                role=role,
                scope_type=command.scope_type,
                company_code=command.company_code,
                branch_code=command.branch_code,
                scope_key=scope_key,
                valid_from=command.valid_from or timezone.now(),
                valid_until=command.valid_until,
                assigned_by=command.actor,
            )
        elif (
            assignment.is_active
            and assignment.valid_from == (command.valid_from or assignment.valid_from)
            and assignment.valid_until == command.valid_until
        ):
            return assignment
        else:
            assignment.is_active = True
            assignment.valid_from = command.valid_from or timezone.now()
            assignment.valid_until = command.valid_until
            assignment.assigned_by = command.actor
            assignment.revoked_by = None
            assignment.revoked_at = None

        assignment.full_clean()
        assignment.save()
        _record_event(
            event_type=AccountEventType.ROLE_ASSIGNED,
            actor=command.actor,
            target_user=user,
            entity_type="ROLE_ASSIGNMENT",
            entity_id=assignment.pk,
            reason=ROLE_ASSIGNMENT_REASON,
            changes={
                "role": role.code,
                "scope": scope_key,
                "valid_from": assignment.valid_from.isoformat(),
                "valid_until": (
                    assignment.valid_until.isoformat()
                    if assignment.valid_until is not None
                    else None
                ),
            },
        )
        return assignment


@dataclass(frozen=True, slots=True)
class RevokeRoleCommand:
    actor: User
    assignment_id: int
    reason: str


class RevokeRoleService:
    @transaction.atomic
    def execute(self, command: RevokeRoleCommand) -> RoleAssignment:
        _require_permission(command.actor, MANAGE_ROLES_PERMISSION)
        reason = _required_reason(command.reason)
        assignment = (
            RoleAssignment.objects.select_for_update()
            .select_related("user", "role")
            .get(pk=command.assignment_id)
        )
        if not assignment.is_active:
            return assignment
        assignment.is_active = False
        assignment.revoked_by = command.actor
        assignment.revoked_at = timezone.now()
        assignment.full_clean()
        assignment.save(update_fields=("is_active", "revoked_by", "revoked_at"))
        _record_event(
            event_type=AccountEventType.ROLE_REVOKED,
            actor=command.actor,
            target_user=assignment.user,
            entity_type="ROLE_ASSIGNMENT",
            entity_id=assignment.pk,
            reason=reason,
            changes={"role": assignment.role.code, "scope": assignment.scope_key},
        )
        return assignment


class DirectoryUserLookup(Protocol):
    def get_user(self, identifier: str) -> DirectoryUser: ...


@dataclass(frozen=True, slots=True)
class CreateUserFromDirectoryCommand:
    actor: User
    identifier: str


class CreateUserFromDirectoryService:
    """Explicitly provision one local account from a verified AD identity."""

    def __init__(self, directory: DirectoryUserLookup | None = None) -> None:
        self.directory = directory or ActiveDirectoryClient()

    def execute(self, command: CreateUserFromDirectoryCommand) -> User:
        _require_permission(command.actor, MANAGE_USERS_PERMISSION)
        _require_permission(command.actor, LINK_AD_IDENTITY_PERMISSION)
        identity = self.directory.get_user(command.identifier)
        if not identity.can_import:
            missing = ", ".join(identity.missing_import_fields)
            raise ValidationError(
                {
                    "identifier": (
                        "A identidade não possui os atributos obrigatórios para importação: "
                        f"{missing}."
                    )
                }
            )
        return self._persist(command.actor, identity)

    @transaction.atomic
    def _persist(self, actor: User, identity: DirectoryUser) -> User:
        try:
            return User.objects.select_for_update().get(ad_identifier=identity.identifier)
        except User.DoesNotExist:
            pass

        # Oracle does not support FETCH FIRST/LIMIT in a SELECT ... FOR UPDATE.
        # Materialize these small, unique-key candidate sets without slicing.
        username_conflicts = list(
            User.objects.select_for_update()
            .filter(username__iexact=identity.username)
            .values_list("pk", flat=True)
        )
        if username_conflicts:
            raise ValidationError(
                {
                    "identifier": (
                        "Já existe uma conta local com o mesmo login. "
                        "Abra essa conta e vincule a identidade encontrada."
                    )
                }
            )
        email_conflicts = list(
            User.objects.select_for_update()
            .filter(email__iexact=identity.email)
            .values_list("pk", flat=True)
        )
        if email_conflicts:
            raise ValidationError(
                {
                    "identifier": (
                        "Já existe uma conta local com o mesmo e-mail. "
                        "Confirme a pessoa e vincule a identidade à conta existente."
                    )
                }
            )

        user = User(
            username=identity.username,
            email=identity.email or "",
            first_name=identity.first_name or "",
            last_name=identity.last_name or "",
            is_active=True,
            must_change_password=False,
            ad_identifier=identity.identifier,
            ad_username=identity.username,
            ad_linked_at=timezone.now(),
            ad_linked_by=actor,
        )
        user.set_unusable_password()
        user.clean()
        try:
            user.full_clean()
            user.save()
        except IntegrityError as exc:
            raise ValidationError(
                "Já existe um usuário com o login, e-mail ou identidade informada."
            ) from exc

        _record_event(
            event_type=AccountEventType.USER_CREATED,
            actor=actor,
            target_user=user,
            entity_type="USER",
            entity_id=user.pk,
            reason=DIRECTORY_IMPORT_REASON,
            changes={
                "username": user.username,
                "email": user.email,
                "is_active": True,
                "source": "ACTIVE_DIRECTORY",
            },
        )
        _record_event(
            event_type=AccountEventType.AD_LINKED,
            actor=actor,
            target_user=user,
            entity_type="USER",
            entity_id=user.pk,
            reason=DIRECTORY_IMPORT_REASON,
            changes={"ad_linked": True, "verified_by_directory": True},
        )
        return user


@dataclass(frozen=True, slots=True)
class LinkAdIdentityCommand:
    actor: User
    user_id: int
    expected_version: int
    identifier: str
    username: str
    reason: str


class LinkAdIdentityService:
    @transaction.atomic
    def execute(self, command: LinkAdIdentityCommand) -> User:
        _require_permission(command.actor, LINK_AD_IDENTITY_PERMISSION)
        reason = _required_reason(command.reason)
        identifier = command.identifier.strip().casefold()
        ad_username = command.username.strip().lower()
        if not identifier or not ad_username:
            raise ValidationError("Identificador e usuário do AD são obrigatórios.")

        user = User.objects.select_for_update().get(pk=command.user_id)
        if user.version != command.expected_version:
            raise ValidationError("O usuário foi alterado por outra sessão. Recarregue a página.")
        if user.has_ad_link:
            if user.ad_identifier == identifier and user.ad_username == ad_username:
                return user
            raise ValidationError(
                "A conta já possui vínculo AD. Desvincule antes de associar outra identidade."
            )

        user.ad_identifier = identifier
        user.ad_username = ad_username
        user.ad_linked_at = timezone.now()
        user.ad_linked_by = command.actor
        user.version += 1
        try:
            user.full_clean()
            user.save(
                update_fields=(
                    "ad_identifier",
                    "ad_username",
                    "ad_linked_at",
                    "ad_linked_by",
                    "version",
                )
            )
        except IntegrityError as exc:
            raise ValidationError(
                "A identidade AD informada já está vinculada a outra conta."
            ) from exc
        _record_event(
            event_type=AccountEventType.AD_LINKED,
            actor=command.actor,
            target_user=user,
            entity_type="USER",
            entity_id=user.pk,
            reason=reason,
            changes={"ad_linked": True},
        )
        return user


class LinkDirectoryIdentityService:
    """Verify the stable AD identity immediately before linking it."""

    def __init__(self, directory: DirectoryUserLookup | None = None) -> None:
        self.directory = directory or ActiveDirectoryClient()

    def execute(self, command: LinkAdIdentityCommand) -> User:
        _require_permission(command.actor, LINK_AD_IDENTITY_PERMISSION)
        reason = _required_reason(command.reason)
        identity = self.directory.get_user(command.identifier)
        return LinkAdIdentityService().execute(
            LinkAdIdentityCommand(
                actor=command.actor,
                user_id=command.user_id,
                expected_version=command.expected_version,
                identifier=identity.identifier,
                username=identity.username,
                reason=reason,
            )
        )


@dataclass(frozen=True, slots=True)
class UnlinkAdIdentityCommand:
    actor: User
    user_id: int
    expected_version: int
    reason: str


class UnlinkAdIdentityService:
    @transaction.atomic
    def execute(self, command: UnlinkAdIdentityCommand) -> User:
        _require_permission(command.actor, LINK_AD_IDENTITY_PERMISSION)
        reason = _required_reason(command.reason)
        user = User.objects.select_for_update().get(pk=command.user_id)
        if user.version != command.expected_version:
            raise ValidationError("O usuário foi alterado por outra sessão. Recarregue a página.")
        if not user.has_ad_link:
            return user

        user.ad_identifier = None
        user.ad_username = None
        user.ad_linked_at = None
        user.ad_linked_by = None
        user.version += 1
        user.full_clean()
        user.save(
            update_fields=(
                "ad_identifier",
                "ad_username",
                "ad_linked_at",
                "ad_linked_by",
                "version",
            )
        )
        _record_event(
            event_type=AccountEventType.AD_UNLINKED,
            actor=command.actor,
            target_user=user,
            entity_type="USER",
            entity_id=user.pk,
            reason=reason,
            changes={"ad_linked": False},
        )
        return user
