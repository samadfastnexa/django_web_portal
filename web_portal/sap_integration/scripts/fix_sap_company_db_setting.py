"""
Fix SAP_COMPANY_DB setting to support multiple companies.
Converts from string to dictionary format.
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
import sys
import django
import json

# Setup Django
sys.path.insert(0, str(PROJECT_DIR))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'web_portal.settings')
django.setup()

from preferences.models import Setting

print("\n=== FIXING SAP_COMPANY_DB SETTING ===\n")

try:
    setting = Setting.objects.get(slug='SAP_COMPANY_DB')
    old_value = setting.value
    print(f"Current value: {old_value}")
    print(f"Current type: {type(old_value)}")
    
    # Create the new dictionary mapping
    new_value = {
        "4B-BIO": "4B-BIO_APP",
        "4B-ORANG": "4B-ORANG_APP"
    }
    
    # Update the setting
    setting.value = new_value
    setting.save()
    
    print(f"\n✅ Updated to: {json.dumps(new_value, indent=2)}")
    print("\nThe setting now maps:")
    print("  - Company key '4B-BIO' → CompanyDB '4B-BIO_APP'")
    print("  - Company key '4B-ORANG' → CompanyDB '4B-ORANG_APP'")
    
except Setting.DoesNotExist:
    print("❌ SAP_COMPANY_DB setting not found!")
    print("\nCreating new setting...")
    new_value = {
        "4B-BIO": "4B-BIO_APP",
        "4B-ORANG": "4B-ORANG_APP"
    }
    Setting.objects.create(
        slug='SAP_COMPANY_DB',
        value=new_value
    )
    print(f"✅ Created with value: {json.dumps(new_value, indent=2)}")

print("\n=== DONE ===\n")
print("Now restart your Django server and test again with ?database=4B-ORANG_APP")
