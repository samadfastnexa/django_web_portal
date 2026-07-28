"""
Map remaining designations to DesignationModel IDs
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

from accounts.models import SalesStaffProfile, DesignationModel
from django.db import connection

print("🔄 Mapping remaining designations...")

# Get all designation IDs
designation_map = {d.code: d.id for d in DesignationModel.objects.all()}

# Define manual mappings for non-exact matches
manual_mappings = {
    'sales manager': designation_map.get('NSM'),  # Map to National Sales Manager
    'Regional Sales Leader': designation_map.get('RSL'),
    'Deputy Regional Sales Leader': designation_map.get('DRSL'),
    'Zonal Manager': designation_map.get('ZM'),
    'Distribution Point Leader': designation_map.get('DPL'),
    'Senior Product Leader': designation_map.get('SR_PL'),
    'Product Leader': designation_map.get('PL'),
    'Senior Field Sales Manager': designation_map.get('SR_FSM'),
    'Field Sales Manager': designation_map.get('FSM'),
    'Senior Multi Territory Officer': designation_map.get('SR_MTO'),
    'Multi Territory Officer': designation_map.get('MTO'),
}

print(f"\n📋 Manual mappings:")
for old_value, new_id in manual_mappings.items():
    if new_id:
        print(f"  '{old_value}' → ID {new_id}")

# Get all unique designation values currently in database
with connection.cursor() as cursor:
    cursor.execute("""
        SELECT DISTINCT designation_id 
        FROM accounts_salesstaffprofile 
        WHERE designation_id NOT REGEXP '^[0-9]+$'
    """)
    rows = cursor.fetchall()
    print(f"\n📊 Non-numeric designation values in database:")
    for row in rows:
        print(f"  '{row[0]}'")

# Update with manual mappings
print(f"\n🔄 Applying manual mappings...")
with connection.cursor() as cursor:
    updated_count = 0
    for old_value, new_id in manual_mappings.items():
        if new_id:
            cursor.execute(
                "UPDATE accounts_salesstaffprofile SET designation_id = %s WHERE designation_id = %s",
                [new_id, old_value]
            )
            count = cursor.rowcount
            if count > 0:
                print(f"  ✅ Updated {count} record(s) from '{old_value}' to ID {new_id}")
                updated_count += count

print(f"\n✅ Updated {updated_count} records with manual mappings.")

# Check for any remaining non-numeric values
with connection.cursor() as cursor:
    cursor.execute("""
        SELECT DISTINCT designation_id 
        FROM accounts_salesstaffprofile 
        WHERE designation_id NOT REGEXP '^[0-9]+$'
    """)
    remaining = cursor.fetchall()
    if remaining:
        print(f"\n⚠️ Still have {len(remaining)} non-numeric designation value(s):")
        for row in remaining:
            cursor.execute(
                "SELECT COUNT(*) FROM accounts_salesstaffprofile WHERE designation_id = %s",
                [row[0]]
            )
            count = cursor.fetchone()[0]
            print(f"  '{row[0]}' ({count} records) - needs manual assignment")
    else:
        print(f"\n✅ All designations successfully migrated!")

print("\n✅ Done!")
