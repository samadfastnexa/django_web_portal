"""
Test product images after fix
"""

import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'web_portal.settings')
django.setup()

from sap_integration.hana_connect import _load_env_file as _hana_load_env_file, products_catalog
from hdbcli import dbapi
from pathlib import Path
from django.conf import settings

print("\n" + "="*70)
print("  Testing Product Images Fix")
print("="*70 + "\n")

_hana_load_env_file(os.path.join(os.path.dirname(__file__), 'sap_integration', '.env'))
_hana_load_env_file(os.path.join(str(settings.BASE_DIR), '.env'))
_hana_load_env_file(os.path.join(str(Path(settings.BASE_DIR).parent), '.env'))

schema = '4B-ORANG_APP'

try:
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
        kwargs['sslValidateCertificate'] = False
    
    conn = dbapi.connect(**kwargs)
    
    try:
        # Set schema first
        cur = conn.cursor()
        cur.execute(f'SET SCHEMA "{schema}"')
        cur.close()
        
        # Test products_catalog function with first 10 products
        print("Fetching products catalog (first 10 items)...\n")
        products = products_catalog(conn, schema)
        
        if products:
            print(f"Found {len(products)} total products\n")
            print("Sample products with image URLs:\n")
            
            for i, product in enumerate(products[:10], 1):
                print(f"{i}. {product.get('ItemCode')} - {product.get('ItemName')}")
                
                img_url = product.get('product_image_url')
                urdu_url = product.get('product_description_urdu_url')
                
                if img_url:
                    print(f"   ✓ Image: {img_url}")
                    # Check if file exists
                    file_path = os.path.join(settings.BASE_DIR, img_url.lstrip('/'))
                    if os.path.exists(file_path):
                        print(f"     ✓ File exists on disk")
                    else:
                        print(f"     ✗ File NOT found: {file_path}")
                else:
                    print(f"   ✗ No image URL generated")
                
                if urdu_url:
                    print(f"   ✓ Urdu: {urdu_url}")
                else:
                    print(f"   ✗ No Urdu URL")
                
                print()
        else:
            print("✗ No products found")
        
    finally:
        conn.close()
        
except Exception as e:
    print(f"✗ Error: {str(e)}")
    import traceback
    traceback.print_exc()

print("="*70 + "\n")
