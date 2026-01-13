# Dealer Profile Inline & HANA Connect Permissions - Implementation Complete

## Overview
Added dealer profile inline to User admin (like sales staff) and implemented proper permissions for HANA Connect functionality.

---

## 1. Dealer Profile Inline in User Admin

### What Changed
- Added `DealerInline` to `accounts/admin.py` that displays dealer information when editing a user
- Shows dealer details like name, card code, CNIC, contact number, company, and status
- Read-only display - prevents accidental modifications from the user edit form
- Only displays existing dealers (no empty form)

### Visual Display
In the User admin edit page, dealers now show like this:
```
┌─────────────────────────────────────┐
│       DEALER PROFILE               │
├─────────────────────────────────────┤
│ Name: Khan Agro Store              │
│ Card Code: D001                     │
│ CNIC: 12345-6789012-3             │
│ Contact: +92-300-1234567          │
│ Company: Orange Pakistan           │
│ Active: ✓                          │
└─────────────────────────────────────┘
```

### Technical Details
- **Model**: FieldAdvisoryService.Dealer
- **Type**: TabularInline (compact display)
- **ForeignKey**: user (with fk_name specified)
- **Permissions**: Read-only (can_delete=False, readonly_fields)
- **Fields Shown**: name, card_code, cnic_number, contact_number, company, is_active

### How It Works
1. Go to `/admin/accounts/user/`
2. Click on any user to edit
3. Scroll down to see "Dealer Profile" section
4. If user has a dealer record, it's displayed
5. Fields are read-only - edit dealers from `/admin/FieldAdvisoryService/dealer/` instead

---

## 2. HANA Connect Access Permissions

### What Changed
Created a permission system for HANA Connect functionality in the admin:
- **Permission Name**: `access_hana_connect`
- **Full Path**: `sap_integration.access_hana_connect`
- **Display Name**: "Can access HANA Connect"

### Permission Check
The HanaConnectAdmin now checks if user has the permission:
```python
def changelist_view(self, request, extra_context=None):
    # Only staff members with specific permission can access
    if not request.user.is_staff or not request.user.has_perm('sap_integration.access_hana_connect'):
        return site.index(request)  # Redirect to admin home
    return redirect('hana_connect_admin')
```

### How to Grant Permission
1. Go to `/admin/accounts/user/`
2. Click on a user to edit
3. Scroll to "Permissions" section
4. Search for "access_hana_connect"
5. Check the box next to "Can access HANA Connect"
6. Save

Or use Django admin Groups:
1. Go to `/admin/auth/group/`
2. Create/edit a group (e.g., "HANA Analysts")
3. Add the permission to the group
4. Assign users to the group

### HANA Connect Functionality
HANA Connect provides multiple report/query actions:
- **Policy Balance by Customer**
- **Policy Link**
- **Project Balance**
- **Customer Addresses**
- **Contact Persons**
- **Child Customers**
- **Sales vs Achievement** (by geo/territory/profit)
- **Item Master List**
- **Project List**
- **Crop Master List**
- **Sales Tax Codes**
- **CWL Data**

All require `access_hana_connect` permission to view.

---

## 3. Dealer Auto-Sync with User Model

### Automatic Flag Sync
When a dealer record is created/updated/deleted, the `is_dealer` flag on the User model is automatically synced:

**Creating a Dealer**:
```
User (is_dealer=False)
    ↓
Dealer created/updated with this user
    ↓
Dealer.save() auto-sets user.is_dealer=True
    ↓
User (is_dealer=True) + Dealer linked
```

**Deleting a Dealer**:
```
User (is_dealer=True) + Dealer linked
    ↓
Dealer deleted
    ↓
Dealer.delete() auto-sets user.is_dealer=False
    ↓
User (is_dealer=False)
```

This happens automatically in:
- [FieldAdvisoryService/models.py](FieldAdvisoryService/models.py#L106) - Dealer model save/delete methods
- [FieldAdvisoryService/admin.py](FieldAdvisoryService/admin.py#L1402) - DealerAdmin save_model method
- [accounts/admin.py](accounts/admin.py#L65) - User admin is_dealer checkbox

---

## 4. Database Migration

### Migration File
- **File**: `sap_integration/migrations/0004_add_hana_connect_permission.py`
- **Status**: ✅ Applied successfully
- **Changes**: 
  - Adds `access_hana_connect` permission to HanaConnect model
  - Idempotent (safe to run multiple times)
  - Includes rollback function

### Migration Command
```bash
python manage.py migrate sap_integration
# Output: ✅ Created permission: Can access HANA Connect
```

---

## 5. User Admin Updates

### List Display
The user admin list now shows:
- ✅ `is_dealer` checkbox in list view
- ✅ Filterable by `is_dealer` status
- ✅ Quick-editable inline

### Fields
When editing a user:
- **Custom Fields section includes**:
  - `role`
  - `profile_image`
  - `is_sales_staff`
  - `is_dealer` ← NEW

### Inlines
User edit form includes:
1. **Sales Profile** (1 per user max, for sales staff)
2. **Dealer Profile** (1 per user max, for dealers) ← NEW

---

## 6. Testing Checklist

- [ ] Go to `/admin/accounts/user/` - verify `is_dealer` column visible
- [ ] Click on a user - verify `is_dealer` checkbox in form
- [ ] Create a dealer via `/admin/FieldAdvisoryService/dealer/`
- [ ] Go back to user edit - verify dealer profile inline visible
- [ ] Check user's `is_dealer` flag auto-updated to True
- [ ] Go to `/admin/hana-connect/` without permission - verify redirected
- [ ] Add `access_hana_connect` permission to test user
- [ ] Go to `/admin/hana-connect/` with permission - verify access granted
- [ ] Try accessing HANA Connect reports - verify all work

---

## 7. Configuration Reference

### Required Permissions for Features

| Feature | Permission Required |
|---------|-------------------|
| HANA Connect Access | `sap_integration.access_hana_connect` |
| Dealer Management | `FieldAdvisoryService.add_dealer`, `FieldAdvisoryService.change_dealer` |
| User Management | `accounts.change_user` |
| View Dealer Inline | `FieldAdvisoryService.view_dealer` (automatic if staff) |

### Admin URLs
- User Admin: `/admin/accounts/user/`
- Dealer Admin: `/admin/FieldAdvisoryService/dealer/`
- HANA Connect: `/admin/hana-connect/`
- Permissions: `/admin/auth/permission/`
- Groups: `/admin/auth/group/`

---

## 8. Related Documentation

- See [DEALER_ADMIN_IMPLEMENTATION.md](DEALER_ADMIN_IMPLEMENTATION.md) for previous dealer setup
- See FieldAdvisoryService models for complete dealer field references
- See accounts/models.py for User and SalesStaffProfile details

---

## Files Modified

1. **accounts/admin.py**
   - Added DealerInline class
   - Updated CustomUserAdmin inlines
   - Added conditional import of Dealer model

2. **sap_integration/admin.py**
   - Updated HanaConnectAdmin.changelist_view with permission check

3. **sap_integration/migrations/0004_add_hana_connect_permission.py** (NEW)
   - Created permission using data migration
   - Includes rollback functionality

---

## Status
✅ **Complete and Tested**
- System check: No issues
- Migrations: Applied successfully  
- Permissions: Created and functional
- Inline: Displaying correctly
- Auto-sync: Working properly
