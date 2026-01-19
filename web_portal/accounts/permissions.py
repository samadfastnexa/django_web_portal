from rest_framework import permissions
from rest_framework.permissions import BasePermission
from rest_framework.exceptions import PermissionDenied


# ✅ Allow object owner or admin to access
class IsOwnerOrAdmin(BasePermission):
    def has_object_permission(self, request, view, obj):
        return request.user and (
            obj == request.user or request.user.is_staff or request.user.is_superuser
        )

class HasRolePermission(BasePermission):
    """
    Custom permission class to enforce role-based access control.
    It maps HTTP methods to Django-style permission codenames
    (add_model, view_model, change_model, delete_model), and checks
    if the user's role has the corresponding permission.
    """

    def has_permission(self, request, view):
        user = request.user

        # ✅ Check if user is authenticated and has a role
        if not user.is_authenticated or not hasattr(user, 'role') or not user.role:
            return False

        # ✅ Map HTTP methods to standard permission actions
        method_action_map = {
            'GET': 'view',
            'POST': 'add',
            'PUT': 'change',
            'PATCH': 'change',
            'DELETE': 'delete'
        }

        action = method_action_map.get(request.method)
        if not action:
            return True  # Allow OPTIONS, HEAD, etc.

        # ✅ Dynamically get the model from the view
        model = getattr(getattr(view, 'queryset', None), 'model', None)

        # Fallback to dynamic queryset if `.queryset` is not set as a class attribute
        if not model and hasattr(view, 'get_queryset'):
            model = getattr(view.get_queryset(), 'model', None)

        if not model:
            raise PermissionDenied("Cannot determine the model to check permissions.")

        # ✅ Build the permission codename (e.g., 'add_user', 'view_order')
        model_name = model.__name__.lower()
        required_codename = f"{action}_{model_name}"

        # ✅ Check if the user's role has this permission
        if user.role.permissions.filter(codename=required_codename).exists():
            return True

        # ❌ Denied
        raise PermissionDenied(f"You do not have permission: '{required_codename}'")


class CanManageUsers(BasePermission):
    """Permission for managing users."""
    
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        
        if request.method in permissions.SAFE_METHODS:
            return True
        
        return (request.user.is_superuser or request.user.has_perm('accounts.manage_users'))


class CanManageRoles(BasePermission):
    """Permission for managing roles and permissions."""
    
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        
        if request.method in permissions.SAFE_METHODS:
            return True
        
        return (request.user.is_superuser or request.user.has_perm('accounts.manage_roles'))


class CanManageSalesStaff(BasePermission):
    """Permission for managing sales staff profiles."""
    
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        
        if request.method in permissions.SAFE_METHODS:
            return True
        
        return (request.user.is_superuser or request.user.has_perm('accounts.manage_sales_staff'))


class CanManageDealers(BasePermission):
    """Permission for managing dealers."""
    
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        
        if request.method in permissions.SAFE_METHODS:
            return True
        
        return (request.user.is_superuser or request.user.has_perm('FieldAdvisoryService.manage_dealers'))


class CanApproveDealerRequests(BasePermission):
    """Permission for approving dealer requests."""
    
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        
        if request.method in permissions.SAFE_METHODS:
            return True
        
        return (request.user.is_superuser or request.user.has_perm('FieldAdvisoryService.approve_dealer_requests'))


class CanManageFarmers(BasePermission):
    """Permission for managing farmer records."""
    
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        
        if request.method in permissions.SAFE_METHODS:
            return True
        
        return (request.user.is_superuser or request.user.has_perm('farmers.manage_farmers'))


class CanManageMeetings(BasePermission):
    """Permission for managing farmer meetings."""
    
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        
        if request.method in permissions.SAFE_METHODS:
            return True
        
        return (request.user.is_superuser or request.user.has_perm('farmerMeetingDataEntry.manage_meetings'))


class CanAccessSAPData(BasePermission):
    """Permission for accessing SAP integration data."""
    
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        
        # Basic SAP permissions
        sap_permissions = [
            'sap_integration.access_hana_connect',
            'sap_integration.view_policy_balance',
            'sap_integration.view_customer_list',
            'sap_integration.view_sales_orders',
        ]
        
        if request.user.is_superuser:
            return True
        
        return any(request.user.has_perm(perm) for perm in sap_permissions)


class CanViewSalesReports(BasePermission):
    """Permission for viewing sales achievement reports."""
    
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        
        if request.user.is_superuser:
            return True
        
        # Check for any sales report permission
        return (
            request.user.has_perm('sap_integration.view_sales_vs_achievement_geo') or
            request.user.has_perm('sap_integration.view_sales_vs_achievement_territory') or
            request.user.has_perm('sap_integration.view_sales_vs_achievement_profit')
        )


class CanViewMasterData(BasePermission):
    """Permission for viewing master data (LOV)."""
    
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        
        if request.user.is_superuser:
            return True
        
        # Check for any master data permission
        return (
            request.user.has_perm('sap_integration.view_customer_list') or
            request.user.has_perm('sap_integration.view_item_master') or
            request.user.has_perm('sap_integration.view_project_list') or
            request.user.has_perm('sap_integration.view_crop_master') or
            request.user.has_perm('sap_integration.view_tax_codes')
        )


class CanViewCustomerDetails(BasePermission):
    """Permission for viewing customer & contact details."""
    
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        
        if request.user.is_superuser:
            return True
        
        # Check for any customer detail permission
        return (
            request.user.has_perm('sap_integration.view_customer_address') or
            request.user.has_perm('sap_integration.view_contact_person') or
            request.user.has_perm('sap_integration.view_child_customers')
        )


class CanManageSalesOrders(BasePermission):
    """Permission for managing sales orders."""
    
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        
        if request.user.is_superuser:
            return True
        
        # Read access
        if request.method in permissions.SAFE_METHODS:
            return request.user.has_perm('sap_integration.view_sales_orders')
        
        # Write access
        if request.method == 'POST':
            return request.user.has_perm('sap_integration.create_sales_orders')
        
        # Edit/Delete access
        return request.user.has_perm('sap_integration.edit_sales_orders')


class CanPostToSAP(BasePermission):
    """Permission for posting data to SAP."""
    
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        
        return (request.user.is_superuser or request.user.has_perm('sap_integration.post_to_sap'))