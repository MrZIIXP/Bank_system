from django.db import models
from django.contrib.auth.models import AbstractUser

class User(AbstractUser):
   ROLES = [
		['Manager', 'manager'],
		['User', 'user']
	]
   phone = models.CharField(max_length=13)
   role = models.CharField(default='user')

class Account(models.Model):
   user = models.ForeignKey(User,on_delete=models.CASCADE, related_name='account')
   first_name = models.CharField(max_length=200)
   last_name = models.CharField(max_length=200)
   passport = models.CharField(unique=True)
   balance = models.PositiveIntegerField(default=0)

class Card(models.Model):
   account =  models.ForeignKey(Account, on_delete=models.CASCADE, related_name='cards')
   card_num = models.PositiveIntegerField()
   balance = models.PositiveIntegerField()

class Transactions(models.Model):
   account_from = models.ForeignKey(Account, on_delete=models.CASCADE, related_name='transaction_from')
   account_to = models.ForeignKey(Account, on_delete=models.CASCADE, related_name='transaction_to')
   amount = models.PositiveIntegerField()
   type = models.CharField()
   description = models.TextField()
   current_balance_acc_from = models.PositiveIntegerField()
   current_balance_acc_to	 = models.PositiveIntegerField()
   created_at = models.DateTimeField(auto_now_add=True)

class Deposite(models.Model):
   card = models.ForeignKey(Card, on_delete=models.CASCADE, related_name='deposites')
   amount = models.PositiveIntegerField()
   procent = models.PositiveSmallIntegerField()
   created_at = models.DateTimeField(auto_now_add=True)

class Credit(models.Model):
   card = models.ForeignKey(Card, on_delete=models.CASCADE, related_name='credits')
   amount = models.PositiveIntegerField()
   procent = models.PositiveSmallIntegerField()
   created_at = models.DateTimeField(auto_now_add=True)
