"""
Quick script to check if phone number exists in database
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'web_portal.settings')
django.setup()

from accounts.models import User, SalesStaffProfile

# Check for the phone number
phone = "03224846103"
print(f"Searching for phone number: {phone}")
print("-" * 50)

# Search in SalesStaffProfile
profiles = SalesStaffProfile.objects.filter(phone_number=phone)
print(f"Found {profiles.count()} profile(s) with this phone number")

for profile in profiles:
    print(f"\nProfile ID: {profile.id}")
    print(f"Employee Code: {profile.employee_code}")
    print(f"Phone Number: {profile.phone_number}")
    print(f"User: {profile.user}")
    if profile.user:
        print(f"  - User ID: {profile.user.id}")
        print(f"  - Email: {profile.user.email}")
        print(f"  - Username: {profile.user.username}")
        print(f"  - Is Active: {profile.user.is_active}")
        print(f"  - Is Sales Staff: {profile.user.is_sales_staff}")
        
        # Test password
        print(f"\nTesting authentication...")
        from django.contrib.auth import authenticate
        user = authenticate(username=phone, password="Ab123456789!")
        if user:
            print(f"✅ Authentication SUCCESSFUL")
        else:
            print(f"❌ Authentication FAILED")
            # Try to check password manually
            if profile.user.check_password("Ab123456789!"):
                print(f"  - Password is CORRECT")
                print(f"  - Issue might be with the backend")
            else:
                print(f"  - Password is INCORRECT")
    else:
        print(f"  - ⚠️ No user assigned to this profile!")

# Also check all phone numbers in database
print("\n" + "=" * 50)
print("All phone numbers in database:")
all_profiles = SalesStaffProfile.objects.exclude(phone_number__isnull=True).exclude(phone_number='')
for p in all_profiles[:10]:  # Show first 10
    print(f"  {p.phone_number} -> {p.user.email if p.user else 'NO USER'}")
