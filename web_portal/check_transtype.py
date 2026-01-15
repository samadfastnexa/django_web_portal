"""
Check TransType values in SAP HANA to understand the mapping
"""

import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'web_portal.settings')
django.setup()

from general_ledger.utils import get_hana_connection

print("\n" + "="*70)
print("  Checking TransType Values and Names")
print("="*70 + "\n")

try:
    conn = get_hana_connection('4B-ORANG')
    
    if conn:
        cur = conn.cursor()
        
        # Check if there's a transaction type table (ONNM)
        print("Checking for Transaction Type Table (NNM1):\n")
        
        sql = """
        SELECT 
            "Series" AS "TypeCode",
            "SeriesName" AS "TypeName",
            "ObjectCode",
            "Indicator"
        FROM "NNM1"
        ORDER BY "Series"
        LIMIT 20
        """
        
        try:
            cur.execute(sql)
            rows = cur.fetchall()
            
            if rows:
                print(f"Found {len(rows)} transaction types:\n")
                for row in rows:
                    print(f"  Code: {row[0]}, Name: {row[1]}, Object: {row[2]}, Indicator: {row[3]}")
            else:
                print("No data in NNM1 table")
        except Exception as e:
            print(f"NNM1 table not found or error: {str(e)}")
        
        # Now check actual TransType values from OJDT
        print("\n" + "="*70)
        print("  Actual TransType Values in OJDT Table")
        print("="*70 + "\n")
        
        sql2 = """
        SELECT DISTINCT 
            T0."TransType",
            COUNT(*) AS "Count"
        FROM "OJDT" T0
        GROUP BY T0."TransType"
        ORDER BY T0."TransType"
        """
        
        cur.execute(sql2)
        rows2 = cur.fetchall()
        
        print(f"Found {len(rows2)} unique TransType values:\n")
        for row in rows2:
            trans_type = row[0]
            count = row[1]
            print(f"  TransType: {trans_type} - Count: {count}")
        
        # Sample some actual transactions
        print("\n" + "="*70)
        print("  Sample Transactions with Type 30")
        print("="*70 + "\n")
        
        sql3 = """
        SELECT 
            T0."TransId",
            T0."TransType",
            T0."RefDate",
            T0."BaseRef",
            T0."Memo",
            T1."ShortName" AS "BPCode",
            T3."CardName" AS "BPName"
        FROM "OJDT" T0
        LEFT JOIN "JDT1" T1 ON T0."TransId" = T1."TransId"
        LEFT JOIN "OCRD" T3 ON T1."ShortName" = T3."CardCode"
        WHERE T0."TransType" = 30
        LIMIT 10
        """
        
        cur.execute(sql3)
        rows3 = cur.fetchall()
        
        for row in rows3:
            print(f"  TransId: {row[0]}, Type: {row[1]}, Date: {row[2]}, BaseRef: {row[3]}")
            print(f"    BP: {row[5]} - {row[6]}")
            print(f"    Memo: {row[4]}")
            print()
        
        cur.close()
        conn.close()
        
except Exception as e:
    print(f"✗ Error: {str(e)}")
    import traceback
    traceback.print_exc()

print("="*70 + "\n")
