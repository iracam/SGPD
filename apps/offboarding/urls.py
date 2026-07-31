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
    # A consolidação é do domínio de pendências, mas a conferência é por
    # processo: a rota mora aqui e a view continua no app dono do dado.
    path(
        "<uuid:process_uuid>/amounts/",
        pending_items_api.ProcessAmountsView.as_view(),
        name="process-amounts",
    ),
]
