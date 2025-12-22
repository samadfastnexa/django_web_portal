import os
import sys
from hdbcli import dbapi

# Add path to find hana_connect
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..')) # django_web_portal
sys.path.append(os.path.dirname(__file__)) # sap_integration

# Mock django models if needed, but hana_connect imports inside function for _get_b4_schema
# So it should be fine if we don't call that function.

from hana_connect import sales_vs_achievement_geo_inv

def _load_env_file(path: str) -> None:
    if not os.path.exists(path):
        return
    try:
        with open(path, 'r') as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                if '=' in line:
                    k, v = line.split('=', 1)
                    k = k.strip()
                    v = v.strip()
                    if v.startswith('"') and v.endswith('"'):
                        v = v[1:-1]
                    elif v.startswith("'") and v.endswith("'"):
                        v = v[1:-1]
                    os.environ[k] = v
    except Exception:
        pass

# Load env
base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
root_dir = os.path.dirname(base_dir)
_load_env_file(os.path.join(root_dir, '.env'))

# Connection details
host = os.environ.get('HANA_HOST')
port = int(os.environ.get('HANA_PORT', 30015))
user = os.environ.get('HANA_USER')
password = os.environ.get('HANA_PASSWORD')

def test_function(schema):
    print(f"--- Testing sales_vs_achievement_geo_inv for {schema} ---")
    try:
        conn = dbapi.connect(address=host, port=port, user=user, password=password)
        cursor = conn.cursor()
        cursor.execute(f'SET SCHEMA "{schema}"')
        cursor.close()
        
        # Call function with defaults (no filters)
        print("Calling sales_vs_achievement_geo_inv(conn, group_by_emp=False)...")
        data = sales_vs_achievement_geo_inv(conn, group_by_emp=False)
        print(f"Returned {len(data)} rows.")
        if len(data) > 0:
            print("First row:", data[0])
            
        conn.close()
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    test_function("4B-BIO_APP")
    test_function("4B-ORANG_APP")
