import logging
import os

from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.throttling import AnonRateThrottle
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken

from .models import TelegramOTP
from .serializers import (
    BotCreateOTPSerializer,
    LoginByCodeSerializer,
    UserMeSerializer,
    UserUpdateSerializer,
)
from .utils import expires_after, generate_6digit_code, normalize_phone

logger = logging.getLogger(__name__)
User = get_user_model()


# ──── OTP rate-limit: IP boshiga 10 ta/soat ────
class OTPLoginThrottle(AnonRateThrottle):
    rate = "10/hour"


def _bot_secret_ok(request) -> bool:
    """Bot secret header tekshiruvi — constant-time compare."""
    import hmac
    got = request.headers.get("X-BOT-SECRET", "")
    need = os.getenv("BOT_OTP_SECRET", "")
    if not need:
        return False
    return hmac.compare_digest(got, need)


class BotCreateOTPView(APIView):
    """
    Faqat Telegram bot chaqiradi.
    POST /user/auth/bot/create-otp/
    Headers: X-BOT-SECRET: <secret>
    Body: {phone, username?, ttl_minutes?}
    """
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        if not _bot_secret_ok(request):
            logger.warning("BotCreateOTP: noto'g'ri secret, IP=%s", request.META.get("REMOTE_ADDR"))
            return Response({"detail": "Forbidden"}, status=status.HTTP_403_FORBIDDEN)

        s = BotCreateOTPSerializer(data=request.data)
        s.is_valid(raise_exception=True)

        phone = normalize_phone(s.validated_data["phone"])
        username = (s.validated_data.get("username") or "").strip() or None
        ttl = int(s.validated_data.get("ttl_minutes") or 3)

        # Unique code generatsiya (10 urinish)
        code = None
        for _ in range(10):
            c = generate_6digit_code()
            if not TelegramOTP.objects.filter(code=c).exists():
                code = c
                break
        if not code:
            return Response(
                {"detail": "Code generatsiya bo'lmadi, qayta urinib ko'ring."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        # Eski OTPlarni tozalash
        TelegramOTP.objects.filter(phone=phone).delete()

        TelegramOTP.objects.create(
            phone=phone,
            code=code,
            username=username,
            expires_at=expires_after(ttl),
            attempts_left=5,
        )

        return Response({"ok": True, "code": code, "expires_in_min": ttl})


class LoginByCodeView(APIView):
    """
    Foydalanuvchi saytdan code yuboradi → JWT oladi.
    POST /user/auth/login/
    Body: {code: "123456"}
    """
    permission_classes = [permissions.AllowAny]
    throttle_classes = [OTPLoginThrottle]

    def post(self, request):
        s = LoginByCodeSerializer(data=request.data)
        s.is_valid(raise_exception=True)

        code = (s.validated_data["code"] or "").strip()

        otp = TelegramOTP.objects.filter(code=code).first()
        if not otp:
            return Response(
                {"detail": "Code topilmadi yoki ishlatilgan."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if timezone.now() > otp.expires_at:
            otp.delete()
            return Response(
                {"detail": "Code muddati tugagan."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if otp.attempts_left <= 0:
            otp.delete()
            return Response(
                {"detail": "Urinishlar tugagan."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        phone = normalize_phone(otp.phone)
        username = (otp.username or "").strip() or None

        # Code bir marta ishlatiladi
        otp.delete()

        defaults = {}
        if username:
            defaults["username"] = username

        user, created = User.objects.get_or_create(phone=phone, defaults=defaults)

        if not created and username and not (user.username or "").strip():
            user.username = username
            user.save(update_fields=["username"])

        refresh = RefreshToken.for_user(user)
        logger.info("Login: user=%s created=%s", user.pk, created)

        return Response({
            "access": str(refresh.access_token),
            "refresh": str(refresh),
            "user": {
                "id": user.id,
                "phone": user.phone,
                "username": getattr(user, "username", None),
            },
        })


class MeView(APIView):
    """GET/PATCH /user/auth/me/"""
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        return Response(UserMeSerializer(request.user).data)

    def patch(self, request):
        serializer = UserUpdateSerializer(
            request.user, data=request.data, partial=True
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(UserMeSerializer(request.user).data)
