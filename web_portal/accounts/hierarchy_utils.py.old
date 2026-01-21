"""
Hierarchy Utility Functions for managing user reporting structure
"""
from django.contrib.auth import get_user_model
from FieldAdvisoryService.models import UserHierarchy
from django.db.models import Q

User = get_user_model()


def get_user_subordinates(user, include_self=False):
    """
    Get all subordinates (direct and indirect) for a given user.
    
    Args:
        user: User object to get subordinates for
        include_self: Whether to include the user themselves in the result
        
    Returns:
        QuerySet of User objects representing all subordinates
    """
    if not user:
        return User.objects.none()
    
    try:
        # Get user's hierarchy assignment
        user_hierarchy = UserHierarchy.objects.get(user=user, is_active=True)
    except UserHierarchy.DoesNotExist:
        return User.objects.none()
    
    # Start with direct reports
    subordinate_ids = set()
    if include_self:
        subordinate_ids.add(user.id)
    
    # Get all direct reports recursively
    def get_all_reports(manager_user):
        direct_reports = UserHierarchy.objects.filter(
            reports_to=manager_user,
            company=user_hierarchy.company,
            is_active=True
        ).select_related('user')
        
        for report in direct_reports:
            if report.user.id not in subordinate_ids:
                subordinate_ids.add(report.user.id)
                # Recursively get their reports
                get_all_reports(report.user)
    
    get_all_reports(user)
    
    return User.objects.filter(id__in=subordinate_ids)


def get_user_managers(user, include_self=False):
    """
    Get all managers (direct and indirect) above a given user.
    
    Args:
        user: User object to get managers for
        include_self: Whether to include the user themselves in the result
        
    Returns:
        QuerySet of User objects representing all managers
    """
    if not user:
        return User.objects.none()
    
    try:
        user_hierarchy = UserHierarchy.objects.get(user=user, is_active=True)
    except UserHierarchy.DoesNotExist:
        return User.objects.none()
    
    manager_ids = set()
    if include_self:
        manager_ids.add(user.id)
    
    # Walk up the reporting chain
    current = user_hierarchy
    while current.reports_to:
        manager_ids.add(current.reports_to.id)
        try:
            current = UserHierarchy.objects.get(
                user=current.reports_to,
                company=user_hierarchy.company,
                is_active=True
            )
        except UserHierarchy.DoesNotExist:
            break
    
    return User.objects.filter(id__in=manager_ids)


def get_direct_reports(user):
    """
    Get only direct reports (immediate subordinates) for a given user.
    
    Args:
        user: User object to get direct reports for
        
    Returns:
        QuerySet of User objects representing direct reports
    """
    if not user:
        return User.objects.none()
    
    try:
        user_hierarchy = UserHierarchy.objects.get(user=user, is_active=True)
    except UserHierarchy.DoesNotExist:
        return User.objects.none()
    
    direct_report_hierarchies = UserHierarchy.objects.filter(
        reports_to=user,
        company=user_hierarchy.company,
        is_active=True
    ).select_related('user')
    
    direct_report_ids = [h.user.id for h in direct_report_hierarchies]
    return User.objects.filter(id__in=direct_report_ids)


def get_immediate_manager(user):
    """
    Get the immediate manager (direct supervisor) for a given user.
    
    Args:
        user: User object to get manager for
        
    Returns:
        User object representing the immediate manager, or None
    """
    if not user:
        return None
    
    try:
        user_hierarchy = UserHierarchy.objects.get(user=user, is_active=True)
        return user_hierarchy.reports_to
    except UserHierarchy.DoesNotExist:
        return None


def get_hierarchy_level_order(user):
    """
    Get the hierarchy level order for a user (0=highest, higher number=lower level).
    
    Args:
        user: User object to get hierarchy level for
        
    Returns:
        Integer representing the hierarchy level order, or None if not assigned
    """
    if not user:
        return None
    
    try:
        user_hierarchy = UserHierarchy.objects.get(user=user, is_active=True)
        return user_hierarchy.hierarchy_level.level_order
    except UserHierarchy.DoesNotExist:
        return None


def user_can_access_data(current_user, data_owner_user):
    """
    Check if current_user can access data belonging to data_owner_user
    based on hierarchy (managers can access subordinates' data).
    
    Args:
        current_user: User trying to access the data
        data_owner_user: User who owns the data
        
    Returns:
        Boolean indicating if access is allowed
    """
    # Superusers can access everything
    if current_user.is_superuser:
        return True
    
    # Users can access their own data
    if current_user.id == data_owner_user.id:
        return True
    
    # Check if data_owner is a subordinate of current_user
    subordinates = get_user_subordinates(current_user, include_self=False)
    return subordinates.filter(id=data_owner_user.id).exists()


