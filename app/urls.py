from django.urls import path
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView
)
from .views import (
   RegisterView,
   LogoutView,
   UserProfileView,
   AccountListCreateView,
   AccountDetailView,
   AccountTotalBalanceView,
   AccountTopUpView,
   CardListCreateView,
   CardDetailView,
   CardBalanceView,
   CardBlockView,
   TransactionListCreateView,
   TransactionDetailView,
   MyTransactionsView,
   TransactionStatisticsView,
   DepositListCreateView,
   DepositDetailView,
   MyDepositsView,
	CreditDetailView,
   CreditListCreateView,
   MyCreditsView,
   CardToCardTransferView
)

urlpatterns = [
    path('auth/register/', RegisterView.as_view(), name='register'),
    path('auth/login/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('auth/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('auth/logout/', LogoutView.as_view(), name='logout'),
    path('profile/', UserProfileView.as_view(), name='profile'),
    
    path('accounts/', AccountListCreateView.as_view(), name='account-list'),
    path('accounts/<int:id>/', AccountDetailView.as_view(), name='account-detail'),
    path('accounts/total-balance/', AccountTotalBalanceView.as_view(), name='total-balance'),
    path('accounts/<int:id>/topup/', AccountTopUpView.as_view(), name='account-topup'),
    
    path('cards/', CardListCreateView.as_view(), name='card-list'),
    path('cards/<int:id>/', CardDetailView.as_view(), name='card-detail'),
    path('cards/balance/<str:card_num>/', CardBalanceView.as_view(), name='card-balance'),
    path('cards/<int:id>/block/', CardBlockView.as_view(), name='card-block'),
    
    path('transactions/', TransactionListCreateView.as_view(), name='transaction-list'),
    path('transactions/<int:id>/', TransactionDetailView.as_view(), name='transaction-detail'),
    path('transactions/card-to-card/', CardToCardTransferView.as_view(), name='card-to-card'),
    path('transactions/my/', MyTransactionsView.as_view(), name='my-transactions'),
    path('transactions/statistics/', TransactionStatisticsView.as_view(), name='transaction-stats'),
    
    path('deposits/', DepositListCreateView.as_view(), name='deposit-list'),
    path('deposits/<int:id>/', DepositDetailView.as_view(), name='deposit-detail'),
    path('deposits/my/', MyDepositsView.as_view(), name='my-deposits'),

    path('credits/', CreditListCreateView.as_view(), name='credit-list'),
    path('credits/<int:id>/', CreditDetailView.as_view(), name='credit-detail'),
    path('credits/my/', MyCreditsView.as_view(), name='my-credits'),
    
]
