import hmac
import hashlib
import json

from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from django.conf import settings
from django.db import IntegrityError
from .models import Payment
from .serializers import PaymentSerializer, InitiatePaymentSerializer, VerifyPaymentSerializer
from apps.orders.models import Order
from apps.users.permissions import IsAdmin
from apps.common.email import send_email


class InitiatePaymentView(APIView):
    permission_classes = [IsAuthenticated]
    throttle_scope = 'payments_write'

    def post(self, request):
        serializer = InitiatePaymentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            order = Order.objects.get(id=serializer.validated_data['order_id'], user=request.user)
        except Order.DoesNotExist:
            return Response({'detail': 'Order not found.'}, status=status.HTTP_404_NOT_FOUND)

        if hasattr(order, 'payment') and order.payment.status == Payment.SUCCESS:
            return Response({'detail': 'Payment already done.'}, status=status.HTTP_400_BAD_REQUEST)

        payment, _ = Payment.objects.get_or_create(
            order=order,
            defaults={
                'user': request.user,
                'amount': order.payable_amount,
                'payment_method': serializer.validated_data['payment_method'],
            }
        )

        return Response({
            'payment_id': payment.id,
            'amount': payment.amount,
            'payment_method': payment.payment_method,
            'order_number': order.order_number,
            'status': payment.status,
            'message': 'Integrate with Razorpay/Stripe SDK on frontend to complete payment.'
        }, status=status.HTTP_200_OK)


class VerifyPaymentView(APIView):
    permission_classes = [IsAuthenticated]
    throttle_scope = 'payments_write'

    def post(self, request):
        serializer = VerifyPaymentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            payment = Payment.objects.get(id=serializer.validated_data['payment_id'], user=request.user)
        except Payment.DoesNotExist:
            return Response({'detail': 'Payment not found.'}, status=status.HTTP_404_NOT_FOUND)

        payment.transaction_id = serializer.validated_data['transaction_id']
        payment.gateway_response = serializer.validated_data.get('gateway_response', {})
        payment.status = Payment.SUCCESS
        try:
            payment.save()
        except IntegrityError:
            return Response({'detail': 'Transaction ID already used.'}, status=status.HTTP_400_BAD_REQUEST)

        payment.order.status = Order.CONFIRMED
        payment.order.save()

        send_email(
            subject='Payment confirmed',
            message=f'Your payment for order {payment.order.order_number} is confirmed.',
            recipients=[payment.user.email]
        )

        return Response({'detail': 'Payment verified successfully.', 'order_number': payment.order.order_number})


class PaymentListView(generics.ListAPIView):
    serializer_class = PaymentSerializer
    permission_classes = [IsAuthenticated]
    throttle_scope = 'payments_read'

    def get_queryset(self):
        user = self.request.user
        if user.role == 'admin':
            return Payment.objects.all().select_related('order', 'user')
        return Payment.objects.filter(user=user)


class PaymentDetailView(generics.RetrieveAPIView):
    serializer_class = PaymentSerializer
    permission_classes = [IsAuthenticated]
    throttle_scope = 'payments_read'

    def get_queryset(self):
        if self.request.user.role == 'admin':
            return Payment.objects.all()
        return Payment.objects.filter(user=self.request.user)


class PaymentWebhookView(APIView):
    permission_classes = [AllowAny]
    throttle_scope = 'payments_write'

    def post(self, request):
        if not settings.PAYMENT_WEBHOOK_SECRET:
            if settings.DEBUG:
                return Response({'detail': 'Webhook secret not configured. Skipping signature validation in DEBUG.'}, status=status.HTTP_200_OK)
            return Response({'detail': 'Webhook secret not configured.'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        signature = request.headers.get('X-Signature', '')
        expected = hmac.new(
            settings.PAYMENT_WEBHOOK_SECRET.encode(),
            msg=request.body,
            digestmod=hashlib.sha256
        ).hexdigest()

        if not hmac.compare_digest(signature, expected):
            return Response({'detail': 'Invalid signature.'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            payload = json.loads(request.body.decode('utf-8'))
        except json.JSONDecodeError:
            return Response({'detail': 'Invalid JSON.'}, status=status.HTTP_400_BAD_REQUEST)

        payment_id = payload.get('payment_id')
        status_value = payload.get('status')
        transaction_id = payload.get('transaction_id')

        if payment_id and status_value:
            try:
                payment = Payment.objects.get(id=payment_id)
                payment.status = status_value
                if transaction_id:
                    payment.transaction_id = transaction_id
                payment.gateway_response = payload
                payment.save()
                if status_value == Payment.SUCCESS:
                    payment.order.status = Order.CONFIRMED
                    payment.order.save()
                    send_email(
                        subject='Payment confirmed',
                        message=f'Your payment for order {payment.order.order_number} is confirmed.',
                        recipients=[payment.user.email]
                    )
            except Payment.DoesNotExist:
                return Response({'detail': 'Payment not found.'}, status=status.HTTP_404_NOT_FOUND)

        return Response({'detail': 'Webhook received.'}, status=status.HTTP_200_OK)
