# Hierarchy and Permissions Implementation Summary

## ✅ Completed Implementation

### 1. Hierarchy Utility Functions
**File:** `accounts/hierarchy_utils.py`

Provides comprehensive functions for managing organizational hierarchy:

- **`get_user_subordinates(user, include_self=False)`** - Get all subordinates (direct + indirect)
- **`get_user_managers(user, include_self=False)`** - Get all managers above a user
- **`get_direct_reports(user)`** - Get only immediate subordinates
- **`get_immediate_manager(user)`** - Get direct supervisor
- **`get_hierarchy_level_order(user)`** - Get user's hierarchy level (0=highest)
- **`user_can_access_data(current_user, data_owner_user)`** - Check if user can access another user's data
- **`get_users_in_same_region(user)`** - Get peers in same region
- **`get_users_in_same_zone(user)`** - Get peers in same zone
- **`get_hierarchy_tree(company, root_user=None)`** - Get complete hierarchy tree structure
- **`print_hierarchy_tree(company, root_user=None, indent=0)`** - Print visual hierarchy

### 2. Custom Permission Classes
**File:** `accounts/permissions.py`

New permission classes added:

- **`HierarchyBasedPermission`** - Base class for hierarchy-based access control
- **`CanManageUsers`** - Permission to manage users (requires `accounts.manage_users`)
- **`CanManageRoles`** - Permission to manage roles (requires `accounts.manage_roles`)
- **`CanManageSalesStaff`** - Permission to manage sales staff (requires `accounts.manage_sales_staff`)
- **`CanManageDealers`** - Permission to manage dealers (requires `FieldAdvisoryService.manage_dealers`)
- **`CanApproveDealerRequests`** - Permission to approve dealer requests
- **`CanManageFarmers`** - Permission to manage farmers (requires `farmers.manage_farmers`)
- **`CanManageMeetings`** - Permission to manage meetings (requires `farmerMeetingDataEntry.manage_meetings`)
- **`CanAccessSAPData`** - Permission to access SAP data
- **`CanPostToSAP`** - Permission to post data to SAP

### 3. Management Command
**File:** `accounts/management/commands/show_hierarchy.py`

Command to visualize organizational hierarchy:

```bash
# Show hierarchy for first company
python manage.py show_hierarchy

# Show hierarchy for specific company
python manage.py show_hierarchy --company=1

# Show hierarchy starting from specific user
python manage.py show_hierarchy --company=1 --user=5

# Output as JSON
python manage.py show_hierarchy --company=1 --format=json
```

---

## 📋 Roles and Permissions in the System

### Built-in Django Permissions (Auto-generated)
For each model, Django creates 4 permissions:
- `add_<model>` - Can create
- `change_<model>` - Can update  
- `delete_<model>` - Can delete
- `view_<model>` - Can view

### Custom Permissions by Module

#### 1. **SAP Integration** (`sap_integration` app)
- `access_hana_connect` - Can access HANA Connect dashboard
- `view_policy_balance` - Can view policy balance reports
- `view_customer_data` - Can view customer data
- `view_item_master` - Can view item master list
- `view_sales_reports` - Can view sales vs achievement reports
- `sync_policies` - Can sync policies from SAP
- `post_to_sap` - Can post data to SAP
- `manage_policies` - Can manage policy records

#### 2. **Field Advisory Service** (`FieldAdvisoryService` app)
- `manage_dealers` - Can add/edit/delete dealers
- `view_dealer_reports` - Can view dealer reports
- `approve_dealer_requests` - Can approve dealer requests
- `manage_companies` - Can manage company records
- `manage_regions` - Can manage regions
- `manage_zones` - Can manage zones
- `manage_territories` - Can manage territories

#### 3. **Farmers** (`farmers` app)
- `manage_farmers` - Can add/edit/delete farmer records
- `view_farmer_reports` - Can view farmer statistics
- `export_farmer_data` - Can export farmer data

#### 4. **Crop Management** (`crop_management` app)
- `manage_crops` - Can manage crops
- `view_crop_analytics` - Can view crop analytics
- `manage_varieties` - Can manage crop varieties
- `manage_yield_data` - Can manage yield data
- `view_yield_analytics` - Can view yield analytics
- `manage_farming_practices` - Can manage farming practices
- `manage_research` - Can manage research data
- `manage_trials` - Can add/edit/delete field trials
- `view_trial_results` - Can view trial results
- `manage_treatments` - Can manage trial treatments
- `manage_products` - Can manage trial products

#### 5. **Farm Management** (`farm` app)
- `manage_farms` - Can add/edit/delete farms
- `view_farm_analytics` - Can view farm analytics

#### 6. **Attendance** (`attendance` app)
- `manage_attendance` - Can mark/edit attendance
- `view_attendance_reports` - Can view attendance reports
- `approve_attendance_requests` - Can approve attendance requests

#### 7. **Complaints** (`complaints` app)
- `manage_complaints` - Can manage complaints
- `view_complaint_analytics` - Can view complaint reports

#### 8. **Meetings** (`farmerMeetingDataEntry` app)
- `manage_meetings` - Can add/edit meetings
- `manage_field_days` - Can manage field days
- `view_meeting_reports` - Can view meeting reports

#### 9. **KindWise** (`kindwise` app)
- `use_plant_identification` - Can use plant identification API
- `view_identification_history` - Can view identification history

#### 10. **User Management** (`accounts` app)
- `manage_users` - Can add/edit users
- `manage_roles` - Can manage roles and permissions
- `manage_sales_staff` - Can manage sales staff profiles
- `view_user_reports` - Can view user reports

#### 11. **General Ledger** (`general_ledger` app)
- `view_ledger` - Can view general ledger entries
- `export_ledger` - Can export ledger data

