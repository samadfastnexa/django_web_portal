from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from django.shortcuts import get_object_or_404, render
from django.db import transaction
from django.utils import timezone
from django.http import HttpResponse
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
import uuid
import logging

from .models import Cart, CartItem, Order, OrderItem, Payment
from .serializers import (
    CartSerializer,
    CartItemSerializer,
    AddToCartSerializer,
    UpdateCartItemSerializer,
    CheckoutSerializer,
    OrderSerializer,
    OrderListSerializer,
    CreateOrderSerializer,
    UpdateOrderStatusSerializer,
    UpdatePaymentSerializer,
    PaymentSerializer,
    PaymentListSerializer,
    InitiatePaymentSerializer,
    JazzCashPaymentResponseSerializer,
    VerifyPaymentSerializer,
)
from .permissions import (
    CanAddToCart,
    CanManageCart,
    CanViewOrderHistory,
    CanManageOrders,
    IsOrderOwner,
)
from .jazzcash_service import JazzCashService, get_jazzcash_response_message

logger = logging.getLogger(__name__)


class CartViewSet(viewsets.ViewSet):
    """
    ViewSet for managing shopping cart.
    
    Provides endpoints for:
    - Viewing cart
    - Listing cart items with pagination and filters
    - Adding items to cart
    - Updating item quantity
    - Removing items
    - Clearing cart
    """
    permission_classes = [IsAuthenticated]
    pagination_class = None  # Will be set dynamically for items endpoint
    
    def get_or_create_cart(self, user):
        """Get or create cart for user"""
        cart, created = Cart.objects.get_or_create(user=user)
        # Clean expired items
        cart.clear_expired_items()
        return cart
    
    def validate_user_access(self, request, user_id):
        """Validate user access - ensure user can only access their own cart unless superuser"""
        # Convert user_id to integer
        try:
            user_id = int(user_id)
        except (ValueError, TypeError):
            return None, Response(
                {'error': 'Invalid user_id format. Must be an integer.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Check if authenticated user matches the requested user_id or is superuser
        if not request.user.is_superuser and request.user.id != user_id:
            return None, Response(
                {'error': 'You do not have permission to access this user\'s cart.'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Get the user object
        from django.contrib.auth import get_user_model
        User = get_user_model()
        try:
            user = User.objects.get(id=user_id)
            return user, None
        except User.DoesNotExist:
            return None, Response(
                {'error': f'User with id {user_id} does not exist.'},
                status=status.HTTP_404_NOT_FOUND
            )
    
    @swagger_auto_schema(
        operation_id='get_user_cart',
        operation_description="Get user's cart with summary. Requires user_id parameter for identification.",
        manual_parameters=[
            openapi.Parameter(
                'user_id',
                openapi.IN_QUERY,
                description="User ID (required). Users can only access their own cart unless they are superusers.",
                type=openapi.TYPE_INTEGER,
                required=True
            ),
            openapi.Parameter(
                'include_expired',
                openapi.IN_QUERY,
                description="Include expired items (default: false)",
                type=openapi.TYPE_BOOLEAN,
                required=False
            ),
        ],
        responses={
            200: CartSerializer(),
            400: "Bad request - missing or invalid user_id",
            401: "Unauthorized - authentication required",
            403: "Forbidden - cannot access another user's cart",
            404: "Not found - user does not exist"
        },
        tags=["06. Shopping Cart"]
    )
    def list(self, request):
        """Get user's cart with user_id validation"""
        # Get user_id from query params
        user_id = request.query_params.get('user_id')
        
        # Validate user_id is provided
        if not user_id:
            return Response(
                {'error': 'user_id parameter is required.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Validate user access
        user, error_response = self.validate_user_access(request, user_id)
        if error_response:
            return error_response
        
        # Get or create cart for the validated user
        cart = self.get_or_create_cart(user)
        
        # Option to include expired items
        include_expired = request.query_params.get('include_expired', 'false').lower() == 'true'
        if not include_expired:
            cart.clear_expired_items()
        
        serializer = CartSerializer(cart)
        return Response(serializer.data)
    
    @swagger_auto_schema(
        operation_description="List cart items with pagination and filtering. Requires user_id parameter.",
        manual_parameters=[
            openapi.Parameter(
                'user_id',
                openapi.IN_QUERY,
                description="User ID (required)",
                type=openapi.TYPE_INTEGER,
                required=True
            ),
            openapi.Parameter(
                'is_active',
                openapi.IN_QUERY,
                description="Filter by active status (true/false, default: true)",
                type=openapi.TYPE_BOOLEAN,
                required=False
            ),
            openapi.Parameter(
                'product_item_code',
                openapi.IN_QUERY,
                description="Filter by product item code",
                type=openapi.TYPE_STRING,
                required=False
            ),
            openapi.Parameter(
                'search',
                openapi.IN_QUERY,
                description="Search in product name or item code",
                type=openapi.TYPE_STRING,
                required=False
            ),
            openapi.Parameter(
                'ordering',
                openapi.IN_QUERY,
                description="Order by field (created_date, -created_date, product_name, -product_name, unit_price, -unit_price)",
                type=openapi.TYPE_STRING,
                required=False
            ),
            openapi.Parameter(
                'page',
                openapi.IN_QUERY,
                description="Page number (default: 1)",
                type=openapi.TYPE_INTEGER,
                required=False
            ),
            openapi.Parameter(
                'page_size',
                openapi.IN_QUERY,
                description="Items per page (default: 10, max: 100)",
                type=openapi.TYPE_INTEGER,
                required=False
            ),
        ],
        responses={
            200: openapi.Response(
                'Paginated cart items',
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'count': openapi.Schema(type=openapi.TYPE_INTEGER),
                        'next': openapi.Schema(type=openapi.TYPE_STRING, format='uri', nullable=True),
                        'previous': openapi.Schema(type=openapi.TYPE_STRING, format='uri', nullable=True),
                        'results': openapi.Schema(type=openapi.TYPE_ARRAY, items=openapi.Schema(type=openapi.TYPE_OBJECT)),
                    }
                )
            ),
            400: "Bad request - missing or invalid user_id",
            403: "Forbidden - cannot access another user's cart",
            404: "Not found - user does not exist"
        },
        tags=["06. Shopping Cart"]
    )
    @action(detail=False, methods=['get'])
    def items(self, request):
        """List cart items with pagination and filters"""
        # Get user_id from query params
        user_id = request.query_params.get('user_id')
        
        # Validate user_id is provided
        if not user_id:
            return Response(
                {'error': 'user_id parameter is required.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Validate user access
        user, error_response = self.validate_user_access(request, user_id)
        if error_response:
            return error_response
        
        # Get cart
        cart = self.get_or_create_cart(user)
        
        # Start with cart items queryset
        queryset = cart.items.all()
        
        # Filter by active status (default: true)
        is_active = request.query_params.get('is_active', 'true').lower()
        if is_active == 'true':
            queryset = queryset.filter(is_active=True)
        elif is_active == 'false':
            queryset = queryset.filter(is_active=False)
        
        # Filter by product item code
        product_item_code = request.query_params.get('product_item_code')
        if product_item_code:
            queryset = queryset.filter(product_item_code__icontains=product_item_code)
        
        # Search in product name or item code
        search = request.query_params.get('search')
        if search:
            from django.db.models import Q
            queryset = queryset.filter(
                Q(product_name__icontains=search) | 
                Q(product_item_code__icontains=search)
            )
        
        # Ordering
        ordering = request.query_params.get('ordering', '-created_date')
        allowed_ordering = ['created_date', '-created_date', 'product_name', '-product_name', 'unit_price', '-unit_price', 'quantity', '-quantity']
        if ordering in allowed_ordering:
            queryset = queryset.order_by(ordering)
        else:
            queryset = queryset.order_by('-created_date')
        
        # Pagination
        from rest_framework.pagination import PageNumberPagination
        paginator = PageNumberPagination()
        
        # Custom page size
        page_size = request.query_params.get('page_size')
        if page_size:
            try:
                page_size = int(page_size)
                if page_size > 100:
                    page_size = 100
                paginator.page_size = page_size
            except ValueError:
                pass
        
        page = paginator.paginate_queryset(queryset, request)
        if page is not None:
            serializer = CartItemSerializer(page, many=True, context={'database': request.query_params.get('database', '4B-BIO')})
            return paginator.get_paginated_response(serializer.data)
        
        serializer = CartItemSerializer(queryset, many=True, context={'database': request.query_params.get('database', '4B-BIO')})
        return Response(serializer.data)
    
    @swagger_auto_schema(
        operation_description="Add product to cart (requires add_to_cart permission)",
        request_body=AddToCartSerializer,
        responses={
            201: CartItemSerializer(),
            400: "Bad request",
            403: "Permission denied"
        },
        tags=["06. Shopping Cart"]
    )
    @action(detail=False, methods=['post'], permission_classes=[IsAuthenticated, CanAddToCart])
    def add_item(self, request):
        """Add item to cart"""
        serializer = AddToCartSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        cart_id = serializer.validated_data['cart_id']
        user_id = serializer.validated_data['user_id']
        
        # Validate cart existence and ownership
        cart = get_object_or_404(Cart, id=cart_id, user_id=user_id)
        
        # Security check: Ensure the authenticated user owns the cart or has permission
        if not request.user.is_superuser and cart.user != request.user:
            return Response({'error': 'You do not have permission to access this cart'}, status=status.HTTP_403_FORBIDDEN)

        # Clean expired items
        cart.clear_expired_items()
        
        # Check if item already exists in cart
        existing_item = CartItem.objects.filter(
            cart=cart,
            product_item_code=serializer.validated_data['product_item_code'],
            is_active=True
        ).first()
        
        database = serializer.validated_data.get('database', '4B-BIO')
        
        if existing_item:
            # Update quantity if item exists
            existing_item.quantity += serializer.validated_data.get('quantity', 1)
            existing_item.save()
            item_serializer = CartItemSerializer(existing_item, context={'database': database})
            return Response(
                {
                    'message': 'Item quantity updated in cart',
                    'cart_id': cart.id,
                    'user_id': cart.user.id,
                    'item': item_serializer.data,
                    'updated_date': timezone.now().isoformat(),
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
            item_serializer = CartItemSerializer(cart_item, context={'database': database})
            return Response(
                {
                    'message': 'Item added to cart',
                    'cart_id': cart.id,
                    'user_id': cart.user.id,
                    'item': item_serializer.data,
                    'created_date': timezone.now().isoformat(),
                },
                status=status.HTTP_201_CREATED
            )
    
    @swagger_auto_schema(
        operation_description="Update cart item quantity",
        manual_parameters=[
            openapi.Parameter(
                'user_id',
                openapi.IN_QUERY,
                description="User ID (required)",
                type=openapi.TYPE_INTEGER,
                required=True
            ),
        ],
        request_body=UpdateCartItemSerializer,
        responses={
            200: CartItemSerializer(),
            400: "Bad request - missing or invalid user_id",
            403: "Forbidden - cannot access another user's cart",
            404: "Not found - item or user does not exist"
        },
        tags=["06. Shopping Cart"]
    )
    @action(detail=False, methods=['patch'], url_path='update-item/(?P<item_id>[^/.]+)')
    def update_item(self, request, item_id=None):
        """Update cart item quantity with user_id validation"""
        # Get user_id from query params
        user_id = request.query_params.get('user_id')
        
        # Validate user_id is provided
        if not user_id:
            return Response(
                {'error': 'user_id parameter is required.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Validate user access
        user, error_response = self.validate_user_access(request, user_id)
        if error_response:
            return error_response
        
        cart = self.get_or_create_cart(user)
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
            'cart_id': cart.id,
            'user_id': user.id,
            'item': item_serializer.data,
            'updated_date': timezone.now().isoformat(),
        })
    
    @swagger_auto_schema(
        operation_description="Remove item from cart",
        manual_parameters=[
            openapi.Parameter(
                'user_id',
                openapi.IN_QUERY,
                description="User ID (required)",
                type=openapi.TYPE_INTEGER,
                required=True
            ),
        ],
        responses={
            200: "Item removed successfully",
            400: "Bad request - missing or invalid user_id",
            403: "Forbidden - cannot access another user's cart",
            404: "Not found - item or user does not exist"
        },
        tags=["06. Shopping Cart"]
    )
    @action(detail=False, methods=['delete'], url_path='remove-item/(?P<item_id>[^/.]+)')
    def remove_item(self, request, item_id=None):
        """Remove item from cart with user_id validation"""
        # Get user_id from query params
        user_id = request.query_params.get('user_id')
        
        # Validate user_id is provided
        if not user_id:
            return Response(
                {'error': 'user_id parameter is required.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Validate user access
        user, error_response = self.validate_user_access(request, user_id)
        if error_response:
            return error_response
        
        cart = self.get_or_create_cart(user)
        cart_item = get_object_or_404(CartItem, id=item_id, cart=cart, is_active=True)
        
        cart_item.is_active = False
        cart_item.save()
        
        return Response({
            'message': 'Item removed from cart',
            'cart_id': cart.id,
            'user_id': user.id,
            'removed_date': timezone.now().isoformat(),
        }, status=status.HTTP_200_OK)
    
    @swagger_auto_schema(
        operation_description="Clear all items from cart",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=['user_id', 'cart_id'],
            properties={
                'user_id': openapi.Schema(type=openapi.TYPE_INTEGER, description='User ID'),
                'cart_id': openapi.Schema(type=openapi.TYPE_INTEGER, description='Cart ID'),
            }
        ),
        responses={
            200: openapi.Response(
                'Cart cleared successfully',
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'message': openapi.Schema(type=openapi.TYPE_STRING),
                        'cart_id': openapi.Schema(type=openapi.TYPE_INTEGER),
                        'user_id': openapi.Schema(type=openapi.TYPE_INTEGER),
                        'cleared_items_count': openapi.Schema(type=openapi.TYPE_INTEGER),
                        'cleared_date': openapi.Schema(type=openapi.TYPE_STRING, format='date-time'),
                    }
                )
            ),
            400: "Bad request - missing cart_id or user_id",
            403: "Forbidden - cannot access another user's cart",
            404: "Not found - cart or user does not exist"
        },
        tags=["06. Shopping Cart"]
    )
    @action(detail=False, methods=['post'])
    def clear(self, request):
        """Clear all items from cart with validation"""
        cart_id = request.data.get('cart_id')
        user_id = request.data.get('user_id')
        
        if not cart_id:
            return Response({'error': 'cart_id is required'}, status=status.HTTP_400_BAD_REQUEST)
        if not user_id:
            return Response({'error': 'user_id is required'}, status=status.HTTP_400_BAD_REQUEST)
        
        # Validate user access
        user, error_response = self.validate_user_access(request, user_id)
        if error_response:
            return error_response
            
        cart = get_object_or_404(Cart, id=cart_id, user_id=user_id)
            
        # Soft delete items (set is_active to False)
        cleared_items_count = cart.items.filter(is_active=True).count()
        cart.items.filter(is_active=True).update(is_active=False)
        
        return Response({
            'message': 'Cart cleared successfully',
            'cart_id': cart.id,
            'user_id': cart.user.id,
            'cleared_items_count': cleared_items_count,
            'cleared_date': timezone.now().isoformat(),
        }, status=status.HTTP_200_OK)
    
    @swagger_auto_schema(
        operation_description="Get count of items in cart",
        manual_parameters=[
            openapi.Parameter(
                'user_id',
                openapi.IN_QUERY,
                description="User ID (required)",
                type=openapi.TYPE_INTEGER,
                required=True
            ),
        ],
        responses={
            200: openapi.Response(
                'Cart item count',
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'cart_id': openapi.Schema(type=openapi.TYPE_INTEGER),
                        'user_id': openapi.Schema(type=openapi.TYPE_INTEGER),
                        'total_items': openapi.Schema(type=openapi.TYPE_INTEGER),
                        'total_quantity': openapi.Schema(type=openapi.TYPE_INTEGER),
                    }
                )
            ),
            400: "Bad request - missing or invalid user_id",
            403: "Forbidden - cannot access another user's cart",
            404: "Not found - user does not exist"
        },
        tags=["06. Shopping Cart"]
    )
    @action(detail=False, methods=['get'])
    def count(self, request):
        """Get cart item count with user_id validation"""
        # Get user_id from query params
        user_id = request.query_params.get('user_id')
        
        # Validate user_id is provided
        if not user_id:
            return Response(
                {'error': 'user_id parameter is required.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Validate user access
        user, error_response = self.validate_user_access(request, user_id)
        if error_response:
            return error_response
        
        cart = self.get_or_create_cart(user)
        return Response({
            'cart_id': cart.id,
            'user_id': user.id,
            'total_items': cart.get_total_items(),
            'total_quantity': cart.get_total_quantity(),
        })
    
    @swagger_auto_schema(
        operation_description="Checkout - Convert cart to order with normalized cart and consumer details",
        request_body=CheckoutSerializer,
        responses={
            201: openapi.Response(
                'Order created successfully',
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'message': openapi.Schema(type=openapi.TYPE_STRING),
                        'order': openapi.Schema(type=openapi.TYPE_OBJECT),
                        'cart_details': openapi.Schema(type=openapi.TYPE_OBJECT),
                        'consumer_details': openapi.Schema(type=openapi.TYPE_OBJECT),
                    }
                )
            ),
            400: "Bad request (empty cart or validation error)"
        },
        tags=["06. Shopping Cart"]
    )
    @transaction.atomic
    @action(detail=False, methods=['post'], permission_classes=[IsAuthenticated, CanAddToCart])
    def checkout(self, request):
        """
        Checkout - Create order from cart with normalized data.
        Returns order with cart details and consumer details.
        Order status will be 'pending' by default.
        """
        serializer = CheckoutSerializer(data=request.data)
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
        
        # Normalize cart details
        cart_details = {
            'cart_id': cart.id,
            'total_items': cart.get_total_items(),
            'total_quantity': cart.get_total_quantity(),
            'items': []
        }
        
        # Normalize consumer details
        consumer_details = {
            'user_id': request.user.id,
            'first_name': serializer.validated_data.get('customer_first_name', ''),
            'last_name': serializer.validated_data.get('customer_last_name', ''),
            'email': serializer.validated_data.get('customer_email', '') or request.user.email,
            'phone': serializer.validated_data.get('customer_phone', ''),
            'shipping_address': serializer.validated_data.get('shipping_address', ''),
            'shipping_area': serializer.validated_data.get('shipping_area', ''),
            'shipping_city': serializer.validated_data.get('shipping_city', ''),
            'shipping_postal_code': serializer.validated_data.get('shipping_postal_code', ''),
            'payment_method': serializer.validated_data.get('payment_method', ''),
            'payment_phone': serializer.validated_data.get('payment_phone', ''),
        }
        
        # Create order with pending status and all customer details
        order = Order.objects.create(
            user=request.user,
            order_number=order_number,
            status='pending',  # Default status as per requirements
            # Customer details
            customer_first_name=consumer_details['first_name'],
            customer_last_name=consumer_details['last_name'],
            customer_phone=consumer_details['phone'],
            customer_email=consumer_details['email'],
            # Shipping details
            shipping_address=consumer_details['shipping_address'],
            shipping_area=consumer_details['shipping_area'],
            shipping_city=consumer_details['shipping_city'],
            shipping_postal_code=consumer_details['shipping_postal_code'],
            # Payment details
            payment_method=consumer_details['payment_method'],
            payment_phone=consumer_details['payment_phone'],
            # Order notes
            notes=serializer.validated_data.get('notes', ''),
        )
        
        # Record initial status in history
        OrderStatusHistory.objects.create(
            order=order,
            new_status='pending',
            changed_by=request.user,
            notes="Order placed via checkout"
        )
        
        # Create order items from cart items and build cart details
        total_amount = 0
        database = serializer.validated_data.get('database', '4B-BIO')
        
        for cart_item in cart_items:
            subtotal = cart_item.get_subtotal()
            
            # Create order item
            OrderItem.objects.create(
                order=order,
                product_item_code=cart_item.product_item_code,
                product_name=cart_item.product_name,
                quantity=cart_item.quantity,
                unit_price=cart_item.unit_price or 0,
                subtotal=subtotal,
                notes=cart_item.notes,
            )
            
            # Add to cart details with product images
            cart_details['items'].append({
                'product_item_code': cart_item.product_item_code,
                'product_name': cart_item.product_name,
                'quantity': cart_item.quantity,
                'unit_price': str(cart_item.unit_price) if cart_item.unit_price else '0',
                'subtotal': str(subtotal),
                'product_image_url': f"/media/product_images/{database}/{cart_item.product_item_code}.jpg",
                'product_description_urdu_url': f"/media/product_images/{database}/{cart_item.product_item_code}-urdu.jpg",
            })
            
            total_amount += subtotal
        
        # Update order total
        order.total_amount = total_amount
        order.save()
        
        # Clear cart
        cart_items.update(is_active=False)
        
        # Prepare response with normalized data
        order_serializer = OrderSerializer(order)
        
        return Response(
            {
                'message': 'Order created successfully',
                'order': order_serializer.data,
                'cart_details': cart_details,
                'consumer_details': consumer_details,
            },
            status=status.HTTP_201_CREATED
        )


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
        # Short-circuit during Swagger schema generation
        if getattr(self, 'swagger_fake_view', False):
            return Order.objects.none()
        
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
        manual_parameters=[
            openapi.Parameter('status', openapi.IN_QUERY, description="Filter by order status (pending, confirmed, processing, shipped, delivered, cancelled)", type=openapi.TYPE_STRING),
            openapi.Parameter('payment_status', openapi.IN_QUERY, description="Filter by payment status (pending, partial, paid, refunded, failed)", type=openapi.TYPE_STRING),
            openapi.Parameter('from_date', openapi.IN_QUERY, description="Filter orders from date (YYYY-MM-DD)", type=openapi.TYPE_STRING, format=openapi.FORMAT_DATE),
            openapi.Parameter('to_date', openapi.IN_QUERY, description="Filter orders to date (YYYY-MM-DD)", type=openapi.TYPE_STRING, format=openapi.FORMAT_DATE),
            openapi.Parameter('search', openapi.IN_QUERY, description="Search by order number", type=openapi.TYPE_STRING),
            openapi.Parameter('payment_method', openapi.IN_QUERY, description="Filter by payment method (cod, jazzcash, easypaisa, credit_card)", type=openapi.TYPE_STRING),
            openapi.Parameter('city', openapi.IN_QUERY, description="Filter by shipping city", type=openapi.TYPE_STRING),
        ],
        responses={200: OrderListSerializer(many=True)},
        tags=["08. Orders"]
    )
    def list(self, request, *args, **kwargs):
        """List user's orders with optional filters"""
        queryset = self.get_queryset()
        
        # Filter by status
        status_filter = request.query_params.get('status')
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        
        # Filter by payment status
        payment_status_filter = request.query_params.get('payment_status')
        if payment_status_filter:
            queryset = queryset.filter(payment_status=payment_status_filter)
        
        # Filter by date range
        from_date = request.query_params.get('from_date')
        if from_date:
            queryset = queryset.filter(created_date__gte=from_date)
        
        to_date = request.query_params.get('to_date')
        if to_date:
            queryset = queryset.filter(created_date__lte=to_date)
        
        # Search by order number
        search = request.query_params.get('search')
        if search:
            queryset = queryset.filter(order_number__icontains=search)
        
        # Filter by payment method
        payment_method = request.query_params.get('payment_method')
        if payment_method:
            queryset = queryset.filter(payment_method=payment_method)
        
        # Filter by city
        city = request.query_params.get('city')
        if city:
            queryset = queryset.filter(shipping_city__icontains=city)
        
        # Paginate and serialize
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)
    
    @swagger_auto_schema(
        operation_description="Get order details",
        responses={200: OrderSerializer()},
        tags=["08. Orders"]
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
        },
        tags=["08. Orders"]
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
        
        # Create order with all customer, shipping, and payment details
        order = Order.objects.create(
            user=request.user,
            order_number=order_number,
            # Customer details
            customer_first_name=serializer.validated_data.get('customer_first_name', ''),
            customer_last_name=serializer.validated_data.get('customer_last_name', ''),
            customer_phone=serializer.validated_data.get('customer_phone', ''),
            customer_email=serializer.validated_data.get('customer_email', ''),
            # Shipping details
            shipping_address=serializer.validated_data.get('shipping_address', ''),
            shipping_area=serializer.validated_data.get('shipping_area', ''),
            shipping_city=serializer.validated_data.get('shipping_city', ''),
            shipping_postal_code=serializer.validated_data.get('shipping_postal_code', ''),
            # Payment details
            payment_method=serializer.validated_data.get('payment_method'),
            payment_phone=serializer.validated_data.get('payment_phone', ''),
            # Order notes
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
        responses={200: OrderSerializer()},
        tags=["08. Orders"]
    )
    @action(detail=True, methods=['patch'], permission_classes=[IsAuthenticated, CanManageOrders])
    def update_status(self, request, pk=None):
        """Update order status with validation and audit trail"""
        order = self.get_object()
        serializer = UpdateOrderStatusSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        old_status = order.status
        new_status = serializer.validated_data['status']
        
        if old_status == new_status:
            return Response({'message': 'Order is already in this status'}, status=status.HTTP_200_OK)
            
        # Transition validation logic
        # Example: delivered cannot go back to pending
        if old_status == 'delivered' and new_status in ['pending', 'inprogress']:
            return Response({'error': 'Cannot change status of a delivered order'}, status=status.HTTP_400_BAD_REQUEST)
            
        order.status = new_status
        
        # Mark as completed if status is delivered
        if order.status == 'delivered' and not order.completed_at:
            order.completed_at = timezone.now()
        
        order.save()
        
        # Record in status history (Audit Trail)
        OrderStatusHistory.objects.create(
            order=order,
            old_status=old_status,
            new_status=new_status,
            changed_by=request.user,
            notes=request.data.get('notes', f"Status changed from {old_status} to {new_status}")
        )
        
        order_serializer = OrderSerializer(order)
        return Response({
            'message': 'Order status updated successfully',
            'order': order_serializer.data
        })
    
    @swagger_auto_schema(
        operation_description="Update payment information (requires manage_orders permission)",
        request_body=UpdatePaymentSerializer,
        responses={200: OrderSerializer()},
        tags=["08. Orders"]
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
        )},
        tags=["08. Orders"]
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


# =============== Payment Views ===============

class PaymentViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing payments.
    
    Provides endpoints for:
    - Viewing payment history
    - Initiating payments (JazzCash, etc.)
    - Verifying payment status
    """
    serializer_class = PaymentSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        """Get payments based on user permissions"""
        # Handle schema generation
        if getattr(self, 'swagger_fake_view', False):
            return Payment.objects.none()
        
        user = self.request.user
        
        # Handle anonymous users
        if not user.is_authenticated:
            return Payment.objects.none()
        
        # Superusers and users with process_payments permission see all payments
        if user.is_superuser or user.has_perm('cart.process_payments'):
            return Payment.objects.all().select_related('order', 'user')
        
        # Regular users see only their own payments
        return Payment.objects.filter(user=user).select_related('order', 'user')
    
    def get_serializer_class(self):
        """Return appropriate serializer based on action"""
        if self.action == 'list':
            return PaymentListSerializer
        return PaymentSerializer
    
    @swagger_auto_schema(
        operation_description="Get payment history",
        manual_parameters=[
            openapi.Parameter('status', openapi.IN_QUERY, description="Filter by payment status (pending, processing, completed, failed, cancelled, refunded)", type=openapi.TYPE_STRING),
            openapi.Parameter('payment_method', openapi.IN_QUERY, description="Filter by payment method (jazzcash, bank_transfer, cash)", type=openapi.TYPE_STRING),
            openapi.Parameter('from_date', openapi.IN_QUERY, description="Filter payments from date (YYYY-MM-DD)", type=openapi.TYPE_STRING, format=openapi.FORMAT_DATE),
            openapi.Parameter('to_date', openapi.IN_QUERY, description="Filter payments to date (YYYY-MM-DD)", type=openapi.TYPE_STRING, format=openapi.FORMAT_DATE),
            openapi.Parameter('order_id', openapi.IN_QUERY, description="Filter by order ID", type=openapi.TYPE_INTEGER),
        ],
        responses={200: PaymentListSerializer(many=True)},
        tags=["07. Payments"]
    )
    def list(self, request, *args, **kwargs):
        """List user's payments with optional filters"""
        queryset = self.get_queryset()
        
        # Filter by status
        status_filter = request.query_params.get('status')
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        
        # Filter by payment method
        payment_method = request.query_params.get('payment_method')
        if payment_method:
            queryset = queryset.filter(payment_method=payment_method)
        
        # Filter by order
        order_id = request.query_params.get('order_id')
        if order_id:
            queryset = queryset.filter(order_id=order_id)
        
        # Filter by date range
        from_date = request.query_params.get('from_date')
        if from_date:
            queryset = queryset.filter(created_date__gte=from_date)
        
        to_date = request.query_params.get('to_date')
        if to_date:
            queryset = queryset.filter(created_date__lte=to_date)
        
        # Paginate and serialize
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)
    
    @swagger_auto_schema(
        operation_description="Get payment details",
        responses={200: PaymentSerializer()},
        tags=["07. Payments"]
    )
    def retrieve(self, request, *args, **kwargs):
        """Get payment details"""
        return super().retrieve(request, *args, **kwargs)
    
    @swagger_auto_schema(
        operation_description="Initiate a payment for an order",
        request_body=InitiatePaymentSerializer,
        responses={
            200: openapi.Response(
                description="Payment initiated successfully",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'payment_method': openapi.Schema(type=openapi.TYPE_STRING),
                        'transaction_id': openapi.Schema(type=openapi.TYPE_STRING),
                        'payment_url': openapi.Schema(type=openapi.TYPE_STRING),
                        'payment_data': openapi.Schema(type=openapi.TYPE_OBJECT),
                    }
                )
            ),
            400: "Bad request",
        },
        tags=["07. Payments"]
    )
    @action(detail=False, methods=['post'])
    @transaction.atomic
    def initiate(self, request):
        """Initiate a payment"""
        serializer = InitiatePaymentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        # Get order
        order = get_object_or_404(
            Order,
            id=serializer.validated_data['order_id'],
            user=request.user
        )
        
        # Check if order is already paid
        if order.payment_status == 'paid':
            return Response(
                {'error': 'Order is already paid'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Generate transaction ID
        transaction_id = f"TXN-{uuid.uuid4().hex[:12].upper()}"
        
        # Create payment record
        payment = Payment.objects.create(
            order=order,
            user=request.user,
            transaction_id=transaction_id,
            payment_method=serializer.validated_data['payment_method'],
            amount=serializer.validated_data['amount'],
            customer_phone=serializer.validated_data.get('customer_phone', ''),
            customer_email=serializer.validated_data.get('customer_email', ''),
            status='pending',
        )
        
        # Handle different payment methods
        payment_method = serializer.validated_data['payment_method']
        
        if payment_method == 'jazzcash':
            # Initialize JazzCash service
            jazzcash = JazzCashService()
            
            # Create payment request
            payment_request = jazzcash.create_payment_request(
                order=order,
                amount=payment.amount,
                customer_mobile=payment.customer_phone,
                customer_email=payment.customer_email,
            )
            
            # Store JazzCash transaction reference
            payment.jazzcash_payment_token = payment_request['transaction_ref']
            payment.save()
            
            return Response({
                'message': 'Payment initiated successfully',
                'payment_id': payment.id,
                'transaction_id': payment.transaction_id,
                'payment_method': payment_method,
                'jazzcash_payment_url': payment_request['api_url'],
                'jazzcash_form_data': payment_request['payment_data'],
                'amount': str(payment.amount),
            }, status=status.HTTP_200_OK)
        
        elif payment_method == 'cash_on_delivery':
            # Cash on delivery doesn't require payment gateway
            payment.status = 'completed'
            payment.completed_at = timezone.now()
            payment.save()
            
            # Update order
            order.payment_status = 'unpaid'  # Will be paid on delivery
            order.status = 'confirmed'
            order.save()
            
            return Response({
                'message': 'Order confirmed with Cash on Delivery',
                'payment_id': payment.id,
                'transaction_id': payment.transaction_id,
                'payment_method': payment_method,
            }, status=status.HTTP_200_OK)
        
        else:
            # Other payment methods (to be implemented)
            return Response({
                'message': 'Payment method coming soon',
                'payment_id': payment.id,
                'transaction_id': payment.transaction_id,
                'payment_method': payment_method,
            }, status=status.HTTP_200_OK)
    
    @swagger_auto_schema(
        operation_description="Verify payment status",
        request_body=VerifyPaymentSerializer,
        responses={
            200: PaymentSerializer(),
            404: "Payment not found",
        },
        tags=["07. Payments"]
    )
    @action(detail=False, methods=['post'])
    def verify(self, request):
        """Verify payment status"""
        serializer = VerifyPaymentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        # Get payment
        payment = get_object_or_404(
            Payment,
            transaction_id=serializer.validated_data['transaction_id'],
            user=request.user
        )
        
        # Check payment status via payment gateway if needed
        if payment.payment_method == 'jazzcash' and payment.status == 'pending':
            jazzcash = JazzCashService()
            status_result = jazzcash.get_transaction_status(payment.jazzcash_payment_token)
            
            if status_result.get('success'):
                # Update payment based on gateway response
                # (This would need proper implementation based on JazzCash API response)
                pass
        
        payment_serializer = PaymentSerializer(payment)
        return Response({
            'message': 'Payment status retrieved',
            'payment': payment_serializer.data,
        })


class JazzCashCallbackView(APIView):
    """
    Handle JazzCash payment callbacks.
    This endpoint receives POST data from JazzCash after payment.
    """
    permission_classes = []  # No authentication required for callbacks
    
    @swagger_auto_schema(
        operation_description="JazzCash payment callback endpoint (called by JazzCash gateway)",
        request_body=JazzCashPaymentResponseSerializer,
        responses={
            200: "Payment processed successfully",
            400: "Bad request or payment verification failed",
        },
        tags=["07. Payments"]
    )
    @transaction.atomic
    def post(self, request):
        """Process JazzCash payment callback"""
        logger.info(f"JazzCash callback received: {request.data}")
        
        try:
            # Initialize JazzCash service
            jazzcash = JazzCashService()
            
            # Verify payment response
            verification_result = jazzcash.verify_payment_response(request.data)
            
            # Find payment record
            transaction_ref = request.data.get('pp_TxnRefNo', '')
            bill_reference = request.data.get('pp_BillReference', '')
            
            try:
                payment = Payment.objects.select_related('order').get(
                    jazzcash_payment_token=transaction_ref
                )
            except Payment.DoesNotExist:
                logger.error(f"Payment not found for transaction: {transaction_ref}")
                return Response(
                    {'error': 'Payment record not found'},
                    status=status.HTTP_404_NOT_FOUND
                )
            
            # Update payment with JazzCash response
            payment.jazzcash_transaction_id = verification_result.get('jazzcash_transaction_id', '')
            payment.jazzcash_response_code = verification_result.get('response_code', '')
            payment.jazzcash_response_message = verification_result.get('response_message', '')
            payment.raw_response = verification_result.get('raw_response', {})
            
            # Handle payment based on verification result
            if verification_result.get('success'):
                # Payment successful
                payment.mark_completed()
                payment.order.status = 'confirmed'
                payment.order.save()
                
                logger.info(f"Payment {payment.transaction_id} completed successfully")
                
                return Response({
                    'success': True,
                    'message': 'Payment completed successfully',
                    'transaction_id': payment.transaction_id,
                })
            else:
                # Payment failed
                error_msg = verification_result.get('response_message', 'Payment verification failed')
                payment.mark_failed(error_msg)
                
                logger.warning(f"Payment {payment.transaction_id} failed: {error_msg}")
                
                return Response({
                    'success': False,
                    'message': error_msg,
                    'transaction_id': payment.transaction_id,
                }, status=status.HTTP_400_BAD_REQUEST)
        
        except Exception as e:
            logger.error(f"Error processing JazzCash callback: {str(e)}", exc_info=True)
            return Response(
                {'error': 'Error processing payment callback'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class JazzCashReturnView(APIView):
    """
    Handle JazzCash payment return (user redirect after payment).
    Shows payment result page to user.
    """
    permission_classes = []  # No authentication required for return URL
    
    def get(self, request):
        """Handle payment return"""
        transaction_ref = request.GET.get('pp_TxnRefNo', '')
        response_code = request.GET.get('pp_ResponseCode', '')
        response_message = request.GET.get('pp_ResponseMessage', '')
        
        # Try to find payment
        payment = None
        try:
            payment = Payment.objects.select_related('order').get(
                jazzcash_payment_token=transaction_ref
            )
        except Payment.DoesNotExist:
            pass
        
        # Get user-friendly message
        message = get_jazzcash_response_message(response_code)
        
        context = {
            'success': response_code == '000',
            'response_code': response_code,
            'response_message': message,
            'transaction_ref': transaction_ref,
            'payment': payment,
        }
        
        # Render a simple HTML page showing payment result
        return render(request, 'cart/payment_result.html', context)
    
    def post(self, request):
        """Handle POST from JazzCash (same as GET)"""
        return self.get(request)
