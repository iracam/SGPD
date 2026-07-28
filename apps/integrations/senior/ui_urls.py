"""Server-rendered Senior reference URLs."""

from django.urls import path

from .views import (
    BranchOptionsView,
    EmployeeOptionsView,
    EmployeeTypeOptionsView,
    SeniorReferenceSelectionView,
)

app_name = "senior-ui"

urlpatterns = [
    path("", SeniorReferenceSelectionView.as_view(), name="selection"),
    path("branches/", BranchOptionsView.as_view(), name="branches"),
    path(
        "employee-types/",
        EmployeeTypeOptionsView.as_view(),
        name="employee-types",
    ),
    path("employees/", EmployeeOptionsView.as_view(), name="employees"),
]
