from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404
from django.db import transaction
from django.utils import timezone
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
import uuid

from .models import Cart, CartItem, Order, OrderItem
from .serializers import (
    CartSerializer,
    CartItemSerializer,
    AddToCartSerializer,
    UpdateCartItemSerializer,
    OrderSerializer,
    OrderListSerializer,
    CreateOrderSerializer,
    UpdateOrderStatusSerializer,
    UpdatePaymentSerializer,
)
from .permissions import (
    CanAddToCart,
    CanManageCart,
    CanViewOrderHistory,
    CanManageOrders,
    IsOrderOwner,
)


class CartViewSet(viewsets.ViewSet):
    """
    ViewSet for managing shopping cart.
    
    Provides endpoints for:
    - Viewing cart
    - Adding items to cart
    - Updating item quantity
    - Removing items
    - Clearing cart
    """
    permission_classes = [IsAuthenticated]
    
    def get_or_create_cart(self, user):
        """Get or create cart for user"""
        cart, created = Cart.objects.get_or_create(user=user)
        # Clean expired items
        cart.clear_expired_items()
        return cart
    
    @swagger_auto_schema(
        operation_description="Get current user's cart",
        responses={200: CartSerializer()}
    )
    def list(self, request):
        """Get user's cart"""
        cart = self.get_or_create_cart(request.user)
        serializer = CartSerializer(cart)
        return Response(serializer.data)
    
    @swagger_auto_schema(
        operation_description="Add product to cart (requires add_to_cart permission)",
        request_body=AddToCartSerializer,
        responses={
            201: CartItemSerializer(),
            400: "Bad request",
            403: "Permission denied"
        }
    )
    @action(detail=False, methods=['post'], permission_classes=[IsAuthenticated, CanAddToCart])
    def add_item(self, request):
        """Add item to cart"""
        serializer = AddToCartSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        cart = self.get_or_create_cart(request.user)
        
        # Check if item already exists in cart
        existing_item = CartItem.objects.filter(
            cart=cart,
            product_item_code=serializer.validated_data['product_item_code'],
            is_active=True
        ).first()
        
        if existing_item:
            # Update quantity if item exists
            existing_item.quantity += serializer.validated_data.get('quantity', 1)
            existing_item.save()
            item_serializer = CartItemSerializer(existing_item)
            return Response(
                {
                    'message': 'Item quantity updated in cart',
                    'item': item_serializer.data
                },
                status=status.HTTP_200_OK
            )
        else:
            # Create new cart item
            cart_item = CartItem.objects.create(
                cart=cart,
                product_item_code=serializer.validated_data['product_item_code'],
                product_name=serializer.validated_data['product_name'],
                quantity=serializer.validated_data.get('quantity', 1),
                unit_price=serializer.validated_data.get('unit_price'),
                notes=serializer.validated_data.get('notes', ''),
            )
            item_serializer = CartItemSerializer(cart_item)
            return Response(
                {
                    'message': 'Item added to cart',
                    'item': item_serializer.data
                },
                status=status.HTTP_201_CREATED
            )
    
    @swagger_auto_schema(
        operation_description="Update cart item quantity",
        request_body=UpdateCartItemSerializer,
        responses={200: CartItemSerializer()}
    )
    @action(detail=False, methods=['patch'], url_path='update-item/(?P<item_id>[^/.]+)')
    def update_item(self, request, item_id=None):
        """Update cart item quantity"""
        cart = self.get_or_create_cart(request.user)
        cart_item = get_object_or_404(CartItem, id=item_id, cart=cart, is_active=True)
        
        serializer = UpdateCartItemSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        cart_item.quantity = serializer.validated_data['quantity']
        if 'notes' in serializer.validated_data:
            cart_item.notes = serializer.validated_data['notes']
        cart_item.save()
        
        item_serializer = CartItemSerializer(cart_item)
        return Response({
            'message': 'Cart item updated',
            'item': item_serializer.data
        })
    
    @swagger_auto_schema(
        operation_description="Remove item from cart",
        responses={200: "Item removed successfully"}
    )
    @action(detail=False, methods=['delete'], url_path='remove-item/(?P<item_id>[^/.]+)')
    def remove_item(self, request, item_id=None):
        """Remove item from cart"""
        cart = self.get_or_create_cart(request.user)
        cart_item = get_object_or_404(CartItem, id=item_id, cart=cart, is_active=True)
        
        cart_item.is_active = False
        cart_item.save()
        
        return Response({
            'message': 'Item removed from cart'
        }, status=status.HTTP_200_OK)
    
    @swagger_auto_schema(
        operation_description="Clear all items from cart",
        responses={200: "Cart cleared successfully"}
    )
    @action(detail=False, methods=['post'])
    def clear(self, request):
        """Clear all items from cart"""
        cart = self.get_or_create_cart(request.user)
        cart.items.filter(is_active=True).update(is_active=False)
        
        return Response({
            'message': 'Cart cleared successfully'
        }, status=status.HTTP_200_OK)
    
    @swagger_auto_schema(
        operation_description="Get count of items in cart",
        responses={200: openapi.Response(
            'Cart item count',
            schema=openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    'total_items': openapi.Schema(type=openapi.TYPE_INTEGER),
                    'total_quantity': openapi.Schema(type=openapi.TYPE_INTEGER),
                }
            )
        )}
    )
    @action(detail=False, methods=['get'])
    def count(self, request):
        """Get cart item count"""
        cart = self.get_or_create_cart(request.user)
        return Response({
            'total_items': cart.get_total_items(),
            'total_quantity': cart.get_total_quantity(),
        })


class OrderViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing orders.
    
    Provides endpoints for:
    - Creating orders from cart
    - Viewing order history
    - Updating order status
    - Managing payments
    """
    serializer_class = OrderSerializer
    permission_classes = [IsAuthenticated, CanViewOrderHistory]
    
    def get_queryset(self):
        """Get orders based on user permissions"""
        user = self.request.user
        
        # Superusers and users with manage_orders permission see all orders
        if user.is_superuser or user.has_perm('cart.manage_orders'):
            return Order.objects.all().prefetch_related('items')
        
        # Regular users see only their own orders
        return Order.objects.filter(user=user).prefetch_related('items')
    
    def get_serializer_class(self):
        """Return appropriate serializer based on action"""
        if self.action == 'list':
            return OrderListSerializer
        return OrderSerializer
    
    @swagger_auto_schema(
        operation_description="Get user's order history",
        responses={200: OrderListSerializer(many=True)}
    )
    def list(self, request, *args, **kwargs):
        """List user's orders"""
        return super().list(request, *args, **kwargs)
    
    @swagger_auto_schema(
        operation_description="Get order details",
        responses={200: OrderSerializer()}
    )
    def retrieve(self, request, *args, **kwargs):
        """Get order details"""
        return super().retrieve(request, *args, **kwargs)
    
    @swagger_auto_schema(
        operation_description="Create order from cart",
        request_body=CreateOrderSerializer,
        responses={
            201: OrderSerializer(),
            400: "Bad request (empty cart or validation error)"
        }
    )
    @transaction.atomic
    def create(self, request, *args, **kwargs):
        """Create order from cart"""
        serializer = CreateOrderSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        # Get user's cart
        try:
            cart = Cart.objects.get(user=request.user)
        except Cart.DoesNotExist:
            return Response(
                {'error': 'Cart is empty'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Clean expired items
        cart.clear_expired_items()
        
        # Get active cart items
        cart_items = cart.items.filter(is_active=True)
        
        if not cart_items.exists():
            return Response(
                {'error': 'Cart is empty'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Generate unique order number
        order_number = f"ORD-{uuid.uuid4().hex[:8].upper()}-{timezone.now().strftime('%Y%m%d')}"
        
        # Create order
        order = Order.objects.create(
            user=request.user,
            order_number=order_number,
            shipping_address=serializer.validated_data.get('shipping_address', ''),
            notes=serializer.validated_data.get('notes', ''),
        )
        
        # Create order items from cart items
        total_amount = 0
        for cart_item in cart_items:
            subtotal = cart_item.get_subtotal()
            OrderItem.objects.create(
                order=order,
                product_item_code=cart_item.product_item_code,
                product_name=cart_item.product_name,
                quantity=cart_item.quantity,
                unit_price=cart_item.unit_price or 0,
                subtotal=subtotal,
                notes=cart_item.notes,
            )
            total_amount += subtotal
        
        # Update order total
        order.total_amount = total_amount
        order.save()
        
        # Clear cart
        cart_items.update(is_active=False)
        
        # Return created order
        order_serializer = OrderSerializer(order)
        return Response(
            {
                'message': 'Order created successfully',
                'order': order_serializer.data
            },
            status=status.HTTP_201_CREATED
        )
    
    @swagger_auto_schema(
        operation_description="Update order status (requires manage_orders permission)",
        request_body=UpdateOrderStatusSerializer,
        responses={200: OrderSerializer()}
    )
    @action(detail=True, methods=['patch'], permission_classes=[IsAuthenticated, CanManageOrders])
    def update_status(self, request, pk=None):
        """Update order status"""
        order = self.get_object()
        serializer = UpdateOrderStatusSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        order.status = serializer.validated_data['status']
        
        # Mark as completed if status is delivered
        if order.status == 'delivered' and not order.completed_at:
            order.completed_at = timezone.now()
        
        order.save()
        
        order_serializer = OrderSerializer(order)
        return Response({
            'message': 'Order status updated',
            'order': order_serializer.data
        })
    
    @swagger_auto_schema(
        operation_description="Update payment information (requires manage_orders permission)",
        request_body=UpdatePaymentSerializer,
        responses={200: OrderSerializer()}
    )
    @action(detail=True, methods=['patch'], permission_classes=[IsAuthenticated, CanManageOrders])
    def update_payment(self, request, pk=None):
        """Update payment information"""
        order = self.get_object()
        serializer = UpdatePaymentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        order.paid_amount = serializer.validated_data['paid_amount']
        
        # Update payment status based on amount paid
        if 'payment_status' in serializer.validated_data:
            order.payment_status = serializer.validated_data['payment_status']
        else:
            order.update_payment_status()
        
        order.save()
        
        order_serializer = OrderSerializer(order)
        return Response({
            'message': 'Payment information updated',
            'order': order_serializer.data
        })
    
    @swagger_auto_schema(
        operation_description="Get current user's order statistics",
        responses={200: openapi.Response(
            'Order statistics',
            schema=openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    'total_orders': openapi.Schema(type=openapi.TYPE_INTEGER),
                    'pending_orders': openapi.Schema(type=openapi.TYPE_INTEGER),
                    'completed_orders': openapi.Schema(type=openapi.TYPE_INTEGER),
                    'total_spent': openapi.Schema(type=openapi.TYPE_NUMBER),
                    'unpaid_amount': openapi.Schema(type=openapi.TYPE_NUMBER),
                }
            )
        )}
    )
    @action(detail=False, methods=['get'])
    def statistics(self, request):
        """Get user's order statistics"""
        user_orders = Order.objects.filter(user=request.user)
        
        stats = {
            'total_orders': user_orders.count(),
            'pending_orders': user_orders.filter(status__in=['pending', 'processing']).count(),
            'completed_orders': user_orders.filter(status='delivered').count(),
            'total_spent': sum(order.paid_amount for order in user_orders),
            'unpaid_amount': sum(
                order.total_amount - order.paid_amount 
                for order in user_orders 
                if order.total_amount > order.paid_amount
            ),
        }
        
        return Response(stats)
