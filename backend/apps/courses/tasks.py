"""
apps/courses/tasks.py
=====================
Celery task: muddati tugayotgan obunalarni avtomatik yangilash.
"""
import logging
import uuid
from datetime import timedelta

from celery import shared_task
from django.utils import timezone

logger = logging.getLogger(__name__)

# Necha kun oldin tekshirilsin (muddati tugashidan 1 kun oldin)
RENEW_BEFORE_DAYS = 1


@shared_task(
    name="courses.auto_renew_subscriptions",
    bind=True,
    max_retries=0,          # retry qilmaymiz — keyingi kecha qayta ishlaydi
    ignore_result=True,
)
def auto_renew_subscriptions(self):
    """
    Har kecha 00:00 da Celery beat tomonidan ishga tushiriladi.

    Muddati (RENEW_BEFORE_DAYS) kun ichida tugaydigan,
    auto_renew=True bo'lgan barcha obunalarni Payme orqali yangilaydi.
    """
    from apps.courses.models import CourseSubscription, add_one_month
    from apps.courses.payme_service import PaymeError, charge_card

    now = timezone.now()
    threshold = now + timedelta(days=RENEW_BEFORE_DAYS)

    # Yangilash kerak bo'lgan obunalar
    subs = (
        CourseSubscription.objects
        .filter(
            active=True,
            auto_renew=True,
            expires_at__lte=threshold,
            payme_card__isnull=False,
            payme_card__is_active=True,
        )
        .select_related("course", "payme_card", "user")
    )

    total = subs.count()
    success_count = 0
    fail_count = 0

    logger.info("Auto-renew started: %d subscriptions to process", total)

    for sub in subs:
        try:
            charge_card(
                token=sub.payme_card.card_token,
                amount_uzs=int(sub.course.price),
                order_id=str(uuid.uuid4()),
                description=f"MyRobo: {sub.course.title} — avtoyengilash",
            )

            # Obunani uzaytirish
            base = now if sub.expires_at <= now else sub.expires_at
            sub.expires_at = add_one_month(base)
            sub.last_billed_at = now
            sub.last_renew_error = None
            sub.save(update_fields=["expires_at", "last_billed_at", "last_renew_error"])

            success_count += 1
            logger.info(
                "Auto-renew OK: sub=%s user=%s course=%s new_expires=%s",
                sub.pk, sub.user_id, sub.course_id, sub.expires_at,
            )

            # Telegram bot orqali xabar yuborish (ixtiyoriy)
            _notify_user_success(sub)

        except PaymeError as e:
            fail_count += 1
            error_msg = str(e)

            # Xatoni DB ga yozish
            sub.last_renew_error = error_msg
            sub.save(update_fields=["last_renew_error"])

            logger.error(
                "Auto-renew FAILED: sub=%s user=%s course=%s error=%s",
                sub.pk, sub.user_id, sub.course_id, error_msg,
            )

            # Foydalanuvchiga xabar yuborish
            _notify_user_failure(sub, error_msg)

        except Exception as e:
            fail_count += 1
            logger.exception(
                "Auto-renew UNEXPECTED ERROR: sub=%s error=%s", sub.pk, e
            )

    logger.info(
        "Auto-renew finished: total=%d success=%d fail=%d",
        total, success_count, fail_count,
    )
    return {"total": total, "success": success_count, "fail": fail_count}


# ──────────────────────────────────────────────────────────────────────
#  Yordamchi: Telegram bot xabarlari (ixtiyoriy)
# ──────────────────────────────────────────────────────────────────────

def _notify_user_success(sub):
    """
    To'lov muvaffaqiyatli bo'lganda foydalanuvchiga xabar yuborish.
    Bot ishlatilmasa — o'chirib qo'ysa bo'ladi.
    """
    try:
        from apps.users.models import User
        user = User.objects.filter(pk=sub.user_id).first()
        if not user or not hasattr(user, "telegram_id"):
            return

        # Bot import (agar bot app mavjud bo'lsa)
        # from bot.utils import send_message
        # send_message(
        #     chat_id=user.telegram_id,
        #     text=(
        #         f"✅ <b>{sub.course.title}</b> kursiga obuna yangilandi!\n"
        #         f"📅 Muddat: {sub.expires_at.strftime('%d.%m.%Y')}\n"
        #         f"💳 Karta: {sub.payme_card.card_number}"
        #     )
        # )
        pass
    except Exception as e:
        logger.warning("Notify success failed: %s", e)


def _notify_user_failure(sub, error: str):
    """
    To'lov muvaffaqiyatsiz bo'lganda foydalanuvchiga xabar yuborish.
    """
    try:
        # from bot.utils import send_message
        # send_message(
        #     chat_id=user.telegram_id,
        #     text=(
        #         f"❌ <b>{sub.course.title}</b> kursiga obuna yangilanmadi!\n"
        #         f"Sabab: {error}\n"
        #         f"Iltimos, kartangizni tekshiring: /my_cards"
        #     )
        # )
        pass
    except Exception as e:
        logger.warning("Notify failure failed: %s", e)