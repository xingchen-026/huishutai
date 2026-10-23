"""
用户业务接口（业务层）。

约定：
  - 这里只做业务逻辑：拿参数、调 crud、判断结果、返回 DBResult。
  - 不出现 User.objects / UserInfo.objects 这类 ORM 操作，那是 crud 的事。
"""
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status as http_status

from sqldb.result import DBResult
from sqldb.enums import DBStatus
from sqldb.crud import (
    get_user_by_username,
    get_user_by_id,
    username_exists,
    create_user,
    get_user_info,
)


#===========登录===========
@api_view(['POST'])
def user_login(request):
    username = request.data.get('username')
    password = request.data.get('password')

    if not username or not password:
        return Response(
            DBResult(code=DBStatus.UNKNOWN_ERR, message="用户名或密码不能为空").to_dict(),
            status=http_status.HTTP_400_BAD_REQUEST
        )

    # 从数据层拿用户，不再直接写 User.objects.get
    user = get_user_by_username(username)
    if user is None:
        return Response(
            DBResult(code=DBStatus.NOT_FOUND, message="用户名不存在").to_dict(),
            status=http_status.HTTP_404_NOT_FOUND
        )

    if not user.check_password(password):
        return Response(
            DBResult(code=DBStatus.UNKNOWN_ERR, message="密码错误").to_dict(),
            status=http_status.HTTP_400_BAD_REQUEST,
        )

    return Response(
        DBResult(
            code=DBStatus.SUCCESS,
            message="登录成功",
            data={"user_id": user.id, "username": user.username},
        ).to_dict()
    )


#===========注册===========
@api_view(['POST'])
def user_register(request):
    username = request.data.get('username')
    password = request.data.get('password')

    if not username or not password:
        return Response(
            DBResult(code=DBStatus.UNKNOWN_ERR, message="用户名或密码不能为空").to_dict(),
            status=http_status.HTTP_400_BAD_REQUEST
        )

    if username_exists(username):
        return Response(
            DBResult(code=DBStatus.DUPLICATE_ERR, message="用户名已存在").to_dict(),
            status=http_status.HTTP_400_BAD_REQUEST,
        )

    # 创建用户 + 建空资料记录，都封在 crud 里了
    user = create_user(username, password)

    return Response(
        DBResult(
            code=DBStatus.SUCCESS,
            message="注册成功",
            data={"user_id": user.id, "username": user.username},
        ).to_dict()
    )


#===========获取用户信息===========
@api_view(['GET'])
def user_info(request):
    user_id = request.query_params.get('user_id')

    if not user_id:
        return Response(
            DBResult(code=DBStatus.UNKNOWN_ERR, message="缺少用户ID").to_dict(),
            status=http_status.HTTP_400_BAD_REQUEST,
        )

    user = get_user_by_id(user_id)
    if user is None:
        return Response(
            DBResult(code=DBStatus.NOT_FOUND, message="用户不存在").to_dict(),
            status=http_status.HTTP_404_NOT_FOUND,
        )

    info = get_user_info(user)

    return Response(
        DBResult(
            code=DBStatus.SUCCESS,
            message="ok",
            data={
                "user_id": user.id,
                "username": user.username,
                "email": info.email if info else "",
                "phone": info.phone if info else "",
                "gender": info.gender if info else "unknown",
            },
        ).to_dict()
    )



