"""Input contracts for workflow-configuration APIs."""

from __future__ import annotations

from typing import Any

from rest_framework import serializers

from .models import ChecklistResponseType


class ChecklistItemSerializer(serializers.Serializer[dict[str, Any]]):
    question = serializers.CharField(max_length=2000, trim_whitespace=True)
    response_type = serializers.ChoiceField(choices=ChecklistResponseType.choices)
    is_required = serializers.BooleanField(default=True)
    blocks_process = serializers.BooleanField(default=False)
    requires_evidence = serializers.BooleanField(default=False)
    allows_pending = serializers.BooleanField(default=True)
    display_order = serializers.IntegerField(min_value=1)
    config = serializers.JSONField(required=False, default=dict)


class ChecklistVersionSerializer(serializers.Serializer[dict[str, Any]]):
    expected_version = serializers.IntegerField(min_value=1, required=False)
    default_due_hours = serializers.IntegerField(
        min_value=1,
        max_value=8760,
        required=False,
        allow_null=True,
    )
    items = ChecklistItemSerializer(many=True, allow_empty=False)


class ChecklistTemplateCreateSerializer(ChecklistVersionSerializer):
    name = serializers.CharField(max_length=120, trim_whitespace=True)
    description = serializers.CharField(
        max_length=2000,
        allow_blank=True,
        required=False,
        default="",
        trim_whitespace=True,
    )


class ChecklistTemplateDraftUpdateSerializer(ChecklistVersionSerializer):
    expected_version = serializers.IntegerField(min_value=1)
    name = serializers.CharField(max_length=120, trim_whitespace=True)
    description = serializers.CharField(
        max_length=2000,
        allow_blank=True,
        required=False,
        default="",
        trim_whitespace=True,
    )


class PublishVersionSerializer(serializers.Serializer[dict[str, Any]]):
    expected_version = serializers.IntegerField(min_value=1)


class GroupSectorSerializer(serializers.Serializer[dict[str, Any]]):
    sector_id = serializers.IntegerField(min_value=1)
    template_version_id = serializers.IntegerField(min_value=1)
    is_required = serializers.BooleanField(default=True)
    blocks_process = serializers.BooleanField(default=True)
    due_hours_override = serializers.IntegerField(
        min_value=1,
        max_value=8760,
        required=False,
        allow_null=True,
    )
    display_order = serializers.IntegerField(min_value=1)


class ValidationGroupVersionSerializer(serializers.Serializer[dict[str, Any]]):
    expected_version = serializers.IntegerField(min_value=1, required=False)
    sectors = GroupSectorSerializer(many=True, allow_empty=False)


class ValidationGroupCreateSerializer(ValidationGroupVersionSerializer):
    name = serializers.CharField(max_length=120, trim_whitespace=True)
    description = serializers.CharField(
        max_length=2000,
        allow_blank=True,
        required=False,
        default="",
        trim_whitespace=True,
    )


class ValidationGroupDraftUpdateSerializer(ValidationGroupCreateSerializer):
    expected_version = serializers.IntegerField(min_value=1)


class ApplicabilityRuleSerializer(serializers.Serializer[dict[str, Any]]):
    name = serializers.CharField(max_length=120, trim_whitespace=True)
    priority = serializers.IntegerField(min_value=1, max_value=9999, default=100)
    group_id = serializers.IntegerField(min_value=1)
    company_code = serializers.IntegerField(min_value=1, required=False, allow_null=True)
    branch_code = serializers.IntegerField(min_value=1, required=False, allow_null=True)
    employee_type_code = serializers.IntegerField(min_value=1, required=False, allow_null=True)
    job_structure_code = serializers.IntegerField(min_value=1, required=False, allow_null=True)
    job_code = serializers.CharField(
        max_length=50,
        required=False,
        allow_null=True,
        allow_blank=True,
        trim_whitespace=True,
    )
    cost_center_code = serializers.CharField(
        max_length=50,
        required=False,
        allow_null=True,
        allow_blank=True,
        trim_whitespace=True,
    )
    is_active = serializers.BooleanField(default=True)
    valid_from = serializers.DateField(required=False, allow_null=True)
    valid_to = serializers.DateField(required=False, allow_null=True)


class ApplicabilityRuleUpdateSerializer(ApplicabilityRuleSerializer):
    expected_version = serializers.IntegerField(min_value=1)
