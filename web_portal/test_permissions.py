"""
Quick test to verify all custom permissions were created successfully
Run with: python manage.py shell < test_permissions.py
"""

from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType

print("\n" + "="*60)
print("🔍 CHECKING ALL CUSTOM PERMISSIONS")
print("="*60 + "\n")

# Expected permissions from permissions_config.py
expected_permissions = {
    'sap_integration': [
        'access_hana_connect', 'view_policy_balance', 'view_customer_data',
        'view_item_master', 'view_sales_reports', 'sync_policies',
        'post_to_sap', 'manage_policies'
    ],
    'FieldAdvisoryService': [
        'manage_dealers', 'view_dealer_reports', 'approve_dealer_requests',
        'manage_companies', 'manage_regions', 'manage_zones', 'manage_territories'
    ],
    'crop_management': [
        'manage_crops', 'view_crop_analytics', 'manage_varieties',
        'manage_yield_data', 'view_yield_analytics', 'manage_farming_practices',
        'manage_research'
    ],
    'crop_manage': [
        'manage_trials', 'view_trial_results', 'manage_treatments', 'manage_products'
    ],
    'farmers': ['manage_farmers', 'view_farmer_reports', 'export_farmer_data'],
    'farm': ['manage_farms', 'view_farm_analytics'],
    'attendance': [
        'manage_attendance', 'view_attendance_reports',
        'manage_attendance_requests', 'approve_leave_requests'
    ],
    'complaints': ['manage_complaints', 'view_complaint_reports', 'assign_complaints'],
    'farmerMeetingDataEntry': [
        'manage_meetings', 'view_meeting_reports', 'manage_field_days'
    ],
    'kindwise': ['use_plant_identification', 'view_identification_history'],
    'accounts': ['manage_users', 'view_user_reports', 'manage_roles', 'manage_sales_staff'],
    'preferences': ['manage_settings', 'view_settings']
}

total_expected = sum(len(perms) for perms in expected_permissions.values())
total_found = 0
missing = []

for app_label, codenames in expected_permissions.items():
    print(f"\n📦 {app_label}:")
    for codename in codenames:
        try:
            perm = Permission.objects.get(codename=codename)
            print(f"  ✅ {codename} - {perm.name}")
            total_found += 1
        except Permission.DoesNotExist:
            print(f"  ❌ {codename} - NOT FOUND")
            missing.append(f"{app_label}.{codename}")

print("\n" + "="*60)
print(f"📊 SUMMARY:")
print(f"  Expected: {total_expected} permissions")
print(f"  Found:    {total_found} permissions")
print(f"  Missing:  {len(missing)} permissions")

if missing:
    print(f"\n❌ Missing permissions:")
    for m in missing:
        print(f"  - {m}")
else:
    print(f"\n✅ ALL PERMISSIONS CREATED SUCCESSFULLY!")

print("="*60 + "\n")
