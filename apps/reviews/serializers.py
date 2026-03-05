from rest_framework import serializers
from .models import Review, ReviewReport


class ReviewSerializer(serializers.ModelSerializer):
    user_name = serializers.CharField(source='user.full_name', read_only=True)
    product_name = serializers.CharField(source='product.name', read_only=True)

    class Meta:
        model = Review
        fields = [
            'id', 'user', 'user_name', 'product', 'product_name',
            'rating', 'title', 'comment', 'vendor_reply',
            'vendor_replied_at', 'vendor_replied_by',
            'is_verified_purchase', 'is_active', 'created_at'
        ]
        read_only_fields = [
            'id', 'user', 'is_verified_purchase', 'created_at',
            'vendor_reply', 'vendor_replied_at', 'vendor_replied_by'
        ]

    def validate(self, attrs):
        request = self.context['request']
        product = attrs.get('product')
        if Review.objects.filter(user=request.user, product=product).exists():
            raise serializers.ValidationError('You have already reviewed this product.')
        return attrs


class ReviewReportSerializer(serializers.ModelSerializer):
    class Meta:
        model = ReviewReport
        fields = [
            'id', 'review', 'reporter', 'reason', 'details',
            'status', 'resolved_by', 'resolved_at', 'created_at'
        ]
        read_only_fields = ['id', 'reporter', 'status', 'resolved_by', 'resolved_at', 'created_at']

    def validate(self, attrs):
        request = self.context['request']
        review = attrs.get('review')
        if review and ReviewReport.objects.filter(review=review, reporter=request.user).exists():
            raise serializers.ValidationError('You have already reported this review.')
        return attrs
