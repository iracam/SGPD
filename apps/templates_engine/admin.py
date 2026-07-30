"""Read-only diagnostics for workflow configuration."""

from django.contrib import admin
from django.http import HttpRequest

from .models import (
    ChecklistTemplate,
    ChecklistTemplateItem,
    ChecklistTemplateVersion,
    GroupApplicabilityRule,
    ValidationGroup,
    ValidationGroupSector,
    ValidationGroupVersion,
    WorkflowConfigurationAuditEvent,
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


for model in (
    ChecklistTemplate,
    ChecklistTemplateVersion,
    ChecklistTemplateItem,
    ValidationGroup,
    ValidationGroupVersion,
    ValidationGroupSector,
    GroupApplicabilityRule,
    WorkflowConfigurationAuditEvent,
):
    admin_class = type(
        f"{model.__name__}Admin",
        (ReadOnlyAdminMixin, admin.ModelAdmin),
        {},
    )
    admin.site.register(model, admin_class)
