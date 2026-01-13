import os
import sys
from hdbcli import dbapi

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
base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__))) # sap_integration -> web_portal
root_dir = os.path.dirname(base_dir) # web_portal -> django_web_portal
_load_env_file(os.path.join(root_dir, '.env'))

# Connection details
host = os.environ.get('HANA_HOST')
port = int(os.environ.get('HANA_PORT', 30015))
user = os.environ.get('HANA_USER')
password = os.environ.get('HANA_PASSWORD')

def check_counts(schema):
    print(f"--- Checking Schema: {schema} ---")
    try:
        conn = dbapi.connect(address=host, port=port, user=user, password=password)
        cursor = conn.cursor()
        
        # Set Schema
        cursor.execute(f'SET SCHEMA "{schema}"')
        
        # Check B4_COLLECTION_TARGET
        try:
            cursor.execute('SELECT COUNT(*) FROM "B4_COLLECTION_TARGET"')
            count = cursor.fetchone()[0]
            print(f"B4_COLLECTION_TARGET count: {count}")
            
            if count > 0:
                cursor.execute('SELECT SUM("colletion_Target"), SUM("DocTotal") FROM "B4_COLLECTION_TARGET"')
                sums = cursor.fetchone()
                print(f"B4_COLLECTION_TARGET sums: Target={sums[0]}, DocTotal={sums[1]}")
        except Exception as e:
            print(f"Error checking B4_COLLECTION_TARGET: {e}")

        # Check OINV (for Profit report)
        try:
            cursor.execute('SELECT COUNT(*) FROM "OINV"')
            count = cursor.fetchone()[0]
            print(f"OINV count: {count}")
        except Exception as e:
            print(f"Error checking OINV: {e}")

        cursor.close()
        conn.close()
    except Exception as e:
        print(f"Connection failed: {e}")

if __name__ == '__main__':
    check_counts("4B-BIO_APP")
    check_counts("4B-ORANG_APP")
