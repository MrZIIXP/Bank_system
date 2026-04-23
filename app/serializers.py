from rest_framework import serializers
import re, secrets
from django.utils import timezone
from .models import User, Account, Card, Transactions, Deposite, Credit


class RegisterSerializer(serializers.ModelSerializer):
    passport_number = serializers.CharField(write_only=True)
    
    class Meta:
        model = User
        fields = ('username', 'password', 'phone', 'first_name', 'last_name', 'passport_number',)

    def validate_phone(self, value):
        if value and not re.match(r'^\+?[0-9\-()]+$', value):
            raise serializers.ValidationError("Некорректный формат телефона")
        return value

    def create(self, validated_data):
        passport_number = validated_data.pop('passport_number')
        
        user = User.objects.create_user(
            username=validated_data['username'],
            password=validated_data['password'],
            first_name=validated_data['first_name'],
            last_name=validated_data['last_name']
        )
        
        Account.objects.create(
            user=user,
            passport=passport_number,
            first_name=validated_data['first_name'],
            last_name=validated_data['last_name']
        )
        return user


class UserProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = Account
        fields = ['id', 'first_name', 'last_name', 'balance']


class CardSerializer(serializers.ModelSerializer):
    class Meta:
        model = Card
        fields = ['id', 'account', 'card_num', 'balance']
        read_only_fields = ['id', 'balance', 'card_num']
    
    def validate_account(self, value):
        try:
            account = Account.objects.get(id=value)
        except Account.DoesNotExist:
            raise serializers.ValidationError('Счет не существует')
        return value
    
    def create(self, validated_data):
        account = validated_data.get('account')
        card = Card.objects.create(
            account=account, 
            card_num=secrets.token_urlsafe(16),
            balance=account.balance
        )
        return card


class AccountSerializer(serializers.ModelSerializer):
    cards = CardSerializer(many=True, read_only=True)
    cards_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Account
        fields = ['id', 'first_name', 'last_name', 'passport', 'balance', 'cards', 'cards_count']
        read_only_fields = ['id', 'balance']

    def get_cards_count(self, obj):
        return obj.cards.count()


class TransactionSerializer(serializers.ModelSerializer):
    account_from_name = serializers.SerializerMethodField()
    account_to_name = serializers.SerializerMethodField()
    
    class Meta:
        model = Transactions
        fields = [
            'id', 'account_from', 'account_from_name', 'account_to', 'account_to_name',
            'amount', 'type', 'description', 'current_balance_acc_from',
            'current_balance_acc_to', 'created_at'
        ]
        read_only_fields = ['current_balance_acc_from', 'current_balance_acc_to', 'created_at', 'account_from']
    
    def validate_amount(self, value):
        if value <= 0:
            raise serializers.ValidationError("Сумма должна быть больше 0")
        if value > 1000000:
            raise serializers.ValidationError("Максимальная сумма перевода 1,000,000 сомов")
        return value
    
    def validate(self, data):
        account_from = data.get('account_from')
        account_to = data.get('account_to')
        amount = data.get('amount')
        
        if account_from.id == account_to.id:
            raise serializers.ValidationError(
                "Счет отправителя и получателя должны быть разными"
            )
        
        if account_from.balance < amount:
            raise serializers.ValidationError(
                f"Недостаточно средств. Баланс: {account_from.balance}, запрос: {amount}"
            )
        
        return data
    
    def create(self, validated_data):
        account_from = validated_data['account_from']
        account_to = validated_data['account_to']
        amount = validated_data['amount']
        
        validated_data['current_balance_acc_from'] = account_from.balance
        validated_data['current_balance_acc_to'] = account_to.balance
        
        account_from.balance -= amount
        account_to.balance += amount
        account_from.save()
        account_to.save()
        
        return super().create(validated_data)
    
    def get_account_from_name(self, obj):
        return f"{obj.account_from.first_name} {obj.account_from.last_name}"
    
    def get_account_to_name(self, obj):
        return f"{obj.account_to.first_name} {obj.account_to.last_name}"


class DepositeSerializer(serializers.ModelSerializer):
    card_number = serializers.SerializerMethodField()
    current_total = serializers.SerializerMethodField()
    weeks_passed = serializers.SerializerMethodField()
    
    class Meta:
        model = Deposite
        fields = ['id', 'card','card_number', 'amount', 'procent', 'created_at', 'weeks_passed', 'current_total']
        read_only_fields = ['id', 'created_at']
    
    def validate_amount(self, value):
        if value < 1000:
            raise serializers.ValidationError("Минимальная сумма депозита: 1000")
        if value > 10000000:
            raise serializers.ValidationError("Максимальная сумма депозита: 10,000")
        return value
    
    def validate_procent(self, value):
        if not (1 <= value <= 50):
            raise serializers.ValidationError("Процент должен быть от 1 до 50")
        return value
    
    def validate(self, data):
        card = data.get('card')
        amount = data.get('amount')
        
        if card.balance < amount:
            raise serializers.ValidationError(
                f"Недостаточно средств на карте. Баланс: {card.balance}, требуется: {amount}"
            )
        
        request = self.context.get('request')
        if request and card.account.user != request.user:
            raise serializers.ValidationError("Вы можете создавать депозиты только для своих карт")
        
        return data
    
    def create(self, validated_data):
        card = validated_data['card']
        amount = validated_data['amount']
        card.balance -= amount
        card.save()
        
        return super().create(validated_data)
    
    def get_card_number(self, obj):
        card_num = str(obj.card.card_num)
        return f"****-****-****-{card_num[-4:]}"
    
    def get_weeks_passed(self, obj):
        delta = timezone.now() - obj.created_at
        return delta.days // 7
    
    def get_current_total(self, obj):
        weeks = self.get_weeks_passed(obj)
        total = obj.amount
        for _ in range(weeks):
            total += total * (obj.procent / 100)
        return int(total)


class CreditSerializer(serializers.ModelSerializer):
    card_number = serializers.SerializerMethodField()
    weeks_passed = serializers.SerializerMethodField()
    current_debt = serializers.SerializerMethodField()
    total_to_pay = serializers.SerializerMethodField()
    
    class Meta:
        model = Credit
        fields = ['id', 'card','card_number', 'amount', 'procent', 'created_at', 'weeks_passed', 'current_debt', 'total_to_pay']
        read_only_fields = ['id', 'created_at']
    
    def validate_amount(self, value):
        if value < 5000:
            raise serializers.ValidationError("Минимальная сумма кредита: 5000")
        if value > 500000:
            raise serializers.ValidationError("Максимальная сумма кредита: 500,000")
        return value
    
    def validate_procent(self, value):
        if not (5 <= value <= 50):
            raise serializers.ValidationError("Процент должен быть от 5 до 50")
        return value
    
    def validate(self, data):
        card = data.get('card')
        if Credit.objects.filter(card=card).exists():
            raise serializers.ValidationError("У вас уже есть активный непогашенный кредит")
        
        request = self.context.get('request')
        if request and card.account.user != request.user:
            raise serializers.ValidationError("Вы можете брать кредиты только для своих карт")
        
        return data
    
    def get_card_number(self, obj):
        card_num = str(obj.card.card_num)
        return f"****-****-****-{card_num[-4:]}"
    
    def get_weeks_passed(self, obj):
        delta = timezone.now() - obj.created_at
        return delta.days // 7
    
    def get_current_debt(self, obj):
        weeks = self.get_weeks_passed(obj)
        debt = obj.amount
        
        for _ in range(weeks):
            debt += debt * (obj.procent / 100)
        
        return int(debt)
    
    def get_total_to_pay(self, obj):
        return self.get_current_debt(obj)