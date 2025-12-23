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

def check_join(schema):
    print(f"--- Checking JOIN for {schema} ---")
    try:
        conn = dbapi.connect(address=host, port=port, user=user, password=password)
        cursor = conn.cursor()
        cursor.execute(f'SET SCHEMA "{schema}"')
        
        # Check OTER count
        cursor.execute('SELECT COUNT(*) FROM "OTER"')
        oter_count = cursor.fetchone()[0]
        print(f"OTER count: {oter_count}")
        
        # Check JOIN count
        sql = (
            'SELECT COUNT(*) '
            'FROM "B4_COLLECTION_TARGET" c '
            'INNER JOIN "OTER" T '
            '    ON T."territryID" = c.TerritoryId '
        )
        cursor.execute(sql)
        join_count = cursor.fetchone()[0]
        print(f"JOIN count: {join_count}")
        
        if join_count == 0:
            print("JOIN returned 0 rows! Checking TerritoryId mismatch...")
            cursor.execute('SELECT DISTINCT TerritoryId FROM "B4_COLLECTION_TARGET" LIMIT 5')
            c_ids = [str(r[0]) for r in cursor.fetchall()]
            print(f"Sample TerritoryIds from B4_COLLECTION_TARGET: {c_ids}")
            
            cursor.execute('SELECT "territryID" FROM "OTER" LIMIT 5')
            t_ids = [str(r[0]) for r in cursor.fetchall()]
            print(f"Sample territryIDs from OTER: {t_ids}")

        cursor.close()
        conn.close()
    except Exception as e:
        print(f"Error: {e}")

if __name__ == '__main__':
    check_join("4B-BIO_APP")
    check_join("4B-ORANG_APP")
