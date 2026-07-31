from __future__ import annotations

from typing import Any

from rest_framework import serializers


class ReportQuerySerializer(serializers.Serializer[Any]):
    """Recorte de período dos relatórios (RF-036).

    Ambos os limites são opcionais: sem nada informado o relatório usa a janela
    padrão. O fim inclui o dia inteiro — quem digita a data de hoje espera ver
    o que aconteceu hoje.
    """

    start = serializers.DateField(required=False, allow_null=True, default=None)
    end = serializers.DateField(required=False, allow_null=True, default=None)

    def validate(self, attrs: dict[str, Any]) -> dict[str, Any]:
        start, end = attrs.get("start"), attrs.get("end")
        if start and end and start > end:
            raise serializers.ValidationError(
                {"start": "A data inicial não pode ser posterior à final."}
            )
        return attrs
