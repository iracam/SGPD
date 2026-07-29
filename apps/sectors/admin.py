"""Read-only diagnostics for functional sector configuration."""

from django.contrib import admin
from django.http import HttpRequest

from .models import (
    SectorAuditEvent,
    SectorResponsible,
    SectorScope,
    ValidationSector,
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


@admin.register(ValidationSector)
class ValidationSectorAdmin(
    ReadOnlyAdminMixin,
    admin.ModelAdmin,  # type: ignore[type-arg]
):
    list_display = ("code", "name", "is_active", "default_due_hours", "updated_at")
    list_filter = ("is_active", "blocks_process", "allows_amount", "requires_evidence")
    search_fields = ("code", "name")


@admin.register(SectorScope)
class SectorScopeAdmin(ReadOnlyAdminMixin, admin.ModelAdmin):  # type: ignore[type-arg]
    list_display = ("sector", "scope_key", "company_code", "branch_code")
    list_filter = ("scope_type",)


@admin.register(SectorResponsible)
class SectorResponsibleAdmin(
    ReadOnlyAdminMixin,
    admin.ModelAdmin,  # type: ignore[type-arg]
):
    list_display = (
        "sector",
        "user",
        "scope_key",
        "valid_from",
        "valid_until",
        "is_active",
    )
    list_filter = ("is_active", "scope_type", "sector")
    search_fields = ("sector__code", "user__username", "user__email")


@admin.register(SectorAuditEvent)
class SectorAuditEventAdmin(
    ReadOnlyAdminMixin,
    admin.ModelAdmin,  # type: ignore[type-arg]
):
    list_display = ("occurred_at", "event_type", "sector", "actor", "correlation_id")
    list_filter = ("event_type",)
    search_fields = ("sector__code", "correlation_id", "reason")
