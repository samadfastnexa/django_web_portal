"""
Quick test to verify farmer login with phone number
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'web_portal.settings')
django.setup()

from django.contrib.auth import authenticate
from farmers.models import Farmer

print("\n" + "="*70)
print("🧪 FARMER PHONE LOGIN TEST")
print("="*70 + "\n")

# Get a farmer with user account
farmer = Farmer.objects.filter(user__isnull=False).first()

if farmer:
    print(f"Testing farmer: {farmer.name} (ID: {farmer.farmer_id})")
    print(f"Phone number: {farmer.primary_phone}")
    print(f"Username: {farmer.user.username}")
    print(f"CNIC: {farmer.cnic}")
    
    # Try to authenticate with phone number
    test_password = 'farmer1234'  # Default password for farmers without CNIC
    if farmer.cnic and len(farmer.cnic) >= 4:
        test_password = farmer.cnic[-4:]
    
    print(f"\n🔐 Testing authentication:")
    print(f"   Phone: {farmer.primary_phone}")
    print(f"   Password: {test_password}")
    
    user = authenticate(username=farmer.primary_phone, password=test_password)
    
    if user:
        print(f"\n✅ SUCCESS! Farmer can login with phone number")
        print(f"   Authenticated User ID: {user.id}")
        print(f"   Email: {user.email}")
        print(f"   Name: {user.first_name} {user.last_name}")
    else:
        print(f"\n❌ FAILED! Authentication did not work")
        print(f"   Trying to check password...")
        if farmer.user.check_password(test_password):
            print(f"   ✓ Password is correct")
        else:
            print(f"   ✗ Password is incorrect")
else:
    print("❌ No farmers with user accounts found")
    print("\nRun this command first:")
    print("   python manage.py link_farmers_to_users")

print("\n" + "="*70)
print("📱 LOGIN EXAMPLES FOR API:")
print("="*70)

if farmer:
    print(f"""
Farmer Login (Phone):
{{
  "phone_number": "{farmer.primary_phone}",
  "password": "{test_password}"
}}

Farmer Login (Email):
{{
  "email": "{farmer.user.email}",
  "password": "{test_password}"
}}
""")

print("Test these at: http://localhost:8000/swagger/")
print("Or: http://localhost:8000/api/login/")
print("="*70 + "\n")
