"""
Sync diseases from SAP @ODID table and check product images
Run: python sync_and_check.py
"""

import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'web_portal.settings')
django.setup()

from sap_integration.sap_client import SAPClient
from sap_integration.models import DiseaseIdentification
from sap_integration.hana_connect import _load_env_file as _hana_load_env_file
from hdbcli import dbapi
from pathlib import Path
from django.conf import settings

print("\n" + "="*70)
print("  STEP 1: Sync Diseases from SAP @ODID Table")
print("="*70 + "\n")

# Sync diseases from SAP
try:
    client = SAPClient(company_db_key='4B-ORANG')
    diseases = client.get_diseases()
    
    print(f"Found {len(diseases)} diseases in SAP @ODID table:\n")
    
    created = 0
    updated = 0
    
    for disease_data in diseases:
        item_code = disease_data.get('item_code', '').strip()
        if not item_code:
            continue
        
        print(f"  • {item_code}: {disease_data.get('disease_name', 'N/A')}")
        
        defaults = {
            'doc_entry': disease_data.get('doc_entry', ''),
            'item_name': disease_data.get('item_name', ''),
            'description': disease_data.get('description', ''),
            'disease_name': disease_data.get('disease_name', ''),
            'is_active': True,
        }
        
        obj, is_created = DiseaseIdentification.objects.update_or_create(
            item_code=item_code,
            defaults=defaults
        )
        created += 1 if is_created else 0
        updated += 0 if is_created else 1
    
    print(f"\n✓ Sync completed: Created={created}, Updated={updated}\n")
    
except Exception as e:
    print(f"✗ Error syncing diseases: {str(e)}\n")

print("="*70)
print("  STEP 2: Check Product Images in SAP HANA")
print("="*70 + "\n")

# Check images for specific products
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
        cur = conn.cursor()
        cur.execute(f'SET SCHEMA "{schema}"')
        
        # Check for products with images
        sql = """
        SELECT 
            T0."ItemCode",
            T0."ItemName",
            T0."AtcEntry",
            PI."FileName" AS "Image_File",
            PI."FileExt" AS "Image_Ext",
            PU."FileName" AS "Urdu_File",
            PU."FileExt" AS "Urdu_Ext"
        FROM OITM T0
        LEFT JOIN ATC1 PI ON PI."AbsEntry" = T0."AtcEntry" AND PI."Line" = 0
        LEFT JOIN ATC1 PU ON PU."AbsEntry" = T0."AtcEntry" AND PU."Line" = 1
        WHERE T0."ItemCode" IN ('FG00259', 'FG00040', 'FG00041')
        """
        
        cur.execute(sql)
        rows = cur.fetchall()
        
        print("Product Image Status:\n")
        for row in rows:
            item_code = row[0]
            item_name = row[1]
            atc_entry = row[2]
            img_file = row[3]
            img_ext = row[4]
            urdu_file = row[5]
            urdu_ext = row[6]
            
            print(f"  📦 {item_code} - {item_name}")
            print(f"     AtcEntry: {atc_entry}")
            
            if img_file and img_ext:
                img_path = f"/media/product_images/4B-ORANG/{img_file}.{img_ext}"
                print(f"     ✓ Image: {img_file}.{img_ext}")
                print(f"       URL: {img_path}")
            else:
                print(f"     ✗ No image attachment (Line 0)")
            
            if urdu_file and urdu_ext:
                urdu_path = f"/media/product_images/4B-ORANG/{urdu_file}.{urdu_ext}"
                print(f"     ✓ Urdu: {urdu_file}.{urdu_ext}")
                print(f"       URL: {urdu_path}")
            else:
                print(f"     ✗ No Urdu attachment (Line 1)")
            
            print()
        
        cur.close()
        
    finally:
        conn.close()
        
except Exception as e:
    print(f"✗ Error checking images: {str(e)}")
    import traceback
    traceback.print_exc()

print("="*70)
print("\n✓ All checks complete\n")
