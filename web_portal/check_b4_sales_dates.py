"""Quick script to check B4_SALES_TARGET date ranges"""
import os
from hdbcli import dbapi

# Set environment variables for SAP HANA connection
pwd = os.environ.get('HANA_PASSWORD', '')
host = os.environ.get('HANA_HOST', '')
port = int(os.environ.get('HANA_PORT', '30015'))
user = os.environ.get('HANA_USER', '')

print(f"Connecting to {host}:{port} as {user}...")

conn = dbapi.connect(address=host, port=port, user=user, password=pwd)
cursor = conn.cursor()

# Set schema
cursor.execute('SET SCHEMA "4B-AGRI_LIVE"')

# Check if table exists and get date ranges
cursor.execute("""
SELECT 
    COUNT(*) as total_rows,
    MIN(F_REFDATE) as earliest_from_date,
    MAX(T_REFDATE) as latest_to_date,
    COUNT(DISTINCT TerritoryId) as territories,
    COUNT(DISTINCT EmpId) as employees
FROM B4_SALES_TARGET
""")

result = cursor.fetchone()
print(f"\nB4_SALES_TARGET Summary:")
print(f"  Total rows: {result[0]}")
print(f"  Date range: {result[1]} to {result[2]}")
print(f"  Unique territories: {result[3]}")
print(f"  Unique employees: {result[4]}")

# Get sample data
cursor.execute("""
SELECT TOP 10
    F_REFDATE, T_REFDATE, TerritoryId, EmpId, Sales_Target, DocTotal
FROM B4_SALES_TARGET
ORDER BY F_REFDATE DESC
""")

print(f"\nSample data (latest 10 rows):")
for row in cursor.fetchall():
    print(f"  {row}")

conn.close()
print("\n✓ Done")
