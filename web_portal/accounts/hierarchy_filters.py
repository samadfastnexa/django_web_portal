"""
Hierarchy-based data filtering utilities for ViewSets and QuerySets.
"""
from django.db.models import Q
from rest_framework.exceptions import PermissionDenied


class HierarchyFilterMixin:
    """
    Mixin to filter querysets based on user's position in reporting hierarchy.
    
    Access Rules:
    - CEO / users with 'view_all_hierarchy' permission: See ALL data
    - Users with 'view_subordinate_data' permission: See own + subordinates' data
    - Regular sales staff: See ONLY their own data
    - Non-sales staff users: See only their own data
    
    Usage:
        class MyViewSet(HierarchyFilterMixin, viewsets.ModelViewSet):
            hierarchy_field = 'sales_staff'  # Field name that links to SalesStaffProfile
            ...
    """
    
    # Override this in your ViewSet to specify which field links to SalesStaffProfile
    # Examples: 'created_by', 'sales_staff', 'assigned_to', etc.
    hierarchy_field = None
    
    def get_hierarchy_filtered_queryset(self, queryset):
        """
        Apply hierarchy-based filtering to the queryset.
        
        Args:
            queryset: The base queryset to filter
            
        Returns:
            Filtered queryset based on user's hierarchy position
        """
        user = self.request.user
        
        # Superuser sees everything
        if user.is_superuser:
            return queryset
        
        # Non-authenticated users get empty queryset
        if not user.is_authenticated:
            return queryset.none()
        
        # Check if hierarchy_field is defined
        if not self.hierarchy_field:
            raise ValueError(
                f"{self.__class__.__name__} must define 'hierarchy_field' attribute "
                "to use HierarchyFilterMixin"
            )
        
        # Non-sales staff users see only their own data
        if not hasattr(user, 'sales_profile') or not user.sales_profile:
            # Filter by user directly (assuming there's a 'user' field)
            if hasattr(queryset.model, 'user'):
                return queryset.filter(user=user)
            return queryset.none()
        
        sales_profile = user.sales_profile
        
        # CEO or users with 'view_all_hierarchy' permission see everything
        if user.has_perm('accounts.view_all_hierarchy'):
            return queryset
        
        # Check designation level (CEO = 0)
        if sales_profile.designation and sales_profile.designation.code == 'CEO':
            return queryset
        
        # Users with 'view_subordinate_data' permission see own + subordinates
        if user.has_perm('accounts.view_subordinate_data'):
            # Get all subordinates including self
            subordinates = sales_profile.get_all_subordinates(include_self=True)
            subordinate_users = [s.user for s in subordinates if s.user]
            
            # Build Q filter for hierarchy field
            lookup = f"{self.hierarchy_field}__in"
            return queryset.filter(**{lookup: subordinate_users})
        
        # Default: Regular sales staff see only their own data
        lookup = self.hierarchy_field
        return queryset.filter(**{lookup: user})
    
    def filter_queryset(self, queryset):
        """
        Override filter_queryset to apply hierarchy filtering first,
        then apply other filters from parent classes.
        """
        # Apply hierarchy filtering first
        queryset = self.get_hierarchy_filtered_queryset(queryset)
        
        # Then apply other filters (search, ordering, etc.)
        return super().filter_queryset(queryset)


def get_accessible_staff_profiles(user):
    """
    Helper function to get all SalesStaffProfile objects accessible to a user.
    
    Returns:
        QuerySet of SalesStaffProfile objects the user can access
    """
    from accounts.models import SalesStaffProfile
    
    # Superuser sees all
    if user.is_superuser:
        return SalesStaffProfile.objects.all()
    
    # Non-authenticated or non-sales staff
    if not user.is_authenticated or not hasattr(user, 'sales_profile'):
        return SalesStaffProfile.objects.none()
    
    sales_profile = user.sales_profile
    
    # CEO or view_all_hierarchy permission
    if user.has_perm('accounts.view_all_hierarchy'):
        return SalesStaffProfile.objects.all()
    
    if sales_profile.designation and sales_profile.designation.code == 'CEO':
        return SalesStaffProfile.objects.all()
    
    # view_subordinate_data permission
    if user.has_perm('accounts.view_subordinate_data'):
        subordinates = sales_profile.get_all_subordinates(include_self=True)
        return SalesStaffProfile.objects.filter(id__in=[s.id for s in subordinates])
    
    # Default: only own profile
    return SalesStaffProfile.objects.filter(id=sales_profile.id)


def get_accessible_users(user):
    """
    Helper function to get all User objects accessible to a user.
    
    Returns:
        QuerySet of User objects the user can access
    """
    from accounts.models import User, SalesStaffProfile
    
    # Superuser sees all
    if user.is_superuser:
        return User.objects.all()
    
    # Non-authenticated
    if not user.is_authenticated:
        return User.objects.none()
    
    # Non-sales staff see only themselves
    if not hasattr(user, 'sales_profile') or not user.sales_profile:
        return User.objects.filter(id=user.id)
    
    sales_profile = user.sales_profile
    
    # CEO or view_all_hierarchy permission
    if user.has_perm('accounts.view_all_hierarchy'):
        return User.objects.all()
    
    if sales_profile.designation and sales_profile.designation.code == 'CEO':
        return User.objects.all()
    
    # view_subordinate_data permission
    if user.has_perm('accounts.view_subordinate_data'):
        subordinates = sales_profile.get_all_subordinates(include_self=True)
        subordinate_user_ids = [s.user.id for s in subordinates if s.user]
        return User.objects.filter(id__in=subordinate_user_ids)
    
    # Default: only self
    return User.objects.filter(id=user.id)
