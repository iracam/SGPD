from django.urls import path

from . import api

app_name = "reporting-api"

urlpatterns = [
    path("dashboard/", api.DashboardView.as_view(), name="dashboard"),
]
