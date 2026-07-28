"""Root URL configuration for SGPD."""

from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("accounts/", include("apps.accounts.urls")),
    path(
        "references/senior/",
        include("apps.integrations.senior.ui_urls"),
    ),
    path("api/v1/auth/", include("apps.accounts.api_urls")),
    path("api/v1/accounts/", include("apps.accounts.api_accounts_urls")),
    path(
        "api/v1/references/",
        include("apps.integrations.senior.urls"),
    ),
    path("health/", include("apps.core.urls")),
]
