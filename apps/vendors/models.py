from django.db import models
from apps.users.models import User


class VendorStore(models.Model):
    PENDING = 'pending'
    APPROVED = 'approved'
    REJECTED = 'rejected'

    STATUS_CHOICES = [
        (PENDING, 'Pending'),
        (APPROVED, 'Approved'),
        (REJECTED, 'Rejected'),
    ]

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='store')
    store_name = models.CharField(max_length=255, unique=True)
    slug = models.SlugField(max_length=255, unique=True)
    description = models.TextField(blank=True)
    logo = models.ImageField(upload_to='vendors/logos/', null=True, blank=True)
    banner = models.ImageField(upload_to='vendors/banners/', null=True, blank=True)
    phone = models.CharField(max_length=15, blank=True)
    address = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=PENDING)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'vendor_stores'
        verbose_name = 'Vendor Store'
        verbose_name_plural = 'Vendor Stores'
        ordering = ['-created_at']

    def __str__(self):
        return self.store_name

    @property
    def total_products(self):
        return self.user.products.filter(is_active=True).count()

    @property
    def total_orders(self):
        from apps.orders.models import OrderItem
        return OrderItem.objects.filter(product__vendor=self.user).values('order').distinct().count()
