import sys
import os
import json
import re
from decimal import Decimal
from datetime import date, datetime, time
import logging

IS_CLI = not os.environ.get("REQUEST_METHOD")
logger = logging.getLogger("hana")

def err(message: str, code: int) -> None:
    if IS_CLI:
        sys.stderr.write(message + "\n")
        sys.exit(code)
    else:
        sys.stdout.write("Status: 500\r\n")
        sys.stdout.write("Content-Type: text/plain\r\n\r\n")
        sys.stdout.write(message + "\n")
        sys.exit(code)

def _json_default(o):
    if isinstance(o, Decimal):
        return str(o)
    if isinstance(o, (date, datetime, time)):
        try:
            return o.isoformat()
        except Exception:
            return str(o)
    return str(o)

def out_json(rows) -> None:
    if not IS_CLI:
        sys.stdout.write("Content-Type: application/json\r\n\r\n")
    sys.stdout.write(json.dumps(rows, ensure_ascii=False, default=_json_default) + "\n")

def out_text(text: str) -> None:
    if not IS_CLI:
        sys.stdout.write("Content-Type: text/plain\r\n\r\n")
    sys.stdout.write(text + "\n")

def quote_ident(ident: str) -> str:
    q = ident.replace('"', '""')
    return '"' + q + '"'

def _fetch_all(db, sql: str, params=()):
    cur = db.cursor()
    cur.execute(sql, params)
    rows = cur.fetchall()
    cols = [d[0] for d in cur.description] if cur.description else []
    out = []
    for r in rows:
        if isinstance(r, dict):
            out.append(dict(r))
        else:
            row = {}
            for i, c in enumerate(cols):
                v = None
                try:
                    v = r[i]
                except Exception:
                    try:
                        v = getattr(r, c)
                    except Exception:
                        v = None
                row[c] = v
            out.append(row)
    cur.close()
    return out

def _fetch_one(db, sql: str, params=()):
    cur = db.cursor()
    cur.execute(sql, params)
    row = cur.fetchone()
    cols = [d[0] for d in cur.description] if cur.description else []
    cur.close()
    if row is None:
        return None
    if isinstance(row, dict):
        return dict(row)
    out = {}
    for i, c in enumerate(cols):
        v = None
        try:
            v = row[i]
        except Exception:
            try:
                v = getattr(row, c)
            except Exception:
                v = None
        out[c] = v
    return out

def select_oitm(db, schema: str) -> list:
    sch = schema.strip() if schema is not None else ''
    sch_sql = ''
    if sch != '':
        sch_sql = sch if re.match(r'^[A-Za-z0-9_]+$', sch) else quote_ident(sch)
    tbl = quote_ident('OITM')
    table_ref = (sch_sql + '.' + tbl) if sch_sql != '' else tbl
    sql = 'SELECT * FROM ' + table_ref
    return _fetch_all(db, sql)

def get_tables_count(db, schema: str) -> int:
    if schema and schema.strip() != '':
        sql = 'SELECT COUNT(*) AS TABLE_COUNT FROM SYS.TABLES WHERE SCHEMA_NAME = CURRENT_SCHEMA'
    else:
        sql = 'SELECT COUNT(*) AS TABLE_COUNT FROM SYS.TABLES'
    row = _fetch_one(db, sql)
    if not row:
        return 0
    v = row.get('TABLE_COUNT')
    if v is None:
        try:
            v = list(row.values())[0]
        except Exception:
            v = 0
    try:
        return int(v)
    except Exception:
        return 0

