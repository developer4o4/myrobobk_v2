"""
Payment utilities and helper functions
"""

from decimal import Decimal
from datetime import datetime, timezone
from django.utils import timezone as django_timezone
from .models import PaymeTransaction
from apps.users.models import User


def get_user_balance(user_id: str) -> Decimal:
    """Get user's current balance"""
    try:
        user = User.objects.get(id=user_id)
        return user.balance
    except User.DoesNotExist:
        return Decimal("0")


def add_balance(user_id: str, amount_som: Decimal) -> Decimal:
    """Add balance to user account"""
    try:
        user = User.objects.get(id=user_id)
        user.balance = (user.balance or Decimal("0")) + amount_som
        user.save(update_fields=["balance"])
        return user.balance
    except User.DoesNotExist:
        return Decimal("0")


def deduct_balance(user_id: str, amount_som: Decimal) -> bool:
    """Deduct balance from user account"""
    try:
        user = User.objects.get(id=user_id)
        if (user.balance or Decimal("0")) < amount_som:
            return False
        user.balance -= amount_som
        user.save(update_fields=["balance"])
        return True
    except User.DoesNotExist:
        return False


def get_transaction_status(transaction_id: str) -> dict:
    """Get transaction details"""
    try:
        tx = PaymeTransaction.objects.get(id=transaction_id)
        return {
            "id": tx.id,
            "user_id": tx.user_id,
            "amount_som": tx.amount_som(),
            "state": tx.get_state_display(),
            "created_at": tx.created_at.isoformat(),
            "is_completed": tx.state == PaymeTransaction.STATE_DONE,
            "is_pending": tx.state == PaymeTransaction.STATE_PENDING,
            "is_canceled": tx.state == PaymeTransaction.STATE_CANCELED,
        }
    except PaymeTransaction.DoesNotExist:
        return None


def get_daily_stats(date=None) -> dict:
    """Get payment statistics for a specific date"""
    if date is None:
        date = django_timezone.now().date()

    from django.db.models import Sum, Count

    done_txs = (
        PaymeTransaction.objects
        .filter(created_at__date=date, state=PaymeTransaction.STATE_DONE)
        .aggregate(
            total_amount=Sum("amount_tiyin"),
            count=Count("id")
        )
    )

    pending_txs = (
        PaymeTransaction.objects
        .filter(created_at__date=date, state=PaymeTransaction.STATE_PENDING)
        .aggregate(
            total_amount=Sum("amount_tiyin"),
            count=Count("id")
        )
    )

    canceled_txs = (
        PaymeTransaction.objects
        .filter(created_at__date=date, state=PaymeTransaction.STATE_CANCELED)
        .aggregate(
            total_amount=Sum("amount_tiyin"),
            count=Count("id")
        )
    )

    return {
        "date": str(date),
        "completed": {
            "count": done_txs["count"] or 0,
            "total_som": (done_txs["total_amount"] or 0) / 100,
        },
        "pending": {
            "count": pending_txs["count"] or 0,
            "total_som": (pending_txs["total_amount"] or 0) / 100,
        },
        "canceled": {
            "count": canceled_txs["count"] or 0,
            "total_som": (canceled_txs["total_amount"] or 0) / 100,
        },
    }


def get_user_total_spent(user_id: str) -> Decimal:
    """Get total amount spent by user (completed transactions)"""
    from django.db.models import Sum

    result = (
        PaymeTransaction.objects
        .filter(user_id=user_id, state=PaymeTransaction.STATE_DONE)
        .aggregate(total=Sum("amount_tiyin"))
    )

    total = result["total"] or 0
    return Decimal(total) / Decimal("100")


def get_user_transaction_count(user_id: str, state=None) -> int:
    """Get transaction count for user"""
    qs = PaymeTransaction.objects.filter(user_id=user_id)
    if state is not None:
        qs = qs.filter(state=state)
    return qs.count()


def get_recent_transactions(limit: int = 10) -> list:
    """Get recent transactions"""
    txs = (
        PaymeTransaction.objects
        .select_related("user")
        .order_by("-created_at")[:limit]
    )

    return [
        {
            "id": tx.id,
            "user_phone": tx.user.phone,
            "amount_som": tx.amount_som(),
            "state": tx.get_state_display(),
            "created_at": tx.created_at.isoformat(),
        }
        for tx in txs
    ]


def calculate_total_balance() -> Decimal:
    """Get total balance of all users"""
    from django.db.models import Sum

    total = User.objects.aggregate(total=Sum("balance"))["total"]
    return Decimal(total or 0)


def find_stuck_transactions():
    """Find transactions stuck in PENDING state for more than 24 hours"""
    from datetime import timedelta

    threshold = django_timezone.now() - timedelta(hours=24)

    stuck = PaymeTransaction.objects.filter(
        state=PaymeTransaction.STATE_PENDING,
        created_at__lt=threshold
    )

    return list(stuck.values_list("id", flat=True))


def cleanup_old_transactions(days: int = 90) -> int:
    """Delete old canceled transactions (for cleanup)"""
    from datetime import timedelta

    threshold = django_timezone.now() - timedelta(days=days)

    count, _ = PaymeTransaction.objects.filter(
        state=PaymeTransaction.STATE_CANCELED,
        created_at__lt=threshold
    ).delete()

    return count
