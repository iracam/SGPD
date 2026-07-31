"""Input contracts for the SuperAdmin configuration API."""

from typing import Any

from rest_framework import serializers

from .certificates import MAX_CERTIFICATE_BYTES


class LdapConfigurationSerializer(serializers.Serializer[dict[str, Any]]):
    version = serializers.IntegerField(min_value=0)
    enabled = serializers.BooleanField()
    authentication_enabled = serializers.BooleanField()
    server_address = serializers.CharField(
        max_length=512,
        allow_blank=True,
        trim_whitespace=True,
    )
    use_tls = serializers.BooleanField()
    bind_dn = serializers.CharField(max_length=512, allow_blank=True, trim_whitespace=True)
    bind_password = serializers.CharField(
        max_length=1024,
        allow_blank=True,
        required=False,
        default="",
        trim_whitespace=False,
        write_only=True,
    )
    user_search_base = serializers.CharField(
        max_length=2000,
        allow_blank=True,
        trim_whitespace=True,
    )
    group_search_base = serializers.CharField(
        max_length=2000,
        allow_blank=True,
        trim_whitespace=True,
    )
    required_group_dn = serializers.CharField(
        max_length=2000,
        allow_blank=True,
        trim_whitespace=True,
    )
    connect_timeout_seconds = serializers.IntegerField(min_value=1, max_value=300)
    receive_timeout_seconds = serializers.IntegerField(min_value=1, max_value=300)
    page_size = serializers.IntegerField(min_value=1, max_value=1000)
    result_limit = serializers.IntegerField(min_value=1, max_value=200)
    nested_group_search = serializers.BooleanField()
    local_superuser_fallback = serializers.BooleanField()
    user_extra_filter = serializers.CharField(
        max_length=2000,
        allow_blank=True,
        trim_whitespace=True,
    )

    def validate(self, attrs: dict[str, object]) -> dict[str, object]:
        if attrs["authentication_enabled"] and not attrs["enabled"]:
            raise serializers.ValidationError(
                {"authentication_enabled": "A autenticação exige a descoberta habilitada."}
            )
        return attrs

    def validate_server_address(self, value: str) -> str:
        if "://" in value:
            raise serializers.ValidationError(
                "Informe somente o servidor ou servidor:porta; o protocolo é automático."
            )
        return value


class LdapCertificateUploadSerializer(serializers.Serializer[dict[str, Any]]):
    version = serializers.IntegerField(min_value=0)
    certificate = serializers.FileField()

    def validate_certificate(self, value):  # type: ignore[no-untyped-def]
        if value.size > MAX_CERTIFICATE_BYTES:
            raise serializers.ValidationError("O certificado deve ter no máximo 512 KiB.")
        return value


class EmailConfigurationSerializer(serializers.Serializer[dict[str, Any]]):
    version = serializers.IntegerField(min_value=0)
    enabled = serializers.BooleanField()
    host = serializers.CharField(max_length=255, allow_blank=True, trim_whitespace=True)
    port = serializers.IntegerField(min_value=1, max_value=65535)
    use_tls = serializers.BooleanField()
    username = serializers.CharField(max_length=255, allow_blank=True, trim_whitespace=True)
    # Em branco preserva a senha vigente; a API nunca devolve o valor.
    password = serializers.CharField(
        max_length=1024,
        allow_blank=True,
        required=False,
        default="",
        trim_whitespace=False,
        write_only=True,
    )
    timeout_seconds = serializers.IntegerField(min_value=1, max_value=300)
    default_from_email = serializers.CharField(
        max_length=254,
        allow_blank=True,
        trim_whitespace=True,
    )
    base_url = serializers.CharField(max_length=255, allow_blank=True, trim_whitespace=True)
    max_attempts = serializers.IntegerField(min_value=1, max_value=20)
    batch_size = serializers.IntegerField(min_value=1, max_value=500)
    stale_minutes = serializers.IntegerField(min_value=1, max_value=1440)
    task_due_soon_hours = serializers.IntegerField(min_value=1, max_value=720)
    task_due_imminent_hours = serializers.IntegerField(min_value=1, max_value=720)
    task_critical_hours = serializers.IntegerField(min_value=1, max_value=720)
    process_due_soon_hours = serializers.IntegerField(min_value=1, max_value=720)

    def validate(self, attrs: dict[str, object]) -> dict[str, object]:
        imminent = int(attrs["task_due_imminent_hours"])  # type: ignore[call-overload]
        due_soon = int(attrs["task_due_soon_hours"])  # type: ignore[call-overload]
        if imminent >= due_soon:
            raise serializers.ValidationError(
                {
                    "task_due_imminent_hours": (
                        "O lembrete final precisa ser mais próximo do prazo que o primeiro."
                    )
                }
            )
        return attrs
