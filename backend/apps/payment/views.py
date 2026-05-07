import base64
import time
from decimal import Decimal

from django.conf import settings
from django.db import transaction as db_tx
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated

from .models import PaymeTransaction
from .services import payme_checkout_link


# ──────────────────────────── PAYME WEBHOOK HELPERS ────────────────────────────

def _payme_result(_id, result: dict):
    """Successful Payme response"""
    return Response({
        "jsonrpc": "2.0",
        "result": result,
        "id": _id
    })


def _payme_error(_id, code: int, ru: str, uz: str):
    """Error Payme response"""
    return Response({
        "jsonrpc": "2.0",
        "error": {
            "code": code,
            "message": {"ru": ru, "uz": uz}
        },
        "id": _id
    })


def _check_basic_auth(request) -> bool:
    """
    Basic Auth tekshirish
    Header: Authorization: Basic <base64(login:password)>
    """
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Basic "):
        return False

    token = auth.split(" ", 1)[1].strip()
    try:
        decoded = base64.b64decode(token).decode()
    except Exception:
        return False

    login, sep, password = decoded.partition(":")
    if not sep:
        return False

    return (
        login == settings.PAYME_LOGIN and
        password == settings.PAYME_SECRET_KEY
    )


# ──────────────────────────── PAYME WEBHOOK VIEW ────────────────────────────

