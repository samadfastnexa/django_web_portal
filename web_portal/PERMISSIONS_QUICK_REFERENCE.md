# 🚀 Permission System - Quick Reference Card

## 🎯 Common Permission Patterns

### 1. Hide/Show Button in Template
```html
<!-- Single permission check -->
{% if perms.farmers.manage_farmers %}
    <button class="btn btn-primary">Add Farmer</button>
{% endif %}

<!-- Multiple permissions (AND) -->
{% if perms.attendance.manage_attendance and perms.attendance.approve_leave_requests %}
    <button class="btn btn-success">Approve All</button>
{% endif %}

<!-- Multiple permissions (OR) -->
{% if perms.farmers.manage_farmers or perms.farmers.view_farmer_reports %}
    <a href="{% url 'farmers_list' %}">View Farmers</a>
{% endif %}
```

### 2. Protect View Function
```python
from django.contrib.auth.decorators import permission_required

# Single permission
@permission_required('sap_integration.access_hana_connect')
def hana_dashboard(request):
    return render(request, 'hana.html')

# Multiple permissions (need ALL)
@permission_required(['farmers.manage_farmers', 'farm.manage_farms'])
def farm_management(request):
    return render(request, 'farm_mgmt.html')
```

### 3. Conditional Logic in View
```python
def farmer_list(request):
    can_edit = request.user.has_perm('farmers.manage_farmers')
    can_export = request.user.has_perm('farmers.export_farmer_data')
    
    farmers = Farmer.objects.all()
    
    return render(request, 'farmers.html', {
        'farmers': farmers,
        'can_edit': can_edit,
        'can_export': can_export,
    })
```

### 4. Protect Class-Based View
```python
from django.contrib.auth.mixins import PermissionRequiredMixin

class FarmerCreateView(PermissionRequiredMixin, CreateView):
    permission_required = 'farmers.manage_farmers'
    model = Farmer
    fields = '__all__'
```

### 5. REST API Permission
```python
from rest_framework import viewsets
from rest_framework.permissions import BasePermission

class HasDealerManagePermission(BasePermission):
    def has_permission(self, request, view):
        if request.method in ['GET', 'HEAD', 'OPTIONS']:
            return True
        return request.user.has_perm('FieldAdvisoryService.manage_dealers')

class DealerViewSet(viewsets.ModelViewSet):
    queryset = Dealer.objects.all()
    serializer_class = DealerSerializer
    permission_classes = [HasDealerManagePermission]
```

### 6. Check Permission in JavaScript (via API)
```javascript
// Check if user has permission to edit
fetch('/api/check-permission/?perm=farmers.manage_farmers')
    .then(response => response.json())
    .then(data => {
        if (data.has_permission) {
            document.getElementById('editBtn').style.display = 'block';
        }
    });
```

---

## 📋 Permission Quick Lookup

| Feature | Permission Codename |
|---------|---------------------|
| **HANA Connect** | `sap_integration.access_hana_connect` |
| **View Sales Reports** | `sap_integration.view_sales_reports` |
| **Manage Dealers** | `FieldAdvisoryService.manage_dealers` |
| **Manage Farmers** | `farmers.manage_farmers` |
| **Export Farmer Data** | `farmers.export_farmer_data` |
| **Manage Attendance** | `attendance.manage_attendance` |
| **Approve Leave** | `attendance.approve_leave_requests` |
| **Manage Complaints** | `complaints.manage_complaints` |
| **Assign Complaints** | `complaints.assign_complaints` |
| **Manage Crops** | `crop_management.manage_crops` |
| **Manage Farms** | `farm.manage_farms` |
| **Manage Users** | `accounts.manage_users` |
| **Manage Roles** | `accounts.manage_roles` |

---

## 🛠️ Setting Up a New Role

### Example: "Field Coordinator" Role

1. **Go to Admin → Accounts → Roles**
2. **Click "Add Role"**
3. **Name**: "Field Coordinator"
4. **Select these permissions**:
   - ✅ `farmers.manage_farmers`
   - ✅ `farmers.view_farmer_reports`
   - ✅ `farm.manage_farms`
   - ✅ `complaints.manage_complaints`
   - ✅ `attendance.manage_attendance`
   - ✅ `farmerMeetingDataEntry.manage_meetings`
5. **Save**

Now any user assigned the "Field Coordinator" role will have these permissions.

---

## ⚠️ Important Notes

### Permission Format
Always use: `app_label.codename`
- ✅ `farmers.manage_farmers`
- ❌ `manage_farmers` (missing app label)
- ❌ `Farmers.manage_farmers` (wrong case)

### Superuser Bypass
Superusers automatically have ALL permissions, regardless of what's assigned to their role.

### Testing Permissions
Use Django shell to test:
```python
python manage.py shell

from django.contrib.auth import get_user_model
User = get_user_model()

user = User.objects.get(email='test@example.com')
print(user.has_perm('farmers.manage_farmers'))  # True/False
print(user.get_all_permissions())  # List all permissions
```

---

## 🎯 Priority Implementation Areas

Start adding permission checks to these critical areas first:

1. **HANA Connect Dashboard** - `sap_integration/views.py`
   - `access_hana_connect` permission

2. **Dealer Management** - `FieldAdvisoryService/views.py`
   - `manage_dealers` permission

3. **Farmer CRUD Operations** - `farmers/views.py`
   - `manage_farmers` permission
   - `export_farmer_data` permission

4. **Attendance System** - `attendance/views.py`
   - `manage_attendance` permission
   - `approve_leave_requests` permission

5. **Complaint Management** - `complaints/views.py`
   - `manage_complaints` permission
   - `assign_complaints` permission

---

## 📞 Need Help?

- **Full Documentation**: See `PERMISSIONS_DOCUMENTATION.md`
- **All Permissions List**: See `permissions_config.py`
- **Implementation Guide**: See `PERMISSIONS_IMPLEMENTATION_COMPLETE.md`
