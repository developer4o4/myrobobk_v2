from django.contrib import admin
from .models import PaymeTransaction


@admin.register(PaymeTransaction)
class PaymeTransactionAdmin(admin.ModelAdmin):
    list_display = [
        "id",
        "user",
        "amount_som",
        "get_state_display",
        "payme_transaction_id",
        "created_at",
    ]
    list_filter = ["state", "created_at", "provider"]
    search_fields = ["id", "user__phone", "payme_transaction_id"]
    readonly_fields = [
        "id",
        "payme_transaction_id",
        "created_at",
        "updated_at",
        "create_time",
        "perform_time",
        "cancel_time",
    ]

    fieldsets = (
        ("Transaction Info", {
            "fields": ("id", "user", "provider", "payme_transaction_id")
        }),
        ("Amount", {
            "fields": ("amount_tiyin",)
        }),
        ("State", {
            "fields": ("state",)
        }),
        ("Timestamps", {
            "fields": ("create_time", "perform_time", "cancel_time", "created_at", "updated_at"),
            "classes": ("collapse",)
        }),
        ("Cancellation", {
            "fields": ("reason",),
            "classes": ("collapse",)
        }),
    )

    def amount_som(self, obj):
        return f"{obj.amount_som():.2f} som"

    amount_som.short_description = "Amount (som)"

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
