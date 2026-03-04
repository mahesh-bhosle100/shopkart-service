from rest_framework import viewsets, status, generics
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from django.utils.text import slugify
from .models import VendorStore
from .serializers import VendorStoreSerializer
from apps.users.permissions import IsVendor, IsAdmin


class VendorStoreViewSet(viewsets.ModelViewSet):
    queryset = VendorStore.objects.filter(is_active=True, status='approved')
    serializer_class = VendorStoreSerializer
    lookup_field = 'slug'
    search_fields = ['store_name', 'description']
    ordering_fields = ['store_name', 'created_at']

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
