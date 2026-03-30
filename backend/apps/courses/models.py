import logging
from calendar import monthrange
from decimal import Decimal
from django.utils.text import slugify

from django.conf import settings
from django.db import models, transaction
from django.utils import timezone

from apps.common.models import BaseModel

logger = logging.getLogger(__name__)
User = settings.AUTH_USER_MODEL


def add_one_month(dt):
    """Berilgan sanadan 1 oy keyingi sana (oy oxirini to'g'ri hisoblab)."""
    year = dt.year
    month = dt.month + 1
    if month == 13:
        month = 1
        year += 1
    day = min(dt.day, monthrange(year, month)[1])
    return dt.replace(year=year, month=month, day=day)

class CourseType(BaseModel):
    title = models.CharField(max_length=256)
    slug = models.CharField(max_length=255, unique=True, blank=True)

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title)
        super().save(*args, **kwargs)
    

class Course(BaseModel):
    course_type = models.ForeignKey(CourseType,on_delete=models.SET_NULL, null=True,blank=True)
    title = models.CharField(max_length=255)
    about = models.TextField(blank=True)
    image = models.ImageField(upload_to="courses/images/", blank=True, null=True)
    price = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    slug = models.CharField(max_length=255, unique=True, blank=True)

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title)
        super().save(*args, **kwargs)
    class Meta:
        indexes = [models.Index(fields=["is_active", "-created_at"])]

    def __str__(self):
        return self.title


class Section(BaseModel):
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name="sections")
    title = models.CharField(max_length=255)
    order = models.PositiveIntegerField(default=1)
    slug = models.CharField(max_length=255, unique=True, blank=True)

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title)
        super().save(*args, **kwargs)
    class Meta:
        unique_together = ("course", "order")
        ordering = ["order", "id"]

    def __str__(self):
        return f"{self.course_id} - {self.title}"


class Topic(BaseModel):
    TYPE_CHOICES = (
        ("content", "Content"),
        ("code", "Code"),
    )
    section = models.ForeignKey(Section, on_delete=models.CASCADE, related_name="topics")
    title = models.CharField(max_length=255)
    about = models.TextField(blank=True)
    video_url = models.CharField(max_length=500, blank=True, null=True)
    topic_type = models.CharField(max_length=10, choices=TYPE_CHOICES, default="content")
    order = models.PositiveIntegerField(default=1)
    slug = models.CharField(max_length=255, unique=True, blank=True)

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title)
        super().save(*args, **kwargs)
    class Meta:
        unique_together = ("section", "order")
        ordering = ["order", "id"]

    @property
    def is_code(self) -> bool:
        return self.topic_type == "code"

    def __str__(self):
        return self.title


class Problem(BaseModel):
    topic = models.ForeignKey(Topic, on_delete=models.CASCADE, related_name="problem")
    title = models.CharField(max_length=255)
    statement = models.TextField()
    sample_input = models.TextField(blank=True)
    sample_output = models.TextField(blank=True)

    def __str__(self):
        return self.title


class TestCase(BaseModel):
    problem = models.ForeignKey(Problem, on_delete=models.CASCADE, related_name="tests")
    input_data = models.TextField()
    output_data = models.TextField()
    is_hidden = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.problem_id} test#{self.id}"


class Submission(BaseModel):
    LANG_CHOICES = (
        ("py", "Python"),
        ("c", "C"),
        ("cpp", "C++"),
    )
    STATUS_CHOICES = (
        ("pending", "Pending"),
        ("accepted", "Accepted"),
        ("rejected", "Rejected"),
        ("error", "Error"),
    )

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="submissions")
    problem = models.ForeignKey(Problem, on_delete=models.CASCADE, related_name="submissions")
    language = models.CharField(max_length=10, choices=LANG_CHOICES)
    source_code = models.TextField()
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default="pending")
    error_message = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=["user", "problem"]),
            models.Index(fields=["status"]),
        ]

    def __str__(self):
        return f"{self.user_id} -> {self.problem_id} ({self.status})"