def territory_summary(db, emp_id: int | None = None, territory_name: str | None = None, year: int | None = None, month: int | None = None, start_date: str | None = None, end_date: str | None = None) -> list:
    base = (
        'select '
        ' c.TerritoryId, '
        ' O."descript" as TerritoryName, '
        ' sum(c.colletion_Target) as colletion_Target, '
        ' sum(c.DocTotal) as DocTotal, '
        ' F_REFDATE, '
        ' T_REFDATE '
        ' from "4B-BIO_APP"."B4_COLLECTION_TARGET" c '
        ' INNER JOIN "4B-ORANG_APP"."OTER" O ON O."territryID" = c.TerritoryId '
    )
    where_clauses = []
    params = []
    if emp_id is not None:
        where_clauses.append(
            ' TerritoryId in (select U_TID from "4B-BIO_APP"."B4_EMP" where empID = ?)' 
        )
        params.append(emp_id)
    if territory_name is not None and territory_name.strip() != '':
        where_clauses.append(' O."descript" = ?')
        params.append(territory_name.strip())
    if start_date and end_date:
        where_clauses.append(" F_REFDATE >= TO_DATE(?, 'YYYY-MM-DD') AND T_REFDATE <= TO_DATE(?, 'YYYY-MM-DD') ")
        params.extend([start_date.strip(), end_date.strip()])
    elif year is not None and month is not None and 1 <= int(month) <= 12:
        y = int(year)
        m = int(month)
        start = date(y, m, 1)
        if m == 12:
            next_start = date(y + 1, 1, 1)
        else:
            next_start = date(y, m + 1, 1)
        start_str = start.strftime('%Y-%m-%d')
        next_str = next_start.strftime('%Y-%m-%d')
        where_clauses.append(" F_REFDATE >= TO_DATE(?, 'YYYY-MM-DD') AND T_REFDATE < TO_DATE(?, 'YYYY-MM-DD') ")
        params.extend([start_str, next_str])
    where_sql = ''
    if len(where_clauses) > 0:
        where_sql = ' where ' + ' AND '.join(where_clauses)
    tail = (
        ' group by c.TerritoryId, '
        ' O."descript", '
        ' F_REFDATE, '
        ' T_REFDATE '
        ' ORDER BY c.TerritoryId, '
        ' F_REFDATE, '
        ' T_REFDATE'
    )
    sql = base + where_sql + tail
    return _fetch_all(db, sql, tuple(params))

def territory_names(db) -> list:
    sql = (
        'select distinct O."descript" as TerritoryName '
        ' from "4B-ORANG_APP"."OTER" O '
        ' order by O."descript"'
    )
    return _fetch_all(db, sql)

def products_catalog(db) -> list:
    sql = (
        'SELECT '
        ' T1."ItmsGrpCod", '
        ' substr(T1."ItmsGrpNam",\'4\') AS ItmsGrpNam, '
        ' T0."U_PCN" AS "Product_Catalog_Name", '
        ' T0."ItemCode", '
        ' T0."ItemName", '
        ' T0."U_GenericName", '
        ' T0."U_BrandName", '
        ' T0."SalPackMsr", '
        ' (SELECT T2."FileName"||\'.\'||T2."FileExt" FROM "ATC1" T2 WHERE T2."U_IMG_C" = \'Product Image\' AND T2."AbsEntry" = T0."AtcEntry") AS "Product_Image", '
        ' (SELECT T2."FileName"||\'.\'||T2."FileExt" FROM "ATC1" T2 WHERE T2."U_IMG_C" = \'Product Description Urdu\' AND T2."AbsEntry" = T0."AtcEntry") AS "Product_Description_Urdu" '
        ' FROM "OITM" T0 '
        ' INNER JOIN "OITB" T1 ON T0."ItmsGrpCod" = T1."ItmsGrpCod" '
        ' WHERE T0."Series" = \'72\' '
        ' AND T0."validFor" = \'Y\' '
        ' AND T0."U_PCN" = \'Gabru-Df\''
    )
    return _fetch_all(db, sql)

