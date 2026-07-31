"""Shared Django settings."""

import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parents[2]
load_dotenv(BASE_DIR / ".env", override=False)


def env_bool(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def env_int(name: str, default: int) -> int:
    value = os.getenv(name)
    return int(value) if value else default


def env_list(name: str, default: str = "") -> list[str]:
    value = os.getenv(name, default)
    return [item.strip() for item in value.split(",") if item.strip()]


SECRET_KEY = os.getenv("DJANGO_SECRET_KEY", "")
DEBUG = env_bool("DJANGO_DEBUG")
ALLOWED_HOSTS = env_list("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1")
CSRF_TRUSTED_ORIGINS = env_list("DJANGO_CSRF_TRUSTED_ORIGINS")

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "apps.accounts",
    "apps.core",
    "apps.evidence",
    "apps.integrations",
    "apps.notifications",
    "apps.offboarding",
    "apps.pending_items",
    "apps.reporting",
    "apps.sectors",
    "apps.system_settings",
    "apps.templates_engine",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "config.middleware.CorrelationIdMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "apps.accounts.middleware.PasswordChangeRequiredMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        # Django Admin remains the only server-rendered interface.
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]

AUTH_USER_MODEL = "accounts.User"

LANGUAGE_CODE = "pt-br"
TIME_ZONE = os.getenv("DJANGO_TIME_ZONE", "America/Sao_Paulo")
USE_I18N = True
USE_TZ = True

STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
SYSTEM_CONFIGURATION_STORAGE_PATH = Path(
    os.getenv(
        "SYSTEM_CONFIGURATION_STORAGE_PATH",
        str(BASE_DIR / "media" / "system-configuration"),
    )
)
if not SYSTEM_CONFIGURATION_STORAGE_PATH.is_absolute():
    SYSTEM_CONFIGURATION_STORAGE_PATH = BASE_DIR / SYSTEM_CONFIGURATION_STORAGE_PATH

STORAGES = {
    "default": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
    },
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
    },
    "system_configuration": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
        "OPTIONS": {
            "location": str(SYSTEM_CONFIGURATION_STORAGE_PATH),
            "base_url": None,
            "file_permissions_mode": 0o600,
            "directory_permissions_mode": 0o700,
        },
    },
}
WHITENOISE_AUTOREFRESH = env_bool("WHITENOISE_AUTOREFRESH", DEBUG)
WHITENOISE_USE_FINDERS = env_bool("WHITENOISE_USE_FINDERS", DEBUG)

# Artefatos do `ng build`. Os assets já carregam hash próprio do Angular e são
# servidos na raiz pelo WhiteNoise; o index.html é servido por uma view Django,
# porque o storage com manifesto renomearia o arquivo e quebraria a rota "/".
FRONTEND_DIST_DIR = BASE_DIR / "frontend" / "dist" / "frontend" / "browser"
FRONTEND_INDEX = FRONTEND_DIST_DIR / "index.html"
if FRONTEND_DIST_DIR.is_dir():
    WHITENOISE_ROOT = FRONTEND_DIST_DIR
WHITENOISE_INDEX_FILE = False

EVIDENCE_STORAGE_PATH = Path(
    os.getenv("EVIDENCE_STORAGE_PATH", str(BASE_DIR / "media" / "evidence"))
)
if not EVIDENCE_STORAGE_PATH.is_absolute():
    EVIDENCE_STORAGE_PATH = BASE_DIR / EVIDENCE_STORAGE_PATH
STORAGES["evidence"] = {
    "BACKEND": "django.core.files.storage.FileSystemStorage",
    "OPTIONS": {
        "location": str(EVIDENCE_STORAGE_PATH),
        "base_url": None,
        "file_permissions_mode": 0o600,
        "directory_permissions_mode": 0o700,
    },
}
EVIDENCE_MAX_UPLOAD_BYTES = env_int("EVIDENCE_MAX_UPLOAD_BYTES", 10 * 1024 * 1024)

SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SECURE = env_bool("SESSION_COOKIE_SECURE")
CSRF_COOKIE_SECURE = env_bool("CSRF_COOKIE_SECURE")
X_FRAME_OPTIONS = "DENY"
SECURE_CONTENT_TYPE_NOSNIFF = True

# Backend dinâmico: lê a configuração da central por envio (ADR-050). As
# variáveis abaixo continuam valendo como baseline do primeiro boot.
EMAIL_BACKEND = "apps.notifications.mail.ConfiguredEmailBackend"
EMAIL_HOST = os.getenv("EMAIL_HOST", "")
EMAIL_PORT = env_int("EMAIL_PORT", 587)
EMAIL_HOST_USER = os.getenv("EMAIL_HOST_USER", "")
EMAIL_HOST_PASSWORD = os.getenv("EMAIL_HOST_PASSWORD", "")
EMAIL_USE_TLS = env_bool("EMAIL_USE_TLS", True)
EMAIL_TIMEOUT_SECONDS = env_int("EMAIL_TIMEOUT_SECONDS", 10)
DEFAULT_FROM_EMAIL = os.getenv("DEFAULT_FROM_EMAIL", "")

LOGIN_THROTTLE_RATE = os.getenv("LOGIN_THROTTLE_RATE", "10/min")

