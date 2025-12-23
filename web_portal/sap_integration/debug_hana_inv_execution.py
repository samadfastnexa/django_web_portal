import os
import sys
from hdbcli import dbapi

def _load_env_file(path: str) -> None:
    if not os.path.exists(path):
        return
    try:
        with open(path, 'r') as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                if '=' in line:
                    k, v = line.split('=', 1)
                    k = k.strip()
                    v = v.strip()
                    if v.startswith('"') and v.endswith('"'):
                        v = v[1:-1]
                    elif v.startswith("'") and v.endswith("'"):
                        v = v[1:-1]
                    os.environ[k] = v
    except Exception:
        pass

# Load env
base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
root_dir = os.path.dirname(base_dir)
_load_env_file(os.path.join(root_dir, '.env'))

# Connection details
host = os.environ.get('HANA_HOST')
port = int(os.environ.get('HANA_PORT', 30015))
user = os.environ.get('HANA_USER')
password = os.environ.get('HANA_PASSWORD')

def debug_inv_query(schema):
    print(f"\n--- Debugging {schema} ---")
    try:
        conn = dbapi.connect(address=host, port=port, user=user, password=password)
        cursor = conn.cursor()
        cursor.execute(f'SET SCHEMA "{schema}"')

        # 1. Check OTER columns
        print("\nChecking OTER columns...")
        try:
            cursor.execute('SELECT * FROM "OTER" LIMIT 1')
            columns = [col[0] for col in cursor.description]
            print(f"OTER Columns: {columns}")
        except Exception as e:
            print(f"Error checking OTER: {e}")

        # 2. Check OTER data count
        try:
            cursor.execute('SELECT COUNT(*) FROM "OTER"')
            count = cursor.fetchone()[0]
            print(f"OTER row count: {count}")
        except Exception as e:
            print(f"Error counting OTER: {e}")

        # 3. Run the exact SQL from sales_vs_achievement_geo_inv (lines 258-280 of hana_connect.py)
        print("\nRunning Full Query...")
        coll_tbl = '"B4_COLLECTION_TARGET"'
        oter_tbl = '"OTER"'
        emp_tbl = '"B4_EMP"'
        ohem_tbl = '"OHEM"'
        
        sql = (
            'SELECT '
            '    COALESCE(R3."descript", R2."descript", R1."descript") AS "Region", '
            '    Z."descript" AS "Zone", '
            '    T."descript" AS "Territory", '
            '    STRING_AGG(HE."firstName" || \' \' || HE."lastName", \', \') AS "EmployeeName", '
            '    SUM(c.colletion_Target) AS "Collection_Target", '
            '    SUM(c.DocTotal) AS "Collection_Achievement" '
            'FROM ' + coll_tbl + ' c '
            'INNER JOIN ' + oter_tbl + ' T '
            '    ON T."territryID" = c.TerritoryId '
            'LEFT JOIN ' + oter_tbl + ' Z '
            '    ON Z."territryID" = T."parent" '
            'LEFT JOIN ' + oter_tbl + ' R1 '
            '    ON R1."territryID" = Z."parent" '
            'LEFT JOIN ' + oter_tbl + ' R2 '
            '    ON R2."territryID" = R1."parent" '
            'LEFT JOIN ' + oter_tbl + ' R3 '
            '    ON R3."territryID" = R2."parent" '
            'LEFT JOIN ' + emp_tbl + ' E '
            '    ON E."U_TID" = T."territryID" '
            'LEFT JOIN ' + ohem_tbl + ' HE '
            '    ON HE."empID" = E.empID '
            ' GROUP BY '
            '    COALESCE(R3."descript", R2."descript", R1."descript"), '
            '    Z."descript", '
            '    T."territryID", '
            '    T."descript" '
            ' ORDER BY 1, 2, 3'
        )
        
        try:
            cursor.execute(sql)
            rows = cursor.fetchall()
            print(f"Query returned {len(rows)} rows.")
            for row in rows[:5]:
                print(row)
        except Exception as e:
            print(f"Query failed: {e}")

        cursor.close()
        conn.close()
    except Exception as e:
        print(f"Connection/Execution failed: {e}")

if __name__ == '__main__':
    debug_inv_query("4B-ORANG_APP")
