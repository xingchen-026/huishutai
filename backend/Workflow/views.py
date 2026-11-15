"""Workflow HTTP 接口层。"""

from rest_framework import status as http_status
from rest_framework.decorators import api_view
from rest_framework.response import Response

from Workflow import services
from Workflow.result import WFResult, WFStatus

_HTTP_STATUS = {
    WFStatus.SUCCESS: http_status.HTTP_200_OK,
    WFStatus.PARAM_ERR: http_status.HTTP_400_BAD_REQUEST,
    WFStatus.NOT_FOUND: http_status.HTTP_404_NOT_FOUND,
    WFStatus.FORBIDDEN: http_status.HTTP_403_FORBIDDEN,
    WFStatus.CONFLICT: http_status.HTTP_409_CONFLICT,
    WFStatus.NODE_ERROR: http_status.HTTP_400_BAD_REQUEST,
    WFStatus.NODE_LOAD_ERROR: http_status.HTTP_500_INTERNAL_SERVER_ERROR,
    WFStatus.EXEC_ERROR: http_status.HTTP_400_BAD_REQUEST,
    WFStatus.UNKNOWN_ERR: http_status.HTTP_500_INTERNAL_SERVER_ERROR,
}


def _body(request) -> dict:
    data = request.data
    return data if isinstance(data, dict) else {}


def _respond(result: WFResult) -> Response:
    return Response(
        result.to_dict(),
        status=_HTTP_STATUS.get(result.code, http_status.HTTP_500_INTERNAL_SERVER_ERROR),
    )


@api_view(["GET", "POST"])
def workflows(request):
    if request.method == "GET":
        return _respond(services.list_workflows(request.user))
    return _respond(services.create_workflow(request.user, _body(request)))


@api_view(["GET", "PATCH", "DELETE"])
def workflow_detail(request, workflow_id: int):
    if request.method == "GET":
        return _respond(services.get_workflow(request.user, workflow_id))
    if request.method == "PATCH":
        return _respond(services.update_workflow(request.user, workflow_id, _body(request)))
    return _respond(services.delete_workflow(request.user, workflow_id))


@api_view(["GET"])
def workflow_events(request, workflow_id: int):
    try:
        after = int(request.query_params.get("after") or 0)
    except (TypeError, ValueError):
        after = 0
    try:
        limit = int(request.query_params.get("limit") or 100)
    except (TypeError, ValueError):
        limit = 100
    return _respond(services.list_events(request.user, workflow_id, after, limit))


@api_view(["POST"])
def workflow_nodes(request, workflow_id: int):
    return _respond(services.add_node(request.user, workflow_id, _body(request)))


@api_view(["PATCH", "DELETE"])
def workflow_node_detail(request, workflow_id: int, node_key: str):
    if request.method == "PATCH":
        return _respond(services.update_node(request.user, workflow_id, node_key, _body(request)))
    return _respond(services.delete_node(request.user, workflow_id, node_key))


@api_view(["POST"])
def workflow_edges(request, workflow_id: int):
    return _respond(services.add_relation(request.user, workflow_id, _body(request)))


@api_view(["DELETE"])
def workflow_edge_detail(request, workflow_id: int, edge_id: int):
    return _respond(services.delete_relation(request.user, workflow_id, edge_id))


@api_view(["GET", "POST"])
def workflow_members(request, workflow_id: int):
    if request.method == "GET":
        result = services.get_workflow(request.user, workflow_id)
        return _respond(result)
    return _respond(services.add_member(request.user, workflow_id, _body(request)))


@api_view(["DELETE"])
def workflow_member_detail(request, workflow_id: int, user_id: int):
    return _respond(services.remove_member(request.user, workflow_id, user_id))


@api_view(["POST"])
def workflow_import(request, workflow_id: int):
    return _respond(services.import_workflow(request.user, workflow_id, _body(request)))


@api_view(["GET"])
def workflow_export(request, workflow_id: int):
    return _respond(services.export_workflow(request.user, workflow_id))


@api_view(["POST"])
def workflow_run(request, workflow_id: int):
    return _respond(services.run_workflow(request.user, workflow_id))


@api_view(["GET"])
def node_types(request):
    return _respond(services.list_node_types())


@api_view(["GET"])
def node_type_detail(request, node_type: str):
    return _respond(services.get_node_type_meta(node_type))
