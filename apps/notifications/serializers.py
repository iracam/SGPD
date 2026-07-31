from __future__ import annotations

from typing import Any

from rest_framework import serializers

from .models import NotificationEvent, NotificationStatus


class NotificationQuerySerializer(serializers.Serializer[dict[str, Any]]):
    process_uuid = serializers.UUIDField(required=False)
    status = serializers.ChoiceField(
        choices=NotificationStatus.choices,
        required=False,
        allow_blank=True,
        default="",
    )
    event = serializers.ChoiceField(
        choices=NotificationEvent.choices,
        required=False,
        allow_blank=True,
        default="",
    )
    # A fila cresce com o tempo e o painel é de operação, não de histórico:
    # sem teto, uma tela de falhas viraria varredura completa da tabela.
    limit = serializers.IntegerField(min_value=1, max_value=500, required=False, default=200)


class ReprocessNotificationSerializer(serializers.Serializer[dict[str, Any]]):
    expected_version = serializers.IntegerField(min_value=1)
