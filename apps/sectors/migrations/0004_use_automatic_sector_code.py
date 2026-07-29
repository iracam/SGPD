from typing import Any

from django.db import migrations, models


def normalize_sector_codes(apps: Any, schema_editor: Any) -> None:
    sector_model = apps.get_model("sectors", "ValidationSector")
    sector_model.objects.update(code=None)
    for sector in sector_model.objects.order_by("pk").iterator():
        sector.code = str(sector.pk)
        sector.save(update_fields=("code",))


class Migration(migrations.Migration):
    dependencies = [
        ("sectors", "0003_responsibility_inherits_sector_scope"),
    ]

    operations = [
        migrations.RemoveConstraint(
            model_name="validationsector",
            name="SGPD_CK_SECTOR_REQUIRED",
        ),
        migrations.AlterField(
            model_name="validationsector",
            name="code",
            field=models.CharField(
                editable=False,
                max_length=50,
                null=True,
                unique=True,
                verbose_name="código técnico",
            ),
        ),
        migrations.AlterModelOptions(
            name="validationsector",
            options={
                "ordering": ("name", "pk"),
                "permissions": [
                    ("manage_sectors", "Pode criar e manter setores de validação"),
                ],
                "verbose_name": "setor de validação",
                "verbose_name_plural": "setores de validação",
            },
        ),
        migrations.AlterModelOptions(
            name="sectorresponsible",
            options={
                "ordering": ("sector__name", "sector_id", "user__username"),
                "verbose_name": "responsável de setor",
                "verbose_name_plural": "responsáveis de setores",
            },
        ),
        migrations.RunPython(
            normalize_sector_codes,
            reverse_code=migrations.RunPython.noop,
        ),
        migrations.AddConstraint(
            model_name="validationsector",
            constraint=models.CheckConstraint(
                condition=models.Q(
                    ("default_due_hours__gt", 0),
                    ("name__isnull", False),
                ),
                name="SGPD_CK_SECTOR_REQUIRED",
            ),
        ),
    ]
