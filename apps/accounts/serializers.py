"""Input contracts for the account API.

Serializers validate shape only. Every business rule stays in the services,
which revalidate authorization at their own boundary as required by ADR-024.
"""

from __future__ import annotations

from typing import Any

from rest_framework import serializers

from .models import ScopeType

REASON_MAX_LENGTH = 2000


def _reason_field() -> serializers.CharField:
    """Every audited use case demands a justification."""

    return serializers.CharField(max_length=REASON_MAX_LENGTH, trim_whitespace=True)


class LoginSerializer(serializers.Serializer[dict[str, str]]):
    username = serializers.CharField(max_length=150, trim_whitespace=True)
    password = serializers.CharField(max_length=128, trim_whitespace=False)


class ChangeOwnPasswordSerializer(serializers.Serializer[dict[str, str]]):
    old_password = serializers.CharField(max_length=128, trim_whitespace=False)
    new_password = serializers.CharField(max_length=128, trim_whitespace=False)
    new_password_confirm = serializers.CharField(max_length=128, trim_whitespace=False)

    def validate(self, attrs: dict[str, str]) -> dict[str, str]:
        if attrs["new_password"] != attrs["new_password_confirm"]:
            raise serializers.ValidationError(
                {"new_password_confirm": "A confirmação não corresponde à nova senha."}
            )
        return attrs


class UserCreateSerializer(serializers.Serializer[dict[str, Any]]):
    username = serializers.CharField(max_length=150, trim_whitespace=True)
    first_name = serializers.CharField(max_length=150, trim_whitespace=True)
    last_name = serializers.CharField(max_length=150, trim_whitespace=True)
    email = serializers.EmailField()
    password = serializers.CharField(max_length=128, trim_whitespace=False)
    password_confirm = serializers.CharField(max_length=128, trim_whitespace=False)
    must_change_password = serializers.BooleanField(default=True)
    reason = _reason_field()

    def validate(self, attrs: dict[str, Any]) -> dict[str, Any]:
        if attrs["password"] != attrs["password_confirm"]:
            raise serializers.ValidationError(
                {"password_confirm": "A confirmação não corresponde à senha."}
            )
        return attrs


class UserUpdateSerializer(serializers.Serializer[dict[str, Any]]):
    version = serializers.IntegerField(min_value=1)
    first_name = serializers.CharField(max_length=150, trim_whitespace=True)
    last_name = serializers.CharField(max_length=150, trim_whitespace=True)
    email = serializers.EmailField()
    is_active = serializers.BooleanField()
    reason = _reason_field()


class ResetPasswordSerializer(serializers.Serializer[dict[str, Any]]):
    password = serializers.CharField(max_length=128, trim_whitespace=False)
    password_confirm = serializers.CharField(max_length=128, trim_whitespace=False)
    must_change_password = serializers.BooleanField(default=True)
    reason = _reason_field()

    def validate(self, attrs: dict[str, Any]) -> dict[str, Any]:
        if attrs["password"] != attrs["password_confirm"]:
            raise serializers.ValidationError(
                {"password_confirm": "A confirmação não corresponde à senha."}
            )
        return attrs


class ReasonSerializer(serializers.Serializer[dict[str, Any]]):
    reason = _reason_field()


class ReasonVersionSerializer(serializers.Serializer[dict[str, Any]]):
    version = serializers.IntegerField(min_value=1)
    reason = _reason_field()


class AdLinkSerializer(serializers.Serializer[dict[str, Any]]):
    version = serializers.IntegerField(min_value=1)
    identifier = serializers.CharField(max_length=255, trim_whitespace=True)
    # Required only while discovery is disabled and the legacy manual-link
    # path remains available. With LDAP_ENABLED, the server resolves it from AD.
    username = serializers.CharField(
        max_length=150,
        trim_whitespace=True,
        required=False,
        allow_blank=True,
        default="",
    )
    reason = _reason_field()


class DirectoryUserCreateSerializer(serializers.Serializer[dict[str, Any]]):
    identifier = serializers.CharField(max_length=255, trim_whitespace=True)


class RoleAssignmentSerializer(serializers.Serializer[dict[str, Any]]):
    role_id = serializers.IntegerField(min_value=1)
    scope_type = serializers.ChoiceField(choices=ScopeType.choices)
    company_code = serializers.IntegerField(min_value=1, required=False, allow_null=True)
    branch_code = serializers.IntegerField(min_value=1, required=False, allow_null=True)
    valid_from = serializers.DateTimeField(required=False, allow_null=True)
    valid_until = serializers.DateTimeField(required=False, allow_null=True)
    reason = _reason_field()

    def validate(self, attrs: dict[str, Any]) -> dict[str, Any]:
        # Mirrors the model constraint SGPD_CK_ROLE_SCOPE so the caller gets a
        # field-level message. The service and the model validate it again.
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


class RoleCreateSerializer(serializers.Serializer[dict[str, Any]]):
    code = serializers.CharField(max_length=50, trim_whitespace=True)
    name = serializers.CharField(max_length=120, trim_whitespace=True)
    description = serializers.CharField(
        max_length=REASON_MAX_LENGTH,
        allow_blank=True,
        default="",
        trim_whitespace=True,
    )
    permission_ids = serializers.ListField(
        child=serializers.IntegerField(min_value=1),
        allow_empty=True,
        default=list,
    )
    reason = _reason_field()


class RoleUpdateSerializer(serializers.Serializer[dict[str, Any]]):
    version = serializers.IntegerField(min_value=1)
    name = serializers.CharField(max_length=120, trim_whitespace=True)
    description = serializers.CharField(
        max_length=REASON_MAX_LENGTH,
        allow_blank=True,
        default="",
        trim_whitespace=True,
    )
    is_active = serializers.BooleanField()
    permission_ids = serializers.ListField(
        child=serializers.IntegerField(min_value=1),
        allow_empty=True,
        default=list,
    )
    reason = _reason_field()
