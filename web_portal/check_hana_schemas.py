import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'web_portal.settings')
django.setup()

from hdbcli import dbapi
from pathlib import Path
from django.conf import settings

# Load environment variables
def load_env_file(path):
    if os.path.exists(path):
        with open(path) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    os.environ[key.strip()] = value.strip()

try:
    load_env_file(os.path.join(settings.BASE_DIR.parent, '.env'))
    load_env_file(os.path.join(settings.BASE_DIR, '.env'))
except Exception:
    pass

# Connect to HANA
cfg = {
    'host': os.environ.get('HANA_HOST', ''),
    'port': os.environ.get('HANA_PORT', '30015'),
    'user': os.environ.get('HANA_USER', ''),
    'password': os.environ.get('HANA_PASSWORD', ''),
}

print(f"Connecting to HANA: {cfg['host']}:{cfg['port']} as {cfg['user']}")

kwargs = {
    'address': cfg['host'],
    'port': int(cfg['port']),
    'user': cfg['user'],
    'password': cfg['password']
}

encrypt = os.environ.get('HANA_ENCRYPT', '')
if encrypt.strip().lower() in ('true', '1', 'yes'):
    kwargs['encrypt'] = True
    ssl_validate = os.environ.get('HANA_SSL_VALIDATE', '')
    if ssl_validate.strip().lower() in ('true', '1', 'yes'):
        kwargs['sslValidateCertificate'] = True
    else:
        kwargs['sslValidateCertificate'] = False

try:
    conn = dbapi.connect(**kwargs)
    cur = conn.cursor()
    
    # Query all schemas
    sql = """
    SELECT SCHEMA_NAME 
    FROM SYS.SCHEMAS 
    WHERE SCHEMA_NAME LIKE '4B%' 
    ORDER BY SCHEMA_NAME
    """
    
    print("\nSchemas in SAP HANA that start with '4B':")
    print("-" * 60)
    
    cur.execute(sql)
    rows = cur.fetchall()
    
    for row in rows:
        schema_name = row[0]
        print(f"  {schema_name}")
    
    print(f"\nTotal: {len(rows)} schemas found")
    
    # Also check from Company table
    print("\n" + "=" * 60)
    print("Companies in Django database:")
    print("-" * 60)
    
    from FieldAdvisoryService.models import Company
    companies = Company.objects.filter(is_active=True)
    
    for c in companies:
        print(f"  name={c.name:25} Company_name={c.Company_name}")
    
    print("\n" + "=" * 60)
    print("Comparison:")
    print("-" * 60)
    
    hana_schemas = {row[0] for row in rows}
    django_schemas = {c.Company_name for c in companies}
    
    print("\nIn Django but NOT in HANA:")
    for s in django_schemas - hana_schemas:
        print(f"  {s}")
        # Try with hyphen to underscore conversion
        converted = s.replace('-', '_')
        if converted in hana_schemas:
            print(f"    -> Exists in HANA as: {converted}")
    
    print("\nIn HANA but NOT in Django:")
    for s in hana_schemas - django_schemas:
        print(f"  {s}")
    
    cur.close()
    conn.close()
    
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
