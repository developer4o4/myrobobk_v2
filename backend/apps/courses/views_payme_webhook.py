"""
apps/courses/views_payme_webhook.py
====================================
Payme Merchant API webhook handler.
Payme Cabinet → Settings → Endpoint URL:
    https://api.myrobo.uz/payments/payme/webhook/
"""
import base64
import hashlib
import json
import logging

from django.conf import settings
from django.http import JsonResponse
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator

logger = logging.getLogger(__name__)


def _check_auth(request) -> bool:
    """Basic Auth tekshiruvi: Payme SECRET_KEY bilan yuboradi."""
    auth_header = request.META.get("HTTP_AUTHORIZATION", "")
    if not auth_header.startswith("Basic "):
        return False
    try:
        decoded = base64.b64decode(auth_header[6:]).decode("utf-8")
        # Format: "Paycom:<SECRET_KEY>"
        _, secret = decoded.split(":", 1)
        return secret == settings.PAYME_SECRET_KEY
    except Exception:
        return False


@method_decorator(csrf_exempt, name="dispatch")
class PaymeWebhookView(View):
    """
    Payme dan kelgan barcha so'rovlarni qabul qiladi.
    Hozirgi loyiha uchun asosan CheckPerformTransaction va
    PerformTransaction metodlari kerak.
    """

    def post(self, request):
        if not _check_auth(request):
            return self._error(-32504, "Insufficient privilege", id=None)

        try:
            body = json.loads(request.body)
        except json.JSONDecodeError:
            return self._error(-32700, "Parse error", id=None)

        method = body.get("method")
        params = body.get("params", {})
        req_id = body.get("id")

        logger.info("Payme webhook: method=%s params=%s", method, params)

        handlers = {
            "CheckPerformTransaction": self.check_perform_transaction,
            "CreateTransaction":       self.create_transaction,
            "PerformTransaction":      self.perform_transaction,
            "CancelTransaction":       self.cancel_transaction,
            "CheckTransaction":        self.check_transaction,
            "GetStatement":            self.get_statement,
        }

        handler = handlers.get(method)
        if not handler:
            return self._error(-32601, "Method not found", id=req_id)

        return handler(params, req_id)

    # ── CheckPerformTransaction ────────────────────────────────────────
    def check_perform_transaction(self, params, req_id):
        """To'lov mumkinmi? order_id tekshiriladi."""
        from apps.courses.models import Course, CourseSubscription

        account = params.get("account", {})
        order_id = account.get("order_id")
        amount = params.get("amount", 0)  # tiyin

        # Bu webhook asosan Merchant API uchun.
        # Subscribe API da bu chaqirilmaydi.
        # Oddiy tasdiqlash: kurs mavjud va aktiv
        try:
            # order_id = "course:<course_id>:<user_id>" formatida bo'lishi mumkin
            # Sizning formatga moslang
            course_id = order_id  # yoki parse qiling
            course = Course.objects.get(id=course_id, is_active=True)
        except Exception:
            return self._error(
                -31050, "Order not found", id=req_id,
                field="order_id"
            )

        if int(course.price) * 100 != amount:
            return self._error(
                -31001, "Wrong amount", id=req_id,
                field="amount"
            )

        return JsonResponse({"id": req_id, "result": {"allow": True}})

    # ── CreateTransaction ──────────────────────────────────────────────
    def create_transaction(self, params, req_id):
        return JsonResponse({"id": req_id, "result": {
            "create_time": self._ms_now(),
            "transaction": params.get("id"),
            "state": 1,
        }})

    # ── PerformTransaction ─────────────────────────────────────────────
    def perform_transaction(self, params, req_id):
        return JsonResponse({"id": req_id, "result": {
            "transaction": params.get("id"),
            "perform_time": self._ms_now(),
            "state": 2,
        }})

    # ── CancelTransaction ──────────────────────────────────────────────
    def cancel_transaction(self, params, req_id):
        return JsonResponse({"id": req_id, "result": {
            "transaction": params.get("id"),
            "cancel_time": self._ms_now(),
            "state": -1,
        }})

    # ── CheckTransaction ───────────────────────────────────────────────
    def check_transaction(self, params, req_id):
        return JsonResponse({"id": req_id, "result": {
            "create_time": self._ms_now(),
            "perform_time": 0,
            "cancel_time": 0,
            "transaction": params.get("id"),
            "state": 1,
            "reason": None,
        }})

    # ── GetStatement ───────────────────────────────────────────────────
    def get_statement(self, params, req_id):
        return JsonResponse({"id": req_id, "result": {"transactions": []}})

    # ── Helpers ────────────────────────────────────────────────────────
    @staticmethod
    def _ms_now() -> int:
        import time
        return int(time.time() * 1000)

    @staticmethod
    def _error(code: int, message: str, id, field: str = None) -> JsonResponse:
        err = {"code": code, "message": {"ru": message, "uz": message, "en": message}}
        if field:
            err["data"] = field
        return JsonResponse({"id": id, "error": err})