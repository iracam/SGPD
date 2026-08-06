"""Read-only diagnostics for offboarding processes."""

from django.contrib import admin
from django.http import HttpRequest

from .models import (
    EmployeeSnapshot,
    OffboardingProcess,
    ProcessActionIdempotency,
    ProcessAuditEvent,
    ProcessChecklistItem,
    ProcessPurgeRecord,
    ProcessSectorOverride,
    ProcessSectorTask,
    ProcessTaskGroupSource,
    ProcessValidationGroup,
)


class ReadOnlyAdminMixin:
    def has_add_permission(self, request: HttpRequest) -> bool:
        return False

    def has_change_permission(
        self,
        request: HttpRequest,
        obj: object | None = None,
    ) -> bool:
        return False

    def has_delete_permission(
        self,
        request: HttpRequest,
        obj: object | None = None,
    ) -> bool:
        return False


@admin.register(OffboardingProcess)
class OffboardingProcessAdmin(
    ReadOnlyAdminMixin,
    admin.ModelAdmin,  # type: ignore[type-arg]
):
    list_display = (
        "uuid",
        "employee_registration",
        "status",
        "company_code",
        "branch_code",
        "due_date",
        "opened_at",
    )
    list_filter = ("status", "company_code", "branch_code")
    search_fields = ("uuid", "employee_registration")


@admin.register(EmployeeSnapshot)
class EmployeeSnapshotAdmin(
    ReadOnlyAdminMixin,
    admin.ModelAdmin,  # type: ignore[type-arg]
):
    list_display = ("process", "registration", "employee_name", "source_queried_at")
    search_fields = ("process__uuid", "registration", "employee_name")


@admin.register(ProcessAuditEvent)
class ProcessAuditEventAdmin(
    ReadOnlyAdminMixin,
    admin.ModelAdmin,  # type: ignore[type-arg]
):
    list_display = ("occurred_at", "event_type", "process", "actor", "correlation_id")
    list_filter = ("event_type",)
    search_fields = ("process__uuid", "correlation_id")


@admin.register(ProcessPurgeRecord)
class ProcessPurgeRecordAdmin(
    ReadOnlyAdminMixin,
    admin.ModelAdmin,  # type: ignore[type-arg]
):
    """A lápide dos processos excluídos (ADR-056): é o que restou deles."""

    list_display = (
        "purged_at",
        "process_uuid",
        "process_status",
        "employee_registration",
        "purged_by",
        "had_material_history",
    )
    list_filter = ("process_status", "had_material_history")
    search_fields = ("process_uuid", "employee_registration", "employee_name")


class ProcessRelatedAdmin(
    ReadOnlyAdminMixin,
    admin.ModelAdmin,  # type: ignore[type-arg]
):
    pass


admin.site.register(
    (
        ProcessValidationGroup,
        ProcessSectorOverride,
        ProcessSectorTask,
        ProcessTaskGroupSource,
        ProcessChecklistItem,
        ProcessActionIdempotency,
    ),
    ProcessRelatedAdmin,
)
