from django.urls import path

from . import api

app_name = "evidence-api"

urlpatterns = [
    path("", api.EvidenceListUploadView.as_view(), name="evidence-list"),
    path(
        "<uuid:evidence_uuid>/download/",
        api.EvidenceDownloadView.as_view(),
        name="evidence-download",
    ),
]
