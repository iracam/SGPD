from django.urls import path

from . import api

app_name = "sector-responsibilities-api"

urlpatterns = [
    path(
        "",
        api.SectorResponsibleListCreateView.as_view(),
        name="responsibility-list",
    ),
    path(
        "candidates/",
        api.SectorResponsibleCandidatesView.as_view(),
        name="responsibility-candidates",
    ),
    path(
        "<int:responsibility_id>/",
        api.SectorResponsibleDetailView.as_view(),
        name="responsibility-detail",
    ),
    path(
        "<int:responsibility_id>/revoke/",
        api.SectorResponsibleRevokeView.as_view(),
        name="responsibility-revoke",
    ),
]
