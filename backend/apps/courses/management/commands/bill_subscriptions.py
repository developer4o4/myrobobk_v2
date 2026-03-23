import logging
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from apps.courses.models import CourseSubscription, add_one_month

logger = logging.getLogger(__name__)
User = get_user_model()


class Command(BaseCommand):
    help = "Muddati tugagan obunalarni qayta hisob-kitob qiladi yoki o'chiradi."

    def handle(self, *args, **options):
        now = timezone.now()
        qs = (
            CourseSubscription.objects
            .select_related("course")
            .filter(active=True, expires_at__lte=now)
        )

        count_ok = 0
        count_off = 0
        count_err = 0

        for sub in qs:
            try:
                with transaction.atomic():
                    u = User.objects.select_for_update().get(pk=sub.user_id)
                    sub_locked = CourseSubscription.objects.select_for_update().get(pk=sub.pk)

                    price = Decimal(str(sub_locked.course.price))

                    if u.balance >= price:
                        u.balance -= price
                        u.save(update_fields=["balance"])
                        sub_locked.expires_at = add_one_month(now)
                        sub_locked.last_billed_at = now
                        sub_locked.active = True
                        sub_locked.save(update_fields=["expires_at", "last_billed_at", "active"])
                        count_ok += 1
                        logger.info("Charged: user=%s course=%s", u.pk, sub_locked.course_id)
                    else:
                        sub_locked.active = False
                        sub_locked.save(update_fields=["active"])
                        count_off += 1
                        logger.info("Deactivated: user=%s course=%s", u.pk, sub_locked.course_id)

            except Exception as e:
                count_err += 1
                logger.error("bill_subscriptions error for sub=%s: %s", sub.pk, e)

        msg = f"Hisob-kitob yakunlandi: to'landi={count_ok}, o'chirildi={count_off}, xato={count_err}"
        self.stdout.write(self.style.SUCCESS(msg))
        logger.info(msg)
