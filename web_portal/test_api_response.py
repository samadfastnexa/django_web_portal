"""
Test the recommended products API with correct product codes
Run: python test_api_response.py
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
_hana_load_env_file(os.path.join(os.path.dirname(__file__), 'sap_integration', '.env'))
_hana_load_env_file(os.path.join(str(settings.BASE_DIR), '.env'))
_hana_load_env_file(os.path.join(str(Path(settings.BASE_DIR).parent), '.env'))

# Product codes from @ODID
product_codes = ['FG00259', 'FG00040']
schema = '4B-ORANG_APP'

print(f"\n{'='*60}")
print(f"  Product Details from HANA Catalog")
print(f"{'='*60}\n")
print(f"Database: {schema}")
print(f"Products: {', '.join(product_codes)}\n")

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
        kwargs['sslValidateCertificate'] = False
    
    conn = dbapi.connect(**kwargs)
    
    try:
        # Set schema
        if cfg['schema']:
            cur = conn.cursor()
            cur.execute(f'SET SCHEMA "{cfg["schema"]}"')
            cur.close()
        
        # Get each product
        for product_code in product_codes:
            catalog_items = products_catalog(conn, cfg['schema'], search=product_code)
            
            for item in catalog_items:
                if item.get('ItemCode') == product_code:
                    print(f"📦 {item.get('ItmsGrpNam', 'N/A')}")
                    print(f"   {item.get('ItemCode')}")
                    print(f"   {item.get('ItemName')}")
                    print(f"   ")
                    print(f"   Generic Name: {item.get('U_GenericName') or 'N/A'}")
                    print(f"   Brand Name: {item.get('U_BrandName') or 'N/A'}")
                    print(f"   Unit: {item.get('SalPackMsr') or item.get('InvntryUom') or 'N/A'}")
                    print(f"   ")
                    
                    # Image info
                    img_name = item.get('Product_Image_Name')
                    img_ext = item.get('Product_Image_Ext')
                    if img_name and img_ext and img_name != 'None':
                        print(f"   🖼️  Image: {item.get('product_image_url')}")
                    else:
                        print(f"   🖼️  Image: Not available (no attachment in SAP)")
                    
                    urdu_name = item.get('Product_Urdu_Name')
                    urdu_ext = item.get('Product_Urdu_Ext')
                    if urdu_name and urdu_ext and urdu_name != 'None':
                        print(f"   📄 Urdu: {item.get('product_description_urdu_url')}")
                    else:
                        print(f"   📄 Urdu: Not available")
                    
                    print(f"\n{'-'*60}\n")
                    break
        
    finally:
        conn.close()
        
except Exception as e:
    print(f"\n✗ Error: {str(e)}")
    import traceback
    traceback.print_exc()

print(f"{'='*60}\n")