# Notificações (ADR-049). A fila vive no Oracle e o despacho roda fora da
# requisição, por comando acionado pelo agendador do sistema operacional.
# `SGPD_BASE_URL` compõe os links das mensagens; vazio produz link relativo.
SGPD_BASE_URL = os.getenv("SGPD_BASE_URL", "").rstrip("/")
NOTIFICATION_MAX_ATTEMPTS = env_int("NOTIFICATION_MAX_ATTEMPTS", 5)
NOTIFICATION_BATCH_SIZE = env_int("NOTIFICATION_BATCH_SIZE", 50)
# Uma mensagem presa em `ENVIANDO` além disso perdeu o despachante que a tomou.
NOTIFICATION_STALE_MINUTES = env_int("NOTIFICATION_STALE_MINUTES", 15)
# Marcos de prazo de WORKFLOWS.md §7, em horas. Os três primeiros são relativos
# ao vencimento da tarefa; o último, à data limite do processo.
NOTIFICATION_TASK_DUE_SOON_HOURS = env_int("NOTIFICATION_TASK_DUE_SOON_HOURS", 48)
NOTIFICATION_TASK_DUE_IMMINENT_HOURS = env_int("NOTIFICATION_TASK_DUE_IMMINENT_HOURS", 24)
NOTIFICATION_TASK_CRITICAL_HOURS = env_int("NOTIFICATION_TASK_CRITICAL_HOURS", 48)
NOTIFICATION_PROCESS_DUE_SOON_HOURS = env_int("NOTIFICATION_PROCESS_DUE_SOON_HOURS", 72)

# Active Directory. Discovery and authentication have separate switches so
# Infrastructure can validate connectivity and filters before changing login.
LDAP_ENABLED = env_bool("LDAP_ENABLED")
LDAP_AUTHENTICATION_ENABLED = env_bool("LDAP_AUTHENTICATION_ENABLED")
# Interface simples vigente: servidor sem protocolo e uma única escolha de TLS.
LDAP_SERVER_ADDRESS = os.getenv("LDAP_SERVER_ADDRESS", "")
LDAP_USE_TLS = env_bool("LDAP_USE_TLS", True)
# Compatibilidade de baseline para instalações anteriores à central dinâmica.
LDAP_SERVER_URI = os.getenv("LDAP_SERVER_URI", "")
LDAP_BIND_DN = os.getenv("LDAP_BIND_DN", "")
LDAP_BIND_PASSWORD = os.getenv("LDAP_BIND_PASSWORD", "")
LDAP_USER_SEARCH_BASE = os.getenv("LDAP_USER_SEARCH_BASE", "")
LDAP_GROUP_SEARCH_BASE = os.getenv("LDAP_GROUP_SEARCH_BASE", "")
LDAP_REQUIRED_GROUP_DN = os.getenv("LDAP_REQUIRED_GROUP_DN", "")
LDAP_START_TLS = env_bool("LDAP_START_TLS")
LDAP_TLS_REQUIRE_CERTIFICATE = env_bool("LDAP_TLS_REQUIRE_CERTIFICATE", True)
LDAP_TLS_CA_CERT_FILE = os.getenv("LDAP_TLS_CA_CERT_FILE", "")
LDAP_CONNECT_TIMEOUT_SECONDS = env_int("LDAP_CONNECT_TIMEOUT_SECONDS", 5)
LDAP_RECEIVE_TIMEOUT_SECONDS = env_int("LDAP_RECEIVE_TIMEOUT_SECONDS", 10)
LDAP_PAGE_SIZE = env_int("LDAP_PAGE_SIZE", 100)
LDAP_RESULT_LIMIT = env_int("LDAP_RESULT_LIMIT", 50)
LDAP_NESTED_GROUP_SEARCH = env_bool("LDAP_NESTED_GROUP_SEARCH", True)
LDAP_LOCAL_SUPERUSER_FALLBACK = env_bool("LDAP_LOCAL_SUPERUSER_FALLBACK", True)
LDAP_USER_EXTRA_FILTER = os.getenv("LDAP_USER_EXTRA_FILTER", "")

AUTHENTICATION_BACKENDS = [
    "apps.integrations.active_directory.ldap_backend.ActiveDirectoryBackend",
    "apps.integrations.active_directory.backends.LocalAccountBackend",
]

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework.authentication.SessionAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
    "EXCEPTION_HANDLER": "config.api.exception_handler",
    "DEFAULT_THROTTLE_RATES": {"login": LOGIN_THROTTLE_RATE},
}

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

SENIOR_QUERY_TIMEOUT_MS = env_int("SENIOR_QUERY_TIMEOUT_MS", 5_000)
SENIOR_QUERY_MAX_PAGE_SIZE = env_int("SENIOR_QUERY_MAX_PAGE_SIZE", 100)

LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "json": {
            "()": "config.logging.JsonFormatter",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "json",
        },
    },
    "root": {
        "handlers": ["console"],
        "level": LOG_LEVEL,
    },
    # django-auth-ldap logs raw LDAP exception payloads at WARNING. The SGPD
    # replaces them with a safe, correlated operational event in its backend.
    "loggers": {
        "django_auth_ldap": {
            "handlers": ["console"],
            "level": "ERROR",
            "propagate": False,
        },
    },
}