# class CourseSubscription(BaseModel):
#     user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="course_subscriptions")
#     course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name="subscriptions")
#     started_at = models.DateTimeField(default=timezone.now)
#     expires_at = models.DateTimeField()
#     active = models.BooleanField(default=True)
#     last_billed_at = models.DateTimeField(blank=True, null=True)

#     class Meta:
#         unique_together = ("user", "course")
#         indexes = [
#             models.Index(fields=["user", "course"]),
#             models.Index(fields=["expires_at", "active"]),
#         ]

#     def __str__(self):
#         return f"{self.user_id}-{self.course_id} active={self.active}"

#     def is_valid(self) -> bool:
#         return self.active and timezone.now() < self.expires_at

#     @classmethod
#     def start_or_renew(cls, user, course):
#         """
#         Kursni sotib olish yoki obunani yangilash.
#         Balansi yetarli bo'lmasa ValueError ko'taradi.
#         """
#         from django.apps import apps
#         UserModel = apps.get_model("users", "User")

#         with transaction.atomic():
#             u = UserModel.objects.select_for_update().get(pk=user.pk)
#             price = Decimal(str(course.price))

#             if u.balance < price:
#                 raise ValueError("Balans yetarli emas")

#             u.balance -= price
#             u.save(update_fields=["balance"])

#             now = timezone.now()
#             sub, created = cls.objects.select_for_update().get_or_create(
#                 user=u,
#                 course=course,
#                 defaults={
#                     "started_at": now,
#                     "expires_at": add_one_month(now),
#                     "active": True,
#                     "last_billed_at": now,
#                 },
#             )

#             if not created:
#                 sub.active = True
#                 base = now if sub.expires_at <= now else sub.expires_at
#                 sub.expires_at = add_one_month(base)
#                 sub.last_billed_at = now
#                 sub.save(update_fields=["active", "expires_at", "last_billed_at"])

#             logger.info(
#                 "Subscription: user=%s course=%s created=%s expires=%s",
#                 u.pk, course.pk, created, sub.expires_at,
#             )
#             return sub



"""
apps/courses/models.py ga QO'SHISH KERAK BO'LGAN O'ZGARISHLAR
==============================================================
Mavjud faylga quyidagilarni qo'shing.
"""

import logging
import uuid
from calendar import monthrange
from decimal import Decimal

from django.conf import settings
from django.db import models, transaction
from django.utils import timezone
from django.utils.text import slugify

from apps.common.models import BaseModel

logger = logging.getLogger(__name__)
User = settings.AUTH_USER_MODEL


def add_one_month(dt):
    """Berilgan sanadan 1 oy keyingi sana (oy oxirini to'g'ri hisoblab)."""
    year = dt.year
    month = dt.month + 1
    if month == 13:
        month = 1
        year += 1
    day = min(dt.day, monthrange(year, month)[1])
    return dt.replace(year=year, month=month, day=day)


# ──────────────────────────────────────────────────────────────────────
#  YANGI MODEL: PaymeCard
# ──────────────────────────────────────────────────────────────────────

class PaymeCard(BaseModel):
    """Foydalanuvchining saqlangan Payme karta tokeni."""

    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="payme_cards"
    )
    # Payme qaytargan masked raqam: "8600 **** **** 1234"
    card_number = models.CharField(max_length=25)
    # "03/27" formatda
    card_expire = models.CharField(max_length=5)
    # Payme Subscribe API tokeni — maxfiy, faqat backend ishlatadi
    card_token = models.CharField(max_length=512, unique=True)
    is_active = models.BooleanField(default=True)
    is_default = models.BooleanField(default=False)

    class Meta:
        indexes = [
            models.Index(fields=["user", "is_active"]),
        ]

    def __str__(self):
        return f"{self.user_id} — {self.card_number}"

    def set_as_default(self):
        """Ushbu kartani default qilish, boshqalardan olib tashlash."""
        PaymeCard.objects.filter(user=self.user, is_default=True).update(is_default=False)
        self.is_default = True
        self.save(update_fields=["is_default"])


