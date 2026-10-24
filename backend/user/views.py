"""
用户业务接口（业务层）。

约定：
  - 这里只做业务逻辑：拿参数、调 sqldb.crud、判断 DBResult、返回 HTTP 响应。
  - 不出现 User.objects / UserInfo.objects 这类 ORM 操作，数据库访问全部走 sqldb。
  - 密码哈希/校验属于业务逻辑，用 django.contrib.auth.hashers 完成，不写进模型。
"""

import re

from django.contrib.auth.hashers import check_password, make_password
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.db import transaction
from rest_framework import status as http_status
from rest_framework.decorators import (
    api_view,
    authentication_classes,
    permission_classes,
)
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from sqldb.crud import user_crud, user_info_crud
from sqldb.enums import DBStatus
from sqldb.result import DBResult
from user.auth import IsLoginUser, issue_token


USERNAME_RE = re.compile(r"^[A-Za-z0-9_\u4e00-\u9fa5]{3,50}$")
PHONE_RE = re.compile(r"^1[3-9][0-9]{9}$")
GENDERS = {"male", "female", "unknown"}


# ==================== 通用小工具 ====================
def _payload(request) -> dict:
    """只接受对象形态的请求体，避免 request.data 是 list 时 .get 报错。"""
    data = request.data
    return data if isinstance(data, dict) else {}


def _ok(message: str, data=None) -> Response:
    return Response(
        DBResult(code=DBStatus.SUCCESS, message=message, data=data).to_dict()
    )

def _fail(
    message: str,
    code: DBStatus = DBStatus.UNKNOWN_ERR,
    status: int = http_status.HTTP_400_BAD_REQUEST,
) -> Response:
    return Response(
        DBResult(code=code, message=message).to_dict(),
        status=status,
    )

def _username_error(username: str) -> str | None:
    if not username:
        return "用户名称不能为空"
    if not USERNAME_RE.fullmatch(username):
        return "用户名只能包含中文、字母、数字、下划线，长度 3-50位"
    return None

def _password_error(password: str) -> str | None:
    if not password:
        return "密码不能为空"
    if len(password) < 6:
        return "密码至少 6 位"
    if len(password) > 128:
        return "密码不能超过 128 位"
    return None

def _email_error(email: str) -> str | None:
    if not email:
        return None
    try:
        validate_email(email)
    except ValidationError:
        return "邮箱格式不正确"
    return None

def _phone_error(phone: str) -> str | None:
    if not phone:
        return None
    if not PHONE_RE.fullmatch(phone):
        return "手机号格式不正确"
    return None

def _profile_dict(user, info) -> dict:
    return {
        "user_id": user.id,
        "username": user.username,
        "email": info.email or "",
        "phone": info.phone or "",
        "gender": info.gender or "unknown",
    }

def _get_or_create_info(user):
    """老数据可能没有 user_info，读资料时顺手补一条空记录。"""
    result = user_info_crud.get_by_user_id(user.id)
    if result.code == DBStatus.NOT_FOUND:
        return user_info_crud.create(user=user, email="", phone="", gender="unknown")
    return result


