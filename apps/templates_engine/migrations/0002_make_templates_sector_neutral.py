from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("templates_engine", "0001_initial"),
    ]

    operations = [
        migrations.RemoveIndex(
            model_name="checklisttemplate",
            name="SGPD_IX_TPL_SECTOR",
        ),
        migrations.RemoveField(
            model_name="checklisttemplate",
            name="sector",
        ),
    ]
