
import os
import sys
import logging
from decimal import Decimal
from datetime import date, datetime

# Setup environment (mocking what's needed)
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Mock db connection
try:
    import hdbcli.dbapi as dbapi
except ImportError:
    print("hdbcli not found")
    sys.exit(1)

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), '.env'))

def get_connection():
    host = os.environ.get('HANA_HOST')
    port = int(os.environ.get('HANA_PORT', 30015))
    user = os.environ.get('HANA_USER')
    password = os.environ.get('HANA_PASSWORD')
    return dbapi.connect(address=host, port=port, user=user, password=password)

def _fetch_all(db, sql, params=()):
    cur = db.cursor()
    try:
        cur.execute(sql, params)
        rows = cur.fetchall()
        cols = [d[0] for d in cur.description] if cur.description else []
        out = []
        for r in rows:
            row = {}
            for i, c in enumerate(cols):
                row[c] = r[i]
            out.append(row)
        return out
    finally:
        cur.close()

def check_hierarchy(db, schema):
    print(f"\n--- Checking Hierarchy for Schema: {schema} ---")
    sql_set = f'SET SCHEMA "{schema}"'
    cursor = db.cursor()
    cursor.execute(sql_set)
    cursor.close()

    # Check max depth
    sql = """
    SELECT 
        T1."territryID" as Level1_ID, T1."descript" as Level1_Name, T1."parent" as Level1_Parent,
        T2."territryID" as Level2_ID, T2."descript" as Level2_Name, T2."parent" as Level2_Parent,
        T3."territryID" as Level3_ID, T3."descript" as Level3_Name, T3."parent" as Level3_Parent,
        T4."territryID" as Level4_ID, T4."descript" as Level4_Name
    FROM "OTER" T1
    LEFT JOIN "OTER" T2 ON T1."parent" = T2."territryID"
    LEFT JOIN "OTER" T3 ON T2."parent" = T3."territryID"
    LEFT JOIN "OTER" T4 ON T3."parent" = T4."territryID"
    LIMIT 5
    """
    rows = _fetch_all(db, sql)
    for r in rows:
        print(r)

def check_sales_inv_query(db, schema):
    print(f"\n--- Checking Sales Geo Inv Query for Schema: {schema} ---")
    # Using the logic from hana_connect.sales_vs_achievement_geo_inv
    coll_tbl = '"B4_COLLECTION_TARGET"'
    oter_tbl = '"OTER"'
    
    sql = (
        'SELECT '
        '    COALESCE(R3."descript", R2."descript", R1."descript") AS "Region", '
        '    Z."descript" AS "Zone", '
        '    T."descript" AS "Territory", '
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
        'GROUP BY '
        '    COALESCE(R3."descript", R2."descript", R1."descript"), '
        '    Z."descript", '
        '    T."descript" '
        'LIMIT 5'
    )
    try:
        rows = _fetch_all(db, sql)
        print(f"Returned {len(rows)} rows")
        for r in rows:
            print(r)
    except Exception as e:
        print(f"Error: {e}")

def check_profit_query(db, schema):
    print(f"\n--- Checking Sales Geo Profit Query for Schema: {schema} ---")
    # Using the logic from hana_connect.sales_vs_achievement_geo_profit
    # Note: Using INNER JOINS as per original code
    sql = (
        'SELECT '
        '    T3."descript" AS "Region", '
        '    T2."descript" AS "Zone", '
        '    T1."descript" AS "Territory", '
        '    SUM(T0."DocTotal") AS "Sales", '
        '    SUM(T0."GrosProfit") AS "Achievement" '
        'FROM OINV T0 '
        '    INNER JOIN OCRD C0 ON T0."CardCode" = C0."CardCode" '
        '    INNER JOIN OTER T1 ON C0."Territory" = T1."territryID" '
        '    INNER JOIN OTER T2 ON T1."parent" = T2."territryID" '
        '    INNER JOIN OTER T3 ON T2."parent" = T3."territryID" '
        'GROUP BY '
        '    T3."descript", '
        '    T2."descript", '
        '    T1."descript" '
        'LIMIT 5'
    )
    try:
        rows = _fetch_all(db, sql)
        print(f"Returned {len(rows)} rows")
        for r in rows:
            print(r)
    except Exception as e:
        print(f"Error: {e}")

def main():
    conn = get_connection()
    schemas = ['4B-BIO_APP', '4B-ORANG_APP']
    
    for schema in schemas:
        check_hierarchy(conn, schema)
        check_sales_inv_query(conn, schema)
        check_profit_query(conn, schema)
    
    conn.close()

if __name__ == '__main__':
    main()
