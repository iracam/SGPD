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
    path(
        "<uuid:pending_uuid>/amount/",
        api.PendingAmountRegisterView.as_view(),
        name="pending-amount",
    ),
    path(
        "<uuid:pending_uuid>/amount/assessment/",
        api.PendingAmountAssessView.as_view(),
        name="pending-amount-assessment",
    ),
    path(
        "<uuid:pending_uuid>/amount/contestation/",
        api.PendingAmountContestView.as_view(),
        name="pending-amount-contestation",
    ),
    path(
        "<uuid:pending_uuid>/amount/decision/",
        api.PendingAmountDecideView.as_view(),
        name="pending-amount-decision",
    ),
]
