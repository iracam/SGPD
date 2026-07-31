"""Constraints dos montantes passam a admitir o valor ausente.

Cada montante da pretensão nasce em um passo do eixo e os demais permanecem
nulos. No Oracle, `NULL >= 0` é desconhecido: `full_clean()` acusava violação em
toda pretensão ainda não apurada e o eixo de valor não funcionava no DEV, embora
a constraint do banco nunca tenha sido violada (o Oracle não recusa a linha).
A condição passa a dizer o que sempre se quis — ausente ou não negativo —, no
mesmo idioma das demais constraints anuláveis do projeto.
"""

from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("pending_items", "0002_add_pending_amounts_and_decisions"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.RemoveConstraint(
            model_name="pendingamount",
            name="SGPD_CK_PAMOUNT_INFORMED",
        ),
        migrations.RemoveConstraint(
            model_name="pendingamount",
            name="SGPD_CK_PAMOUNT_ASSESSED",
        ),
        migrations.RemoveConstraint(
            model_name="pendingamount",
            name="SGPD_CK_PAMOUNT_CONTESTED",
        ),
        migrations.RemoveConstraint(
            model_name="pendingamount",
            name="SGPD_CK_PAMOUNT_APPROVED",
        ),
        migrations.RemoveConstraint(
            model_name="pendingamount",
            name="SGPD_CK_PAMOUNT_PROCESSED",
        ),
        migrations.AddConstraint(
            model_name="pendingamount",
            constraint=models.CheckConstraint(
                condition=models.Q(
                    ("amount_informed__isnull", True),
                    ("amount_informed__gte", 0),
                    _connector="OR",
                ),
                name="SGPD_CK_PAMOUNT_INFORMED",
            ),
        ),
        migrations.AddConstraint(
            model_name="pendingamount",
            constraint=models.CheckConstraint(
                condition=models.Q(
                    ("amount_assessed__isnull", True),
                    ("amount_assessed__gte", 0),
                    _connector="OR",
                ),
                name="SGPD_CK_PAMOUNT_ASSESSED",
            ),
        ),
        migrations.AddConstraint(
            model_name="pendingamount",
            constraint=models.CheckConstraint(
                condition=models.Q(
                    ("amount_contested__isnull", True),
                    ("amount_contested__gte", 0),
                    _connector="OR",
                ),
                name="SGPD_CK_PAMOUNT_CONTESTED",
            ),
        ),
        migrations.AddConstraint(
            model_name="pendingamount",
            constraint=models.CheckConstraint(
                condition=models.Q(
                    ("amount_approved__isnull", True),
                    ("amount_approved__gte", 0),
                    _connector="OR",
                ),
                name="SGPD_CK_PAMOUNT_APPROVED",
            ),
        ),
        migrations.AddConstraint(
            model_name="pendingamount",
            constraint=models.CheckConstraint(
                condition=models.Q(
                    ("amount_processed__isnull", True),
                    ("amount_processed__gte", 0),
                    _connector="OR",
                ),
                name="SGPD_CK_PAMOUNT_PROCESSED",
            ),
        ),
    ]
