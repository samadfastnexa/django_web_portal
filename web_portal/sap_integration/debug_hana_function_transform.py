
import os
import sys
from hdbcli import dbapi

def _load_env_file(filepath):
    if not os.path.exists(filepath):
        print(f"Skipping {filepath} (not found)")
        return
    print(f"Loading {filepath}")
    with open(filepath, 'r') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            if '=' in line:
                key, val = line.split('=', 1)
                os.environ[key.strip()] = val.strip()

# Load env
base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
root_dir = os.path.dirname(base_dir)
_load_env_file(os.path.join(root_dir, '.env'))

# Connection details
host = os.environ.get('HANA_HOST')
port = int(os.environ.get('HANA_PORT') or 30015)
user = os.environ.get('HANA_USER')
password = os.environ.get('HANA_PASSWORD')
schema = '4B-BIO_APP' # Hardcoded to test BIO

print(f"Connecting to {host}:{port} user={user} schema={schema}")

# Import the function from hana_connect
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from hana_connect import sales_vs_achievement_geo_inv

def test_transform():
    try:
        conn = dbapi.connect(address=host, port=port, user=user, password=password)
        cursor = conn.cursor()
        cursor.execute(f'SET SCHEMA "{schema}"')
        cursor.close()
        
        # Simulate view parameters (defaults)
        emp_val = None
        region_param = None
        zone_param = None
        territory_param = None
        start_date_param = None
        end_date_param = None
        in_millions_param = '' # 'true' or ''
        group_by_emp = False

        print("Calling sales_vs_achievement_geo_inv with defaults...")
        data = sales_vs_achievement_geo_inv(
            conn, 
            emp_id=emp_val,
            region=region_param, 
            zone=zone_param, 
            territory=territory_param,
            start_date=start_date_param,
            end_date=end_date_param,
            group_by_emp=group_by_emp
        )
        print(f"Raw rows returned: {len(data)}")
        if len(data) > 0:
            print(f"First raw row keys: {data[0].keys()}")
        else:
            print("No raw data returned.")
            return

        # Transformation Logic
        scaled = []
        for row in data or []:
            if isinstance(row, dict):
                r = dict(row)
                try:
                    v = r.get('Collection_Target')
                    if v is None: v = r.get('COLLECTION_TARGET')
                    if v is None: v = r.get('colletion_Target')
                    if v is not None:
                        r['Collection_Target'] = round((float(v) / 1000000.0), 2)
                except Exception:
                    pass
                try:
                    v = r.get('Collection_Achievement')
                    if v is None: v = r.get('COLLECTION_ACHIEVEMENT')
                    if v is None: v = r.get('DocTotal')
                    if v is not None:
                        r['Collection_Achievement'] = round((float(v) / 1000000.0), 2)
                except Exception:
                    pass
                scaled.append(r)
            else:
                scaled.append(row)
        data = scaled

        # Hierarchy
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

        print(f"Hierarchy keys: {list(hierarchy.keys())}")
        
        conn.close()
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_transform()
