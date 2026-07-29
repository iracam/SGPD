from collections import defaultdict
from typing import Any

from django.db import migrations, models


def validate_scope_inheritance(apps: Any, schema_editor: Any) -> None:
    SectorResponsible = apps.get_model("sectors", "SectorResponsible")
    SectorScope = apps.get_model("sectors", "SectorScope")

    sector_scopes: dict[int, set[str]] = defaultdict(set)
    for sector_id, scope_key in SectorScope.objects.values_list("sector_id", "scope_key"):
        sector_scopes[sector_id].add(scope_key)

    links_by_pair: dict[tuple[int, int], list[Any]] = defaultdict(list)
    for link in SectorResponsible.objects.all().order_by("pk").iterator():
        links_by_pair[(link.sector_id, link.user_id)].append(link)

    duplicates = [pair for pair, links in links_by_pair.items() if len(links) > 1]
    if duplicates:
        sector_id, user_id = sorted(duplicates)[0]
        raise RuntimeError(
            "A migração não pode consolidar automaticamente múltiplos escopos "
            f"do vínculo setor={sector_id}, usuário={user_id}."
        )

    for (sector_id, user_id), links in links_by_pair.items():
        link_scopes = {links[0].scope_key}
        if link_scopes != sector_scopes.get(sector_id, set()):
            raise RuntimeError(
                "O escopo atual do responsável difere do escopo do setor; "
                "revise antes de herdar automaticamente: "
                f"setor={sector_id}, usuário={user_id}."
            )


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0009_derive_sector_responsible_role"),
        ("sectors", "0002_alter_sectorauditevent_event_type_sectorresponsible"),
    ]

    operations = [
        migrations.RunPython(
            validate_scope_inheritance,
            migrations.RunPython.noop,
        ),
        migrations.AlterModelOptions(
            name="sectorresponsible",
            options={
                "ordering": ("sector__code", "user__username"),
                "verbose_name": "responsável de setor",
                "verbose_name_plural": "responsáveis de setores",
            },
        ),
        migrations.RemoveConstraint(
            model_name="sectorresponsible",
            name="SGPD_UQ_SECTOR_RESP_SCOPE",
        ),
        migrations.RemoveConstraint(
            model_name="sectorresponsible",
            name="SGPD_CK_SECTOR_RESP_SCOPE",
        ),
        migrations.RemoveConstraint(
            model_name="sectorresponsible",
            name="SGPD_CK_SECTOR_RESP_REQ",
        ),
        migrations.RemoveConstraint(
            model_name="sectorresponsible",
            name="SGPD_CK_SECTOR_RESP_CODES",
        ),
        migrations.RemoveIndex(
            model_name="sectorresponsible",
            name="SGPD_IX_RESP_ORG",
        ),
        migrations.RemoveField(
            model_name="sectorresponsible",
            name="branch_code",
        ),
        migrations.RemoveField(
            model_name="sectorresponsible",
            name="company_code",
        ),
        migrations.RemoveField(
            model_name="sectorresponsible",
            name="scope_key",
        ),
        migrations.RemoveField(
            model_name="sectorresponsible",
            name="scope_type",
        ),
        migrations.AddConstraint(
            model_name="sectorresponsible",
            constraint=models.UniqueConstraint(
                fields=("sector", "user"),
                name="SGPD_UQ_SECTOR_RESP_USER",
            ),
        ),
        migrations.AddConstraint(
            model_name="sectorresponsible",
            constraint=models.CheckConstraint(
                condition=models.Q(
                    assigned_by__isnull=False,
                    updated_by__isnull=False,
                ),
                name="SGPD_CK_SECTOR_RESP_REQ",
            ),
        ),
    ]
