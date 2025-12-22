
import os
import sys
import django

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'web_portal.settings')
django.setup()

from preferences.models import Setting

try:
    s = Setting.objects.filter(slug='SAP_COMPANY_DB').first()
    print(f"SAP_COMPANY_DB: {s.value if s else 'Not Found'}")
except Exception as e:
    print(f"Error: {e}")
