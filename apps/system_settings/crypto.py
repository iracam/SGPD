"""Authenticated encryption for secrets persisted by the configuration UI."""

from __future__ import annotations

import base64
import hashlib

from cryptography.fernet import Fernet, InvalidToken
from django.conf import settings

from .exceptions import ConfigurationSecretError

_CONTEXT = b"sgpd-system-settings-v1"


def _cipher() -> Fernet:
    secret_key = str(getattr(settings, "SECRET_KEY", ""))
    if not secret_key:
        raise ConfigurationSecretError(
            "DJANGO_SECRET_KEY é obrigatória para proteger segredos de configuração."
        )
    key = hashlib.sha256(secret_key.encode("utf-8") + b":" + _CONTEXT).digest()
    return Fernet(base64.urlsafe_b64encode(key))


def encrypt_secret(value: str) -> str:
    if not value:
        raise ConfigurationSecretError("O segredo de configuração não pode ser vazio.")
    return _cipher().encrypt(value.encode("utf-8")).decode("ascii")


def decrypt_secret(value: str) -> str:
    if not value:
        return ""
    try:
        return _cipher().decrypt(value.encode("ascii")).decode("utf-8")
    except (InvalidToken, UnicodeDecodeError, ValueError) as exc:
        raise ConfigurationSecretError(
            "O segredo LDAP armazenado não pôde ser decifrado com a chave atual."
        ) from exc
