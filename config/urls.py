"""Root URL configuration for SGPD."""

from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path(
        "api/v1/references/",
        include("apps.integrations.senior.urls"),
    ),
    path("health/", include("apps.core.urls")),
]
