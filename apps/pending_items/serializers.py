from __future__ import annotations

from decimal import Decimal
from typing import Any

from rest_framework import serializers

from .models import BlockingLevel, PendingCategory, PendingStatus


class PendingLineSerializer(serializers.Serializer[dict[str, Any]]):
    description = serializers.CharField(max_length=500, trim_whitespace=True)
    code = serializers.CharField(
        max_length=80, required=False, allow_blank=True, default="", trim_whitespace=True
    )
    asset_tag = serializers.CharField(
        max_length=100, required=False, allow_blank=True, default="", trim_whitespace=True
    )
    serial_number = serializers.CharField(
        max_length=120, required=False, allow_blank=True, default="", trim_whitespace=True
    )
    quantity = serializers.DecimalField(
        max_digits=12,
        decimal_places=3,
        min_value=Decimal("0.001"),
    )
    unit = serializers.CharField(max_length=30, required=False, default="UN")
    item_condition = serializers.CharField(
        max_length=120, required=False, allow_blank=True, default="", trim_whitespace=True
    )
    extra_data = serializers.JSONField(required=False, default=dict)


class CreatePendingItemSerializer(serializers.Serializer[dict[str, Any]]):
    task_id = serializers.IntegerField(min_value=1)
    expected_task_version = serializers.IntegerField(min_value=1)
    checklist_item_id = serializers.IntegerField(min_value=1, required=False, allow_null=True)
    category = serializers.ChoiceField(choices=PendingCategory.choices)
    title = serializers.CharField(max_length=200, trim_whitespace=True)
    description = serializers.CharField(max_length=4000, trim_whitespace=True)
    blocking_level = serializers.ChoiceField(choices=BlockingLevel.choices)
    regularization_due_at = serializers.DateTimeField(required=False, allow_null=True)
    items = PendingLineSerializer(many=True, required=False, default=list)


class PendingQuerySerializer(serializers.Serializer[dict[str, Any]]):
    task_id = serializers.IntegerField(min_value=1, required=False)
    process_uuid = serializers.UUIDField(required=False)
    status = serializers.ChoiceField(
        choices=PendingStatus.choices, required=False, allow_blank=True, default=""
    )

    def validate(self, attrs: dict[str, Any]) -> dict[str, Any]:
        if not attrs.get("task_id") and not attrs.get("process_uuid"):
            raise serializers.ValidationError("Informe task_id ou process_uuid.")
        return attrs


class ChangePendingStatusSerializer(serializers.Serializer[dict[str, Any]]):
    expected_version = serializers.IntegerField(min_value=1)
    status = serializers.ChoiceField(choices=PendingStatus.choices)
    comment = serializers.CharField(max_length=4000, trim_whitespace=True)


class AddPendingCommentSerializer(serializers.Serializer[dict[str, Any]]):
    expected_version = serializers.IntegerField(min_value=1)
    comment = serializers.CharField(max_length=4000, trim_whitespace=True)
