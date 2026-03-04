from rest_framework import serializers
from .models import Category, Product, ProductImage


class CategorySerializer(serializers.ModelSerializer):
    subcategories = serializers.SerializerMethodField()

    class Meta:
        model = Category
        fields = ['id', 'name', 'slug', 'parent', 'description', 'is_active', 'subcategories']
        read_only_fields = ['id']

    def get_subcategories(self, obj):
        if obj.subcategories.exists():
            return CategorySerializer(obj.subcategories.filter(is_active=True), many=True).data
        return []


class ProductImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductImage
        fields = ['id', 'image', 'is_primary']


class ProductListSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source='category.name', read_only=True)
    vendor_name = serializers.CharField(source='vendor.full_name', read_only=True)
    final_price = serializers.ReadOnlyField()
    average_rating = serializers.ReadOnlyField()
    is_in_stock = serializers.ReadOnlyField()

    class Meta:
        model = Product
        fields = [
            'id', 'name', 'slug', 'category_name', 'vendor_name',
            'price', 'discount_price', 'final_price', 'stock',
            'is_in_stock', 'image', 'is_active', 'is_featured',
            'average_rating', 'created_at'
        ]


class ProductDetailSerializer(serializers.ModelSerializer):
    category = CategorySerializer(read_only=True)
    category_id = serializers.PrimaryKeyRelatedField(
        queryset=Category.objects.filter(is_active=True), source='category', write_only=True
    )
    images = ProductImageSerializer(many=True, read_only=True)
    vendor_name = serializers.CharField(source='vendor.full_name', read_only=True)
    final_price = serializers.ReadOnlyField()
    average_rating = serializers.ReadOnlyField()
    is_in_stock = serializers.ReadOnlyField()

    class Meta:
        model = Product
        fields = [
            'id', 'name', 'slug', 'description', 'category', 'category_id',
            'vendor_name', 'price', 'discount_price', 'final_price',
            'stock', 'is_in_stock', 'image', 'images',
            'is_active', 'is_featured', 'average_rating', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'slug', 'vendor_name', 'created_at', 'updated_at']
