from django.contrib import admin
from .models import VendorStore


@admin.register(VendorStore)
class VendorStoreAdmin(admin.ModelAdmin):
    list_display = ['store_name', 'user', 'status', 'is_active', 'created_at']
    list_filter = ['status', 'is_active']
    search_fields = ['store_name', 'user__email']
    ordering = ['-created_at']
