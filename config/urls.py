"""Root URL configuration for SGPD."""

from django.conf import settings
from django.contrib import admin
from django.urls import include, path, re_path

from apps.core.views import manual, spa

urlpatterns = [
    path("api/v1/auth/", include("apps.accounts.api_urls")),
    path("api/v1/accounts/", include("apps.accounts.api_accounts_urls")),
    path("api/v1/evidence/", include("apps.evidence.urls")),
    path("api/v1/notifications/", include("apps.notifications.urls")),
    path("api/v1/pending-items/", include("apps.pending_items.urls")),
    path("api/v1/processes/", include("apps.offboarding.urls")),
    path("api/v1/reporting/", include("apps.reporting.urls")),
    path("api/v1/tasks/", include("apps.offboarding.task_urls")),
    path("api/v1/sectors/", include("apps.sectors.urls")),
    path("api/v1/settings/", include("apps.system_settings.urls")),
    path(
        "api/v1/workflow-config/",
        include("apps.templates_engine.urls"),
    ),
    path(
        "api/v1/references/",
        include("apps.integrations.senior.urls"),
    ),
    path("health/", include("apps.core.urls")),
    # Manuais operacionais abertos pela ajuda das telas, em aba nova. Não são
    # rota da SPA: o conteúdo é o HTML gerado em `docs/operacao/`.
    path("ajuda/<slug:slug>/", manual, name="manual"),
    # Catch-all da SPA. Precisa vir por último e excluir os prefixos servidos
    # pelo backend: sem a exclusão, uma rota inexistente sob /api/ devolveria o
    # HTML da SPA com 200 em vez de 404.
    re_path(
        r"^(?!api/|admin/|health/|static/|ajuda/).*$",
        spa,
        name="spa",
    ),
]

# Desligado, `admin/` continua fora do catch-all acima e responde 404 em vez de
# devolver o HTML da SPA.
if settings.ADMIN_SITE_ENABLED:
    urlpatterns.insert(0, path("admin/", admin.site.urls))
