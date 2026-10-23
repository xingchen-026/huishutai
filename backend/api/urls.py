from django.urls import path
from user.views import user_login, user_info, user_register
from rest_framework.routers import DefaultRouter
from .views import BookViewSet

# 图书接口视图集：暂时只注册未挂载，需要时在 urlpatterns 里 include(router.urls) 即可生效
router = DefaultRouter()
router.register(r'books', BookViewSet)

urlpatterns = [
    path("user/login/", user_login),          # 用户登录
    path("user/info/", user_info),           # 用户信息 
    path("user/register/", user_register)    # 用户注册
]