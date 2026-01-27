from django.contrib import admin
from .models import Cart, CartItem, Order, OrderItem, Payment


@admin.register(Cart)
class CartAdmin(admin.ModelAdmin):
    list_display = ['id', 'user', 'get_total_items', 'created_at', 'updated_at']
    search_fields = ['user__email', 'user__username']
    readonly_fields = ['created_at', 'updated_at']
    
    def get_total_items(self, obj):
        return obj.get_total_items()
    get_total_items.short_description = 'Total Items'


class CartItemInline(admin.TabularInline):
    model = CartItem
    extra = 0
    readonly_fields = ['created_at', 'updated_at']


@admin.register(CartItem)
class CartItemAdmin(admin.ModelAdmin):
    list_display = [
        'id',
        'cart',
        'product_item_code',
        'product_name',
        'quantity',
        'unit_price',
        'is_active',
        'is_expired',
        'created_at'
    ]
    list_filter = ['is_active', 'created_at']
    search_fields = ['product_item_code', 'product_name', 'cart__user__email']
    readonly_fields = ['created_at', 'updated_at']
    
    def is_expired(self, obj):
        return obj.is_expired()
    is_expired.boolean = True
    is_expired.short_description = 'Expired'


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ['subtotal', 'created_at']


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = [
        'order_number',
        'user',
        'status',
        'payment_status',
        'total_amount',
        'paid_amount',
        'is_synced_to_sap',
        'created_at'
    ]
    list_filter = ['status', 'payment_status', 'is_synced_to_sap', 'created_at']
    search_fields = [
        'order_number',
        'user__email',
        'user__username',
        'sap_order_id'
    ]
    readonly_fields = [
        'order_number',
        'created_at',
        'updated_at',
        'get_total_items',
        'get_total_quantity'
    ]
    inlines = [OrderItemInline]
    
    fieldsets = (
        ('Order Information', {
            'fields': (
                'order_number',
                'user',
                'status',
                'get_total_items',
                'get_total_quantity',
            )
        }),
        ('Payment Information', {
            'fields': (
                'payment_status',
                'total_amount',
                'paid_amount',
            )
        }),
        ('Shipping & Notes', {
            'fields': (
                'shipping_address',
                'notes',
            )
        }),
        ('SAP Integration', {
            'fields': (
                'sap_order_id',
                'is_synced_to_sap',
                'sap_sync_date',
            )
        }),
        ('Timestamps', {
            'fields': (
                'created_at',
                'updated_at',
                'completed_at',
            )
        }),
    )
    
    def get_total_items(self, obj):
        return obj.get_total_items()
    get_total_items.short_description = 'Total Items'
    
    def get_total_quantity(self, obj):
        return obj.get_total_quantity()
    get_total_quantity.short_description = 'Total Quantity'


@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    list_display = [
        'id',
        'order',
        'product_item_code',
        'product_name',
        'quantity',
        'unit_price',
        'subtotal',
        'created_at'
    ]
    search_fields = [
        'order__order_number',
        'product_item_code',
        'product_name'
    ]
    readonly_fields = ['subtotal', 'created_at']
    list_filter = ['created_at']


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = [
        'transaction_id',
        'order',
        'user',
        'payment_method',
        'amount',
        'status',
        'jazzcash_response_code',
        'created_at',
        'completed_at',
    ]
    list_filter = ['payment_method', 'status', 'created_at', 'completed_at']
    search_fields = [
        'transaction_id',
        'jazzcash_transaction_id',
        'order__order_number',
        'user__email',
        'customer_phone',
        'customer_email',
    ]
    readonly_fields = [
        'transaction_id',
        'created_at',
        'updated_at',
        'completed_at',
        'raw_response',
    ]
    
    fieldsets = (
        ('Basic Information', {
            'fields': (
                'transaction_id',
                'order',
                'user',
                'payment_method',
                'amount',
                'status',
            )
        }),
        ('JazzCash Details', {
            'fields': (
                'jazzcash_transaction_id',
                'jazzcash_response_code',
                'jazzcash_response_message',
                'jazzcash_payment_token',
            ),
            'classes': ('collapse',),
        }),
        ('Customer Information', {
            'fields': (
                'customer_phone',
                'customer_email',
            )
        }),
        ('Additional Information', {
            'fields': (
                'notes',
                'raw_response',
            ),
            'classes': ('collapse',),
        }),
        ('Timestamps', {
            'fields': (
                'created_at',
                'updated_at',
                'completed_at',
            )
        }),
    )
    
    def has_delete_permission(self, request, obj=None):
        """Prevent deletion of completed payments"""
        if obj and obj.status == 'completed':
            return False
        return super().has_delete_permission(request, obj)
