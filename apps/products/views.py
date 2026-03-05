from rest_framework import viewsets, status, generics
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.decorators import action
from django.conf import settings
from django.db import models
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page
from django.utils.text import slugify
from .models import Category, Product, ProductImage
from .serializers import CategorySerializer, ProductListSerializer, ProductDetailSerializer, ProductImageSerializer
from apps.users.permissions import IsVendorOrAdmin, IsAdmin


@method_decorator(cache_page(settings.CACHE_TTL_SECONDS), name='list')
@method_decorator(cache_page(settings.CACHE_TTL_SECONDS), name='retrieve')
class CategoryViewSet(viewsets.ModelViewSet):
    queryset = Category.objects.filter(parent=None, is_active=True)
    serializer_class = CategorySerializer
    lookup_field = 'slug'

    def get_permissions(self):
        if self.action in ['list', 'retrieve']:
            return [AllowAny()]
        return [IsAdmin()]


@method_decorator(cache_page(settings.CACHE_TTL_SECONDS), name='list')
@method_decorator(cache_page(settings.CACHE_TTL_SECONDS), name='retrieve')
class ProductViewSet(viewsets.ModelViewSet):
    queryset = Product.objects.filter(is_active=True).select_related('vendor', 'category')
    lookup_field = 'slug'
    filterset_fields = ['category', 'is_featured', 'vendor']
    search_fields = ['name', 'description']
    ordering_fields = ['price', 'created_at', 'name']

    def get_serializer_class(self):
        if self.action == 'list':
            return ProductListSerializer
        return ProductDetailSerializer

    def get_permissions(self):
        if self.action in ['list', 'retrieve']:
            return [AllowAny()]
        return [IsVendorOrAdmin()]

    def get_queryset(self):
        queryset = super().get_queryset()
        q = self.request.query_params.get('q')
        if q:
            queryset = queryset.filter(
                models.Q(name__icontains=q) |
                models.Q(description__icontains=q) |
                models.Q(category__name__icontains=q) |
                models.Q(vendor__first_name__icontains=q) |
                models.Q(vendor__last_name__icontains=q)
            )
        if self.request.user.is_authenticated and self.request.user.role == 'vendor':
            if self.action not in ['list', 'retrieve']:
                return queryset.filter(vendor=self.request.user)
        return queryset

    def perform_create(self, serializer):
        name = serializer.validated_data.get('name', '')
        slug = slugify(name)
        counter = 1
        original_slug = slug
        while Product.objects.filter(slug=slug).exists():
            slug = f'{original_slug}-{counter}'
            counter += 1
        serializer.save(vendor=self.request.user, slug=slug)

    @action(detail=True, methods=['post'], permission_classes=[IsVendorOrAdmin])
    def upload_images(self, request, slug=None):
        product = self.get_object()
        images = request.FILES.getlist('images')
        if not images:
            return Response({'detail': 'No images provided.'}, status=status.HTTP_400_BAD_REQUEST)
        max_bytes = settings.MAX_UPLOAD_IMAGE_SIZE_MB * 1024 * 1024
        for img in images:
            if img.size > max_bytes:
                return Response(
                    {'detail': f'Image too large. Max size is {settings.MAX_UPLOAD_IMAGE_SIZE_MB}MB.'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            if img.content_type not in settings.ALLOWED_IMAGE_TYPES:
                return Response(
                    {'detail': f'Invalid image type: {img.content_type}.'},
                    status=status.HTTP_400_BAD_REQUEST
                )
        product_images = [ProductImage(product=product, image=img) for img in images]
        ProductImage.objects.bulk_create(product_images)
        return Response({'detail': f'{len(images)} images uploaded.'}, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=['get'], permission_classes=[IsVendorOrAdmin])
    def my_products(self, request):
        products = Product.objects.filter(vendor=request.user)
        serializer = ProductListSerializer(products, many=True)
        return Response(serializer.data)
