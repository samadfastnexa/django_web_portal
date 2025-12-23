import os
import sys
from hdbcli import dbapi

# Setup paths
base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
root_dir = os.path.dirname(base_dir)
sys.path.append(base_dir)

# Load env
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

_load_env_file(os.path.join(root_dir, '.env'))

# Connection details
host = os.environ.get('HANA_HOST')
port = int(os.environ.get('HANA_PORT', 30015))
user = os.environ.get('HANA_USER')
password = os.environ.get('HANA_PASSWORD')

try:
    from sap_integration.hana_connect import sales_vs_achievement_geo_inv
    print("Successfully imported sales_vs_achievement_geo_inv")
except ImportError as e:
    print(f"Import failed: {e}")
    sys.exit(1)

def test_view_logic(schema):
    print(f"\n--- Testing View Logic for {schema} ---")
    try:
        conn = dbapi.connect(address=host, port=port, user=user, password=password)
        cursor = conn.cursor()
        cursor.execute(f'SET SCHEMA "{schema}"')
        cursor.close()
        
        # Call the function
        print("Calling sales_vs_achievement_geo_inv...")
        data = sales_vs_achievement_geo_inv(conn, group_by_emp=False)
        
        print(f"Data returned: {len(data) if data else 0} rows")
        
        if data:
            print("First row sample:")
            print(data[0])
            
            # Simulate View Transformation
            hierarchy = {}
            for row in data:
                if not isinstance(row, dict):
                    continue
                reg = row.get('Region', 'Unknown Region')
                # ... just printing keys to verify
                print(f"Keys in row: {list(row.keys())}")
                break
                
        conn.close()
    except Exception as e:
        print(f"Test failed: {e}")

if __name__ == '__main__':
    test_view_logic("4B-ORANG_APP")
