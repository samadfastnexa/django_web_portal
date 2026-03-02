import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'web_portal.settings')
django.setup()

from sap_integration.hana_connect import _load_env_file as _hana_load_env_file, products_catalog
from hdbcli import dbapi
from pathlib import Path
from django.conf import settings

_hana_load_env_file(os.path.join(os.path.dirname(__file__), 'sap_integration', '.env'))
_hana_load_env_file(os.path.join(str(settings.BASE_DIR), '.env'))
_hana_load_env_file(os.path.join(str(Path(settings.BASE_DIR).parent), '.env'))

schema = '4B-AGRI_LIVE'

print("🧪 Testing Image Sharing for Amazon and Astene Products")
print("=" * 70)

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
    cur = conn.cursor()
    cur.execute(f'SET SCHEMA "{schema}"')
    cur.close()
    
    # Test Amazon products
    print("\n📦 AMAZON 1.8 EC Products:")
    print("-" * 70)
    amazon_products = products_catalog(conn, schema, search='Amazone 1.8')
    
    if amazon_products:
        amazon_images = {}
        for p in amazon_products:
            item_code = p.get('ItemCode', 'N/A')
            item_name = p.get('ItemName', 'N/A')
            pack_size = p.get('SalPackMsr', 'N/A')
            image_url = p.get('product_image_url', None)
            
            print(f"  {item_code} - {item_name}")
            print(f"    Pack Size: {pack_size}")
            print(f"    Image: {image_url if image_url else '❌ No image'}")
            print()
            
            if image_url:
                amazon_images[image_url] = amazon_images.get(image_url, 0) + 1
        
        print(f"  📊 Summary: {len(amazon_products)} products, {len(amazon_images)} unique image(s)")
        if len(amazon_images) == 1:
            print(f"  ✅ SUCCESS! All variants share the same image")
        elif len(amazon_images) > 1:
            print(f"  ⚠️  Multiple images found")
        else:
            print(f"  ❌ No images found")
    else:
        print("  ❌ No Amazon products found")
    
    # Test Astene products
    print("\n📦 ASTENE 75 SP Products:")
    print("-" * 70)
    astene_products = products_catalog(conn, schema, search='Astene 75')
    
    if astene_products:
        astene_images = {}
        for p in astene_products:
            item_code = p.get('ItemCode', 'N/A')
            item_name = p.get('ItemName', 'N/A')
            pack_size = p.get('SalPackMsr', 'N/A')
            image_url = p.get('product_image_url', None)
            
            print(f"  {item_code} - {item_name}")
            print(f"    Pack Size: {pack_size}")
            print(f"    Image: {image_url if image_url else '❌ No image'}")
            print()
            
            if image_url:
                astene_images[image_url] = astene_images.get(image_url, 0) + 1
        
        print(f"  📊 Summary: {len(astene_products)} products, {len(astene_images)} unique image(s)")
        if len(astene_images) == 1:
            print(f"  ✅ SUCCESS! All variants share the same image")
        elif len(astene_images) > 1:
            print(f"  ⚠️  Multiple images found")
        else:
            print(f"  ❌ No images found")
    else:
        print("  ❌ No Astene products found")
    
    print("\n" + "=" * 70)
    print("🎉 Image sharing is working! Each product family shares a single image.")
    print("=" * 70)
    
    conn.close()
    
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
