"""LLMapi HTTP 接口层：供应商模板 / 配置 / 模型目录 / 统一调用网关。

权限沿用全局 DRF 配置（需要登录），所有数据按 request.user 隔离。
"""

from rest_framework import status as http_status
from rest_framework.decorators import api_view
from rest_framework.response import Response

from LLMapi import services
from LLMapi.result import LLMResult, LLMStatus

_HTTP_STATUS = {
    LLMStatus.SUCCESS: http_status.HTTP_200_OK,
    LLMStatus.PARAM_ERR: http_status.HTTP_400_BAD_REQUEST,
    LLMStatus.NOT_FOUND: http_status.HTTP_404_NOT_FOUND,
    LLMStatus.PROVIDER_AUTH_ERR: http_status.HTTP_400_BAD_REQUEST,
    LLMStatus.PROVIDER_UNREACHABLE: http_status.HTTP_502_BAD_GATEWAY,
    LLMStatus.PROVIDER_API_ERR: http_status.HTTP_502_BAD_GATEWAY,
    LLMStatus.MODEL_UNSUPPORTED: http_status.HTTP_400_BAD_REQUEST,
    LLMStatus.DB_ERR: http_status.HTTP_500_INTERNAL_SERVER_ERROR,
    LLMStatus.UNKNOWN_ERR: http_status.HTTP_500_INTERNAL_SERVER_ERROR,
}


def _body(request) -> dict:
    data = request.data
    return data if isinstance(data, dict) else {}


def _respond(result: LLMResult) -> Response:
    return Response(
        result.to_dict(),
        status=_HTTP_STATUS.get(result.code, http_status.HTTP_500_INTERNAL_SERVER_ERROR),
    )


@api_view(["GET"])
def provider_templates(request):
    """GET /llm/provider-templates/ 内置供应商模板 + 模型分类。"""
    return _respond(services.list_provider_templates())


@api_view(["GET", "POST"])
def providers(request):
    """GET 列出我的供应商配置；POST 新增配置并尝试拉取模型。"""
    if request.method == "GET":
        return _respond(services.list_providers(request.user))
    return _respond(services.create_provider(request.user, _body(request)))


@api_view(["GET", "PATCH", "DELETE"])
def provider_detail(request, provider_id: int):
    if request.method == "GET":
        return _respond(services.get_provider(request.user, provider_id))
    if request.method == "PATCH":
        return _respond(services.update_provider(request.user, provider_id, _body(request)))
    return _respond(services.delete_provider(request.user, provider_id))


@api_view(["POST"])
def provider_refresh_models(request, provider_id: int):
    """POST 重新在线拉取该供应商的模型列表。"""
    return _respond(services.refresh_models(request.user, provider_id))


@api_view(["GET", "POST"])
def provider_models(request, provider_id: int):
    """GET 该供应商下的模型；POST 手动登记模型（拉不到列表时使用）。"""
    if request.method == "GET":
        return _respond(services.list_provider_models(request.user, provider_id))
    return _respond(services.add_manual_model(request.user, provider_id, _body(request)))


@api_view(["GET"])
def models(request):
    """GET /llm/models/ 我的模型列表，按分类分组；支持 ?category= & ?provider_id=。"""
    return _respond(services.list_models(request.user, request.query_params.dict()))


@api_view(["PATCH", "DELETE"])
def model_detail(request, model_pk: int):
    if request.method == "PATCH":
        return _respond(services.update_model(request.user, model_pk, _body(request)))
    return _respond(services.delete_model(request.user, model_pk))


@api_view(["POST"])
def chat(request):
    """POST /llm/chat/ 统一对话调用：{model_id, messages, params?}。"""
    return _respond(services.chat_completion(request.user, _body(request)))


@api_view(["POST"])
def embeddings(request):
    """POST /llm/embeddings/ 统一嵌入调用：{model_id, input, params?}。"""
    return _respond(services.create_embeddings(request.user, _body(request)))
