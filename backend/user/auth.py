"""用户认证：签名 Token + DRF 认证/权限类。

不新增 token 表：登录成功后用 django.core.signing 把 user_id 签成字符串，
前端放到 Authorization: Bearer <token> 里。
token 的签名密钥就是 settings.SECRET_KEY，所以更换 SECRET_KEY 会让所有 token 失效。
"""

from __future__ import annotations

from django.core import signing
from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed
from rest_framework.permissions import BasePermission

from sqldb.crud import user_crud
from sqldb.enums import DBStatus
from sqldb.models import User

TOKEN_SALT = "huishutai.user.token"
TOKEN_MAX_AGE = 60 * 60 * 24 * 7  # 7 天


def issue_token(user_id: int) -> str:
    """登录/注册成功后签发 token。"""
    return signing.dumps({"uid": user_id}, salt=TOKEN_SALT)


def parse_token(token: str) -> int:
    """校验签名和有效期，返回 user_id。"""
    try:
        payload = signing.loads(token, salt=TOKEN_SALT, max_age=TOKEN_MAX_AGE)
    except signing.BadSignature as exc:
        raise AuthenticationFailed("登录状态无效或已过期，请重新登录") from exc

    uid = payload.get("uid") if isinstance(payload, dict) else None
    if not isinstance(uid, int):
        raise AuthenticationFailed("登录状态无效，请重新登录")
    return uid


class SignedTokenAuthentication(BaseAuthentication):
    """从 Authorization: Bearer <token> 恢复当前用户。"""

    keyword = "Bearer"

    def authenticate(self, request):
        header = request.headers.get("Authorization", "")
        if not header:
            return None

        parts = header.split()
        if len(parts) != 2 or parts[0] != self.keyword:
            raise AuthenticationFailed("Authorization 头格式应为:Bearer <token>")

        result = user_crud.get_by_pk(parse_token(parts[1]))
        if result.code != DBStatus.SUCCESS:
            raise AuthenticationFailed("用户不存在或登录状态已失效")

        return (result.data, None)

    def authenticate_header(self, request) -> str:
        # 返回非空值，DRF 才会对未登录请求返回 401 而不是 403
        return self.keyword


class IsLoginUser(BasePermission):
    """只允许已登录用户访问。"""

    message = "请先登录"

    def has_permission(self, request, view) -> bool:
        return isinstance(request.user, User)
