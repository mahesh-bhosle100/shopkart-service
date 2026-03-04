from rest_framework import viewsets
from rest_framework.permissions import AllowAny, IsAuthenticated
from .models import Review
from .serializers import ReviewSerializer
from .filters import ReviewFilter
from apps.users.permissions import IsAdmin


class ReviewViewSet(viewsets.ModelViewSet):
    queryset = Review.objects.filter(is_active=True).select_related('user', 'product')
    serializer_class = ReviewSerializer
    filterset_class = ReviewFilter
    search_fields = ['title', 'comment', 'user__full_name', 'product__name']
    ordering_fields = ['rating', 'created_at']

    def get_permissions(self):
        if self.action in ['list', 'retrieve']:
            return [AllowAny()]
        if self.action == 'destroy':
            return [IsAdmin()]
        return [IsAuthenticated()]

    def get_queryset(self):
        queryset = super().get_queryset()
        product_id = self.request.query_params.get('product_id')
        if product_id:
            queryset = queryset.filter(product_id=product_id)
        return queryset

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)
