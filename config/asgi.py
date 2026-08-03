"""ASGI config for SGPD."""

from django.core.asgi import get_asgi_application

from config.bootstrap import configure_settings_module

configure_settings_module()

application = get_asgi_application()
