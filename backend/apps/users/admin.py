from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from .models import TelegramOTP, User


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ("phone", "username", "balance", "is_active", "is_staff", "date_joined")
    list_filter = ("is_active", "is_staff")
    search_fields = ("phone", "username")
    ordering = ("-date_joined",)
    fieldsets = (
        (None, {"fields": ("phone", "password")}),
        ("Shaxsiy", {"fields": ("username", "first_name", "last_name", "balance")}),
        ("Ruxsatlar", {"fields": ("is_active", "is_staff", "is_superuser", "groups", "user_permissions")}),
        ("Sanalar", {"fields": ("date_joined", "last_login")}),
    )
    add_fieldsets = (
        (None, {
            "classes": ("wide",),
            "fields": ("phone", "password1", "password2"),
        }),
    )
    readonly_fields = ("date_joined", "last_login")


@admin.register(TelegramOTP)
class TelegramOTPAdmin(admin.ModelAdmin):
    list_display = ("phone", "code", "expires_at", "attempts_left", "created_at")
    list_filter = ("created_at",)
    search_fields = ("phone",)
    readonly_fields = ("created_at",)
