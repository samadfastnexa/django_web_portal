import os
import sys
import hana_connect

# Load env
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
env_path = os.path.join(project_root, '.env')
if not os.path.exists(env_path):
    env_path = os.path.join(os.path.dirname(hana_connect.__file__), '.env')

print(f"Loading env from: {env_path}")
hana_connect._load_env_file(env_path)

# Connect
host = os.environ.get('HANA_HOST')
port = os.environ.get('HANA_PORT', '30015')
user = os.environ.get('HANA_USER')
password = os.environ.get('HANA_PASSWORD')

if not host or not user or not password:
    print("Missing HANA credentials")
    sys.exit(1)

print(f"Connecting to {host}:{port} as {user}...")
try:
    db = hana_connect._connect_hdbcli(host, port, user, password, None, None, None)
    print("Connected.")
except Exception as e:
    print(f"Connection failed: {e}")
    sys.exit(1)

# Run query
print("Running sales_vs_achievement_geo_inv...")
try:
    # Set default schema if needed for the query context (though the query uses table names directly,
    # hana_connect functions often rely on default schema or synonyms. 
    # But sales_vs_achievement_geo_inv uses 'OINV', 'OCRD' etc directly.
    # In HANA, if user is FASTAPP, it defaults to FASTAPP schema.
    # We might need to set schema.
    # hana_connect.py doesn't set schema in the function, it assumes tables are accessible.
    # Wait, the user error was "invalid column name", not "invalid table name".
    # So table resolution was fine.
    
    # We might need to set current schema.
    cursor = db.cursor()
    cursor.execute("SET SCHEMA \"4B-BIO_APP\"") 
    
    rows = hana_connect.sales_vs_achievement_geo_inv(db)
    print(f"Query successful. Returned {len(rows)} rows.")
    if rows:
        print("First row:", rows[0])
except Exception as e:
    print(f"Query failed: {e}")
    import traceback
    traceback.print_exc()
