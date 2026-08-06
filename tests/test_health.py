from unittest.mock import MagicMock, patch

from django.db import DatabaseError
from django.test import Client


def test_liveness_returns_ok_and_correlation_id(client: Client) -> None:
    response = client.get("/health/live/")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
    assert response.headers["X-Correlation-ID"]


def test_liveness_preserves_safe_correlation_id(client: Client) -> None:
    response = client.get("/health/live/", headers={"X-Correlation-ID": "request-123"})

    assert response.headers["X-Correlation-ID"] == "request-123"


def test_liveness_replaces_unsafe_correlation_id(client: Client) -> None:
    response = client.get("/health/live/", headers={"X-Correlation-ID": "unsafe value"})

    assert response.headers["X-Correlation-ID"] != "unsafe value"


@patch("apps.core.views.connection.cursor")
def test_readiness_returns_ok_when_database_responds(
    cursor_factory: MagicMock,
    client: Client,
) -> None:
    cursor = cursor_factory.return_value.__enter__.return_value
    cursor.fetchone.return_value = (1,)

    response = client.get("/health/ready/")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
    cursor.execute.assert_called_once_with("SELECT 1 FROM DUAL")


@patch("apps.core.views.connection.cursor", side_effect=DatabaseError)
def test_readiness_hides_database_failure(
    cursor_factory: MagicMock,
    client: Client,
) -> None:
    response = client.get("/health/ready/")

    assert response.status_code == 503
    assert response.json() == {"status": "unavailable"}


@patch("apps.core.views.cache.set", side_effect=ConnectionError("Redis fora do ar"))
@patch("apps.core.views.connection.cursor")
def test_readiness_fails_when_the_shared_cache_is_down(
    cursor_factory: MagicMock,
    cache_set: MagicMock,
    client: Client,
) -> None:
    # O limite de tentativas de login vive no cache (ADR-057). Sem ele o
    # controle contra força bruta não é aplicável, e receber tráfego nessa
    # condição seria pior que não receber.
    cursor_factory.return_value.__enter__.return_value.fetchone.return_value = (1,)

    response = client.get("/health/ready/")

    assert response.status_code == 503
    assert response.json() == {"status": "unavailable"}


@patch("apps.core.views.cache.get", return_value=None)
@patch("apps.core.views.connection.cursor")
def test_readiness_fails_when_the_cache_does_not_return_what_it_stored(
    cursor_factory: MagicMock,
    cache_get: MagicMock,
    client: Client,
) -> None:
    # Cache que aceita a escrita e não devolve a leitura não está servindo.
    cursor_factory.return_value.__enter__.return_value.fetchone.return_value = (1,)

    response = client.get("/health/ready/")

    assert response.status_code == 503
    assert response.json() == {"status": "unavailable"}
