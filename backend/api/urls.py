from django.urls import path
from user.views import user_login, user_info

# 创建路由器并注册视图集
router = DefaultRouter()
router.register(r'books', BookViewSet)

urlpatterns = [
    path("user/login/", user_login),          # 用户登录
    path("user/info/", user_info),            # 用户信息
]