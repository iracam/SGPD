from django.contrib import admin
from django.http import HttpRequest

from .models import Evidence


@admin.register(Evidence)
class EvidenceAdmin(admin.ModelAdmin):  # type: ignore[type-arg]
    list_display = ("uuid", "task", "classification", "size_bytes", "uploaded_at")
    list_filter = ("classification", "is_active")
    search_fields = ("uuid", "sha256")

    def has_add_permission(self, request: HttpRequest) -> bool:
        return False

    def has_change_permission(self, request: HttpRequest, obj: object | None = None) -> bool:
        return False

    def has_delete_permission(self, request: HttpRequest, obj: object | None = None) -> bool:
        return False
