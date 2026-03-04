from django.test import TestCase
from rest_framework.test import APITestCase
from rest_framework import status
from django.urls import reverse
from apps.users.models import User
from apps.products.models import Category, Product


class CategoryTest(APITestCase):
    def setUp(self):
        self.category = Category.objects.create(name='Electronics', slug='electronics')

    def test_list_categories(self):
        response = self.client.get('/api/v1/products/categories/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)


class ProductTest(APITestCase):
    def setUp(self):
        self.vendor = User.objects.create_user(
            email='vendor@example.com',
            password='StrongPass@123',
            first_name='Vendor',
            last_name='User',
            role='vendor'
        )
        self.category = Category.objects.create(name='Electronics', slug='electronics')
        self.client.force_authenticate(user=self.vendor)

    def test_create_product(self):
        response = self.client.post('/api/v1/products/', {
            'name': 'Test Product',
            'description': 'A test product description',
            'price': '999.00',
            'stock': 50,
            'category_id': self.category.id
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_list_products_public(self):
        self.client.logout()
        response = self.client.get('/api/v1/products/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
