"""Escolha do módulo de settings antes de o Django subir.

O `.env` precisa ser lido aqui, e não só dentro de `config.settings.base`, para
que `DJANGO_SETTINGS_MODULE` declarado no arquivo tenha efeito: quando o Django
resolve esse nome, os settings ainda não foram importados. Sem isto, o host
publicado e o agendador do sistema continuariam subindo em desenvolvimento.
"""

import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parents[1]
DEFAULT_SETTINGS_MODULE = "config.settings.development"


def configure_settings_module() -> str:
    # `override=False`: uma variável já exportada no ambiente vence o arquivo.
    load_dotenv(BASE_DIR / ".env", override=False)
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", DEFAULT_SETTINGS_MODULE)
    return os.environ["DJANGO_SETTINGS_MODULE"]
