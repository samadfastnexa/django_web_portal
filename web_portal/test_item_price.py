#!/usr/bin/env python
"""
Test script to diagnose item_price_api issues
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

from sap_integration.hana_connect import unit_price_by_policy, _fetch_one
from django.conf import settings
from hdbcli import dbapi

def test_item_price(database='4B-ORANG_APP', doc_entry='1', item_code='ORANGE-001'):
    """Test the item price lookup"""
    print(f"\n{'='*80}")
    print(f"Testing Item Price Lookup")
    print(f"{'='*80}")
    print(f"Database: {database}")
    print(f"DocEntry: {doc_entry}")
    print(f"ItemCode: {item_code}")
    print(f"{'='*80}\n")
    
    try:
        # Connect to HANA directly
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
        
        conn = dbapi.connect(**kwargs)
        print(f"✓ Connected to HANA: {cfg['host']}:{cfg['port']}")
        
        # Test 1: Check if policy table exists
        print("\n[TEST 1] Checking if policy tables exist...")
        cur = conn.cursor()
        cur.execute(f'SET SCHEMA "{database}"')
        
        # Check @PL1 table
        try:
            cur.execute('SELECT COUNT(*) as cnt FROM "@PL1"')
            result = cur.fetchone()
            print(f"  ✓ @PL1 table exists with {result[0]} rows")
        except Exception as e:
            print(f"  ✗ @PL1 table error: {e}")
        
        # Check @PLR4 table
        try:
            cur.execute('SELECT COUNT(*) as cnt FROM "@PLR4"')
            result = cur.fetchone()
            print(f"  ✓ @PLR4 table exists with {result[0]} rows")
        except Exception as e:
            print(f"  ✗ @PLR4 table error: {e}")
        
        # Test 2: List sample policies
        print("\n[TEST 2] Listing sample policies from @PL1...")
        try:
            cur.execute('SELECT "DocEntry", "U_proj", "DocDate" FROM "@PL1" LIMIT 10')
            rows = cur.fetchall()
            if rows:
                print(f"  Found {len(rows)} policies:")
                for row in rows:
                    print(f"    - DocEntry: {row[0]}, Project: {row[1]}, Date: {row[2]}")
            else:
                print("  ✗ No policies found!")
        except Exception as e:
            print(f"  ✗ Error: {e}")
        
        # Test 3: List sample items in @PLR4
        print("\n[TEST 3] Listing sample items from @PLR4...")
        try:
            cur.execute('SELECT "DocEntry", "U_itc", "U_frp" FROM "@PLR4" LIMIT 10')
            rows = cur.fetchall()
            if rows:
                print(f"  Found {len(rows)} items:")
                for row in rows:
                    print(f"    - DocEntry: {row[0]}, ItemCode: {row[1]}, Price: {row[2]}")
            else:
                print("  ✗ No items found!")
        except Exception as e:
            print(f"  ✗ Error: {e}")
        
        # Test 4: Try to find the specific doc_entry
        print(f"\n[TEST 4] Searching for doc_entry={doc_entry} in @PL1...")
        try:
            cur.execute('SELECT "DocEntry", "U_proj" FROM "@PL1" WHERE "DocEntry" = ?', (doc_entry,))
            result = cur.fetchone()
            if result:
                print(f"  ✓ Found: DocEntry={result[0]}, Project={result[1]}")
            else:
                print(f"  ✗ DocEntry {doc_entry} not found!")
                # List all available doc entries
                cur.execute('SELECT "DocEntry" FROM "@PL1" LIMIT 5')
                available = [str(row[0]) for row in cur.fetchall()]
                print(f"  Available DocEntries: {available}")
        except Exception as e:
            print(f"  ✗ Error: {e}")
        
        # Test 5: Try to find the specific item_code
        print(f"\n[TEST 5] Searching for item_code={item_code} in @PLR4...")
        try:
            cur.execute('SELECT "DocEntry", "U_itc", "U_frp" FROM "@PLR4" WHERE "U_itc" = ? LIMIT 5', (item_code,))
            results = cur.fetchall()
            if results:
                print(f"  ✓ Found {len(results)} matching items:")
                for row in results:
                    print(f"    - DocEntry: {row[0]}, ItemCode: {row[1]}, Price: {row[2]}")
            else:
                print(f"  ✗ ItemCode {item_code} not found!")
                # List available item codes
                cur.execute('SELECT DISTINCT "U_itc" FROM "@PLR4" LIMIT 10')
                available = [row[0] for row in cur.fetchall()]
                print(f"  Sample available ItemCodes: {available}")
        except Exception as e:
            print(f"  ✗ Error: {e}")
        
        # Test 6: Run the actual query
        print(f"\n[TEST 6] Running unit_price_by_policy query...")
        print(f"  Query: SELECT U_frp FROM @PL1 T0")
        print(f"         INNER JOIN @PLR4 T1 ON T0.DocEntry = T1.DocEntry")
        print(f"         WHERE T0.DocEntry = {doc_entry} AND T1.U_itc = {item_code}")
        try:
            result = unit_price_by_policy(conn, doc_entry, item_code)
            if result:
                print(f"  ✓ Price found: {result}")
            else:
                print(f"  ✗ No price found (None returned)")
        except Exception as e:
            print(f"  ✗ Error: {e}")
        
        cur.close()
        conn.close()
        print(f"\n✓ Test completed\n")
        
    except Exception as e:
        print(f"✗ Connection error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    # Test with different parameters
    print("\n" + "="*80)
    print("ITEM PRICE API DIAGNOSTIC TEST")
    print("="*80)
    
    # Test 1: ORANG with default values
    test_item_price(database='4B-ORANG_APP', doc_entry='1', item_code='ORANGE-001')
    
    # Test 2: BIO database for comparison
    print("\n" + "="*80)
    print("Running same test on BIO database for comparison...")
    print("="*80)
    test_item_price(database='4B-BIO_APP', doc_entry='1', item_code='BIO-001')
