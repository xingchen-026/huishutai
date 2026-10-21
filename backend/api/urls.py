from django.urls import path
from user.views import user_login, user_info

urlpatterns = [
    path("user/login/", user_login),          # 用户登录
    path("user/info/", user_info),            # 用户信息
]