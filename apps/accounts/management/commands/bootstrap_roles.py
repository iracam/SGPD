"""Create the initial SGPD role catalog without embedding user credentials."""

from django.contrib.auth.models import Permission
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.accounts.models import (
    FUNCTIONAL_ROLE_CODES,
    PEOPLE_DEPARTMENT_ROLE_CODE,
    AccountAuditEvent,
    AccountEventType,
    Role,
)

ROLE_CATALOG: dict[str, tuple[str, str, tuple[str, ...]]] = {
    PEOPLE_DEPARTMENT_ROLE_CODE: (
        "Departamento Pessoal",
        (
            "Autoriza iniciar, acompanhar, avaliar, liberar e encerrar o "
            "processo demissional dentro do escopo atribuído."
        ),
        ("accounts.query_senior_references",),
    ),
}


class Command(BaseCommand):
    help = "Reconcilia o catálogo funcional fixo com o papel atribuível DP."

    @transaction.atomic
    def handle(self, *args: object, **options: object) -> None:
        required_permissions = {
            permission for _, _, permissions in ROLE_CATALOG.values() for permission in permissions
        }
        permissions = {
            f"{permission.content_type.app_label}.{permission.codename}": permission
            for permission in Permission.objects.select_related("content_type")
        }
        missing = required_permissions - permissions.keys()
        if missing:
            raise CommandError(
                "Permissões ausentes; execute migrate antes do bootstrap: "
                + ", ".join(sorted(missing))
            )

        created_count = 0
        updated_count = 0
        retired_count = 0
        for code, (name, description, permission_names) in ROLE_CATALOG.items():
            role, created = Role.objects.get_or_create(
                code=code,
                defaults={
                    "name": name,
                    "description": description,
                },
            )
            expected = {permissions[name] for name in permission_names}
            if created:
                role.permissions.set(expected)
                AccountAuditEvent.objects.create(
                    event_type=AccountEventType.ROLE_CREATED,
                    actor=None,
                    entity_type="ROLE",
                    entity_id=str(role.pk),
                    reason="Bootstrap idempotente do catálogo funcional fixo.",
                    changes={
                        "code": role.code,
                        "name": role.name,
                        "permissions": sorted(permission_names),
                    },
                    correlation_id="bootstrap-roles",
                )
                created_count += 1
                continue

            before = {
                "name": role.name,
                "description": role.description,
                "is_active": role.is_active,
                "permissions": sorted(
                    f"{permission.content_type.app_label}.{permission.codename}"
                    for permission in role.permissions.select_related("content_type")
                ),
            }
            after = {
                "name": name,
                "description": description,
                "is_active": True,
                "permissions": sorted(permission_names),
            }
            if before == after:
                continue
            role.name = name
            role.description = description
            role.is_active = True
            role.version += 1
            role.save(update_fields=("name", "description", "is_active", "version", "updated_at"))
            role.permissions.set(expected)
            AccountAuditEvent.objects.create(
                event_type=AccountEventType.ROLE_UPDATED,
                actor=None,
                entity_type="ROLE",
                entity_id=str(role.pk),
                reason="Reconciliação do catálogo funcional fixo.",
                changes={"before": before, "after": after},
                correlation_id="bootstrap-roles",
            )
            updated_count += 1

        legacy_roles = (
            Role.objects.select_for_update()
            .exclude(code__in=FUNCTIONAL_ROLE_CODES)
            .filter(is_active=True)
        )
        for role in legacy_roles:
            role.is_active = False
            role.version += 1
            role.save(update_fields=("is_active", "version", "updated_at"))
            AccountAuditEvent.objects.create(
                event_type=AccountEventType.ROLE_UPDATED,
                actor=None,
                entity_type="ROLE",
                entity_id=str(role.pk),
                reason="Inativação de papel fora do catálogo funcional fixo.",
                changes={
                    "before": {"is_active": True},
                    "after": {"is_active": False},
                },
                correlation_id="bootstrap-roles",
            )
            retired_count += 1

        self.stdout.write(
            self.style.SUCCESS(
                "Catálogo verificado: "
                f"{created_count} papel(is) criado(s), "
                f"{updated_count} papel(is) atualizado(s), "
                f"{retired_count} papel(is) legado(s) inativado(s)."
            )
        )
