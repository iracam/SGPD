"""Input contracts for the account API.

Serializers validate shape only. Every business rule stays in the services,
which revalidate authorization at their own boundary as required by ADR-024.
"""

from __future__ import annotations

from rest_framework import serializers


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
