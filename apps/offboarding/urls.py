from django.urls import path

from apps.pending_items import api as pending_items_api

from . import api

app_name = "offboarding-api"

urlpatterns = [
    path("", api.ProcessListCreateView.as_view(), name="process-list"),
    path(
        "<uuid:process_uuid>/draft/",
        api.ProcessDraftDetailView.as_view(),
        name="process-draft",
    ),
    path(
        "<uuid:process_uuid>/tasks/",
        api.ProcessTaskListView.as_view(),
        name="process-tasks",
    ),
    path(
        "<uuid:process_uuid>/draft/selection/",
        api.ProcessDraftSelectionView.as_view(),
        name="process-draft-selection",
    ),
    path(
        "<uuid:process_uuid>/start/",
        api.ProcessStartView.as_view(),
        name="process-start",
    ),
    path(
        "<uuid:process_uuid>/readiness/",
        api.ProcessReadinessView.as_view(),
        name="process-readiness",
    ),
    path(
        "<uuid:process_uuid>/release/",
        api.ProcessReleaseView.as_view(),
        name="process-release",
    ),
    path(
        "<uuid:process_uuid>/processing/",
        api.ProcessTerminationProcessingView.as_view(),
        name="process-processing",
    ),
    path(
        "<uuid:process_uuid>/close/",
        api.ProcessCloseView.as_view(),
        name="process-close",
    ),
    path(
        "<uuid:process_uuid>/cancel/",
        api.ProcessCancelView.as_view(),
        name="process-cancel",
    ),
    path(
        "<uuid:process_uuid>/reopen/",
        api.ProcessReopenView.as_view(),
        name="process-reopen",
    ),
    # `GET` avisa o que a exclusão destrói; `POST` executa e nada volta atrás.
    path(
        "<uuid:process_uuid>/purge/",
        api.ProcessPurgeView.as_view(),
        name="process-purge",
    ),
    # A consolidação é do domínio de pendências, mas a conferência é por
    # processo: a rota mora aqui e a view continua no app dono do dado.
    path(
        "<uuid:process_uuid>/amounts/",
        pending_items_api.ProcessAmountsView.as_view(),
        name="process-amounts",
    ),
]
