"""Account administration URLs."""

from django.urls import path

from . import views

app_name = "accounts"

urlpatterns = [
    path("", views.home, name="home"),
    path("login/", views.SGPDLoginView.as_view(), name="login"),
    path("logout/", views.SGPDLogoutView.as_view(), name="logout"),
    path(
        "password/change/",
        views.change_own_password,
        name="change-own-password",
    ),
    path("users/", views.user_list, name="user-list"),
    path("users/new/", views.user_create, name="user-create"),
    path("users/<int:user_id>/", views.user_detail, name="user-detail"),
    path("users/<int:user_id>/edit/", views.user_update, name="user-update"),
    path(
        "users/<int:user_id>/password/",
        views.reset_password,
        name="reset-password",
    ),
    path(
        "users/<int:user_id>/roles/new/",
        views.assign_role,
        name="assign-role",
    ),
    path(
        "role-assignments/<int:assignment_id>/revoke/",
        views.revoke_role,
        name="revoke-role",
    ),
    path("users/<int:user_id>/ad/link/", views.link_ad, name="link-ad"),
    path("users/<int:user_id>/ad/unlink/", views.unlink_ad, name="unlink-ad"),
    path("roles/", views.role_list, name="role-list"),
    path("roles/new/", views.role_create, name="role-create"),
    path("roles/<int:role_id>/", views.role_update, name="role-update"),
    path("audit/", views.audit_list, name="audit-list"),
]
