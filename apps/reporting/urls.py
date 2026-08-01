from django.urls import path

from . import api

app_name = "reporting-api"

urlpatterns = [
    path("dashboard/", api.DashboardView.as_view(), name="dashboard"),
    path("reports/", api.ReportsView.as_view(), name="reports"),
    path("exports/<slug:dataset>.csv", api.ExportView.as_view(), name="export"),
    path("operations/", api.OperationsView.as_view(), name="operations"),
]
