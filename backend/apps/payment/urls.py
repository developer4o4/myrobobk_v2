from django.urls import path

from .views import (
    PaymeWebhookAPIView,
    PaymeCheckoutLinkAPIView,
    PaymeTransactionHistoryAPIView,
)

app_name = "payment"

urlpatterns = [
    # Payme webhook (Payme tomonidan callback)
    path("payme/webhook/", PaymeWebhookAPIView.as_view(), name="payme_webhook"),

    # Checkout link yaratish
    path("checkout/", PaymeCheckoutLinkAPIView.as_view(), name="checkout"),

    # To'lov tarixi
    path("history/", PaymeTransactionHistoryAPIView.as_view(), name="history"),
]
