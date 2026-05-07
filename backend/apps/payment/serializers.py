from rest_framework import serializers
from .models import PaymeTransaction


class PaymeTransactionSerializer(serializers.ModelSerializer):
    amount_som = serializers.SerializerMethodField()
    state_display = serializers.CharField(source="get_state_display", read_only=True)

    class Meta:
        model = PaymeTransaction
        fields = [
            "id",
            "user",
            "amount_tiyin",
            "amount_som",
            "state",
            "state_display",
            "payme_transaction_id",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "payme_transaction_id",
            "created_at",
            "updated_at",
        ]

    def get_amount_som(self, obj):
        return obj.amount_som()
