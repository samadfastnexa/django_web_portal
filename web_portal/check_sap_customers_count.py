"""
Check total customers count in SAP HANA
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
    
    # OCRD is the Business Partners master table (Customers, Vendors, Leads)
    # CardType: C = Customer, S = Supplier, L = Lead
    
    # Total Business Partners
    cursor.execute('SELECT COUNT(*) FROM "OCRD"')
    total_bp = cursor.fetchone()[0]
    print(f"\nTotal Business Partners: {total_bp}")
    
    # Customers only
    cursor.execute('SELECT COUNT(*) FROM "OCRD" WHERE "CardType" = \'C\'')
    total_customers = cursor.fetchone()[0]
    print(f"Total Customers: {total_customers}")
    
    # Suppliers
    cursor.execute('SELECT COUNT(*) FROM "OCRD" WHERE "CardType" = \'S\'')
    total_suppliers = cursor.fetchone()[0]
    print(f"Total Suppliers: {total_suppliers}")
    
    # Leads
    cursor.execute('SELECT COUNT(*) FROM "OCRD" WHERE "CardType" = \'L\'')
    total_leads = cursor.fetchone()[0]
    print(f"Total Leads: {total_leads}")
    
    # Sample customer data (first 3 records)
    print(f"\n--- Sample Customer Data ---")
    cursor.execute('''
        SELECT 
            "CardCode",
            "CardName",
            "CardType",
            "Phone1",
            "Cellular",
            "E_Mail",
            "Address",
            "City",
            "validFor"
        FROM "OCRD" 
        WHERE "CardType" = 'C'
        LIMIT 3
    ''')
    
    customers = cursor.fetchall()
    for cust in customers:
        print(f"\nCardCode: {cust[0]}")
        print(f"  Name: {cust[1]}")
        print(f"  CardType: {cust[2]}")
        print(f"  Phone1: {cust[3]}")
        print(f"  Cellular: {cust[4]}")
        print(f"  Email: {cust[5]}")
        print(f"  Address: {cust[6]}")
        print(f"  City: {cust[7]}")
        print(f"  Active: {'Yes' if cust[8] == 'Y' else 'No'}")

cursor.close()
conn.close()

print(f"\n{'='*60}")
print("Check complete!")
print(f"{'='*60}")
