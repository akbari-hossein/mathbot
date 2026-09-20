from django.conf import settings
from django.db import models


class ContractTransaction(models.Model):
    """Every transaction the backend (contract owner) sends to ContestPrize - an audit log of money movements."""

    class Status(models.TextChoices):
        PENDING = 'pending', 'در انتظار تایید'
        SUCCESS = 'success', 'موفق'
        FAILED = 'failed', 'ناموفق'

    tx_hash = models.CharField(max_length=66, unique=True)
    action = models.CharField(max_length=64)  # contract function name, e.g. 'Awardwinners'
    contest_id = models.PositiveBigIntegerField(null=True, blank=True, db_index=True)
    params = models.JSONField(default=dict, blank=True)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.PENDING)
    block_number = models.PositiveBigIntegerField(null=True, blank=True)
    gas_used = models.PositiveBigIntegerField(null=True, blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name='contract_transactions'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.action} #{self.contest_id} {self.status} {self.tx_hash}'
