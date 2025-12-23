import os
import sys
# Add path to site-packages if needed, but standard python should have hdbcli if installed in environment
try:
    from hdbcli import dbapi
except ImportError:
    print("hdbcli not found")
    sys.exit(1)

# Load env
def load_env(path):
    if os.path.exists(path):
        with open(path) as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('#'): continue
                if '=' in line:
                    k, v = line.split('=', 1)
                    os.environ[k] = v.strip().strip('"').strip("'")

# Try to find .env
paths = [
    r'f:\samad\clone tarzan\.env',
    r'f:\samad\clone tarzan\django_web_portal\.env',
    os.path.join(os.getcwd(), '.env')
]
for p in paths:
    if os.path.exists(p):
        print(f"Loading env from {p}")
        load_env(p)
        break

host = os.environ.get('HANA_HOST')
port = os.environ.get('HANA_PORT', '30015')
user = os.environ.get('HANA_USER')
password = os.environ.get('HANA_PASSWORD')
schema = os.environ.get('HANA_SCHEMA') or '4B-BIO_APP'

print(f"Connecting to {host}:{port} user={user} schema={schema}")

try:
    conn = dbapi.connect(address=host, port=int(port), user=user, password=password)
    cur = conn.cursor()
    
    schemas_to_check = ['4B-BIO_APP', '4B-ORANG_APP']
    
    for sch in schemas_to_check:
        print(f"\n--- Checking Schema: {sch} ---")
        try:
            cur.execute(f'SET SCHEMA "{sch}"')
        except Exception as e:
            print(f"Could not set schema {sch}: {e}")
            continue

        # Check B4_COLLECTION_TARGET count
        try:
            cur.execute('SELECT COUNT(*) FROM "B4_COLLECTION_TARGET"')
            row = cur.fetchone()
            print(f"B4_COLLECTION_TARGET count: {row[0]}")
        except Exception as e:
            print(f"Error checking B4_COLLECTION_TARGET: {e}")
            continue

        # Check OTER count
        try:
            cur.execute('SELECT COUNT(*) FROM "OTER"')
            row = cur.fetchone()
            print(f"OTER count: {row[0]}")
        except Exception as e:
            print(f"Error checking OTER: {e}")

        # Run sample aggregation query to check columns
        try:
            coll_tbl = '"B4_COLLECTION_TARGET"'
            oter_tbl = '"OTER"'
            sql = (
                'SELECT '
                '    SUM(c.colletion_Target) AS Collection_Target, '
                '    SUM(c.DocTotal) AS Collection_Achievement '
                'FROM ' + coll_tbl + ' c '
                'INNER JOIN ' + oter_tbl + ' T '
                '    ON T."territryID" = c.TerritoryId '
            )
            cur.execute(sql)
            # Get description
            cols = [d[0] for d in cur.description]
            print(f"Query Columns: {cols}")
            row = cur.fetchone()
            print(f"Query Result: {row}")
            
            # Check with quotes if alias was quoted in python code?
            # In python code: '    SUM(c.colletion_Target) AS Collection_Target, '
            # This means column name is COLLECTION_TARGET (uppercase)
            
        except Exception as e:
            print(f"Error running sample query: {e}")

    conn.close()
except Exception as e:
    print(f"Connection failed: {e}")
