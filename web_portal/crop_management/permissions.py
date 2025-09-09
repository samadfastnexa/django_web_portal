from rest_framework import permissions
from django.contrib.auth.models import Group


class IsRDTeamOrMISOrReadOnly(permissions.BasePermission):
    """
    Custom permission to allow:
    - R&D team: Full access (CRUD)
    - MIS team: Full access (CRUD)
    - Other authenticated users: Read-only access
    - Anonymous users: No access
    """
    
    def has_permission(self, request, view):
        # Deny access to anonymous users
        if not request.user or not request.user.is_authenticated:
            return False
        
        # Allow read permissions for any authenticated user
        if request.method in permissions.SAFE_METHODS:
            return True
        
        # Write permissions only for R&D and MIS teams
        return self.is_rd_or_mis_user(request.user)
    
    def has_object_permission(self, request, view, obj):
        # Read permissions for any authenticated user
        if request.method in permissions.SAFE_METHODS:
            return True
        
        # Write permissions only for R&D and MIS teams
        return self.is_rd_or_mis_user(request.user)
    
    def is_rd_or_mis_user(self, user):
        """Check if user belongs to R&D or MIS team"""
        try:
            rd_group = Group.objects.get(name='R&D Team')
            mis_group = Group.objects.get(name='MIS Team')
            return user.groups.filter(id__in=[rd_group.id, mis_group.id]).exists()
        except Group.DoesNotExist:
            # If groups don't exist, check by user role or staff status
            return user.is_staff or user.is_superuser


class IsRDTeamOnly(permissions.BasePermission):
    """
    Permission class that only allows R&D team members to access.
    Used for sensitive research data and experimental practices.
    """
    
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        
        return self.is_rd_user(request.user)
    
    def has_object_permission(self, request, view, obj):
        return self.is_rd_user(request.user)
    
    def is_rd_user(self, user):
        """Check if user belongs to R&D team"""
        try:
            rd_group = Group.objects.get(name='R&D Team')
            return user.groups.filter(id=rd_group.id).exists()
        except Group.DoesNotExist:
            return user.is_superuser


class IsMISTeamOnly(permissions.BasePermission):
    """
    Permission class that only allows MIS team members to access.
    Used for analytics and reporting endpoints.
    """
    
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        
        return self.is_mis_user(request.user)
    
    def has_object_permission(self, request, view, obj):
        return self.is_mis_user(request.user)
    
    def is_mis_user(self, user):
        """Check if user belongs to MIS team"""
        try:
            mis_group = Group.objects.get(name='MIS Team')
            return user.groups.filter(id=mis_group.id).exists()
        except Group.DoesNotExist:
            return user.is_superuser


class IsOwnerOrRDOrMIS(permissions.BasePermission):
    """
    Permission class that allows:
    - Object owner: Full access
    - R&D team: Full access
    - MIS team: Full access
    - Others: Read-only access
    """
    
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        
        # Allow read permissions for any authenticated user
        if request.method in permissions.SAFE_METHODS:
            return True
        
        # Write permissions for authenticated users (object-level check will handle specifics)
        return True
    
    def has_object_permission(self, request, view, obj):
        # Read permissions for any authenticated user
        if request.method in permissions.SAFE_METHODS:
            return True
        
        # Check if user is the owner (if object has created_by field)
        if hasattr(obj, 'created_by') and obj.created_by == request.user:
            return True
        
        # Check if user is R&D or MIS team member
        return self.is_rd_or_mis_user(request.user)
    
    def is_rd_or_mis_user(self, user):
        """Check if user belongs to R&D or MIS team"""
        try:
            rd_group = Group.objects.get(name='R&D Team')
            mis_group = Group.objects.get(name='MIS Team')
            return user.groups.filter(id__in=[rd_group.id, mis_group.id]).exists()
        except Group.DoesNotExist:
            return user.is_staff or user.is_superuser


class CanViewAnalytics(permissions.BasePermission):
    """
    Permission for viewing analytics and reports.
    Allows MIS team, R&D team, and managers.
    """
    
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        
        # Only allow GET requests for analytics
        if request.method not in permissions.SAFE_METHODS:
            return False
        
        return self.can_view_analytics(request.user)
    
    def can_view_analytics(self, user):
        """Check if user can view analytics"""
        try:
            # Check for specific groups
            allowed_groups = ['R&D Team', 'MIS Team', 'Managers', 'Farm Managers']
            user_groups = user.groups.values_list('name', flat=True)
            
            if any(group in user_groups for group in allowed_groups):
                return True
            
            # Fallback to staff status
            return user.is_staff or user.is_superuser
        except Exception:
            return user.is_staff or user.is_superuser


class CanManageResearch(permissions.BasePermission):
    """
    Permission for managing research data.
    Only R&D team and research coordinators.
    """
    
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        
        # Read access for authenticated users
        if request.method in permissions.SAFE_METHODS:
            return True
        
        return self.can_manage_research(request.user)
    
    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return True
        
        return self.can_manage_research(request.user)
    
    def can_manage_research(self, user):
        """Check if user can manage research data"""
        try:
            research_groups = ['R&D Team', 'Research Coordinators']
            user_groups = user.groups.values_list('name', flat=True)
            
            if any(group in user_groups for group in research_groups):
                return True
            
            return user.is_superuser
        except Exception:
            return user.is_superuser


class CanManageFarmingPractices(permissions.BasePermission):
    """
    Permission for managing farming practices.
    Allows R&D team, agricultural experts, and farm managers.
    """
    
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        
        # Read access for authenticated users
        if request.method in permissions.SAFE_METHODS:
            return True
        
        return self.can_manage_practices(request.user)
    
    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return True
        
        return self.can_manage_practices(request.user)
    
    def can_manage_practices(self, user):
        """Check if user can manage farming practices"""
        try:
            practice_groups = ['R&D Team', 'Agricultural Experts', 'Farm Managers']
            user_groups = user.groups.values_list('name', flat=True)
            
            if any(group in user_groups for group in practice_groups):
                return True
            
            return user.is_staff or user.is_superuser
        except Exception:
            return user.is_staff or user.is_superuser