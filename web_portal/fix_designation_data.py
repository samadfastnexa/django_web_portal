"""
Script to migrate existing SalesStaffProfile designation data
Run with: python manage.py shell < fix_designation_data.py
"""
from accounts.models import SalesStaffProfile, DesignationModel
from django.db import connection

print("🔄 Starting designation data migration...")

# Get all designation mappings
designation_map = {d.code: d.id for d in DesignationModel.objects.all()}
print(f"\n📋 Available designation codes and their IDs:")
for code, pk in designation_map.items():
    print(f"  {code} → ID {pk}")

# Check current state - use designation_id which is the actual database column name
with connection.cursor() as cursor:
    # First let's see what the column is called
    cursor.execute("SHOW COLUMNS FROM accounts_salesstaffprofile LIKE 'designation%'")
    columns = cursor.fetchall()
    print(f"\n📊 Designation-related columns in database:")
    for col in columns:
        print(f"  Column: {col[0]}, Type: {col[1]}, Null: {col[2]}, Key: {col[3]}")
    
    # Now check the data
    cursor.execute("SELECT id, designation_id FROM accounts_salesstaffprofile LIMIT 5")
    rows = cursor.fetchall()
    print(f"\n📊 Sample data (first 5 rows):")
    for row in rows:
        print(f"  Profile ID {row[0]}: designation_id = '{row[1]}'")

# Update using raw SQL with the correct column name
print(f"\n🔄 Updating records...")
with connection.cursor() as cursor:
    updated_count = 0
    for code, designation_id in designation_map.items():
        # The column in database is designation_id, and it contains string values like 'CEO'
        cursor.execute(
            "UPDATE accounts_salesstaffprofile SET designation_id = %s WHERE designation_id = %s",
            [designation_id, code]
        )
        count = cursor.rowcount
        if count > 0:
            print(f"  ✅ Updated {count} record(s) from '{code}' to ID {designation_id}")
            updated_count += count

print(f"\n✅ Migration complete! Updated {updated_count} total records.")

# Verify
with connection.cursor() as cursor:
    cursor.execute("SELECT id, designation_id FROM accounts_salesstaffprofile LIMIT 5")
    rows = cursor.fetchall()
    print(f"\n📊 After migration (first 5 rows):")
    for row in rows:
        print(f"  Profile ID {row[0]}: designation_id = {row[1]}")

print("\n✅ Done!")
