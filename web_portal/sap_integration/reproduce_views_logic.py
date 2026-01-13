
import os
import sys
import django
from django.conf import settings
from decimal import Decimal

# Setup Django environment
base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__))) # This is .../web_portal
sys.path.append(base_dir) # Add .../web_portal to path
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "web_portal.settings")
django.setup()

# Move hana_connect import AFTER django setup to avoid issues if it imports django stuff
from sap_integration.hana_connect import sales_vs_achievement_geo_inv
from hdbcli import dbapi

def load_env(path):
    with open(path) as f:
        for line in f:
            if line.strip() and not line.startswith('#'):
                k, v = line.strip().split('=', 1)
                os.environ[k] = v

root_dir = os.path.dirname(base_dir)
env_path = os.path.join(root_dir, '.env')
print(f"Loading .env from: {env_path}")
load_env(env_path)

def test_views_logic(schema_name):
    print(f"--- Testing Schema: {schema_name} ---")
    host = os.environ.get('HANA_HOST')
    port = int(os.environ.get('HANA_PORT', 30015))
    user = os.environ.get('HANA_USER')
    password = os.environ.get('HANA_PASSWORD')

    conn = dbapi.connect(address=host, port=port, user=user, password=password)
    cur = conn.cursor()
    cur.execute(f'SET SCHEMA "{schema_name}"')
    cur.close()

    # Simulate request params (empty dates, default in_millions)
    start_date = None
    end_date = None
    in_millions_param = '' # Default from request.GET.get('in_millions') or ''
    
    # 1. Fetch Data
    print("Fetching data...")
    data = sales_vs_achievement_geo_inv(conn, start_date=start_date, end_date=end_date)
    print(f"Fetched {len(data)} rows.")
    if data:
        print(f"First row raw: {data[0]}")

    # 2. Scaling Logic
    scaled = []
    # Logic from views.py:587
    if in_millions_param in ('', 'true','1','yes','y'):
        print("Scaling to millions (default behavior)...")
        for row in data:
            r = dict(row)
            try:
                v = r.get('Collection_Target')
                if v is None: v = r.get('COLLECTION_TARGET')
                if v is None: v = r.get('colletion_Target')
                if v is not None:
                    # DEBUG PRINT
                    # print(f"Scaling value: {v} type: {type(v)}")
                    r['Collection_Target'] = round((float(v) / 1000000.0), 2)
            except Exception as e:
                print(f"Error scaling Collection_Target: {e}")
                pass
            
            try:
                v = r.get('Collection_Achievement')
                if v is None: v = r.get('COLLECTION_ACHIEVEMENT')
                if v is None: v = r.get('DocTotal')
                if v is not None:
                    r['Collection_Achievement'] = round((float(v) / 1000000.0), 2)
            except Exception as e:
                print(f"Error scaling Collection_Achievement: {e}")
                pass
            scaled.append(r)
        data = scaled
    else:
        print("Not scaling.")

    if data:
        print(f"First row scaled: {data[0]}")

    # 3. Hierarchy Transformation
    print("Transforming hierarchy...")
    hierarchy = {}
    for row in (data or []):
        if not isinstance(row, dict):
            continue
        reg = row.get('Region', 'Unknown Region')
        zon = row.get('Zone', 'Unknown Zone')
        ter = row.get('Territory', 'Unknown Territory')
        sal = 0.0
        ach = 0.0
        try:
            v = row.get('Collection_Target')
            if v is None: v = row.get('COLLECTION_TARGET')
            if v is None: v = row.get('colletion_Target')
            sal = float(v or 0.0)
        except: pass
        try:
            v = row.get('Collection_Achievement')
            if v is None: v = row.get('COLLECTION_ACHIEVEMENT')
            if v is None: v = row.get('DocTotal')
            ach = float(v or 0.0)
        except: pass

        if reg not in hierarchy:
            hierarchy[reg] = {'name': reg, 'sales': 0.0, 'achievement': 0.0, 'zones': {}}
        
        hierarchy[reg]['sales'] += sal
        hierarchy[reg]['achievement'] += ach
        
        if zon not in hierarchy[reg]['zones']:
            hierarchy[reg]['zones'][zon] = {'name': zon, 'sales': 0.0, 'achievement': 0.0, 'territories': []}
            
        hierarchy[reg]['zones'][zon]['sales'] += sal
        hierarchy[reg]['zones'][zon]['achievement'] += ach
        
        hierarchy[reg]['zones'][zon]['territories'].append({
            'name': ter,
            'sales': sal,
            'achievement': ach,
            'employee_name': row.get('EmployeeName', '')
        })

    # 4. Flattening to Final List
    final_list = []
    for r_name in sorted(hierarchy.keys()):
        r_data = hierarchy[r_name]
        zones_list = []
        # Convert zones dict to list
        for z_name in sorted(r_data['zones'].keys()):
            z_data = r_data['zones'][z_name]
            z_data['territories'] = sorted(z_data['territories'], key=lambda x: x['name'])
            zones_list.append(z_data)
        r_data['zones'] = zones_list
        final_list.append(r_data)

    # 5. Rounding
    for r in final_list:
        r['sales'] = round(r['sales'], 2)
        r['achievement'] = round(r['achievement'], 2)
        for z in r['zones']:
            z['sales'] = round(z['sales'], 2)
            z['achievement'] = round(z['achievement'], 2)

    print(f"Final List Count: {len(final_list)}")
    if final_list:
        r = final_list[0]
        print(f"Region: {r['name']}, Sales: {r['sales']}, Ach: {r['achievement']}")
        if r['zones']:
            z = r['zones'][0]
            print(f"  Zone: {z['name']}, Sales: {z['sales']}, Ach: {z['achievement']}")
            if z['territories']:
                t = z['territories'][0]
                print(f"    Territory: {t['name']}, Sales: {t['sales']}, Ach: {t['achievement']}")

    conn.close()

if __name__ == '__main__':
    test_views_logic('4B-BIO_APP')
    test_views_logic('4B-ORANG_APP')
