from rest_framework import viewsets, status, generics
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from django.conf import settings
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page
from django.utils import timezone
from datetime import timedelta
from django.db.models import Sum, Avg
from django.utils.text import slugify
from .models import VendorStore
from .serializers import VendorStoreSerializer
from apps.users.permissions import IsVendor, IsAdmin
from apps.products.models import Product
from apps.orders.models import OrderItem, Order
from apps.reviews.models import Review


@method_decorator(cache_page(settings.CACHE_TTL_SECONDS), name='list')
@method_decorator(cache_page(settings.CACHE_TTL_SECONDS), name='retrieve')
class VendorStoreViewSet(viewsets.ModelViewSet):
    queryset = VendorStore.objects.filter(is_active=True, status='approved')
    serializer_class = VendorStoreSerializer
    lookup_field = 'slug'
    search_fields = ['store_name', 'description']
    ordering_fields = ['store_name', 'created_at']

    def get_throttles(self):
        if self.action == 'dashboard':
            self.throttle_scope = 'vendors_dashboard'
        return super().get_throttles()

    def get_permissions(self):
        if self.action in ['list', 'retrieve']:
            return [AllowAny()]
        if self.action in ['approve', 'reject']:
            return [IsAdmin()]
        return [IsVendor()]

    def get_queryset(self):
        if self.request.user.is_authenticated and self.request.user.role == 'admin':
            return VendorStore.objects.all()
        return super().get_queryset()

    def perform_create(self, serializer):
        store_name = serializer.validated_data.get('store_name', '')
        slug = slugify(store_name)
        serializer.save(user=self.request.user, slug=slug)

    @action(detail=False, methods=['get'], permission_classes=[IsVendor])
    def my_store(self, request):
        try:
            store = VendorStore.objects.get(user=request.user)
            serializer = self.get_serializer(store)
            return Response(serializer.data)
        except VendorStore.DoesNotExist:
            return Response({'detail': 'Store not found.'}, status=status.HTTP_404_NOT_FOUND)

    @action(detail=False, methods=['get'], permission_classes=[IsVendor])
    def dashboard(self, request):
        vendor = request.user
        products = Product.objects.filter(vendor=vendor, is_active=True)
        product_ids = products.values_list('id', flat=True)

        orders = Order.objects.filter(items__product__vendor=vendor).distinct()
        revenue = OrderItem.objects.filter(product__vendor=vendor).aggregate(total=Sum('subtotal'))['total'] or 0

        reviews = Review.objects.filter(product__vendor=vendor, is_active=True)
        avg_rating = reviews.aggregate(avg=Avg('rating'))['avg'] or 0

        last_30_days = timezone.now() - timedelta(days=30)
        recent_orders = orders.filter(created_at__gte=last_30_days).count()
        recent_reviews = reviews.filter(created_at__gte=last_30_days).count()

        data = {
            'total_products': products.count(),
            'total_orders': orders.count(),
            'total_revenue': float(revenue),
            'average_rating': round(avg_rating, 2) if avg_rating else 0,
            'recent_orders_30d': recent_orders,
            'recent_reviews_30d': recent_reviews,
        }
        return Response(data)

    @action(detail=True, methods=['patch'], permission_classes=[IsAdmin])
    def approve(self, request, slug=None):
        store = self.get_object()
        store.status = VendorStore.APPROVED
        store.save()
        return Response({'detail': 'Store approved.'}, status=status.HTTP_200_OK)

    @action(detail=True, methods=['patch'], permission_classes=[IsAdmin])
    def reject(self, request, slug=None):
        store = self.get_object()
        store.status = VendorStore.REJECTED
        store.save()
        return Response({'detail': 'Store rejected.'}, status=status.HTTP_200_OK)
