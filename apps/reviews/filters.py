import django_filters
from .models import Review


class ReviewFilter(django_filters.FilterSet):
    rating_min = django_filters.NumberFilter(field_name='rating', lookup_expr='gte')
    rating_max = django_filters.NumberFilter(field_name='rating', lookup_expr='lte')
    created_from = django_filters.DateTimeFilter(field_name='created_at', lookup_expr='gte')
    created_to = django_filters.DateTimeFilter(field_name='created_at', lookup_expr='lte')
    verified = django_filters.BooleanFilter(field_name='is_verified_purchase')

    class Meta:
        model = Review
        fields = [
            'product',
            'rating',
            'is_verified_purchase',
        ]
