"""Serving contract of the Angular shell from Django."""

from __future__ import annotations

from pathlib import Path

import pytest
from django.test import Client

pytestmark = pytest.mark.django_db


@pytest.fixture
def bundle(tmp_path: Path, settings: pytest.FixtureRequest) -> Path:
    index = tmp_path / "index.html"
    index.write_text("<!doctype html><app-root></app-root>", encoding="utf-8")
    settings.FRONTEND_INDEX = index  # type: ignore[attr-defined]
    return index


def test_root_serves_the_shell_and_seeds_the_csrf_cookie(bundle: Path) -> None:
    response = Client().get("/")

    assert response.status_code == 200
    assert response["Content-Type"].startswith("text/html")
    assert b"<app-root>" in response.content
    assert "csrftoken" in response.cookies


def test_shell_is_never_cached(bundle: Path) -> None:
    # The bundle references hashed assets that change on every build.
    response = Client().get("/")

    assert "no-store" in response["Cache-Control"]


def test_client_side_routes_fall_back_to_the_shell(bundle: Path) -> None:
    for route in ("/fe/painel", "/fe/login", "/fe/usuarios/42"):
        response = Client().get(route)

        assert response.status_code == 200, route
        assert b"<app-root>" in response.content


@pytest.mark.parametrize(
    "route",
    [
        "/api/v1/auth/inexistente/",
        "/api/v1/accounts/inexistente/",
        "/api/v1/references/inexistente/",
    ],
)
def test_unknown_api_routes_return_404_instead_of_the_shell(bundle: Path, route: str) -> None:
    # Without the negative lookahead in the catch-all these would answer 200
    # with HTML, turning a typo into a silent success for API clients.
    response = Client().get(route)

    assert response.status_code == 404
    assert b"<app-root>" not in response.content


def test_health_endpoints_are_not_shadowed_by_the_shell(bundle: Path) -> None:
    response = Client().get("/health/live/")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_missing_bundle_reports_503_instead_of_crashing(
    tmp_path: Path,
    settings: pytest.FixtureRequest,
) -> None:
    settings.FRONTEND_INDEX = tmp_path / "ausente.html"  # type: ignore[attr-defined]

    response = Client().get("/")

    assert response.status_code == 503
    assert "npm" in response.content.decode()
