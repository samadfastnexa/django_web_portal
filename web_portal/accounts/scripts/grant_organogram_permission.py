"""
Grant view_organogram permission to a user
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

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'web_portal.settings')
django.setup()

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission

User = get_user_model()

print("Granting view_organogram permission...")
print("=" * 50)

# Get all superusers and staff users
users = User.objects.filter(is_staff=True)
print(f"Found {users.count()} staff users:")

for user in users:
    print(f"\n  User: {user.username} ({user.email})")
    print(f"  Superuser: {user.is_superuser}")
    print(f"  Has view_organogram: {user.has_perm('accounts.view_organogram')}")

# Get the permission
try:
    permission = Permission.objects.get(
        content_type__app_label='accounts',
        codename='view_organogram'
    )
    print(f"\n✓ Permission exists: {permission}")
    
    # Grant to all staff users
    print("\nGranting permission to all staff users...")
    for user in users:
        if not user.is_superuser:  # Superusers already have all permissions
            user.user_permissions.add(permission)
            print(f"  ✓ Granted to {user.username}")
        else:
            print(f"  ⊙ {user.username} is superuser (already has permission)")
    
    print("\n" + "=" * 50)
    print("DONE! Refresh your admin page to see the Organization section.")
    
except Permission.DoesNotExist:
    print("\n✗ ERROR: view_organogram permission doesn't exist!")
    print("  Run: python manage.py migrate accounts")
    print("=" * 50)
