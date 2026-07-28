"""Account administration endpoints consumed by the SPA."""

from django.urls import path

from . import api_accounts, api_directory

app_name = "accounts-api"

urlpatterns = [
    path(
        "directory/status/",
        api_directory.DirectoryStatusView.as_view(),
        name="directory-status",
    ),
    path(
        "directory/users/",
        api_directory.DirectoryUserSearchView.as_view(),
        name="directory-user-search",
    ),
    path(
        "directory/groups/",
        api_directory.DirectoryGroupSearchView.as_view(),
        name="directory-group-search",
    ),
    path(
        "directory/users/create/",
        api_directory.DirectoryUserCreateView.as_view(),
        name="directory-user-create",
    ),
    path("users/", api_accounts.UserListCreateView.as_view(), name="user-list"),
    path("users/<int:user_id>/", api_accounts.UserDetailView.as_view(), name="user-detail"),
    path(
        "users/<int:user_id>/reset-password/",
        api_accounts.UserResetPasswordView.as_view(),
        name="user-reset-password",
    ),
    path(
        "users/<int:user_id>/roles/",
        api_accounts.UserRoleAssignmentView.as_view(),
        name="user-assign-role",
    ),
    path(
        "users/<int:user_id>/ad-link/",
        api_accounts.UserAdLinkView.as_view(),
        name="user-ad-link",
    ),
    path(
        "users/<int:user_id>/ad-unlink/",
        api_accounts.UserAdUnlinkView.as_view(),
        name="user-ad-unlink",
    ),
    path(
        "role-assignments/<int:assignment_id>/revoke/",
        api_accounts.RoleAssignmentRevokeView.as_view(),
        name="role-assignment-revoke",
    ),
    path("roles/", api_accounts.RoleListCreateView.as_view(), name="role-list"),
    path("roles/<int:role_id>/", api_accounts.RoleDetailView.as_view(), name="role-detail"),
    path("permissions/", api_accounts.PermissionListView.as_view(), name="permission-list"),
    path("audit/", api_accounts.AuditListView.as_view(), name="audit-list"),
]
