from django.urls import path

from api.views import route_list
from files.views import file_upload
from user.views import (
    user_change_password,
    user_info,
    user_login,
    user_logout,
    user_register,
    username_available,
)

urlpatterns = [
    path("user/register/", user_register, name="user-register"),
    path("user/login/", user_login, name="user-login"),
    path("user/logout/", user_logout, name="user-logout"),
    path("user/info/", user_info, name="user-info"),
    path("user/password/", user_change_password, name="user-password"),
    path("user/check-username/", username_available, name="user-check-username"),
    path("files/upload/", file_upload, name="file-upload"),
    path("routes/", route_list, name="route-list"),
]