"""
Test script to check if products exist in HANA catalog
Run: python manage.py shell < test_product_lookup.py
"""

import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'web_portal.settings')
django.setup()

from sap_integration.hana_connect import _load_env_file as _hana_load_env_file, products_catalog
from hdbcli import dbapi
from pathlib import Path
from django.conf import settings

# Load environment variables
try:
    _hana_load_env_file(os.path.join(os.path.dirname(__file__), 'sap_integration', '.env'))
    _hana_load_env_file(os.path.join(str(settings.BASE_DIR), '.env'))
    _hana_load_env_file(os.path.join(str(Path(settings.BASE_DIR).parent), '.env'))
except Exception as e:
    print(f"Error loading env: {e}")

# Product codes to test
product_codes = ['FG00100', 'FG00101', 'FG00102']

# Test database
schema = '4B-ORANG_APP'

print(f"\n=== Testing Product Lookup in HANA ===")
print(f"Schema: {schema}")
print(f"Product codes: {product_codes}")
print(f"\nHANA Host: {os.environ.get('HANA_HOST')}")
print(f"HANA Port: {os.environ.get('HANA_PORT')}")
print(f"HANA User: {os.environ.get('HANA_USER')}")

try:
    # Connect to HANA
    cfg = {
        'host': os.environ.get('HANA_HOST', ''),
        'port': os.environ.get('HANA_PORT', ''),
        'user': os.environ.get('HANA_USER', ''),
        'encrypt': os.environ.get('HANA_ENCRYPT', ''),
        'schema': schema
    }
    
    pwd = os.environ.get('HANA_PASSWORD', '')
    kwargs = {
        'address': cfg['host'],
        'port': int(cfg['port']),
        'user': cfg['user'],
        'password': pwd
    }
    
    if str(cfg['encrypt']).strip().lower() in ('true', '1', 'yes'):
        kwargs['encrypt'] = True
        kwargs['sslValidateCertificate'] = False  # Skip SSL validation for testing
    
    print(f"\nConnecting to HANA...")
    conn = dbapi.connect(**kwargs)
    print(f"✓ Connected successfully")
    
    try:
        # Set schema
        if cfg['schema']:
            cur = conn.cursor()
            cur.execute(f'SET SCHEMA "{cfg["schema"]}"')
            cur.close()
            print(f"✓ Schema set to: {cfg['schema']}")
        
        # Search for each product
        print(f"\n=== Searching for Products ===")
        for product_code in product_codes:
            print(f"\nSearching for: {product_code}")
            catalog_items = products_catalog(conn, cfg['schema'], search=product_code)
            
            if catalog_items:
                print(f"  Found {len(catalog_items)} items")
                for item in catalog_items:
                    if item.get('ItemCode') == product_code:
                        print(f"  ✓ EXACT MATCH: {item.get('ItemCode')} - {item.get('ItemName')}")
                        print(f"    Generic Name: {item.get('U_GenericName')}")
                        print(f"    Brand Name: {item.get('U_BrandName')}")
                        print(f"    Item Group: {item.get('ItmsGrpNam')}")
                        print(f"    Image File: {item.get('Product_Image_Name')}.{item.get('Product_Image_Ext')}")
                        print(f"    Image URL: {item.get('product_image_url')}")
                        break
                else:
                    print(f"  Partial matches found but no exact match for '{product_code}':")
                    for item in catalog_items[:3]:  # Show first 3
                        print(f"    - {item.get('ItemCode')} - {item.get('ItemName')}")
            else:
                print(f"  ✗ NOT FOUND in HANA")
        
        # Try broad search to see what products exist
        print(f"\n=== Checking all FG products ===")
        all_fg = products_catalog(conn, cfg['schema'], search='FG')
        print(f"Found {len(all_fg)} products starting with 'FG'")
        print(f"First 10 products:")
        for item in all_fg[:10]:
            print(f"  - {item.get('ItemCode')} - {item.get('ItemName')}")
        
    finally:
        conn.close()
        print(f"\n✓ Connection closed")
        
except Exception as e:
    print(f"\n✗ Error: {str(e)}")
    import traceback
    traceback.print_exc()

print(f"\n=== Test Complete ===\n")
