from typing import Any

from django.db import migrations, models


def normalize_template_codes(apps: Any, schema_editor: Any) -> None:
    template_model = apps.get_model("templates_engine", "ChecklistTemplate")
    template_model.objects.update(code=None)
    for template in template_model.objects.order_by("pk").iterator():
        template.code = str(template.pk)
        template.save(update_fields=("code",))


class Migration(migrations.Migration):
    dependencies = [
        ("templates_engine", "0002_make_templates_sector_neutral"),
    ]

    operations = [
        migrations.AlterField(
            model_name="checklisttemplate",
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
            name="checklisttemplate",
            options={
                "ordering": ("name", "pk"),
                "verbose_name": "template de checklist",
                "verbose_name_plural": "templates de checklist",
            },
        ),
        migrations.AlterModelOptions(
            name="checklisttemplateversion",
            options={
                "ordering": ("template_id", "-version_number"),
                "verbose_name": "versão de template",
                "verbose_name_plural": "versões de templates",
            },
        ),
        migrations.RemoveConstraint(
            model_name="checklisttemplate",
            name="SGPD_CK_TPL_REQUIRED",
        ),
        migrations.AddConstraint(
            model_name="checklisttemplate",
            constraint=models.CheckConstraint(
                condition=models.Q(("name__isnull", False), ("version__gt", 0)),
                name="SGPD_CK_TPL_REQUIRED",
            ),
        ),
        migrations.RunPython(
            normalize_template_codes,
            reverse_code=migrations.RunPython.noop,
        ),
        migrations.AlterField(
            model_name="workflowconfigurationauditevent",
            name="event_type",
            field=models.CharField(
                choices=[
                    ("TEMPLATE_CREATED", "Template criado"),
                    ("TPL_VERSION_CREATED", "Versão de template criada"),
                    ("TPL_DRAFT_UPDATED", "Rascunho de template alterado"),
                    ("TEMPLATE_PUBLISHED", "Template publicado"),
                    ("GROUP_CREATED", "Grupo criado"),
                    ("GROUP_VERSION_CREATED", "Versão de grupo criada"),
                    ("GROUP_PUBLISHED", "Grupo publicado"),
                ],
                max_length=30,
                verbose_name="tipo do evento",
            ),
        ),
    ]
