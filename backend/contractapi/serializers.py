from decimal import Decimal

from rest_framework import serializers
from web3 import Web3

from .models import ContractTransaction
from . import services


class EthAddressField(serializers.CharField):
    """Accepts any valid 0x address and returns it checksummed."""

    def to_internal_value(self, data):
        value = super().to_internal_value(data).strip()
        if not Web3.is_address(value):
            raise serializers.ValidationError('آدرس کیف پول نامعتبر است.')
        return Web3.to_checksum_address(value)


def eth_amount_field(**kwargs):
    """Amount in ETH as a string or number, e.g. "0.05" (max 18 decimals)."""
    return serializers.DecimalField(max_digits=60, decimal_places=18, min_value=Decimal(0), **kwargs)


class CreateContestSerializer(serializers.Serializer):
    contest_id = serializers.IntegerField(min_value=0, help_text='همان id مسابقه در دیتابیس جنگو')
    price_eth = eth_amount_field(help_text='هزینه ثبت نام به اتر، 0 = مسابقه رایگان')
    signup_deadline = serializers.DateTimeField(help_text='پایان مهلت ثبت نام (معمولا start_time مسابقه)')
    budget_eth = eth_amount_field(required=False, default=Decimal(0), help_text='بودجه جایزه اولیه از کیف پول سرور')


class DeadlineSerializer(serializers.Serializer):
    signup_deadline = serializers.DateTimeField()


class BudgetSerializer(serializers.Serializer):
    amount_eth = eth_amount_field()

    def validate_amount_eth(self, value):
        if value <= 0:
            raise serializers.ValidationError('مبلغ باید بیشتر از صفر باشد.')
        return value


class RefundSerializer(serializers.Serializer):
    wallets = serializers.ListField(child=EthAddressField(), min_length=1, max_length=200)


class Top3Serializer(serializers.Serializer):
    first = EthAddressField()
    second = EthAddressField()
    third = EthAddressField()

    def validate(self, attrs):
        if len({attrs['first'], attrs['second'], attrs['third']}) != 3:
            raise serializers.ValidationError('یک آدرس نمی‌تواند چند رتبه را بگیرد.')
        return attrs


class PercentageAwardSerializer(Top3Serializer):
    percents = serializers.ListField(
        child=serializers.IntegerField(min_value=0, max_value=100), min_length=3, max_length=3
    )

    def validate_percents(self, value):
        if sum(value) > 100:
            raise serializers.ValidationError('مجموع درصدها نباید بیشتر از ۱۰۰ باشد.')
        return value


class FixedAwardSerializer(Top3Serializer):
    amounts_eth = serializers.ListField(child=eth_amount_field(), min_length=3, max_length=3)


class DuelAwardSerializer(serializers.Serializer):
    winner = EthAddressField()


class CustomAwardSerializer(serializers.Serializer):
    winners = serializers.ListField(child=EthAddressField(), min_length=1, max_length=100)
    amounts_eth = serializers.ListField(child=eth_amount_field(), min_length=1, max_length=100)

    def validate(self, attrs):
        if len(attrs['winners']) != len(attrs['amounts_eth']):
            raise serializers.ValidationError('تعداد برندگان و جوایز برابر نیست.')
        return attrs


class WithdrawSerializer(serializers.Serializer):
    to = EthAddressField(help_text='کیف پولی که سهم سایت به آن واریز می‌شود')


class ContractTransactionSerializer(serializers.ModelSerializer):
    explorer_url = serializers.SerializerMethodField()
    created_by = serializers.CharField(source='created_by.username', default=None, read_only=True)

    class Meta:
        model = ContractTransaction
        fields = [
            'tx_hash', 'action', 'contest_id', 'params', 'status', 'block_number', 'gas_used',
            'created_by', 'created_at', 'updated_at', 'explorer_url',
        ]

    def get_explorer_url(self, obj):
        return services.explorer_tx_url(obj.tx_hash)
