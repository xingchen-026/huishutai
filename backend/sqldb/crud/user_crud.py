"""
用户表相关的数据库操作（数据访问层）。

约定：
  - 这个文件只做「查、增、改、删」，不做业务判断。
  - 不返回 DBResult，不判断"用户名重复该返回什么 code"，那些在 views 里做。
  - 查不到一律返回 None，由调用方自己决定怎么处理。
"""

from sqldb.models import User, UserInfo


def get_user_by_username(username: str):
    """按用户名查用户，查不到返回 None"""
    return User.objects.filter(username=username).first()


def get_user_by_id(user_id):
    """按主键 id 查用户，查不到返回 None"""
    return User.objects.filter(id=user_id).first()


def username_exists(username: str) -> bool:
    """用户名是否已被占用"""
    return User.objects.filter(username=username).exists()


def create_user(username: str, raw_password: str) -> User:
    """
    创建用户：
      1. 用 model 自带的 set_password 加密密码
      2. 写 user 表
      3. 顺手建一条空的 user_info 资料记录（一对一）
    返回新建好的 User 对象
    """
    user = User(username=username)
    user.set_password(raw_password)
    user.save()

    UserInfo.objects.get_or_create(user=user)
    return user


def get_user_info(user: User):
    """取某个用户的资料记录，没有就返回 None"""
    return UserInfo.objects.filter(user=user).first()
