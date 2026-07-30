from django.contrib import admin
from django.http import HttpRequest

from .models import PendingComment, PendingItem, PendingItemLine


class ReadOnlyAdmin(admin.ModelAdmin):  # type: ignore[type-arg]
    def has_add_permission(self, request: HttpRequest) -> bool:
        return False

    def has_change_permission(self, request: HttpRequest, obj: object | None = None) -> bool:
        return False

    def has_delete_permission(self, request: HttpRequest, obj: object | None = None) -> bool:
        return False


admin.site.register((PendingItem, PendingItemLine, PendingComment), ReadOnlyAdmin)
