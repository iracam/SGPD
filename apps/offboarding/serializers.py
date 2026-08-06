"""Input contracts for offboarding-process endpoints."""

from __future__ import annotations

from typing import Any

from rest_framework import serializers

from .models import DraftOverrideAction, ProcessStatus, SectorTaskStatus


class OpenOffboardingProcessSerializer(serializers.Serializer[dict[str, Any]]):
    company_code = serializers.IntegerField(min_value=1)
    branch_code = serializers.IntegerField(min_value=1)
    employee_type_code = serializers.IntegerField(min_value=1)
    employee_registration = serializers.IntegerField(min_value=1)
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


class ProcessQuerySerializer(serializers.Serializer[dict[str, Any]]):
    status = serializers.ChoiceField(
        choices=ProcessStatus.choices,
        required=False,
        allow_blank=True,
        default="",
    )
    completed = serializers.BooleanField(required=False, default=False)
    open = serializers.BooleanField(required=False, default=False)
    offset = serializers.IntegerField(min_value=0, required=False, default=0)
    limit = serializers.IntegerField(min_value=1, max_value=100, required=False, default=50)

    def validate(self, attrs: dict[str, Any]) -> dict[str, Any]:
        active_filters = sum(
            bool(value)
            for value in (
                attrs.get("status"),
                attrs.get("completed"),
                attrs.get("open"),
            )
        )
        if active_filters > 1:
            raise serializers.ValidationError(
                "Os filtros status, completed e open não podem ser combinados."
            )
        return attrs


class DraftSectorOverrideSerializer(serializers.Serializer[dict[str, Any]]):
    sector_id = serializers.IntegerField(min_value=1)
    action = serializers.ChoiceField(choices=DraftOverrideAction.choices)
    template_version_id = serializers.IntegerField(
        min_value=1,
        required=False,
        allow_null=True,
    )
    is_required = serializers.BooleanField(default=True)
    blocks_process = serializers.BooleanField(default=True)
    due_hours_override = serializers.IntegerField(
        min_value=1,
        max_value=8760,
        required=False,
        allow_null=True,
    )
    reason = serializers.CharField(max_length=2000, trim_whitespace=True)


class UpdateDraftSelectionSerializer(serializers.Serializer[dict[str, Any]]):
    expected_version = serializers.IntegerField(min_value=1)
    group_version_ids = serializers.ListField(
        child=serializers.IntegerField(min_value=1),
        allow_empty=False,
    )
    overrides = DraftSectorOverrideSerializer(many=True, required=False, default=list)


class StartOffboardingProcessSerializer(serializers.Serializer[dict[str, Any]]):
    expected_version = serializers.IntegerField(min_value=1)


class ReleaseProcessSerializer(serializers.Serializer[dict[str, Any]]):
    expected_version = serializers.IntegerField(min_value=1)
    notes = serializers.CharField(
        max_length=1000,
        required=False,
        allow_blank=True,
        default="",
        trim_whitespace=True,
    )
    # Só o service sabe se há impedimento: a obrigatoriedade condicional
    # (ADR-054) é decidida lá, não aqui.
    override_reason = serializers.CharField(
        max_length=1000,
        required=False,
        allow_blank=True,
        default="",
        trim_whitespace=True,
    )


class RegisterTerminationProcessingSerializer(serializers.Serializer[dict[str, Any]]):
    """O número e a data são declaração do `DP`, não leitura do Senior (ADR-051)."""

    expected_version = serializers.IntegerField(min_value=1)
    termination_reference = serializers.CharField(max_length=60, trim_whitespace=True)
    processed_on = serializers.DateField()
    notes = serializers.CharField(
        max_length=1000,
        required=False,
        allow_blank=True,
        default="",
        trim_whitespace=True,
    )


class CloseProcessSerializer(serializers.Serializer[dict[str, Any]]):
    expected_version = serializers.IntegerField(min_value=1)
    notes = serializers.CharField(
        max_length=1000,
        required=False,
        allow_blank=True,
        default="",
        trim_whitespace=True,
    )
    override_reason = serializers.CharField(
        max_length=1000,
        required=False,
        allow_blank=True,
        default="",
        trim_whitespace=True,
    )


class CancelProcessSerializer(serializers.Serializer[dict[str, Any]]):
    expected_version = serializers.IntegerField(min_value=1)
    reason = serializers.CharField(max_length=1000, trim_whitespace=True)


class PurgeProcessSerializer(serializers.Serializer[dict[str, Any]]):
    """Exclusão definitiva (ADR-056): a justificativa é o que fica de relato."""

    expected_version = serializers.IntegerField(min_value=1)
    reason = serializers.CharField(max_length=1000, trim_whitespace=True)


class ReopenProcessSerializer(serializers.Serializer[dict[str, Any]]):
    expected_version = serializers.IntegerField(min_value=1)
    reason = serializers.CharField(max_length=1000, trim_whitespace=True)
    #: Tarefas concluídas que voltam para análise. Lista vazia corrige só a
    #: marca formal, sem devolver trabalho ao setor.
    task_ids = serializers.ListField(
        child=serializers.IntegerField(min_value=1),
        required=False,
        default=list,
    )


class SectorTaskQuerySerializer(serializers.Serializer[dict[str, Any]]):
    status = serializers.ChoiceField(
        choices=SectorTaskStatus.choices,
        required=False,
        allow_blank=True,
        default="",
    )
    offset = serializers.IntegerField(min_value=0, required=False, default=0)
    limit = serializers.IntegerField(min_value=1, max_value=100, required=False, default=50)


class StartSectorTaskSerializer(serializers.Serializer[dict[str, Any]]):
    expected_version = serializers.IntegerField(min_value=1)


class ChecklistAnswerSerializer(serializers.Serializer[dict[str, Any]]):
    item_id = serializers.IntegerField(min_value=1)
    value = serializers.JSONField(allow_null=True)


class CompleteSectorTaskSerializer(serializers.Serializer[dict[str, Any]]):
    expected_version = serializers.IntegerField(min_value=1)
    answers = ChecklistAnswerSerializer(many=True)
    notes = serializers.CharField(
        max_length=4000,
        required=False,
        allow_blank=True,
        default="",
        trim_whitespace=True,
    )
