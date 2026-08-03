#!/usr/bin/env python
"""Django command-line utility for the SGPD project."""

import sys

from config.bootstrap import configure_settings_module


def main() -> None:
    configure_settings_module()

    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Django não está disponível. Execute `uv sync --dev` antes de usar manage.py."
        ) from exc

    execute_from_command_line(sys.argv)


if __name__ == "__main__":
    main()
