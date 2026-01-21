# Hierarchy Permissions Reference

## New Custom Permissions Added

The following permissions were added to `SalesStaffProfile` model:

### 1. `view_hierarchy`
**Codename:** `accounts.view_hierarchy`  
**Description:** Can view reporting hierarchy  
**Usage:** Allows users to access:
- `/api/users/my-team/` - View subordinates
- `/api/users/my-reporting-chain/` - View upward chain
- `/api/users/my-hierarchy/` - View complete hierarchy

**Default Access:**
- ✅ All Sales Staff (automatic)
- ✅ Superusers
- Assign to roles that need to see organizational structure

---

### 2. `manage_hierarchy`
**Codename:** `accounts.manage_hierarchy`  
**Description:** Can assign/change managers  
**Usage:** Allows users to:
- Assign managers to sales staff
- Update reporting relationships
- Modify `manager` field via API/Admin

**Default Access:**
- ✅ Superusers only
- Assign to HR managers, CEO, Regional Leaders

---

### 3. `view_subordinate_data`
**Codename:** `accounts.view_subordinate_data`  
**Description:** Can view subordinates' data  
**Usage:** Automatically applied in ViewSets:
- MeetingViewSet - see subordinates' meetings
- FieldDayViewSet - see subordinates' field days
- Any future data filtered by hierarchy

**Default Access:**
- ✅ All Sales Staff with subordinates (automatic)
- ✅ Superusers
- No need to assign manually

---

### 4. `view_all_hierarchy`
**Codename:** `accounts.view_all_hierarchy`  
**Description:** Can view entire organization hierarchy  
**Usage:** Future-proofing for:
- Organization chart view (all staff)
- HR dashboard showing complete structure
- Reporting tools

**Default Access:**
- ✅ Superusers only
- Assign to CEO, HR Manager, CFO

---

## Permission Classes Created

### `CanViewHierarchy`
Applied to hierarchy API endpoints (`my-team`, `my-reporting-chain`, `my-hierarchy`)

**Logic:**
- ✅ Superusers → Always allowed
- ✅ Sales Staff → Can view their own hierarchy
- ✅ Users with `view_hierarchy` permission

---

### `CanManageHierarchy`
Applied to user create/update operations involving `manager` field

**Logic:**
- ✅ Superusers → Always allowed
- ✅ Users with `manage_hierarchy` permission → Can modify
- ❌ Others → Read-only

---

### `CanViewSubordinateData`
Applied to data access (meetings, field days, etc.)

**Logic:**
- ✅ Superusers → All data
- ✅ Sales Staff → Their data + subordinates' data (automatic via get_queryset)
- ✅ Users with `view_subordinate_data` permission

---

### `CanViewAllHierarchy`
Reserved for future org chart features

**Logic:**
- ✅ Superusers → Always allowed
- ✅ Users with `view_all_hierarchy` permission

---

## How to Assign Permissions to Roles

### Via Django Admin:

1. Go to **Roles** admin
2. Select a role (e.g., "Regional Sales Leader")
3. In **Permissions** section, add:
   - `accounts | sales staff profile | Can view reporting hierarchy`
   - `accounts | sales staff profile | Can assign/change managers`
   - `accounts | sales staff profile | Can view subordinates data`
   - `accounts | sales staff profile | Can view entire organization hierarchy`

4. Save

### Via Code/Migration:

```python
from django.contrib.auth.models import Permission
from accounts.models import Role

# Get permissions
view_hierarchy = Permission.objects.get(codename='view_hierarchy')
manage_hierarchy = Permission.objects.get(codename='manage_hierarchy')
view_subordinate_data = Permission.objects.get(codename='view_subordinate_data')
view_all_hierarchy = Permission.objects.get(codename='view_all_hierarchy')

# Assign to role
role = Role.objects.get(name='Regional Sales Leader')
role.permissions.add(
    view_hierarchy,
    manage_hierarchy,
    view_subordinate_data
)
```

---

## Recommended Permission Assignments

### CEO Role:
```
✅ view_hierarchy
✅ manage_hierarchy  
✅ view_subordinate_data
✅ view_all_hierarchy
```

### Regional Sales Leader (RSL):
```
✅ view_hierarchy (automatic as sales staff)
✅ manage_hierarchy (to assign zone managers)
✅ view_subordinate_data (automatic)
❌ view_all_hierarchy (not needed)
```

### Zone Manager (ZM):
```
✅ view_hierarchy (automatic)
❌ manage_hierarchy (cannot assign managers)
✅ view_subordinate_data (automatic)
❌ view_all_hierarchy
```

### Field Sales Manager (FSM):
```
✅ view_hierarchy (automatic)
❌ manage_hierarchy
✅ view_subordinate_data (if has subordinates)
❌ view_all_hierarchy
```

### HR Manager:
```
✅ view_hierarchy
✅ manage_hierarchy
✅ view_subordinate_data
✅ view_all_hierarchy
```

---

## Testing Permissions

### 1. Test as Sales Staff (should work):
```bash
GET /api/users/my-team/
GET /api/users/my-reporting-chain/
GET /api/users/my-hierarchy/
```

### 2. Test as Non-Sales Staff without permission (should fail):
```bash
GET /api/users/my-team/
# Response: 403 Forbidden
```

### 3. Test Manager Assignment (requires manage_hierarchy):
```bash
PATCH /api/users/{id}/
{
  "manager": 5
}
# Works if user has 'manage_hierarchy' permission
# Fails with 403 otherwise
```

### 4. Test Data Filtering (automatic):
```bash
# As Zone Manager with 3 FSMs reporting to them
GET /api/meetings/
# Should return: ZM's meetings + all 3 FSMs' meetings

# As FSM with no subordinates
GET /api/meetings/
# Should return: Only FSM's own meetings
```

---

## Migration Applied

✅ Migration created: `0017_add_hierarchy_permissions.py`
✅ Migration applied successfully

The new permissions are now available in Django admin under:
**Roles → Permissions → Select → accounts | sales staff profile**

---

## Summary

✅ 4 new custom permissions added
✅ 4 permission classes created
✅ Applied to hierarchy API endpoints
✅ Automatic filtering in MeetingViewSet and FieldDayViewSet
✅ Admin actions check permissions
✅ Migration applied

**Next Steps:**
1. Assign permissions to appropriate roles via Admin
2. Test hierarchy endpoints with different role users
3. Verify data filtering works correctly
