"""
apps/courses/views_payme.py
===========================
Payme Subscribe API — karta qo'shish va kurs sotib olish viewlari.
"""
import uuid
import logging

from django.core.cache import cache
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.courses.models import Course, CourseSubscription, PaymeCard
from apps.courses.payme_service import (
    PaymeError,
    cards_create,
    cards_get_verify_code,
    cards_remove,
    cards_verify,
    charge_card,
)

logger = logging.getLogger(__name__)

# OTP cache timeout (sekund)
OTP_CACHE_TTL = 300  # 5 daqiqa


# ──────────────────────────────────────────────────────────────────────
#  Yordamchi: cache key
# ──────────────────────────────────────────────────────────────────────

def _otp_cache_key(user_id) -> str:
    return f"payme_otp:{user_id}"


# ──────────────────────────────────────────────────────────────────────
#  1-qadam: Karta raqamini yuborish → SMS keladi
# ──────────────────────────────────────────────────────────────────────

class CardCreateView(APIView):
    """
    POST /payments/cards/create/
    Body: { "card_number": "8600123456781234", "card_expire": "0327" }
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        number = request.data.get("card_number", "")
        expire = request.data.get("card_expire", "")  # "0327" yoki "03/27"

        if not number or not expire:
            return Response(
                {"detail": "card_number va card_expire majburiy"},
                status=400,
            )

        # Normalize
        number = number.replace(" ", "")
        expire = expire.replace("/", "")

        if len(number) != 16 or not number.isdigit():
            return Response({"detail": "Karta raqami 16 ta raqamdan iborat bo'lishi kerak"}, status=400)
        if len(expire) != 4 or not expire.isdigit():
            return Response({"detail": "Muddat MMYY formatida bo'lishi kerak (masalan: 0327)"}, status=400)

        try:
            token = cards_create(number, expire)
            cards_get_verify_code(token)
        except PaymeError as e:
            return Response({"detail": str(e)}, status=400)

        # Token ni Redis cache da saqlaymiz (DB ga emas — hali tasdiqlanmagan)
        cache.set(_otp_cache_key(request.user.id), token, timeout=OTP_CACHE_TTL)

        return Response({"detail": "SMS kod yuborildi. 5 daqiqa ichida tasdiqlang."})


# ──────────────────────────────────────────────────────────────────────
#  2-qadam: SMS kodni tasdiqlash → karta DB ga saqlanadi
# ──────────────────────────────────────────────────────────────────────

class CardVerifyView(APIView):
    """
    POST /payments/cards/verify/
    Body: { "code": "123456" }
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        code = request.data.get("code", "").strip()
        if not code:
            return Response({"detail": "code majburiy"}, status=400)

        token = cache.get(_otp_cache_key(request.user.id))
        if not token:
            return Response(
                {"detail": "Sessiya tugagan. Iltimos, kartani qaytadan kiriting."},
                status=400,
            )

        try:
            card_data = cards_verify(token, code)
        except PaymeError as e:
            return Response({"detail": str(e)}, status=400)

        # Karta DB ga saqlanadi
        card, created = PaymeCard.objects.get_or_create(
            card_token=card_data["token"],
            defaults={
                "user": request.user,
                "card_number": card_data["number"],  # masked: "8600 **** **** 1234"
                "card_expire": card_data["expire"],
                "is_active": True,
                # Birinchi karta bo'lsa — default qilinadi
                "is_default": not PaymeCard.objects.filter(
                    user=request.user, is_active=True
                ).exists(),
            },
        )

        # Agar boshqa user ning kartasi bo'lsa (xavfsizlik tekshiruvi)
        if card.user_id != request.user.id:
            return Response({"detail": "Karta boshqa foydalanuvchiga tegishli"}, status=400)

        # Cache tozalash
        cache.delete(_otp_cache_key(request.user.id))

        return Response({
            "card_id": str(card.id),
            "card_number": card.card_number,
            "card_expire": card.card_expire,
            "is_default": card.is_default,
            "created": created,
        })


# ──────────────────────────────────────────────────────────────────────
#  Kartalar ro'yxati va o'chirish
# ──────────────────────────────────────────────────────────────────────

