from decimal import Decimal
import random
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.db.models import Q
from rest_framework import generics, permissions, status, viewsets
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken

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
from .serializers import (
    AccountBlackListSerializer,
    AccountSerializer,
    AuthSerializer,
    CardBlackListSerializer,
    CardSerializer,
    CheckExistsSerializer,
    CreditSerializer,
    DepositSerializer,
    TransactionInsideSerializer,
    TransactionSerializer,
    VerifySerializer,
)

User = get_user_model()

OTP_TTL_SECONDS = 180
EXISTS_TTL_SECONDS = 120
HISTORY_TTL_SECONDS = 180
BLACKLIST_TTL_SECONDS = 300


def history_cache_key(user_id, params):
    version = cache.get(f"history:version:{user_id}", 1)
    card = params.get("card", "")
    income_and_pays = params.get("income_and_pays", "")
    inside = params.get("inside", "")
    time_filter = params.get("time", "")
    return f"history:{user_id}:{version}:{card}:{income_and_pays}:{inside}:{time_filter}"


def invalidate_history_cache(user_id):
    version_key = f"history:version:{user_id}"
    version = cache.get(version_key, 1)
    cache.set(version_key, version + 1, HISTORY_TTL_SECONDS * 10)


def set_blacklist_cache_for_account(account_id, in_blacklist):
    cache.set(f"blacklist:account:{account_id}", in_blacklist, BLACKLIST_TTL_SECONDS)


def set_blacklist_cache_for_card(card_id, in_blacklist):
    cache.set(f"blacklist:card:{card_id}", in_blacklist, BLACKLIST_TTL_SECONDS)


class AuthView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = AuthSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        phone_num = serializer.validated_data["phone_num"]
        otp = f"{random.randint(0, 999999):06d}"
        cache.set(f"otp:{phone_num}", otp, OTP_TTL_SECONDS)
        return Response(
            {"message": "OTP sent.", "phone_num": phone_num, "otp": otp},
            status=status.HTTP_200_OK,
        )


class VerifyView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = VerifySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        phone_num = data["phone_num"]
        cached_otp = cache.get(f"otp:{phone_num}")
        if not cached_otp or cached_otp != data["otp"]:
            return Response({"detail": "OTP invalid or expired."}, status=status.HTTP_400_BAD_REQUEST)

        user, _ = User.objects.get_or_create(
            phone_num=phone_num,
            defaults={"username": data["username"]},
        )
        user.username = data["username"]
        user.set_password(data["password"])
        user.save()

        account, created = Account.objects.get_or_create(
            user=user,
            defaults={
                "fname": data["fname"],
                "lname": data["lname"],
                "passport_id": data["passport_id"],
                "balance": Decimal("0"),
            },
        )
        if not created:
            return Response({"detail": "Account already exists."}, status=status.HTTP_400_BAD_REQUEST)

        cache.delete(f"otp:{phone_num}")
        cache.delete(f"exists:phone:{phone_num}")
        refresh = RefreshToken.for_user(user)
        return Response(
            {
                "account": AccountSerializer(account).data,
                "tokens": {"refresh": str(refresh), "access": str(refresh.access_token)},
            },
            status=status.HTTP_201_CREATED,
        )


class AddCardView(generics.CreateAPIView):
    serializer_class = CardSerializer
    permission_classes = [permissions.IsAuthenticated]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            account = request.user.account
        except Account.DoesNotExist:
            return Response({"detail": "Account not found."}, status=status.HTTP_404_NOT_FOUND)

        card = serializer.save(account=account, balance=Decimal("0"))
        cache.delete(f"exists:card:{card.card_id}")
        return Response(CardSerializer(card).data, status=status.HTTP_201_CREATED)