def policy_customer_balance(db, card_code: str) -> list:
    sql = (
        'SELECT '
        ' T0."CardCode", '
        ' T0."CardName", '
        ' CAST(T0."Project" AS NVARCHAR(100)) AS "Project", '
        ' T0."PrjName", '
        ' SUM(T0."Sale")+SUM(T0."Tax")-SUM(T0."Return")+SUM(T0."Collection")+SUM(T0."DebitSwitching")-'
        ' SUM(T0."CreditSwitching")+SUM(T0."SwitchingDebit")-SUM(T0."SwitchingCredit")+SUM(T0."SecuredDebit")-'
        ' SUM(T0."SecuredCredit")+SUM(T0."BulkDebit")-SUM(T0."BulkCredit")+SUM(T0."Opening") AS "Balance" '
        ' FROM "CUSTLEDG12" T0 '
        ' WHERE T0."CardCode" = ? '
        ' GROUP BY T0."CardCode", T0."CardName", T0."Project", T0."PrjName"'
    )
    return _fetch_all(db, sql, (card_code,))

def sales_vs_achievement(db, emp_id: int | None = None, territory_name: str | None = None, year: int | None = None, month: int | None = None, start_date: str | None = None, end_date: str | None = None) -> list:
    base = (
        'select '
        ' c.TerritoryId, '
        ' O."descript" as TerritoryName, '
        ' sum(c.Sales_Target) as Sales_Target, '
        ' sum(c.DocTotal) as Acchivement, '
        ' F_REFDATE, '
        ' T_REFDATE '
        ' from "4B-BIO_APP"."B4_SALES_TARGET" c '
        ' INNER JOIN "4B-ORANG_APP"."OTER" O ON O."territryID" = c.TerritoryId '
    )
    where_clauses = []
    params = []
    if emp_id is not None:
        where_clauses.append(
            ' TerritoryId in (select U_TID from "4B-BIO_APP"."B4_EMP" where empID = ?)' 
        )
        params.append(emp_id)
    if territory_name is not None and territory_name.strip() != '':
        where_clauses.append(' O."descript" = ?')
        params.append(territory_name.strip())
    if start_date and end_date:
        where_clauses.append(" F_REFDATE >= TO_DATE(?, 'YYYY-MM-DD') AND T_REFDATE <= TO_DATE(?, 'YYYY-MM-DD') ")
        params.extend([start_date.strip(), end_date.strip()])
    elif year is not None and month is not None and 1 <= int(month) <= 12:
        y = int(year)
        m = int(month)
        start = date(y, m, 1)
        if m == 12:
            next_start = date(y + 1, 1, 1)
        else:
            next_start = date(y, m + 1, 1)
        start_str = start.strftime('%Y-%m-%d')
        next_str = next_start.strftime('%Y-%m-%d')
        where_clauses.append(" F_REFDATE >= TO_DATE(?, 'YYYY-MM-DD') AND T_REFDATE < TO_DATE(?, 'YYYY-MM-DD') ")
        params.extend([start_str, next_str])
    where_sql = ''
    if len(where_clauses) > 0:
        where_sql = ' where ' + ' AND '.join(where_clauses)
    tail = (
        ' group by c.TerritoryId, '
        ' O."descript", '
        ' F_REFDATE, '
        ' T_REFDATE '
        ' ORDER BY c.TerritoryId, '
        ' F_REFDATE, '
        ' T_REFDATE'
    )
    sql = base + where_sql + tail
    return _fetch_all(db, sql, tuple(params))

