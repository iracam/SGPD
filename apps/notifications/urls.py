from django.urls import path

from . import api

app_name = "notifications-api"

urlpatterns = [
    path("", api.NotificationListView.as_view(), name="notification-list"),
    path(
        "<uuid:notification_uuid>/reprocess/",
        api.NotificationReprocessView.as_view(),
        name="notification-reprocess",
    ),
]
