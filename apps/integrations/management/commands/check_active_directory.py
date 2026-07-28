"""Validate AD configuration, secure bind and RootDSE discovery without PII."""

from django.core.management.base import BaseCommand, CommandError

from apps.integrations.active_directory.client import ActiveDirectoryClient
from apps.integrations.active_directory.exceptions import ActiveDirectoryError


class Command(BaseCommand):
    help = (
        "Valida configuração, transporte escolhido, bind somente leitura e "
        "descoberta RootDSE do Active Directory sem listar usuários."
    )

    def handle(self, *args: object, **options: object) -> None:
        del args, options
        client = ActiveDirectoryClient()
        status = client.status()
        if not status["enabled"]:
            raise CommandError("A integração está desativada por LDAP_ENABLED=false.")
        errors = status["errors"]
        if isinstance(errors, list) and errors:
            raise CommandError("Configuração inválida: " + " ".join(errors))
        try:
            probe = client.probe()
        except ActiveDirectoryError as exc:
            raise CommandError(str(exc)) from exc
        transport = (
            "TLS"
            if probe.secure_transport
            else (
                "LDAP sem TLS; a credencial técnica e as senhas dos usuários "
                "trafegam sem criptografia"
            )
        )
        self.stdout.write(
            self.style.SUCCESS(
                f"Active Directory validado: {transport}, bind e RootDSE operacionais; "
                f"base de usuários={probe.user_search_base_source}; "
                f"base de grupos={probe.group_search_base_source}."
            )
        )
