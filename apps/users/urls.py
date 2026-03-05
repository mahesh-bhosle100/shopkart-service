from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenRefreshView
from .views import (
    RegisterView, LogoutView, ProfileView, ChangePasswordView, AddressViewSet, UserListView,
    LoginView, EmailVerificationView, EmailVerificationRequestView,
    PasswordResetRequestView, PasswordResetConfirmView
)

router = DefaultRouter()
router.register('addresses', AddressViewSet, basename='address')

urlpatterns = [
    path('register/', RegisterView.as_view(), name='register'),
    path('login/', LoginView.as_view(), name='login'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token-refresh'),
    path('logout/', LogoutView.as_view(), name='logout'),
    path('profile/', ProfileView.as_view(), name='profile'),
    path('change-password/', ChangePasswordView.as_view(), name='change-password'),
    path('email/verify/', EmailVerificationView.as_view(), name='email-verify'),
    path('email/verify/request/', EmailVerificationRequestView.as_view(), name='email-verify-request'),
    path('password-reset/request/', PasswordResetRequestView.as_view(), name='password-reset-request'),
    path('password-reset/confirm/', PasswordResetConfirmView.as_view(), name='password-reset-confirm'),
    path('users/', UserListView.as_view(), name='user-list'),
    path('', include(router.urls)),
]
