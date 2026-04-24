from datetime import timedelta
import random

from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone


class User(AbstractUser):
    phone_num = models.CharField(max_length=20, unique=True)


class Account(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="account")
    fname = models.CharField(max_length=100)
    lname = models.CharField(max_length=100)
    passport_id = models.CharField(max_length=50, unique=True)
    balance = models.DecimalField(max_digits=14, decimal_places=2, default=0)


class Card(models.Model):
    CARD_TYPES = (
        ("visa", "visa"),
        ("credit", "credit"),
        ("master", "master"),
        ("simple", "simple"),
    )

    account = models.ForeignKey(Account, on_delete=models.CASCADE, related_name="cards")
    card_id = models.CharField(max_length=16, unique=True)
    balance = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    cart_name = models.CharField(max_length=20, choices=CARD_TYPES)
    cvv = models.CharField(max_length=3, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    expair = models.DateField(blank=True, null=True)

    def save(self, *args, **kwargs):
        if not self.cvv:
            self.cvv = f"{random.randint(0, 999):03d}"
        if not self.expair:
            self.expair = (timezone.now() + timedelta(days=5 * 365)).date()
        super().save(*args, **kwargs)


class Transaction(models.Model):
    TYPE_CHOICES = (("phone_num", "phone_num"), ("card", "card"))
    STATUS_CHOICES = (("pending", "pending"), ("success", "success"), ("failed", "failed"))

    type = models.CharField(max_length=20, choices=TYPE_CHOICES)
    sender = models.ForeignKey(Account, on_delete=models.PROTECT, related_name="sent_transactions")
    reciver = models.ForeignKey(Account, on_delete=models.PROTECT, related_name="received_transactions")
    amount = models.DecimalField(max_digits=14, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)
    cuur_balance_sender = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    cuur_balance_reciver = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    description = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="success")


class TransactionInside(models.Model):
    TYPE_CHOICES = (("phone_num", "phone_num"), ("card", "card"))
    STATUS_CHOICES = (("pending", "pending"), ("success", "success"), ("failed", "failed"))

    type = models.CharField(max_length=20, choices=TYPE_CHOICES)
    sender = models.CharField(max_length=32)
    reciver = models.CharField(max_length=32)
    amount = models.DecimalField(max_digits=14, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)
    cuur_balance_sender = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    cuur_balance_reciver = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    description = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="success")


class Credit(models.Model):
    STATUS_CHOICES = (("pending", "pending"), ("success", "success"), ("failed", "failed"))

    card = models.ForeignKey(Card, on_delete=models.CASCADE, related_name="credits")
    amount = models.DecimalField(max_digits=14, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)
    procent = models.DecimalField(max_digits=5, decimal_places=2)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="success")


class Deposit(models.Model):
    STATUS_CHOICES = (("pending", "pending"), ("success", "success"), ("failed", "failed"))

    card = models.ForeignKey(Card, on_delete=models.CASCADE, related_name="deposits")
    amount = models.DecimalField(max_digits=14, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)
    procent = models.DecimalField(max_digits=5, decimal_places=2)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="success")


class AccountBlackList(models.Model):
    account = models.OneToOneField(Account, on_delete=models.CASCADE, related_name="blacklist_entry")
    created_at = models.DateTimeField(auto_now_add=True)
    description = models.TextField()


class CardBlackList(models.Model):
    card = models.OneToOneField(Card, on_delete=models.CASCADE, related_name="blacklist_entry")
    created_at = models.DateTimeField(auto_now_add=True)
    description = models.TextField()
