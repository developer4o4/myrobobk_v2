from django.contrib import admin
from .models import (
    Course, Section, Topic,
    Problem, TestCase, Submission,
    CourseSubscription
)


# ─── INLINE (ichida ko‘rsatish uchun) ──────────────────────────────
class SectionInline(admin.TabularInline):
    model = Section
    extra = 1


class TopicInline(admin.TabularInline):
    model = Topic
    extra = 1


class TestCaseInline(admin.TabularInline):
    model = TestCase
    extra = 1


# ─── COURSE ────────────────────────────────────────────────────────
@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = ("id", "title", "price", "is_active", "created_at")
    list_filter = ("is_active",)
    search_fields = ("title",)
    inlines = [SectionInline]


# ─── SECTION ───────────────────────────────────────────────────────
@admin.register(Section)
class SectionAdmin(admin.ModelAdmin):
    list_display = ("id", "title", "course", "order")
    list_filter = ("course",)
    ordering = ("course", "order")
    inlines = [TopicInline]


# ─── TOPIC ─────────────────────────────────────────────────────────
@admin.register(Topic)
class TopicAdmin(admin.ModelAdmin):
    list_display = ("id", "title", "section", "topic_type", "order")
    list_filter = ("topic_type", "section")
    search_fields = ("title",)
    ordering = ("section", "order")


# ─── PROBLEM ───────────────────────────────────────────────────────
@admin.register(Problem)
class ProblemAdmin(admin.ModelAdmin):
    list_display = ("id", "title", "topic")
    search_fields = ("title",)
    list_filter = ("topic",)
    inlines = [TestCaseInline]


# ─── TEST CASE ─────────────────────────────────────────────────────
@admin.register(TestCase)
class TestCaseAdmin(admin.ModelAdmin):
    list_display = ("id", "problem", "is_hidden")
    list_filter = ("is_hidden",)


# ─── SUBMISSION ────────────────────────────────────────────────────
@admin.register(Submission)
class SubmissionAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "problem", "language", "status", "created_at")
    list_filter = ("status", "language")
    search_fields = ("user__id", "problem__title")
    readonly_fields = ("created_at",)


# ─── SUBSCRIPTION ─────────────────────────────────────────────────
@admin.register(CourseSubscription)
class CourseSubscriptionAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "course", "active", "expires_at")
    list_filter = ("active", "course")
    search_fields = ("user__id", "course__title")
    readonly_fields = ("started_at", "last_billed_at")