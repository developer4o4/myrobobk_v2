from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView

from .views import BotCreateOTPView, LoginByCodeView, MeView

urlpatterns = [
    path("auth/bot/create-otp/", BotCreateOTPView.as_view(), name="bot_create_otp"),
    path("auth/login/", LoginByCodeView.as_view(), name="login_by_code"),
    path("auth/token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    path("auth/me/", MeView.as_view(), name="me"),
]
