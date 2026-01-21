# Hierarchy Management - Complete Implementation Guide

## ✅ What's Already Implemented

### 1. **Database Structure**
- **DesignationModel**: Dynamic job titles/roles (CEO, NSM, RSL, etc.) with hierarchy levels
- **SalesStaffProfile.manager**: Self-referencing ForeignKey for reporting relationships  
- **Geographic Hierarchy**: Companies → Regions → Zones → Territories (Many-to-Many)

### 2. **Hierarchy Methods** (SalesStaffProfile model)
```python
# Get all subordinates recursively
subordinates = profile.get_all_subordinates(include_self=True)

# Get reporting chain up to CEO
chain = profile.get_reporting_chain()

# Check if user A reports to user B
is_subordinate = profileA.is_subordinate_of(profileB)
```

### 3. **Custom Permissions**
- `accounts.view_hierarchy` - View hierarchy endpoints
- `accounts.manage_hierarchy` - Modify hierarchy relationships
- `accounts.view_subordinate_data` - Access subordinates' data
- `accounts.view_all_hierarchy` - Full access (CEO-level)

### 4. **Permission Classes** (`accounts/hierarchy_permissions.py`)
- `CanViewHierarchy` - For hierarchy endpoints
- `CanManageHierarchy` - For modifying hierarchy
- `CanViewSubordinateData` - For data access control
- `CanViewAllHierarchy` - CEO/admin access

### 5. **API Endpoints** (UserViewSet)
```
GET /api/users/my-team/              # View your direct reports
GET /api/users/my-reporting-chain/    # View your reporting chain
GET /api/users/my-hierarchy/          # View entire team tree
```

### 6. **Admin Interface** (`accounts/admin.py`)
- Hierarchy columns in list view (Reports To, Team Size)
- Admin actions: View Hierarchy Tree, View Reporting Chain
- DesignationAdmin for managing job titles dynamically

---

## 🎯 Data Access Control Rules

### Access Levels

| Role | Access |
|------|--------|
| **CEO** | All data across organization |
| **Managers with `view_subordinate_data`** | Own + all subordinates' data (recursive) |
| **Regular Sales Staff** | Only own data |
| **Non-sales users** | Only own data |

---

## 🚀 How to Implement Hierarchy Filtering in ViewSets

### Step 1: Import the Mixin

```python
from accounts.hierarchy_filters import HierarchyFilterMixin
```

### Step 2: Add Mixin to ViewSet

```python
class FarmerViewSet(HierarchyFilterMixin, viewsets.ModelViewSet):
    queryset = Farmer.objects.all()
    serializer_class = FarmerSerializer
    
    # Specify which field links to User (who has SalesStaffProfile)
    hierarchy_field = 'created_by'  # or 'assigned_to', 'staff', etc.
```

### Step 3: That's it!

The mixin automatically:
- ✅ Filters queryset based on user's hierarchy position
- ✅ Applies CEO/manager/staff rules
- ✅ Works with search, ordering, and other filters

---

## 📋 ViewSets That Need Hierarchy Filtering

Add `HierarchyFilterMixin` to these ViewSets:

### Critical (User-created data):
1. **MeetingScheduleViewSet** - `hierarchy_field = 'staff'`
2. **SalesOrderViewSet** - `hierarchy_field = 'staff'`
3. **FarmerViewSet** - `hierarchy_field = 'created_by'` or `'assigned_to'`
4. **FarmViewSet** - `hierarchy_field = 'created_by'`
5. **MeetingViewSet** (farmerMeetingDataEntry) - `hierarchy_field = 'created_by'`
6. **FieldDayViewSet** - `hierarchy_field = 'created_by'`
7. **DealerRequestViewSet** - `hierarchy_field = 'requested_by'`

### Optional (Master data - typically no filtering):
- CompanyViewSet, RegionViewSet, ZoneViewSet, TerritoryViewSet
- CropViewSet, CropVarietyViewSet
- ProductViewSet

