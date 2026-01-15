# Custom Permissions Documentation

This file documents all custom permissions added to the AgriGenie system.
These permissions can be assigned to roles in the Django admin.

## Permission Format
Permissions follow Django's format: `app_label.codename`

## Module-wise Permissions

### 1. HANA Connect (sap_integration app)
- `sap_integration.access_hana_connect` - Can access HANA Connect dashboard
- `sap_integration.view_policy_balance` - Can view policy balance reports
- `sap_integration.view_customer_data` - Can view customer data
- `sap_integration.view_item_master` - Can view item master list
- `sap_integration.view_sales_reports` - Can view sales vs achievement reports
- `sap_integration.sync_policies` - Can sync policies from SAP
- `sap_integration.post_to_sap` - Can post data to SAP

### 2. Field Advisory (FieldAdvisoryService app)
- `FieldAdvisoryService.manage_dealers` - Can add/edit/delete dealers
- `FieldAdvisoryService.approve_dealer_requests` - Can approve dealer requests
- `FieldAdvisoryService.view_dealer_reports` - Can view dealer reports

### 3. Crop Management (crop_management app)
- `crop_management.manage_crops` - Can add/edit/delete crops
- `crop_management.manage_varieties` - Can manage crop varieties
- `crop_management.manage_research` - Can manage crop research data
- `crop_management.manage_farming_practices` - Can manage farming practices
- `crop_management.view_yield_analytics` - Can view yield analytics

### 4. Crop Manage (crop_manage app)
- `crop_manage.manage_trials` - Can add/edit/delete field trials
- `crop_manage.manage_treatments` - Can manage trial treatments
- `crop_manage.manage_products` - Can manage trial products
- `crop_manage.view_trial_results` - Can view trial results

### 5. Farmers (farmers app)
- `farmers.manage_farmers` - Can add/edit/delete farmer records
- `farmers.view_farmer_reports` - Can view farmer statistics
- `farmers.export_farmer_data` - Can export farmer data

### 6. Farm Management (farm app)
- `farm.manage_farms` - Can add/edit/delete farms
- `farm.manage_plots` - Can manage farm plots
- `farm.view_farm_analytics` - Can view farm analytics

### 7. Attendance (attendance app)
- `attendance.manage_attendance` - Can mark/edit attendance
- `attendance.approve_leave_requests` - Can approve leave requests
- `attendance.view_attendance_reports` - Can view attendance reports
- `attendance.manage_attendance_requests` - Can manage attendance requests

### 8. Complaints (complaints app)
- `complaints.manage_complaints` - Can add/edit/resolve complaints
- `complaints.view_complaint_reports` - Can view complaint reports
- `complaints.assign_complaints` - Can assign complaints to staff

### 9. Meetings (farmerMeetingDataEntry app)
- `farmerMeetingDataEntry.manage_meetings` - Can add/edit meetings
- `farmerMeetingDataEntry.manage_field_days` - Can manage field days
- `farmerMeetingDataEntry.view_meeting_reports` - Can view meeting reports

### 10. KindWise (kindwise app)
- `kindwise.use_plant_identification` - Can use plant identification API
- `kindwise.view_identification_history` - Can view identification history

### 11. User Management (accounts app)
- `accounts.manage_users` - Can add/edit users
- `accounts.manage_roles` - Can manage roles and permissions
- `accounts.manage_sales_staff` - Can manage sales staff profiles
- `accounts.view_user_reports` - Can view user reports

### 12. General Ledger (general_ledger app)
- `general_ledger.view_ledger` - Can view general ledger entries
- `general_ledger.export_ledger` - Can export ledger data

### 13. Analytics (analytics app)
- `analytics.view_dashboard` - Can access analytics dashboard
- `analytics.view_sales_analytics` - Can view sales analytics
- `analytics.view_farmer_analytics` - Can view farmer analytics
- `analytics.export_analytics` - Can export analytics reports

### 14. Settings (preferences app)
- `preferences.manage_settings` - Can manage system settings
- `preferences.view_settings` - Can view system settings

## Usage in Code
Check permission in views:
```python
if request.user.has_perm('sap_integration.access_hana_connect'):
    # Allow access
    pass
```

Check permission in templates:
```django
{% if perms.sap_integration.access_hana_connect %}
    <button>Access HANA Connect</button>
{% endif %}
```

Assign permission to role:
```python
from django.contrib.auth.models import Permission
permission = Permission.objects.get(codename='access_hana_connect')
role.permissions.add(permission)
```
