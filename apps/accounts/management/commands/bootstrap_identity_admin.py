"""Interactive, audited bootstrap for the first human SGPD administrator."""

from getpass import getpass

from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand, CommandError, CommandParser

from apps.accounts.services import (
    BootstrapIdentityAdminCommand,
    BootstrapIdentityAdminService,
)


class Command(BaseCommand):
    help = "Cria, uma única vez, a primeira conta humana de administração."

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument("--username")
        parser.add_argument("--email")
        parser.add_argument("--first-name")
        parser.add_argument("--last-name")

    def _value(self, options: dict[str, object], option: str, label: str) -> str:
        value = str(options.get(option) or "").strip()
        return value or input(f"{label}: ").strip()

    def handle(self, *args: object, **options: object) -> None:
        username = self._value(options, "username", "Login")
        email = self._value(options, "email", "E-mail")
        first_name = self._value(options, "first_name", "Nome")
        last_name = self._value(options, "last_name", "Sobrenome")
        password = getpass("Senha inicial: ")
        confirmation = getpass("Confirme a senha: ")
        if password != confirmation:
            raise CommandError("As senhas não coincidem.")

        try:
            user = BootstrapIdentityAdminService().execute(
                BootstrapIdentityAdminCommand(
                    username=username,
                    email=email,
                    first_name=first_name,
                    last_name=last_name,
                    password=password,
                )
            )
        except ValidationError as exc:
            raise CommandError("; ".join(exc.messages)) from exc

        self.stdout.write(
            self.style.SUCCESS(
                f"Administrador {user.username} criado com auditoria e papel global."
            )
        )
