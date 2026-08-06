"""Fast isolated settings for unit tests."""

import os

os.environ.setdefault("DJANGO_SECRET_KEY", "test-only-not-for-runtime")

from .base import *  # noqa: E402,F403

DEBUG = False
# Unit tests never inherit a live or intentionally insecure directory endpoint
# from the developer's local .env. AD behavior is enabled explicitly per test.
LDAP_ENABLED = False
LDAP_AUTHENTICATION_ENABLED = False
PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]
EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"
# Baseline de e-mail fixo pelo mesmo motivo do LDAP: sem isto o resultado da
# suíte dependeria do `.env` da máquina, onde `EMAIL_HOST` pode estar vazio e
# desligar o envio, ou apontar para o SMTP real.
EMAIL_HOST = "smtp.invalid"
EMAIL_PORT = 587
EMAIL_HOST_USER = ""
EMAIL_HOST_PASSWORD = ""
EMAIL_USE_TLS = True
DEFAULT_FROM_EMAIL = "sgpd@example.invalid"
SGPD_BASE_URL = ""
# Transporte, admin e contagem de proxies também são fixados aqui: no host
# publicado o `.env` liga os cookies `Secure`, desliga o admin e declara um
# proxy à frente, e a suíte não pode depender de qual máquina a executa.
SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False
ADMIN_SITE_ENABLED = True
REST_FRAMEWORK = {**REST_FRAMEWORK, "NUM_PROXIES": 0}  # noqa: F405
STORAGES["staticfiles"] = {  # noqa: F405
    "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage",
}

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
    }
}

# A suíte executa a tarefa no próprio processo e propaga a exceção: nenhum teste
# depende de broker de pé, e um erro dentro da tarefa falha o teste em vez de
# sumir no worker. O `.delay()` disparado por `on_commit` continua sendo
# exercido — o que muda é quem executa.
CELERY_TASK_ALWAYS_EAGER = True
CELERY_TASK_EAGER_PROPAGATES = True
# Sem broker configurado: qualquer caminho que tente falar com o Redis na suíte
# falha de imediato, em vez de ficar tentando reconectar.
CELERY_BROKER_URL = "memory://"
