import os
import sys
import django
import json
from django.test import RequestFactory

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'web_portal.settings')
django.setup()

from sap_integration.views import sales_vs_achievement_api

class MockUser:
    is_authenticated = True
    is_staff = True
    is_active = True

def main():
    factory = RequestFactory()
    request = factory.get('/api/sap/sales-vs-achievement/', {'emp_id': '729', 'territory': 'D.G Khan Territory'})
    request.user = MockUser()
    response = sales_vs_achievement_api(request)
    print("Status Code:", response.status_code)
    try:
        response.render()
    except Exception:
        pass
    content = getattr(response, 'content', b'').decode('utf-8') if hasattr(response, 'content') else json.dumps(getattr(response, 'data', {}))
    print("Raw JSON:", content[:1000])
    try:
        data = json.loads(content)
    except Exception:
        data = {}
    rows = data.get('data') or []
    print("Total Rows:", len(rows))
    dg = [r for r in rows if isinstance(r, dict) and (r.get('TERRITORYNAME') == 'D.G Khan Territory')]
    if dg:
        print("D.G Khan Territory Row:", json.dumps(dg[0], ensure_ascii=False))
    else:
        print("D.G Khan Territory not found in result")

if __name__ == '__main__':
    main()
