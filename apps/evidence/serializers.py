from __future__ import annotations

from typing import Any

from rest_framework import serializers

from .models import EvidenceClassification


class EvidenceQuerySerializer(serializers.Serializer[dict[str, Any]]):
    task_id = serializers.IntegerField(min_value=1, required=False)
    process_uuid = serializers.UUIDField(required=False)

    def validate(self, attrs: dict[str, Any]) -> dict[str, Any]:
        if not attrs.get("task_id") and not attrs.get("process_uuid"):
            raise serializers.ValidationError("Informe task_id ou process_uuid.")
        return attrs


class UploadEvidenceSerializer(serializers.Serializer[dict[str, Any]]):
    task_id = serializers.IntegerField(min_value=1)
    expected_task_version = serializers.IntegerField(min_value=1)
    pending_uuid = serializers.UUIDField(required=False, allow_null=True)
    checklist_item_id = serializers.IntegerField(min_value=1, required=False, allow_null=True)
    classification = serializers.ChoiceField(choices=EvidenceClassification.choices)
    file = serializers.FileField()
