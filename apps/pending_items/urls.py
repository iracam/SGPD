from django.urls import path

from . import api

app_name = "pending-items-api"

urlpatterns = [
    path("", api.PendingItemListCreateView.as_view(), name="pending-list"),
    path("<uuid:pending_uuid>/status/", api.PendingStatusView.as_view(), name="pending-status"),
    path(
        "<uuid:pending_uuid>/comments/",
        api.PendingCommentView.as_view(),
        name="pending-comment",
    ),
]
