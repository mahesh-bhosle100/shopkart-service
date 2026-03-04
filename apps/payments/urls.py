from django.urls import path
from .views import InitiatePaymentView, VerifyPaymentView, PaymentListView, PaymentDetailView

urlpatterns = [
    path('initiate/', InitiatePaymentView.as_view(), name='payment-initiate'),
    path('verify/', VerifyPaymentView.as_view(), name='payment-verify'),
    path('', PaymentListView.as_view(), name='payment-list'),
    path('<int:pk>/', PaymentDetailView.as_view(), name='payment-detail'),
]
