from rest_framework import serializers
from .models import Review


class ReviewSerializer(serializers.ModelSerializer):
    user_name = serializers.CharField(source='user.full_name', read_only=True)
    product_name = serializers.CharField(source='product.name', read_only=True)

    class Meta:
        model = Review
        fields = [
            'id', 'user', 'user_name', 'product', 'product_name',
            'rating', 'title', 'comment', 'is_verified_purchase',
            'is_active', 'created_at'
        ]
        read_only_fields = ['id', 'user', 'is_verified_purchase', 'created_at']

    def validate(self, attrs):
        request = self.context['request']
        product = attrs.get('product')
        if Review.objects.filter(user=request.user, product=product).exists():
            raise serializers.ValidationError('You have already reviewed this product.')
        return attrs
