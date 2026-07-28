"""
Script to find a user with phone number and show login details
"""

# --- bootstrap: this script lives in <app>/scripts/, so locate the project ---
import os as _os
import sys as _sys
from pathlib import Path as _P

PROJECT_DIR = _P(__file__).resolve().parents[2]   # web_portal/ (holds manage.py)
REPO_DIR = PROJECT_DIR.parent                     # django_web_portal/ (holds .env)
if str(PROJECT_DIR) not in _sys.path:
    _sys.path.insert(0, str(PROJECT_DIR))
_os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'web_portal.settings')
# --- end bootstrap ---

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