class CheckIfAccountExistsView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        serializer = CheckExistsSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        phone_num = serializer.validated_data.get("phone_num")
        card_id = serializer.validated_data.get("card_id")
        response = {}

        if phone_num:
            phone_key = f"exists:phone:{phone_num}"
            account_exists = cache.get(phone_key)
            if account_exists is None:
                account_exists = Account.objects.filter(user__phone_num=phone_num).exists()
                cache.set(phone_key, account_exists, EXISTS_TTL_SECONDS)
            response["account_exists"] = account_exists

        if card_id:
            card_key = f"exists:card:{card_id}"
            card_exists = cache.get(card_key)
            if card_exists is None:
                card_exists = Card.objects.filter(card_id=card_id).exists()
                cache.set(card_key, card_exists, EXISTS_TTL_SECONDS)
            response["card_exists"] = card_exists

        return Response(response, status=status.HTTP_200_OK)


class TransactionView(generics.CreateAPIView):
    serializer_class = TransactionSerializer
    permission_classes = [permissions.IsAuthenticated]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        sender = serializer.validated_data["sender"]
        reciver = serializer.validated_data["reciver"]
        amount = serializer.validated_data["amount"]

        if sender.user != request.user:
            return Response({"detail": "Sender must be your account."}, status=status.HTTP_403_FORBIDDEN)
        if sender.balance < amount:
            return Response({"detail": "Insufficient sender balance."}, status=status.HTTP_400_BAD_REQUEST)

        sender.balance -= amount
        reciver.balance += amount
        sender.save(update_fields=["balance"])
        reciver.save(update_fields=["balance"])

        txn = serializer.save(
            cuur_balance_sender=sender.balance,
            cuur_balance_reciver=reciver.balance,
            status="success",
        )
        invalidate_history_cache(sender.user_id)
        if reciver.user_id != sender.user_id:
            invalidate_history_cache(reciver.user_id)
        return Response(TransactionSerializer(txn).data, status=status.HTTP_201_CREATED)


class TransactionInsideView(generics.CreateAPIView):
    serializer_class = TransactionInsideSerializer
    permission_classes = [permissions.IsAuthenticated]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        tx_type = serializer.validated_data["type"]
        sender_ref = serializer.validated_data["sender"]
        reciver_ref = serializer.validated_data["reciver"]
        amount = serializer.validated_data["amount"]

        if tx_type == "phone_num":
            try:
                sender_account = Account.objects.get(user__phone_num=sender_ref)
                reciver_account = Account.objects.get(user__phone_num=reciver_ref)
            except Account.DoesNotExist:
                return Response({"detail": "Sender or receiver phone account not found."}, status=status.HTTP_404_NOT_FOUND)
            if sender_account.user != request.user:
                return Response({"detail": "Sender phone must be yours."}, status=status.HTTP_403_FORBIDDEN)
            sender_balance = sender_account.balance
            reciver_balance = reciver_account.balance
            if sender_balance < amount:
                return Response({"detail": "Insufficient sender balance."}, status=status.HTTP_400_BAD_REQUEST)
            sender_account.balance -= amount
            reciver_account.balance += amount
            sender_account.save(update_fields=["balance"])
            reciver_account.save(update_fields=["balance"])
            sender_balance = sender_account.balance
            reciver_balance = reciver_account.balance
            invalidate_history_cache(sender_account.user_id)
            invalidate_history_cache(reciver_account.user_id)
        else:
            try:
                sender_card = Card.objects.get(card_id=sender_ref)
                reciver_card = Card.objects.get(card_id=reciver_ref)
            except Card.DoesNotExist:
                return Response({"detail": "Sender or receiver card not found."}, status=status.HTTP_404_NOT_FOUND)
            if sender_card.account.user != request.user:
                return Response({"detail": "Sender card must be yours."}, status=status.HTTP_403_FORBIDDEN)
            if sender_card.balance < amount:
                return Response({"detail": "Insufficient sender balance."}, status=status.HTTP_400_BAD_REQUEST)
            sender_card.balance -= amount
            reciver_card.balance += amount
            sender_card.save(update_fields=["balance"])
            reciver_card.save(update_fields=["balance"])
            sender_balance = sender_card.balance
            reciver_balance = reciver_card.balance
            invalidate_history_cache(sender_card.account.user_id)
            invalidate_history_cache(reciver_card.account.user_id)

        inside_tx = serializer.save(
            cuur_balance_sender=sender_balance,
            cuur_balance_reciver=reciver_balance,
            status="success",
        )
        return Response(TransactionInsideSerializer(inside_tx).data, status=status.HTTP_201_CREATED)


