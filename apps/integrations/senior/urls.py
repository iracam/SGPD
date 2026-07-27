from django.urls import path

from .api import (
    BranchListAPIView,
    CompanyListAPIView,
    EmployeeListAPIView,
    EmployeeTypeListAPIView,
)

app_name = "senior"

urlpatterns = [
    path("companies/", CompanyListAPIView.as_view(), name="companies"),
    path("branches/", BranchListAPIView.as_view(), name="branches"),
    path(
        "employee-types/",
        EmployeeTypeListAPIView.as_view(),
        name="employee-types",
    ),
    path("employees/", EmployeeListAPIView.as_view(), name="employees"),
]