@method_decorator(csrf_exempt, name="dispatch")
class PaymeWebhookAPIView(APIView):
    """
    Payme webhook callback handler
    Payme bu URL'ga POST requests yuboradi:
    - CheckPerformTransaction
    - CreateTransaction
    - PerformTransaction
    - CancelTransaction
    """
    permission_classes = [AllowAny]

    def post(self, request):
        print("🔥 PAYME WEBHOOK HIT")
        print("🔥 PAYME DATA:", request.data)

        # Basic Auth tekshirish
        if not _check_basic_auth(request):
            print("❌ PAYME AUTH FAILED")
            return Response(status=401)

        data = request.data
        _id = data.get("id")
        method = data.get("method")
        params = data.get("params", {}) or {}

        # Method handler tanlash
        if method == "CheckPerformTransaction":
            return self.check_perform(_id, params)
        elif method == "CreateTransaction":
            return self.create_transaction(_id, params)
        elif method == "PerformTransaction":
            return self.perform_transaction(_id, params)
        elif method == "CancelTransaction":
            return self.cancel_transaction(_id, params)

        return _payme_error(_id, -32601, "Method not found", "Method topilmadi")

    def _get_tx(self, params):
        """
        PaymeTransaction topish
        - account.user_id orqali (CheckPerform/Create)
        - payme_transaction_id orqali (Perform/Cancel)
        """
        account = params.get("account") or {}
        account_id = str(account.get("user_id") or "").strip()

        # Account ID bo'yicha qidiramiz (Create va Check uchun)
        if account_id:
            return (
                PaymeTransaction.objects
                .select_related("user")
                .filter(id=account_id)
                .first()
            )

        # Payme transaction ID bo'yicha qidiramiz (Perform va Cancel uchun)
        payme_tx_id = str(params.get("id") or "").strip()
        if payme_tx_id:
            return (
                PaymeTransaction.objects
                .select_related("user")
                .filter(payme_transaction_id=payme_tx_id)
                .order_by("-created_at")
                .first()
            )

        return None

    def check_perform(self, _id, params):
        """
        CheckPerformTransaction - to'lovni amalga oshirish imkoniyatini tekshirish
        """
        tx = self._get_tx(params)
        if not tx:
            return _payme_error(_id, -31050, "Счет не найден.", "Hisob topilmadi")

        # Miqdor tekshirish
        amount = int(params.get("amount") or 0)
        if amount <= 0 or amount != tx.amount_tiyin:
            return _payme_error(_id, -31008, "Неверная сумма.", "Noto'g'ri summa")

        # Allaqachon to'langan bo'lsa
        if tx.state == PaymeTransaction.STATE_DONE:
            return _payme_error(_id, -31008, "Уже оплачено.", "Allaqachon to'langan")

        # Bekor qilingan bo'lsa
        if tx.state == PaymeTransaction.STATE_CANCELED:
            return _payme_error(_id, -31008, "Отменено.", "Bekor qilingan")

        return _payme_result(_id, {"allow": True})

    def create_transaction(self, _id, params):
        """
        CreateTransaction - Payme tomonida transaction yaratildi
        Biz uni database'da pending holatiga o'zgartiramiz
        """
        tx = self._get_tx(params)
        if not tx:
            return _payme_error(_id, -31050, "Счет не найден.", "Hisob topilmadi")

        payme_tx_id = str(params.get("id"))
        amount = int(params.get("amount") or 0)
        create_time = int(params.get("time") or 0)

        # Miqdor tekshirish
        if amount != tx.amount_tiyin:
            return _payme_error(_id, -31008, "Неверная сумма.", "Noto'g'ri summa")

        # Agar boshqa payme_transaction_id bilan bog'langan bo'lsa
        if tx.payme_transaction_id and tx.payme_transaction_id != payme_tx_id:
            return _payme_error(_id, -31003, "Транзакция не найдена.", "Tranzaksiya topilmadi")

        # Idempotent: Agar allaqachon DONE bo'lsa
        if tx.state == PaymeTransaction.STATE_DONE:
            return _payme_result(_id, {
                "create_time": tx.create_time,
                "transaction": str(tx.id),
                "state": tx.state,
            })

        # Transaction'ni PENDING holatiga yangilash
        tx.payme_transaction_id = payme_tx_id
        tx.create_time = create_time
        tx.state = PaymeTransaction.STATE_PENDING
        tx.save(update_fields=["payme_transaction_id", "create_time", "state", "updated_at"])

        return _payme_result(_id, {
            "create_time": tx.create_time,
            "transaction": str(tx.id),
            "state": tx.state,
        })

    def perform_transaction(self, _id, params):
        """
        PerformTransaction - To'lov amalga oshdi, balansni qo'shamiz
        """
        tx = self._get_tx(params)
        if not tx:
            return _payme_error(_id, -31050, "Счет не найден.", "Hisob topilmadi")

        payme_tx_id = str(params.get("id") or "").strip()
        if not payme_tx_id:
            return _payme_error(_id, -32602, "Invalid params", "Noto'g'ri parametr")

        # PerformTransaction'da amount kelmasligi mumkin
        perform_time = int(params.get("time") or 0) or int(time.time() * 1000)

        with db_tx.atomic():
            # Lock ishlatib qo'yamiz (concurrent requests uchun)
            tx = (
                PaymeTransaction.objects
                .select_for_update()
                .select_related("user")
                .get(pk=tx.pk)
            )

            # Payme transaction ID tekshirish
            if tx.payme_transaction_id and tx.payme_transaction_id != payme_tx_id:
                return _payme_error(_id, -31003, "Транзакция не найдена.", "Tranzaksiya topilmadi")

            # Idempotent: Agar allaqachon DONE bo'lsa
            if tx.state == PaymeTransaction.STATE_DONE:
                return _payme_result(_id, {
                    "transaction": str(tx.id),
                    "perform_time": tx.perform_time or perform_time,
                    "state": tx.state,
                })

            # Bekor qilingan bo'lsa
            if tx.state == PaymeTransaction.STATE_CANCELED:
                return _payme_error(_id, -31008, "Отменено.", "Bekor qilingan")

            # ✅ User balansiga pul qo'shamiz
            user = tx.user
            amount_som = Decimal(tx.amount_tiyin) / Decimal("100")
            user.balance = (user.balance or Decimal("0")) + amount_som
            user.save(update_fields=["balance"])

            # Transaction'ni DONE holatiga o'zgartiramiz
            tx.state = PaymeTransaction.STATE_DONE
            tx.perform_time = perform_time
            tx.payme_transaction_id = tx.payme_transaction_id or payme_tx_id
            tx.save(update_fields=["state", "perform_time", "payme_transaction_id", "updated_at"])

        print(f"✅ PAYMENT COMPLETED: User={user.id}, Amount={amount_som} som")

        return _payme_result(_id, {
            "transaction": str(tx.id),
            "perform_time": tx.perform_time,
            "state": tx.state,
        })

    def cancel_transaction(self, _id, params):
        """
        CancelTransaction - To'lov bekor qilindi
        """
        tx = self._get_tx(params)
        if not tx:
            return _payme_error(_id, -31050, "Счет не найден.", "Hisob topilmadi")

        payme_tx_id = str(params.get("id"))
        cancel_time = int(params.get("time") or 0)
        reason = params.get("reason")

        with db_tx.atomic():
            tx = (
                PaymeTransaction.objects
                .select_for_update()
                .get(pk=tx.pk)
            )

            # Payme transaction ID tekshirish
            if tx.payme_transaction_id and tx.payme_transaction_id != payme_tx_id:
                return _payme_error(_id, -31003, "Транзакция не найдена.", "Tranzaksiya topilmadi")

            # Agar allaqachon to'langan bo'lsa, bekor qilib bo'lmaydi
            if tx.state == PaymeTransaction.STATE_DONE:
                return _payme_error(_id, -31007, "Невозможно отменить.", "Bekor qilib bo'lmaydi")

            # CANCELED holatiga o'zgartiramiz
            tx.state = PaymeTransaction.STATE_CANCELED
            tx.cancel_time = cancel_time
            tx.reason = reason
            tx.payme_transaction_id = tx.payme_transaction_id or payme_tx_id
            tx.save(update_fields=["state", "cancel_time", "reason", "payme_transaction_id", "updated_at"])

        print(f"🛑 CANCEL COMPLETED: Transaction={tx.id}, Reason={reason}")

        return _payme_result(_id, {
            "transaction": str(tx.id),
            "cancel_time": tx.cancel_time,
            "state": tx.state,
        })


