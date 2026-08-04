"""Serving contract of the operational manuals opened by the SPA help link."""

from __future__ import annotations

import re
from pathlib import Path

import pytest
from django.test import Client

from apps.accounts.models import User
from apps.core.views import OPERATION_MANUALS

pytestmark = pytest.mark.django_db

#: `<app-ajuda-link manual="…" secao="…">` como a SPA o escreve, em uma ou mais
#: linhas. `secao` é opcional: sem ela o manual abre na capa.
AJUDA_LINK = re.compile(
    r"<app-ajuda-link\b(?P<atributos>[^>]*)>",
    re.DOTALL,
)


@pytest.fixture
def manuais(tmp_path: Path, settings: pytest.FixtureRequest) -> Path:
    for slug in OPERATION_MANUALS:
        (tmp_path / f"{slug}.html").write_text(
            f"<!doctype html><h1>{slug}</h1>",
            encoding="utf-8",
        )
    settings.OPERATION_MANUALS_DIR = tmp_path  # type: ignore[attr-defined]
    return tmp_path


@pytest.fixture
def usuario() -> User:
    return User.objects.create_user(
        username="ajuda.leitor",
        email="ajuda.leitor@example.invalid",
        password="Ajuda-leitor-test!2026",
    )


def test_authenticated_user_reads_each_manual(manuais: Path, usuario: User) -> None:
    client = Client()
    client.force_login(usuario)

    for slug in OPERATION_MANUALS:
        response = client.get(f"/ajuda/{slug}/")

        assert response.status_code == 200, slug
        assert response["Content-Type"].startswith("text/html")
        assert slug.encode() in response.content


def test_anonymous_is_sent_to_the_login_instead_of_the_document(manuais: Path) -> None:
    # O manual descreve o processo interno inteiro; servir sem sessão o
    # transformaria em documento público.
    response = Client().get("/ajuda/responsaveis-de-area/")

    assert response.status_code == 302
    assert response["Location"] == "/fe/login"


def test_anonymous_cannot_probe_which_manuals_exist(manuais: Path) -> None:
    # Slug inexistente e slug real respondem igual para quem não entrou.
    response = Client().get("/ajuda/inexistente/")

    assert response.status_code == 302
    assert response["Location"] == "/fe/login"


def test_unknown_slug_is_404_for_authenticated_user(manuais: Path, usuario: User) -> None:
    client = Client()
    client.force_login(usuario)

    response = client.get("/ajuda/inexistente/")

    assert response.status_code == 404
    assert b"<app-root>" not in response.content


@pytest.mark.parametrize(
    "caminho",
    [
        "/ajuda/../settings/base/",
        "/ajuda/..%2f..%2fmanage/",
        "/ajuda/responsaveis-de-area.html/",
    ],
)
def test_path_traversal_never_reaches_the_filesystem(
    manuais: Path,
    usuario: User,
    caminho: str,
) -> None:
    # O caminho no disco vem da lista branca, nunca da URL: qualquer coisa fora
    # dela morre antes de virar `Path`.
    client = Client()
    client.force_login(usuario)

    response = client.get(caminho)

    assert response.status_code in {301, 404}
    assert b"<!doctype html><h1>" not in response.content


def test_missing_file_reports_503_instead_of_crashing(
    tmp_path: Path,
    settings: pytest.FixtureRequest,
    usuario: User,
) -> None:
    settings.OPERATION_MANUALS_DIR = tmp_path / "ausente"  # type: ignore[attr-defined]
    client = Client()
    client.force_login(usuario)

    response = client.get("/ajuda/responsaveis-de-area/")

    assert response.status_code == 503
    assert "build.mjs" in response.content.decode()


def test_manual_is_revalidated_so_a_rebuild_reaches_the_reader(
    manuais: Path,
    usuario: User,
) -> None:
    client = Client()
    client.force_login(usuario)

    response = client.get("/ajuda/departamento-pessoal/")

    assert "no-cache" in response["Cache-Control"]
    assert "private" in response["Cache-Control"]


def test_help_route_is_not_swallowed_by_the_spa_catch_all(
    manuais: Path,
    usuario: User,
) -> None:
    # Sem a exclusão no catch-all, `/ajuda/...` devolveria o shell do Angular
    # com 200 e o manual nunca apareceria.
    client = Client()
    client.force_login(usuario)

    response = client.get("/ajuda/grupos-templates-regras/")

    assert b"<app-root>" not in response.content


def test_every_published_manual_exists_in_the_repository() -> None:
    # A lista branca e os arquivos gerados precisam andar juntos: um slug sem
    # arquivo vira 503 na cara de quem pediu ajuda.
    from django.conf import settings as django_settings

    for slug in OPERATION_MANUALS:
        caminho = django_settings.OPERATION_MANUALS_DIR / f"{slug}.html"
        assert caminho.is_file(), f"gere {caminho} com `node docs/operacao/build.mjs`"


def _links_de_ajuda_da_spa() -> list[tuple[Path, str, str]]:
    raiz = Path(__file__).resolve().parent.parent / "frontend" / "src" / "app"
    encontrados: list[tuple[Path, str, str]] = []
    for template in sorted(raiz.rglob("*.html")):
        for ocorrencia in AJUDA_LINK.finditer(template.read_text(encoding="utf-8")):
            atributos = ocorrencia.group("atributos")
            manual = re.search(r'manual="([^"]+)"', atributos)
            if manual is None:
                continue
            secao = re.search(r'secao="([^"]+)"', atributos)
            encontrados.append((template, manual.group(1), secao.group(1) if secao else ""))
    return encontrados


def test_the_spa_only_asks_for_manuals_that_exist() -> None:
    links = _links_de_ajuda_da_spa()

    assert links, "nenhum <app-ajuda-link> encontrado: o casamento abaixo perderia sentido"
    for template, slug, _ in links:
        assert slug in OPERATION_MANUALS, f"{template.name} pede o manual inexistente {slug!r}"


def test_every_screen_anchor_still_exists_in_the_generated_manual() -> None:
    # A ADR-053 registra a armadilha: renomear um título muda o `id` e o link
    # continua válido, abrindo o manual na capa. Só um teste percebe isso.
    from django.conf import settings as django_settings

    gerados: dict[str, set[str]] = {}
    for template, slug, secao in _links_de_ajuda_da_spa():
        if not secao:
            continue
        if slug not in gerados:
            html = (django_settings.OPERATION_MANUALS_DIR / f"{slug}.html").read_text(
                encoding="utf-8"
            )
            gerados[slug] = set(re.findall(r'<h[1-4] id="([^"]+)"', html))
        assert secao in gerados[slug], (
            f"{template.name} aponta para {slug}#{secao}, que não existe no manual gerado — "
            "confira se a seção foi renomeada"
        )
