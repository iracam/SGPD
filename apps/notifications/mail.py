"""Backend SMTP que lê a configuração vigente da central (ADR-050).

Django instancia o backend a cada envio, então a configuração validada entra em
vigor sem mutação de settings global e sem reinício — mesma propriedade que a
ADR-031 deu ao LDAP. Parâmetro explicitamente passado por quem abre a conexão
continua vencendo, para que o teste da central possa usar valores candidatos.
"""

from __future__ import annotations

from typing import Any

from django.core.mail.backends.smtp import EmailBackend as SmtpEmailBackend

from .config import EmailConfig


class ConfiguredEmailBackend(SmtpEmailBackend):
    def __init__(
        self,
        host: str | None = None,
        port: int | None = None,
        username: str | None = None,
        password: str | None = None,
        use_tls: bool | None = None,
        timeout: int | None = None,
        **kwargs: Any,
    ) -> None:
        config = EmailConfig.from_settings()
        super().__init__(
            host=host if host is not None else (config.host or None),
            port=port if port is not None else config.port,
            username=username if username is not None else (config.username or None),
            password=password if password is not None else (config.password or None),
            use_tls=use_tls if use_tls is not None else config.use_tls,
            timeout=timeout if timeout is not None else config.timeout_seconds,
            **kwargs,
        )
