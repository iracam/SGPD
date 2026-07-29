from django.urls import path

from . import api

app_name = "offboarding-task-api"

urlpatterns = [
    path("", api.SectorTaskListView.as_view(), name="task-list"),
    path("<int:task_id>/", api.SectorTaskDetailView.as_view(), name="task-detail"),
    path("<int:task_id>/start/", api.SectorTaskStartView.as_view(), name="task-start"),
    path(
        "<int:task_id>/complete/",
        api.SectorTaskCompleteView.as_view(),
        name="task-complete",
    ),
]
