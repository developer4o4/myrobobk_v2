import secrets
from datetime import timedelta
from django.utils import timezone


def normalize_phone(phone: str) -> str:
    return (phone or "").strip().replace(" ", "")


def generate_6digit_code() -> str:
    return str(secrets.randbelow(900000) + 100000)


def expires_after(minutes: int = 3):
    return timezone.now() + timedelta(minutes=minutes)
