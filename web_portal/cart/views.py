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
        responses={200: PaymentListSerializer(many=True)},
        tags=["07. Payments"]
    )
    def list(self, request, *args, **kwargs):
        """List user's payments"""
        return super().list(request, *args, **kwargs)
    
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
