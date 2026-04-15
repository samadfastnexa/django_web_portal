import django
import os
import sys
# Add the web_portal directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'web_portal'))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'web_portal.settings')
django.setup()

from sap_integration.hana_connect import _fetch_all, _load_env_file

# Load env vars
_load_env_file(os.path.join(os.path.dirname(__file__), 'web_portal', 'sap_integration', '.env'))
_load_env_file(os.path.join(os.path.dirname(__file__), '.env'))

try:
    from hdbcli import dbapi
    cfg_host = os.environ.get('HANA_HOST') or ''
    cfg_port = os.environ.get('HANA_PORT') or '30015'
    cfg_user = os.environ.get('HANA_USER') or ''
    cfg_pwd = os.environ.get('HANA_PASSWORD') or ''
    
    kwargs = {'address': cfg_host, 'port': int(cfg_port), 'user': cfg_user, 'password': cfg_pwd}
    conn = dbapi.connect(**kwargs)
    
    # Set schema
    cur = conn.cursor()
    cur.execute('SET SCHEMA "4B-AGRI_LIVE"')
    cur.close()
    
    # Check if BHANKAR territory exists in HANA and get its code
    sql = "SELECT \"TerritoryId\", \"descript\" FROM OTER WHERE \"descript\" LIKE '%BHANKAR%' OR \"TerritoryId\" LIKE '%BHANKAR%'"
    result = _fetch_all(conn, sql)
    print('=== HANA Territories matching BHANKAR ===')
    for row in result:
        print(row)
    
    # Check if there are any customers with Territory codes
    sql2 = "SELECT DISTINCT T0.\"Territory\", COUNT(*) as customer_count FROM OCRD T0 WHERE T0.\"Territory\" IS NOT NULL GROUP BY T0.\"Territory\" ORDER BY customer_count DESC LIMIT 20"
    result2 = _fetch_all(conn, sql2)
    print('\n=== Top Territory Codes in OCRD (Customer Master) ===')
    for row in result2:
        print(row)
    
    # Check OTER table structure
    sql3 = "SELECT \"TerritoryId\", \"descript\" FROM OTER ORDER BY \"TerritoryId\" LIMIT 10"
    result3 = _fetch_all(conn, sql3)
    print('\n=== Sample OTER Records (First 10) ===')
    for row in result3:
        print(row)
    
    # Check customers with specific territories
    sql4 = "SELECT COUNT(*) as total_customers FROM OCRD T0 WHERE T0.\"Territory\" = 'BHANKAR'"
    result4 = _fetch_all(conn, sql4)
    print('\n=== Customers with Territory = "BHANKAR" ===')
    print(result4)
    
    # Try variant
    sql5 = "SELECT COUNT(*) as total_customers FROM OCRD T0 WHERE T0.\"Territory\" = '01'"
    result5 = _fetch_all(conn, sql5)
    print('\n=== Customers with Territory = "01" ===')
    print(result5)
    
    conn.close()
    
except Exception as e:
    print(f'Error: {e}')
    import traceback
    traceback.print_exc()
