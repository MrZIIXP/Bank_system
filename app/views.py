from rest_framework import generics, status, permissions
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from django.db.models import Q, Sum
from rest_framework.filters import OrderingFilter
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework.serializers import ValidationError
from django.utils import timezone

from .models import Account, Card, Transactions, Deposite, Credit
from .serializers import (
    RegisterSerializer, UserProfileSerializer,
    AccountSerializer, CardSerializer, TransactionSerializer, DepositeSerializer,
    CreditSerializer
)


# ============= AUTH VIEWS (не трогать) =============

class RegisterView(generics.CreateAPIView):
    serializer_class = RegisterSerializer
    permission_classes = [permissions.AllowAny]


class LogoutView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        try:
            refresh_token = request.data["refresh"]
            token = RefreshToken(refresh_token)
            token.blacklist()
            return Response(
                {"detail": "Logout successful"},
                status=status.HTTP_205_RESET_CONTENT
            )
        except Exception:
            return Response(
                {"detail": "Invalid token"},
                status=status.HTTP_400_BAD_REQUEST
            )


# ============= PROFILE VIEWS =============

class UserProfileView(generics.RetrieveUpdateAPIView):
    """Просмотр и обновление профиля пользователя"""
    permission_classes = [IsAuthenticated]
    serializer_class = UserProfileSerializer
    
    def get_object(self):
        return Account.objects.get(user=self.request.user)
    
    def retrieve(self, request, *args, **kwargs):
        account = self.get_object()
        serializer = self.get_serializer(account)
        
        return Response({
            'user': {
                'id': request.user.id,
                'username': request.user.username,
                'first_name': request.user.first_name,
                'last_name': request.user.last_name,
                'phone': request.user.phone,
                'email': request.user.email,
            },
            'account': serializer.data
        }, status=status.HTTP_200_OK)
    
    def update(self, request, *args, **kwargs):
        account = self.get_object()
        user = request.user
        
        # Обновляем User
        if 'first_name' in request.data:
            user.first_name = request.data.get('first_name')
        if 'last_name' in request.data:
            user.last_name = request.data.get('last_name')
        if 'phone' in request.data:
            user.phone = request.data.get('phone')
        if 'email' in request.data:
            user.email = request.data.get('email')
        user.save()
        
        # Обновляем Account
        if 'first_name' in request.data:
            account.first_name = request.data.get('first_name')
        if 'last_name' in request.data:
            account.last_name = request.data.get('last_name')
        account.save()
        
        serializer = self.get_serializer(account)
        
        return Response({
            'message': 'Профиль успешно обновлен',
            'user': {
                'id': user.id,
                'username': user.username,
                'first_name': user.first_name,
                'last_name': user.last_name,
                'phone': user.phone,
                'email': user.email,
            },
            'account': serializer.data
        }, status=status.HTTP_200_OK)



class AccountListCreateView(generics.ListCreateAPIView):
    """Список счетов и создание нового счета"""
    serializer_class = AccountSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [OrderingFilter]
    ordering_fields = ['id', 'balance', 'first_name', 'last_name']
    ordering = ['-id']
    
    def get_queryset(self):
        return Account.objects.filter(user=self.request.user)
    
    def perform_create(self, serializer):
        serializer.save(user=self.request.user)
    
    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        return Response({
            'count': queryset.count(),
            'results': serializer.data
        }, status=status.HTTP_200_OK)