class GetCreditView(generics.CreateAPIView):
    serializer_class = CreditSerializer
    permission_classes = [permissions.IsAuthenticated]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            card = Card.objects.get(card_id=serializer.validated_data["card_id"])
        except Card.DoesNotExist:
            return Response({"detail": "Card not found."}, status=status.HTTP_404_NOT_FOUND)
        if card.account.user != request.user:
            return Response({"detail": "Card must be yours."}, status=status.HTTP_403_FORBIDDEN)
        if card.cart_name != "credit":
            return Response({"detail": "Credit can be issued only for credit card type."}, status=status.HTTP_400_BAD_REQUEST)
        card.balance += serializer.validated_data["amount"]
        card.save(update_fields=["balance"])
        credit = Credit.objects.create(
            card=card,
            amount=serializer.validated_data["amount"],
            procent=serializer.validated_data["procent"],
            status="success",
        )
        invalidate_history_cache(request.user.id)
        return Response(CreditSerializer(credit).data, status=status.HTTP_201_CREATED)


class PutDepositView(generics.CreateAPIView):
    serializer_class = DepositSerializer
    permission_classes = [permissions.IsAuthenticated]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            card = Card.objects.get(card_id=serializer.validated_data["card_id"])
        except Card.DoesNotExist:
            return Response({"detail": "Card not found."}, status=status.HTTP_404_NOT_FOUND)
        if card.account.user != request.user:
            return Response({"detail": "Card must be yours."}, status=status.HTTP_403_FORBIDDEN)
        if card.balance < serializer.validated_data["amount"]:
            return Response({"detail": "Insufficient card balance."}, status=status.HTTP_400_BAD_REQUEST)
        card.balance -= serializer.validated_data["amount"]
        card.save(update_fields=["balance"])
        deposit = Deposit.objects.create(
            card=card,
            amount=serializer.validated_data["amount"],
            procent=serializer.validated_data["procent"],
            status="success",
        )
        invalidate_history_cache(request.user.id)
        return Response(DepositSerializer(deposit).data, status=status.HTTP_201_CREATED)


class HistoryView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        key = history_cache_key(request.user.id, request.query_params)
        cached = cache.get(key)
        if cached is not None:
            return Response({"source": "cache", "transaction_history": cached}, status=status.HTTP_200_OK)

        account = request.user.account
        tx_qs = Transaction.objects.filter(Q(sender=account) | Q(reciver=account)).order_by("-created_at")
        inside_qs = TransactionInside.objects.none()

        card_filter = request.query_params.get("card")
        if card_filter:
            own_cards = Card.objects.filter(account=account, card_id=card_filter)
            if own_cards.exists():
                inside_qs = TransactionInside.objects.filter(Q(sender=card_filter) | Q(reciver=card_filter))
            else:
                tx_qs = tx_qs.none()

        direction = request.query_params.get("income_and_pays")
        if direction == "income":
            tx_qs = tx_qs.filter(reciver=account)
        elif direction == "pays":
            tx_qs = tx_qs.filter(sender=account)

        if request.query_params.get("inside") in ("1", "true", "True"):
            if not inside_qs.exists():
                phone = request.user.phone_num
                card_ids = list(Card.objects.filter(account=account).values_list("card_id", flat=True))
                inside_qs = TransactionInside.objects.filter(
                    Q(sender=phone)
                    | Q(reciver=phone)
                    | Q(sender__in=card_ids)
                    | Q(reciver__in=card_ids)
                ).order_by("-created_at")

        date_from = request.query_params.get("time")
        if date_from:
            tx_qs = tx_qs.filter(created_at__date__gte=date_from)
            inside_qs = inside_qs.filter(created_at__date__gte=date_from)

        data = {
            "transactions": TransactionSerializer(tx_qs, many=True).data,
            "inside_transactions": TransactionInsideSerializer(inside_qs, many=True).data,
        }
        cache.set(key, data, HISTORY_TTL_SECONDS)
        return Response({"source": "db", "transaction_history": data}, status=status.HTTP_200_OK)


