from decimal import Decimal

from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers

from .models import (
    Account,
    AccountBlackList,
    Card,
    CardBlackList,
    Credit,
    Deposit,
    Transaction,
    TransactionInside,
)

User = get_user_model()


class AuthSerializer(serializers.Serializer):
    phone_num = serializers.CharField(max_length=20)


class VerifySerializer(serializers.Serializer):
    phone_num = serializers.CharField(max_length=20)
    otp = serializers.CharField(max_length=6)
    fname = serializers.CharField(max_length=100)
    lname = serializers.CharField(max_length=100)
    passport_id = serializers.CharField(max_length=50)
    username = serializers.CharField(max_length=150)
    password = serializers.CharField(write_only=True)

    def validate_password(self, value):
        validate_password(value)
        return value


class AccountSerializer(serializers.ModelSerializer):
    user = serializers.StringRelatedField(read_only=True)

    class Meta:
        model = Account
        fields = ("id", "user", "fname", "lname", "passport_id", "balance")


class CardSerializer(serializers.ModelSerializer):
    account = AccountSerializer(read_only=True)

    class Meta:
        model = Card
        fields = ("id", "account", "card_id", "balance", "cart_name", "cvv", "created_at", "expair")
        read_only_fields = ("cvv", "created_at", "expair", "balance")

    def validate_card_id(self, value):
        if not value.isdigit() or len(value) != 16:
            raise serializers.ValidationError("card_id must be 16 digits.")
        return value


class CheckExistsSerializer(serializers.Serializer):
    phone_num = serializers.CharField(required=False, max_length=20)
    card_id = serializers.CharField(required=False, max_length=16)


class TransactionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Transaction
        fields = "__all__"
        read_only_fields = ("created_at", "cuur_balance_sender", "cuur_balance_reciver", "status")

    def validate_amount(self, value):
        if value <= Decimal("0"):
            raise serializers.ValidationError("Amount must be positive.")
        return value


class TransactionInsideSerializer(serializers.ModelSerializer):
    class Meta:
        model = TransactionInside
        fields = "__all__"
        read_only_fields = ("created_at", "cuur_balance_sender", "cuur_balance_reciver", "status")

    def validate_amount(self, value):
        if value <= Decimal("0"):
            raise serializers.ValidationError("Amount must be positive.")
        return value


class CreditSerializer(serializers.ModelSerializer):
    card_id = serializers.CharField(write_only=True)

    class Meta:
        model = Credit
        fields = ("id", "card_id", "amount", "created_at", "procent", "status")
        read_only_fields = ("created_at", "status")

    def validate_amount(self, value):
        if value <= Decimal("0"):
            raise serializers.ValidationError("Amount must be positive.")
        return value


class DepositSerializer(serializers.ModelSerializer):
    card_id = serializers.CharField(write_only=True)

    class Meta:
        model = Deposit
        fields = ("id", "card_id", "amount", "created_at", "procent", "status")
        read_only_fields = ("created_at", "status")

    def validate_amount(self, value):
        if value <= Decimal("0"):
            raise serializers.ValidationError("Amount must be positive.")
        return value


class AccountBlackListSerializer(serializers.ModelSerializer):
    class Meta:
        model = AccountBlackList
        fields = "__all__"
        read_only_fields = ("created_at",)


class CardBlackListSerializer(serializers.ModelSerializer):
    class Meta:
        model = CardBlackList
        fields = "__all__"
        read_only_fields = ("created_at",)
