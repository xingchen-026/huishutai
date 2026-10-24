from django.urls import path

from user.views import (
    user_change_password,
    user_info,
    user_login,
    user_logout,
    user_register,
    username_available,
)

urlpatterns = [
    path("user/register/", user_register),
    path("user/login/", user_login),
    path("user/logout/", user_logout),
    path("user/info/", user_info),
    path("user/password/", user_change_password),
    path("user/check-username/", username_available),
]