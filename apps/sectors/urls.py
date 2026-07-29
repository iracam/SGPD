from django.urls import path

from . import api

app_name = "sectors-api"

urlpatterns = [
    path("", api.SectorListCreateView.as_view(), name="sector-list"),
    path(
        "responsible-candidates/",
        api.SectorResponsibleCandidatesView.as_view(),
        name="responsible-candidates",
    ),
    path("<int:sector_id>/", api.SectorDetailView.as_view(), name="sector-detail"),
]
