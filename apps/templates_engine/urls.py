from django.urls import path

from . import api

app_name = "workflow-configuration-api"

urlpatterns = [
    path(
        "templates/",
        api.ChecklistTemplateListCreateView.as_view(),
        name="template-list",
    ),
    path(
        "templates/<int:template_id>/versions/",
        api.ChecklistTemplateVersionCreateView.as_view(),
        name="template-version-create",
    ),
    path(
        "template-versions/<int:version_id>/publish/",
        api.ChecklistTemplatePublishView.as_view(),
        name="template-version-publish",
    ),
    path(
        "groups/",
        api.ValidationGroupListCreateView.as_view(),
        name="group-list",
    ),
    path(
        "groups/<int:group_id>/versions/",
        api.ValidationGroupVersionCreateView.as_view(),
        name="group-version-create",
    ),
    path(
        "group-versions/<int:version_id>/publish/",
        api.ValidationGroupPublishView.as_view(),
        name="group-version-publish",
    ),
]
