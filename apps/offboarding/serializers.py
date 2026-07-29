"""Input contracts for offboarding-process endpoints."""

from __future__ import annotations

from typing import Any

from rest_framework import serializers


class OpenOffboardingProcessSerializer(serializers.Serializer[dict[str, Any]]):
    company_code = serializers.IntegerField(min_value=1)
    branch_code = serializers.IntegerField(min_value=1)
    employee_type_code = serializers.IntegerField(min_value=1)
    employee_registration = serializers.IntegerField(min_value=1)
    manager_user_id = serializers.IntegerField(min_value=1)
    planned_termination_date = serializers.DateField()
    due_date = serializers.DateField()
    reason = serializers.CharField(max_length=2000, trim_whitespace=True)
    priority = serializers.CharField(max_length=50, trim_whitespace=True)
    notes = serializers.CharField(
        max_length=4000,
        required=False,
        allow_blank=True,
        default="",
        trim_whitespace=True,
    )


class ManagerCandidateQuerySerializer(serializers.Serializer[dict[str, Any]]):
    company = serializers.IntegerField(min_value=1)
    branch = serializers.IntegerField(min_value=1)
    q = serializers.CharField(
        max_length=100,
        required=False,
        allow_blank=True,
        default="",
        trim_whitespace=True,
    )
    limit = serializers.IntegerField(min_value=1, max_value=200, required=False, default=100)
