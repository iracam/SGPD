"""Create the initial SGPD role catalog without embedding user credentials."""

from django.contrib.auth.models import Permission
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.accounts.models import AccountAuditEvent, AccountEventType, Role

ROLE_CATALOG: dict[str, tuple[str, tuple[str, ...]]] = {
    "ADMIN_IDENTIDADE": (
        "Administrador de identidades",
        (
            "manage_users",
            "manage_roles",
            "link_ad_identity",
            "view_account_audit",
        ),
    ),
    "DP": ("Departamento Pessoal", ("query_senior_references",)),
    "RESPONSAVEL_SETOR": ("Responsável de setor", ()),
    "COORDENADOR_SETOR": ("Coordenador de setor", ()),
    "GESTOR_IMEDIATO": ("Gestor imediato", ()),
    "FINANCEIRO": ("Financeiro", ()),
    "JURIDICO": ("Jurídico", ()),
    "AUDITOR": ("Auditor", ("view_account_audit",)),
    "ADMIN_FUNCIONAL": (
        "Administrador funcional",
        ("query_senior_references",),
    ),
}


class Command(BaseCommand):
    help = "Cria, de forma idempotente, o catálogo inicial de papéis do SGPD."

    @transaction.atomic
    def handle(self, *args: object, **options: object) -> None:
        required_codenames = {
            codename for _, permissions in ROLE_CATALOG.values() for codename in permissions
        }
        permissions = {
            permission.codename: permission
            for permission in Permission.objects.filter(
                content_type__app_label="accounts",
                codename__in=required_codenames,
            )
        }
        missing = required_codenames - permissions.keys()
        if missing:
            raise CommandError(
                "Permissões ausentes; execute migrate antes do bootstrap: "
                + ", ".join(sorted(missing))
            )

        created_count = 0
        for code, (name, permission_codenames) in ROLE_CATALOG.items():
            role, created = Role.objects.get_or_create(
                code=code,
                defaults={
                    "name": name,
                    "description": "Papel inicial definido na matriz funcional do SGPD.",
                },
            )
            if not created:
                continue
            role.permissions.set([permissions[codename] for codename in permission_codenames])
            AccountAuditEvent.objects.create(
                event_type=AccountEventType.ROLE_CREATED,
                actor=None,
                entity_type="ROLE",
                entity_id=str(role.pk),
                reason="Bootstrap idempotente do catálogo inicial de papéis.",
                changes={
                    "code": role.code,
                    "name": role.name,
                    "permissions": sorted(permission_codenames),
                },
                correlation_id="bootstrap-roles",
            )
            created_count += 1

        self.stdout.write(
            self.style.SUCCESS(f"Catálogo verificado: {created_count} papel(is) criado(s).")
        )
