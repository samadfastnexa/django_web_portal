from rest_framework import permissions
from rest_framework.permissions import BasePermission


# ==================== Hierarchy-Specific Permissions ====================

class CanViewHierarchy(BasePermission):
    """Permission to view reporting hierarchy (my-team, my-reporting-chain, my-hierarchy)."""
    
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        
        if request.user.is_superuser:
            return True
        
        # Sales staff can view their own hierarchy
        if hasattr(request.user, 'sales_profile'):
            return True
        
        # Check explicit permission
        return request.user.has_perm('accounts.view_hierarchy')


class CanManageHierarchy(BasePermission):
    """Permission to assign/change managers in reporting hierarchy."""
    
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        
        if request.user.is_superuser:
            return True
        
        # Only allow POST/PUT/PATCH/DELETE if user has permission
        if request.method not in permissions.SAFE_METHODS:
            return request.user.has_perm('accounts.manage_hierarchy')
        
        return True


class CanViewSubordinateData(BasePermission):
    """Permission to view subordinates' data (meetings, field days, etc.)."""
    
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        
        if request.user.is_superuser:
            return True
        
        # Sales staff with subordinates can view their data
        sales_profile = getattr(request.user, 'sales_profile', None)
        if sales_profile:
            return True
        
        # Check explicit permission
        return request.user.has_perm('accounts.view_subordinate_data')


class CanViewAllHierarchy(BasePermission):
    """Permission to view entire organization hierarchy (CEO/HR view)."""
    
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        
        if request.user.is_superuser:
            return True
        
        # Check explicit permission
        return request.user.has_perm('accounts.view_all_hierarchy')