class CardListView(APIView):
    """
    GET /payments/cards/
    Foydalanuvchining barcha faol kartalarini qaytaradi.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        cards = PaymeCard.objects.filter(user=request.user, is_active=True).order_by("-is_default", "-created_at")
        data = [
            {
                "id": str(c.id),
                "card_number": c.card_number,
                "card_expire": c.card_expire,
                "is_default": c.is_default,
            }
            for c in cards
        ]
        return Response(data)


class CardDeleteView(APIView):
    """
    DELETE /payments/cards/<card_id>/
    Kartani o'chiradi (Payme + DB).
    """
    permission_classes = [IsAuthenticated]

    def delete(self, request, card_id):
        try:
            card = PaymeCard.objects.get(id=card_id, user=request.user, is_active=True)
        except PaymeCard.DoesNotExist:
            return Response({"detail": "Karta topilmadi"}, status=404)

        # Aktiv obunalar tekshiruvi
        active_subs = CourseSubscription.objects.filter(
            payme_card=card, active=True, auto_renew=True
        ).exists()
        if active_subs:
            return Response(
                {"detail": "Bu karta aktiv obunalar bilan bog'liq. Avval obunani to'xtating."},
                status=400,
            )

        try:
            cards_remove(card.card_token)
        except PaymeError as e:
            logger.warning("Payme cards.remove failed card=%s: %s", card.id, e)
            # Payme da o'chirilmasa ham DB dan o'chiramiz

        card.is_active = False
        card.save(update_fields=["is_active"])
        return Response({"detail": "Karta o'chirildi"})


class CardSetDefaultView(APIView):
    """
    POST /payments/cards/<card_id>/set-default/
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, card_id):
        try:
            card = PaymeCard.objects.get(id=card_id, user=request.user, is_active=True)
        except PaymeCard.DoesNotExist:
            return Response({"detail": "Karta topilmadi"}, status=404)

        card.set_as_default()
        return Response({"detail": "Default karta o'rnatildi"})


# ──────────────────────────────────────────────────────────────────────
#  Kurs sotib olish (Payme orqali)
# ──────────────────────────────────────────────────────────────────────

class BuyCourseView(APIView):
    """
    POST /courses/buy/
    Body: { "course_id": "<uuid>", "card_id": "<uuid>" }

    card_id ixtiyoriy — yo'q bo'lsa default karta ishlatiladi.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        course_id = request.data.get("course_id")
        card_id = request.data.get("card_id")

        if not course_id:
            return Response({"detail": "course_id majburiy"}, status=400)

        # Kursni topish
        try:
            course = Course.objects.get(id=course_id, is_active=True)
        except Course.DoesNotExist:
            return Response({"detail": "Kurs topilmadi"}, status=404)

        # Kartani tanlash
        qs = PaymeCard.objects.filter(user=request.user, is_active=True)
        if card_id:
            card = qs.filter(id=card_id).first()
        else:
            card = qs.filter(is_default=True).first() or qs.first()

        if not card:
            return Response(
                {"detail": "Faol karta topilmadi. Avval karta qo'shing."},
                status=400,
            )

        # To'lov
        order_id = str(uuid.uuid4())
        try:
            charge_card(
                token=card.card_token,
                amount_uzs=int(course.price),
                order_id=order_id,
                description=f"MyRobo: {course.title} — 1 oylik obuna",
            )
        except PaymeError as e:
            return Response({"detail": str(e)}, status=400)

        # Obunani yozish
        sub = CourseSubscription.start_or_renew_payme(
            user=request.user,
            course=course,
            card=card,
        )

        return Response({
            "detail": "Muvaffaqiyatli sotib olindi!",
            "course": course.title,
            "expires_at": sub.expires_at,
            "auto_renew": sub.auto_renew,
            "card_number": card.card_number,
        })


# ──────────────────────────────────────────────────────────────────────
#  Obunani bekor qilish (auto_renew o'chirish)
# ──────────────────────────────────────────────────────────────────────

class CancelSubscriptionView(APIView):
    """
    POST /courses/<course_id>/cancel-subscription/
    Avtoyengilashni o'chiradi (obuna muddat oxirigacha davom etadi).
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, course_id):
        try:
            sub = CourseSubscription.objects.get(
                user=request.user, course_id=course_id, active=True
            )
        except CourseSubscription.DoesNotExist:
            return Response({"detail": "Aktiv obuna topilmadi"}, status=404)

        sub.auto_renew = False
        sub.save(update_fields=["auto_renew"])

        return Response({
            "detail": "Avtoyengilash o'chirildi.",
            "expires_at": sub.expires_at,
        })