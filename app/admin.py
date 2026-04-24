from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import (
    Account,
    AccountBlackList,
    Card,
    CardBlackList,
    Credit,
    Deposit,
    Transaction,
    TransactionInside,
    User,
)

admin.site.register(User, UserAdmin)
admin.site.register(Account)
admin.site.register(Card)
admin.site.register(Transaction)
admin.site.register(TransactionInside)
admin.site.register(Credit)
admin.site.register(Deposit)
admin.site.register(AccountBlackList)
admin.site.register(CardBlackList)