# ──────────────────────────────────────────────────────────────────────
#  MAVJUD MODELLAR (o'zgarishsiz qoladi)
# ──────────────────────────────────────────────────────────────────────

class CourseType(BaseModel):
    title = models.CharField(max_length=256)
    slug = models.CharField(max_length=255, unique=True, blank=True)

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title)
        super().save(*args, **kwargs)
    
    def __str__(self):
        return self.title

class Course(BaseModel):
    course_type = models.ForeignKey(
        CourseType, on_delete=models.SET_NULL, null=True, blank=True
    )
    title = models.CharField(max_length=255)
    about = models.TextField(blank=True)
    image = models.ImageField(upload_to="courses/images/", blank=True, null=True)
    price = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    slug = models.CharField(max_length=255, unique=True, blank=True)

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title)
        super().save(*args, **kwargs)

    class Meta:
        indexes = [models.Index(fields=["is_active", "-created_at"])]

    def __str__(self):
        return self.title


class Section(BaseModel):
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name="sections")
    title = models.CharField(max_length=255)
    order = models.PositiveIntegerField(default=1)
    slug = models.CharField(max_length=255, unique=True, blank=True)

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title)
        super().save(*args, **kwargs)

    class Meta:
        unique_together = ("course", "order")
        ordering = ["order", "id"]

    def __str__(self):
        return f"{self.course_id} - {self.title}"


class Topic(BaseModel):
    TYPE_CHOICES = (("content", "Content"), ("code", "Code"))
    section = models.ForeignKey(Section, on_delete=models.CASCADE, related_name="topics")
    title = models.CharField(max_length=255)
    about = models.TextField(blank=True)
    video_url = models.CharField(max_length=500, blank=True, null=True)
    topic_type = models.CharField(max_length=10, choices=TYPE_CHOICES, default="content")
    order = models.PositiveIntegerField(default=1)
    slug = models.CharField(max_length=255, unique=True, blank=True)

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title)
        super().save(*args, **kwargs)

    class Meta:
        unique_together = ("section", "order")
        ordering = ["order", "id"]

    @property
    def is_code(self) -> bool:
        return self.topic_type == "code"

    def __str__(self):
        return self.title


class Problem(BaseModel):
    topic = models.ForeignKey(Topic, on_delete=models.CASCADE, related_name="problem")
    title = models.CharField(max_length=255)
    statement = models.TextField()
    sample_input = models.TextField(blank=True)
    sample_output = models.TextField(blank=True)

    def __str__(self):
        return self.title


class TestCase(BaseModel):
    problem = models.ForeignKey(Problem, on_delete=models.CASCADE, related_name="tests")
    input_data = models.TextField()
    output_data = models.TextField()
    is_hidden = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.problem_id} test#{self.id}"


class Submission(BaseModel):
    LANG_CHOICES = (("py", "Python"), ("c", "C"), ("cpp", "C++"))
    STATUS_CHOICES = (
        ("pending", "Pending"),
        ("accepted", "Accepted"),
        ("rejected", "Rejected"),
        ("error", "Error"),
    )
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="submissions")
    problem = models.ForeignKey(Problem, on_delete=models.CASCADE, related_name="submissions")
    language = models.CharField(max_length=10, choices=LANG_CHOICES)
    source_code = models.TextField()
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default="pending")
    error_message = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=["user", "problem"]),
            models.Index(fields=["status"]),
        ]

    def __str__(self):
        return f"{self.user_id} -> {self.problem_id} ({self.status})"


# ──────────────────────────────────────────────────────────────────────
#  CourseSubscription — YANGILANGAN (payme_card + auto_renew qo'shildi)
# ──────────────────────────────────────────────────────────────────────

