import uuid
from rest_framework import viewsets, generics, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.db import transaction
from .models import Cart, CartItem, Order, OrderItem, OrderStatusHistory
from .serializers import (
    CartSerializer, CartItemSerializer, OrderSerializer, PlaceOrderSerializer
)
from apps.users.models import Address
from apps.users.permissions import IsAdmin, IsVendorOrAdmin


def generate_order_number():
    return f'ORD-{uuid.uuid4().hex[:10].upper()}'


class CartView(generics.RetrieveAPIView):
    serializer_class = CartSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        cart, _ = Cart.objects.get_or_create(user=self.request.user)
        return cart


class CartItemViewSet(viewsets.ModelViewSet):
    serializer_class = CartItemSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        cart, _ = Cart.objects.get_or_create(user=self.request.user)
        return CartItem.objects.filter(cart=cart)

    def perform_create(self, serializer):
        cart, _ = Cart.objects.get_or_create(user=self.request.user)
        product = serializer.validated_data['product']
        existing = CartItem.objects.filter(cart=cart, product=product).first()
        if existing:
            existing.quantity += serializer.validated_data.get('quantity', 1)
            existing.save()
        else:
            serializer.save(cart=cart)

    @action(detail=False, methods=['delete'])
    def clear(self, request):
        cart, _ = Cart.objects.get_or_create(user=request.user)
        cart.items.all().delete()
        return Response({'detail': 'Cart cleared.'}, status=status.HTTP_200_OK)


class OrderViewSet(viewsets.ModelViewSet):
    serializer_class = OrderSerializer
    permission_classes = [IsAuthenticated]
    filterset_fields = ['status']
    ordering_fields = ['created_at', 'total_amount']

    def get_queryset(self):
        user = self.request.user
        if user.role == 'admin':
            return Order.objects.all().select_related('user', 'shipping_address').prefetch_related('items')
        if user.role == 'vendor':
            return Order.objects.filter(items__product__vendor=user).distinct()
        return Order.objects.filter(user=user).prefetch_related('items', 'status_history')

    @action(detail=False, methods=['post'])
    @transaction.atomic
    def place_order(self, request):
        serializer = PlaceOrderSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            address = Address.objects.get(id=serializer.validated_data['shipping_address_id'], user=request.user)
        except Address.DoesNotExist:
            return Response({'detail': 'Address not found.'}, status=status.HTTP_404_NOT_FOUND)

        cart = Cart.objects.filter(user=request.user).first()
        if not cart or not cart.items.exists():
            return Response({'detail': 'Cart is empty.'}, status=status.HTTP_400_BAD_REQUEST)

        total = cart.total_price
        order = Order.objects.create(
            user=request.user,
            order_number=generate_order_number(),
            shipping_address=address,
            total_amount=total,
            notes=serializer.validated_data.get('notes', '')
        )

        for item in cart.items.all():
            OrderItem.objects.create(
                order=order,
                product=item.product,
                product_name=item.product.name,
                product_price=item.product.final_price,
                quantity=item.quantity,
                subtotal=item.subtotal
            )
            item.product.stock -= item.quantity
            item.product.save()

        cart.items.all().delete()

        OrderStatusHistory.objects.create(
            order=order,
            status=Order.PENDING,
            notes='Order placed.',
            changed_by=request.user
        )

        return Response(OrderSerializer(order).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['patch'], permission_classes=[IsVendorOrAdmin])
    def update_status(self, request, pk=None):
        order = self.get_object()
        new_status = request.data.get('status')
        valid_statuses = [s[0] for s in Order.STATUS_CHOICES]
        if new_status not in valid_statuses:
            return Response({'detail': 'Invalid status.'}, status=status.HTTP_400_BAD_REQUEST)

        order.status = new_status
        order.save()
        OrderStatusHistory.objects.create(
            order=order,
            status=new_status,
            notes=request.data.get('notes', ''),
            changed_by=request.user
        )
        return Response(OrderSerializer(order).data, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        order = self.get_object()
        if order.user != request.user:
            return Response({'detail': 'Not authorized.'}, status=status.HTTP_403_FORBIDDEN)
        if order.status not in [Order.PENDING, Order.CONFIRMED]:
            return Response({'detail': 'Cannot cancel this order.'}, status=status.HTTP_400_BAD_REQUEST)
        order.status = Order.CANCELLED
        order.save()
        OrderStatusHistory.objects.create(
            order=order, status=Order.CANCELLED, notes='Cancelled by customer.', changed_by=request.user
        )
        return Response({'detail': 'Order cancelled.'}, status=status.HTTP_200_OK)
