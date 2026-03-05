import secrets
from datetime import timedelta

from rest_framework import generics, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework_simplejwt.tokens import RefreshToken
from django.conf import settings
from django.utils import timezone
from .models import User, Address, EmailVerificationToken, PasswordResetToken
from .serializers import (
    RegisterSerializer, UserSerializer, ChangePasswordSerializer, AddressSerializer,
    EmailVerificationConfirmSerializer, PasswordResetRequestSerializer, PasswordResetConfirmSerializer
)
from .permissions import IsOwnerOrAdmin, IsAdmin
from apps.common.email import send_email


def _create_email_token(user):
    token = secrets.token_hex(32)
    expires_at = timezone.now() + timedelta(hours=settings.EMAIL_VERIFICATION_TTL_HOURS)
    EmailVerificationToken.objects.create(user=user, token=token, expires_at=expires_at)
    return token


def _create_password_reset_token(user):
    token = secrets.token_hex(32)
    expires_at = timezone.now() + timedelta(hours=settings.PASSWORD_RESET_TTL_HOURS)
    PasswordResetToken.objects.create(user=user, token=token, expires_at=expires_at)
    return token


class RegisterView(generics.CreateAPIView):
    serializer_class = RegisterSerializer
    permission_classes = [AllowAny]
    throttle_scope = 'auth_register'

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        token = _create_email_token(user)
        send_email(
            subject='Verify your email',
            message=f'Use this token to verify your email: {token}',
            recipients=[user.email]
        )
        refresh = RefreshToken.for_user(user)
        return Response({
            'user': UserSerializer(user).data,
            'refresh': str(refresh),
            'access': str(refresh.access_token),
        }, status=status.HTTP_201_CREATED)


class LogoutView(generics.GenericAPIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            refresh_token = request.data['refresh']
            token = RefreshToken(refresh_token)
            token.blacklist()
            return Response({'detail': 'Logged out successfully.'}, status=status.HTTP_200_OK)
        except Exception:
            return Response({'detail': 'Invalid token.'}, status=status.HTTP_400_BAD_REQUEST)


class ProfileView(generics.RetrieveUpdateAPIView):
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        return self.request.user


class ChangePasswordView(generics.UpdateAPIView):
    serializer_class = ChangePasswordSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        return self.request.user

    def update(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        request.user.set_password(serializer.validated_data['new_password'])
        request.user.save()
        return Response({'detail': 'Password changed successfully.'}, status=status.HTTP_200_OK)


class AddressViewSet(viewsets.ModelViewSet):
    serializer_class = AddressSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Address.objects.filter(user=self.request.user)

    @action(detail=True, methods=['patch'])
    def set_default(self, request, pk=None):
        address = self.get_object()
        Address.objects.filter(user=request.user).update(is_default=False)
        address.is_default = True
        address.save()
        return Response({'detail': 'Default address updated.'}, status=status.HTTP_200_OK)


class UserListView(generics.ListAPIView):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [IsAdmin]
    filterset_fields = ['role', 'is_active', 'is_verified']
    search_fields = ['email', 'first_name', 'last_name']
    ordering_fields = ['created_at', 'email']


class LoginView(TokenObtainPairView):
    throttle_scope = 'auth_login'


class EmailVerificationView(generics.GenericAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = EmailVerificationConfirmSerializer

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        token = serializer.validated_data['token']
        record = EmailVerificationToken.objects.filter(token=token, used_at__isnull=True).first()
        if not record or record.expires_at < timezone.now():
            return Response({'detail': 'Invalid or expired token.'}, status=status.HTTP_400_BAD_REQUEST)
        record.used_at = timezone.now()
        record.save(update_fields=['used_at'])
        user = record.user
        user.is_verified = True
        user.save(update_fields=['is_verified'])
        return Response({'detail': 'Email verified.'}, status=status.HTTP_200_OK)


class EmailVerificationRequestView(generics.GenericAPIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        if request.user.is_verified:
            return Response({'detail': 'Email already verified.'}, status=status.HTTP_200_OK)
        token = _create_email_token(request.user)
        send_email(
            subject='Verify your email',
            message=f'Use this token to verify your email: {token}',
            recipients=[request.user.email]
        )
        return Response({'detail': 'Verification email sent.'}, status=status.HTTP_200_OK)


class PasswordResetRequestView(generics.GenericAPIView):
    permission_classes = [AllowAny]
    serializer_class = PasswordResetRequestSerializer
    throttle_scope = 'auth_login'

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data['email']
        user = User.objects.filter(email=email).first()
        if user:
            token = _create_password_reset_token(user)
            send_email(
                subject='Password reset',
                message=f'Use this token to reset your password: {token}',
                recipients=[user.email]
            )
        return Response({'detail': 'If the email exists, a reset token was sent.'}, status=status.HTTP_200_OK)


class PasswordResetConfirmView(generics.GenericAPIView):
    permission_classes = [AllowAny]
    serializer_class = PasswordResetConfirmSerializer

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        token = serializer.validated_data['token']
        record = PasswordResetToken.objects.filter(token=token, used_at__isnull=True).first()
        if not record or record.expires_at < timezone.now():
            return Response({'detail': 'Invalid or expired token.'}, status=status.HTTP_400_BAD_REQUEST)
        user = record.user
        user.set_password(serializer.validated_data['new_password'])
        user.save()
        record.used_at = timezone.now()
        record.save(update_fields=['used_at'])
        return Response({'detail': 'Password reset successful.'}, status=status.HTTP_200_OK)
