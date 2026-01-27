from rest_framework import serializers
from .models import Cart, CartItem, Order, OrderItem, Payment
from django.utils import timezone


class CartItemSerializer(serializers.ModelSerializer):
    """Serializer for cart items"""
    subtotal = serializers.SerializerMethodField()
    is_expired = serializers.SerializerMethodField()
    
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
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'subtotal', 'is_expired']
    
    def get_subtotal(self, obj):
        """Calculate subtotal for this item"""
        return obj.get_subtotal()
    
    def get_is_expired(self, obj):
        """Check if item is expired"""
        return obj.is_expired()


class CartSerializer(serializers.ModelSerializer):
    """Serializer for shopping cart"""
    items = CartItemSerializer(many=True, read_only=True)
    total_items = serializers.SerializerMethodField()
    total_quantity = serializers.SerializerMethodField()
    cart_total = serializers.SerializerMethodField()
    
    class Meta:
        model = Cart
        fields = [
            'id',
            'user',
            'items',
            'total_items',
            'total_quantity',
            'cart_total',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'user', 'created_at', 'updated_at']
    
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
            'created_at',
        ]
        read_only_fields = ['id', 'subtotal', 'created_at']


class OrderSerializer(serializers.ModelSerializer):
    """Serializer for orders"""
    items = OrderItemSerializer(many=True, read_only=True)
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
            'total_items',
            'total_quantity',
            'notes',
            'shipping_address',
            'sap_order_id',
            'is_synced_to_sap',
            'sap_sync_date',
            'created_at',
            'updated_at',
            'completed_at',
        ]
        read_only_fields = [
            'id',
            'order_number',
            'user',
            'total_amount',
            'created_at',
            'updated_at',
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
            'is_synced_to_sap',
            'created_at',
        ]
        read_only_fields = fields
    
    def get_total_items(self, obj):
        """Get total number of items"""
        return obj.get_total_items()


class CreateOrderSerializer(serializers.Serializer):
    """Serializer for creating an order from cart"""
    shipping_address = serializers.CharField(required=False, allow_blank=True)
    notes = serializers.CharField(required=False, allow_blank=True)


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
            'created_at',
            'updated_at',
            'completed_at',
        ]
        read_only_fields = [
            'id',
            'transaction_id',
            'user',
            'jazzcash_transaction_id',
            'jazzcash_response_code',
            'jazzcash_response_message',
            'created_at',
            'updated_at',
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
            'created_at',
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
