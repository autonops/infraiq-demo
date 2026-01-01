"""
Order processing models.
Bounded Context: Orders
Dependencies: Users, Products, Payments, Inventory
"""

from decimal import Decimal
from django.db import models
from django.conf import settings


class Order(models.Model):
    """Customer order."""
    
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('confirmed', 'Confirmed'),
        ('processing', 'Processing'),
        ('shipped', 'Shipped'),
        ('delivered', 'Delivered'),
        ('cancelled', 'Cancelled'),
        ('refunded', 'Refunded'),
    ]
    
    # Relations
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.PROTECT, 
        related_name='orders'
    )
    
    # Order info
    order_number = models.CharField(max_length=32, unique=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    
    # Pricing
    subtotal = models.DecimalField(max_digits=10, decimal_places=2)
    tax = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    shipping_cost = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    discount = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    total = models.DecimalField(max_digits=10, decimal_places=2)
    
    # Addresses (denormalized for historical accuracy)
    shipping_name = models.CharField(max_length=100)
    shipping_address = models.TextField()
    billing_name = models.CharField(max_length=100)
    billing_address = models.TextField()
    
    # Payment
    payment_method = models.CharField(max_length=50)
    payment_id = models.CharField(max_length=100, blank=True)
    paid_at = models.DateTimeField(null=True, blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    shipped_at = models.DateTimeField(null=True, blank=True)
    delivered_at = models.DateTimeField(null=True, blank=True)
    
    # Notes
    customer_notes = models.TextField(blank=True)
    internal_notes = models.TextField(blank=True)
    
    class Meta:
        db_table = 'orders'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Order {self.order_number}"
    
    @property
    def is_paid(self):
        return self.paid_at is not None
    
    def calculate_total(self):
        self.total = self.subtotal + self.tax + self.shipping_cost - self.discount
        return self.total


class OrderItem(models.Model):
    """Individual item in an order."""
    
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    
    # Product info (denormalized)
    product_id = models.IntegerField()
    product_name = models.CharField(max_length=200)
    product_sku = models.CharField(max_length=50)
    
    # Pricing
    quantity = models.PositiveIntegerField(default=1)
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    total_price = models.DecimalField(max_digits=10, decimal_places=2)
    
    class Meta:
        db_table = 'order_items'
    
    def save(self, *args, **kwargs):
        self.total_price = self.unit_price * self.quantity
        super().save(*args, **kwargs)


class OrderStatusHistory(models.Model):
    """Track order status changes."""
    
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='status_history')
    status = models.CharField(max_length=20)
    changed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.SET_NULL, 
        null=True
    )
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'order_status_history'
        ordering = ['-created_at']
