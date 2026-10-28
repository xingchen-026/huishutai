"""文件上传接口（HTTP 层）。

权限沿用全局 DRF 配置（user.auth.IsLoginUser）：
请求必须带 Authorization: Bearer <token>，否则 401。
文件归属取 request.user.id，不接受前端传 user_id，避免越权。
"""

from rest_framework import status as http_status
from rest_framework.decorators import api_view
from rest_framework.response import Response

from files.services import save_uploaded_file
from sqldb.enums import DBStatus
from sqldb.result import DBResult

_HTTP_STATUS = {
    DBStatus.SUCCESS: http_status.HTTP_200_OK,
    DBStatus.PARAM_ERR: http_status.HTTP_400_BAD_REQUEST,
    DBStatus.NOT_FOUND: http_status.HTTP_404_NOT_FOUND,
    DBStatus.DUPLICATE_ERR: http_status.HTTP_409_CONFLICT,
    DBStatus.SERVICE_ERR: http_status.HTTP_503_SERVICE_UNAVAILABLE,
    DBStatus.UNKNOWN_ERR: http_status.HTTP_500_INTERNAL_SERVER_ERROR,
}


@api_view(["POST"])
def file_upload(request):
    """POST /files/upload/

    multipart/form-data，字段名固定为 file；
    data.url 是浏览器可直接打开的临时签名链接（默认 1 小时有效）。
    """
    uploaded_file = request.FILES.get("file")
    if uploaded_file is None:
        return Response(
            DBResult(DBStatus.PARAM_ERR, "请选择要上传的文件").to_dict(),
            status=http_status.HTTP_400_BAD_REQUEST,
        )

    result = save_uploaded_file(uploaded_file, request.user)
    return Response(
        result.to_dict(),
        status=_HTTP_STATUS.get(
            result.code, http_status.HTTP_500_INTERNAL_SERVER_ERROR
        ),
    )