#### 12. **Analytics** (`analytics` app)
- `view_dashboard` - Can access analytics dashboard
- `view_sales_analytics` - Can view sales analytics
- `view_farmer_analytics` - Can view farmer analytics
- `export_analytics` - Can export analytics reports

#### 13. **Settings** (`preferences` app)
- `manage_settings` - Can manage system settings
- `view_settings` - Can view system settings

---

## 🎯 How to Use

### 1. Assign Permissions to Roles (Django Admin)

1. Go to **Admin → Accounts → Roles**
2. Create or edit a role (e.g., "Sales Manager")
3. In the **Permissions** multi-select field, choose relevant permissions
4. Save the role

**Example Role Setups:**

**Admin Role:**
- All permissions

**Sales Manager:**
- `sap_integration.view_sales_reports`
- `sap_integration.view_customer_data`
- `FieldAdvisoryService.manage_dealers`
- `FieldAdvisoryService.view_dealer_reports`
- `farmers.view_farmer_reports`
- `accounts.manage_sales_staff`

**Field Officer:**
- `farmers.manage_farmers`
- `farm.manage_farms`
- `farmerMeetingDataEntry.manage_meetings`
- `farmerMeetingDataEntry.manage_field_days`
- `attendance.manage_attendance`

**Dealer:**
- `FieldAdvisoryService.view_dealer_reports`
- `farmers.view_farmer_reports`

### 2. Use Permissions in ViewSets

```python
from rest_framework.permissions import IsAuthenticated
from accounts.permissions import CanManageFarmers, HierarchyBasedPermission

class FarmerViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated, CanManageFarmers, HierarchyBasedPermission]
    # ...
```

### 3. Use Hierarchy Functions in Code

```python
from accounts.hierarchy_utils import get_user_subordinates, user_can_access_data

# Get all subordinates for current user
subordinates = get_user_subordinates(request.user, include_self=False)

# Filter queryset to show only user's data and subordinates' data
queryset = Model.objects.filter(user__in=subordinates)

# Check if user can access specific data
if user_can_access_data(request.user, data_owner):
    # Allow access
    pass
```

### 4. Check Permissions in Templates

```django
{% if perms.farmers.manage_farmers %}
    <button>Add Farmer</button>
{% endif %}

{% if perms.sap_integration.post_to_sap %}
    <button>Post to SAP</button>
{% endif %}
```

### 5. Check Permissions in Views

```python
if request.user.has_perm('farmers.manage_farmers'):
    # User can manage farmers
    pass

if request.user.has_perm('sap_integration.post_to_sap'):
    # User can post to SAP
    pass
```

---

## 🔄 Next Steps (Not Yet Implemented)

### 3. Update ViewSets to Use Hierarchy Filtering ⏳

To filter data based on hierarchy, modify ViewSets:

```python
from accounts.hierarchy_utils import get_user_subordinates

class MeetingViewSet(viewsets.ModelViewSet):
    def get_queryset(self):
        queryset = super().get_queryset()
        user = self.request.user
        
        if user.is_superuser:
            return queryset
        
        # Filter to show only user's data and their subordinates' data
        subordinates = get_user_subordinates(user, include_self=True)
        return queryset.filter(user__in=subordinates)
```

### 4. Update Admin to Show Hierarchy ⏳

Add hierarchy information to User admin:

```python
from accounts.hierarchy_utils import get_immediate_manager, get_direct_reports

class UserAdmin(admin.ModelAdmin):
    list_display = ['username', 'email', 'role', 'get_manager', 'get_direct_reports_count']
    
    def get_manager(self, obj):
        manager = get_immediate_manager(obj)
        return manager.username if manager else '-'
    get_manager.short_description = 'Manager'
    
    def get_direct_reports_count(self, obj):
        return get_direct_reports(obj).count()
    get_direct_reports_count.short_description = '# Direct Reports'
```

---

## 📊 Current System Status

✅ **Completed:**
1. Hierarchy Utility Functions
2. Custom Permission Classes  
3. Management Command for Viewing Hierarchy
4. All Custom Permissions Created (48 total)
5. Role Model with Permissions
6. UserHierarchy Model with Reporting Structure

⏳ **Pending:**
1. Apply hierarchy filtering to ViewSets
2. Update Admin interfaces to show hierarchy
3. Frontend integration with permissions
4. Permission-based menu visibility

---

## 📝 Example: Complete Role Setup

### Creating "Regional Sales Manager" Role

1. **Go to Admin → Accounts → Roles → Add Role**

2. **Enter role name:** "Regional Sales Manager"

3. **Select permissions:**
   - SAP Integration:
     - `access_hana_connect`
     - `view_sales_reports`
     - `view_customer_data`
     - `view_policy_balance`
   
   - Dealers:
     - `view_dealer_reports`
     - `approve_dealer_requests`
   
   - Farmers:
     - `view_farmer_reports`
   
   - Users:
     - `manage_sales_staff`
     - `view_user_reports`
   
   - Analytics:
     - `view_dashboard`
     - `view_sales_analytics`

4. **Save the role**

5. **Assign to users:**
   - Go to **Admin → Accounts → Users**
   - Edit a user
   - Set **Role** to "Regional Sales Manager"
   - Save

Now that user will have all those permissions and can access only their subordinates' data through the hierarchy system.

---

## 🔐 Security Best Practices

1. **Always check permissions in API views**
2. **Filter data based on hierarchy when appropriate**
3. **Use `IsAuthenticated` as the base permission**
4. **Combine permissions for defense in depth**
5. **Audit permission usage regularly**
6. **Review role assignments periodically**

---

For more details, see:
- `PERMISSIONS_DOCUMENTATION.md`
- `PERMISSIONS_IMPLEMENTATION_COMPLETE.md`
- `permissions_config.py`
