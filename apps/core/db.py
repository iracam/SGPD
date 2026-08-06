"""Bases de queryset compartilhadas entre os apps do domínio."""

from typing import TypeVar

from django.db import models

_Model = TypeVar("_Model", bound=models.Model)


class PurgeableQuerySet(models.QuerySet[_Model]):
    """Guarda de exclusão com uma única porta de saída: o serviço de purga.

    A regra do projeto continua sendo que nada some do processo em curso — os
    querysets do domínio recusam `delete()` justamente para isso. A ADR-056 abre
    uma exceção estreita: excluir processo ainda não encerrado, deixando lápide
    em `SGPD_PROCESS_PURGE`. Essa exceção precisa ser explícita no código de
    quem a exerce, e não um `_raw_delete()` que fura a guarda por baixo — daí
    um nome próprio, `hard_delete()`, fácil de encontrar em uma varredura.
    """

    def hard_delete(self) -> tuple[int, dict[str, int]]:
        return super().delete()
