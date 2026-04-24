from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    AddCardView,
    AdminAccountBlackListViewSet,
    AdminAccountViewSet,
    AdminCardBlackListViewSet,
    AdminCardViewSet,
    AdminCreditViewSet,
    AdminDepositViewSet,
    AdminTransactionInsideViewSet,
    AdminTransactionViewSet,
    AccountBlackListView,
    AuthView,
    BlackListCheckView,
    CardBlackListView,
    CheckIfAccountExistsView,
    GetCreditView,
    HistoryView,
    PutDepositView,
    TransactionInsideView,
    TransactionView,
    VerifyView,
)

router = DefaultRouter()
router.register("admin/accounts", AdminAccountViewSet, basename="admin-accounts")
router.register("admin/cards", AdminCardViewSet, basename="admin-cards")
router.register("admin/transactions", AdminTransactionViewSet, basename="admin-transactions")
router.register("admin/inside-transactions", AdminTransactionInsideViewSet, basename="admin-inside-transactions")
router.register("admin/credits", AdminCreditViewSet, basename="admin-credits")
router.register("admin/deposits", AdminDepositViewSet, basename="admin-deposits")
router.register("admin/account-blacklist", AdminAccountBlackListViewSet, basename="admin-account-blacklist")
router.register("admin/card-blacklist", AdminCardBlackListViewSet, basename="admin-card-blacklist")

urlpatterns = [
    path("auth/", AuthView.as_view(), name="auth"),
    path("verify/", VerifyView.as_view(), name="verify"),
    path("add_card/", AddCardView.as_view(), name="add_card"),
    path("check_if_account_exsits/", CheckIfAccountExistsView.as_view(), name="check_if_account_exsits"),
    path("transaction/", TransactionView.as_view(), name="transaction"),
    path("transaction_inside/", TransactionInsideView.as_view(), name="transaction_inside"),
    path("get_creadit/", GetCreditView.as_view(), name="get_creadit"),
    path("put_deposit/", PutDepositView.as_view(), name="put_deposit"),
    path("history/", HistoryView.as_view(), name="history"),
    path("black_list/account/", AccountBlackListView.as_view(), name="black_list_account"),
    path("black_list/card/", CardBlackListView.as_view(), name="black_list_card"),
    path("black_list/check/", BlackListCheckView.as_view(), name="black_list_check"),
    path("", include(router.urls)),
]