# ==================== 注册 ====================
@api_view(["POST"])
@authentication_classes([])
@permission_classes([AllowAny])
def user_register(request):
    data = _payload(request)
    username = (data.get("username") or "").strip()
    password = data.get("password") or ""
    confirm_password = data.get("confirm_password")

    error = _username_error(username) or _password_error(password)
    if error:
        return _fail(error)
    if confirm_password is not None and confirm_password != password:
        return _fail("两次输入的密码不一致")

     # 友好提示；真正的唯一性由数据库 unique 约束兜底
    exists = user_crud.exists(username=username)
    if exists.code != DBStatus.SUCCESS:
        return _fail(
            "注册失败，请稍后重试",
            DBStatus.UNKNOWN_ERR,
            http_status.HTTP_500_INTERNAL_SERVER_ERROR,
        )
    if exists.data:
        return _fail("用户名已存在", DBStatus.DUPLICATE_ERR)

    # user + user_info 要么都成功，要么都回滚
    with transaction.atomic():
        created = user_crud.create(
            username=username,
            password=make_password(password),
        )
        if created.code != DBStatus.SUCCESS:
            transaction.set_rollback(True)
            if created.code == DBStatus.DUPLICATE_ERR:
                return _fail("用户名已存在", DBStatus.DUPLICATE_ERR)
            return _fail(
                "注册失败，请稍后重试",
                created.code,
                http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        user = created.data

        info = user_info_crud.create(
            user=user,
            email="",
            phone="",
            gender="unknown",
        )
        if info.code != DBStatus.SUCCESS:
            transaction.set_rollback(True)
            return _fail(
                "用户资料初始化失败，请稍后重试",
                DBStatus.UNKNOWN_ERR,
                http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    # 注册后直接登录，前端拿到 token 就不用再让用户登录一次
    return _ok(
        "注册成功",
        {
            "token": issue_token(user.id),
            "user_id": user.id,
            "username": user.username,
        },
    )

# ==================== 登录 ====================
@api_view(["POST"])
@authentication_classes([])
@permission_classes([AllowAny])
def user_login(request):
    data = _payload(request)
    username = (data.get("username") or "").strip()
    password = data.get("password") or ""

    if not username or not password:
        return _fail("用户名或密码不能为空")

    result = user_crud.get_by_username(username)
    if result.code == DBStatus.NOT_FOUND:
        # 不区分“用户不存在”和“密码错误”，避免暴露账号是否存在
        return _fail("用户名或密码错误")
    if result.code != DBStatus.SUCCESS:
        return _fail(
            "登录失败，请稍后重试",
            result.code,
            http_status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

    user = result.data
    if not check_password(password, user.password):
        return _fail("用户名或密码错误")

    return _ok(
        "登录成功",
        {
            "token": issue_token(user.id),
            "user_id": user.id,
            "username": user.username,
        },
    )

#==========退出==========
@api_view(["POST"])
@authentication_classes([])
@permission_classes([AllowAny])
def user_logout(request):
    # 签名 token 是无状态的，服务端没有会话可删；前端清掉本地 token 即可
    return _ok("已退出登录")

# ==================== 用户名查重 ====================
@api_view(["GET"])
@authentication_classes([])
@permission_classes([AllowAny])
def username_available(request):
    username = (request.query_params.get("username") or "").strip()

    error = _username_error(username)
    if error:
        return _fail(error)

    result = user_crud.exists(username=username)
    if result.code != DBStatus.SUCCESS:
        return _fail(
            "查询失败，请稍后重试",
            result.code,
            http_status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

    return _ok("ok", {"username": username, "available": not result.data})



# ==================== 个人资料：GET 查看 / PATCH 修改 ====================
@api_view(["GET", "PATCH"])
@permission_classes([IsLoginUser])
def user_info(request):
    user = request.user

    info_result = _get_or_create_info(user)
    if info_result.code != DBStatus.SUCCESS:
        return _fail(
            "读取用户资料失败",
            info_result.code,
            http_status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

    if request.method == "GET":
        return _ok("ok", _profile_dict(user, info_result.data))

    data = _payload(request)
    fields = {}

    if "email" in data:
        email = (data.get("email") or "").strip()
        error = _email_error(email)
        if error:
            return _fail(error)
        fields["email"] = email

    if "phone" in data:
        phone = (data.get("phone") or "").strip()
        error = _phone_error(phone)
        if error:
            return _fail(error)
        fields["phone"] = phone

    if "gender" in data:
        gender = (data.get("gender") or "").strip()
        if gender not in GENDERS:
            return _fail("性别取值不正确")
        fields["gender"] = gender

    if not fields:
        return _fail("没有需要更新的字段")

    updated = user_info_crud.update_by_user_id(user.id, **fields)
    if updated.code != DBStatus.SUCCESS:
        return _fail(
            "资料保存失败，请稍后重试",
            updated.code,
            http_status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

    return _ok("资料已更新", _profile_dict(user, updated.data))


# ==================== 修改密码 ====================
@api_view(["POST"])
@permission_classes([IsLoginUser])
def user_change_password(request):
    data = _payload(request)
    old_password = data.get("old_password") or ""
    new_password = data.get("new_password") or ""
    confirm_password = data.get("confirm_password")

    if not old_password or not new_password:
        return _fail("原密码和新密码不能为空")

    error = _password_error(new_password)
    if error:
        return _fail(error)
    if confirm_password is not None and confirm_password != new_password:
        return _fail("两次输入的新密码不一致")
    if not check_password(old_password, request.user.password):
        return _fail("原密码错误")
    if check_password(new_password, request.user.password):
        return _fail("新密码不能与原密码相同")

    result = user_crud.update(
        request.user.id,
        password=make_password(new_password),
    )
    if result.code != DBStatus.SUCCESS:
        return _fail(
            "密码修改失败，请稍后重试",
            result.code,
            http_status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

    return _ok("密码修改成功，请重新登录")