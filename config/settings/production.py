"""Settings do host publicado atrás do proxy corporativo.

O proxy roda em outro host, termina o TLS de `sgpd.bsabioenergia.com.br` e
repassa `X-Forwarded-Proto` e `X-Forwarded-For`. Este módulo assume esse
contrato: o que protege dado pessoal fica fixo no código e não depende de o
`.env` estar certo.
"""

from django.core.exceptions import ImproperlyConfigured

from .base import *  # noqa: F403
from .oracle import init_thick_client, oracle_database

if env_bool("DJANGO_DEBUG"):  # noqa: F405
    raise ImproperlyConfigured(
        "DJANGO_DEBUG não pode estar ligado no host publicado: a página de erro do "
        "Django expõe settings e variáveis locais de cada requisição."
    )

DEBUG = False

# 50 é o piso do `check --deploy`. A chave também deriva o Fernet que cifra os
# segredos da central de configurações (apps/system_settings/crypto.py), então
# uma chave fraca aqui enfraquece a senha de bind do AD e a do SMTP.
if len(SECRET_KEY) < 50:  # noqa: F405
    raise ImproperlyConfigured(
        "DJANGO_SECRET_KEY precisa ter ao menos 50 caracteres aleatórios no host publicado."
    )

init_thick_client()

DATABASES = {
    "default": oracle_database(env_int("SGPD_DB_CONN_MAX_AGE", 60)),  # noqa: F405
}

# O TLS termina no proxy; sem esta linha `request.is_secure()` seria sempre
# falso e o Django entraria em laço de redirecionamento.
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True

SECURE_SSL_REDIRECT = True
# O proxy sonda a saúde da aplicação em HTTP direto; sem a isenção ele receberia
# 301 em vez do 200/503 que precisa avaliar.
SECURE_REDIRECT_EXEMPT = [r"^health/"]

SECURE_HSTS_SECONDS = env_int("SECURE_HSTS_SECONDS", 3600)  # noqa: F405
SECURE_HSTS_INCLUDE_SUBDOMAINS = env_bool("SECURE_HSTS_INCLUDE_SUBDOMAINS", False)  # noqa: F405
SECURE_HSTS_PRELOAD = False

ADMIN_SITE_ENABLED = env_bool("DJANGO_ADMIN_ENABLED", False)  # noqa: F405

# Releitura de disco a cada requisição só faz sentido enquanto se desenvolve.
WHITENOISE_AUTOREFRESH = False
WHITENOISE_USE_FINDERS = False