# ──────────────────────────── CHECKOUT LINK VIEW ────────────────────────────

class PaymeCheckoutLinkAPIView(APIView):
    """
    Foydalanuvchi uchun Payme checkout linkini yaratish
    POST /payment/checkout/
    body: {"amount": 10000}  # som'da
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        print("🔥 Payme uchun checkout link yaratilmoqda...")

        amount_som = int(request.data.get("amount", 0))
        if amount_som <= 0:
            return Response({"detail": "Noto'g'ri summa"}, status=400)

        amount_tiyin = amount_som * 100

        # PaymeTransaction yaratish
        tx = PaymeTransaction.objects.create(
            user=request.user,
            amount_tiyin=amount_tiyin,
            state=PaymeTransaction.STATE_PENDING,
            create_time=0,
        )

        # Checkout link yaratish
        checkout_url = payme_checkout_link(
            order_id=tx.id,
            amount_tiyin=amount_tiyin,
            lang="uz"
        )

        print(f"✅ Link yaratildi: {checkout_url}")

        return Response({
            "order_id": tx.id,
            "payment_url": checkout_url,
            "amount_som": amount_som,
            "status": "pending"
        })


class PaymeTransactionHistoryAPIView(APIView):
    """
    Foydalanuvchining to'lov tarixini ko'rish
    GET /payment/history/
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        transactions = (
            PaymeTransaction.objects
            .filter(user=request.user)
            .values(
                "id",
                "amount_tiyin",
                "state",
                "created_at",
                "payme_transaction_id"
            )
            .order_by("-created_at")
        )

        # amount_tiyin'ni som'ga aylantirish
        data = [
            {
                **tx,
                "amount_som": tx["amount_tiyin"] / 100,
                "state_display": dict(PaymeTransaction.STATE_CHOICES).get(tx["state"], "Unknown")
            }
            for tx in transactions
        ]

        return Response({"transactions": data})
