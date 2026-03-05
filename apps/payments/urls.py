from django.urls import path
from .views import InitiatePaymentView, VerifyPaymentView, PaymentListView, PaymentDetailView, PaymentWebhookView

urlpatterns = [
    path('initiate/', InitiatePaymentView.as_view(), name='payment-initiate'),
    path('verify/', VerifyPaymentView.as_view(), name='payment-verify'),
    path('webhook/', PaymentWebhookView.as_view(), name='payment-webhook'),
    path('', PaymentListView.as_view(), name='payment-list'),
    path('<int:pk>/', PaymentDetailView.as_view(), name='payment-detail'),
]
