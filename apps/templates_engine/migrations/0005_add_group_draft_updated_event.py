from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("templates_engine", "0004_use_automatic_group_and_question_codes"),
    ]

    operations = [
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
                    ("GROUP_DRAFT_UPDATED", "Rascunho de grupo alterado"),
                    ("GROUP_PUBLISHED", "Grupo publicado"),
                ],
                max_length=30,
                verbose_name="tipo do evento",
            ),
        ),
    ]
