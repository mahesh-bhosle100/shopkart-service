from rest_framework import serializers
from .models import Payment


class PaymentSerializer(serializers.ModelSerializer):
    order_number = serializers.CharField(source='order.order_number', read_only=True)

    class Meta:
        model = Payment
        fields = [
            'id', 'order', 'order_number', 'user', 'amount',
            'payment_method', 'status', 'transaction_id', 'created_at'
        ]
        read_only_fields = ['id', 'user', 'status', 'created_at']


class InitiatePaymentSerializer(serializers.Serializer):
    order_id = serializers.IntegerField()
    payment_method = serializers.ChoiceField(choices=['razorpay', 'stripe', 'cod'])


class VerifyPaymentSerializer(serializers.Serializer):
    payment_id = serializers.IntegerField()
    transaction_id = serializers.CharField()
    gateway_response = serializers.DictField(required=False)
