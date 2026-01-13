import os
import sys
import hana_connect

# Load env
# Try to find .env in project root
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
env_path = os.path.join(project_root, '.env')

if not os.path.exists(env_path):
    # Fallback to current dir
    env_path = os.path.join(os.path.dirname(hana_connect.__file__), '.env')

print(f"Loading env from: {env_path}")
hana_connect._load_env_file(env_path)

# Connect
host = os.environ.get('HANA_HOST')
port = os.environ.get('HANA_PORT', '30015')
user = os.environ.get('HANA_USER')
password = os.environ.get('HANA_PASSWORD')

if not host or not user or not password:
    print("Missing HANA credentials in env")
    # Try to print env keys to see what we have
    print("Env keys:", list(os.environ.keys()))
    sys.exit(1)

print(f"Connecting to {host}:{port} as {user}...")

try:
    db = hana_connect._connect_hdbcli(host, port, user, password, None, None, None)
    print("Connected.")
except Exception as e:
    print(f"Connection failed: {e}")
    sys.exit(1)

# List columns
schemas_to_try = ['4B-BIO', '4B-BIO_APP', '4B-ORANG', '4B-ORANG_APP']
found_schema = None

for schema in schemas_to_try:
    print(f"\nChecking schema {schema}...")
    try:
        # Check if schema exists
        rows = hana_connect._fetch_all(db, "SELECT SCHEMA_NAME FROM SYS.SCHEMAS WHERE SCHEMA_NAME = ?", (schema,))
        if not rows:
            print(f"Schema {schema} does not exist.")
            continue
            
        print(f"Schema {schema} exists.")
        
        # Check table
        rows = hana_connect._fetch_all(db, "SELECT TABLE_NAME FROM SYS.TABLES WHERE SCHEMA_NAME = ? AND TABLE_NAME = 'OINV'", (schema,))
        if not rows:
            print(f"Table OINV does not exist in {schema}.")
            continue
            
        print(f"Table OINV exists in {schema}.")
        found_schema = schema
        break
        
    except Exception as e:
        print(f"Error checking schema {schema}: {e}")

if found_schema:
    print(f"\nListing columns for {found_schema}.OINV...")
    try:
        cols = hana_connect.table_columns(db, found_schema, 'OINV')
        print(f"Found {len(cols)} columns in OINV:")
        # Check for similar names
        print("\nSearching for similar names to 'OpenCreQty' in OINV...")
        found = False
        for c in cols:
            if 'open' in c.lower() or 'qty' in c.lower() or 'cre' in c.lower() or 'ach' in c.lower():
                print(f"  - {c}")
                found = True
        if not found:
            print("  None found.")

        # Check INV1
        print(f"\nListing columns for {found_schema}.INV1...")
        cols_inv1 = hana_connect.table_columns(db, found_schema, 'INV1')
        print(f"Found {len(cols_inv1)} columns in INV1:")
        print("\nSearching for similar names to 'OpenCreQty' in INV1...")
        for c in cols_inv1:
            if 'open' in c.lower() or 'qty' in c.lower() or 'cre' in c.lower():
                print(f"  - {c}")

    except Exception as e:
        print(f"Error listing columns: {e}")
        import traceback
        traceback.print_exc()
else:
    print("\nCould not find OINV table in expected schemas.")
