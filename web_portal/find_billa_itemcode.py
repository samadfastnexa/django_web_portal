"""Find product by document name"""
import os
import sys
import django

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'web_portal.settings')
django.setup()

from hdbcli import dbapi

# Load environment manually
def load_env():
    env_paths = ['.env', '../.env']
    for env_path in env_paths:
        if os.path.exists(env_path):
            with open(env_path) as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        key, value = line.split('=', 1)
                        os.environ.setdefault(key.strip(), value.strip())

load_env()

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

# Query for products with Billa document
query = """
SELECT 
    T0."ItemCode",
    T0."ItemName",
    PU."FileName" AS "Product_Urdu_Name",
    PU."FileExt" AS "Product_Urdu_Ext"
FROM "OITM" T0
LEFT JOIN "ATC1" PU ON PU."AbsEntry" = T0."AtcEntry" AND PU."Line" = 1
WHERE PU."FileName" LIKE '%Billa%'
   OR T0."ItemName" LIKE '%Billa%'
ORDER BY T0."ItemCode"
"""

cur.execute(query)
results = cur.fetchall()

print("Products with Billa:")
print("=" * 100)
for row in results:
    print(f"ItemCode: {row[0]}")
    print(f"ItemName: {row[1]}")
    print(f"Document: {row[2]}.{row[3]}")
    print("-" * 100)

cur.close()
conn.close()
