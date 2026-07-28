"""
Find parent customers that have child customers
"""

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

import os
import django
import sys

sys.path.insert(0, str(PROJECT_DIR))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'web_portal.settings')
django.setup()

from FieldAdvisoryService.admin import get_hana_connection

db = get_hana_connection()
if not db:
    print("Failed to connect to HANA")
    sys.exit(1)

# Query to find parents with children
query = """
SELECT 
    p."CardCode" AS ParentCode,
    p."CardName" AS ParentName,
    COUNT(c."CardCode") AS ChildCount
FROM OCRD p
INNER JOIN OCRD c ON c."FatherCard" = p."CardCode"
WHERE p."CardType" = 'C' AND p."validFor" = 'Y'
GROUP BY p."CardCode", p."CardName"
HAVING COUNT(c."CardCode") > 0
ORDER BY COUNT(c."CardCode") DESC
"""

cursor = db.cursor()
cursor.execute(query)
results = cursor.fetchall()

print(f"\n=== TOP 20 PARENT CUSTOMERS WITH CHILDREN ===\n")
print(f"{'Parent Code':<15} {'Parent Name':<50} {'Children'}")
print("=" * 75)

for row in results:
    parent_code = row[0]
    parent_name = row[1][:48] if len(row[1]) > 48 else row[1]
    child_count = row[2]
    print(f"{parent_code:<15} {parent_name:<50} {child_count:>8}")

print(f"\n{'='*75}")
print(f"\nTo test child customer dropdown, select any of the above Parent Codes")
print(f"in the Customer Code field.\n")

db.close()
