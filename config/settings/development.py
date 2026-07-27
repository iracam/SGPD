"""DEV settings backed by the SGPD Oracle schema."""

import os

import oracledb
from django.core.exceptions import ImproperlyConfigured

from .base import *  # noqa: F403


def required_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise ImproperlyConfigured(f"A variável {name} é obrigatória no ambiente DEV.")
    return value


if not SECRET_KEY:  # noqa: F405
    raise ImproperlyConfigured("A variável DJANGO_SECRET_KEY é obrigatória no ambiente DEV.")

oracle_client_lib_dir = required_env("ORACLE_CLIENT_LIB_DIR")
try:
    oracledb.init_oracle_client(lib_dir=oracle_client_lib_dir)
except oracledb.Error as exc:
    raise ImproperlyConfigured(
        "Não foi possível inicializar o Oracle Client em modo Thick."
    ) from exc

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.oracle",
        "NAME": required_env("SGPD_DB_NAME"),
        "USER": required_env("SGPD_DB_USER"),
        "PASSWORD": required_env("SGPD_DB_PASSWORD"),
        "CONN_MAX_AGE": env_int("SGPD_DB_CONN_MAX_AGE", 60),  # noqa: F405
        "CONN_HEALTH_CHECKS": True,
    }
}
