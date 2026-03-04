from rest_framework import serializers
from .models import VendorStore


class VendorStoreSerializer(serializers.ModelSerializer):
    vendor_email = serializers.CharField(source='user.email', read_only=True)
    total_products = serializers.ReadOnlyField()
    total_orders = serializers.ReadOnlyField()

    class Meta:
        model = VendorStore
        fields = [
            'id', 'vendor_email', 'store_name', 'slug', 'description',
            'logo', 'banner', 'phone', 'address', 'status',
            'is_active', 'total_products', 'total_orders', 'created_at'
        ]
        read_only_fields = ['id', 'slug', 'status', 'vendor_email', 'created_at']
