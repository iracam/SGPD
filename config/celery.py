"""Runtime assíncrono do SGPD (ADR-057).

O worker executa as tarefas e o Beat dispara a agenda periódica, no lugar do
agendador do sistema operacional. O broker carrega apenas o sinal de trabalho:
a fila durável continua sendo `SGPD_NOTIFICATION`, no Oracle, gravada na mesma
transação do fato que a originou (ADR-049).

A agenda é estática de propósito. Mudar o ritmo do sistema é decisão de
engenharia, revisável por diff; o que a operação ajusta — tentativas, tamanho
do lote e janela de reabertura — já vive na central de configuração (ADR-050).
"""

from __future__ import annotations

import os
from typing import Any

from celery import Celery

from .bootstrap import configure_settings_module

configure_settings_module()

#: O Celery lê estas duas do ambiente e elas vencem o módulo de settings, em
#: silêncio. Um `.env` antigo já apontou o backend de resultado para o índice do
#: cache por esse caminho. Aqui o conflito para de ser silencioso: o endereço do
#: Redis vem de `SGPD_REDIS_URL` e de mais lugar nenhum.
CELERY_ENV_OVERRIDES = ("CELERY_BROKER_URL", "CELERY_RESULT_BACKEND")

_conflicting = [name for name in CELERY_ENV_OVERRIDES if os.getenv(name)]
if _conflicting:
    raise RuntimeError(
        f"{', '.join(_conflicting)} definida(s) no ambiente sobrepõe(m) o módulo de "
        "settings sem aviso. Remova do `.env` e configure o Redis por "
        "SGPD_REDIS_URL, SGPD_REDIS_BROKER_DB e SGPD_REDIS_CACHE_DB (ADR-057)."
    )

app = Celery("sgpd")
# Namespace `CELERY_`: a configuração do worker mora junto com a do Django, em
# `config/settings/`, e não em um arquivo paralelo com regras próprias.
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()


@app.on_after_configure.connect
def register_periodic_tasks(sender: Celery, **_kwargs: Any) -> None:
    """Declara a agenda do Beat pelos nomes das tarefas.

    Referência por nome, e não por importação, para que este módulo continue
    subindo antes de qualquer app do Django estar carregada.
    """

    from django.conf import settings

    sender.conf.beat_schedule = {
        # Enfileira lembretes, atrasos e escaladas. Idempotente por chave de
        # deduplicação: rodar mais vezes muda a latência do aviso, nunca a
        # quantidade.
        "notificacoes-varrer-prazos": {
            "task": "apps.notifications.scan_deadlines",
            "schedule": float(settings.SGPD_BEAT_SCAN_SECONDS),
        },
        # Rede de segurança do despacho imediato: recolhe o que o `on_commit`
        # não conseguiu agendar, o que falhou e voltou para a fila com backoff,
        # e o que ficou preso em `ENVIANDO`.
        "notificacoes-despachar-fila": {
            "task": "apps.notifications.dispatch_queue",
            "schedule": float(settings.SGPD_BEAT_DISPATCH_SECONDS),
        },
        # Batimento da sonda: é o que permite ao processo web dizer que o
        # agendamento parou (R63).
        "operacao-sondar": {
            "task": "apps.reporting.operations_check",
            "schedule": float(settings.SGPD_BEAT_OPERATIONS_SECONDS),
        },
    }
