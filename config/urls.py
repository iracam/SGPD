"""Root URL configuration for SGPD."""

from django.contrib import admin
from django.urls import include, path, re_path

from apps.core.views import spa

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/v1/auth/", include("apps.accounts.api_urls")),
    path("api/v1/accounts/", include("apps.accounts.api_accounts_urls")),
    path(
        "api/v1/references/",
        include("apps.integrations.senior.urls"),
    ),
    path("health/", include("apps.core.urls")),
    # Catch-all da SPA. Precisa vir por último e excluir os prefixos servidos
    # pelo backend: sem a exclusão, uma rota inexistente sob /api/ devolveria o
    # HTML da SPA com 200 em vez de 404.
    re_path(
        r"^(?!api/|admin/|health/|static/).*$",
        spa,
        name="spa",
    ),
]
