"""SGPD project configuration."""

# A instância precisa existir no import do pacote para que `shared_task` tenha
# app corrente: sem isto, um `.delay()` disparado de dentro da requisição não
# encontraria broker (ADR-057).
from .celery import app as celery_app

__all__ = ("celery_app",)
