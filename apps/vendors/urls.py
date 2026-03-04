from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import VendorStoreViewSet

router = DefaultRouter()
router.register('', VendorStoreViewSet, basename='vendor')

urlpatterns = [
    path('', include(router.urls)),
]
