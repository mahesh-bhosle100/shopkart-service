import uuid
from rest_framework import viewsets, generics, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.db import transaction
from .models import Cart, CartItem, Order, OrderItem, OrderStatusHistory
from .serializers import (
    CartSerializer, CartItemSerializer, OrderSerializer, PlaceOrderSerializer, ReturnRequestSerializer
)
from apps.users.models import Address
from apps.users.permissions import IsVendorOrAdmin, IsCustomer
from apps.products.models import Product
from apps.common.email import send_email
from django.utils import timezone


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

    def get_throttles(self):
        if self.action in ['list', 'retrieve']:
            self.throttle_scope = 'orders_read'
        else:
            self.throttle_scope = 'orders_write'
        return super().get_throttles()

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

        cart_items = cart.items.select_related('product')
        product_ids = [item.product_id for item in cart_items]
        products = Product.objects.select_for_update().filter(id__in=product_ids)
        product_map = {p.id: p for p in products}

        total = 0
        order = Order.objects.create(
            user=request.user,
            order_number=generate_order_number(),
            shipping_address=address,
            total_amount=total,
            notes=serializer.validated_data.get('notes', '')
        )

        for item in cart_items:
            product = product_map.get(item.product_id)
            if not product:
                return Response({'detail': 'Product not found.'}, status=status.HTTP_404_NOT_FOUND)
            if product.stock < item.quantity:
                return Response(
                    {'detail': f'Only {product.stock} items available for {product.name}.'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            subtotal = product.final_price * item.quantity
            OrderItem.objects.create(
                order=order,
                product=product,
                product_name=product.name,
                product_price=product.final_price,
                quantity=item.quantity,
                subtotal=subtotal
            )
            product.stock -= item.quantity
            product.save(update_fields=['stock'])
            total += subtotal

        cart.items.all().delete()

        order.total_amount = total
        order.save(update_fields=['total_amount'])

        OrderStatusHistory.objects.create(
            order=order,
            status=Order.PENDING,
            notes='Order placed.',
            changed_by=request.user
        )

        send_email(
            subject='Order Placed',
            message=f'Your order {order.order_number} has been placed successfully.',
            recipients=[request.user.email]
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
        send_email(
            subject='Order Status Updated',
            message=f'Your order {order.order_number} status changed to {new_status}.',
            recipients=[order.user.email]
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


class ReturnRequestViewSet(viewsets.ModelViewSet):
    serializer_class = ReturnRequestSerializer
    permission_classes = [IsAuthenticated]
    ordering_fields = ['created_at', 'status']

    def get_permissions(self):
        if self.action == 'create':
            return [IsCustomer()]
        if self.action == 'update_status':
            return [IsVendorOrAdmin()]
        if self.action in ['list', 'retrieve']:
            return [IsAuthenticated()]
        return super().get_permissions()

    def get_queryset(self):
        user = self.request.user
        if user.role == 'admin':
            return ReturnRequest.objects.all()
        if user.role == 'vendor':
            return ReturnRequest.objects.filter(order_item__product__vendor=user)
        return ReturnRequest.objects.filter(user=user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    @action(detail=True, methods=['patch'], permission_classes=[IsVendorOrAdmin])
    def update_status(self, request, pk=None):
        return_request = self.get_object()
        new_status = request.data.get('status')
        valid_statuses = [s[0] for s in ReturnRequest.STATUS_CHOICES]
        if new_status not in valid_statuses:
            return Response({'detail': 'Invalid status.'}, status=status.HTTP_400_BAD_REQUEST)

        return_request.status = new_status
        return_request.resolved_by = request.user
        return_request.resolved_at = timezone.now()
        return_request.save(update_fields=['status', 'resolved_by', 'resolved_at'])

        send_email(
            subject='Return Request Update',
            message=f'Your return request #{return_request.id} status changed to {new_status}.',
            recipients=[return_request.user.email]
        )

        return Response(ReturnRequestSerializer(return_request).data, status=status.HTTP_200_OK)
