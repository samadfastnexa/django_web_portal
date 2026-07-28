
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
import sys
import django

# Setup Django environment
current_dir = str(PROJECT_DIR)
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'web_portal.settings')
try:
    django.setup()
except Exception as e:
    print(f"Warning: Django setup failed ({e})")

from FieldAdvisoryService.models import SalesOrder

def fix_order():
    try:
        order = SalesOrder.objects.get(pk=32)
        print(f"Current Order #32:")
        print(f"  CardCode: {order.card_code}")
        print(f"  CardName: {order.card_name}")
        print(f"  SAP Error: {order.sap_error}")

        new_code = 'ORC02041'
        print(f"\nUpdating CardCode to '{new_code}' (The BP created by your script)...")
        
        order.card_code = new_code
        # Optionally update name to match the BP if desired, but keeping original order name is often better for history
        # order.card_name = "Test Partner BIC01563" 
        
        # Clear previous errors so it looks clean
        order.sap_error = None
        order.sap_response_json = None
        order.save()
        
        print("✓ Order #32 updated successfully.")
        print("You can now try posting it to SAP again.")

    except SalesOrder.DoesNotExist:
        print("SalesOrder #32 does not exist.")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == '__main__':
    fix_order()
