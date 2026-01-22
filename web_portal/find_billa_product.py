"""Find Billa product ItemCode"""
import os
import sys
import django

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'web_portal.settings')
django.setup()

from sap_integration.views import products_catalog
from hdbcli import dbapi
from pathlib import Path
from dotenv import load_dotenv

# Load environment
load_dotenv('.env')
load_dotenv(Path.cwd().parent / '.env')

cfg = {
    'host': os.environ.get('HANA_HOST'),
    'port': int(os.environ.get('HANA_PORT', 30015)),
    'user': os.environ.get('HANA_USER'),
    'password': os.environ.get('HANA_PASSWORD'),
}

conn = dbapi.connect(
    address=cfg['host'],
    port=cfg['port'],
    user=cfg['user'],
    password=cfg['password']
)

cur = conn.cursor()
cur.execute('SET SCHEMA "4B-ORANG_APP"')
cur.close()

products = products_catalog(conn, schema_name='4B-ORANG_APP', search='Billa')
conn.close()

print("Billa Products:")
print("=" * 80)
for p in products:
    item_name = p.get('ItemName', '')
    if 'Billa' in item_name or 'BILLA' in item_name:
        print(f"ItemCode: {p.get('ItemCode')}")
        print(f"ItemName: {item_name}")
        print(f"Document: {p.get('Product_Urdu_Name')}.{p.get('Product_Urdu_Ext')}")
        print("-" * 80)
