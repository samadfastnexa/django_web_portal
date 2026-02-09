"""
Quick diagnostic script to check B4_SALES_TARGET table structure and data
"""
import os
import sys
import django

# Add the project directory to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'web_portal.settings')
django.setup()

from django.conf import settings
from hdbcli import dbapi

# Get SAP HANA connection details from settings
hana_settings = settings.DATABASES.get('sap_hana_4b_agri_live', {})
host = hana_settings.get('HOST')
port = hana_settings.get('PORT', 30015)
user = hana_settings.get('USER')
password = hana_settings.get('PASSWORD')

print(f"Connecting to SAP HANA at {host}:{port}...")

try:
    conn = dbapi.connect(
        address=host,
        port=port,
        user=user,
        password=password
    )
    cursor = conn.cursor()
    
    # Check if B4_SALES_TARGET table exists
    print("\n1. Checking if B4_SALES_TARGET table exists...")
    cursor.execute("""
        SELECT COUNT(*) 
        FROM SYS.TABLES 
        WHERE SCHEMA_NAME = 'FOURB' 
        AND TABLE_NAME = 'B4_SALES_TARGET'
    """)
    exists = cursor.fetchone()[0]
    print(f"   Table exists: {exists > 0}")
    
    if exists == 0:
        print("\n   ERROR: B4_SALES_TARGET table does not exist!")
        conn.close()
        sys.exit(1)
    
    # Get table structure
    print("\n2. Getting B4_SALES_TARGET table structure...")
    cursor.execute("""
        SELECT COLUMN_NAME, DATA_TYPE_NAME 
        FROM SYS.TABLE_COLUMNS 
        WHERE SCHEMA_NAME = 'FOURB' 
        AND TABLE_NAME = 'B4_SALES_TARGET'
        ORDER BY POSITION
    """)
    columns = cursor.fetchall()
    print("   Columns:")
    for col in columns:
        print(f"   - {col[0]}: {col[1]}")
    
    # Get total row count
    print("\n3. Checking total row count...")
    cursor.execute("SELECT COUNT(*) FROM B4_SALES_TARGET")
    total_rows = cursor.fetchone()[0]
    print(f"   Total rows: {total_rows}")
    
    if total_rows == 0:
        print("\n   WARNING: Table is empty!")
        conn.close()
        sys.exit(0)
    
    # Get sample data
    print("\n4. Getting sample data (first 5 rows)...")
    cursor.execute("""
        SELECT TOP 5 * 
        FROM B4_SALES_TARGET
    """)
    sample_rows = cursor.fetchall()
    print(f"   Sample data ({len(sample_rows)} rows):")
    for i, row in enumerate(sample_rows, 1):
        print(f"   Row {i}: {row}")
    
    # Check date range
    print("\n5. Checking date range in table...")
    cursor.execute("""
        SELECT 
            MIN(F_REFDATE) as min_from_date,
            MAX(T_REFDATE) as max_to_date
        FROM B4_SALES_TARGET
    """)
    date_range = cursor.fetchone()
    print(f"   Date range: {date_range[0]} to {date_range[1]}")
    
    # Check data for today
    from datetime import date
    today = date.today()
    print(f"\n6. Checking data for today ({today})...")
    cursor.execute("""
        SELECT COUNT(*) 
        FROM B4_SALES_TARGET
        WHERE F_REFDATE <= ? AND T_REFDATE >= ?
    """, (today, today))
    today_count = cursor.fetchone()[0]
    print(f"   Rows matching today: {today_count}")
    
    # Check territories
    print("\n7. Checking unique territories...")
    cursor.execute("""
        SELECT COUNT(DISTINCT TerritoryId) 
        FROM B4_SALES_TARGET
    """)
    territory_count = cursor.fetchone()[0]
    print(f"   Unique territories: {territory_count}")
    
    # Check employees
    print("\n8. Checking unique employees...")
    cursor.execute("""
        SELECT COUNT(DISTINCT EmpId) 
        FROM B4_SALES_TARGET
    """)
    emp_count = cursor.fetchone()[0]
    print(f"   Unique employees: {emp_count}")
    
    print("\n✓ Diagnostic complete!")
    
    conn.close()
    
except Exception as e:
    print(f"\n✗ Error: {e}")
    import traceback
    traceback.print_exc()
