#!/usr/bin/env python
"""
Interactive test for item_price_api - Query with real data
"""
import os
import sys
import django
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'web_portal.settings')
sys.path.insert(0, str(Path(__file__).parent))
django.setup()

from sap_integration.hana_connect import unit_price_by_policy
from hdbcli import dbapi

def connect_hana():
    """Connect to HANA"""
    cfg = {
        'host': os.environ.get('HANA_HOST') or '',
        'port': os.environ.get('HANA_PORT') or '30015',
        'user': os.environ.get('HANA_USER') or '',
        'encrypt': os.environ.get('HANA_ENCRYPT') or '',
        'ssl_validate': os.environ.get('HANA_SSL_VALIDATE') or '',
    }
    
    pwd = os.environ.get('HANA_PASSWORD','')
    kwargs = {'address': cfg['host'], 'port': int(cfg['port']), 'user': cfg['user'] or '', 'password': pwd or ''}
    if str(cfg['encrypt']).strip().lower() in ('true','1','yes'):
        kwargs['encrypt'] = True
        if cfg['ssl_validate']:
            kwargs['sslValidateCertificate'] = (str(cfg['ssl_validate']).strip().lower() in ('true','1','yes'))
    
    return dbapi.connect(**kwargs)

def test_with_real_data(database='4B-ORANG_APP'):
    """Test with actual data from the database"""
    print(f"\n{'='*100}")
    print(f"ITEM PRICE API - REAL DATA TEST FOR {database}")
    print(f"{'='*100}\n")
    
    conn = connect_hana()
    cur = conn.cursor()
    cur.execute(f'SET SCHEMA "{database}"')
    
    try:
        # Get a sample of valid policy + item combinations with non-null prices
        print("[STEP 1] Finding valid policy + item combinations with actual prices...\n")
        
        query = '''
        SELECT TOP 20 
            T0."DocEntry",
            T1."U_itc" as "ItemCode",
            T1."U_frp" as "UnitPrice"
        FROM "@PL1" T0 
        INNER JOIN "@PLR4" T1 ON T0."DocEntry" = T1."DocEntry" 
        WHERE T1."U_itc" IS NOT NULL 
        AND T1."U_frp" IS NOT NULL 
        AND T1."U_frp" != 0
        AND T1."U_frp" != -1
        ORDER BY T0."DocEntry" ASC
        '''
        
        cur.execute(query)
        results = cur.fetchall()
        
        if not results:
            print("✗ No valid combinations found with actual prices!")
            print("\nTrying with ANY non-null items (even if price is 0 or -1)...\n")
            query = '''
            SELECT TOP 20 
                T0."DocEntry",
                T1."U_itc" as "ItemCode",
                T1."U_frp" as "UnitPrice"
            FROM "@PL1" T0 
            INNER JOIN "@PLR4" T1 ON T0."DocEntry" = T1."DocEntry" 
            WHERE T1."U_itc" IS NOT NULL 
            ORDER BY T0."DocEntry" ASC
            '''
            cur.execute(query)
            results = cur.fetchall()
        
        print(f"Found {len(results)} sample combinations:\n")
        test_cases = []
        for row in results:
            doc_entry, item_code, price = row
            print(f"  DocEntry: {doc_entry:5} | ItemCode: {str(item_code):12} | Price: {price}")
            test_cases.append((str(doc_entry), str(item_code)))
        
        # Test each combination
        print(f"\n[STEP 2] Testing each combination via unit_price_by_policy()...\n")
        
        for doc_entry, item_code in test_cases[:5]:  # Test first 5
            print(f"Testing: doc_entry={doc_entry}, item_code={item_code}")
            try:
                result = unit_price_by_policy(conn, doc_entry, item_code)
                if result:
                    print(f"  ✓ FOUND: {result}")
                else:
                    print(f"  ✗ No result (None returned)")
            except Exception as e:
                print(f"  ✗ Error: {e}")
            print()
        
        # Test direct SQL query
        print(f"[STEP 3] Testing direct SQL query...\n")
        if test_cases:
            doc_entry, item_code = test_cases[0]
            sql = (
                'SELECT T1."U_frp" '
                'FROM "@PL1" T0 '
                'INNER JOIN "@PLR4" T1 ON T0."DocEntry" = T1."DocEntry" '
                'WHERE T0."DocEntry" = ? '
                'AND T1."U_itc" = ? '
            )
            print(f"Query: {sql}")
            print(f"Params: doc_entry={doc_entry}, item_code={item_code}\n")
            
            cur.execute(sql, (doc_entry, item_code))
            result = cur.fetchone()
            if result:
                print(f"✓ Direct SQL returned: {result}")
            else:
                print(f"✗ Direct SQL returned: None")
        
        # Check data issues
        print(f"\n[STEP 4] Checking data quality issues...\n")
        
        cur.execute('SELECT COUNT(*) FROM "@PLR4" WHERE "U_itc" IS NULL')
        null_items = cur.fetchone()[0]
        
        cur.execute('SELECT COUNT(*) FROM "@PLR4" WHERE "U_frp" IS NULL OR "U_frp" = 0 OR "U_frp" = -1')
        invalid_prices = cur.fetchone()[0]
        
        cur.execute('SELECT COUNT(*) FROM "@PLR4"')
        total_items = cur.fetchone()[0]
        
        print(f"Data Quality Summary:")
        print(f"  Total items in @PLR4: {total_items}")
        print(f"  Items with NULL ItemCode: {null_items} ({null_items*100//total_items}%)")
        print(f"  Items with invalid/zero prices: {invalid_prices} ({invalid_prices*100//total_items}%)")
        print(f"  Valid items (non-null code AND valid price): {total_items - null_items - invalid_prices}")
        
    except Exception as e:
        print(f"✗ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        cur.close()
        conn.close()

def test_api_endpoint(doc_entry, item_code, database='4B-ORANG'):
    """Test the API endpoint"""
    print(f"\n{'='*100}")
    print(f"TESTING API ENDPOINT")
    print(f"{'='*100}\n")
    
    import requests
    url = f"http://localhost:8000/sap/item-price/"
    params = {
        'database': database,
        'doc_entry': doc_entry,
        'item_code': item_code
    }
    
    print(f"GET {url}")
    print(f"Params: {params}\n")
    
    try:
        response = requests.get(url, params=params)
        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.json()}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == '__main__':
    # Test with real data
    test_with_real_data('4B-ORANG_APP')
    test_with_real_data('4B-BIO_APP')
    
    # Optionally test the API if running locally
    print(f"\n{'='*100}")
    print("To test the API endpoint, use one of these examples:")
    print("  curl 'http://localhost:8000/sap/item-price/?database=4B-ORANG&doc_entry=10&item_code=FG00004'")
    print(f"{'='*100}\n")
