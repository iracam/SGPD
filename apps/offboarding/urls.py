from django.urls import path

from . import api

app_name = "offboarding-api"

urlpatterns = [
    path("", api.ProcessListCreateView.as_view(), name="process-list"),
    path(
        "manager-candidates/",
        api.ManagerCandidateListView.as_view(),
        name="manager-candidates",
    ),
]