def fetchdata(db, p: dict) -> list:
    table = str(p.get('table', '') or '').strip()
    select = str(p.get('select', '') or '').strip()
    filters = str(p.get('filters', '') or '').strip()
    order = str(p.get('order', '') or '').strip()
    limit = int(p.get('limit', 0) or 0)
    offset = int(p.get('offset', 0) or 0)
    schema_param = str(p.get('schema', '') or '').strip()
    if table == '':
        return []
    if not re.match(r'^[A-Za-z0-9_@\.]+$', table):
        return []
    if schema_param != '' and '.' not in table:
        table = schema_param + '.' + table
    if '.' not in table and schema_param == '':
        row0 = _fetch_one(db, 'SELECT SCHEMA_NAME FROM SYS.TABLES WHERE TABLE_NAME = ? ORDER BY SCHEMA_NAME LIMIT 1', (table,))
        if row0:
            sch = str(row0.get('SCHEMA_NAME') or '')
            if sch != '' and re.match(r'^[A-Za-z0-9_]+$', sch):
                table = sch + '.' + table
    schema_part = ''
    table_part = ''
    if '.' in table:
        parts = table.split('.', 2)
        schema_part, table_part = parts[0], parts[1]
    else:
        table_part = table
    schema_sql = ''
    if schema_part != '':
        schema_sql = schema_part if re.match(r'^"[^"]+"$', schema_part) else quote_ident(schema_part)
    table_sql = table_part if re.match(r'^"[^"]+"$', table_part) else quote_ident(table_part)
    table_ref = (schema_sql + '.' + table_sql) if schema_sql != '' else table_sql
    cols = '*'
    if select != '':
        parts = [x.strip() for x in select.split(',')]
        valid = []
        for col in parts:
            if col == '*':
                valid.append(col)
            elif col != '' and re.match(r'^"[^"]+"$|^[A-Za-z0-9_@\.]+$', col):
                valid.append(col)
        if len(valid) > 0:
            cols = ','.join(valid)
    where = []
    values = []
    if filters != '':
        pairs = [x.strip() for x in filters.split(',')]
        for pair in pairs:
            kv = pair.split(':', 1)
            if len(kv) == 2:
                k = kv[0].strip()
                v = kv[1].strip()
                if k != '' and re.match(r'^"[^"]+"$|^[A-Za-z0-9_@\.]+$', k):
                    where.append(k + ' = ?')
                    values.append(v)
    order_sql = ''
    if order != '':
        order_parts = [x.strip() for x in order.split(',')]
        order_valid = []
        for part in order_parts:
            if part == '':
                continue
            tokens = re.split(r'\s+', part)
            col = tokens[0] if tokens else ''
            dirc = (tokens[1].upper() if len(tokens) > 1 else '')
            if col != '' and re.match(r'^"[^"]+"$|^[A-Za-z0-9_@\.]+$', col):
                if dirc in ('ASC', 'DESC'):
                    order_valid.append(col + ' ' + dirc)
                else:
                    order_valid.append(col)
        if len(order_valid) > 0:
            order_sql = ' ORDER BY ' + ', '.join(order_valid)
    sql = 'SELECT ' + cols + ' FROM ' + table_ref
    if len(where) > 0:
        sql += ' WHERE ' + ' AND '.join(where)
    if order_sql != '':
        sql += order_sql
    if limit > 0:
        sql += ' LIMIT ' + str(limit)
        if offset > 0:
            sql += ' OFFSET ' + str(offset)
    return _fetch_all(db, sql, tuple(values))

def _load_env_file(path: str) -> None:
    if os.path.isfile(path) and os.access(path, os.R_OK):
        with open(path, 'r', encoding='utf-8') as f:
            for line in f:
                s = line.strip()
                if s == '' or s.startswith('#') or '=' not in s:
                    continue
                k, v = s.split('=', 1)
                k = k.strip()
                v = v.strip()
                if v != '' and ((v[0] == '"' and v[-1] == '"') or (v[0] == "'" and v[-1] == "'")):
                    v = v[1:-1]
                if k != '' and not os.environ.get(k):
                    os.environ[k] = v

def _to_bool_str(v):
    if v is None:
        return None
    s = str(v).strip().lower()
    if s in ('1', 'true', 'yes'):
        return 'true'
    if s in ('0', 'false', 'no'):
        return 'false'
    return None

