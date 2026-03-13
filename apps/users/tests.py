from django.urls import reverse
from rest_framework.test import APITestCase
from rest_framework import status
from apps.users.models import User


class UserRegistrationTest(APITestCase):
    def setUp(self):
        self.register_url = reverse('register')
        self.user_data = {
            'email': 'test@example.com',
            'first_name': 'Test',
            'last_name': 'User',
            'password': 'StrongPass@123',
            'password2': 'StrongPass@123',
            'role': 'customer'
        }

    def test_register_success(self):
        response = self.client.post(self.register_url, self.user_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn('access', response.data)
        self.assertIn('refresh', response.data)

    def test_register_password_mismatch(self):
        self.user_data['password2'] = 'WrongPass@123'
        response = self.client.post(self.register_url, self.user_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_register_duplicate_email(self):
        self.client.post(self.register_url, self.user_data, format='json')
        response = self.client.post(self.register_url, self.user_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class UserLoginTest(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email='login@example.com',
            password='StrongPass@123',
            first_name='Login',
            last_name='User'
        )
        self.login_url = reverse('login')

    def test_login_success(self):
        response = self.client.post(self.login_url, {
            'email': 'login@example.com',
            'password': 'StrongPass@123'
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('access', response.data)

    def test_login_wrong_password(self):
        response = self.client.post(self.login_url, {
            'email': 'login@example.com',
            'password': 'WrongPass'
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class UserProfileTest(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email='profile@example.com',
            password='StrongPass@123',
            first_name='Profile',
            last_name='User'
        )
        self.client.force_authenticate(user=self.user)
        self.profile_url = reverse('profile')

    def test_get_profile(self):
        response = self.client.get(self.profile_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['email'], self.user.email)

    def test_update_profile(self):
        response = self.client.patch(self.profile_url, {'first_name': 'Updated'}, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['first_name'], 'Updated')
