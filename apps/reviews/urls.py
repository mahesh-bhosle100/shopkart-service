from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ReviewViewSet, ReviewReportViewSet

router = DefaultRouter()
router.register('', ReviewViewSet, basename='review')
router.register('reports', ReviewReportViewSet, basename='review-report')

urlpatterns = [
    path('', include(router.urls)),
]
