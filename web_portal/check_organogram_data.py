"""
Check if there's data for the organogram
"""
import os
import django

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'web_portal.settings')
django.setup()

from accounts.models import SalesStaffProfile

print("Checking organogram data...")
print("=" * 50)

# Get all sales profiles
total_profiles = SalesStaffProfile.objects.count()
print(f"Total Sales Profiles: {total_profiles}")

# Get active profiles
active_profiles = SalesStaffProfile.objects.filter(is_vacant=False).count()
print(f"Active (non-vacant) Profiles: {active_profiles}")

# Get top-level managers
top_level = SalesStaffProfile.objects.filter(is_vacant=False, manager__isnull=True)
print(f"Top-level managers: {top_level.count()}")

if top_level.exists():
    print("\nTop-level managers:")
    for profile in top_level:
        user_name = f"{profile.user.first_name} {profile.user.last_name}" if profile.user else "Vacant"
        designation = profile.designation.name if profile.designation else "N/A"
        subordinates = profile.subordinates.filter(is_vacant=False).count()
        print(f"  - {user_name} ({designation}) - {subordinates} subordinates")

# Get profiles with managers
with_manager = SalesStaffProfile.objects.filter(is_vacant=False, manager__isnull=False).count()
print(f"\nProfiles with managers: {with_manager}")

# Show sample hierarchy
if top_level.exists():
    print("\nSample hierarchy structure:")
    for profile in top_level[:3]:  # Show first 3 top-level managers
        print(f"\n{profile.user.first_name if profile.user else 'Vacant'}")
        subordinates = profile.subordinates.filter(is_vacant=False)[:3]
        for sub in subordinates:
            sub_name = f"{sub.user.first_name} {sub.user.last_name}" if sub.user else "Vacant"
            print(f"  └─ {sub_name}")
            
print("\n" + "=" * 50)
