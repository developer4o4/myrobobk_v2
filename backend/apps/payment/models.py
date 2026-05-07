from django.conf import settings
from django.db import models


class PaymeTransaction(models.Model):
    """
    Payme payment transactions
    Status workflow: STATE_PENDING -> STATE_DONE (or STATE_CANCELED)
    """
    PROVIDER_PAYME = "payme"

    PROVIDER_CHOICES = (
        (PROVIDER_PAYME, "Payme"),
    )

    STATE_PENDING = 1      # CreateTransaction - to'lov kutilmoqda
    STATE_DONE = 2         # PerformTransaction - to'lov amalga oshdi
    STATE_CANCELED = -1    # CancelTransaction - to'lov bekor qilindi

    STATE_CHOICES = (
        (STATE_PENDING, "Pending"),
        (STATE_DONE, "Done"),
        (STATE_CANCELED, "Canceled"),
    )

    id = models.CharField(
        primary_key=True,
        max_length=36,
        editable=False,
        unique=True
    )

    provider = models.CharField(
        max_length=20,
        choices=PROVIDER_CHOICES,
        default=PROVIDER_PAYME
    )

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="payme_transactions"
    )

    # Payme tomonidan berilan transaction ID
    payme_transaction_id = models.CharField(
        max_length=64,
        unique=True,
        null=True,
        blank=True,
        db_index=True
    )

    # To'lov miqdori (tiyin da: 1 som = 100 tiyin)
    amount_tiyin = models.PositiveBigIntegerField()

    # Tranzaksiya holati
    state = models.SmallIntegerField(
        choices=STATE_CHOICES,
        default=STATE_PENDING,
        db_index=True
    )

    # Payme'dan kelgan timestamps (millisekundda)
    create_time = models.BigIntegerField(default=0)
    perform_time = models.BigIntegerField(null=True, blank=True)
    cancel_time = models.BigIntegerField(null=True, blank=True)

    # Bekor qilinish sababı
    reason = models.IntegerField(null=True, blank=True)

    # Bizning timestamps
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "payme_transactions"
        ordering = ("-created_at",)
        indexes = [
            models.Index(fields=["user", "-created_at"]),
            models.Index(fields=["payme_transaction_id"]),
            models.Index(fields=["state"]),
        ]

    def __str__(self):
        return f"PaymeTransaction #{self.id} | user={self.user_id} | {self.amount_tiyin/100:.2f} som | {self.get_state_display()}"

    def amount_som(self):
        """Amount in som (not tiyin)"""
        return self.amount_tiyin / 100
