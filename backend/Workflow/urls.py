from django.urls import path

from Workflow import views

urlpatterns = [
    path("workflows/", views.workflows, name="workflow-list"),
    path("workflows/<int:workflow_id>/", views.workflow_detail, name="workflow-detail"),
    path(
        "workflows/<int:workflow_id>/events/",
        views.workflow_events,
        name="workflow-events",
    ),
    path("workflows/<int:workflow_id>/nodes/", views.workflow_nodes, name="workflow-nodes"),
    path(
        "workflows/<int:workflow_id>/nodes/<str:node_key>/",
        views.workflow_node_detail,
        name="workflow-node-detail",
    ),
    path("workflows/<int:workflow_id>/edges/", views.workflow_edges, name="workflow-edges"),
    path(
        "workflows/<int:workflow_id>/edges/<int:edge_id>/",
        views.workflow_edge_detail,
        name="workflow-edge-detail",
    ),
    path(
        "workflows/<int:workflow_id>/members/",
        views.workflow_members,
        name="workflow-members",
    ),
    path(
        "workflows/<int:workflow_id>/members/<int:user_id>/",
        views.workflow_member_detail,
        name="workflow-member-detail",
    ),
    path(
        "workflows/<int:workflow_id>/import/",
        views.workflow_import,
        name="workflow-import",
    ),
    path(
        "workflows/<int:workflow_id>/export/",
        views.workflow_export,
        name="workflow-export",
    ),
    path("workflows/<int:workflow_id>/run/", views.workflow_run, name="workflow-run"),
    path("node-types/", views.node_types, name="workflow-node-types"),
    path(
        "node-types/<str:node_type>/",
        views.node_type_detail,
        name="workflow-node-type-detail",
    ),
]
