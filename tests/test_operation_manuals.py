"""Serving contract of the operational manuals opened by the SPA help link."""

from __future__ import annotations

from pathlib import Path

import pytest
from django.test import Client

from apps.accounts.models import User
from apps.core.views import OPERATION_MANUALS

pytestmark = pytest.mark.django_db


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
