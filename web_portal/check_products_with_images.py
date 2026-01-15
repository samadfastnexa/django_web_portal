"""
Check which products have images in SAP HANA
"""

import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'web_portal.settings')
django.setup()

from sap_integration.hana_connect import _load_env_file as _hana_load_env_file
from hdbcli import dbapi
from pathlib import Path
from django.conf import settings

print("\n" + "="*70)
print("  Checking Products with Images in SAP HANA")
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
        cur = conn.cursor()
        cur.execute(f'SET SCHEMA "{schema}"')
        
        # Check for products with AtcEntry (attachments)
        sql = """
        SELECT 
            T0."ItemCode",
            T0."ItemName",
            T0."AtcEntry",
            T0."Series",
            T0."validFor",
            PI."FileName" AS "Image_File",
            PI."FileExt" AS "Image_Ext",
            PU."FileName" AS "Urdu_File",
            PU."FileExt" AS "Urdu_Ext"
        FROM OITM T0
        LEFT JOIN ATC1 PI ON PI."AbsEntry" = T0."AtcEntry" AND PI."Line" = 0
        LEFT JOIN ATC1 PU ON PU."AbsEntry" = T0."AtcEntry" AND PU."Line" = 1
        WHERE T0."Series" = '72' 
        AND T0."validFor" = 'Y'
        AND T0."AtcEntry" IS NOT NULL
        ORDER BY T0."ItemCode"
        LIMIT 20
        """
        
        cur.execute(sql)
        rows = cur.fetchall()
        
        if rows:
            print(f"Found {len(rows)} products with attachments:\n")
            for row in rows:
                item_code = row[0]
                item_name = row[1]
                atc_entry = row[2]
                series = row[3]
                valid_for = row[4]
                img_file = row[5]
                img_ext = row[6]
                urdu_file = row[7]
                urdu_ext = row[8]
                
                print(f"  📦 {item_code} - {item_name}")
                print(f"     AtcEntry: {atc_entry}, Series: {series}, ValidFor: {valid_for}")
                
                if img_file and img_ext:
                    print(f"     ✓ Image: {img_file}.{img_ext}")
                else:
                    print(f"     ✗ No image (Line 0)")
                
                if urdu_file and urdu_ext:
                    print(f"     ✓ Urdu: {urdu_file}.{urdu_ext}")
                else:
                    print(f"     ✗ No Urdu (Line 1)")
                
                print()
        else:
            print("✗ No products found with attachments (AtcEntry IS NOT NULL)")
        
        # Check total counts
        cur.execute(f"""
        SELECT 
            COUNT(*) as total,
            COUNT(T0."AtcEntry") as with_attachments
        FROM OITM T0
        WHERE T0."Series" = '72' 
        AND T0."validFor" = 'Y'
        """)
        
        counts = cur.fetchone()
        print(f"\n📊 Statistics:")
        print(f"   Total products (Series=72, ValidFor=Y): {counts[0]}")
        print(f"   Products with attachments: {counts[1]}")
        print(f"   Products without attachments: {counts[0] - counts[1]}")
        
        cur.close()
        
    finally:
        conn.close()
        
except Exception as e:
    print(f"✗ Error: {str(e)}")
    import traceback
    traceback.print_exc()

print("\n" + "="*70 + "\n")
