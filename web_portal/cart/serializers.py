from rest_framework import serializers
from .models import Cart, CartItem, Order, OrderItem, Payment, OrderStatusHistory
from django.utils import timezone
from django.conf import settings
import os


class CartItemSerializer(serializers.ModelSerializer):
    """Serializer for cart items"""
    subtotal = serializers.SerializerMethodField()
    is_expired = serializers.SerializerMethodField()
    product_image_url = serializers.SerializerMethodField()
    product_description_urdu_url = serializers.SerializerMethodField()
    
    class Meta:
        model = CartItem
        fields = [
            'id',
            'product_item_code',
            'product_name',
            'quantity',
            'unit_price',
            'subtotal',
            'notes',
            'is_active',
            'is_expired',
            'product_image_url',
            'product_description_urdu_url',
            'created_date',
            'updated_date',
        ]
        read_only_fields = ['id', 'created_date', 'updated_date', 'subtotal', 'is_expired', 'product_image_url', 'product_description_urdu_url']
    
    def get_subtotal(self, obj):
        """Calculate subtotal for this item"""
        return obj.get_subtotal()
    
    def get_is_expired(self, obj):
        """Check if item is expired"""
        return obj.is_expired()
    
    def get_product_image_url(self, obj):
        """Get product image URL from media folder"""
        # Get database from context or default to 4B-BIO
        database = self.context.get('database', '4B-BIO')
        
        # Construct image path based on product_item_code
        # Assuming image naming convention: {ItemCode}-{ProductName}.jpg
        # You may need to adjust this based on your actual SAP data
        image_filename = f"{obj.product_item_code}.jpg"
        image_path = f"/media/product_images/{database}/{image_filename}"
        
        # Check if file exists (optional)
        # For now, return the path - frontend can handle 404s
        return image_path
    
    def get_product_description_urdu_url(self, obj):
        """Get product Urdu description image URL"""
        database = self.context.get('database', '4B-BIO')
        image_filename = f"{obj.product_item_code}-urdu.jpg"
        image_path = f"/media/product_images/{database}/{image_filename}"
        return image_path


class CartSerializer(serializers.ModelSerializer):
    """Serializer for shopping cart"""
    items = CartItemSerializer(many=True, read_only=True)
    total_items = serializers.SerializerMethodField()
    total_quantity = serializers.SerializerMethodField()
    cart_total = serializers.SerializerMethodField()
    cart_id = serializers.IntegerField(source='id', read_only=True)
    user_id = serializers.IntegerField(source='user.id', read_only=True)
    
    class Meta:
        model = Cart
        fields = [
            'cart_id',
            'id',
            'user_id',
            'user',
            'items',
            'total_items',
            'total_quantity',
            'cart_total',
            'created_date',
            'updated_date',
        ]
        read_only_fields = ['id', 'cart_id', 'user_id', 'user', 'created_date', 'updated_date']
    
    def get_total_items(self, obj):
        """Get total number of items"""
        return obj.get_total_items()
    
    def get_total_quantity(self, obj):
        """Get total quantity"""
        return obj.get_total_quantity()
    
    def get_cart_total(self, obj):
        """Calculate cart total"""
        return sum(item.get_subtotal() for item in obj.items.filter(is_active=True))


class AddToCartSerializer(serializers.Serializer):
    """Serializer for adding items to cart"""
    cart_id = serializers.IntegerField(required=True)
    user_id = serializers.IntegerField(required=True)
    product_item_code = serializers.CharField(max_length=100, required=True)
    product_name = serializers.CharField(max_length=255, required=True)
    quantity = serializers.IntegerField(min_value=1, default=1)
    unit_price = serializers.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        required=False,
        allow_null=True
    )
    notes = serializers.CharField(required=False, allow_blank=True)
    database = serializers.CharField(max_length=50, default='4B-BIO')


class UpdateCartItemSerializer(serializers.Serializer):
    """Serializer for updating cart item quantity"""
    quantity = serializers.IntegerField(min_value=1, required=True)
    notes = serializers.CharField(required=False, allow_blank=True)


class OrderItemSerializer(serializers.ModelSerializer):
    """Serializer for order items"""
    
    class Meta:
        model = OrderItem
        fields = [
            'id',
            'product_item_code',
            'product_name',
            'quantity',
            'unit_price',
            'subtotal',
            'notes',
            'created_date',
        ]
        read_only_fields = ['id', 'subtotal', 'created_date']


class OrderStatusHistorySerializer(serializers.ModelSerializer):
    """Serializer for order status history"""
    changed_by_name = serializers.SerializerMethodField()
    
    class Meta:
        model = OrderStatusHistory
        fields = [
            'id',
            'old_status',
            'new_status',
            'changed_by',
            'changed_by_name',
            'notes',
            'created_at',
        ]
        read_only_fields = ['id', 'created_at']
    
    def get_changed_by_name(self, obj):
        if obj.changed_by:
            if hasattr(obj.changed_by, 'first_name') and obj.changed_by.first_name:
                return f"{obj.changed_by.first_name} {obj.changed_by.last_name}".strip()
            return obj.changed_by.email
        return "System"