def _build_conn_str_dsn(dsn: str, user: str, password: str, database: str, encrypt: str | None, ssl_validate: str | None) -> str:
    s = f"DSN={dsn};UID={user};PWD={password}"
    if database:
        s += f";DATABASENAME={database}"
    if encrypt is not None:
        s += f";Encrypt={encrypt}"
    if ssl_validate is not None:
        s += f";sslValidateCertificate={ssl_validate}"
    return s

def _build_conn_str_host(driver: str, host: str, port: str, user: str, password: str, database: str, encrypt: str | None, ssl_validate: str | None) -> str:
    s = "Driver={" + driver + "};ServerNode=" + host + ":" + str(port) + ";UID=" + user + ";PWD=" + password
    if database:
        s += f";DATABASENAME={database}"
    if encrypt is not None:
        s += f";Encrypt={encrypt}"
    if ssl_validate is not None:
        s += f";sslValidateCertificate={ssl_validate}"
    return s
def _connect_hdbcli(host: str, port: str, user: str, password: str, database: str, encrypt: str | None, ssl_validate: str | None):
    from hdbcli import dbapi
    use_encrypt = (encrypt == 'true') if encrypt is not None else False
    kwargs = {
        'address': host,
        'port': int(port),
        'user': user,
        'password': password,
    }
    if use_encrypt:
        kwargs['encrypt'] = True
        if ssl_validate is not None:
            kwargs['sslValidateCertificate'] = (ssl_validate == 'true')
    return dbapi.connect(**kwargs)

