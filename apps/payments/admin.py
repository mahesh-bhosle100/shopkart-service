from django.contrib import admin
from .models import Payment


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ['order', 'user', 'amount', 'payment_method', 'status', 'created_at']
    list_filter = ['status', 'payment_method']
    search_fields = ['order__order_number', 'user__email', 'transaction_id']
    ordering = ['-created_at']
    readonly_fields = ['created_at', 'updated_at']