class CourseSubscription(BaseModel):
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="course_subscriptions"
    )
    course = models.ForeignKey(
        Course, on_delete=models.CASCADE, related_name="subscriptions"
    )
    started_at = models.DateTimeField(default=timezone.now)
    expires_at = models.DateTimeField()
    active = models.BooleanField(default=True)
    last_billed_at = models.DateTimeField(blank=True, null=True)

    # ── YANGI FIELDLAR ──────────────────────────────────────────────
    payme_card = models.ForeignKey(
        PaymeCard,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="subscriptions",
        help_text="Avtoyengilash uchun ishlatiladigan karta",
    )
    auto_renew = models.BooleanField(
        default=True,
        help_text="True bo'lsa Celery avtomatik yangilaydi",
    )
    # Avtoyengilash muvaffaqiyatsiz bo'lsa log uchun
    last_renew_error = models.TextField(blank=True, null=True)
    # ────────────────────────────────────────────────────────────────

    class Meta:
        unique_together = ("user", "course")
        indexes = [
            models.Index(fields=["user", "course"]),
            models.Index(fields=["expires_at", "active"]),
            models.Index(fields=["auto_renew", "active", "expires_at"]),
        ]

    def __str__(self):
        return f"{self.user_id}-{self.course_id} active={self.active}"

    def is_valid(self) -> bool:
        return self.active and timezone.now() < self.expires_at

    # ── Eski metod (balance orqali) — o'zgarmaydi ───────────────────
    @classmethod
    def start_or_renew(cls, user, course):
        from django.apps import apps
        UserModel = apps.get_model("users", "User")

        with transaction.atomic():
            u = UserModel.objects.select_for_update().get(pk=user.pk)
            price = Decimal(str(course.price))
            if u.balance < price:
                raise ValueError("Balans yetarli emas")
            u.balance -= price
            u.save(update_fields=["balance"])

            now = timezone.now()
            sub, created = cls.objects.select_for_update().get_or_create(
                user=u, course=course,
                defaults={
                    "started_at": now,
                    "expires_at": add_one_month(now),
                    "active": True,
                    "last_billed_at": now,
                },
            )
            if not created:
                sub.active = True
                base = now if sub.expires_at <= now else sub.expires_at
                sub.expires_at = add_one_month(base)
                sub.last_billed_at = now
                sub.save(update_fields=["active", "expires_at", "last_billed_at"])

            logger.info(
                "Subscription (balance): user=%s course=%s created=%s expires=%s",
                u.pk, course.pk, created, sub.expires_at,
            )
            return sub

    # ── YANGI metod: Payme orqali ────────────────────────────────────
    @classmethod
    def start_or_renew_payme(cls, user, course, card: "PaymeCard"):
        """
        Payme to'lovi muvaffaqiyatli bo'lgandan KEYIN chaqiriladi.
        Balansni olmaydi — to'lov allaqachon Payme orqali yechilgan.
        """
        now = timezone.now()
        with transaction.atomic():
            sub, created = cls.objects.select_for_update().get_or_create(
                user=user,
                course=course,
                defaults={
                    "started_at": now,
                    "expires_at": add_one_month(now),
                    "active": True,
                    "last_billed_at": now,
                    "payme_card": card,
                    "auto_renew": True,
                    "last_renew_error": None,
                },
            )
            if not created:
                base = now if sub.expires_at <= now else sub.expires_at
                sub.expires_at = add_one_month(base)
                sub.active = True
                sub.last_billed_at = now
                sub.payme_card = card
                sub.auto_renew = True
                sub.last_renew_error = None
                sub.save(update_fields=[
                    "active", "expires_at", "last_billed_at",
                    "payme_card", "auto_renew", "last_renew_error",
                ])

            logger.info(
                "Subscription (Payme): user=%s course=%s created=%s card=%s expires=%s",
                user.pk, course.pk, created, card.pk, sub.expires_at,
            )
            return sub