def main():
    _load_env_file(os.path.join(os.path.dirname(__file__), '.env'))
    import argparse
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument('--dsn')
    parser.add_argument('--host')
    parser.add_argument('--port')
    parser.add_argument('--user')
    parser.add_argument('--password')
    parser.add_argument('--schema')
    parser.add_argument('--database')
    parser.add_argument('--query')
    parser.add_argument('--action')
    parser.add_argument('--table')
    parser.add_argument('--select')
    parser.add_argument('--filters')
    parser.add_argument('--order')
    parser.add_argument('--limit')
    parser.add_argument('--offset')
    parser.add_argument('--verbose', action='store_true')
    args, _ = parser.parse_known_args() if IS_CLI else (parser.parse_args([]), [])
    level = logging.DEBUG if getattr(args, 'verbose', False) else logging.INFO
    if IS_CLI:
        logging.basicConfig(level=level, format='%(asctime)s %(levelname)s %(message)s', stream=sys.stdout)
    else:
        logging.basicConfig(level=level, format='%(levelname)s %(message)s', stream=sys.stdout)
    logger.info('starting')
    user = args.user or os.environ.get('HANA_USER', '')
    password = args.password or os.environ.get('HANA_PASSWORD', '')
    dsn_name = args.dsn or os.environ.get('HANA_DSN', '')
    host = args.host or os.environ.get('HANA_HOST', '')
    port = args.port or os.environ.get('HANA_PORT', '30015')
    schema = args.schema or os.environ.get('HANA_SCHEMA', '')
    database = args.database or os.environ.get('HANA_DATABASE', '')
    query = args.query or 'SELECT CURRENT_UTCTIMESTAMP AS TS FROM DUMMY'
    driver = os.environ.get('HANA_DRIVER', 'HDBODBC')
    encrypt = _to_bool_str(os.environ.get('HANA_ENCRYPT'))
    ssl_validate = _to_bool_str(os.environ.get('HANA_SSL_VALIDATE'))
    action = args.action or ''
    qs = {}
    if not IS_CLI:
        from urllib.parse import parse_qs
        qs = {k: v[-1] for k, v in parse_qs(os.environ.get('QUERY_STRING', '')).items()}
        if action == '':
            action = qs.get('action', '')
        if action == '':
            action = 'select_oitm'
    logger.info('env loaded dsn=%s host=%s port=%s schema=%s database=%s action=%s', dsn_name, host, port, schema, database, action or '(none)')
    if user == '' or password == '':
        err('Missing credentials. Provide --user and --password or set HANA_USER/HANA_PASSWORD.', 2)
    try:
        import pyodbc
        odbc_available = True
    except Exception:
        odbc_available = False
    if not odbc_available:
        err('No ODBC driver available. Install pyodbc for Python.', 3)
    conn_str = ''
    if dsn_name:
        conn_str = _build_conn_str_dsn(dsn_name, user, password, database, encrypt, ssl_validate)
    elif host:
        conn_str = _build_conn_str_host(driver, host, port, user, password, database, encrypt, ssl_validate)
    else:
        err('Provide --dsn or --host/--port.', 2)
    try:
        import pyodbc
        logger.info('connecting')
        conn = pyodbc.connect(conn_str)
        logger.info('connected')
    except Exception as e:
        msg = str(e)
        if dsn_name and host and (('IM002' in msg) or ('data source name not found' in msg.lower())):
            fallback = _build_conn_str_host(driver, host, port, user, password, database, encrypt, ssl_validate)
            try:
                import pyodbc
                logger.info('connecting with fallback')
                conn = pyodbc.connect(fallback)
                logger.info('connected')
            except Exception as e2:
                try:
                    logger.info('connecting with hdbcli')
                    conn = _connect_hdbcli(host, port, user, password, database, encrypt, ssl_validate)
                    logger.info('connected')
                except Exception as e3:
                    err(str(e3), 1)
        else:
            try:
                if host:
                    logger.info('connecting with hdbcli')
                    conn = _connect_hdbcli(host, port, user, password, database, encrypt, ssl_validate)
                    logger.info('connected')
                else:
                    err(msg, 1)
            except Exception as e4:
                err(str(e4), 1)
    try:
        if schema:
            sch_sql = schema if re.match(r'^[A-Za-z0-9_]+$', schema) else quote_ident(schema)
            cur = conn.cursor()
            logger.info('setting schema %s', schema)
            cur.execute('SET SCHEMA ' + sch_sql)
            cur.close()
        if action == 'fetchdata':
            params = {
                'table': args.table or (qs.get('table') if not IS_CLI else None) or '@AATCH_H',
                'select': args.select or (qs.get('select') if not IS_CLI else None) or '',
                'filters': args.filters or (qs.get('filters') if not IS_CLI else None) or '',
                'order': args.order or (qs.get('order') if not IS_CLI else None) or '',
                'limit': args.limit or (qs.get('limit') if not IS_CLI else None) or '10',
                'offset': args.offset or (qs.get('offset') if not IS_CLI else None) or '',
                'schema': schema,
            }
            logger.info('action fetchdata table=%s limit=%s offset=%s', params['table'], params['limit'], params['offset'])
            rows = fetchdata(conn, params)
            logger.info('rows %d', len(rows))
            out_json(rows)
            if odbc_available:
                conn.close()
            sys.exit(0)
        if action == 'select_oitm':
            logger.info('action select_oitm')
            rows = select_oitm(conn, schema)
            logger.info('rows %d', len(rows))
            out_json(rows)
            conn.close()
            sys.exit(0)
        if action == 'count_tables':
            logger.info('action count_tables')
            count = get_tables_count(conn, schema)
            out_text(str(count))
            conn.close()
            sys.exit(0)
        if action == 'territory_summary':
            logger.info('action territory_summary')
            rows = territory_summary(conn)
            logger.info('rows %d', len(rows))
            out_json(rows)
            conn.close()
            sys.exit(0)
        logger.info('executing query')
        rows = _fetch_all(conn, query)
        logger.info('rows %d', len(rows))
        out_json(rows)
        cur.close()
        conn.close()
        sys.exit(0)
    except Exception as e:
        logger.error('error %s', str(e))
        try:
            conn.close()
        except Exception:
            pass
        err(str(e), 1)

if __name__ == '__main__':
    main()
