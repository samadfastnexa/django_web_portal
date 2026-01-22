"""
Create a CEO sales profile (vacant or with user)
"""
import os
import django

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'web_portal.settings')
django.setup()

from accounts.models import SalesStaffProfile, Designation
from django.contrib.auth import get_user_model

User = get_user_model()

print("=" * 60)
print("CREATE CEO SALES PROFILE")
print("=" * 60)

# Find CEO designation
ceo_designations = Designation.objects.filter(name__icontains='ceo')
print(f"\nFound {ceo_designations.count()} CEO designations:")
for d in ceo_designations:
    print(f"  - {d.name} (code: {d.code})")

if not ceo_designations.exists():
    print("\n❌ No CEO designation found!")
    print("Please create a CEO designation first in the admin panel.")
    exit()

ceo_designation = ceo_designations.first()
print(f"\nUsing designation: {ceo_designation.name}")

# Check if CEO profile already exists
existing_ceo = SalesStaffProfile.objects.filter(designation=ceo_designation)
if existing_ceo.exists():
    print(f"\n⚠️  CEO profile already exists:")
    for profile in existing_ceo:
        user_info = f"{profile.user.username}" if profile.user else "VACANT"
        print(f"  - {user_info} (ID: {profile.id}, Vacant: {profile.is_vacant})")
    
    response = input("\nDo you want to create another CEO profile? (yes/no): ")
    if response.lower() != 'yes':
        print("Exiting...")
        exit()

print("\n" + "=" * 60)
print("Choose an option:")
print("1. Create VACANT CEO position (for hierarchy structure)")
print("2. Assign existing user as CEO")
print("=" * 60)

choice = input("Enter choice (1 or 2): ").strip()

if choice == '1':
    # Create vacant CEO profile
    profile = SalesStaffProfile.objects.create(
        designation=ceo_designation,
        is_vacant=True,
        employee_code='CEO-VACANT',
        manager=None  # Top of hierarchy
    )
    print(f"\n✅ Created VACANT CEO profile (ID: {profile.id})")
    print(f"   Designation: {profile.designation.name}")
    print(f"   This can serve as the top of your organization hierarchy.")
    print(f"\n   To assign someone later:")
    print(f"   1. Go to Admin → Sales Staff Profiles")
    print(f"   2. Edit this profile (ID: {profile.id})")
    print(f"   3. Assign a user and set is_vacant=False")

elif choice == '2':
    # List available users
    users = User.objects.filter(is_staff=True)
    print(f"\nAvailable staff users:")
    for i, user in enumerate(users, 1):
        has_profile = SalesStaffProfile.objects.filter(user=user).exists()
        status = "✅ Already has profile" if has_profile else "Available"
        print(f"  {i}. {user.username} ({user.email}) - {status}")
    
    user_num = input(f"\nSelect user number (1-{users.count()}): ").strip()
    try:
        selected_user = users[int(user_num) - 1]
        
        # Check if user already has a profile
        if SalesStaffProfile.objects.filter(user=selected_user).exists():
            print(f"\n⚠️  {selected_user.username} already has a sales profile!")
            response = input("Create anyway? (yes/no): ")
            if response.lower() != 'yes':
                print("Exiting...")
                exit()
        
        employee_code = input(f"Enter employee code (e.g., CEO-001): ").strip() or "CEO-001"
        
        profile = SalesStaffProfile.objects.create(
            user=selected_user,
            designation=ceo_designation,
            is_vacant=False,
            employee_code=employee_code,
            manager=None  # Top of hierarchy
        )
        
        print(f"\n✅ Created CEO profile for {selected_user.username}")
        print(f"   ID: {profile.id}")
        print(f"   Designation: {profile.designation.name}")
        print(f"   Employee Code: {profile.employee_code}")
        
    except (ValueError, IndexError):
        print("Invalid selection!")
        exit()

else:
    print("Invalid choice!")
    exit()

print("\n" + "=" * 60)
print("NEXT STEPS:")
print("=" * 60)
print("1. Create or edit other sales profiles")
print("2. Set their 'Manager' field to this CEO profile")
print("3. Refresh the organogram page to see the hierarchy")
print("\nTo set managers:")
print("  Admin → Sales Staff Profiles → Edit profile → Manager field")
print("=" * 60)
