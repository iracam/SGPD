"""Authentication and authorization-context endpoints consumed by the SPA."""

from django.urls import path

from . import api

app_name = "auth-api"

urlpatterns = [
    path("csrf/", api.CsrfView.as_view(), name="csrf"),
    path("login/", api.LoginView.as_view(), name="login"),
    path("logout/", api.LogoutView.as_view(), name="logout"),
    path("me/", api.CurrentUserView.as_view(), name="me"),
    path("context/", api.AuthorizationContextView.as_view(), name="context"),
    path(
        "change-password/",
        api.ChangeOwnPasswordView.as_view(),
        name="change-password",
    ),
]
