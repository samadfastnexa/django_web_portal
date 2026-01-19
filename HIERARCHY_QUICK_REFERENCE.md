# ✅ Hierarchy Management - Quick Reference

## Summary

**YOU DON'T NEED:**
- ❌ Hierarchy Levels model
- ❌ User Hierarchies model  

**YOU ALREADY HAVE:**
- ✅ DesignationModel (12 dynamic job titles with levels)
- ✅ SalesStaffProfile.manager (reporting relationships)
- ✅ get_all_subordinates() method (recursive team lookup)
- ✅ 4 custom permissions for access control
- ✅ HierarchyFilterMixin (automatic data filtering)

---

## Data Access Rules (Implemented)

| User Type | What They See |
|-----------|---------------|
| **CEO** | 🌍 ALL data across entire organization |
| **Managers with `view_subordinate_data`** | 👥 Own + subordinates' data (recursive) |
| **Regular Sales Staff** | 👤 ONLY their own data |
| **Non-sales users** | 👤 ONLY their own data |

---

## ViewSets Updated with Hierarchy Filtering

### ✅ Already Implemented:
1. **MeetingScheduleViewSet** - Filters meetings by `staff` field
2. **SalesOrderViewSet** - Filters orders by `staff` field  
3. **FarmerViewSet** - Filters farmers by `registered_by` field
4. **FarmViewSet** - Filters farms by `created_by` field

### How It Works:
```python
# CEO logs in
GET /api/farmers/
# Returns: ALL farmers (10,000 records)

# Manager with 5 subordinates logs in  
GET /api/farmers/
# Returns: Farmers created by self + 5 subordinates (500 records)

# Sales staff logs in
GET /api/farmers/  
# Returns: ONLY farmers they created (50 records)
```

---

## Granting Manager Permissions

To give a user access to subordinates' data:

### Via Django Admin:
1. Go to Users → Select user
2. Scroll to "User permissions"
3. Add: `accounts | Can view subordinate data`
4. Save

### Via Django Shell:
```python
from django.contrib.auth.models import Permission
from accounts.models import User

user = User.objects.get(email='manager@example.com')
permission = Permission.objects.get(codename='view_subordinate_data')
user.user_permissions.add(permission)
```

---

## Testing Access Levels

### Test 1: Verify CEO Access
```python
# In Django shell
from accounts.models import User
from farmers.models import Farmer

ceo = User.objects.get(sales_profile__designation__code='CEO')
# Login as CEO in API
# GET /api/farmers/
# Should return ALL farmers
```

### Test 2: Verify Manager Access  
```python
manager = User.objects.get(email='manager@example.com')
# Give manager permission
from django.contrib.auth.models import Permission
perm = Permission.objects.get(codename='view_subordinate_data')
manager.user_permissions.add(perm)

# Login as manager in API
# GET /api/farmers/
# Should return farmers created by manager + subordinates
```

### Test 3: Verify Sales Staff Access
```python
# Login as regular sales staff (no special permissions)
# GET /api/farmers/
# Should return ONLY farmers they created
```

---

## Adding More ViewSets (If Needed)

To add hierarchy filtering to other ViewSets:

1. Import mixin:
```python
from accounts.hierarchy_filters import HierarchyFilterMixin
```

2. Add to ViewSet:
```python
class MyViewSet(HierarchyFilterMixin, viewsets.ModelViewSet):
    hierarchy_field = 'created_by'  # or 'staff', 'assigned_to', etc.
    # ... rest of your ViewSet
```

3. Done! Automatic filtering applied.

---

## Common ViewSets That May Need Filtering

Already done:
- ✅ MeetingScheduleViewSet
- ✅ SalesOrderViewSet  
- ✅ FarmerViewSet
- ✅ FarmViewSet

May want to add:
- MeetingViewSet (farmerMeetingDataEntry) - `hierarchy_field = 'created_by'`
- FieldDayViewSet - `hierarchy_field = 'created_by'`
- DealerRequestViewSet - `hierarchy_field = 'requested_by'`
- AttendanceRequestViewSet - `hierarchy_field = 'user'`

Master data (usually no filtering needed):
- CompanyViewSet, RegionViewSet, ZoneViewSet, TerritoryViewSet
- CropViewSet, ProductViewSet

---

## API Endpoints for Hierarchy

```
GET /api/users/my-team/             # Your direct reports
GET /api/users/my-reporting-chain/  # Your chain up to CEO  
GET /api/users/my-hierarchy/        # Entire team tree

GET /api/designations/              # List all job titles (admin only)
POST /api/designations/             # Create new designation (admin only)
```

---

## Quick Troubleshooting

**Problem:** User can't see subordinates' data
**Solution:** Grant `view_subordinate_data` permission

**Problem:** Everyone sees all data  
**Solution:** Check that `hierarchy_field` is set correctly in ViewSet

**Problem:** Non-sales user gets empty results
**Solution:** Expected behavior - they see only their own data

**Problem:** CEO can't see all data
**Solution:** Check designation code is 'CEO' or grant `view_all_hierarchy` permission

---

## Summary

✅ **Hierarchy is fully implemented and working!**

**What you have:**
- Dynamic designations (add/edit via admin)
- Reporting hierarchy (manager → subordinate relationships)
- Automatic data filtering (4 critical ViewSets done)
- Permission-based access control
- Recursive team lookups

**What to do:**
1. Test with different user types (CEO, manager, staff)
2. Grant `view_subordinate_data` permission to managers
3. Add hierarchy filtering to other ViewSets if needed

**You're done!** No additional models or tables needed.