class OrderSerializer(serializers.ModelSerializer):
    """Serializer for orders"""
    items = OrderItemSerializer(many=True, read_only=True)
    status_history = OrderStatusHistorySerializer(many=True, read_only=True)
    total_items = serializers.SerializerMethodField()
    total_quantity = serializers.SerializerMethodField()
    user_email = serializers.CharField(source='user.email', read_only=True)
    user_name = serializers.SerializerMethodField()
    
    class Meta:
        model = Order
        fields = [
            'id',
            'order_number',
            'user',
            'user_email',
            'user_name',
            'status',
            'payment_status',
            'total_amount',
            'paid_amount',
            'items',
            'status_history',
            'total_items',
            'total_quantity',
            'notes',
            # Customer details
            'customer_first_name',
            'customer_last_name',
            'customer_phone',
            'customer_email',
            # Shipping details
            'shipping_address',
            'shipping_area',
            'shipping_city',
            'shipping_postal_code',
            # Payment details
            'payment_method',
            'payment_phone',
            # SAP Integration
            'sap_order_id',
            'is_synced_to_sap',
            'sap_sync_date',
            'created_date',
            'updated_date',
            'completed_at',
        ]
        read_only_fields = [
            'id',
            'order_number',
            'user',
            'total_amount',
            'created_date',
            'updated_date',
        ]
    
    def get_total_items(self, obj):
        """Get total number of items"""
        return obj.get_total_items()
    
    def get_total_quantity(self, obj):
        """Get total quantity"""
        return obj.get_total_quantity()
    
    def get_user_name(self, obj):
        """Get user's full name"""
        if hasattr(obj.user, 'first_name') and hasattr(obj.user, 'last_name'):
            return f"{obj.user.first_name} {obj.user.last_name}".strip()
        return obj.user.email


class OrderListSerializer(serializers.ModelSerializer):
    """Simplified serializer for order list"""
    user_email = serializers.CharField(source='user.email', read_only=True)
    total_items = serializers.SerializerMethodField()
    customer_name = serializers.SerializerMethodField()
    
    class Meta:
        model = Order
        fields = [
            'id',
            'order_number',
            'user_email',
            'status',
            'payment_status',
            'total_amount',
            'paid_amount',
            'total_items',
            'customer_name',
            'customer_phone',
            'shipping_city',
            'payment_method',
            'is_synced_to_sap',
            'created_date',
        ]
        read_only_fields = fields
    
    def get_total_items(self, obj):
        """Get total number of items"""
        return obj.get_total_items()
    
    def get_customer_name(self, obj):
        """Get customer's full name"""
        if obj.customer_first_name and obj.customer_last_name:
            return f"{obj.customer_first_name} {obj.customer_last_name}".strip()
        elif obj.customer_first_name:
            return obj.customer_first_name
        elif obj.customer_last_name:
            return obj.customer_last_name
        return ""


class CreateOrderSerializer(serializers.Serializer):
    """Serializer for creating an order from cart via checkout"""
    # Customer details
    customer_first_name = serializers.CharField(max_length=100, required=True)
    customer_last_name = serializers.CharField(max_length=100, required=True)
    customer_phone = serializers.CharField(max_length=20, required=True)
    customer_email = serializers.EmailField(required=True)
    
    # Shipping details
    shipping_address = serializers.CharField(required=True)
    shipping_area = serializers.CharField(max_length=100, required=True)
    shipping_city = serializers.CharField(max_length=100, required=True)
    shipping_postal_code = serializers.CharField(max_length=20, required=False, allow_blank=True)
    
    # Payment details
    payment_method = serializers.ChoiceField(
        choices=Order.PAYMENT_METHOD_CHOICES,
        required=True
    )
    payment_phone = serializers.CharField(
        max_length=20,
        required=False,
        allow_blank=True,
        help_text="Required for JazzCash/Easypaisa payments"
    )
    
    # Order notes
    notes = serializers.CharField(required=False, allow_blank=True)


class CheckoutSerializer(serializers.Serializer):
    """Serializer for checkout - creates order from cart with normalized data"""
    # Customer details
    customer_first_name = serializers.CharField(max_length=100, required=True)
    customer_last_name = serializers.CharField(max_length=100, required=True)
    customer_phone = serializers.CharField(max_length=20, required=True)
    customer_email = serializers.EmailField(required=True)
    
    # Shipping details
    shipping_address = serializers.CharField(required=True)
    shipping_area = serializers.CharField(max_length=100, required=True)
    shipping_city = serializers.CharField(max_length=100, required=True)
    shipping_postal_code = serializers.CharField(max_length=20, required=False, allow_blank=True)
    
    # Payment details
    payment_method = serializers.ChoiceField(
        choices=Order.PAYMENT_METHOD_CHOICES,
        required=True
    )
    payment_phone = serializers.CharField(
        max_length=20,
        required=False,
        allow_blank=True,
        help_text="Required for JazzCash/Easypaisa payments"
    )
    
    # Order details
    notes = serializers.CharField(required=False, allow_blank=True)
    
    # Database context (for product images)
    database = serializers.CharField(max_length=20, default='4B-BIO', required=False)
    
    def validate(self, data):
        """Validate payment phone for mobile wallet payments"""
        payment_method = data.get('payment_method')
        payment_phone = data.get('payment_phone')
        
        # Require payment_phone for JazzCash and Easypaisa
        if payment_method in ['jazzcash', 'easypaisa'] and not payment_phone:
            raise serializers.ValidationError({
                'payment_phone': f'Phone number is required for {payment_method} payments'
            })
        
        return data


