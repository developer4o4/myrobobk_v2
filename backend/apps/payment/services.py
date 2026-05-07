import uuid
from django.conf import settings
from django.urls import reverse


def payme_checkout_link(order_id: str, amount_tiyin: int, lang: str = "uz") -> str:
    """
    Payme checkout link yaratish
    
    Args:
        order_id: Transaction ID (PaymeTransaction.id)
        amount_tiyin: Amount in tiyin (100 tiyin = 1 som)
        lang: Language code (uz, ru, en)
    
    Returns:
        Payme checkout URL
    """
    merchant_id = settings.PAYME_MERCHANT_ID
    account = {"user_id": str(order_id)}
    
    # Rasmiy Payme checkout URL
    checkout_url = f"https://checkout.payme.uz"
    
    params = f"m={merchant_id};a={amount_tiyin};ac.user_id={order_id};l={lang}"
    
    return f"{checkout_url}/{params}"


def generate_transaction_id() -> str:
    """UUID-based transaction ID"""
    return str(uuid.uuid4()).replace("-", "")[:24]
