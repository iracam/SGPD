"""DEV settings backed by the SGPD Oracle schema."""

from django.core.exceptions import ImproperlyConfigured

from .base import *  # noqa: F403
from .oracle import init_thick_client, oracle_database

if not SECRET_KEY:  # noqa: F405
    raise ImproperlyConfigured("A variável DJANGO_SECRET_KEY é obrigatória no ambiente DEV.")

init_thick_client()

DATABASES = {
    "default": oracle_database(env_int("SGPD_DB_CONN_MAX_AGE", 60)),  # noqa: F405
}
