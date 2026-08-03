"""Bootstrap da conexão Oracle, compartilhado pelos ambientes que a utilizam.

O owner `SGPD` é a conexão única do ambiente (ADR-022): DEV e o host publicado
apontam para o mesmo schema, então a construção do `DATABASES` mora aqui em vez
de ser duplicada em cada módulo de settings.
"""

import os
from typing import Any

import oracledb
from django.core.exceptions import ImproperlyConfigured


def required_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise ImproperlyConfigured(f"A variável {name} é obrigatória neste ambiente.")
    return value


def init_thick_client() -> None:
    lib_dir = required_env("ORACLE_CLIENT_LIB_DIR")
    try:
        oracledb.init_oracle_client(lib_dir=lib_dir)
    except oracledb.Error as exc:
        raise ImproperlyConfigured(
            "Não foi possível inicializar o Oracle Client em modo Thick."
        ) from exc


def oracle_database(conn_max_age: int = 60) -> dict[str, Any]:
    return {
        "ENGINE": "django.db.backends.oracle",
        "NAME": required_env("SGPD_DB_NAME"),
        "USER": required_env("SGPD_DB_USER"),
        "PASSWORD": required_env("SGPD_DB_PASSWORD"),
        "CONN_MAX_AGE": conn_max_age,
        "CONN_HEALTH_CHECKS": True,
    }
