"""
Script to migrate existing SalesStaffProfile records to use DesignationModel ForeignKey
Run with: python manage.py shell < migrate_existing_designations.py
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

print("🔄 Migrating existing designation data...")

# First, let's see what we have in the database
with connection.cursor() as cursor:
    cursor.execute("SELECT id, designation FROM accounts_salesstaffprofile LIMIT 10")
    rows = cursor.fetchall()
    print(f"\n📊 Sample of existing data (first 10 rows):")
    for row in rows:
        print(f"  ID {row[0]}: designation = '{row[1]}'")

# Get all designation mappings
designation_map = {d.code: d.id for d in DesignationModel.objects.all()}
print(f"\n📋 Available designation mappings:")
for code, pk in designation_map.items():
    print(f"  {code} → ID {pk}")

# Update records using raw SQL to avoid Django's type checking
with connection.cursor() as cursor:
    updated_count = 0
    for code, designation_id in designation_map.items():
        cursor.execute(
            "UPDATE accounts_salesstaffprofile SET designation = %s WHERE designation = %s",
            [designation_id, code]
        )
        count = cursor.rowcount
        if count > 0:
            print(f"  ✅ Updated {count} record(s) from '{code}' to ID {designation_id}")
            updated_count += count

print(f"\n✅ Migration complete! Updated {updated_count} total records.")

# Verify the migration
with connection.cursor() as cursor:
    cursor.execute("SELECT id, designation FROM accounts_salesstaffprofile LIMIT 10")
    rows = cursor.fetchall()
    print(f"\n📊 After migration (first 10 rows):")
    for row in rows:
        print(f"  ID {row[0]}: designation = {row[1]} (now an integer ID)")

print("\n✅ Done!")
