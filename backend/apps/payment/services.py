import base64
from django.conf import settings


def payme_checkout_link(order_id, amount_tiyin: int, lang: str = "uz", callback_url: str = None) -> str:
    """
    Paycom/Payme checkout link yaratish (base64 encoded)
    
    Args:
        order_id: Transaction ID (PaymeTransaction.id)
        amount_tiyin: Amount in tiyin (100 tiyin = 1 som)
        lang: Language code (uz, ru, en)
        callback_url: Optional callback URL after payment
    
    Returns:
        Paycom checkout URL (base64 encoded)
    
    Example:
        https://checkout.paycom.uz/bT02NDNlNGFkMDQ3NzE1YjU5NGM1MWM1N2Y7YWMudXNlcl9pZD0zNDY7YT0xMDAwMDA7bD11ejtjPWh0dHBzOi8vYXBpLmVkdW1hcmsudXo=
    """
    merchant_id = settings.PAYME_MERCHANT_ID
    
    # Build parameters string
    params = f"m={merchant_id};ac.user_id={order_id};a={amount_tiyin};l={lang}"
    
    # Add callback URL if provided
    if callback_url:
        params += f";c={callback_url}"
    
    # Encode to base64
    encoded = base64.b64encode(params.encode()).decode()
    
    return f"https://checkout.paycom.uz/{encoded}"


def payme_checkout_link_simple(order_id, amount_tiyin: int, lang: str = "uz") -> str:
    """
    Payme checkout link (without base64 encoding) - if needed
    """
    merchant_id = settings.PAYME_MERCHANT_ID
    params = f"m={merchant_id};a={amount_tiyin};ac.user_id={order_id};l={lang}"
    return f"https://checkout.payme.uz/{params}"
