from rest_framework import permissions
from rest_framework.permissions import BasePermission


class CanAddToCart(BasePermission):
    """
    Permission for adding products to cart.
    Requires 'cart.add_to_cart' permission.
    """
    
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        
        # Check for add_to_cart permission
        return (
            request.user.is_superuser or 
            request.user.has_perm('cart.add_to_cart')
        )


class CanManageCart(BasePermission):
    """
    Permission for managing shopping cart.
    Requires 'cart.manage_cart' permission.
    """
    
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        
        # Read-only access for authenticated users
        if request.method in permissions.SAFE_METHODS:
            return True
        
        # Write access requires permission
        return (
            request.user.is_superuser or 
            request.user.has_perm('cart.manage_cart')
        )


class CanViewOrderHistory(BasePermission):
    """
    Permission for viewing order history.
    Requires 'cart.view_order_history' permission.
    """
    
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        
        return (
            request.user.is_superuser or 
            request.user.has_perm('cart.view_order_history')
        )
    
    def has_object_permission(self, request, view, obj):
        """Users can view their own orders"""
        return (
            request.user.is_superuser or 
            obj.user == request.user or
            request.user.has_perm('cart.manage_orders')
        )


class CanManageOrders(BasePermission):
    """
    Permission for managing orders (admin/staff).
    Requires 'cart.manage_orders' permission.
    """
    
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        
        # Read access for authenticated users with view permission
        if request.method in permissions.SAFE_METHODS:
            return (
                request.user.is_superuser or
                request.user.has_perm('cart.view_order_history')
            )
        
        # Write access requires manage permission
        return (
            request.user.is_superuser or 
            request.user.has_perm('cart.manage_orders')
        )


class IsOrderOwner(BasePermission):
    """
    Permission to ensure users can only access their own orders.
    """
    
    def has_object_permission(self, request, view, obj):
        """Check if user owns the order"""
        return obj.user == request.user or request.user.is_superuser
