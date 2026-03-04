from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from .models import Payment
from .serializers import PaymentSerializer, InitiatePaymentSerializer, VerifyPaymentSerializer
from apps.orders.models import Order
from apps.users.permissions import IsAdmin


class InitiatePaymentView(APIView):
    permission_classes = [IsAuthenticated]

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
        payment.save()

        payment.order.status = Order.CONFIRMED
        payment.order.save()

        return Response({'detail': 'Payment verified successfully.', 'order_number': payment.order.order_number})


class PaymentListView(generics.ListAPIView):
    serializer_class = PaymentSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.role == 'admin':
            return Payment.objects.all().select_related('order', 'user')
        return Payment.objects.filter(user=user)


class PaymentDetailView(generics.RetrieveAPIView):
    serializer_class = PaymentSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        if self.request.user.role == 'admin':
            return Payment.objects.all()
        return Payment.objects.filter(user=self.request.user)
