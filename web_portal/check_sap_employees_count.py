"""
Check total employees (sales staff) count in SAP HANA
"""
from hdbcli import dbapi
import os
from dotenv import load_dotenv

load_dotenv()

conn = dbapi.connect(
    address=os.getenv('HANA_HOST'),
    port=int(os.getenv('HANA_PORT')),
    user=os.getenv('HANA_USER'),
    password=os.getenv('HANA_PASSWORD')
)

cursor = conn.cursor()

# Check both company schemas
schemas = ['4B-BIO_APP', '4B-ORANG_APP']

for schema in schemas:
    print(f"\n{'='*60}")
    print(f"Schema: {schema}")
    print(f"{'='*60}")
    
    cursor.execute(f'SET SCHEMA "{schema}"')
    
    # OHEM is the Employee Master Data table
    
    # Total Employees
    cursor.execute('SELECT COUNT(*) FROM "OHEM"')
    total_employees = cursor.fetchone()[0]
    print(f"\nTotal Employees: {total_employees}")
    
    # Active Employees
    cursor.execute('SELECT COUNT(*) FROM "OHEM" WHERE "Active" = \'Y\'')
    active_employees = cursor.fetchone()[0]
    print(f"Active Employees: {active_employees}")
    
    # Inactive Employees
    cursor.execute('SELECT COUNT(*) FROM "OHEM" WHERE "Active" = \'N\'')
    inactive_employees = cursor.fetchone()[0]
    print(f"Inactive Employees: {inactive_employees}")
    
    # Check available columns in OHEM
    print(f"\n--- Sample Employee Data ---")
    cursor.execute('''
        SELECT 
            "empID",
            "firstName",
            "middleName",
            "lastName",
            "jobTitle",
            "dept",
            "position",
            "email",
            "mobile",
            "homeTel",
            "officeExt",
            "Active",
            "startDate",
            "U_TERR",
            "U_HOD"
        FROM "OHEM" 
        WHERE "Active" = 'Y'
        LIMIT 5
    ''')
    
    employees = cursor.fetchall()
    for emp in employees:
        print(f"\nEmployee ID: {emp[0]}")
        print(f"  Name: {emp[1]} {emp[2] or ''} {emp[3]}")
        print(f"  Job Title: {emp[4]}")
        print(f"  Department: {emp[5]}")
        print(f"  Position: {emp[6]}")
        print(f"  Email: {emp[7]}")
        print(f"  Mobile: {emp[8]}")
        print(f"  Home Tel: {emp[9]}")
        print(f"  Office Ext: {emp[10]}")
        print(f"  Active: {'Yes' if emp[11] == 'Y' else 'No'}")
        print(f"  Start Date: {emp[12]}")
        print(f"  Territory: {emp[13]}")
        print(f"  HOD: {emp[14]}")
    
    # Check for sales-related employees
    print(f"\n--- Sales Department Employees ---")
    cursor.execute('''
        SELECT COUNT(*) 
        FROM "OHEM" 
        WHERE "dept" LIKE '%Sales%' OR "position" LIKE '%Sales%' OR "jobTitle" LIKE '%Sales%'
    ''')
    sales_employees = cursor.fetchone()[0]
    print(f"Sales-related Employees: {sales_employees}")

cursor.close()
conn.close()

print(f"\n{'='*60}")
print("Check complete!")
print(f"{'='*60}")
