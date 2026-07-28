
# --- bootstrap: this script lives in <app>/scripts/, so locate the project ---
import os as _os
import sys as _sys
from pathlib import Path as _P

PROJECT_DIR = _P(__file__).resolve().parents[2]   # web_portal/ (holds manage.py)
REPO_DIR = PROJECT_DIR.parent                     # django_web_portal/ (holds .env)
if str(PROJECT_DIR) not in _sys.path:
    _sys.path.insert(0, str(PROJECT_DIR))
_os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'web_portal.settings')
# --- end bootstrap ---

from hdbcli import dbapi
import os
from dotenv import load_dotenv

load_dotenv(REPO_DIR / '.env')

conn = dbapi.connect(
    address=os.getenv('HANA_HOST'),
    port=int(os.getenv('HANA_PORT')),
    user=os.getenv('HANA_USER'),
    password=os.getenv('HANA_PASSWORD')
)

cursor = conn.cursor()
cursor.execute("SELECT SCHEMA_NAME FROM SYS.SCHEMAS WHERE HAS_PRIVILEGES = 'TRUE' ORDER BY SCHEMA_NAME")
schemas = cursor.fetchall()

print("Available schemas:")
for schema in schemas:
    print(f"  - {schema[0]}")

conn.close()