class AccountBlackListView(generics.CreateAPIView):
    serializer_class = AccountBlackListSerializer
    permission_classes = [permissions.IsAdminUser]

    def perform_create(self, serializer):
        instance = serializer.save()
        set_blacklist_cache_for_account(instance.account_id, True)


class CardBlackListView(generics.CreateAPIView):
    serializer_class = CardBlackListSerializer
    permission_classes = [permissions.IsAdminUser]

    def perform_create(self, serializer):
        instance = serializer.save()
        set_blacklist_cache_for_card(instance.card_id, True)


class BlackListCheckView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        account_id = request.query_params.get("account")
        card_id = request.query_params.get("card")
        payload = {}

        if account_id:
            key = f"blacklist:account:{account_id}"
            is_blacklisted = cache.get(key)
            if is_blacklisted is None:
                is_blacklisted = AccountBlackList.objects.filter(account_id=account_id).exists()
                cache.set(key, is_blacklisted, BLACKLIST_TTL_SECONDS)
            payload["account_blacklisted"] = is_blacklisted

        if card_id:
            key = f"blacklist:card:{card_id}"
            is_blacklisted = cache.get(key)
            if is_blacklisted is None:
                is_blacklisted = CardBlackList.objects.filter(card__card_id=card_id).exists()
                cache.set(key, is_blacklisted, BLACKLIST_TTL_SECONDS)
            payload["card_blacklisted"] = is_blacklisted

        return Response(payload, status=status.HTTP_200_OK)


class AdminAccountViewSet(viewsets.ModelViewSet):
    queryset = Account.objects.all().order_by("-id")
    serializer_class = AccountSerializer
    permission_classes = [permissions.IsAdminUser]


class AdminCardViewSet(viewsets.ModelViewSet):
    queryset = Card.objects.all().order_by("-id")
    serializer_class = CardSerializer
    permission_classes = [permissions.IsAdminUser]


class AdminTransactionViewSet(viewsets.ModelViewSet):
    queryset = Transaction.objects.all().order_by("-created_at")
    serializer_class = TransactionSerializer
    permission_classes = [permissions.IsAdminUser]


class AdminTransactionInsideViewSet(viewsets.ModelViewSet):
    queryset = TransactionInside.objects.all().order_by("-created_at")
    serializer_class = TransactionInsideSerializer
    permission_classes = [permissions.IsAdminUser]


class AdminCreditViewSet(viewsets.ModelViewSet):
    queryset = Credit.objects.all().order_by("-created_at")
    serializer_class = CreditSerializer
    permission_classes = [permissions.IsAdminUser]


class AdminDepositViewSet(viewsets.ModelViewSet):
    queryset = Deposit.objects.all().order_by("-created_at")
    serializer_class = DepositSerializer
    permission_classes = [permissions.IsAdminUser]


class AdminAccountBlackListViewSet(viewsets.ModelViewSet):
    queryset = AccountBlackList.objects.all().order_by("-created_at")
    serializer_class = AccountBlackListSerializer
    permission_classes = [permissions.IsAdminUser]


class AdminCardBlackListViewSet(viewsets.ModelViewSet):
    queryset = CardBlackList.objects.all().order_by("-created_at")
    serializer_class = CardBlackListSerializer
    permission_classes = [permissions.IsAdminUser]