def get_users_in_same_region(user):
    """
    Get all users in the same region as the given user.
    
    Args:
        user: User object to find region peers for
        
    Returns:
        QuerySet of User objects in the same region
    """
    if not user:
        return User.objects.none()
    
    try:
        user_hierarchy = UserHierarchy.objects.get(user=user, is_active=True)
        if not user_hierarchy.region:
            return User.objects.none()
        
        peer_hierarchies = UserHierarchy.objects.filter(
            region=user_hierarchy.region,
            company=user_hierarchy.company,
            is_active=True
        ).exclude(user=user).select_related('user')
        
        peer_ids = [h.user.id for h in peer_hierarchies]
        return User.objects.filter(id__in=peer_ids)
    except UserHierarchy.DoesNotExist:
        return User.objects.none()


def get_users_in_same_zone(user):
    """
    Get all users in the same zone as the given user.
    
    Args:
        user: User object to find zone peers for
        
    Returns:
        QuerySet of User objects in the same zone
    """
    if not user:
        return User.objects.none()
    
    try:
        user_hierarchy = UserHierarchy.objects.get(user=user, is_active=True)
        if not user_hierarchy.zone:
            return User.objects.none()
        
        peer_hierarchies = UserHierarchy.objects.filter(
            zone=user_hierarchy.zone,
            company=user_hierarchy.company,
            is_active=True
        ).exclude(user=user).select_related('user')
        
        peer_ids = [h.user.id for h in peer_hierarchies]
        return User.objects.filter(id__in=peer_ids)
    except UserHierarchy.DoesNotExist:
        return User.objects.none()


def get_hierarchy_tree(company, root_user=None):
    """
    Get the complete hierarchy tree for a company.
    
    Args:
        company: Company object
        root_user: Optional User object to start from (defaults to top of hierarchy)
        
    Returns:
        Dictionary representing the hierarchy tree
    """
    def build_tree(user):
        """Recursively build hierarchy tree"""
        try:
            hierarchy = UserHierarchy.objects.get(
                user=user,
                company=company,
                is_active=True
            )
        except UserHierarchy.DoesNotExist:
            return None
        
        # Get direct reports
        direct_reports = UserHierarchy.objects.filter(
            reports_to=user,
            company=company,
            is_active=True
        ).select_related('user', 'hierarchy_level').order_by('hierarchy_level__level_order', 'user__first_name')
        
        node = {
            'user_id': user.id,
            'username': user.username,
            'full_name': f"{user.first_name} {user.last_name}".strip() or user.username,
            'email': user.email,
            'hierarchy_level': hierarchy.hierarchy_level.level_name,
            'level_order': hierarchy.hierarchy_level.level_order,
            'region': hierarchy.region.name if hierarchy.region else None,
            'zone': hierarchy.zone.name if hierarchy.zone else None,
            'territory': hierarchy.territory.name if hierarchy.territory else None,
            'direct_reports': []
        }
        
        # Recursively add children
        for report_hierarchy in direct_reports:
            child_node = build_tree(report_hierarchy.user)
            if child_node:
                node['direct_reports'].append(child_node)
        
        return node
    
    if root_user:
        return build_tree(root_user)
    
    # Find top-level users (no reports_to)
    top_level_hierarchies = UserHierarchy.objects.filter(
        company=company,
        reports_to__isnull=True,
        is_active=True
    ).select_related('user', 'hierarchy_level').order_by('hierarchy_level__level_order', 'user__first_name')
    
    tree = []
    for hierarchy in top_level_hierarchies:
        node = build_tree(hierarchy.user)
        if node:
            tree.append(node)
    
    return tree


def print_hierarchy_tree(company, root_user=None, indent=0):
    """
    Print a visual representation of the hierarchy tree.
    
    Args:
        company: Company object
        root_user: Optional User object to start from
        indent: Current indentation level (for recursion)
    """
    def print_node(node, indent_level):
        """Recursively print hierarchy nodes"""
        prefix = "  " * indent_level
        print(f"{prefix}├─ {node['full_name']} ({node['hierarchy_level']})")
        if node['region'] or node['zone'] or node['territory']:
            geo = []
            if node['region']:
                geo.append(f"Region: {node['region']}")
            if node['zone']:
                geo.append(f"Zone: {node['zone']}")
            if node['territory']:
                geo.append(f"Territory: {node['territory']}")
            print(f"{prefix}   {', '.join(geo)}")
        
        for report in node['direct_reports']:
            print_node(report, indent_level + 1)
    
    tree = get_hierarchy_tree(company, root_user)
    
    if isinstance(tree, list):
        print(f"\n{'='*60}")
        print(f"Hierarchy Tree for {company.Company_name}")
        print(f"{'='*60}\n")
        for node in tree:
            print_node(node, 0)
            print()
    elif tree:
        print_node(tree, indent)
