"""Ajusta as fixtures recém-exportadas para que carreguem em qualquer banco.

Dois consertos, ambos consequência de como o `dumpdata` enxerga o Oracle. Rodam
depois de todo despejo e antes de qualquer carga — `scripts/reset_from_fixtures.sh`
já os aplica.

1. **NULL de texto.** O backend Oracle do Django devolve `''` ao ler
   `CharField`/`TextField` nulo, mesmo quando o campo é `null=True`, e o
   `dumpdata` grava esse `''` no JSON. Só o Oracle o reconverte para NULL na
   carga: em qualquer outro banco a string vazia permanece e distorce o dado — o
   par `ad_identifier`/`ad_username` das contas locais quebra
   `SGPD_CK_USER_AD_LINK`, e `job_code`/`cost_center_code` viram filtro por
   string vazia em vez de "sem filtro".

2. **Ordem das chaves naturais.** O `loaddata` resolve uma FK serializada como
   chave natural com uma consulta ao banco, no momento em que lê o objeto: se o
   alvo ainda não foi inserido, a carga falha — e desabilitar a checagem de
   constraint não ajuda, porque a consulta é do desserializador, não do banco.
   `SGPD_USER.ad_linked_by` aponta para outro usuário do mesmo arquivo e o
   `dumpdata` não garante ordem nenhuma: `accounts.User` não declara
   `Meta.ordering` e o Oracle devolve as linhas na ordem que quiser. Hoje o
   despejo sai com `admin` na frente por sorte; este passo tira a sorte do
   caminho.

Uso:

    uv run python scripts/normalize_fixtures.py docs/fixtures/0*.json
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
# Metadado de modelo, não dado: o script lê `_meta` e nunca abre conexão. O
# módulo de teste evita exigir cliente Oracle e `.env` só para isso.
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.test")

import django  # noqa: E402

django.setup()

from django.apps import apps  # noqa: E402
from django.db import models  # noqa: E402

TEXT_FIELDS = (models.CharField, models.TextField)


def nullable_text_fields(label: str) -> set[str]:
    model = apps.get_model(label)
    return {
        field.name
        for field in model._meta.get_fields()
        if isinstance(field, TEXT_FIELDS) and field.null
    }


def restore_nulls(objects: list[dict[str, Any]]) -> int:
    cache: dict[str, set[str]] = {}
    changed = 0
    for obj in objects:
        label = obj["model"]
        if label not in cache:
            cache[label] = nullable_text_fields(label)
        for name in cache[label]:
            if obj["fields"].get(name) == "":
                obj["fields"][name] = None
                changed += 1
    return changed


def self_natural_fks(label: str) -> list[str]:
    """FKs do modelo para si mesmo que o `dumpdata` serializa por chave natural."""

    model = apps.get_model(label)
    if not hasattr(model, "natural_key"):
        return []
    return [
        field.name
        for field in model._meta.get_fields()
        if isinstance(field, models.ForeignKey) and field.related_model is model
    ]


def serialized_natural_key(label: str, obj: dict[str, Any]) -> tuple[Any, ...]:
    """Chave natural de um objeto do JSON, sem tocar no banco.

    A instância é montada só com os campos escalares — o suficiente para
    `natural_key()`, que por definição não depende de relação — e nunca é salva.
    """

    model = apps.get_model(label)
    scalars = {
        field.name: obj["fields"][field.name]
        for field in model._meta.concrete_fields
        if not field.is_relation and field.name in obj["fields"]
    }
    return tuple(model(**scalars).natural_key())


def topological_order(
    slots: list[int], dependencies: dict[int, list[int]], label: str
) -> list[int]:
    """Ordena `slots` de modo que cada dependência venha antes de quem depende."""

    ordered: list[int] = []
    state: dict[int, int] = {}  # 1 = em visita, 2 = pronto

    def visit(index: int) -> None:
        if state.get(index) == 2:
            return
        if state.get(index) == 1:
            # Ciclo (A vincula B e B vincula A). Nenhuma ordem resolve, e
            # inventar uma esconderia o problema: avisa e segue.
            print(f"  aviso: ciclo em {label} na posição {index}", file=sys.stderr)
            return
        state[index] = 1
        for target in dependencies[index]:
            visit(target)
        state[index] = 2
        ordered.append(index)

    for index in slots:
        visit(index)
    return ordered


def order_by_dependency(objects: list[dict[str, Any]]) -> int:
    """Põe o alvo de cada FK por chave natural antes de quem o referencia.

    Reordena apenas as posições já ocupadas pelo modelo em questão: objetos de
    outros modelos ficam onde estão, e a ordem entre arquivos continua sendo a
    numérica dos nomes.
    """

    moved = 0
    fields_cache: dict[str, list[str]] = {}
    for label in dict.fromkeys(obj["model"] for obj in objects):
        if label not in fields_cache:
            fields_cache[label] = self_natural_fks(label)
        fk_names = fields_cache[label]
        if not fk_names:
            continue

        slots = [index for index, obj in enumerate(objects) if obj["model"] == label]
        by_key = {serialized_natural_key(label, objects[index]): index for index in slots}
        dependencies: dict[int, list[int]] = {}
        for index in slots:
            targets = []
            for name in fk_names:
                value = objects[index]["fields"].get(name)
                if not value:
                    continue
                target = by_key.get(tuple(value) if isinstance(value, list) else (value,))
                if target is not None and target != index:
                    targets.append(target)
            dependencies[index] = targets

        ordered = topological_order(slots, dependencies, label)
        if ordered != slots:
            rearranged = [objects[index] for index in ordered]
            for slot, obj in zip(slots, rearranged, strict=True):
                objects[slot] = obj
            moved += sum(1 for before, after in zip(slots, ordered, strict=True) if before != after)
    return moved


def main(paths: list[str]) -> int:
    if not paths:
        print(__doc__, file=sys.stderr)
        return 2

    for path in paths:
        with open(path, encoding="utf-8") as handle:
            objects = json.load(handle)

        nulls = restore_nulls(objects)
        moved = order_by_dependency(objects)

        if nulls or moved:
            with open(path, "w", encoding="utf-8") as handle:
                json.dump(objects, handle, indent=2, ensure_ascii=False)
                handle.write("\n")
        print(f"{path}: {nulls} campo(s) normalizado(s), {moved} objeto(s) reordenado(s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
