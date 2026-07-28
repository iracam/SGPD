"""Django system checks for the AD contract."""

from __future__ import annotations

from django.core.checks import Error, Warning, register

from .config import ActiveDirectoryConfig


@register()
def active_directory_configuration_check(**kwargs: object) -> list[Error | Warning]:
    del kwargs
    config = ActiveDirectoryConfig.from_settings()
    errors = config.validation_errors()
    if not errors:
        if config.enabled and not config.secure_transport:
            scope = "descoberta e autenticação" if config.authentication_enabled else "descoberta"
            return [
                Warning(
                    f"LDAP sem TLS ativo para {scope}; a credencial técnica e as "
                    "senhas dos usuários trafegam sem criptografia.",
                    id="sgpd.AD900",
                )
            ]
        return []
    severity = Error if config.enabled or config.authentication_enabled else Warning
    return [
        severity(
            message,
            id=f"sgpd.AD{index:03d}",
        )
        for index, message in enumerate(errors, start=1)
    ]
