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

# Mesmo cache do host publicado (ADR-057): o limite de tentativas de login e o
# batimento do agendador precisam ser visíveis entre o processo web, o worker e
# o Beat, que são processos diferentes também no desenvolvimento.
CACHES = redis_cache()  # noqa: F405
