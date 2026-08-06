"""Postura de segurança do módulo de settings do host publicado.

O host atende `sgpd.bsabioenergia.com.br` por um proxy que roda em outro
servidor e termina o TLS. O que protege dado pessoal nesse cenário não pode
depender de o `.env` estar correto, então cada trava é verificada aqui.
"""

from __future__ import annotations

import importlib
import sys
from collections.abc import Callable, Iterator
from types import ModuleType
from typing import Any

import pytest
from django.core.exceptions import ImproperlyConfigured

MODULE = "config.settings.production"
STRONG_KEY = "k" * 60


@pytest.fixture
def load_production(monkeypatch: pytest.MonkeyPatch) -> Iterator[Any]:
    def _load(
        _patch_base: Callable[[ModuleType], None] | None = None,
        **overrides: str,
    ) -> ModuleType:
        # O cliente Oracle Thick não existe na suíte, e o que se verifica aqui
        # é a postura de segurança, não a conexão.
        monkeypatch.setattr("config.settings.oracle.init_thick_client", lambda: None)
        environment = {
            "DJANGO_DEBUG": "false",
            "DJANGO_SECRET_KEY": STRONG_KEY,
            "SGPD_DB_NAME": "banco-de-teste",
            "SGPD_DB_USER": "sgpd",
            "SGPD_DB_PASSWORD": "senha-de-teste",
        }
        environment.update(overrides)
        for name, value in environment.items():
            monkeypatch.setenv(name, value)
        # `base` guarda os valores lidos do ambiente no momento do import, e a
        # suíte já o carregou pelos settings de teste.
        for name in (MODULE, "config.settings.base"):
            sys.modules.pop(name, None)
        base = importlib.import_module("config.settings.base")
        # O gancho existe para exercer o que o ambiente não alcança: `base` é
        # reimportado a cada carga, então substituir algo nele só vale depois
        # desta linha e antes de `production` fazer o `import *`.
        if _patch_base is not None:
            _patch_base(base)
        return importlib.import_module(MODULE)

    yield _load

    for name in (MODULE, "config.settings.base"):
        sys.modules.pop(name, None)


def test_debug_is_off_and_cannot_be_turned_back_on(load_production: Any) -> None:
    settings = load_production()

    assert settings.DEBUG is False

    with pytest.raises(ImproperlyConfigured, match="DJANGO_DEBUG"):
        load_production(DJANGO_DEBUG="true")


def test_a_weak_secret_key_refuses_to_boot(load_production: Any) -> None:
    # A chave também deriva a cifra dos segredos da central de configurações.
    with pytest.raises(ImproperlyConfigured, match="DJANGO_SECRET_KEY"):
        load_production(DJANGO_SECRET_KEY="curta-demais")


def test_cookies_carry_the_secure_flag(load_production: Any) -> None:
    settings = load_production()

    assert settings.SESSION_COOKIE_SECURE is True
    assert settings.CSRF_COOKIE_SECURE is True
    assert settings.SESSION_COOKIE_HTTPONLY is True


def test_the_proxy_terminating_tls_is_recognized(load_production: Any) -> None:
    settings = load_production()

    assert settings.SECURE_PROXY_SSL_HEADER == ("HTTP_X_FORWARDED_PROTO", "https")
    assert settings.SECURE_SSL_REDIRECT is True
    # A sonda de saúde do proxy chega em HTTP e precisa do status, não de um 301.
    assert settings.SECURE_REDIRECT_EXEMPT == [r"^health/"]
    assert settings.SECURE_HSTS_SECONDS > 0


def test_the_read_only_admin_is_off_by_default(load_production: Any) -> None:
    # O login do Admin não passa pelo limite de tentativas do DRF.
    assert load_production().ADMIN_SITE_ENABLED is False
    assert load_production(DJANGO_ADMIN_ENABLED="true").ADMIN_SITE_ENABLED is True


def test_the_login_throttle_cache_is_shared_between_processes(load_production: Any) -> None:
    # O limite de tentativas de login mora no cache. Compartilhado, ele é um
    # número só para todos os processos — é o que a ADR-057 destravou.
    settings = load_production()

    backend = settings.CACHES["default"]["BACKEND"]
    assert "locmem" not in backend
    assert backend.endswith("redis.RedisCache")
    # O Redis é de outras aplicações também: sem prefixo, uma chave de nome
    # comum atravessaria sistemas.
    assert settings.CACHES["default"]["KEY_PREFIX"] == "sgpd"
    # Broker e cache em índices distintos, para que um `FLUSHDB` de manutenção
    # em um não leve o outro junto.
    assert settings.CACHES["default"]["LOCATION"] != settings.CELERY_BROKER_URL


def test_more_than_one_worker_boots_with_the_shared_cache(load_production: Any) -> None:
    assert load_production(WEB_CONCURRENCY="4").WEB_CONCURRENCY == 4


def test_more_than_one_worker_still_refuses_a_per_process_cache(load_production: Any) -> None:
    # A trava continua de pé para quem voltar o cache para o processo: dois
    # workers dobrariam a taxa efetiva do controle contra força bruta.
    def force_local_cache(base: ModuleType) -> None:
        base.redis_cache = lambda: {  # type: ignore[attr-defined]
            "default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}
        }

    with pytest.raises(ImproperlyConfigured, match="WEB_CONCURRENCY"):
        load_production(force_local_cache, WEB_CONCURRENCY="2")


def test_static_assets_are_not_reread_from_disk_on_every_request(load_production: Any) -> None:
    settings = load_production()

    assert settings.WHITENOISE_AUTOREFRESH is False
    assert settings.WHITENOISE_USE_FINDERS is False
