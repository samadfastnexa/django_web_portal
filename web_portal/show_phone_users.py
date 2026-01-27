"""
Script to find a user with phone number and show login details
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'web_portal.settings')
django.setup()

from accounts.models import User, SalesStaffProfile

print("Users with phone numbers that can login:")
print("=" * 70)

profiles = SalesStaffProfile.objects.exclude(
    phone_number__isnull=True
).exclude(
    phone_number=''
).select_related('user')

for profile in profiles[:15]:
    if profile.user and profile.user.is_active:
        print(f"\n📱 Phone: {profile.phone_number}")
        print(f"   Email: {profile.user.email}")
        print(f"   Username: {profile.user.username}")
        print(f"   Active: {profile.user.is_active}")
        print(f"   Employee Code: {profile.employee_code or 'N/A'}")
        
print("\n" + "=" * 70)
print("To test login, use one of these phone numbers with its user's password")
print("\nExample API request:")
print("""
{
  "phone_number": "03001234001",
  "password": "your_password_here"
}
""")