class AccountDetailView(generics.RetrieveUpdateDestroyAPIView):
    """Просмотр, обновление и удаление счета"""
    serializer_class = AccountSerializer
    permission_classes = [IsAuthenticated]
    lookup_field = 'id'
    
    def get_queryset(self):
        return Account.objects.filter(user=self.request.user)
    
    def destroy(self, request, *args, **kwargs):
        account = self.get_object()
        
        # Проверка наличия активных карт
        if account.cards.exists():
            return Response({
                'error': 'Невозможно удалить счет с активными картами'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        account.delete()
        return Response({
            'message': 'Счет успешно удален'
        }, status=status.HTTP_204_NO_CONTENT)


class AccountTotalBalanceView(generics.GenericAPIView):
    """Общий баланс всех счетов"""
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        accounts = Account.objects.filter(user=request.user)
        total = accounts.aggregate(total=Sum('balance'))['total'] or 0
        
        return Response({
            'total_balance': total,
            'accounts_count': accounts.count()
        }, status=status.HTTP_200_OK)


class AccountTopUpView(generics.GenericAPIView):
    permission_classes = [IsAuthenticated]
    
    def post(self, request, id):
        try:
            account = Account.objects.get(id=id, user=request.user)
        except Account.DoesNotExist:
            return Response({
                'error': 'Счет не найден'
            }, status=status.HTTP_404_NOT_FOUND)
        
        amount = request.data.get('amount')
        if not amount:
            return Response({
                'error': 'Необходимо указать сумму'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            amount = int(amount)
        except ValueError:
            return Response({
                'error': 'Сумма должна быть числом'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        if amount <= 0:
            return Response({
                'error': 'Сумма должна быть больше 0'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        if amount > 1000000:
            return Response({
                'error': 'Максимальная сумма пополнения 1,000,000 сомов'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        old_balance = account.balance
        account.balance += amount
        account.save()
        
        return Response({
            'message': 'Счет успешно пополнен',
            'account_id': account.id,
            'old_balance': old_balance,
            'new_balance': account.balance,
            'amount': amount
        }, status=status.HTTP_200_OK)



class CardListCreateView(generics.ListCreateAPIView):
    serializer_class = CardSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [OrderingFilter]
    filterset_fields = ['account']
    ordering_fields = ['id', 'balance', 'account']
    ordering = ['-id']
    
    def get_queryset(self):
        return Card.objects.filter(account__user=self.request.user)
    
    def perform_create(self, serializer):
        
        try:
            account = Account.objects.get(user=self.request.user)
        except Account.DoesNotExist:
            from rest_framework.exceptions import ValidationError
            raise ValidationError({'account': 'Счет не найден или вы не владеете им'})
        
        if Card.objects.filter(account=account).count() >= 3:
            from rest_framework.exceptions import ValidationError
            raise ValidationError({'error': 'Нельзя выпустить более 3 карт на один счет'})
        
        serializer.save(account=account)
    
    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        return Response({
            'count': queryset.count(),
            'results': serializer.data
        }, status=status.HTTP_200_OK)


class CardDetailView(generics.RetrieveDestroyAPIView):
    serializer_class = CardSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        return Card.objects.filter(account__user=self.request.user)
    
    def destroy(self, request, *args, **kwargs):
        card = self.get_object()
        if card.deposites.exists():
            return Response({
                'error': 'Невозможно удалить карту с активными депозитами'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        card.delete()
        return Response({
            'message': 'Карта успешно удалена'
        }, status=status.HTTP_204_NO_CONTENT)


class CardBalanceView(generics.GenericAPIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request, card_num):
        try:
            card = Card.objects.get(card_num=card_num, account__user=request.user)
        except Card.DoesNotExist:
            return Response({
                'error': 'Карта не найдена'
            }, status=status.HTTP_404_NOT_FOUND)
        
        return Response({
            'card_num': card.card_num,
            'balance': card.account.balance,
            'account_id': card.account.id,
        }, status=status.HTTP_200_OK)


class CardBlockView(generics.GenericAPIView):
    permission_classes = [IsAuthenticated]
    
    def destroy(self, request, id):
        try:
            card = Card.objects.get(id=id, account__user=request.user)
        except Card.DoesNotExist:
            return Response({
                'error': 'Карта не найдена'
            }, status=status.HTTP_404_NOT_FOUND)
        
        card.delete()
        
        return Response({
            'message': 'Карта успешно заблокирована',
        }, status=status.HTTP_200_OK)



class TransactionListCreateView(generics.ListCreateAPIView):
    serializer_class = TransactionSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [OrderingFilter]
    filterset_fields = ['account_from', 'account_to', 'type']
    ordering_fields = ['created_at', 'amount']
    ordering = ['-created_at']
    
    def get_queryset(self):
        return Transactions.objects.filter(
            Q(account_from__user=self.request.user) |
            Q(account_to__user=self.request.user)
        ).order_by('-created_at')
    
    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        trans_type = request.query_params.get('type')
        if trans_type:
            queryset = queryset.filter(type=trans_type)
        
        account_from = request.query_params.get('account_from')
        if account_from:
            queryset = queryset.filter(account_from_id=account_from)
        
        serializer = self.get_serializer(queryset, many=True)
        return Response({
            'count': queryset.count(),
            'results': serializer.data
        }, status=status.HTTP_200_OK)
    
    def perform_create(self, serializer):
       account = Account.objects.get(user=self.request.user)
       serializer.save(account_from=account)

class TransactionDetailView(generics.RetrieveAPIView):
    serializer_class = TransactionSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        return Transactions.objects.filter(
            Q(account_from__user=self.request.user) |
            Q(account_to__user=self.request.user)
        )
    


class MyTransactionsView(generics.GenericAPIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        account = Account.objects.get(user=request.user)
        
        transactions_from = Transactions.objects.filter(account_from=account)
        transactions_to = Transactions.objects.filter(account_to=account)
        
        all_transactions = (transactions_from | transactions_to).order_by('-created_at')
        
        serializer = TransactionSerializer(all_transactions, many=True)
        return Response({
            'count': all_transactions.count(),
            'results': serializer.data
        }, status=status.HTTP_200_OK)


class TransactionStatisticsView(generics.GenericAPIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        account = Account.objects.get(user=request.user)
        
        transactions_from = Transactions.objects.filter(account_from=account)
        transactions_to = Transactions.objects.filter(account_to=account)
        
        total_income = transactions_to.aggregate(total=Sum('amount'))['total'] or 0
        total_outcome = transactions_from.aggregate(total=Sum('amount'))['total'] or 0
        
        stats = {
            'total_transactions': transactions_from.count() + transactions_to.count(),
            'total_income': total_income,
            'total_outcome': total_outcome,
            'balance': account.balance,
            'by_type': {
                'to_account': transactions_to.filter(type='to_account').count(),
                'to_card': transactions_to.filter(type='to_card').count(),
                'from_card': transactions_from.filter(type='from_card').count(),
                'from_account': transactions_from.filter(type='from_account').count(),
            }
        }
        
        return Response(stats, status=status.HTTP_200_OK)



class DepositListCreateView(generics.ListCreateAPIView):
    serializer_class = DepositeSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [OrderingFilter]
    filterset_fields = ['card']
    ordering_fields = ['created_at', 'amount', 'procent']
    ordering = ['-created_at']
    
    def get_queryset(self):
        return Deposite.objects.filter(card__account__user=self.request.user)
    
    def perform_create(self, serializer):
        card_id = self.request.data.get('card')
        
        try:
            card = Card.objects.get(id=card_id, account__user=self.request.user)
        except Card.DoesNotExist:
            raise ValidationError({'card': 'Карта не найдена или вы не владеете ей'})
        
        serializer.save(card=card)
    
    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        card_id = request.query_params.get('card')
        
        if card_id:
            queryset = queryset.filter(card_id=card_id)
        
        serializer = self.get_serializer(queryset, many=True)
        return Response({
            'count': queryset.count(),
            'results': serializer.data
        }, status=status.HTTP_200_OK)


class DepositDetailView(generics.RetrieveDestroyAPIView):
    serializer_class = DepositeSerializer
    permission_classes = [IsAuthenticated]
    lookup_field = 'id'
    
    def get_queryset(self):
        return Deposite.objects.filter(card__account__user=self.request.user)
    
    def destroy(self, request, *args, **kwargs):
        deposit = self.get_object()
        weeks_passed = (timezone.now() - deposit.created_at).days // 7
        
        total = deposit.amount
        for _ in range(weeks_passed):
            total += total * (deposit.procent / 100)
        deposit.card.balance += int(total)
        deposit.card.save()
        
        deposit.delete()
        return Response({
            'message': f'Депозит закрыт. Получено: {int(total)} сомов',
            'initial_amount': deposit.amount,
            'earned': int(total - deposit.amount),
            'total_received': int(total)
        }, status=status.HTTP_200_OK)


class MyDepositsView(generics.GenericAPIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        account = Account.objects.get(user=request.user)
        deposits = Deposite.objects.filter(card__account=account).order_by('-created_at')
        
        serializer = DepositeSerializer(deposits, many=True)
        return Response({
            'count': deposits.count(),
            'total_in_deposits': sum(d.amount for d in deposits),
            'results': serializer.data
        }, status=status.HTTP_200_OK)


class CreditListCreateView(generics.ListCreateAPIView):
    serializer_class = CreditSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [OrderingFilter]
    filterset_fields = ['card']
    ordering_fields = ['created_at', 'amount', 'procent']
    ordering = ['-created_at']
    
    def get_queryset(self):
        return Credit.objects.filter(card__account__user=self.request.user)
    
    def perform_create(self, serializer):
        card_id = self.request.data.get('card')
        try:
            card = Card.objects.select_for_update().get(id=card_id, account__user=self.request.user)
        except Card.DoesNotExist:
            raise ValidationError({'card': 'Карта не найдена или вы не владеете ей'})
        
        amount = self.request.data.get('amount')
        card.balance += int(amount)
        card.save()
        
        serializer.save(card=card)
    
    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        card_id = request.query_params.get('card')
        
        if card_id:
            queryset = queryset.filter(card_id=card_id)
        
        serializer = self.get_serializer(queryset, many=True)
        return Response({
            'count': queryset.count(),
            'results': serializer.data
        }, status=status.HTTP_200_OK)


class CreditDetailView(generics.RetrieveUpdateAPIView):
    serializer_class = CreditSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        return Credit.objects.filter(card__account__user=self.request.user)
    
    def destroy(self, request, *args, **kwargs):
        credit = self.get_object()
        
        weeks_passed = (timezone.now() - credit.created_at).days // 7
        debt = credit.amount
        for _ in range(weeks_passed):
            debt += debt * (credit.procent / 100)
        debt = int(debt)
        
        card = credit.card
        
        if card.balance < debt:
            return Response({
                'error': f'Недостаточно средств для погашения кредита. Нужно: {debt}, доступно: {card.balance}',
                'debt': debt,
                'balance': card.balance
            }, status=status.HTTP_400_BAD_REQUEST)
        
        card.balance -= debt
        card.save()
        
        credit_amount = credit.amount
        
        credit.delete()
        
        return Response({
            'message': f'Кредит успешно погашен. Сумма: {debt} сомов',
            'initial_amount': credit_amount,
            'paid': debt,
            'overpayment': debt - credit_amount
        }, status=status.HTTP_200_OK)


class MyCreditsView(generics.GenericAPIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        account = Account.objects.get(user=request.user)
        credits = Credit.objects.filter(card__account=account).order_by('-created_at')
        
        total_debt = 0
        results = []
        
        for credit in credits:
            if not credit.is_closed:
                weeks_passed = (timezone.now() - credit.created_at).days // 7
                debt = credit.amount
                for _ in range(weeks_passed):
                    debt += debt * (credit.procent / 100)
                total_debt += int(debt)
            
            results.append({
                'id': credit.id,
                'card_number': f"****-****-****-{str(credit.card.card_num)[-4:]}",
                'initial_amount': credit.amount,
                'procent': credit.procent,
                'created_at': credit.created_at,
                'is_closed': credit.is_closed,
                'current_debt': int(debt) if not credit.is_closed else 0
            })
        
        return Response({
            'count': credits.count(),
            'total_debt': total_debt,
            'results': results
        }, status=status.HTTP_200_OK)


class CardToCardTransferView(generics.GenericAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = TransactionSerializer
    
    def post(self, request):
        from_card_num = request.data.get('from_card_num')
        to_account = request.data.get('to_account')
        amount = request.data.get('amount')
        description = request.data.get('description', '')
        
        try:
            from_card = Card.objects.select_for_update().get(
                card_num=from_card_num, 
                account__user=request.user
            )
            account = Account.objects.get(id=to_account)
        except Account.DoesNotExist:
            return Response({
                'error': 'Аккаунт не найдена'
            }, status=status.HTTP_404_NOT_FOUND)
        
        amount = int(amount)
        
        if from_card.balance < amount:
            return Response({
                'error': 'Недостаточно средств на балансе'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        from_card.balance -= amount
        account.balance += amount
        from_card.save()
        account.save()
        
        transaction = Transactions.objects.create(
            account_from=from_card.account,
            account_to=account,
            amount=amount,
            type='from_card_to_account',
            description=description,
            current_balance_acc_from=from_card.balance,
            current_balance_acc_to=account.balance
        )
        
        return Response({
            'message': 'Перевод успешно выполнен',
            'from_card': from_card.account.first_name,
            'to_card': account.first_name,
            'amount': amount,
            'transaction_id': transaction.id
        }, status=status.HTTP_200_OK)