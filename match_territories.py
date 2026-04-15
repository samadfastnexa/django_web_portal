import django
import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'web_portal'))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'web_portal.settings')
django.setup()

from sap_integration.hana_connect import _fetch_all, _load_env_file

_load_env_file(os.path.join(os.path.dirname(__file__), 'web_portal', 'sap_integration', '.env'))
_load_env_file(os.path.join(os.path.dirname(__file__), '.env'))

try:
    from hdbcli import dbapi
    from FieldAdvisoryService.models import Territory
    
    cfg_host = os.environ.get('HANA_HOST') or ''
    cfg_port = os.environ.get('HANA_PORT') or '30015'
    cfg_user = os.environ.get('HANA_USER') or ''
    cfg_pwd = os.environ.get('HANA_PASSWORD') or ''
    
    kwargs = {'address': cfg_host, 'port': int(cfg_port), 'user': cfg_user, 'password': cfg_pwd}
    conn = dbapi.connect(**kwargs)
    
    # Set schema
    cur = conn.cursor()
    cur.execute('SET SCHEMA "4B-AGRI_LIVE"')
    cur.close()
    
    # Get all HANA territories
    sql_hana = "SELECT \"territryID\", \"descript\" FROM OTER ORDER BY \"territryID\""
    hana_territories = _fetch_all(conn, sql_hana)
    print(f"=== Found {len(hana_territories)} territories in HANA ===")
    
    # Get all Django territories
    django_territories = Territory.objects.filter(company__name='4B-AGRI_LIVE').all()
    print(f"=== Found {len(django_territories)} territories in Django for 4B-AGRI_LIVE ===\n")
    
    # Try to match them
    print("=== Attempting to match Django territories with HANA ===")
    for dt in django_territories[:10]:  # First 10
        print(f"\nDjango Territory {dt.id}: '{dt.name}'")
        # Search for similar names in HANA
        matches = []
        for ht in hana_territories:
            desc = ht['descript'].upper() if ht['descript'] else ''
            django_upper = dt.name.upper()
            if django_upper in desc or desc in django_upper[:20]:  # Check if it's a substring or close
                matches.append(ht)
        
        if matches:
            print(f"  Possible HANA matches:")
            for m in matches[:3]:
                print(f"    - Territory ID {m['territryID']}: {m['descript']}")
        else:
            print(f"  ❌ No matches found in HANA")
    
    conn.close()
    
except Exception as e:
    print(f'Error: {e}')
    import traceback
    traceback.print_exc()
