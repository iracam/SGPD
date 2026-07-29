from typing import Any

from django.db import migrations, models

RESPONSIBLE_SECTOR_ROLE_CODE = "RESPONSAVEL_SETOR"


def retire_legacy_roles(apps: Any, schema_editor: Any) -> None:
    Role = apps.get_model("accounts", "Role")
    AccountAuditEvent = apps.get_model("accounts", "AccountAuditEvent")

    legacy_roles = Role.objects.exclude(code=RESPONSIBLE_SECTOR_ROLE_CODE).filter(is_active=True)
    for role in legacy_roles:
        role.is_active = False
        role.version += 1
        role.save(update_fields=("is_active", "version", "updated_at"))
        AccountAuditEvent.objects.create(
            event_type="ROLE_UPDATED",
            actor=None,
            target_user=None,
            entity_type="ROLE",
            entity_id=str(role.pk),
            reason="Inativação do catálogo legado pela decisão de papel funcional único.",
            changes={
                "before": {"is_active": True},
                "after": {"is_active": False},
            },
            correlation_id="migration-accounts-0007",
        )


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0006_alter_accountauditevent_event_type"),
    ]

    operations = [
        migrations.RunPython(retire_legacy_roles, migrations.RunPython.noop),
        migrations.AddConstraint(
            model_name="role",
            constraint=models.CheckConstraint(
                condition=(models.Q(code=RESPONSIBLE_SECTOR_ROLE_CODE) | models.Q(is_active=False)),
                name="SGPD_CK_ROLE_ACTIVE_CODE",
            ),
        ),
    ]
