from django.contrib import admin

from .models import ContractTransaction


@admin.register(ContractTransaction)
class ContractTransactionAdmin(admin.ModelAdmin):
    """Read only: the log must match what really happened on chain."""

    list_display = ('created_at', 'action', 'contest_id', 'status', 'tx_hash', 'created_by')
    list_filter = ('status', 'action')
    search_fields = ('tx_hash', 'contest_id')
    readonly_fields = [f.name for f in ContractTransaction._meta.fields]

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
