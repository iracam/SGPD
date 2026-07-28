"""Read-only diagnostics in Django admin.

Operational account changes must use the audited SGPD account screens/services.
"""

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.http import HttpRequest

from .models import AccountAuditEvent, Role, RoleAssignment, User


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


@admin.register(User)
class SGPDUserAdmin(ReadOnlyAdminMixin, UserAdmin):  # type: ignore[type-arg]
    list_display = (
        "username",
        "email",
        "first_name",
        "last_name",
        "is_active",
        "has_ad_link",
    )
    readonly_fields = (
        "username",
        "first_name",
        "last_name",
        "email",
        "is_active",
        "is_staff",
        "is_superuser",
        "last_login",
        "date_joined",
        "must_change_password",
        "ad_identifier",
        "ad_username",
        "ad_linked_at",
        "ad_linked_by",
        "version",
    )
    fieldsets = (
        (
            "Conta SGPD",
            {
                "fields": (
                    "username",
                    "first_name",
                    "last_name",
                    "email",
                    "is_active",
                    "is_staff",
                    "is_superuser",
                    "must_change_password",
                    "last_login",
                    "date_joined",
                    "version",
                )
            },
        ),
        (
            "Vínculo administrativo com o AD",
            {
                "fields": (
                    "ad_identifier",
                    "ad_username",
                    "ad_linked_at",
                    "ad_linked_by",
                )
            },
        ),
    )


@admin.register(Role)
class RoleAdmin(ReadOnlyAdminMixin, admin.ModelAdmin):  # type: ignore[type-arg]
    list_display = ("code", "name", "is_active", "updated_at")
    search_fields = ("code", "name")


@admin.register(RoleAssignment)
class RoleAssignmentAdmin(ReadOnlyAdminMixin, admin.ModelAdmin):  # type: ignore[type-arg]
    list_display = ("user", "role", "scope_key", "is_active", "valid_from", "valid_until")
    list_filter = ("is_active", "scope_type", "role")


@admin.register(AccountAuditEvent)
class AccountAuditEventAdmin(
    ReadOnlyAdminMixin,
    admin.ModelAdmin,  # type: ignore[type-arg]
):
    list_display = ("occurred_at", "event_type", "actor", "target_user", "correlation_id")
    list_filter = ("event_type",)
    search_fields = ("entity_id", "correlation_id", "reason")
