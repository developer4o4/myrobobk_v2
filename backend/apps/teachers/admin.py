from django.contrib import admin

from .models import Teacher


@admin.register(Teacher)
class TeacherAdmin(admin.ModelAdmin):
    list_display = ("username", "job", "is_active", "created_at")
    list_filter = ("is_active",)
    search_fields = ("username", "slug")
    prepopulated_fields = {"slug": ("username",)}
    filter_horizontal = ("courses",)
    readonly_fields = ("created_at", "updated_at")
