import csv
from io import StringIO

from rest_framework import viewsets, status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.decorators import action
from rest_framework.response import Response
from django.http import HttpResponse
from django.conf import settings
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page
from django.utils import timezone
from django.db.models import Avg, Count
from apps.common.email import send_email
from .models import Review, ReviewReport
from .serializers import ReviewSerializer, ReviewReportSerializer
from .filters import ReviewFilter
from apps.users.permissions import IsAdmin, IsVendorOrAdmin, IsReviewOwnerOrAdmin


@method_decorator(cache_page(settings.CACHE_TTL_SECONDS), name='list')
@method_decorator(cache_page(settings.CACHE_TTL_SECONDS), name='retrieve')
class ReviewViewSet(viewsets.ModelViewSet):
    queryset = Review.objects.filter(is_active=True).select_related('user', 'product')
    serializer_class = ReviewSerializer
    filterset_class = ReviewFilter
    search_fields = ['title', 'comment', 'user__full_name', 'product__name']
    ordering_fields = ['rating', 'created_at']

    def get_permissions(self):
        if self.action in ['list', 'retrieve', 'stats']:
            return [AllowAny()]
        if self.action in ['update', 'partial_update']:
            return [IsReviewOwnerOrAdmin()]
        if self.action in ['destroy', 'approve', 'deactivate']:
            return [IsAdmin()]
        if self.action in ['vendor_reviews', 'export']:
            return [IsVendorOrAdmin()]
        return [IsAuthenticated()]

    def get_throttles(self):
        if self.action in ['list', 'retrieve', 'stats']:
            self.throttle_scope = 'reviews_read'
        elif self.action in ['create', 'update', 'partial_update', 'destroy', 'approve', 'deactivate']:
            self.throttle_scope = 'reviews_write'
        elif self.action in ['vendor_reviews', 'export']:
            self.throttle_scope = 'reviews_export'
        return super().get_throttles()

    def get_queryset(self):
        queryset = super().get_queryset()
        product_id = self.request.query_params.get('product_id')
        if product_id:
            queryset = queryset.filter(product_id=product_id)
        return queryset

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    @action(detail=False, methods=['get'], permission_classes=[IsVendorOrAdmin])
    def vendor_reviews(self, request):
        queryset = self.get_queryset()
        if request.user.role == 'vendor':
            queryset = queryset.filter(product__vendor=request.user)
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'], permission_classes=[IsVendorOrAdmin])
    def export(self, request):
        queryset = self.get_queryset()
        if request.user.role == 'vendor':
            queryset = queryset.filter(product__vendor=request.user)
        export_format = request.query_params.get('format', 'json').lower()

        if export_format == 'csv':
            buffer = StringIO()
            writer = csv.writer(buffer)
            writer.writerow([
                'id', 'product_id', 'product_name', 'user_id', 'user_name',
                'rating', 'title', 'comment', 'is_verified_purchase',
                'is_active', 'created_at'
            ])
            for review in queryset:
                writer.writerow([
                    review.id,
                    review.product_id,
                    review.product.name if review.product else '',
                    review.user_id,
                    review.user.full_name,
                    review.rating,
                    review.title,
                    review.comment,
                    review.is_verified_purchase,
                    review.is_active,
                    review.created_at.isoformat(),
                ])
            response = HttpResponse(buffer.getvalue(), content_type='text/csv')
            response['Content-Disposition'] = 'attachment; filename="reviews.csv"'
            return response

        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(detail=False, methods=['get'], permission_classes=[AllowAny])
    def stats(self, request):
        product_id = request.query_params.get('product_id')
        if not product_id:
            return Response({'detail': 'product_id is required.'}, status=status.HTTP_400_BAD_REQUEST)
        queryset = Review.objects.filter(product_id=product_id, is_active=True)
        data = queryset.aggregate(
            count=Count('id'),
            average=Avg('rating'),
        )
        distribution = queryset.values('rating').annotate(total=Count('id'))
        dist_map = {item['rating']: item['total'] for item in distribution}
        data['distribution'] = {str(i): dist_map.get(i, 0) for i in range(1, 6)}
        data['average'] = round(data['average'] or 0, 2)
        return Response(data)

    @action(detail=True, methods=['post'], permission_classes=[IsVendorOrAdmin])
    def reply(self, request, pk=None):
        review = self.get_object()
        if request.user.role == 'vendor' and review.product.vendor != request.user:
            return Response({'detail': 'Not authorized for this review.'}, status=status.HTTP_403_FORBIDDEN)
        reply_text = request.data.get('reply', '').strip()
        if not reply_text:
            return Response({'detail': 'Reply text is required.'}, status=status.HTTP_400_BAD_REQUEST)
        review.vendor_reply = reply_text
        review.vendor_replied_at = timezone.now()
        review.vendor_replied_by = request.user
        review.save(update_fields=['vendor_reply', 'vendor_replied_at', 'vendor_replied_by'])
        send_email(
            subject='Vendor replied to your review',
            message=f'Your review for {review.product.name} has a reply: {reply_text}',
            recipients=[review.user.email]
        )
        return Response({'detail': 'Reply saved.'}, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def report(self, request, pk=None):
        review = self.get_object()
        # Ensure serializer has request context and review id for validation
        data = request.data.copy()
        if 'review' not in data:
            data['review'] = review.id
        serializer = ReviewReportSerializer(data=data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        serializer.save(review=review, reporter=request.user)
        return Response({'detail': 'Report submitted.'}, status=status.HTTP_201_CREATED)


class ReviewReportViewSet(viewsets.ModelViewSet):
    queryset = ReviewReport.objects.all()
    serializer_class = ReviewReportSerializer

    def get_permissions(self):
        if self.action in ['list', 'retrieve', 'partial_update', 'update']:
            return [IsAdmin()]
        return [IsAuthenticated()]

    def perform_create(self, serializer):
        serializer.save(reporter=self.request.user)

    @action(detail=True, methods=['patch'], permission_classes=[IsAdmin])
    def approve(self, request, pk=None):
        report = self.get_object()
        review = report.review
        review.is_active = True
        review.save(update_fields=['is_active'])
        report.status = ReviewReport.RESOLVED
        report.resolved_by = request.user
        report.resolved_at = timezone.now()
        report.save(update_fields=['status', 'resolved_by', 'resolved_at'])
        return Response({'detail': 'Review approved.'}, status=status.HTTP_200_OK)

    @action(detail=True, methods=['patch'], permission_classes=[IsAdmin])
    def deactivate(self, request, pk=None):
        report = self.get_object()
        review = report.review
        review.is_active = False
        review.save(update_fields=['is_active'])
        report.status = ReviewReport.REJECTED
        report.resolved_by = request.user
        report.resolved_at = timezone.now()
        report.save(update_fields=['status', 'resolved_by', 'resolved_at'])
        return Response({'detail': 'Review deactivated.'}, status=status.HTTP_200_OK)
