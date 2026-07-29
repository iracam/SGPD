from typing import Any

from django.db import migrations, models


def normalize_automatic_codes(apps: Any, schema_editor: Any) -> None:
    group_model = apps.get_model("templates_engine", "ValidationGroup")
    item_model = apps.get_model("templates_engine", "ChecklistTemplateItem")

    group_model.objects.update(code=None)
    for group in group_model.objects.order_by("pk").iterator():
        group.code = str(group.pk)
        group.save(update_fields=("code",))

    item_model.objects.update(code=None)
    for item in item_model.objects.order_by("pk").iterator():
        item.code = str(item.pk)
        item.save(update_fields=("code",))


class Migration(migrations.Migration):
    dependencies = [
        ("templates_engine", "0003_use_numeric_template_identifier_and_edit_drafts"),
    ]

    operations = [
        migrations.RemoveConstraint(
            model_name="checklisttemplateitem",
            name="SGPD_CK_TPL_ITEM_REQ",
        ),
        migrations.RemoveConstraint(
            model_name="validationgroup",
            name="SGPD_CK_GROUP_REQUIRED",
        ),
        migrations.AlterField(
            model_name="checklisttemplateitem",
            name="code",
            field=models.CharField(
                editable=False,
                max_length=50,
                null=True,
                verbose_name="código técnico",
            ),
        ),
        migrations.AlterField(
            model_name="validationgroup",
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
            name="validationgroup",
            options={
                "ordering": ("name", "pk"),
                "permissions": [
                    (
                        "manage_workflow_configuration",
                        "Pode criar e publicar grupos e templates",
                    ),
                ],
                "verbose_name": "grupo de validação",
                "verbose_name_plural": "grupos de validação",
            },
        ),
        migrations.AlterModelOptions(
            name="validationgroupversion",
            options={
                "ordering": ("group_id", "-version_number"),
                "verbose_name": "versão de grupo",
                "verbose_name_plural": "versões de grupos",
            },
        ),
        migrations.RunPython(
            normalize_automatic_codes,
            reverse_code=migrations.RunPython.noop,
        ),
        migrations.AddConstraint(
            model_name="checklisttemplateitem",
            constraint=models.CheckConstraint(
                condition=models.Q(
                    ("display_order__gt", 0),
                    ("question__isnull", False),
                    ("response_type__isnull", False),
                ),
                name="SGPD_CK_TPL_ITEM_REQ",
            ),
        ),
        migrations.AddConstraint(
            model_name="validationgroup",
            constraint=models.CheckConstraint(
                condition=models.Q(
                    ("name__isnull", False),
                    ("version__gt", 0),
                ),
                name="SGPD_CK_GROUP_REQUIRED",
            ),
        ),
    ]
