from django.db import models
from django.conf import settings
from django.utils import timezone
from datetime import timedelta


class Cart(models.Model):
    """
    Shopping cart for users.
    Each user has one active cart at a time.
    """
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='cart',
        help_text="User who owns this cart"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Cart"
        verbose_name_plural = "Carts"
        permissions = [
            ('add_to_cart', 'Can add products to cart'),
            ('manage_cart', 'Can manage shopping cart'),
        ]
    
    def __str__(self):
        return f"Cart for {self.user.email}"
    
    def get_total_items(self):
        """Get total number of items in cart"""
        return self.items.filter(is_active=True).count()
    
    def get_total_quantity(self):
        """Get total quantity of all items in cart"""
        return sum(item.quantity for item in self.items.filter(is_active=True))
    
    def clear_expired_items(self):
        """Remove items that have been in cart for more than 24 hours"""
        expiry_time = timezone.now() - timedelta(days=1)
        expired_items = self.items.filter(
            created_at__lt=expiry_time,
            is_active=True
        )
        count = expired_items.count()
        expired_items.update(is_active=False)
        return count


class CartItem(models.Model):
    """
    Individual items in a shopping cart.
    Includes automatic expiry after 24 hours.
    """
    cart = models.ForeignKey(
        Cart,
        on_delete=models.CASCADE,
        related_name='items',
        help_text="Cart this item belongs to"
    )
    product_item_code = models.CharField(
        max_length=100,
        help_text="SAP Item Code of the product (e.g., FG00259)"
    )
    product_name = models.CharField(
        max_length=255,
        help_text="Product name for display"
    )
    quantity = models.PositiveIntegerField(
        default=1,
        help_text="Quantity of this product"
    )
    unit_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Unit price at the time of adding to cart"
    )
    notes = models.TextField(
        blank=True,
        null=True,
        help_text="Special instructions or notes"
    )
    is_active = models.BooleanField(
        default=True,
        help_text="Is this item still active in cart?"
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        help_text="When this item was added to cart"
    )
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Cart Item"
        verbose_name_plural = "Cart Items"
        ordering = ['-created_at']
        unique_together = [['cart', 'product_item_code', 'is_active']]
    
    def __str__(self):
        return f"{self.product_name} (x{self.quantity}) in {self.cart.user.email}'s cart"
    
    def is_expired(self):
        """Check if this item has been in cart for more than 24 hours"""
        expiry_time = timezone.now() - timedelta(days=1)
        return self.created_at < expiry_time
    
    def get_subtotal(self):
        """Calculate subtotal for this item"""
        if self.unit_price:
            return self.quantity * self.unit_price
        return 0


class Order(models.Model):
    """
    Order placed by a user.
    Tracks order history and payment status.
    """
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('confirmed', 'Confirmed'),
        ('shipped', 'Shipped'),
        ('delivered', 'Delivered'),
        ('cancelled', 'Cancelled'),
    ]
    
    PAYMENT_STATUS_CHOICES = [
        ('unpaid', 'Unpaid'),
        ('partially_paid', 'Partially Paid'),
        ('paid', 'Paid'),
        ('refunded', 'Refunded'),
    ]
    
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='orders',
        help_text="User who placed this order"
    )
    order_number = models.CharField(
        max_length=50,
        unique=True,
        help_text="Unique order number"
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending',
        help_text="Current order status"
    )
    payment_status = models.CharField(
        max_length=20,
        choices=PAYMENT_STATUS_CHOICES,
        default='unpaid',
        help_text="Payment status"
    )
    total_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        help_text="Total order amount"
    )
    paid_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        help_text="Amount paid so far"
    )
    notes = models.TextField(
        blank=True,
        null=True,
        help_text="Order notes or special instructions"
    )
    shipping_address = models.TextField(
        blank=True,
        null=True,
        help_text="Shipping address"
    )
    
    # SAP Integration
    sap_order_id = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text="SAP Sales Order ID if synced"
    )
    is_synced_to_sap = models.BooleanField(
        default=False,
        help_text="Has this order been synced to SAP?"
    )
    sap_sync_date = models.DateTimeField(
        blank=True,
        null=True,
        help_text="When was this order synced to SAP?"
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    completed_at = models.DateTimeField(
        blank=True,
        null=True,
        help_text="When was this order completed/delivered?"
    )
    
    class Meta:
        verbose_name = "Order"
        verbose_name_plural = "Orders"
        ordering = ['-created_at']
        permissions = [
            ('view_order_history', 'Can view order history'),
            ('manage_orders', 'Can manage orders'),
            ('sync_orders_to_sap', 'Can sync orders to SAP'),
        ]
    
    def __str__(self):
        return f"Order {self.order_number} - {self.user.email}"
    
    def get_total_items(self):
        """Get total number of unique items in order"""
        return self.items.count()
    
    def get_total_quantity(self):
        """Get total quantity of all items in order"""
        return sum(item.quantity for item in self.items.all())
    
    def update_total_amount(self):
        """Recalculate total amount from order items"""
        self.total_amount = sum(item.get_subtotal() for item in self.items.all())
        self.save()
        return self.total_amount
    
    def update_payment_status(self):
        """Update payment status based on paid amount"""
        if self.paid_amount >= self.total_amount:
            self.payment_status = 'paid'
        elif self.paid_amount > 0:
            self.payment_status = 'partially_paid'
        else:
            self.payment_status = 'unpaid'
        self.save()


class OrderItem(models.Model):
    """
    Individual items in an order.
    Snapshot of cart items at time of order placement.
    """
    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name='items',
        help_text="Order this item belongs to"
    )
    product_item_code = models.CharField(
        max_length=100,
        help_text="SAP Item Code of the product"
    )
    product_name = models.CharField(
        max_length=255,
        help_text="Product name at time of order"
    )
    quantity = models.PositiveIntegerField(
        default=1,
        help_text="Quantity ordered"
    )
    unit_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        help_text="Unit price at time of order"
    )
    subtotal = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        help_text="Subtotal (quantity × unit_price)"
    )
    notes = models.TextField(
        blank=True,
        null=True,
        help_text="Item-specific notes"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = "Order Item"
        verbose_name_plural = "Order Items"
        ordering = ['id']
    
    def __str__(self):
        return f"{self.product_name} (x{self.quantity}) in Order {self.order.order_number}"
    
    def get_subtotal(self):
        """Calculate subtotal"""
        return self.quantity * self.unit_price
    
    def save(self, *args, **kwargs):
        """Auto-calculate subtotal before saving"""
        self.subtotal = self.get_subtotal()
        super().save(*args, **kwargs)