class UpdateOrderStatusSerializer(serializers.Serializer):
    """Serializer for updating order status"""
    status = serializers.ChoiceField(choices=Order.STATUS_CHOICES, required=True)


class UpdatePaymentSerializer(serializers.Serializer):
    """Serializer for updating payment information"""
    paid_amount = serializers.DecimalField(
        max_digits=12, 
        decimal_places=2, 
        min_value=0,
        required=True
    )
    payment_status = serializers.ChoiceField(
        choices=Order.PAYMENT_STATUS_CHOICES,
        required=False
    )


# =============== Payment Serializers ===============

class PaymentSerializer(serializers.ModelSerializer):
    """Serializer for payment records"""
    order_number = serializers.CharField(source='order.order_number', read_only=True)
    user_email = serializers.CharField(source='user.email', read_only=True)
    payment_method_display = serializers.CharField(source='get_payment_method_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    
    class Meta:
        model = Payment
        fields = [
            'id',
            'transaction_id',
            'order',
            'order_number',
            'user',
            'user_email',
            'payment_method',
            'payment_method_display',
            'amount',
            'status',
            'status_display',
            'jazzcash_transaction_id',
            'jazzcash_response_code',
            'jazzcash_response_message',
            'customer_phone',
            'customer_email',
            'notes',
            'created_date',
            'updated_date',
            'completed_at',
        ]
        read_only_fields = [
            'id',
            'transaction_id',
            'user',
            'jazzcash_transaction_id',
            'jazzcash_response_code',
            'jazzcash_response_message',
            'created_date',
            'updated_date',
            'completed_at',
        ]


class PaymentListSerializer(serializers.ModelSerializer):
    """Simplified serializer for payment list"""
    order_number = serializers.CharField(source='order.order_number', read_only=True)
    payment_method_display = serializers.CharField(source='get_payment_method_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    
    class Meta:
        model = Payment
        fields = [
            'id',
            'transaction_id',
            'order_number',
            'payment_method',
            'payment_method_display',
            'amount',
            'status',
            'status_display',
            'created_date',
        ]
        read_only_fields = fields


class InitiatePaymentSerializer(serializers.Serializer):
    """Serializer for initiating a payment"""
    order_id = serializers.IntegerField(required=True)
    payment_method = serializers.ChoiceField(
        choices=Payment.PAYMENT_METHOD_CHOICES,
        required=True
    )
    amount = serializers.DecimalField(
        max_digits=12,
        decimal_places=2,
        min_value=1,
        required=True
    )
    customer_phone = serializers.CharField(
        max_length=20,
        required=False,
        help_text="Customer mobile number (format: 03xxxxxxxxx)"
    )
    customer_email = serializers.EmailField(required=False)
    
    def validate_customer_phone(self, value):
        """Validate Pakistani mobile number format"""
        if value and not value.startswith('03') and not value.startswith('+923'):
            raise serializers.ValidationError(
                "Phone number must be in format 03xxxxxxxxx or +923xxxxxxxxx"
            )
        return value
    
    def validate(self, data):
        """Validate payment request"""
        # JazzCash requires phone number
        if data['payment_method'] == 'jazzcash' and not data.get('customer_phone'):
            raise serializers.ValidationError({
                'customer_phone': 'Phone number is required for JazzCash payments'
            })
        return data


class JazzCashPaymentResponseSerializer(serializers.Serializer):
    """Serializer for JazzCash payment response/callback"""
    pp_TxnRefNo = serializers.CharField(required=True)
    pp_ResponseCode = serializers.CharField(required=True)
    pp_ResponseMessage = serializers.CharField(required=False, allow_blank=True)
    pp_Amount = serializers.CharField(required=True)
    pp_BillReference = serializers.CharField(required=False, allow_blank=True)
    pp_SecureHash = serializers.CharField(required=True)
    
    # Optional fields
    pp_TxnDateTime = serializers.CharField(required=False, allow_blank=True)
    pp_TxnType = serializers.CharField(required=False, allow_blank=True)
    pp_MerchantID = serializers.CharField(required=False, allow_blank=True)


class VerifyPaymentSerializer(serializers.Serializer):
    """Serializer for manual payment verification"""
    transaction_id = serializers.CharField(required=True)