---

## 🔧 Example Implementation

### Before (No Hierarchy Filtering):
```python
class FarmerViewSet(viewsets.ModelViewSet):
    queryset = Farmer.objects.all()
    serializer_class = FarmerSerializer
    # Everyone sees all farmers ❌
```

### After (With Hierarchy Filtering):
```python
from accounts.hierarchy_filters import HierarchyFilterMixin

class FarmerViewSet(HierarchyFilterMixin, viewsets.ModelViewSet):
    queryset = Farmer.objects.all()
    serializer_class = FarmerSerializer
    hierarchy_field = 'created_by'  # Field linking to User
    
    # ✅ CEO sees all farmers
    # ✅ Managers see farmers created by their team
    # ✅ Sales staff see only their own farmers
```

---

## 🔍 Helper Functions

If you need custom logic outside ViewSets:

```python
from accounts.hierarchy_filters import get_accessible_users, get_accessible_staff_profiles

# Get users accessible to current user
accessible_users = get_accessible_users(request.user)

# Get staff profiles accessible to current user  
accessible_profiles = get_accessible_staff_profiles(request.user)

# Use in custom queries
farmers = Farmer.objects.filter(created_by__in=accessible_users)
```

---

## ❌ What You DON'T Need

### **Hierarchy Levels Model** - NOT NEEDED ✓
- Already have `DesignationModel` with `level` field (0=CEO, 11=MTO)
- Provides ordering and hierarchy structure

### **User Hierarchies Model** - NOT NEEDED ✓
- Already have `SalesStaffProfile.manager` field
- Provides direct reporting relationships
- `get_all_subordinates()` method handles recursive lookups

---

## 📊 Testing Hierarchy Access

### Test Scenario 1: CEO Access
```python
# Login as CEO
response = client.get('/api/farmers/')
# Should see ALL farmers in system
```

### Test Scenario 2: Manager Access  
```python
# Login as Regional Sales Leader with 5 subordinates
response = client.get('/api/farmers/')
# Should see farmers created by self + 5 subordinates
```

### Test Scenario 3: Sales Staff Access
```python
# Login as Field Sales Manager (lowest level)
response = client.get('/api/farmers/')
# Should see ONLY farmers they created
```

---

## 🎯 Next Steps

1. **Add HierarchyFilterMixin to critical ViewSets** (see list above)
2. **Grant permissions to managers**:
   ```python
   # In Django admin or shell
   user.user_permissions.add(
       Permission.objects.get(codename='view_subordinate_data')
   )
   ```
3. **Test access levels** with different user roles
4. **Update serializers** (optional) to include hierarchy info:
   ```python
   class FarmerSerializer(serializers.ModelSerializer):
       created_by_name = serializers.CharField(source='created_by.get_full_name', read_only=True)
       created_by_designation = serializers.CharField(source='created_by.sales_profile.designation.name', read_only=True)
   ```

---

## 🔒 Security Notes

- **Superusers** bypass all filtering (full access)
- **Permissions are checked** on every request
- **Hierarchy is recursive** - managers see entire sub-tree
- **Non-sales users** are isolated (no cross-access)
- **CEO designation** automatically grants full access

---

## 📝 Summary

✅ **Fully Implemented:**
- Database models (DesignationModel, manager field)
- Hierarchy methods (get_all_subordinates, etc.)
- Custom permissions (4 permissions created)
- Permission classes (in hierarchy_permissions.py)
- API endpoints (my-team, my-hierarchy, etc.)
- Admin interface (hierarchy columns, actions)
- Filtering utilities (HierarchyFilterMixin)

🟡 **Needs Implementation:**
- Apply HierarchyFilterMixin to ViewSets
- Assign permissions to manager-level users

❌ **NOT Needed:**
- Hierarchy Levels model
- User Hierarchies model
- Any additional database tables

