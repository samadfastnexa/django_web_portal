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
base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
root_dir = os.path.dirname(base_dir)
_load_env_file(os.path.join(root_dir, '.env'))

# Connection details
host = os.environ.get('HANA_HOST')
port = int(os.environ.get('HANA_PORT', 30015))
user = os.environ.get('HANA_USER')
password = os.environ.get('HANA_PASSWORD')

def list_columns(schema, table):
    print(f"--- Checking Columns for {schema}.{table} ---")
    try:
        conn = dbapi.connect(address=host, port=port, user=user, password=password)
        cursor = conn.cursor()
        cursor.execute(f'SET SCHEMA "{schema}"')
        cursor.close()

        tables_to_check = ['B4_COLLECTION_TARGET', 'OINV']
        
        for table_name in tables_to_check:
            print(f"\nChecking columns for table: {table_name}")
            sql = f"SELECT COLUMN_NAME FROM SYS.COLUMNS WHERE TABLE_NAME = '{table_name}' AND SCHEMA_NAME = CURRENT_SCHEMA ORDER BY POSITION"
            
            try:
                cursor = conn.cursor()
                cursor.execute(sql)
                rows = cursor.fetchall()
                cursor.close()
                
                if not rows:
                    print(f"No columns found for table {table_name} (Table might not exist in this schema)")
                else:
                    print(f"Columns in {table_name}:")
                    for row in rows:
                        print(f"  - {row[0]}")
                        
            except Exception as e:
                print(f"Error querying columns for {table_name}: {e}")
        conn.close()
    except Exception as e:
        print(f"Connection failed: {e}")

if __name__ == '__main__':
    list_columns("4B-BIO_APP", "B4_COLLECTION_TARGET")
