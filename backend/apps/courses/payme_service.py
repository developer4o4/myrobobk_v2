"""
Payme Subscribe API — kartani saqlash va avtomatik yechish.
Docs: https://developer.paycom.uz/ru/subscribe_api
"""
import base64
import logging
import uuid

import requests
from django.conf import settings

logger = logging.getLogger(__name__)

# Production: https://checkout.paycom.uz/api
# Test:       https://checkout.test.paycom.uz/api
PAYME_URL = getattr(settings, "PAYME_URL", "https://checkout.paycom.uz/api")


# ──────────────────────────────────────────────────────────────────────
#  Internal helpers
# ──────────────────────────────────────────────────────────────────────

def _headers() -> dict:
    key = f"{settings.PAYME_MERCHANT_ID}:{settings.PAYME_SECRET_KEY}"
    token = base64.b64encode(key.encode()).decode()
    return {
        "X-Auth": token,
        "Content-Type": "application/json",
    }


def _rpc(method: str, params: dict) -> dict:
    payload = {
        "id": str(uuid.uuid4()),
        "method": method,
        "params": params,
    }
    try:
        r = requests.post(PAYME_URL, json=payload, headers=_headers(), timeout=15)
        r.raise_for_status()
    except requests.RequestException as e:
        logger.error("Payme network error [%s]: %s", method, e)
        raise ValueError("Payme bilan bog'lanishda xatolik yuz berdi")

    data = r.json()
    if "error" in data:
        err = data["error"]
        code = err.get("code", 0)
        msg = err.get("message") or err.get("ru") or "Payme xatosi"
        logger.warning("Payme API error [%s] code=%s msg=%s", method, code, msg)
        raise PaymeError(msg, code=code)

    return data.get("result", {})


# ──────────────────────────────────────────────────────────────────────
#  Custom exception
# ──────────────────────────────────────────────────────────────────────

class PaymeError(Exception):
    def __init__(self, message: str, code: int = 0):
        super().__init__(message)
        self.code = code


# ──────────────────────────────────────────────────────────────────────
#  Cards API
# ──────────────────────────────────────────────────────────────────────

def cards_create(card_number: str, card_expire: str) -> str:
    """
    Birinchi qadam: karta raqami va muddatini yuborish.
    card_expire format: "MMYY"  (masalan "0327")

    Returns:
        token — hali tasdiqlanmagan vaqtinchalik token
    """
    result = _rpc("cards.create", {
        "card": {
            "number": card_number.replace(" ", ""),
            "expire": card_expire.replace("/", ""),
        },
        "save": True,
    })
    return result["card"]["token"]


def cards_get_verify_code(token: str) -> None:
    """
    Ikkinchi qadam: tokenga SMS kod yuborish.
    """
    _rpc("cards.get_verify_code", {"token": token})


def cards_verify(token: str, code: str) -> dict:
    """
    Uchinchi qadam: SMS kodni tasdiqlash.

    Returns: {
        "number": "8600 **** **** 1234",
        "expire": "03/27",
        "token": "<doimiy token>"
    }
    """
    result = _rpc("cards.verify", {"token": token, "code": code})
    return result["card"]


def cards_remove(token: str) -> None:
    """Kartani Payme tizimidan o'chirish."""
    _rpc("cards.remove", {"token": token})


def cards_check(token: str) -> dict:
    """Karta holati va ma'lumotlarini tekshirish."""
    result = _rpc("cards.check", {"token": token})
    return result.get("card", {})


# ──────────────────────────────────────────────────────────────────────
#  Receipts API (to'lov)
# ──────────────────────────────────────────────────────────────────────

def charge_card(
    token: str,
    amount_uzs: int,
    order_id: str,
    description: str,
    ikpu_code: str = None,
    package_code: str = None,
) -> dict:
    """
    Kartadan to'lov yechish (receipts.create + receipts.pay).

    Args:
        token:        Payme karta tokeni
        amount_uzs:   To'lov summasi so'mda (masalan 50_000)
        order_id:     Tizim ichidagi unikal ID (UUID yoki str)
        description:  To'lov izohi
        ikpu_code:    IKPU kodi (Soliq qo'mitasi) — settings dan olish mumkin
        package_code: Qadoq kodi

    Returns:
        Payme receipt dict
    """
    amount_tiyin = amount_uzs * 100
    ikpu = ikpu_code or getattr(settings, "PAYME_IKPU_CODE", "00702001001000001")
    pkg = package_code or getattr(settings, "PAYME_PACKAGE_CODE", "1496156")

    # 1. Receipt yaratish
    receipt_result = _rpc("receipts.create", {
        "amount": amount_tiyin,
        "account": {"order_id": str(order_id)},
        "description": description,
        "detail": {
            "receipt_type": 0,
            "items": [{
                "title": description,
                "price": amount_tiyin,
                "count": 1,
                "code": ikpu,
                "vat_percent": 12,
                "package_code": pkg,
            }],
        },
    })
    receipt_id = receipt_result["receipt"]["_id"]

    # 2. To'lovni amalga oshirish
    pay_result = _rpc("receipts.pay", {
        "id": receipt_id,
        "token": token,
        "payer": {},
    })
    logger.info("Payme charge OK: order_id=%s receipt_id=%s", order_id, receipt_id)
    return pay_result["receipt"]