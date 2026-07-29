"""Input contracts for the validation-sector aggregate API."""

from __future__ import annotations

from typing import Any

from rest_framework import serializers

from apps.accounts.models import ScopeType


class SectorScopeSerializer(serializers.Serializer[dict[str, Any]]):
    scope_type = serializers.ChoiceField(choices=ScopeType.choices)
    company_code = serializers.IntegerField(min_value=1, required=False, allow_null=True)
    branch_code = serializers.IntegerField(min_value=1, required=False, allow_null=True)

    def validate(self, attrs: dict[str, Any]) -> dict[str, Any]:
        scope_type = attrs["scope_type"]
        company_code = attrs.get("company_code")
        branch_code = attrs.get("branch_code")
        if scope_type == ScopeType.GLOBAL and (company_code or branch_code):
            raise serializers.ValidationError(
                {"scope_type": "O escopo global não aceita empresa ou filial."}
            )
        if scope_type == ScopeType.COMPANY and (not company_code or branch_code):
            raise serializers.ValidationError(
                {"company_code": "Informe somente a empresa para esse escopo."}
            )
        if scope_type == ScopeType.BRANCH and (not company_code or not branch_code):
            raise serializers.ValidationError(
                {"branch_code": "Informe empresa e filial para esse escopo."}
            )
        return attrs


class SectorResponsibleSerializer(serializers.Serializer[dict[str, Any]]):
    user_id = serializers.IntegerField(min_value=1)
    valid_from = serializers.DateTimeField(required=False)
    valid_until = serializers.DateTimeField(required=False, allow_null=True)

    def validate(self, attrs: dict[str, Any]) -> dict[str, Any]:
        valid_from = attrs.get("valid_from")
        valid_until = attrs.get("valid_until")
        if valid_from is not None and valid_until is not None and valid_until <= valid_from:
            raise serializers.ValidationError(
                {"valid_until": "A validade final deve ser posterior à inicial."}
            )
        return attrs


class SectorBaseSerializer(serializers.Serializer[dict[str, Any]]):
    name = serializers.CharField(max_length=120, trim_whitespace=True)
    description = serializers.CharField(
        max_length=2000,
        allow_blank=True,
        default="",
        trim_whitespace=True,
    )
    default_due_hours = serializers.IntegerField(min_value=1, max_value=8760)
    blocks_process = serializers.BooleanField()
    allows_amount = serializers.BooleanField()
    requires_evidence = serializers.BooleanField()
    escalation_sector_id = serializers.IntegerField(
        min_value=1,
        required=False,
        allow_null=True,
    )
    scopes = SectorScopeSerializer(many=True, allow_empty=False)
    responsibles = SectorResponsibleSerializer(many=True, allow_empty=True)

    def validate(self, attrs: dict[str, Any]) -> dict[str, Any]:
        user_ids = [item["user_id"] for item in attrs["responsibles"]]
        if len(user_ids) != len(set(user_ids)):
            raise serializers.ValidationError(
                {"responsibles": "O mesmo usuário foi informado mais de uma vez."}
            )
        return attrs


class SectorCreateSerializer(SectorBaseSerializer):
    pass


class SectorUpdateSerializer(SectorBaseSerializer):
    version = serializers.IntegerField(min_value=1)
    is_active = serializers.BooleanField()
