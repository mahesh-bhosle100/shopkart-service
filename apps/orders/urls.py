from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import CartView, CartItemViewSet, OrderViewSet

router = DefaultRouter()
router.register('cart/items', CartItemViewSet, basename='cart-item')
router.register('', OrderViewSet, basename='order')

urlpatterns = [
    path('cart/', CartView.as_view(), name='cart'),
    path('', include(router.urls)),
]
