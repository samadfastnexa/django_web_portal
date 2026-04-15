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
    
    # Check actual OTER table columns
    sql = 'SELECT * FROM OTER LIMIT 1'
    result = _fetch_all(conn, sql)
    print('=== OTER Table Structure ===')
    if result:
        cols = list(result[0].keys())
        print(f"Columns: {cols}")
    
    # Check if BHANKAR territory exists in HANA and get its code
    sql = "SELECT \"territryID\", \"descript\" FROM OTER WHERE \"descript\" LIKE '%BHANKAR%' OR \"territryID\" LIKE '%BHANKAR%' LIMIT 10"
    result = _fetch_all(conn, sql)
    print('\n=== HANA Territories matching BHANKAR ===')
    for row in result:
        print(row)
    
    # Check all territories
    sql_all = "SELECT \"territryID\", \"descript\" FROM OTER ORDER BY \"territryID\" LIMIT 30"
    result_all = _fetch_all(conn, sql_all)
    print('\n=== First 30 Territories in OTER ===')
    for row in result_all:
        print(row)
    
    # Check customer territories
    sql_cust = "SELECT DISTINCT T0.\"Territory\" as territory_code, O.\"descript\" as territory_desc FROM OCRD T0 LEFT JOIN OTER O ON O.\"territryID\" = T0.\"Territory\" WHERE T0.\"CardType\" = 'C' ORDER BY T0.\"Territory\" LIMIT 30"
    result_cust = _fetch_all(conn, sql_cust)
    print('\n=== First 30 Customer Territory Codes ===')
    for row in result_cust:
        print(row)
    
    # Count customers by territory
    sql_count = "SELECT T0.\"Territory\" as territory_code, O.\"descript\" as territory_desc, COUNT(*) as customer_count FROM OCRD T0 LEFT JOIN OTER O ON O.\"territryID\" = T0.\"Territory\" WHERE T0.\"CardType\" = 'C' GROUP BY T0.\"Territory\", O.\"descript\" ORDER BY customer_count DESC LIMIT 20"
    result_count = _fetch_all(conn, sql_count)
    print('\n=== Top 20 Territory Codes by Customer Count ===')
    for row in result_count:
        print(row)
    
    # Test the exact where clause from customer_lov
    print('\n=== Testing exact WHERE clause from API ===')
    sql_test = 'SELECT COUNT(*) as cnt FROM OCRD T0 LEFT JOIN OTER O ON O."territryID" = T0."Territory" WHERE T0."CardType" = \'C\' AND O."descript" = \'BHANKAR\''
    result_test = _fetch_all(conn, sql_test)
    print(f"Customers with O.descript = 'BHANKAR': {result_test}")
    
    conn.close()
    
except Exception as e:
    print(f'Error: {e}')
    import traceback
    traceback.print_exc()
