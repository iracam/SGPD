from typing import Any

from django.db import migrations, models
from django.utils import timezone

RESPONSIBLE_SECTOR_ROLE_CODE = "RESPONSAVEL_SETOR"
PEOPLE_DEPARTMENT_ROLE_CODE = "DP"


def retire_assignable_sector_role(apps: Any, schema_editor: Any) -> None:
    Role = apps.get_model("accounts", "Role")
    RoleAssignment = apps.get_model("accounts", "RoleAssignment")
    AccountAuditEvent = apps.get_model("accounts", "AccountAuditEvent")

    role = Role.objects.filter(code=RESPONSIBLE_SECTOR_ROLE_CODE).first()
    if role is None:
        return

    now = timezone.now()
    assignments = RoleAssignment.objects.filter(role=role, is_active=True).order_by("pk")
    for assignment in assignments.iterator():
        assignment.is_active = False
        assignment.revoked_by_id = assignment.assigned_by_id
        assignment.revoked_at = now
        assignment.save(update_fields=("is_active", "revoked_by", "revoked_at"))
        AccountAuditEvent.objects.create(
            event_type="ROLE_REVOKED",
            actor_id=assignment.assigned_by_id,
            target_user_id=assignment.user_id,
            entity_type="ROLE_ASSIGNMENT",
            entity_id=str(assignment.pk),
            reason=(
                "Revogação técnica da atribuição redundante: a responsabilidade "
                "passou a ser derivada do vínculo com o setor."
            ),
            changes={
                "role": RESPONSIBLE_SECTOR_ROLE_CODE,
                "scope": assignment.scope_key,
                "migration": "accounts-0009",
            },
            correlation_id="migration-accounts-0009",
        )

    if role.is_active:
        role.is_active = False
        role.version += 1
        role.save(update_fields=("is_active", "version", "updated_at"))
        AccountAuditEvent.objects.create(
            event_type="ROLE_UPDATED",
            actor=None,
            target_user=None,
            entity_type="ROLE",
            entity_id=str(role.pk),
            reason=(
                "Inativação do papel atribuível RESPONSAVEL_SETOR; a autorização "
                "passou a ser derivada do vínculo vigente com o setor."
            ),
            changes={
                "before": {"is_active": True},
                "after": {"is_active": False, "derived": True},
                "migration": "accounts-0009",
            },
            correlation_id="migration-accounts-0009",
        )


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0008_two_functional_roles"),
    ]

    operations = [
        migrations.RemoveConstraint(
            model_name="role",
            name="SGPD_CK_ROLE_ACTIVE_CODE",
        ),
        migrations.RunPython(
            retire_assignable_sector_role,
            migrations.RunPython.noop,
        ),
        migrations.AddConstraint(
            model_name="role",
            constraint=models.CheckConstraint(
                condition=(
                    models.Q(code__in=(PEOPLE_DEPARTMENT_ROLE_CODE,)) | models.Q(is_active=False)
                ),
                name="SGPD_CK_ROLE_ACTIVE_CODE",
            ),
        ),
    ]
