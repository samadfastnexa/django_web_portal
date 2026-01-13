from rest_framework.response import Response
from rest_framework import status
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from rest_framework.decorators import api_view

from .sap_client import SAPClient
from .models import Policy
from .serializers import PolicySerializer
from django.views.decorators.csrf import ensure_csrf_cookie
from django.shortcuts import render
from django.contrib.admin.views.decorators import staff_member_required
from django.http import JsonResponse
import os
import json
import re
import logging
from .hana_connect import _load_env_file as _hana_load_env_file, territory_summary, products_catalog, policy_customer_balance, policy_customer_balance_all, sales_vs_achievement, territory_names, territories_all, territories_all_full, cwl_all_full, table_columns, sales_orders_all, customer_lov, customer_addresses, contact_person_name, item_lov, warehouse_for_item, sales_tax_codes, projects_lov, policy_link, project_balance, policy_balance_by_customer, crop_lov, child_card_code, sales_vs_achievement_geo, sales_vs_achievement_geo_inv, geo_options, sales_vs_achievement_geo_profit, collection_vs_achievement, unit_price_by_policy
from django.conf import settings
from pathlib import Path
import sys
from django.utils.safestring import mark_safe
from django.core.paginator import Paginator
from FieldAdvisoryService.models import Company, Region, Zone, Territory

logger = logging.getLogger(__name__)


def get_hana_schema_from_request(request):
    """
    Resolve HANA schema from query param, session, or first active company.
    Returns Company_name (e.g., '4B-BIO_APP').
    """
    db_param = request.GET.get('database', '').strip()
    if db_param:
        token = db_param.upper().strip()
        # Build robust candidate variants
        variants = set()
        variants.add(db_param)
        variants.add(token)
        # Dash/underscore toggles
        variants.add(token.replace('-', '_'))
        variants.add(token.replace('_', '-'))
        # Ensure APP suffix when missing
        if not token.endswith('_APP') and not token.endswith('-APP'):
            variants.add(f"{token}_APP")
            variants.add(f"{token}-APP")
        # Try exact/case-insensitive matches against active companies
        for candidate in list(variants):
            try:
                company = Company.objects.get(Company_name=candidate, is_active=True)
                logger.info(f"[DB RESOLVER] Matched exact company: {company.Company_name} from '{db_param}'")
                return company.Company_name
            except Company.DoesNotExist:
                pass
            try:
                company = Company.objects.get(Company_name__iexact=candidate, is_active=True)
                logger.info(f"[DB RESOLVER] Matched iexact company: {company.Company_name} from '{db_param}'")
                return company.Company_name
            except Company.DoesNotExist:
                pass

        # If still not found, map common keys like '4B-ORANG'/'4B-BIO' to active companies
        if 'ORANG' in token:
            company = Company.objects.filter(is_active=True, Company_name__icontains='ORANG').first()
            if company:
                logger.info(f"[DB RESOLVER] Fallback mapped to ORANG company: {company.Company_name}")
                return company.Company_name
        if 'BIO' in token:
            company = Company.objects.filter(is_active=True, Company_name__icontains='BIO').first()
            if company:
                logger.info(f"[DB RESOLVER] Fallback mapped to BIO company: {company.Company_name}")
                return company.Company_name

    session_db = request.session.get('selected_db', '').strip()
    if session_db:
        try:
            company = Company.objects.get(Company_name=session_db, is_active=True)
            return company.Company_name
        except Company.DoesNotExist:
            pass

    try:
        company = Company.objects.filter(is_active=True).first()
        if company:
            return company.Company_name
    except Exception:
        pass

    return '4B-BIO_APP'


def get_valid_company_schemas():
    """Return list of active company schemas for documentation."""
    try:
        schemas = list(Company.objects.filter(is_active=True).values_list('Company_name', flat=True))
        if schemas:
            return schemas
    except Exception:
        pass
    return ['4B-BIO_APP', '4B-ORANG_APP']

@staff_member_required
def sales_order_admin(request):
    error = None
    result = None
    default_payload = {
        "Series": 8,
        "DocType": "dDocument_Items",
        "DocDate": "2025-11-21",
        "DocDueDate": "2025-11-21",
        "TaxDate": "2025-11-21",
        "CardCode": "BIC01563",
        "CardName": "Master Agro Traders",
        "ContactPersonCode": 4804,
        "FederalTaxID": "32402-7881906-3",
        "PayToCode": 1,
        "Address": "Dhandla Road Dajal Tehsil Jampur\r\r\rPAKISTAN",
        "DocCurrency": "PKR",
        "DocRate": 1.0,
        "Comments": "",
        "SummeryType": "dNoSummary",
        "DocObjectCode": "oOrders",
        "U_sotyp": "01",
        "U_USID": "Dgk01",
        "U_SWJE": None,
        "U_SECJE": None,
        "U_CRJE": None,
        "U_SCardCode": "BIC01812",
        "U_SCardName": "Malik Agro Traders",
        "DocumentLines": [
            {
                "LineNum": 0,
                "ItemCode": "FG00581",
                "ItemDescription": "Jadogar 25 Od - 360-Mls.",
                "Quantity": 20.0,
                "DiscountPercent": 0.0,
                "WarehouseCode": "WH06",
                "VatGroup": "SE",
                "UnitsOfMeasurment": 1.0,
                "TaxPercentagePerRow": 0.0,
                "UnitPrice": 1170.0,
                "UoMEntry": 68,
                "MeasureUnit": "No",
                "UoMCode": "No",
                "ProjectCode": "0223254",
                "U_SD": 0.0,
                "U_AD": 0.0,
                "U_EXD": 0.0,
                "U_zerop": 0.0,
                "U_pl": 275,
                "U_BP": 1322.0,
                "U_policy": "0223271",
                "U_focitem": "No",
                "U_crop": None
            }
        ]
    }
    payload_text = json.dumps(default_payload, ensure_ascii=False, indent=2)
    if request.method == 'POST':
        try:
            payload_text = request.POST.get('payload') or payload_text
            data = json.loads(payload_text)
            selected_db = request.session.get('selected_db', '4B-BIO')
            client = SAPClient(company_db_key=selected_db)
            result = client.create_sales_order(data)
        except Exception as e:
            error = str(e)
    result_json = None
    if result is not None:
        try:
            result_json = json.dumps(result, ensure_ascii=False, indent=2)
        except Exception:
            result_json = str(result)
    return render(
        request,
        'admin/sap_integration/sales_order.html',
        {
            'payload': payload_text,
            'result_json': result_json,
            'error': error,
        }
    )
@staff_member_required
def hana_connect_admin(request):
    try:
        _hana_load_env_file(os.path.join(os.path.dirname(__file__), '.env'))
        _hana_load_env_file(os.path.join(str(settings.BASE_DIR), '.env'))
        _hana_load_env_file(os.path.join(str(Path(settings.BASE_DIR).parent), '.env'))
        _hana_load_env_file(os.path.join(os.getcwd(), '.env'))
    except Exception:
        pass
    
    # Get database options from settings
    db_options = {}
    selected_db_key = request.GET.get('company_db', '4B-BIO')  # Default to 4B-BIO
    
    try:
        from preferences.models import Setting
        db_setting = Setting.objects.filter(slug='SAP_COMPANY_DB').first()
        if db_setting:
            # Handle both dict (JSONField) and string (TextField) formats
            if isinstance(db_setting.value, dict):
                db_options = db_setting.value
            elif isinstance(db_setting.value, str):
                try:
                    db_options = json.loads(db_setting.value)
                except:
                    pass
    except Exception as e:
        pass
    
    # Fallback to default options if setting not found or invalid
    if not db_options:
        db_options = {
            '4B-ORANG': '4B-ORANG_APP',
            '4B-BIO': '4B-BIO_APP'
        }
    
    # Clean up keys and values - remove any embedded quotes
    cleaned_options = {}
    for k, v in db_options.items():
        clean_key = k.strip().strip('"').strip("'")
        clean_value = v.strip().strip('"').strip("'")
        cleaned_options[clean_key] = clean_value
    db_options = cleaned_options
    
    # Clean the selected key as well
    selected_db_key = selected_db_key.strip().strip('"').strip("'")
    
    # Get the schema based on selected database
    selected_schema = db_options.get(selected_db_key, os.environ.get('HANA_SCHEMA') or '4B-BIO_APP')
    
    # Debug logging
    print(f"DEBUG hana_connect_admin:")
    print(f"  selected_db_key: {selected_db_key}")
    print(f"  db_options: {db_options}")
    print(f"  selected_schema: {selected_schema}")
    print(f"  type(selected_schema): {type(selected_schema)}")
    
    cfg = {
        'dsn': os.environ.get('HANA_DSN') or '',
        'host': os.environ.get('HANA_HOST') or '',
        'port': os.environ.get('HANA_PORT') or '30015',
        'schema': selected_schema,  # Use selected schema
        'database': os.environ.get('HANA_DATABASE') or '',
        'encrypt': os.environ.get('HANA_ENCRYPT') or '',
        'ssl_validate': os.environ.get('HANA_SSL_VALIDATE') or '',
        'user': os.environ.get('HANA_USER') or '',
        'driver': os.environ.get('HANA_DRIVER') or 'HDBCLI',
    }
    action = request.GET.get('action') or 'policy_customer_balance'
    result = None
    error = None
    error_fields = {}
    diagnostics = {
        'python': sys.executable,
        'hdbcli_import': False,
        'env': {
            'has_host': bool(os.environ.get('HANA_HOST')),
            'has_port': bool(os.environ.get('HANA_PORT')),
            'has_user': bool(os.environ.get('HANA_USER')),
            'has_password': bool(os.environ.get('HANA_PASSWORD')),
        },
        'action': action,
        'selected_db': selected_db_key,
        'selected_schema': selected_schema,
    }
    if action:
        def _sanitize_error(msg):
            s = str(msg or '')
            s = re.sub(r'PWD=([^;\s]+)', 'PWD=****', s, flags=re.IGNORECASE)
            s = re.sub(r'UID=([^;\s]+)', 'UID=****', s, flags=re.IGNORECASE)
            s = re.sub(r'password\s*[:=]\s*[^\s;]+', 'password=****', s, flags=re.IGNORECASE)
            return s
        try:
            conn = None
            try:
                from hdbcli import dbapi
                diagnostics['hdbcli_import'] = True
                pwd = os.environ.get('HANA_PASSWORD','')
                if not cfg['host']:
                    error = 'Missing HANA_HOST configuration'
                else:
                    use_encrypt = str(cfg['encrypt']).strip().lower() in ('true','1','yes')
                    kwargs = {'address': cfg['host'], 'port': int(cfg['port']), 'user': cfg['user'] or '', 'password': pwd or ''}
                    if use_encrypt:
                        kwargs['encrypt'] = True
                        if cfg['ssl_validate']:
                            kwargs['sslValidateCertificate'] = (str(cfg['ssl_validate']).strip().lower() in ('true','1','yes'))
                    conn = dbapi.connect(**kwargs)
            except Exception as e_cli_first:
                error = _sanitize_error(e_cli_first)
            if not conn:
                if not error:
                    error = 'HANA connection not established'
            else:
                try:
                    if cfg['schema']:
                        sch = cfg['schema']
                        cur = conn.cursor()
                        # Quote schema name for HANA (use double quotes for identifiers with hyphens)
                        cur.execute(f'SET SCHEMA "{sch}"')
                        cur.close()
                    if action == 'health':
                        cur = conn.cursor()
                        cur.execute('SELECT CURRENT_UTCTIMESTAMP AS TS FROM DUMMY')
                        rows = cur.fetchall()
                        cols = [d[0] for d in cur.description] if cur.description else []
                        data = []
                        for r in rows:
                            row = {}
                            for i, c in enumerate(cols):
                                try:
                                    row[c] = r[i]
                                except Exception:
                                    row[c] = None
                            data.append(row)
                        result = data
                        cur.close()
                    elif action == 'count_tables':
                        cur = conn.cursor()
                        if cfg['schema']:
                            cur.execute('SELECT COUNT(*) AS TABLE_COUNT FROM SYS.TABLES WHERE SCHEMA_NAME = CURRENT_SCHEMA')
                        else:
                            cur.execute('SELECT COUNT(*) AS TABLE_COUNT FROM SYS.TABLES')
                        r = cur.fetchone()
                        val = None
                        if r is not None:
                            try:
                                val = int(r[0])
                            except Exception:
                                val = None
                        result = {'table_count': val}
                        cur.close()
                    elif action == 'select_oitm':
                        cur = conn.cursor()
                        sql = 'SELECT * FROM ' + ('"OITM"' if not cfg['schema'] else (cfg['schema'] if re.match(r'^[A-Za-z0-9_]+$', cfg['schema']) else '"' + cfg['schema'].replace('"','""') + '"') + '."OITM"')
                        cur.execute(sql)
                        rows = cur.fetchmany(10)
                        cols = [d[0] for d in cur.description] if cur.description else []
                        data = []
                        for r in rows:
                            row = {}
                            for i, c in enumerate(cols):
                                try:
                                    row[c] = r[i]
                                except Exception:
                                    row[c] = None
                            data.append(row)
                        result = data
                        cur.close()
                    elif action == 'territory_summary':
                        try:
                            emp_id_param = request.GET.get('emp_id')
                            territory_param = request.GET.get('territory')
                            year_param = None
                            month_param = None
                            start_date_param = request.GET.get('start_date')
                            end_date_param = request.GET.get('end_date')
                            in_millions_param = (request.GET.get('in_millions') or '').strip().lower()
                            emp_val = None
                            if emp_id_param is not None and emp_id_param != '':
                                try:
                                    emp_val = int(emp_id_param)
                                except Exception:
                                    error = 'Invalid emp_id'
                            yr_val = None
                            mo_val = None
                            if error is None:
                                data = territory_summary(conn, emp_val, (territory_param or '').strip() or None, yr_val, mo_val, (start_date_param or '').strip() or None, (end_date_param or '').strip() or None)
                                if in_millions_param in ('true','1','yes','y'):
                                    scaled = []
                                    for row in data or []:
                                        if isinstance(row, dict):
                                            r = dict(row)
                                            try:
                                                v = r.get('COLLECTION_TARGET', None)
                                                if v is None:
                                                    v = r.get('colletion_Target', None)
                                                if v is not None:
                                                    r['COLLECTION_TARGET'] = round((float(v) / 1000000.0), 2)
                                                    r['colletion_Target'] = r['COLLECTION_TARGET']
                                            except Exception:
                                                pass
                                            try:
                                                v = r.get('ACHIEVEMENT', None)
                                                if v is None:
                                                    v = r.get('DocTotal', None)
                                                if v is not None:
                                                    r['ACHIEVEMENT'] = round((float(v) / 1000000.0), 2)
                                                    r['DocTotal'] = r['ACHIEVEMENT']
                                            except Exception:
                                                pass
                                            scaled.append(r)
                                        else:
                                            scaled.append(row)
                                    data = scaled
                                result = data
                                try:
                                    opts = territory_names(conn)
                                except Exception:
                                    opts = []
                                territory_options = []
                                for row in opts or []:
                                    v = row.get('TERRITORYNAME') or row.get('TerritoryName') or row.get('DESCRIPT') or row.get('descript')
                                    if v and v not in territory_options:
                                        territory_options.append(v)
                                diagnostics['territory_options_count'] = len(territory_options)
                                diagnostics['selected_territory'] = territory_param or ''
                                diagnostics['emp_id'] = emp_val
                                diagnostics['year'] = None
                                diagnostics['month'] = None
                                diagnostics['start_date'] = (start_date_param or '').strip()
                                diagnostics['end_date'] = (end_date_param or '').strip()
                                diagnostics['in_millions'] = (in_millions_param in ('', 'true','1','yes','y'))
                                request._territory_options = territory_options
                        except Exception as e_ts:
                            error = str(e_ts)
                    elif action == 'products_catalog':
                        try:
                            data = products_catalog(conn, selected_schema)
                            result = data
                        except Exception as e_pc:
                            error = str(e_pc)
                    elif action == 'list_territories':
                        try:
                            data = territories_all(conn)
                            # Build hierarchical Region -> Zone -> Territory structure with aggregated totals
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
                                except Exception:
                                    pass
                                try:
                                    v = row.get('Collection_Achievement')
                                    if v is None: v = row.get('COLLECTION_ACHIEVEMENT')
                                    if v is None: v = row.get('DocTotal')
                                    ach = float(v or 0.0)
                                except Exception:
                                    pass
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
                                    'achievement': ach
                                })
                            final_list = []
                            for r_name in sorted(hierarchy.keys()):
                                r_data = hierarchy[r_name]
                                zones_list = []
                                for z_name in sorted(r_data['zones'].keys()):
                                    z_data = r_data['zones'][z_name]
                                    z_data['territories'] = sorted(z_data['territories'], key=lambda x: x['name'])
                                    zones_list.append(z_data)
                                r_data['zones'] = zones_list
                                final_list.append(r_data)
                            for r in final_list:
                                r['sales'] = round(r['sales'], 2)
                                r['achievement'] = round(r['achievement'], 2)
                                for z in r['zones']:
                                    z['sales'] = round(z['sales'], 2)
                                    z['achievement'] = round(z['achievement'], 2)
                            result = final_list
                            if isinstance(result, list) and len(result) == 0:
                                error = 'No territories found'
                            # Diagnostics: show available OTER columns to help mapping
                            try:
                                diagnostics['oter_columns'] = table_columns(conn, cfg['schema'] or '4B-ORANG_APP', 'OTER')
                                diagnostics['schema_used'] = cfg['schema'] or '4B-ORANG_APP'
                            except Exception:
                                diagnostics['oter_columns'] = []
                        except Exception as e_lt:
                            error = str(e_lt)
                    elif action == 'list_territories_full':
                        try:
                            top_param = request.GET.get('top')
                            top_val = 500
                            try:
                                if top_param:
                                    top_val = int(top_param)
                            except Exception:
                                top_val = 500
                            status_param = (request.GET.get('status') or '').strip().lower()
                            if status_param not in ('active','inactive',''):
                                status_param = ''
                            data = territories_all_full(conn, top_val, status_param or None)
                            result = data
                            if isinstance(result, list) and len(result) == 0:
                                error = 'No territories found'
                        except Exception as e_ltf:
                            error = str(e_ltf)
                    elif action == 'list_cwl':
                        try:
                            top_param = request.GET.get('top')
                            top_val = 500
                            try:
                                if top_param:
                                    top_val = int(top_param)
                            except Exception:
                                top_val = 500
                            data = cwl_all_full(conn, top_val)
                            result = data
                            if isinstance(result, list) and len(result) == 0:
                                error = 'No CWL rows found'
                        except Exception as e_cwl:
                            error = str(e_cwl)
                    elif action == 'policy_customer_balance':
                        try:
                            cc = (request.GET.get('card_code') or '').strip()
                            top_param = request.GET.get('top')
                            db_param = (request.GET.get('database') or '').strip()
                            
                            # Handle database parameter for admin view
                            if db_param:
                                norm = db_param.strip().upper().replace('-APP', '_APP')
                                if '4B-BIO' in norm:
                                    cfg['schema'] = '4B-BIO_APP'
                                elif '4B-ORANG' in norm:
                                    cfg['schema'] = '4B-ORANG_APP'
                                else:
                                    cfg['schema'] = db_param
                                # Reconnect with new schema
                                try:
                                    conn.close()
                                except Exception:
                                    pass
                                conn = dbapi.connect(**kwargs)
                                if cfg['schema']:
                                    sch = cfg['schema']
                                    cur = conn.cursor()
                                    cur.execute(f'SET SCHEMA "{sch}"')
                                    cur.close()
                            
                            top_val = None
                            if cc:
                                data = policy_customer_balance(conn, cc)
                            else:
                                try:
                                    top_val = int(top_param) if (top_param or '').strip() != '' else 200
                                except Exception:
                                    top_val = 200
                                data = policy_customer_balance_all(conn, top_val)
                            result = data
                            if isinstance(result, list) and len(result) == 0:
                                error = 'No rows found'
                        except Exception as e_pb:
                            error = str(e_pb)
                    elif action == 'sales_vs_achievement':
                        try:
                            emp_id_param = request.GET.get('emp_id')
                            territory_param = request.GET.get('territory')
                            year_param = None
                            month_param = None
                            start_date_param = request.GET.get('start_date')
                            end_date_param = request.GET.get('end_date')
                            in_millions_param = (request.GET.get('in_millions') or '').strip().lower()
                            emp_val = None
                            if emp_id_param is not None and emp_id_param != '':
                                try:
                                    emp_val = int(emp_id_param)
                                except Exception:
                                    error = 'Invalid emp_id'
                            yr_val = None
                            mo_val = None
                            if error is None:
                                data = sales_vs_achievement(conn, emp_val, (territory_param or '').strip() or None, yr_val, mo_val, (start_date_param or '').strip() or None, (end_date_param or '').strip() or None)
                                if in_millions_param in ('', 'true','1','yes','y'):
                                    scaled = []
                                    for row in data or []:
                                        if isinstance(row, dict):
                                            r = dict(row)
                                            try:
                                                v = r.get('Sales_Target', None)
                                                if v is None:
                                                    v = r.get('SALES_TARGET', None)
                                                if v is not None:
                                                    val = round((float(v) / 1000000.0), 2)
                                                    r['SALES_TARGET'] = val
                                                    r.pop('Sales_Target', None)
                                            except Exception:
                                                pass
                                            try:
                                                v = r.get('Achievement', None)
                                                if v is None:
                                                    v = r.get('ACHIEVEMENT', None)
                                                if v is not None:
                                                    val2 = round((float(v) / 1000000.0), 2)
                                                    r['ACHIEVEMENT'] = val2
                                                    r.pop('Achievement', None)
                                            except Exception:
                                                pass
                                            scaled.append(r)
                                        else:
                                            scaled.append(row)
                                    data = scaled
                                result = data
                                try:
                                    opts = territory_names(conn)
                                except Exception:
                                    opts = []
                                territory_options = []
                                for row in opts or []:
                                    v = row.get('TERRITORYNAME') or row.get('TerritoryName') or row.get('DESCRIPT') or row.get('descript')
                                    if v and v not in territory_options:
                                        territory_options.append(v)
                                diagnostics['territory_options_count'] = len(territory_options)
                                diagnostics['selected_territory'] = territory_param or ''
                                diagnostics['emp_id'] = emp_val
                                diagnostics['year'] = None
                                diagnostics['month'] = None
                                diagnostics['start_date'] = (start_date_param or '').strip()
                                diagnostics['end_date'] = (end_date_param or '').strip()
                                diagnostics['in_millions'] = (in_millions_param in ('', 'true','1','yes','y'))
                                request._territory_options = territory_options
                        except Exception as e_sa:
                            error = str(e_sa)
                    elif action == 'sales_vs_achievement_geo':
                        try:
                            emp_id_param = request.GET.get('emp_id')
                            region_param = request.GET.get('region')
                            zone_param = request.GET.get('zone')
                            territory_param = request.GET.get('territory')
                            start_date_param = request.GET.get('start_date')
                            end_date_param = request.GET.get('end_date')
                            in_millions_param = (request.GET.get('in_millions') or '').strip().lower()
                            
                            emp_val = None
                            if emp_id_param is not None and emp_id_param != '':
                                try:
                                    emp_val = int(emp_id_param)
                                except Exception:
                                    error = 'Invalid emp_id'
                            
                            if error is None:
                                data = sales_vs_achievement_geo(conn, emp_val, (region_param or '').strip() or None, (zone_param or '').strip() or None, (territory_param or '').strip() or None, (start_date_param or '').strip() or None, (end_date_param or '').strip() or None)
                                
                                # Scaling to millions if requested
                                if in_millions_param in ('', 'true','1','yes','y'):
                                    scaled = []
                                    for row in data or []:
                                        if isinstance(row, dict):
                                            r = dict(row)
                                            try:
                                                v = r.get('Collection_Target', None)
                                                if v is not None:
                                                    r['Collection_Target'] = round((float(v) / 1000000.0), 2)
                                            except Exception:
                                                pass
                                            try:
                                                v = r.get('Collection_Achievement', None)
                                                if v is not None:
                                                    r['Collection_Achievement'] = round((float(v) / 1000000.0), 2)
                                            except Exception:
                                                pass
                                            scaled.append(r)
                                        else:
                                            scaled.append(row)
                                    data = scaled
                                result = data
                                
                                try:
                                    company = Company.objects.filter(Company_name=selected_db_key).first()
                                    if company:
                                        regions_qs = Region.objects.filter(company=company)
                                        zones_qs = Zone.objects.filter(company=company)
                                        territories_qs = Territory.objects.filter(company=company)
                                    else:
                                        regions_qs = Region.objects.all()
                                        zones_qs = Zone.objects.all()
                                        territories_qs = Territory.objects.all()
                                    regions = list(regions_qs.order_by('name').values_list('name', flat=True).distinct())
                                    zones = list(zones_qs.order_by('name').values_list('name', flat=True).distinct())
                                    territories = list(territories_qs.order_by('name').values_list('name', flat=True).distinct())
                                    request._geo_options = {'regions': regions, 'zones': zones, 'territories': territories}
                                except Exception:
                                    request._geo_options = {'regions': [], 'zones': [], 'territories': []}
                                    
                                diagnostics['emp_id'] = emp_val
                                diagnostics['start_date'] = (start_date_param or '').strip()
                                diagnostics['end_date'] = (end_date_param or '').strip()
                                diagnostics['region'] = (region_param or '').strip()
                                diagnostics['zone'] = (zone_param or '').strip()
                                diagnostics['territory'] = (territory_param or '').strip()
                                diagnostics['in_millions'] = (in_millions_param in ('', 'true','1','yes','y'))
                                
                        except Exception as e_geo:
                            error = str(e_geo)
                    elif action == 'collection_vs_achievement':
                        try:
                            emp_id_param = request.GET.get('emp_id')
                            region_param = request.GET.get('region')
                            zone_param = request.GET.get('zone')
                            territory_param = request.GET.get('territory')
                            start_date_param = request.GET.get('start_date')
                            end_date_param = request.GET.get('end_date')
                            in_millions_param = (request.GET.get('in_millions') or '').strip().lower()
                            detailed_view_param = (request.GET.get('detailed_view') or '').strip().lower()
                            
                            is_detailed = detailed_view_param in ('true', '1', 'yes', 'on')
                            
                            emp_val = None
                            if emp_id_param is not None and emp_id_param != '':
                                try:
                                    emp_val = int(emp_id_param)
                                except Exception:
                                    error = 'Invalid emp_id'
                            
                            if error is None:
                                data = sales_vs_achievement_geo_inv(
                                    conn,
                                    emp_id=emp_val,
                                    region=(region_param or '').strip() or None,
                                    zone=(zone_param or '').strip() or None,
                                    territory=(territory_param or '').strip() or None,
                                    start_date=(start_date_param or '').strip() or None,
                                    end_date=(end_date_param or '').strip() or None,
                                    group_by_emp=False,
                                    group_by_date=is_detailed
                                )
                                
                                if in_millions_param in ('', 'true','1','yes','y'):
                                    scaled = []
                                    for row in data or []:
                                        if isinstance(row, dict):
                                            r = dict(row)
                                            try:
                                                v = r.get('Collection_Target')
                                                if v is None: v = r.get('COLLECTION_TARGET')
                                                if v is not None:
                                                    r['Collection_Target'] = round((float(v) / 1000000.0), 2)
                                            except Exception:
                                                pass
                                            try:
                                                v = r.get('Collection_Achievement')
                                                if v is None: v = r.get('COLLECTION_ACHIEVEMENT')
                                                if v is not None:
                                                    r['Collection_Achievement'] = round((float(v) / 1000000.0), 2)
                                            except Exception:
                                                pass
                                            scaled.append(r)
                                        else:
                                            scaled.append(row)
                                    data = scaled

                                # Hierarchical Transformation
                                hierarchy = {}
                                for row in (data or []):
                                    if not isinstance(row, dict):
                                        continue
                                    reg = row.get('Region', 'Unknown Region')
                                    zon = row.get('Zone', 'Unknown Zone')
                                    ter = row.get('Territory', 'Unknown Territory')
                                    
                                    # Handle Date Range
                                    date_range_str = ""
                                    if is_detailed:
                                        fd = row.get('From_Date')
                                        td = row.get('To_Date')
                                        if fd and td:
                                            date_range_str = f"{fd} to {td}"
                                        elif fd:
                                            date_range_str = f"From {fd}"
                                        elif td:
                                            date_range_str = f"To {td}"
                                    else:
                                        # For aggregated view, we might also want to show date range if min/max available
                                        fd = row.get('From_Date')
                                        td = row.get('To_Date')
                                        if fd and td:
                                             date_range_str = f"{fd} to {td}"

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
                                        'date_range': date_range_str
                                    })

                                # Convert dicts to sorted lists
                                final_list = []
                                for r_name in sorted(hierarchy.keys()):
                                    r_data = hierarchy[r_name]
                                    zones_list = []
                                    for z_name in sorted(r_data['zones'].keys()):
                                        z_data = r_data['zones'][z_name]
                                        # Sort territories by name and date
                                        z_data['territories'] = sorted(z_data['territories'], key=lambda x: (x['name'], x['date_range']))
                                        zones_list.append(z_data)
                                    r_data['zones'] = zones_list
                                    final_list.append(r_data)
                                
                                # Rounding
                                for r in final_list:
                                    r['sales'] = round(r['sales'], 2)
                                    r['achievement'] = round(r['achievement'], 2)
                                    for z in r['zones']:
                                        z['sales'] = round(z['sales'], 2)
                                        z['achievement'] = round(z['achievement'], 2)

                                result = final_list
                                
                                try:
                                    company = Company.objects.filter(Company_name=selected_db_key).first()
                                    if company:
                                        regions_qs = Region.objects.filter(company=company)
                                        zones_qs = Zone.objects.filter(company=company)
                                        territories_qs = Territory.objects.filter(company=company)
                                    else:
                                        regions_qs = Region.objects.all()
                                        zones_qs = Zone.objects.all()
                                        territories_qs = Territory.objects.all()
                                    regions = list(regions_qs.order_by('name').values_list('name', flat=True).distinct())
                                    zones = list(zones_qs.order_by('name').values_list('name', flat=True).distinct())
                                    territories = list(territories_qs.order_by('name').values_list('name', flat=True).distinct())
                                    request._geo_options = {'regions': regions, 'zones': zones, 'territories': territories}
                                except Exception:
                                    request._geo_options = {'regions': [], 'zones': [], 'territories': []}
                                    
                                diagnostics['emp_id'] = emp_val
                                diagnostics['start_date'] = (start_date_param or '').strip()
                                diagnostics['end_date'] = (end_date_param or '').strip()
                                diagnostics['region'] = (region_param or '').strip()
                                diagnostics['zone'] = (zone_param or '').strip()
                                diagnostics['territory'] = (territory_param or '').strip()
                                diagnostics['in_millions'] = (in_millions_param in ('', 'true','1','yes','y'))
                                diagnostics['detailed_view'] = is_detailed
                                
                        except Exception as e_coll:
                            error = str(e_coll)
                    elif action == 'sales_vs_achievement_geo_inv':
                        try:
                            emp_id_param = request.GET.get('emp_id')
                            region_param = request.GET.get('region')
                            zone_param = request.GET.get('zone')
                            territory_param = request.GET.get('territory')
                            start_date_param = request.GET.get('start_date')
                            end_date_param = request.GET.get('end_date')
                            in_millions_param = (request.GET.get('in_millions') or '').strip().lower()
                            group_by_emp_param = request.GET.get('group_by_emp')
                            
                            # Default to False for Inv
                            group_by_emp = False
                            if group_by_emp_param is not None:
                                group_by_emp = str(group_by_emp_param).strip().lower() in ('true','1','yes')
                            
                            emp_val = None
                            if emp_id_param is not None and emp_id_param != '':
                                try:
                                    emp_val = int(emp_id_param)
                                except Exception:
                                    error = 'Invalid emp_id'
                            
                            data = sales_vs_achievement_geo_inv(
                                conn, 
                                emp_id=emp_val,
                                region=(region_param or '').strip() or None, 
                                zone=(zone_param or '').strip() or None, 
                                territory=(territory_param or '').strip() or None,
                                start_date=(start_date_param or '').strip() or None,
                                end_date=(end_date_param or '').strip() or None,
                                group_by_emp=group_by_emp
                            )
                            
                            # Scaling to millions if requested
                            if in_millions_param in ('', 'true','1','yes','y'):
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
                            
                            # Hierarchical Transformation
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

                            # Convert dicts to sorted lists for rendering
                            final_list = []
                            for r_name in sorted(hierarchy.keys()):
                                r_data = hierarchy[r_name]
                                zones_list = []
                                for z_name in sorted(r_data['zones'].keys()):
                                    z_data = r_data['zones'][z_name]
                                    # Sort territories by name
                                    z_data['territories'] = sorted(z_data['territories'], key=lambda x: x['name'])
                                    zones_list.append(z_data)
                                r_data['zones'] = zones_list
                                final_list.append(r_data)
                            
                            # Rounding totals after aggregation
                            for r in final_list:
                                r['sales'] = round(r['sales'], 2)
                                r['achievement'] = round(r['achievement'], 2)
                                for z in r['zones']:
                                    z['sales'] = round(z['sales'], 2)
                                    z['achievement'] = round(z['achievement'], 2)

                            result = final_list
                            
                            try:
                                company = Company.objects.filter(Company_name=selected_db_key).first()
                                if company:
                                    regions_qs = Region.objects.filter(company=company)
                                    zones_qs = Zone.objects.filter(company=company)
                                    territories_qs = Territory.objects.filter(company=company)
                                else:
                                    regions_qs = Region.objects.all()
                                    zones_qs = Zone.objects.all()
                                    territories_qs = Territory.objects.all()
                                regions = list(regions_qs.order_by('name').values_list('name', flat=True).distinct())
                                zones = list(zones_qs.order_by('name').values_list('name', flat=True).distinct())
                                territories = list(territories_qs.order_by('name').values_list('name', flat=True).distinct())
                                request._geo_options = {'regions': regions, 'zones': zones, 'territories': territories}
                            except Exception:
                                request._geo_options = {'regions': [], 'zones': [], 'territories': []}
                                
                            diagnostics['emp_id'] = emp_val
                            diagnostics['start_date'] = (start_date_param or '').strip()
                            diagnostics['end_date'] = (end_date_param or '').strip()
                            diagnostics['region'] = (region_param or '').strip()
                            diagnostics['zone'] = (zone_param or '').strip()
                            diagnostics['territory'] = (territory_param or '').strip()
                            diagnostics['in_millions'] = (in_millions_param in ('', 'true','1','yes','y'))
                            diagnostics['group_by_emp'] = group_by_emp
                            
                        except Exception as e_geo_inv:
                            error = str(e_geo_inv)
                    elif action == 'sales_vs_achievement_territory':
                        try:
                            region_param = request.GET.get('region')
                            zone_param = request.GET.get('zone')
                            territory_param = request.GET.get('territory')
                            start_date_param = request.GET.get('start_date')
                            end_date_param = request.GET.get('end_date')
                            in_millions_param = (request.GET.get('in_millions') or '').strip().lower()
                            
                            data = sales_vs_achievement_geo_inv(
                                conn,
                                emp_id=None,
                                region=(region_param or '').strip() or None,
                                zone=(zone_param or '').strip() or None,
                                territory=(territory_param or '').strip() or None,
                                start_date=(start_date_param or '').strip() or None,
                                end_date=(end_date_param or '').strip() or None,
                                group_by_emp=False
                            )
                            
                            if in_millions_param in ('', 'true','1','yes','y'):
                                scaled = []
                                for row in data or []:
                                    if isinstance(row, dict):
                                        r = dict(row)
                                        try:
                                            v = r.get('Collection_Target')
                                            if v is None: v = r.get('COLLECTION_TARGET')
                                            if v is not None:
                                                r['Collection_Target'] = round((float(v) / 1000000.0), 2)
                                        except Exception:
                                            pass
                                        try:
                                            v = r.get('Collection_Achievement')
                                            if v is None: v = r.get('COLLECTION_ACHIEVEMENT')
                                            if v is not None:
                                                r['Collection_Achievement'] = round((float(v) / 1000000.0), 2)
                                        except Exception:
                                            pass
                                        r.pop('EmployeeName', None)
                                        scaled.append(r)
                                    else:
                                        scaled.append(row)
                                data = scaled
                            else:
                                cleaned = []
                                for row in data or []:
                                    if isinstance(row, dict):
                                        r = dict(row)
                                        r.pop('EmployeeName', None)
                                        cleaned.append(r)
                                    else:
                                        cleaned.append(row)
                                data = cleaned
                            
                            hierarchy = {}
                            for row in (data or []):
                                if not isinstance(row, dict):
                                    continue
                                reg = None
                                zon = None
                                ter = None
                                if reg is None: reg = row.get('Region')
                                if reg is None: reg = row.get('REGION')
                                if reg is None: reg = 'Unknown Region'
                                if zon is None: zon = row.get('Zone')
                                if zon is None: zon = row.get('ZONE')
                                if zon is None: zon = 'Unknown Zone'
                                if ter is None: ter = row.get('Territory')
                                if ter is None: ter = row.get('TERRITORY')
                                if ter is None: ter = row.get('TerritoryName')
                                if ter is None: ter = row.get('TERRITORYNAME')
                                if ter is None: ter = 'Unknown Territory'
                                sal = 0.0
                                ach = 0.0
                                try:
                                    v = row.get('Collection_Target')
                                    if v is None: v = row.get('COLLECTION_TARGET')
                                    if v is None: v = row.get('colletion_Target')
                                    if v is None: v = row.get('COLLETION_TARGET')
                                    sal = float(v or 0.0)
                                except Exception:
                                    pass
                                try:
                                    v = row.get('Collection_Achievement')
                                    if v is None: v = row.get('COLLECTION_ACHIEVEMENT')
                                    if v is None: v = row.get('DocTotal')
                                    if v is None: v = row.get('ACHIEVEMENT')
                                    ach = float(v or 0.0)
                                except Exception:
                                    pass
                                if reg not in hierarchy:
                                    hierarchy[reg] = {'name': reg or 'Unknown Region', 'sales': 0.0, 'achievement': 0.0, 'zones': {}}
                                hierarchy[reg]['sales'] += sal
                                hierarchy[reg]['achievement'] += ach
                                if zon not in hierarchy[reg]['zones']:
                                    hierarchy[reg]['zones'][zon] = {'name': zon or 'Unknown Zone', 'sales': 0.0, 'achievement': 0.0, 'territories': []}
                                hierarchy[reg]['zones'][zon]['sales'] += sal
                                hierarchy[reg]['zones'][zon]['achievement'] += ach
                                hierarchy[reg]['zones'][zon]['territories'].append({'name': ter or 'Unknown Territory', 'sales': sal, 'achievement': ach})
                            final_list = []
                            for r_name in sorted(hierarchy.keys()):
                                r_data = hierarchy[r_name]
                                zones_list = []
                                for z_name in sorted(r_data['zones'].keys()):
                                    z_data = r_data['zones'][z_name]
                                    z_data['territories'] = sorted(z_data['territories'], key=lambda x: x['name'])
                                    zones_list.append(z_data)
                                r_data['zones'] = zones_list
                                final_list.append(r_data)
                            for r in final_list:
                                r['sales'] = round(r['sales'], 2)
                                r['achievement'] = round(r['achievement'], 2)
                                for z in r['zones']:
                                    z['sales'] = round(z['sales'], 2)
                                    z['achievement'] = round(z['achievement'], 2)
                            result = final_list
                            
                            try:
                                company = Company.objects.filter(Company_name=selected_db_key).first()
                                if company:
                                    regions_qs = Region.objects.filter(company=company)
                                    zones_qs = Zone.objects.filter(company=company)
                                    territories_qs = Territory.objects.filter(company=company)
                                else:
                                    regions_qs = Region.objects.all()
                                    zones_qs = Zone.objects.all()
                                    territories_qs = Territory.objects.all()
                                regions = list(regions_qs.order_by('name').values_list('name', flat=True).distinct())
                                zones = list(zones_qs.order_by('name').values_list('name', flat=True).distinct())
                                territories = list(territories_qs.order_by('name').values_list('name', flat=True).distinct())
                                request._geo_options = {'regions': regions, 'zones': zones, 'territories': territories}
                            except Exception:
                                request._geo_options = {'regions': [], 'zones': [], 'territories': []}
                            
                            diagnostics['start_date'] = (start_date_param or '').strip()
                            diagnostics['end_date'] = (end_date_param or '').strip()
                            diagnostics['region'] = (region_param or '').strip()
                            diagnostics['zone'] = (zone_param or '').strip()
                            diagnostics['territory'] = (territory_param or '').strip()
                            diagnostics['in_millions'] = (in_millions_param in ('', 'true','1','yes','y'))
                        except Exception as e_svat:
                            error = str(e_svat)
                    elif action == 'collection_vs_achievement':
                        try:
                            emp_id_param = request.GET.get('emp_id')
                            region_param = request.GET.get('region')
                            zone_param = request.GET.get('zone')
                            territory_param = request.GET.get('territory')
                            start_date_param = request.GET.get('start_date')
                            end_date_param = request.GET.get('end_date')
                            in_millions_param = (request.GET.get('in_millions') or '').strip().lower()
                            group_by_date_param = (request.GET.get('group_by_date') or '').strip().lower()
                            ignore_emp_filter_param = (request.GET.get('ignore_emp_filter') or '').strip().lower()
                            
                            emp_val = None
                            if emp_id_param is not None and emp_id_param != '':
                                try:
                                    emp_val = int(emp_id_param)
                                except Exception:
                                    error = 'Invalid emp_id'
                            
                            data = collection_vs_achievement(
                                conn,
                                emp_id=emp_val,
                                region=(region_param or '').strip() or None,
                                zone=(zone_param or '').strip() or None,
                                territory=(territory_param or '').strip() or None,
                                start_date=(start_date_param or '').strip() or None,
                                end_date=(end_date_param or '').strip() or None,
                                group_by_date=(group_by_date_param in ('true', '1', 'yes', 'on')),
                                ignore_emp_filter=(ignore_emp_filter_param in ('true', '1', 'yes', 'on'))
                            )
                            
                            if in_millions_param in ('', 'true','1','yes','y'):
                                scaled = []
                                for row in data or []:
                                    if isinstance(row, dict):
                                        r = dict(row)
                                        try:
                                            v = r.get('Collection_Target')
                                            if v is not None:
                                                r['Collection_Target'] = round((float(v) / 1000000.0), 2)
                                        except Exception:
                                            pass
                                        try:
                                            v = r.get('Collection_Achievement')
                                            if v is not None:
                                                r['Collection_Achievement'] = round((float(v) / 1000000.0), 2)
                                        except Exception:
                                            pass
                                        scaled.append(r)
                                    else:
                                        scaled.append(row)
                                data = scaled

                            hierarchy = {}
                            for row in (data or []):
                                if not isinstance(row, dict):
                                    continue
                                reg = row.get('Region', 'Unknown Region')
                                zon = row.get('Zone', 'Unknown Zone')
                                ter = row.get('TerritoryName', 'Unknown Territory')
                                sal = 0.0
                                ach = 0.0
                                try:
                                    v = row.get('Collection_Target')
                                    sal = float(v or 0.0)
                                except Exception:
                                    pass
                                try:
                                    v = row.get('Collection_Achievement')
                                    ach = float(v or 0.0)
                                except Exception:
                                    pass
                                
                                from_date = row.get('From_Date')
                                to_date = row.get('To_Date')
                                date_range_str = ''
                                if from_date and to_date:
                                    date_range_str = f"{from_date} to {to_date}"
                                elif from_date:
                                    date_range_str = f"From {from_date}"
                                elif to_date:
                                    date_range_str = f"To {to_date}"

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
                                    'employee_name': date_range_str  # Reuse employee_name field for Date Range display
                                })
                            
                            final_list = []
                            for r_name in sorted(hierarchy.keys()):
                                r_data = hierarchy[r_name]
                                zones_list = []
                                for z_name in sorted(r_data['zones'].keys()):
                                    z_data = r_data['zones'][z_name]
                                    z_data['territories'] = sorted(z_data['territories'], key=lambda x: x['name'])
                                    zones_list.append(z_data)
                                r_data['zones'] = zones_list
                                final_list.append(r_data)
                            
                            for r in final_list:
                                r['sales'] = round(r['sales'], 2)
                                r['achievement'] = round(r['achievement'], 2)
                                for z in r['zones']:
                                    z['sales'] = round(z['sales'], 2)
                                    z['achievement'] = round(z['achievement'], 2)
                            result = final_list
                            
                            try:
                                company = Company.objects.filter(Company_name=selected_db_key).first()
                                if company:
                                    regions_qs = Region.objects.filter(company=company)
                                    zones_qs = Zone.objects.filter(company=company)
                                    territories_qs = Territory.objects.filter(company=company)
                                else:
                                    regions_qs = Region.objects.all()
                                    zones_qs = Zone.objects.all()
                                    territories_qs = Territory.objects.all()
                                regions = list(regions_qs.order_by('name').values_list('name', flat=True).distinct())
                                zones = list(zones_qs.order_by('name').values_list('name', flat=True).distinct())
                                territories = list(territories_qs.order_by('name').values_list('name', flat=True).distinct())
                                request._geo_options = {'regions': regions, 'zones': zones, 'territories': territories}
                            except Exception:
                                request._geo_options = {'regions': [], 'zones': [], 'territories': []}
                            
                            diagnostics['emp_id'] = emp_val
                            diagnostics['start_date'] = (start_date_param or '').strip()
                            diagnostics['end_date'] = (end_date_param or '').strip()
                            diagnostics['region'] = (region_param or '').strip()
                            diagnostics['zone'] = (zone_param or '').strip()
                            diagnostics['territory'] = (territory_param or '').strip()
                            diagnostics['in_millions'] = (in_millions_param in ('', 'true','1','yes','y'))
                            diagnostics['group_by_date'] = (group_by_date_param in ('true', '1', 'yes', 'on'))
                            diagnostics['ignore_emp_filter'] = (ignore_emp_filter_param in ('true', '1', 'yes', 'on'))
                        except Exception as e_cva:
                            error = str(e_cva)
                    elif action == 'sales_vs_achievement_geo_profit':
                        try:
                            emp_id_param = request.GET.get('emp_id')
                            region_param = request.GET.get('region')
                            zone_param = request.GET.get('zone')
                            territory_param = request.GET.get('territory')
                            start_date_param = request.GET.get('start_date')
                            end_date_param = request.GET.get('end_date')
                            in_millions_param = (request.GET.get('in_millions') or '').strip().lower()
                            group_by_emp_param = request.GET.get('group_by_emp')
                            
                            # Default to True for Profit
                            group_by_emp = True
                            if group_by_emp_param is not None:
                                group_by_emp = str(group_by_emp_param).strip().lower() in ('true','1','yes')
                            
                            emp_val = None
                            if emp_id_param is not None and emp_id_param != '':
                                try:
                                    emp_val = int(emp_id_param)
                                except Exception:
                                    error = 'Invalid emp_id'
                            
                            data = sales_vs_achievement_geo_profit(
                                conn, 
                                emp_id=emp_val,
                                region=(region_param or '').strip() or None, 
                                zone=(zone_param or '').strip() or None, 
                                territory=(territory_param or '').strip() or None,
                                start_date=(start_date_param or '').strip() or None,
                                end_date=(end_date_param or '').strip() or None,
                                group_by_emp=group_by_emp
                            )
                            
                            # Scaling to millions if requested
                            if in_millions_param in ('', 'true','1','yes','y'):
                                scaled = []
                                for row in data or []:
                                    if isinstance(row, dict):
                                        r = dict(row)
                                        try:
                                            v = r.get('Sales')
                                            if v is None: v = r.get('SALES')
                                            if v is not None:
                                                r['Sales'] = round((float(v) / 1000000.0), 2)
                                        except Exception:
                                            pass
                                        try:
                                            v = r.get('Achievement')
                                            if v is None: v = r.get('ACHIEVEMENT')
                                            if v is not None:
                                                r['Achievement'] = round((float(v) / 1000000.0), 2)
                                        except Exception:
                                            pass
                                        scaled.append(r)
                                    else:
                                        scaled.append(row)
                                data = scaled
                            
                            # Hierarchical Transformation
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
                                    v = row.get('Sales')
                                    if v is None: v = row.get('SALES')
                                    sal = float(v or 0.0)
                                except: pass
                                try:
                                    v = row.get('Achievement')
                                    if v is None: v = row.get('ACHIEVEMENT')
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

                            # Convert dicts to sorted lists for rendering
                            final_list = []
                            for r_name in sorted(hierarchy.keys()):
                                r_data = hierarchy[r_name]
                                zones_list = []
                                for z_name in sorted(r_data['zones'].keys()):
                                    z_data = r_data['zones'][z_name]
                                    # Sort territories by name
                                    z_data['territories'] = sorted(z_data['territories'], key=lambda x: x['name'])
                                    zones_list.append(z_data)
                                r_data['zones'] = zones_list
                                final_list.append(r_data)
                            
                            # Rounding totals after aggregation
                            for r in final_list:
                                r['sales'] = round(r['sales'], 2)
                                r['achievement'] = round(r['achievement'], 2)
                                for z in r['zones']:
                                    z['sales'] = round(z['sales'], 2)
                                    z['achievement'] = round(z['achievement'], 2)

                            result = final_list
                            
                            try:
                                company = Company.objects.filter(Company_name=selected_db_key).first()
                                if company:
                                    regions_qs = Region.objects.filter(company=company)
                                    zones_qs = Zone.objects.filter(company=company)
                                    territories_qs = Territory.objects.filter(company=company)
                                else:
                                    regions_qs = Region.objects.all()
                                    zones_qs = Zone.objects.all()
                                    territories_qs = Territory.objects.all()
                                regions = list(regions_qs.order_by('name').values_list('name', flat=True).distinct())
                                zones = list(zones_qs.order_by('name').values_list('name', flat=True).distinct())
                                territories = list(territories_qs.order_by('name').values_list('name', flat=True).distinct())
                                request._geo_options = {'regions': regions, 'zones': zones, 'territories': territories}
                            except Exception:
                                request._geo_options = {'regions': [], 'zones': [], 'territories': []}
                                
                            diagnostics['emp_id'] = emp_val
                            diagnostics['start_date'] = (start_date_param or '').strip()
                            diagnostics['end_date'] = (end_date_param or '').strip()
                            diagnostics['region'] = (region_param or '').strip()
                            diagnostics['zone'] = (zone_param or '').strip()
                            diagnostics['territory'] = (territory_param or '').strip()
                            diagnostics['in_millions'] = (in_millions_param in ('', 'true','1','yes','y'))
                            diagnostics['group_by_emp'] = group_by_emp
                            
                        except Exception as e_geo_prof:
                            error = str(e_geo_prof)
                    elif action == 'sales_vs_achievement_by_emp':
                        try:
                            emp_id_param = request.GET.get('emp_id')
                            territory_param = request.GET.get('territory')
                            year_param = None
                            month_param = None
                            start_date_param = request.GET.get('start_date')
                            end_date_param = request.GET.get('end_date')
                            in_millions_param = (request.GET.get('in_millions') or '').strip().lower()
                            group_by_param = (request.GET.get('group_by') or '').strip().lower()
                            if group_by_param not in ('emp','territory','month'):
                                group_by_param = 'territory'
                            emp_val = None
                            if emp_id_param is not None and emp_id_param != '':
                                try:
                                    emp_val = int(emp_id_param)
                                except Exception:
                                    error = 'Invalid emp_id'
                            yr_val = None
                            mo_val = None
                            if error is None:
                                from .hana_connect import sales_vs_achievement_by_emp
                                data = sales_vs_achievement_by_emp(conn, emp_val, (territory_param or '').strip() or None, yr_val, mo_val, (start_date_param or '').strip() or None, (end_date_param or '').strip() or None)
                                if in_millions_param in ('', 'true','1','yes','y'):
                                    scaled = []
                                    for row in data or []:
                                        if isinstance(row, dict):
                                            r = dict(row)
                                            try:
                                                v = r.get('Sales_Target', None)
                                                if v is None:
                                                    v = r.get('SALES_TARGET', None)
                                                if v is not None:
                                                    r['SALES_TARGET'] = round((float(v) / 1000000.0), 2)
                                                    r.pop('Sales_Target', None)
                                            except Exception:
                                                pass
                                            try:
                                                v = r.get('Achievement', None)
                                                if v is None:
                                                    v = r.get('ACHIEVEMENT', None)
                                                if v is None:
                                                    v = r.get('ACCHIVEMENT', None)
                                                if v is not None:
                                                    r['ACCHIVEMENT'] = round((float(v) / 1000000.0), 2)
                                                    r.pop('Achievement', None)
                                            except Exception:
                                                pass
                                            scaled.append(r)
                                        else:
                                            scaled.append(row)
                                    data = scaled
                                gb = (request.GET.get('group_by') or '').strip().lower()
                                if gb not in ('emp','territory','month'):
                                    gb = 'territory'
                                if gb == 'emp':
                                    grouped = {}
                                    for r in (data or []):
                                        if isinstance(r, dict):
                                            eid = r.get('EMPID')
                                            if eid is None:
                                                continue
                                            if eid not in grouped:
                                                grouped[eid] = {
                                                    'EMPID': eid,
                                                    'SALES_TARGET': 0.0,
                                                    'ACCHIVEMENT': 0.0,
                                                    'TERRITORYID': 0,
                                                    'TERRITORYNAME': 'All Territories',
                                                    'F_REFDATE': r.get('F_REFDATE'),
                                                    'T_REFDATE': r.get('T_REFDATE'),
                                                }
                                            st = r.get('SALES_TARGET') or 0.0
                                            ac = r.get('ACCHIVEMENT') or 0.0
                                            try:
                                                grouped[eid]['SALES_TARGET'] += float(st)
                                            except Exception:
                                                pass
                                            try:
                                                grouped[eid]['ACCHIVEMENT'] += float(ac)
                                            except Exception:
                                                pass
                                            f = r.get('F_REFDATE')
                                            t = r.get('T_REFDATE')
                                            if f and (grouped[eid]['F_REFDATE'] is None or str(f) < str(grouped[eid]['F_REFDATE'])):
                                                grouped[eid]['F_REFDATE'] = f
                                            if t and (grouped[eid]['T_REFDATE'] is None or str(t) > str(grouped[eid]['T_REFDATE'])):
                                                grouped[eid]['T_REFDATE'] = t
                                    agg = []
                                    for _, g in grouped.items():
                                        row = {
                                            'EMPID': g['EMPID'],
                                            'TERRITORYID': g['TERRITORYID'],
                                            'TERRITORYNAME': g['TERRITORYNAME'],
                                            'SALES_TARGET': g['SALES_TARGET'],
                                            'ACCHIVEMENT': g['ACCHIVEMENT'],
                                            'F_REFDATE': g['F_REFDATE'],
                                            'T_REFDATE': g['T_REFDATE'],
                                        }
                                        agg.append(row)
                                    data = agg
                                result = data
                                try:
                                    opts = territory_names(conn)
                                except Exception:
                                    opts = []
                                territory_options = []
                                for row in opts or []:
                                    v = row.get('TERRITORYNAME') or row.get('TerritoryName') or row.get('DESCRIPT') or row.get('descript')
                                    if v and v not in territory_options:
                                        territory_options.append(v)
                                diagnostics['territory_options_count'] = len(territory_options)
                                diagnostics['selected_territory'] = territory_param or ''
                                diagnostics['emp_id'] = emp_val
                                diagnostics['year'] = None
                                diagnostics['month'] = None
                                diagnostics['start_date'] = (start_date_param or '').strip()
                                diagnostics['end_date'] = (end_date_param or '').strip()
                                diagnostics['in_millions'] = (in_millions_param in ('', 'true','1','yes','y'))
                                request._territory_options = territory_options
                        except Exception as e_sa_emp:
                            error = str(e_sa_emp)
                    elif action == 'sales_orders':
                        try:
                            card_code_param = request.GET.get('card_code')
                            doc_status_param = request.GET.get('doc_status')
                            from_date_param = request.GET.get('from_date')
                            to_date_param = request.GET.get('to_date')
                            limit_param = request.GET.get('limit')
                            
                            limit_val = 100
                            try:
                                if limit_param:
                                    limit_val = int(limit_param)
                            except Exception:
                                limit_val = 100
                            
                            data = sales_orders_all(
                                conn, 
                                limit=limit_val,
                                card_code=(card_code_param or '').strip() or None,
                                doc_status=(doc_status_param or '').strip() or None,
                                from_date=(from_date_param or '').strip() or None,
                                to_date=(to_date_param or '').strip() or None
                            )
                            result = data
                            if isinstance(result, list) and len(result) == 0:
                                error = 'No sales orders found'
                            diagnostics['card_code'] = (card_code_param or '').strip()
                            diagnostics['doc_status'] = (doc_status_param or '').strip()
                            diagnostics['from_date'] = (from_date_param or '').strip()
                            diagnostics['to_date'] = (to_date_param or '').strip()
                            diagnostics['limit'] = limit_val
                        except Exception as e_so:
                            error = str(e_so)
                    elif action == 'customer_lov':
                        try:
                            search_param = request.GET.get('search')
                            top_param = request.GET.get('top') or request.GET.get('limit')
                            lim = None
                            try:
                                if top_param:
                                    lim = int(str(top_param).strip())
                            except Exception:
                                lim = None
                            data = customer_lov(conn, (search_param or '').strip() or None, limit=(lim or 5000))
                            result = data
                        except Exception as e_cl:
                            error = str(e_cl)
                    elif action == 'child_customers':
                        try:
                            father_card = (request.GET.get('father_card', '') or '').strip()
                            if father_card:
                                data = child_card_code(conn, father_card, None)
                                result = data
                                diagnostics['father_card'] = father_card
                            else:
                                # If no father_card is provided, show all child customers
                                from .hana_connect import all_child_customers
                                data = all_child_customers(conn, limit=5000)
                                result = data
                        except Exception as e_cc:
                            error = str(e_cc)
                    elif action == 'item_lov':
                        try:
                            search_param = request.GET.get('search')
                            db_param = (request.GET.get('database') or '').strip()
                            
                            # Handle database parameter for admin view
                            if db_param:
                                norm = db_param.strip().upper().replace('-APP', '_APP')
                                if '4B-BIO' in norm:
                                    cfg['schema'] = '4B-BIO_APP'
                                elif '4B-ORANG' in norm:
                                    cfg['schema'] = '4B-ORANG_APP'
                                else:
                                    cfg['schema'] = db_param
                                # Reconnect with new schema
                                try:
                                    conn.close()
                                except Exception:
                                    pass
                                conn = dbapi.connect(**kwargs)
                                if cfg['schema']:
                                    sch = cfg['schema']
                                    cur = conn.cursor()
                                    cur.execute(f'SET SCHEMA "{sch}"')
                                    cur.close()
                            
                            data = item_lov(conn, (search_param or '').strip() or None)
                            result = data
                        except Exception as e_il:
                            error = str(e_il)
                    elif action == 'projects_lov':
                        try:
                            search_param = request.GET.get('search')
                            data = projects_lov(conn, (search_param or '').strip() or None)
                            result = data
                        except Exception as e_pl:
                            error = str(e_pl)
                    elif action == 'crop_lov':
                        try:
                            data = crop_lov(conn)
                            result = data
                        except Exception as e_crop:
                            error = str(e_crop)
                    elif action == 'item_price':
                        try:
                            doc_entry = (request.GET.get('doc_entry', '') or '').strip()
                            item_code = (request.GET.get('item_code', '') or '').strip()
                            if not doc_entry or not item_code:
                                error_fields['doc_entry'] = 'doc_entry is required'
                                error_fields['item_code'] = 'item_code is required'
                                error = 'doc_entry and item_code are required parameters'
                            else:
                                price_row = unit_price_by_policy(conn, doc_entry, item_code)
                                if price_row:
                                    price_val = price_row.get('U_frp') if isinstance(price_row, dict) else None
                                    try:
                                        price_val = float(price_val) if price_val is not None else price_val
                                    except Exception:
                                        pass
                                    result = [{
                                        'DocEntry': doc_entry,
                                        'ItemCode': item_code,
                                        'Unit_Price': price_val
                                    }]
                                else:
                                    result = []
                                    error = f'No price found for DocEntry={doc_entry} and ItemCode={item_code}'
                        except Exception as e_price:
                            error = str(e_price)
                    elif action == 'contact_person_name':
                        try:
                            card_code = (request.GET.get('card_code', '') or '').strip()
                            contact_code = (request.GET.get('contact_code', '') or '').strip()
                            show_all = (request.GET.get('show_all', '') or '').strip().lower() in ('true','1','yes')
                            from .hana_connect import contacts_all, contacts_by_card
                            if show_all or (not card_code and not contact_code):
                                data = contacts_all(conn)
                            elif card_code and not contact_code:
                                data = contacts_by_card(conn, card_code)
                            elif card_code and contact_code:
                                one = contact_person_name(conn, card_code, contact_code)
                                data = []
                                if one:
                                    data = [{
                                        'CardCode': card_code,
                                        'ContactCode': contact_code,
                                        'Name': one.get('Name') if isinstance(one, dict) else one
                                    }]
                            else:
                                data = []
                            result = data
                        except Exception as e:
                            error = str(e)
                    elif action == 'customer_addresses':
                        try:
                            card_code = (request.GET.get('card_code', '') or '').strip()
                            show_all = (request.GET.get('show_all', '') or '').strip().lower() in ('true','1','yes')
                            if show_all or not card_code:
                                from .hana_connect import customer_addresses_all
                                data = customer_addresses_all(conn)
                            else:
                                data = customer_addresses(conn, card_code)
                            result = data
                        except Exception as e:
                            error = str(e)
                    elif action == 'warehouse_for_item':
                        try:
                            item_code = request.GET.get('item_code', '').strip()
                            if not item_code:
                                from .hana_connect import warehouses_all
                                data = warehouses_all(conn)
                            else:
                                data = warehouse_for_item(conn, item_code)
                            result = data
                        except Exception as e:
                            error = str(e)
                    elif action == 'sales_tax_codes':
                        try:
                            data = sales_tax_codes(conn)
                            result = data
                        except Exception as e:
                            error = str(e)
                    elif action == 'policy_link':
                        try:
                            bp_code = request.GET.get('bp_code', '')
                            show_all = request.GET.get('show_all', '').lower() in ('true', '1', 'yes')
                            
                            if not bp_code and not show_all:
                                error = 'bp_code is required, or set show_all=true to see all policies'
                            else:
                                data = policy_link(conn, bp_code=bp_code if bp_code else None, show_all=show_all)
                                result = data
                        except Exception as e:
                            error = str(e)
                    elif action == 'project_balance':
                        try:
                            project_code = (request.GET.get('project_code', '') or '').strip()
                            show_all = (request.GET.get('show_all', '') or '').strip().lower() in ('true','1','yes')
                            from .hana_connect import project_balances_all
                            if show_all or not project_code:
                                data = project_balances_all(conn)
                                result = data
                            else:
                                one = project_balance(conn, project_code)
                                result = []
                                if one:
                                    result = [one]
                        except Exception as e:
                            error = str(e)
                    elif action == 'policy_balance_by_customer':
                        try:
                            # Accept card_code from either dropdown or manual input
                            card_code = request.GET.get('card_code', '').strip()
                            card_code_manual = request.GET.get('card_code_manual', '').strip()
                            # Prefer manual input if provided, otherwise use dropdown
                            final_card_code = card_code_manual if card_code_manual else card_code
                            # card_code is optional - if not provided, show all
                            data = policy_balance_by_customer(conn, final_card_code if final_card_code else None)
                            result = data
                        except Exception as e:
                            error = str(e)
                    
                    customer_list = []
                    try:
                        if action == 'child_customers':
                            from .hana_connect import customer_codes_all, parents_with_children
                            only_parents = (request.GET.get('only_parents', '') or '').strip().lower() in ('1','true','yes')
                            if only_parents:
                                customer_data = parents_with_children(conn, limit=1000)
                            else:
                                customer_data = customer_codes_all(conn, limit=5000)
                                if not customer_data:
                                    customer_data = parents_with_children(conn, limit=1000)
                        else:
                            customer_data = customer_lov(conn, search=None)
                        if customer_data and isinstance(customer_data, list):
                            customer_list = customer_data
                    except Exception as e:
                        logger.error(f"Failed to load customer list: {e}")
                        customer_list = []
                    
                finally:
                    try:
                        conn.close()
                    except Exception:
                        pass
        except Exception as e:
            error = _sanitize_error(e)
    
    # Set customer_list if not already set
    if 'customer_list' not in locals():
        customer_list = []
    selected_father_name = ''
    try:
        if action == 'child_customers':
            fc = (request.GET.get('father_card') or '').strip()
            if fc and isinstance(customer_list, list):
                for c in customer_list:
                    cc = c.get('CardCode')
                    if isinstance(cc, str) and cc == fc:
                        selected_father_name = (c.get('CardName') or '')
                        break
    except Exception:
        selected_father_name = ''
    
    if request.headers.get('Accept') == 'application/json' and (action or request.GET.get('json')):
        return JsonResponse({'result': result, 'error': error, 'diagnostics': diagnostics})
    result_json = None
    if result is not None:
        try:
            result_json = json.dumps(result, ensure_ascii=False, indent=2, default=str)
        except Exception:
            result_json = None
    diag_json = None
    try:
        diag_json = json.dumps(diagnostics, ensure_ascii=False, indent=2)
    except Exception:
        diag_json = None
    territory_options = getattr(request, '_territory_options', [])
    selected_territory = (request.GET.get('territory') or '').strip()
    current_emp_id = (request.GET.get('emp_id') or '').strip()
    current_year = ''
    current_month = ''
    current_start_date = (request.GET.get('start_date') or '').strip()
    current_end_date = (request.GET.get('end_date') or '').strip()
    
    # Fetch customer list for policy_balance_by_customer filter
    customer_options = []
    if action == 'policy_balance_by_customer':
        try:
            from hdbcli import dbapi
            pwd = os.environ.get('HANA_PASSWORD','')
            if cfg['host']:
                use_encrypt = str(cfg['encrypt']).strip().lower() in ('true','1','yes')
                kwargs = {'address': cfg['host'], 'port': int(cfg['port']), 'user': cfg['user'] or '', 'password': pwd or ''}
                if use_encrypt:
                    kwargs['encrypt'] = True
                    if cfg['ssl_validate']:
                        kwargs['sslValidateCertificate'] = (str(cfg['ssl_validate']).strip().lower() in ('true','1','yes'))
                temp_conn = dbapi.connect(**kwargs)
                if cfg['schema']:
                    cur = temp_conn.cursor()
                    cur.execute(f'SET SCHEMA "{cfg["schema"]}"')
                    cur.close()
                customer_options = customer_lov(temp_conn)
                temp_conn.close()
        except Exception as e:
            pass
    
    # Item dropdown options for warehouse_for_item
    item_options = []
    if action == 'warehouse_for_item':
        try:
            from hdbcli import dbapi
            pwd = os.environ.get('HANA_PASSWORD','')
            if cfg['host']:
                use_encrypt = str(cfg['encrypt']).strip().lower() in ('true','1','yes')
                kwargs = {'address': cfg['host'], 'port': int(cfg['port']), 'user': cfg['user'] or '', 'password': pwd or ''}
                if use_encrypt:
                    kwargs['encrypt'] = True
                    if cfg['ssl_validate']:
                        kwargs['sslValidateCertificate'] = (str(cfg['ssl_validate']).strip().lower() in ('true','1','yes'))
                temp_conn = dbapi.connect(**kwargs)
                if cfg['schema']:
                    cur = temp_conn.cursor()
                    cur.execute(f'SET SCHEMA "{cfg["schema"]}"')
                    cur.close()
                item_options = item_lov(temp_conn, search=None)
                temp_conn.close()
        except Exception:
            item_options = []

    # Project options for project_balance filter
    project_options = []
    try:
        if action == 'project_balance':
            from hdbcli import dbapi
            pwd = os.environ.get('HANA_PASSWORD','')
            if cfg['host']:
                use_encrypt = str(cfg['encrypt']).strip().lower() in ('true','1','yes')
                kwargs = {'address': cfg['host'], 'port': int(cfg['port']), 'user': cfg['user'] or '', 'password': pwd or ''}
                if use_encrypt:
                    kwargs['encrypt'] = True
                    if cfg['ssl_validate']:
                        kwargs['sslValidateCertificate'] = (str(cfg['ssl_validate']).strip().lower() in ('true','1','yes'))
                temp_conn = dbapi.connect(**kwargs)
                if cfg['schema']:
                    cur = temp_conn.cursor()
                    cur.execute(f'SET SCHEMA "{cfg["schema"]}"')
                    cur.close()
                project_options = projects_lov(temp_conn, search=None)
                temp_conn.close()
    except Exception:
        project_options = []

    result_rows = result if isinstance(result, list) else []
    result_cols = []
    if action == 'child_customers':
        # Check if FatherCard column is present in results (all_child_customers includes it)
        if result_rows and isinstance(result_rows[0], dict) and 'FatherCard' in result_rows[0]:
            result_cols = ['FatherCard', 'CardCode', 'CardName']
        else:
            result_cols = ['CardCode', 'CardName']
    elif isinstance(result_rows, list) and len(result_rows) > 0 and isinstance(result_rows[0], dict):
        try:
            result_cols = list(result_rows[0].keys())
        except Exception:
            result_cols = []
    page_param = (request.GET.get('page') or '1').strip()
    page_size_param = (request.GET.get('page_size') or '').strip()
    try:
        page_num = int(page_param) if page_param else 1
    except Exception:
        page_num = 1
    # Use default page size for products_catalog
    if action == 'products_catalog':
        default_page_size = 10
    else:
        default_page_size = 10
        try:
            default_page_size = int(getattr(settings, 'REST_FRAMEWORK', {}).get('PAGE_SIZE', 10) or 10)
        except Exception:
            default_page_size = 10
    try:
        page_size = int(page_size_param) if page_size_param else default_page_size
    except Exception:
        page_size = default_page_size
    paginator = None
    page_obj = None
    paged_rows = result_rows
    try:
        if isinstance(result_rows, list) and result_rows:
            paginator = Paginator(result_rows, page_size)
            page_obj = paginator.get_page(page_num)
            paged_rows = list(page_obj.object_list)
    except Exception:
        paged_rows = result_rows
    table_rows = []
    if result_cols:
        for row in paged_rows:
            if isinstance(row, dict):
                values = []
                for c in result_cols:
                    values.append(row.get(c))
                table_rows.append(values)
    # Get base URL for full image URLs
    # Priority: settings.BASE_URL (configurable) -> request-based URL
    base_url = getattr(settings, 'BASE_URL', None) or request.build_absolute_uri('/').rstrip('/')
    
    # Add full URLs to product images if this is products_catalog action
    if action == 'products_catalog' and result_rows:
        for row in result_rows:
            if isinstance(row, dict):
                if row.get('product_image_url'):
                    row['product_image_url_full'] = base_url + row['product_image_url']
                if row.get('product_description_urdu_url'):
                    row['product_description_urdu_url_full'] = base_url + row['product_description_urdu_url']
    
    geo_options = getattr(request, '_geo_options', {'regions': [], 'zones': [], 'territories': []})
    
    return render(
        request,
        'admin/sap_integration/hana_connect.html',
        {
            'result_json': result_json,
            'error': error,
            'diagnostics_json': diag_json,
            'territory_options': territory_options,
            'geo_options': geo_options,
            'selected_territory': selected_territory,
            'current_action': action,
            'current_emp_id': current_emp_id,
            'current_year': current_year,
            'current_month': current_month,
            'current_start_date': current_start_date,
            'current_end_date': current_end_date,
            'months': [],
            'result_rows': paged_rows,
            'result_cols': result_cols,
            'table_rows': table_rows,
            'is_tabular': (action in ('territory_summary','sales_vs_achievement','sales_vs_achievement_geo','sales_vs_achievement_geo_inv','sales_vs_achievement_geo_profit','collection_vs_achievement','sales_vs_achievement_by_emp','sales_vs_achievement_territory','policy_customer_balance','list_territories','list_territories_full','list_cwl','sales_orders','customer_lov','child_customers','item_lov','projects_lov','crop_lov','policy_balance_by_customer','warehouse_for_item','contact_person_name','project_balance','customer_addresses','products_catalog','item_price')),
            'current_card_code': (request.GET.get('card_code_manual') or request.GET.get('card_code') or '').strip(),
            'customer_options': customer_options,
            'customer_list': customer_list,
            'selected_father_name': selected_father_name,
            'db_options': db_options,
            'selected_db_key': selected_db_key,
            'base_url': base_url,
            'item_options': item_options,
            'project_options': project_options,
            'pagination': {
                'page': (page_obj.number if page_obj else 1),
                'num_pages': (paginator.num_pages if paginator else 1),
                'has_next': (page_obj.has_next() if page_obj else False),
                'has_prev': (page_obj.has_previous() if page_obj else False),
                'next_page': ((page_obj.next_page_number() if page_obj and page_obj.has_next() else None)),
                'prev_page': ((page_obj.previous_page_number() if page_obj and page_obj.has_previous() else None)),
                'count': (paginator.count if paginator else len(result_rows)),
                'page_size': page_size,
            },
        }
    )

@staff_member_required
def bp_entry_admin(request):
    result = None
    error = None
    error_fields = {}
    fields = {
        'Series': '70',
        'CardName': 'TEST API POST',
        'CardType': 'cCustomer',
        'GroupCode': '100',
        'Address': 'Pull Sardarpur Kabirwala',
        'Phone1': '923224052911',
        'MobilePhone': '',
        'ContactPerson': 'Abdul Razzaq',
        'FederalTaxID': '36102-1926109-7',
        'AdditionalID': '',
        'OwnerIDNumber': '36102-1926109-7',
        'UnifiedFederalTaxID': '36102-1926109-7',
        'Territory': '235',
        'DebitorAccount': 'A020301001',
        'U_leg': '17-5349',
        'U_gov': '2023-05-28',
        'U_fil': '02',
        'U_lic': '506/R/2020',
        'U_region': 'Green',
        'U_zone': 'Sahiwal',
        'U_WhatsappMessages': 'YES',
        'VatGroup': 'AT1',
        'VatLiable': 'vLiable',
    }
    if request.method == 'POST':
        created = None
        result = None
        try:
            for k in list(fields.keys()):
                fields[k] = (request.POST.get(k) or '').strip()
            # Comprehensive validation to prevent SAP "Failed to initialize object data" error
            if not fields['CardName'] or not fields['CardName'].strip():
                error_fields['CardName'] = 'CardName is required and cannot be empty'
            
            # Validate CardName length (SAP typically has limits)
            if fields['CardName'] and len(fields['CardName'].strip()) > 100:
                error_fields['CardName'] = 'CardName must be 100 characters or less'
            
            # Validate Series
            try:
                series_val = int(fields['Series']) if fields['Series'] else 70
                if series_val <= 0:
                    error_fields['Series'] = 'Series must be a positive number'
            except Exception:
                error_fields['Series'] = 'Series must be a valid number'
            
            # Validate GroupCode
            try:
                group_val = int(fields['GroupCode']) if fields['GroupCode'] else 100
                if group_val <= 0:
                    error_fields['GroupCode'] = 'GroupCode must be a positive number'
            except Exception:
                error_fields['GroupCode'] = 'GroupCode must be a valid number'
                
            # Validate Territory if provided
            if fields['Territory']:
                try:
                    territory_val = int(fields['Territory'])
                    if territory_val <= 0:
                        error_fields['Territory'] = 'Territory must be a positive number'
                except Exception:
                    error_fields['Territory'] = 'Territory must be a valid number'
                    
            # Return early if validation fails
            if error_fields:
                error = 'Please fix the validation errors below'
            # Only create payload if validation passes
            if not error_fields:
                # Build payload exactly like working Postman request with empty strings instead of null
                # This structure matches SAP Business One Service Layer requirements
                # IMPORTANT: Field order matters! Must match working Postman request exactly
                payload = {
                    'Series': int(fields['Series']) if fields['Series'] else 70,
                    'CardName': fields['CardName'].strip(),
                    'CardType': fields['CardType'].strip() if fields['CardType'] else 'cCustomer',
                    'GroupCode': int(fields['GroupCode']) if fields['GroupCode'] else 100,
                    'Address': fields['Address'].strip() if fields['Address'] else '',
                    'Phone1': fields['Phone1'].strip() if fields['Phone1'] else '',
                    'ContactPerson': fields['ContactPerson'].strip() if fields['ContactPerson'] else '',
                    'FederalTaxID': fields['FederalTaxID'].strip() if fields['FederalTaxID'] else '',
                    'AdditionalID': None if not fields['AdditionalID'] or not fields['AdditionalID'].strip() else fields['AdditionalID'].strip(),
                    'OwnerIDNumber': fields['OwnerIDNumber'].strip() if fields['OwnerIDNumber'] else '',
                    'UnifiedFederalTaxID': fields['UnifiedFederalTaxID'].strip() if fields['UnifiedFederalTaxID'] else '',
                }
                
                # Add Territory if provided
                if fields['Territory'] and fields['Territory'].strip():
                    payload['Territory'] = int(fields['Territory'])
                
                # Add standard fields
                if fields['DebitorAccount'] and fields['DebitorAccount'].strip():
                    payload['DebitorAccount'] = fields['DebitorAccount'].strip()
                
                # Add UDF fields
                if fields['U_leg'] and fields['U_leg'].strip():
                    payload['U_leg'] = fields['U_leg'].strip()
                if fields['U_gov'] and fields['U_gov'].strip():
                    payload['U_gov'] = fields['U_gov'].strip()
                if fields['U_fil'] and fields['U_fil'].strip():
                    payload['U_fil'] = fields['U_fil'].strip()
                if fields['U_lic'] and fields['U_lic'].strip():
                    payload['U_lic'] = fields['U_lic'].strip()
                if fields['U_region'] and fields['U_region'].strip():
                    payload['U_region'] = fields['U_region'].strip()
                if fields['U_zone'] and fields['U_zone'].strip():
                    payload['U_zone'] = fields['U_zone'].strip()
                if fields['U_WhatsappMessages'] and fields['U_WhatsappMessages'].strip():
                    payload['U_WhatsappMessages'] = fields['U_WhatsappMessages'].strip()
                
                # Add VAT fields
                if fields['VatGroup'] and fields['VatGroup'].strip():
                    payload['VatGroup'] = fields['VatGroup'].strip()
                if fields['VatLiable'] and fields['VatLiable'].strip():
                    payload['VatLiable'] = fields['VatLiable'].strip()
                
                # Add arrays at the end - exact match to Postman structure
                payload['BPAddresses'] = [
                    {
                        'AddressName': 'Bill To',
                        'AddressName2': '',
                        'AddressName3': '',
                        'City': '',
                        'Country': 'PK',
                        'State': '',
                        'Street': fields['Address'].strip() if fields['Address'] else '',
                        'AddressType': 'bo_BillTo',
                    }
                ]
                payload['ContactEmployees'] = [
                    {
                        'Name': fields['ContactPerson'].strip() if fields['ContactPerson'] else '',
                        'Position': '',
                        'MobilePhone': '',
                        'E_Mail': '',
                    }
                ]
                
                selected_db = request.session.get('selected_db', '4B-BIO')
                client = SAPClient(company_db_key=selected_db)
                try:
                    # Log the payload for debugging
                    import logging
                    logger = logging.getLogger('sap')
                    logger.info(f"SAP BP Payload: {json.dumps(payload, indent=2)}")
                    logger.info(f"SAP Session: {client.get_session_id()}")
                    
                    created = client.create_business_partner(payload)
                    # Ensure created is in the expected format
                    if not isinstance(created, (dict, list, type(None))):
                        # If it's a string or other type, convert to dict
                        created = {"error": str(created)}
                except Exception as e:
                    error = str(e)
                    msg = str(error or '')
                    
                    # Add payload and session info to error message for debugging
                    try:
                        payload_debug = json.dumps(payload, indent=2, default=str)
                        session_info = f"\n\nSession ID: {client.get_session_id()}"
                        user_info = f"\nSAP User: {client.username}"
                        db_info = f"\nCompany DB: {client.company_db}"
                        error = f"{msg}\n\nPayload sent to SAP:\n{payload_debug}{session_info}{user_info}{db_info}\n\nNote: This exact payload works in Postman. Check if SAP user has permission to create Business Partners."
                    except Exception:
                        pass
                    
                    # Provide specific help for common SAP errors
                    if "Failed to initialize object data" in msg:
                        # Don't clear error_fields, just show helpful message
                        if not error_fields:
                            error_fields['CardName'] = 'SAP rejected this value - check field requirements'
                    
                    # Try to extract JSON error payload and map detailed paths to form fields
                    parsed = None
                    try:
                        start = msg.find('{')
                        if start != -1:
                            parsed = json.loads(msg[start:])
                    except Exception:
                        parsed = None
                    
                    def map_path_to_field(path: str):
                        p = str(path or '')
                        if p.startswith('BPAddresses'):
                            return 'Address'
                        if p.startswith('ContactEmployees'):
                            return 'ContactPerson'
                        if p.startswith('Phone1'):
                            return 'Phone1'
                        if p.startswith('MobilePhone'):
                            return 'MobilePhone'
                        return p.split('/')[0] if '/' in p else p
                    
                    # Populate error_fields from Service Layer error structure
                    if isinstance(parsed, dict):
                        try:
                            error_data = parsed.get('error', {})
                            if isinstance(error_data, dict):
                                message_data = error_data.get('message', {})
                                if isinstance(message_data, dict):
                                    emsg = message_data.get('value')
                                    if emsg:
                                        error = emsg
                        except Exception:
                            pass
                        try:
                            error_data = parsed.get('error', {})
                            if isinstance(error_data, dict):
                                details = error_data.get('details')
                                if isinstance(details, list):
                                    for d in details:
                                        if isinstance(d, dict):
                                            fld = map_path_to_field(d.get('path'))
                                            msgv = d.get('message') or error
                                            if fld and msgv:
                                                error_fields[fld] = msgv
                                        elif isinstance(d, str):
                                            fld = map_path_to_field(d)
                                            if fld and (fld not in error_fields):
                                                error_fields[fld] = error
                        except Exception:
                            pass
                        # Also show parsed error JSON in response block
                        if not error_fields and parsed:
                            result = parsed
                    # Fallback keyword mapping if JSON not available
                    if not error_fields:
                        keys = [
                            'Series','CardName','CardType','GroupCode','Address','Phone1','ContactPerson',
                            'MobilePhone','FederalTaxID','AdditionalID','OwnerIDNumber','UnifiedFederalTaxID','Territory',
                            'DebitorAccount','U_leg','U_gov','U_fil','U_lic','U_region','U_zone','U_WhatsappMessages',
                            'VatGroup','VatLiable','BPAddresses','ContactEmployees','AddressName','Street','Name'
                        ]
                        low = msg.lower()
                        for k in keys:
                            if k.lower() in low:
                                mapped = k
                                if k in ('BPAddresses','AddressName','Street'):
                                    mapped = 'Address'
                                if k in ('ContactEmployees','Name'):
                                    mapped = 'ContactPerson'
                                if mapped not in error_fields:
                                    error_fields[mapped] = msg
                    # If we have no parsed JSON, still surface raw message
                    if result is None:
                        result = msg
                
                card_code = None
                if isinstance(created, dict):
                    card_code = created.get('CardCode') or created.get('code')
                    if not card_code:
                        hdrs = created.get('headers') if isinstance(created.get('headers'), dict) else None
                        if hdrs:
                            loc = hdrs.get('Location') or hdrs.get('location')
                            if isinstance(loc, str):
                                start = loc.find("BusinessPartners('")
                                if start != -1:
                                    start += len("BusinessPartners('")
                                    end = loc.find("')", start)
                                    if end != -1:
                                        card_code = loc[start:end]
                if card_code and isinstance(payload, dict) and payload.get('ContactEmployees'):
                    for ce in payload['ContactEmployees']:
                        try:
                            client.add_contact_employee(card_code, ce)
                        except Exception:
                            pass
                    try:
                        bp_result = client.get_business_partner(card_code, expand_contacts=True)
                        # Ensure result is in expected format
                        if isinstance(bp_result, (dict, list)):
                            result = bp_result
                        else:
                            result = created
                    except Exception:
                        result = created
                else:
                    result = created
        except Exception as e:
            error = str(e)
    result_json = None
    if result is not None:
        try:
            result_json = json.dumps(result, ensure_ascii=False, indent=2)
        except Exception:
            result_json = str(result)
    return render(
        request,
        'admin/sap_integration/bp_entry.html',
        {
            'fields': fields or {},
            'result_json': result_json,
            'error': error,
            'error_fields': error_fields or {},
        }
    )

@staff_member_required
def bp_lookup_admin(request):
    error = None
    result = None
    card_code = (request.GET.get('card_code') or request.POST.get('card_code') or '').strip()
    rows = []
    cols = []
    table_rows = []
    if request.method in ('POST',) or (request.method == 'GET'):
        try:
            selected_db = request.session.get('selected_db', '4B-BIO')
            client = SAPClient(company_db_key=selected_db)
            if card_code:
                result = client.get_bp_details(card_code)
            else:
                rows = client.list_business_partners(top=100, select='CardCode,CardName,GroupCode,VatGroup') or []
        except Exception as e:
            error = str(e)
    if isinstance(rows, list) and len(rows) > 0 and isinstance(rows[0], dict):
        try:
            cols = list(rows[0].keys())
        except Exception:
            cols = []
    if cols and rows:
        try:
            for r in rows:
                if isinstance(r, dict):
                    vals = []
                    for c in cols:
                        vals.append(r.get(c))
                    table_rows.append(vals)
        except Exception:
            table_rows = []
    result_json = None
    if result is not None:
        try:
            result_json = json.dumps(result, ensure_ascii=False, indent=2)
        except Exception:
            result_json = str(result)
    return render(
        request,
        'admin/sap_integration/bp_lookup.html',
        {
            'card_code': card_code,
            'result_json': result_json,
            'error': error,
            'rows': rows,
            'cols': cols,
            'table_rows': table_rows,
        }
    )


# Unified API for Frontend - Core function
def get_business_partner_data(request, card_code=None):
    """
    Unified API endpoint for frontend to get business partner data.
    This endpoint handles all SAP integration internally and returns clean data.
    
    Usage: 
        GET /api/sap/business-partner/ - List all business partners
        GET /api/sap/business-partner/{card_code}/ - Get specific business partner
    
    Examples: 
        GET /api/sap/business-partner/
        GET /api/sap/business-partner/BIC00001/
        GET /api/sap/business-partner/?top=50
        GET /api/sap/business-partner/?database=4B-BIO_APP
        GET /api/sap/business-partner/?database=4B-ORANG_APP
    """
    
    try:
        # Get HANA schema from database parameter, session, or company model
        db_param_received = request.GET.get('database', 'NOT PROVIDED')
        logger.info(f"[BUSINESS_PARTNER] Received database parameter: {db_param_received}")
        
        hana_schema = get_hana_schema_from_request(request)
        logger.info(f"[BUSINESS_PARTNER] Using HANA schema: {hana_schema}")
        
        # Map HANA schema to company_db_key for SAPClient
        # Extract the key from company name (e.g., 4B-BIO_APP -> 4B-BIO)
        if 'BIO' in hana_schema.upper():
            company_db_key = '4B-BIO'
        elif 'ORANG' in hana_schema.upper():
            company_db_key = '4B-ORANG'
        else:
            company_db_key = '4B-BIO'  # Default fallback
        
        logger.info(f"[BUSINESS_PARTNER] Using company_db_key: {company_db_key}")
        
        # Create SAP client with logging
        try:
            sap_client = SAPClient(company_db_key=company_db_key)
            logger.info(f"[BUSINESS_PARTNER] SAPClient created successfully with CompanyDB: {sap_client.company_db}")
        except Exception as e:
            logger.error(f"[BUSINESS_PARTNER] Failed to create SAPClient: {str(e)}")
            raise
        
        # If card_code is provided, get specific business partner
        if card_code and card_code.strip():
            # Get business partner details with specific fields
            bp_data = sap_client.get_bp_details(card_code.strip())
            
            # Return formatted response for frontend
            return Response({
                "success": True,
                "data": bp_data,
                "message": "Business partner data retrieved successfully"
            }, status=status.HTTP_200_OK)
        
        # Otherwise, list all business partners
        else:
            # Get parameters
            top_param = request.query_params.get('top')
            card_type_param = request.query_params.get('card_type', 'C')  # Default to Customers only (ORC*)
            
            # Set default limit to 500 for reasonable loading time
            # User can request more with ?top=10000 or ?top=0 (unlimited)
            max_records = 500
            if top_param is not None:
                try:
                    max_records = int(top_param)
                    if max_records == 0:
                        max_records = 10000  # 0 means "all", cap at 10k
                except Exception:
                    max_records = 500
            
            # Include CardType in select to enable filtering
            logger.info(f"[BUSINESS_PARTNER] Fetching business partners (limit: {max_records})")
            
            # Fetch records using pagination (SAP returns 20 per request)
            all_rows = []
            batch_size = 20  # SAP's default limit
            skip = 0
            batch_count = 0
            
            while len(all_rows) < max_records:
                batch = sap_client.list_business_partners(
                    top=batch_size, 
                    skip=skip,
                    select='CardCode,CardName,CardType,GroupCode,VatGroup'
                ) or []
                
                if not batch or len(batch) == 0:
                    logger.info(f"[BUSINESS_PARTNER] End of records reached at skip={skip}")
                    break
                    
                all_rows.extend(batch)
                batch_count += 1
                
                # Log every 10 batches to reduce spam
                if batch_count % 10 == 0 or len(batch) < batch_size:
                    logger.info(f"[BUSINESS_PARTNER] Fetched {batch_count} batches, total: {len(all_rows)} records")
                
                skip += batch_size
                
                # Safety check
                if batch_count > 500:
                    logger.warning(f"[BUSINESS_PARTNER] Reached max batch limit (500)")
                    break
            
            rows = all_rows
            logger.info(f"[BUSINESS_PARTNER] Total retrieved: {len(rows)} records from SAP in {batch_count} batches")
            
            # Filter by CardType only if specified (C=Customer, S=Supplier/Vendor)
            # SAP returns "cCustomer" and "cSupplier", so we need to map our parameter
            original_count = len(rows)
            if card_type_param and card_type_param.strip():
                card_type_upper = card_type_param.upper()
                if card_type_upper == 'C':
                    # Filter for Customers only (ORC*)
                    rows = [bp for bp in rows if 'customer' in bp.get('CardType', '').lower()]
                elif card_type_upper == 'S':
                    # Filter for Suppliers/Vendors only (ORV*)
                    rows = [bp for bp in rows if 'supplier' in bp.get('CardType', '').lower()]
                logger.info(f"[BUSINESS_PARTNER] After CardType={card_type_param} filter: {len(rows)} of {original_count} records")
            
            return Response({
                "success": True,
                "count": len(rows),
                "data": rows,
                "message": "Business partners retrieved successfully"
            }, status=status.HTTP_200_OK)
        
    except Exception as e:
        error_message = str(e)
        
        # Handle specific SAP errors
        if "not found" in error_message.lower() or "404" in error_message:
            return Response({
                "success": False,
                "error": "Business partner not found",
                "message": f"No business partner found with card code: {card_code}"
            }, status=status.HTTP_404_NOT_FOUND)
        
        elif "session" in error_message.lower() or "timeout" in error_message.lower():
            return Response({
                "success": False,
                "error": "SAP session error",
                "message": "SAP session expired or invalid. Please try again."
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
        else:
            return Response({
                "success": False,
                "error": "SAP integration failed",
                "message": f"Unable to retrieve business partner data: {error_message}"
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# Wrapper for list endpoint with Swagger documentation
@swagger_auto_schema(tags=['SAP'], 
    method='get',
    operation_description="List all Business Partners from SAP (CardCode NOT required - use this endpoint to get all BPs)",
    operation_summary="List All Business Partners",
    manual_parameters=[
        openapi.Parameter(
            'database',
            openapi.IN_QUERY,
            description="HANA database/schema to query. Accepts Company name values (e.g., 4B-BIO_APP, 4B-ORANG_APP) or company keys (e.g., 4B-BIO, 4B-ORANG). If not provided, falls back to session or first active company.",
            type=openapi.TYPE_STRING,
            required=False
        ),
        openapi.Parameter(
            'top',
            openapi.IN_QUERY,
            description="Maximum number of items to return (default 500, use 0 or 10000 for all records)",
            type=openapi.TYPE_INTEGER,
            required=False
        ),
        openapi.Parameter(
            'card_type',
            openapi.IN_QUERY,
            description="Filter by CardType: C (Customer/Dealer - default, shows only ORC*), S (Supplier/Vendor - shows ORV*). Omit or use empty string to show all.",
            type=openapi.TYPE_STRING,
            enum=['C', 'S', ''],
            required=False,
            default='C'
        )
    ],
    responses={
        200: openapi.Response(
            description="Business Partners list retrieved successfully",
            examples={
                "application/json": {
                    "success": True,
                    "count": 2,
                    "data": [
                        {
                            "CardCode": "BIC00001",
                            "CardName": "Sample Customer 1",
                            "GroupCode": 100,
                            "VatGroup": "SE"
                        },
                        {
                            "CardCode": "BIC00002",
                            "CardName": "Sample Customer 2",
                            "GroupCode": 101,
                            "VatGroup": "SE"
                        }
                    ],
                    "message": "Business partners retrieved successfully"
                }
            }
        ),
        500: openapi.Response(
            description="SAP integration error",
            examples={
                "application/json": {
                    "success": False,
                    "error": "SAP integration failed",
                    "message": "Unable to connect to SAP system"
                }
            }
        )
    }
)
@api_view(['GET'])
def get_business_partners_list(request):
    """List all business partners (wrapper for Swagger)"""
    return get_business_partner_data(request, card_code=None)


# Wrapper for detail endpoint with Swagger documentation
@swagger_auto_schema(tags=['SAP'], 
    method='get',
    operation_description="Get specific Business Partner by CardCode (CardCode IS required in URL path for this endpoint)",
    operation_summary="Get Business Partner by CardCode",
    manual_parameters=[
        openapi.Parameter(
            'card_code',
            openapi.IN_PATH,
            description="Business Partner Card Code (e.g., BIC00001)",
            type=openapi.TYPE_STRING,
            required=True
        ),
        openapi.Parameter(
            'database',
            openapi.IN_QUERY,
            description="HANA database/schema to query. Accepts Company name values (e.g., 4B-BIO_APP, 4B-ORANG_APP) or company keys (e.g., 4B-BIO, 4B-ORANG). If not provided, falls back to session or first active company.",
            type=openapi.TYPE_STRING,
            required=False
        )
    ],
    responses={
        200: openapi.Response(
            description="Business Partner data retrieved successfully",
            examples={
                "application/json": {
                    "success": True,
                    "data": {
                        "CardCode": "BIC00001",
                        "CardName": "Sample Business Partner",
                        "CardType": "cCustomer",
                        "CurrentAccountBalance": 15000.50
                    },
                    "message": "Business partner data retrieved successfully"
                }
            }
        ),
        404: openapi.Response(
            description="Business partner not found",
            examples={
                "application/json": {
                    "success": False,
                    "error": "Business partner not found",
                    "message": "No business partner found with card code: BIC00001"
                }
            }
        ),
        500: openapi.Response(
            description="SAP integration error",
            examples={
                "application/json": {
                    "success": False,
                    "error": "SAP integration failed",
                    "message": "Unable to connect to SAP system"
                }
            }
        )
    }
)
@api_view(['GET'])
def get_business_partner_detail(request, card_code):
    """Get specific business partner (wrapper for Swagger)"""
    return get_business_partner_data(request, card_code=card_code)


@swagger_auto_schema(tags=['SAP'], 
    method='get',
    operation_description="List all policies from SAP Projects (UDF U_pol)",
    manual_parameters=[
        openapi.Parameter(
            'active',
            openapi.IN_QUERY,
            description="Filter by Active projects (true/false)",
            type=openapi.TYPE_BOOLEAN,
            required=False
        )
    ],
    responses={
        200: openapi.Response(
            description="Policies retrieved successfully",
            examples={
                "application/json": {
                    "success": True,
                    "count": 2,
                    "data": [
                        {
                            "code": "PRJ001",
                            "name": "Example Project",
                            "valid_from": "2024-01-01",
                            "valid_to": "2025-01-01",
                            "active": True,
                            "policy": "POL-123"
                        },
                        {
                            "code": "PRJ002",
                            "name": "Another Project",
                            "valid_from": "2024-02-01",
                            "valid_to": "2025-02-01",
                            "active": False,
                            "policy": "POL-456"
                        }
                    ]
                }
            }
        ),
        500: openapi.Response(
            description="SAP integration error",
            examples={
                "application/json": {
                    "success": False,
                    "error": "SAP integration failed",
                    "message": "Unable to connect to SAP system"
                }
            }
        )
    }
)
@api_view(['GET'])
def list_policies(request):
    """
    API endpoint to list policies from SAP Projects based on UDF `U_pol`.
    Usage: GET /api/sap/policies/
    Optional: ?active=true|false
    """
    try:
        selected_db = request.session.get('selected_db', '4B-BIO')
        sap_client = SAPClient(company_db_key=selected_db)
        policies = sap_client.get_all_policies()

        active_param = request.query_params.get('active')
        if active_param is not None:
            active_val = str(active_param).lower() in ('true', '1', 'yes')
            policies = [p for p in policies if bool(p.get('active')) == active_val]

        return Response({
            "success": True,
            "count": len(policies),
            "data": policies,
            "message": "Policies retrieved successfully"
        }, status=status.HTTP_200_OK)

    except Exception as e:
        return Response({
            "success": False,
            "error": "SAP integration failed",
            "message": str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# --- Database policy listing (secure API) ---
@swagger_auto_schema(tags=['SAP'], 
    method='get',
    operation_description="List policies stored in the database with search and filtering.",
    manual_parameters=[
        openapi.Parameter('search', openapi.IN_QUERY, description="Search code/name/policy", type=openapi.TYPE_STRING),
        openapi.Parameter('active', openapi.IN_QUERY, description="Filter by active true/false", type=openapi.TYPE_BOOLEAN),
        openapi.Parameter('valid_from', openapi.IN_QUERY, description="Filter policies valid on/after this date (YYYY-MM-DD)", type=openapi.TYPE_STRING),
        openapi.Parameter('valid_to', openapi.IN_QUERY, description="Filter policies valid on/before this date (YYYY-MM-DD)", type=openapi.TYPE_STRING),
    ]
)
@api_view(['GET'])
def list_db_policies(request):
    qs = Policy.objects.all().order_by('-updated_at')

    search = request.query_params.get('search')
    if search:
        qs = qs.filter(models.Q(code__icontains=search) | models.Q(name__icontains=search) | models.Q(policy__icontains=search))

    active = request.query_params.get('active')
    if active is not None:
        active_val = str(active).lower() in ('true', '1', 'yes')
        qs = qs.filter(active=active_val)

    vf = request.query_params.get('valid_from')
    if vf:
        qs = qs.filter(valid_from__gte=vf)

    vt = request.query_params.get('valid_to')
    if vt:
        qs = qs.filter(valid_to__lte=vt)

    serializer = PolicySerializer(qs, many=True)
    return Response({
        'success': True,
        'count': len(serializer.data),
        'data': serializer.data,
        'message': 'Policies retrieved from database'
    }, status=status.HTTP_200_OK)


# --- Sync from SAP to DB ---
@swagger_auto_schema(tags=['SAP'], 
    method='post',
    operation_description="Sync policies from SAP Projects (UDF U_pol) into the database.",
    responses={
        200: openapi.Response(description="Sync completed")
    }
)
@api_view(['POST'])
def sync_policies(request):
    selected_db = request.session.get('selected_db', '4B-BIO')
    client = SAPClient(company_db_key=selected_db)
    try:
        rows = client.get_all_policies()
    except Exception as e:
        return Response({
            'success': False,
            'error': 'SAP integration failed',
            'message': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    import datetime
    def parse_date(val):
        if not val:
            return None
        try:
            if isinstance(val, str):
                return datetime.date.fromisoformat(val.split('T')[0])
            if isinstance(val, datetime.datetime):
                return val.date()
            if isinstance(val, datetime.date):
                return val
        except Exception:
            return None
        return None

    created = 0
    updated = 0
    for row in rows:
        obj, is_created = Policy.objects.update_or_create(
            code=row.get('code'),
            defaults={
                'name': row.get('name') or '',
                'policy': row.get('policy') or '',
                'valid_from': parse_date(row.get('valid_from')),
                'valid_to': parse_date(row.get('valid_to')),
                'active': bool(row.get('active'))
            }
        )
        created += 1 if is_created else 0
        updated += 0 if is_created else 1

    return Response({
        'success': True,
        'created': created,
        'updated': updated,
        'message': 'Policies synced from SAP'
    }, status=status.HTTP_200_OK)


# --- Policy listing page (responsive) ---
@ensure_csrf_cookie
def policy_list_page(request):
    """Render a responsive page to list DB policies with a Sync button."""
    return render(request, 'sap_integration/policies.html')

@swagger_auto_schema(tags=['SAP'], 
    method='get',
    operation_description="Sales vs Achievement data",
    manual_parameters=[
        openapi.Parameter('database', openapi.IN_QUERY, description="Database/schema", type=openapi.TYPE_STRING, enum=['4B-BIO-app', '4B-ORANG-app'], default='4B-BIO-app'),
        openapi.Parameter('start_date', openapi.IN_QUERY, description="Start date YYYY-MM-DD", type=openapi.TYPE_STRING),
        openapi.Parameter('end_date', openapi.IN_QUERY, description="End date YYYY-MM-DD", type=openapi.TYPE_STRING),
        openapi.Parameter('territory', openapi.IN_QUERY, description="Territory name", type=openapi.TYPE_STRING),
        openapi.Parameter('emp_id', openapi.IN_QUERY, description="Employee ID", type=openapi.TYPE_INTEGER),
        openapi.Parameter('in_millions', openapi.IN_QUERY, description="Scale numeric values to millions", type=openapi.TYPE_BOOLEAN),
        openapi.Parameter('legacy', openapi.IN_QUERY, description="Include legacy mixed-case keys", type=openapi.TYPE_BOOLEAN),
        openapi.Parameter('sum_all', openapi.IN_QUERY, description="Aggregate totals across territories", type=openapi.TYPE_BOOLEAN),
        openapi.Parameter('group_by', openapi.IN_QUERY, description="Aggregation level: 'month' or 'territory'", type=openapi.TYPE_STRING),
        openapi.Parameter('page', openapi.IN_QUERY, description="Page number (default 1)", type=openapi.TYPE_INTEGER, default=1),
        openapi.Parameter('page_size', openapi.IN_QUERY, description="Items per page (default 10)", type=openapi.TYPE_INTEGER, default=10),
    ],
    responses={
        200: openapi.Response(description="OK"),
        400: openapi.Response(description="Bad Request"),
        500: openapi.Response(description="Server Error"),
    }
)
@api_view(['GET'])
def sales_vs_achievement_api(request):
    try:
        _hana_load_env_file(os.path.join(os.path.dirname(__file__), '.env'))
        _hana_load_env_file(os.path.join(str(settings.BASE_DIR), '.env'))
        _hana_load_env_file(os.path.join(str(Path(settings.BASE_DIR).parent), '.env'))
        _hana_load_env_file(os.path.join(os.getcwd(), '.env'))
    except Exception:
        pass
    cfg = {
        'host': os.environ.get('HANA_HOST') or '',
        'port': os.environ.get('HANA_PORT') or '30015',
        'user': os.environ.get('HANA_USER') or '',
        'schema': os.environ.get('HANA_SCHEMA') or '4B-BIO_APP',
        'encrypt': os.environ.get('HANA_ENCRYPT') or '',
        'ssl_validate': os.environ.get('HANA_SSL_VALIDATE') or '',
    }
    db_param = (request.query_params.get('database') or '').strip()
    if db_param:
        norm = db_param.strip().upper().replace('-APP', '_APP')
        if '4B-BIO' in norm:
            cfg['schema'] = '4B-BIO_APP'
        elif '4B-ORANG' in norm:
            cfg['schema'] = '4B-ORANG_APP'
        else:
            cfg['schema'] = db_param
    else:
        cfg['schema'] = '4B-BIO_APP'
    start_date = (request.query_params.get('start_date') or '').strip()
    end_date = (request.query_params.get('end_date') or '').strip()
    territory = (request.query_params.get('territory') or '').strip()
    in_millions_param = (request.query_params.get('in_millions') or '').strip().lower()
    legacy_param = (request.query_params.get('legacy') or request.query_params.get('include_legacy') or request.query_params.get('compat') or '').strip().lower()
    include_legacy = (legacy_param in ('true','1','yes','y'))
    sum_all_param = (request.query_params.get('sum_all') or '').strip().lower()
    do_sum_all = (sum_all_param in ('true','1','yes','y'))
    emp_id_param = request.query_params.get('emp_id')
    emp_id = None
    if emp_id_param:
        try:
            emp_id = int(emp_id_param)
        except Exception:
            return Response({'success': False, 'error': 'Invalid emp_id'}, status=status.HTTP_400_BAD_REQUEST)
    group_by_param = (request.query_params.get('group_by') or '').strip().lower()
    if group_by_param not in ('emp','territory','month'):
        group_by_param = 'emp'
    try:
        from hdbcli import dbapi
        pwd = os.environ.get('HANA_PASSWORD','')
        kwargs = {'address': cfg['host'], 'port': int(cfg['port']), 'user': cfg['user'] or '', 'password': pwd or ''}
        if str(cfg['encrypt']).strip().lower() in ('true','1','yes'):
            kwargs['encrypt'] = True
            if cfg['ssl_validate']:
                kwargs['sslValidateCertificate'] = (str(cfg['ssl_validate']).strip().lower() in ('true','1','yes'))
        conn = dbapi.connect(**kwargs)
        try:
            if cfg['schema']:
                sch = cfg['schema']
                cur = conn.cursor()
                cur.execute(f'SET SCHEMA "{sch}"')
                cur.close()
            data = sales_vs_achievement(conn, emp_id, territory or None, None, None, start_date or None, end_date or None)
            if in_millions_param in ('true','1','yes','y'):
                scaled = []
                for row in data or []:
                    if isinstance(row, dict):
                        r = dict(row)
                        try:
                            v = r.get('Sales_Target', None)
                            if v is None:
                                v = r.get('SALES_TARGET', None)
                            if v is not None:
                                val = round((float(v) / 1000000.0), 2)
                                r['SALES_TARGET'] = val
                                if include_legacy:
                                    r['Sales_Target'] = r['SALES_TARGET']
                                else:
                                    r.pop('Sales_Target', None)
                        except Exception:
                            pass
                        try:
                            v = r.get('Achievement', None)
                            if v is None:
                                v = r.get('ACHIEVEMENT', None)
                            if v is None:
                                v = r.get('ACCHIVEMENT', None)
                            if v is not None:
                                val2 = round((float(v) / 1000000.0), 2)
                                r['ACCHIVEMENT'] = val2
                                if include_legacy:
                                    r['Achievement'] = r['ACCHIVEMENT']
                                else:
                                    r.pop('Achievement', None)
                        except Exception:
                            pass
                        scaled.append(r)
                    else:
                        scaled.append(row)
                data = scaled
            if group_by_param == 'territory' and not do_sum_all:
                grouped = {}
                for r in (data or []):
                    if isinstance(r, dict):
                        tid = r.get('TERRITORYID')
                        tname = r.get('TERRITORYNAME')
                        k = (tid, tname)
                        if k not in grouped:
                            grouped[k] = {'SALES_TARGET': 0.0, 'ACCHIVEMENT': 0.0, 'TERRITORYID': tid, 'TERRITORYNAME': tname, 'F_REFDATE': r.get('F_REFDATE'), 'T_REFDATE': r.get('T_REFDATE')}
                        st = r.get('SALES_TARGET') or 0.0
                        ac = r.get('ACCHIVEMENT') or 0.0
                        try:
                            grouped[k]['SALES_TARGET'] += float(st)
                        except Exception:
                            pass
                        try:
                            grouped[k]['ACCHIVEMENT'] += float(ac)
                        except Exception:
                            pass
                        f = r.get('F_REFDATE')
                        t = r.get('T_REFDATE')
                        if f and (grouped[k]['F_REFDATE'] is None or str(f) < str(grouped[k]['F_REFDATE'])):
                            grouped[k]['F_REFDATE'] = f
                        if t and (grouped[k]['T_REFDATE'] is None or str(t) > str(grouped[k]['T_REFDATE'])):
                            grouped[k]['T_REFDATE'] = t
                data = []
                for k, g in grouped.items():
                    row = {'TERRITORYID': g['TERRITORYID'] or 0, 'TERRITORYNAME': g['TERRITORYNAME'] or '', 'SALES_TARGET': g['SALES_TARGET'], 'ACCHIVEMENT': g['ACCHIVEMENT'], 'F_REFDATE': g['F_REFDATE'], 'T_REFDATE': g['T_REFDATE']}
                    if include_legacy:
                        row['Sales_Target'] = row['SALES_TARGET']
                        row['Achievement'] = row['ACCHIVEMENT']
                    data.append(row)
            if do_sum_all:
                if group_by_param == 'month':
                    grouped = {}
                    for r in (data or []):
                        if isinstance(r, dict):
                            k = (r.get('F_REFDATE'), r.get('T_REFDATE'))
                            if k not in grouped:
                                grouped[k] = {'SALES_TARGET': 0.0, 'ACCHIVEMENT': 0.0, 'F_REFDATE': k[0], 'T_REFDATE': k[1]}
                            st = r.get('SALES_TARGET') or 0.0
                            ac = r.get('ACCHIVEMENT') or 0.0
                            try:
                                grouped[k]['SALES_TARGET'] += float(st)
                            except Exception:
                                pass
                            try:
                                grouped[k]['ACCHIVEMENT'] += float(ac)
                            except Exception:
                                pass
                    agg = []
                    for k, g in grouped.items():
                        row = {'TERRITORYID': 0, 'TERRITORYNAME': 'All Territories', 'SALES_TARGET': g['SALES_TARGET'], 'ACCHIVEMENT': g['ACCHIVEMENT'], 'F_REFDATE': g['F_REFDATE'], 'T_REFDATE': g['T_REFDATE']}
                        if include_legacy:
                            row['Sales_Target'] = row['SALES_TARGET']
                            row['Achievement'] = row['ACCHIVEMENT']
                        agg.append(row)
                    data = agg
                elif group_by_param == 'territory':
                    grouped = {}
                    for r in (data or []):
                        if isinstance(r, dict):
                            tid = r.get('TERRITORYID')
                            tname = r.get('TERRITORYNAME')
                            k = (tid, tname)
                            if k not in grouped:
                                grouped[k] = {'SALES_TARGET': 0.0, 'ACCHIVEMENT': 0.0, 'TERRITORYID': tid, 'TERRITORYNAME': tname, 'F_REFDATE': r.get('F_REFDATE'), 'T_REFDATE': r.get('T_REFDATE')}
                            st = r.get('SALES_TARGET') or 0.0
                            ac = r.get('ACCHIVEMENT') or 0.0
                            try:
                                grouped[k]['SALES_TARGET'] += float(st)
                            except Exception:
                                pass
                            try:
                                grouped[k]['ACCHIVEMENT'] += float(ac)
                            except Exception:
                                pass
                            f = r.get('F_REFDATE')
                            t = r.get('T_REFDATE')
                            if f and (grouped[k]['F_REFDATE'] is None or str(f) < str(grouped[k]['F_REFDATE'])):
                                grouped[k]['F_REFDATE'] = f
                            if t and (grouped[k]['T_REFDATE'] is None or str(t) > str(grouped[k]['T_REFDATE'])):
                                grouped[k]['T_REFDATE'] = t
                    data = []
                    for k, g in grouped.items():
                        row = {'TERRITORYID': g['TERRITORYID'] or 0, 'TERRITORYNAME': g['TERRITORYNAME'] or '', 'SALES_TARGET': g['SALES_TARGET'], 'ACCHIVEMENT': g['ACCHIVEMENT'], 'F_REFDATE': g['F_REFDATE'], 'T_REFDATE': g['T_REFDATE']}
                        if include_legacy:
                            row['Sales_Target'] = row['SALES_TARGET']
                            row['Achievement'] = row['ACCHIVEMENT']
                        data.append(row)
                else:
                    total_st = 0.0
                    total_ac = 0.0
                    min_f = None
                    max_t = None
                    for r in (data or []):
                        if isinstance(r, dict):
                            st = r.get('SALES_TARGET') or 0.0
                            ac = r.get('ACCHIVEMENT') or 0.0
                            try:
                                total_st += float(st)
                            except Exception:
                                pass
                            try:
                                total_ac += float(ac)
                            except Exception:
                                pass
                            f = r.get('F_REFDATE')
                            t = r.get('T_REFDATE')
                            if f and (min_f is None or str(f) < str(min_f)):
                                min_f = f
                            if t and (max_t is None or str(t) > str(max_t)):
                                max_t = t
                    one = {'TERRITORYID': 0, 'TERRITORYNAME': 'All Territories', 'SALES_TARGET': total_st, 'ACCHIVEMENT': total_ac, 'F_REFDATE': (start_date or min_f), 'T_REFDATE': (end_date or max_t)}
                    if include_legacy:
                        one['Sales_Target'] = one['SALES_TARGET']
                        one['Achievement'] = one['ACCHIVEMENT']
                    data = [one]
            page_param = (request.query_params.get('page') or '1').strip()
            page_size_param = (request.query_params.get('page_size') or '').strip()
            try:
                page_num = int(page_param) if page_param else 1
            except Exception:
                page_num = 1
            default_page_size = 10
            try:
                default_page_size = int(getattr(settings, 'REST_FRAMEWORK', {}).get('PAGE_SIZE', 10) or 10)
            except Exception:
                default_page_size = 10
            try:
                page_size = int(page_size_param) if page_size_param else default_page_size
            except Exception:
                page_size = default_page_size
            paginator = Paginator(list(data or []), page_size)
            try:
                page_obj = paginator.page(page_num)
                paged_rows = list(page_obj.object_list)
            except Exception:
                paged_rows = list(data or [])
                page_obj = None
            pagination = {
                'page': (page_obj.number if page_obj else 1),
                'num_pages': (paginator.num_pages if paginator else 1),
                'has_next': (page_obj.has_next() if page_obj else False),
                'has_prev': (page_obj.has_previous() if page_obj else False),
                'next_page': ((page_obj.next_page_number() if page_obj and page_obj.has_next() else None)),
                'prev_page': ((page_obj.previous_page_number() if page_obj and page_obj.has_previous() else None)),
                'count': (paginator.count if paginator else len(data or [])),
                'page_size': page_size,
            }
            return Response({'success': True, 'count': (paginator.count if paginator else len(data or [])), 'data': paged_rows, 'pagination': pagination}, status=status.HTTP_200_OK)
        finally:
            try:
                conn.close()
            except Exception:
                pass
    except Exception as e:
        return Response({
            'success': False,
            'error': str(e),
            'schema': cfg.get('schema'),
            'host': cfg.get('host'),
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@swagger_auto_schema(tags=['SAP'], 
    method='get',
    operation_description="Sales vs Achievement (Geo Inv) with Region/Zone/Territory hierarchy",
    manual_parameters=[
        openapi.Parameter('database', openapi.IN_QUERY, description="Database/schema", type=openapi.TYPE_STRING, enum=['4B-BIO-app', '4B-ORANG-app'], default='4B-BIO-app'),
        openapi.Parameter('start_date', openapi.IN_QUERY, description="Start date YYYY-MM-DD", type=openapi.TYPE_STRING),
        openapi.Parameter('end_date', openapi.IN_QUERY, description="End date YYYY-MM-DD", type=openapi.TYPE_STRING),
        openapi.Parameter('region', openapi.IN_QUERY, description="Region name", type=openapi.TYPE_STRING),
        openapi.Parameter('zone', openapi.IN_QUERY, description="Zone name", type=openapi.TYPE_STRING),
        openapi.Parameter('territory', openapi.IN_QUERY, description="Territory name", type=openapi.TYPE_STRING),
        openapi.Parameter('emp_id', openapi.IN_QUERY, description="Employee ID (optional)", type=openapi.TYPE_INTEGER),
        openapi.Parameter('group_by_emp', openapi.IN_QUERY, description="Group rows by employee", type=openapi.TYPE_BOOLEAN, default=False),
        openapi.Parameter('in_millions', openapi.IN_QUERY, description="Scale numeric values to millions", type=openapi.TYPE_BOOLEAN),
        openapi.Parameter('page', openapi.IN_QUERY, description="Page number (default 1)", type=openapi.TYPE_INTEGER, default=1),
        openapi.Parameter('page_size', openapi.IN_QUERY, description="Items per page (default 10)", type=openapi.TYPE_INTEGER, default=10),
    ],
    responses={200: openapi.Response(description="OK"), 400: openapi.Response(description="Bad Request"), 500: openapi.Response(description="Server Error")}
)
@api_view(['GET'])
def sales_vs_achievement_geo_inv_api(request):
    try:
        _hana_load_env_file(os.path.join(os.path.dirname(__file__), '.env'))
        _hana_load_env_file(os.path.join(str(settings.BASE_DIR), '.env'))
        _hana_load_env_file(os.path.join(str(Path(settings.BASE_DIR).parent), '.env'))
        _hana_load_env_file(os.path.join(os.getcwd(), '.env'))
    except Exception:
        pass
    cfg = {'host': os.environ.get('HANA_HOST') or '', 'port': os.environ.get('HANA_PORT') or '30015', 'user': os.environ.get('HANA_USER') or '', 'schema': os.environ.get('HANA_SCHEMA') or '4B-BIO_APP', 'encrypt': os.environ.get('HANA_ENCRYPT') or '', 'ssl_validate': os.environ.get('HANA_SSL_VALIDATE') or ''}
    db_param = (request.query_params.get('database') or '').strip()
    if db_param:
        norm = db_param.strip().upper().replace('-APP', '_APP')
        if '4B-BIO' in norm:
            cfg['schema'] = '4B-BIO_APP'
        elif '4B-ORANG' in norm:
            cfg['schema'] = '4B-ORANG_APP'
        else:
            cfg['schema'] = db_param
    else:
        cfg['schema'] = '4B-BIO_APP'
    start_date = (request.query_params.get('start_date') or '').strip()
    end_date = (request.query_params.get('end_date') or '').strip()
    region = (request.query_params.get('region') or '').strip()
    zone = (request.query_params.get('zone') or '').strip()
    territory = (request.query_params.get('territory') or '').strip()
    in_millions_param = (request.query_params.get('in_millions') or '').strip().lower()
    group_by_emp_param = (request.query_params.get('group_by_emp') or '').strip().lower()
    group_by_emp = (group_by_emp_param in ('true','1','yes','y'))
    emp_id_param = request.query_params.get('emp_id')
    emp_id = None
    if emp_id_param:
        try:
            emp_id = int(emp_id_param)
        except Exception:
            return Response({'success': False, 'error': 'Invalid emp_id'}, status=status.HTTP_400_BAD_REQUEST)
    try:
        from hdbcli import dbapi
        pwd = os.environ.get('HANA_PASSWORD','')
        kwargs = {'address': cfg['host'], 'port': int(cfg['port']), 'user': cfg['user'] or '', 'password': pwd or ''}
        if str(cfg['encrypt']).strip().lower() in ('true','1','yes'):
            kwargs['encrypt'] = True
            if cfg['ssl_validate']:
                kwargs['sslValidateCertificate'] = (str(cfg['ssl_validate']).strip().lower() in ('true','1','yes'))
        conn = dbapi.connect(**kwargs)
        try:
            if cfg['schema']:
                sch = cfg['schema']
                cur = conn.cursor()
                cur.execute(f'SET SCHEMA "{sch}"')
                cur.close()
            data = sales_vs_achievement_geo_inv(conn, emp_id=emp_id, region=region or None, zone=zone or None, territory=territory or None, start_date=start_date or None, end_date=end_date or None, group_by_emp=group_by_emp)
            if in_millions_param in ('true','1','yes','y'):
                scaled = []
                for row in data or []:
                    if isinstance(row, dict):
                        r = dict(row)
                        try:
                            v = r.get('Collection_Target')
                            if v is None: v = r.get('COLLECTION_TARGET')
                            if v is None: v = r.get('COLLETION_TARGET')
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
            hierarchy = {}
            for row in (data or []):
                if not isinstance(row, dict):
                    continue
                reg = row.get('Region') or row.get('REGION') or 'Unknown Region'
                zon = row.get('Zone') or row.get('ZONE') or 'Unknown Zone'
                ter = row.get('Territory') or row.get('TERRITORY') or 'Unknown Territory'
                sal = 0.0
                ach = 0.0
                try:
                    v = row.get('Collection_Target')
                    if v is None: v = row.get('COLLECTION_TARGET')
                    if v is None: v = row.get('COLLETION_TARGET')
                    sal = float(v or 0.0)
                except Exception:
                    pass
                try:
                    v = row.get('Collection_Achievement')
                    if v is None: v = row.get('COLLECTION_ACHIEVEMENT')
                    if v is None: v = row.get('DocTotal')
                    ach = float(v or 0.0)
                except Exception:
                    pass
                if reg not in hierarchy:
                    hierarchy[reg] = {'name': reg, 'sales': 0.0, 'achievement': 0.0, 'zones': {}}
                hierarchy[reg]['sales'] += sal
                hierarchy[reg]['achievement'] += ach
                if zon not in hierarchy[reg]['zones']:
                    hierarchy[reg]['zones'][zon] = {'name': zon, 'sales': 0.0, 'achievement': 0.0, 'territories': []}
                hierarchy[reg]['zones'][zon]['sales'] += sal
                hierarchy[reg]['zones'][zon]['achievement'] += ach
                territory_item = {'name': ter, 'sales': sal, 'achievement': ach}
                if group_by_emp:
                    territory_item['employee_name'] = row.get('EmployeeName','')
                hierarchy[reg]['zones'][zon]['territories'].append(territory_item)
            final_list = []
            for r_name in sorted(hierarchy.keys()):
                r_data = hierarchy[r_name]
                zones_list = []
                for z_name in sorted(r_data['zones'].keys()):
                    z_data = r_data['zones'][z_name]
                    z_data['territories'] = sorted(z_data['territories'], key=lambda x: x['name'])
                    zones_list.append(z_data)
                r_data['zones'] = zones_list
                final_list.append(r_data)
            for r in final_list:
                r['sales'] = round(r['sales'], 2)
                r['achievement'] = round(r['achievement'], 2)
                for z in r['zones']:
                    z['sales'] = round(z['sales'], 2)
                    z['achievement'] = round(z['achievement'], 2)
            page_param = (request.query_params.get('page') or '1').strip()
            page_size_param = (request.query_params.get('page_size') or '').strip()
            try:
                page_num = int(page_param) if page_param else 1
            except Exception:
                page_num = 1
            default_page_size = 10
            try:
                default_page_size = int(getattr(settings, 'REST_FRAMEWORK', {}).get('PAGE_SIZE', 10) or 10)
            except Exception:
                default_page_size = 10
            try:
                page_size = int(page_size_param) if page_size_param else default_page_size
            except Exception:
                page_size = default_page_size
            paginator = Paginator(list(final_list or []), page_size)
            try:
                page_obj = paginator.page(page_num)
                paged_rows = list(page_obj.object_list)
            except Exception:
                paged_rows = list(final_list or [])
                page_obj = None
            pagination = {'page': (page_obj.number if page_obj else 1), 'num_pages': (paginator.num_pages if paginator else 1), 'has_next': (page_obj.has_next() if page_obj else False), 'has_prev': (page_obj.has_previous() if page_obj else False), 'next_page': ((page_obj.next_page_number() if page_obj and page_obj.has_next() else None)), 'prev_page': ((page_obj.previous_page_number() if page_obj and page_obj.has_previous() else None)), 'count': (paginator.count if paginator else len(final_list or [])), 'page_size': page_size}
            return Response({'success': True, 'count': (paginator.count if paginator else len(final_list or [])), 'data': paged_rows, 'pagination': pagination}, status=status.HTTP_200_OK)
        finally:
            try:
                conn.close()
            except Exception:
                pass
    except Exception as e:
        return Response({'success': False, 'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@swagger_auto_schema(tags=['SAP'], 
    method='get',
    operation_description="Sales vs Achievement (Territory) hierarchy by Region/Zone/Territory",
    manual_parameters=[
        openapi.Parameter('database', openapi.IN_QUERY, description="Database/schema", type=openapi.TYPE_STRING, enum=['4B-BIO-app', '4B-ORANG-app'], default='4B-BIO-app'),
        openapi.Parameter('start_date', openapi.IN_QUERY, description="Start date YYYY-MM-DD", type=openapi.TYPE_STRING),
        openapi.Parameter('end_date', openapi.IN_QUERY, description="End date YYYY-MM-DD", type=openapi.TYPE_STRING),
        openapi.Parameter('region', openapi.IN_QUERY, description="Region name", type=openapi.TYPE_STRING),
        openapi.Parameter('zone', openapi.IN_QUERY, description="Zone name", type=openapi.TYPE_STRING),
        openapi.Parameter('territory', openapi.IN_QUERY, description="Territory name", type=openapi.TYPE_STRING),
        openapi.Parameter('in_millions', openapi.IN_QUERY, description="Scale numeric values to millions", type=openapi.TYPE_BOOLEAN),
        openapi.Parameter('page', openapi.IN_QUERY, description="Page number (default 1)", type=openapi.TYPE_INTEGER, default=1),
        openapi.Parameter('page_size', openapi.IN_QUERY, description="Items per page (default 10)", type=openapi.TYPE_INTEGER, default=10),
    ],
    responses={200: openapi.Response(description="OK"), 400: openapi.Response(description="Bad Request"), 500: openapi.Response(description="Server Error")}
)
@api_view(['GET'])
def sales_vs_achievement_territory_api(request):
    try:
        _hana_load_env_file(os.path.join(os.path.dirname(__file__), '.env'))
        _hana_load_env_file(os.path.join(str(settings.BASE_DIR), '.env'))
        _hana_load_env_file(os.path.join(str(Path(settings.BASE_DIR).parent), '.env'))
        _hana_load_env_file(os.path.join(os.getcwd(), '.env'))
    except Exception:
        pass
    cfg = {'host': os.environ.get('HANA_HOST') or '', 'port': os.environ.get('HANA_PORT') or '30015', 'user': os.environ.get('HANA_USER') or '', 'schema': os.environ.get('HANA_SCHEMA') or '4B-BIO_APP', 'encrypt': os.environ.get('HANA_ENCRYPT') or '', 'ssl_validate': os.environ.get('HANA_SSL_VALIDATE') or ''}
    db_param = (request.query_params.get('database') or '').strip()
    if db_param:
        norm = db_param.strip().upper().replace('-APP', '_APP')
        if '4B-BIO' in norm:
            cfg['schema'] = '4B-BIO_APP'
        elif '4B-ORANG' in norm:
            cfg['schema'] = '4B-ORANG_APP'
        else:
            cfg['schema'] = db_param
    else:
        cfg['schema'] = '4B-BIO_APP'
    start_date = (request.query_params.get('start_date') or '').strip()
    end_date = (request.query_params.get('end_date') or '').strip()
    region = (request.query_params.get('region') or '').strip()
    zone = (request.query_params.get('zone') or '').strip()
    territory = (request.query_params.get('territory') or '').strip()
    in_millions_param = (request.query_params.get('in_millions') or '').strip().lower()
    try:
        from hdbcli import dbapi
        pwd = os.environ.get('HANA_PASSWORD','')
        kwargs = {'address': cfg['host'], 'port': int(cfg['port']), 'user': cfg['user'] or '', 'password': pwd or ''}
        if str(cfg['encrypt']).strip().lower() in ('true','1','yes'):
            kwargs['encrypt'] = True
            if cfg['ssl_validate']:
                kwargs['sslValidateCertificate'] = (str(cfg['ssl_validate']).strip().lower() in ('true','1','yes'))
        conn = dbapi.connect(**kwargs)
        try:
            if cfg['schema']:
                sch = cfg['schema']
                cur = conn.cursor()
                cur.execute(f'SET SCHEMA "{sch}"')
                cur.close()
            data = sales_vs_achievement_geo_inv(conn, emp_id=None, region=region or None, zone=zone or None, territory=territory or None, start_date=start_date or None, end_date=end_date or None, group_by_emp=False)
            if in_millions_param in ('true','1','yes','y'):
                scaled = []
                for row in data or []:
                    if isinstance(row, dict):
                        r = dict(row)
                        try:
                            v = r.get('Collection_Target')
                            if v is None: v = r.get('COLLECTION_TARGET')
                            if v is None: v = r.get('COLLETION_TARGET')
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
                        r.pop('EmployeeName', None)
                        scaled.append(r)
                    else:
                        scaled.append(row)
                data = scaled
            hierarchy = {}
            total_sales = 0.0
            total_achievement = 0.0
            for row in (data or []):
                if not isinstance(row, dict):
                    continue
                reg = row.get('Region') or row.get('REGION') or 'Unknown Region'
                zon = row.get('Zone') or row.get('ZONE') or 'Unknown Zone'
                ter = row.get('Territory') or row.get('TERRITORY') or 'Unknown Territory'
                sal = 0.0
                ach = 0.0
                try:
                    v = row.get('Collection_Target')
                    if v is None: v = row.get('COLLECTION_TARGET')
                    if v is None: v = row.get('COLLETION_TARGET')
                    sal = float(v or 0.0)
                except Exception:
                    pass
                try:
                    v = row.get('Collection_Achievement')
                    if v is None: v = row.get('COLLECTION_ACHIEVEMENT')
                    if v is None: v = row.get('DocTotal')
                    ach = float(v or 0.0)
                except Exception:
                    pass
                total_sales += sal
                total_achievement += ach
                if reg not in hierarchy:
                    hierarchy[reg] = {'name': reg, 'sales': 0.0, 'achievement': 0.0, 'zones': {}}
                hierarchy[reg]['sales'] += sal
                hierarchy[reg]['achievement'] += ach
                if zon not in hierarchy[reg]['zones']:
                    hierarchy[reg]['zones'][zon] = {'name': zon, 'sales': 0.0, 'achievement': 0.0, 'territories': []}
                hierarchy[reg]['zones'][zon]['sales'] += sal
                hierarchy[reg]['zones'][zon]['achievement'] += ach
                hierarchy[reg]['zones'][zon]['territories'].append({'name': ter, 'sales': sal, 'achievement': ach})
            final_list = []
            for r_name in sorted(hierarchy.keys()):
                r_data = hierarchy[r_name]
                zones_list = []
                for z_name in sorted(r_data['zones'].keys()):
                    z_data = r_data['zones'][z_name]
                    z_data['territories'] = sorted(z_data['territories'], key=lambda x: x['name'])
                    zones_list.append(z_data)
                r_data['zones'] = zones_list
                final_list.append(r_data)
            for r in final_list:
                r['sales'] = round(r['sales'], 2)
                r['achievement'] = round(r['achievement'], 2)
                for z in r['zones']:
                    z['sales'] = round(z['sales'], 2)
                    z['achievement'] = round(z['achievement'], 2)
            page_param = (request.query_params.get('page') or '1').strip()
            page_size_param = (request.query_params.get('page_size') or '').strip()
            try:
                page_num = int(page_param) if page_param else 1
            except Exception:
                page_num = 1
            default_page_size = 10
            try:
                default_page_size = int(getattr(settings, 'REST_FRAMEWORK', {}).get('PAGE_SIZE', 10) or 10)
            except Exception:
                default_page_size = 10
            try:
                page_size = int(page_size_param) if page_size_param else default_page_size
            except Exception:
                page_size = default_page_size
            paginator = Paginator(list(final_list or []), page_size)
            try:
                page_obj = paginator.page(page_num)
                paged_rows = list(page_obj.object_list)
            except Exception:
                paged_rows = list(final_list or [])
                page_obj = None
            pagination = {'page': (page_obj.number if page_obj else 1), 'num_pages': (paginator.num_pages if paginator else 1), 'has_next': (page_obj.has_next() if page_obj else False), 'has_prev': (page_obj.has_previous() if page_obj else False), 'next_page': ((page_obj.next_page_number() if page_obj and page_obj.has_next() else None)), 'prev_page': ((page_obj.previous_page_number() if page_obj and page_obj.has_previous() else None)), 'count': (paginator.count if paginator else len(final_list or [])), 'page_size': page_size}
            return Response({
                'success': True,
                'count': (paginator.count if paginator else len(final_list or [])),
                'data': paged_rows,
                'pagination': pagination,
                'totals': {
                    'sales': round(total_sales, 2),
                    'achievement': round(total_achievement, 2),
                },
            }, status=status.HTTP_200_OK)
        finally:
            try:
                conn.close()
            except Exception:
                pass
    except Exception as e:
        return Response({'success': False, 'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
@swagger_auto_schema(tags=['SAP'], 
    method='get',
    operation_description="Sales vs Achievement grouped by employee and territory",
    manual_parameters=[
        openapi.Parameter('database', openapi.IN_QUERY, description="Database/schema", type=openapi.TYPE_STRING, enum=['4B-BIO-app', '4B-ORANG-app'], default='4B-BIO-app'),
        openapi.Parameter('start_date', openapi.IN_QUERY, description="Start date YYYY-MM-DD", type=openapi.TYPE_STRING),
        openapi.Parameter('end_date', openapi.IN_QUERY, description="End date YYYY-MM-DD", type=openapi.TYPE_STRING),
        openapi.Parameter('territory', openapi.IN_QUERY, description="Territory name", type=openapi.TYPE_STRING),
        openapi.Parameter('emp_id', openapi.IN_QUERY, description="Employee ID (optional to filter)", type=openapi.TYPE_INTEGER),
        openapi.Parameter('in_millions', openapi.IN_QUERY, description="Scale numeric values to millions", type=openapi.TYPE_BOOLEAN),
        openapi.Parameter('legacy', openapi.IN_QUERY, description="Include legacy mixed-case keys", type=openapi.TYPE_BOOLEAN),
        openapi.Parameter('group_by', openapi.IN_QUERY, description="Aggregation level: use 'emp' to sum per EMPID", type=openapi.TYPE_STRING, default='emp'),
        openapi.Parameter('page', openapi.IN_QUERY, description="Page number (default 1)", type=openapi.TYPE_INTEGER, default=1),
        openapi.Parameter('page_size', openapi.IN_QUERY, description="Items per page (default 10)", type=openapi.TYPE_INTEGER, default=10),
    ],
    responses={
        200: openapi.Response(description="OK"),
        400: openapi.Response(description="Bad Request"),
        500: openapi.Response(description="Server Error"),
    }
)
@api_view(['GET'])
def sales_vs_achievement_by_emp_api(request):
    try:
        _hana_load_env_file(os.path.join(os.path.dirname(__file__), '.env'))
        _hana_load_env_file(os.path.join(str(settings.BASE_DIR), '.env'))
        _hana_load_env_file(os.path.join(str(Path(settings.BASE_DIR).parent), '.env'))
        _hana_load_env_file(os.path.join(os.getcwd(), '.env'))
    except Exception:
        pass
    cfg = {
        'host': os.environ.get('HANA_HOST') or '',
        'port': os.environ.get('HANA_PORT') or '30015',
        'user': os.environ.get('HANA_USER') or '',
        'schema': os.environ.get('HANA_SCHEMA') or '4B-BIO_APP',
        'encrypt': os.environ.get('HANA_ENCRYPT') or '',
        'ssl_validate': os.environ.get('HANA_SSL_VALIDATE') or '',
    }
    db_param = (request.query_params.get('database') or '').strip()
    if db_param:
        norm = db_param.strip().upper().replace('-APP', '_APP')
        if '4B-BIO' in norm:
            cfg['schema'] = '4B-BIO_APP'
        elif '4B-ORANG' in norm:
            cfg['schema'] = '4B-ORANG_APP'
        else:
            cfg['schema'] = db_param
    else:
        cfg['schema'] = '4B-BIO_APP'
    start_date = (request.query_params.get('start_date') or '').strip()
    end_date = (request.query_params.get('end_date') or '').strip()
    territory = (request.query_params.get('territory') or '').strip()
    in_millions_param = (request.query_params.get('in_millions') or '').strip().lower()
    legacy_param = (request.query_params.get('legacy') or request.query_params.get('include_legacy') or request.query_params.get('compat') or '').strip().lower()
    include_legacy = (legacy_param in ('true','1','yes','y'))
    group_by_param = (request.query_params.get('group_by') or '').strip().lower()
    emp_id_param = request.query_params.get('emp_id')
    emp_id = None
    if emp_id_param:
        try:
            emp_id = int(emp_id_param)
        except Exception:
            return Response({'success': False, 'error': 'Invalid emp_id'}, status=status.HTTP_400_BAD_REQUEST)
    try:
        from hdbcli import dbapi
        pwd = os.environ.get('HANA_PASSWORD','')
        kwargs = {'address': cfg['host'], 'port': int(cfg['port']), 'user': cfg['user'] or '', 'password': pwd or ''}
        if str(cfg['encrypt']).strip().lower() in ('true','1','yes'):
            kwargs['encrypt'] = True
            if cfg['ssl_validate']:
                kwargs['sslValidateCertificate'] = (str(cfg['ssl_validate']).strip().lower() in ('true','1','yes'))
        conn = dbapi.connect(**kwargs)
        try:
            if cfg['schema']:
                sch = cfg['schema']
                cur = conn.cursor()
                cur.execute(f'SET SCHEMA "{sch}"')
                cur.close()
            from .hana_connect import sales_vs_achievement_by_emp
            data = sales_vs_achievement_by_emp(conn, emp_id, territory or None, None, None, start_date or None, end_date or None)
            if in_millions_param in ('true','1','yes','y'):
                scaled = []
                for row in data or []:
                    if isinstance(row, dict):
                        r = dict(row)
                        try:
                            v = r.get('Sales_Target', None)
                            if v is None:
                                v = r.get('SALES_TARGET', None)
                            if v is not None:
                                r['SALES_TARGET'] = round((float(v) / 1000000.0), 2)
                                if include_legacy:
                                    r['Sales_Target'] = r['SALES_TARGET']
                                else:
                                    r.pop('Sales_Target', None)
                        except Exception:
                            pass
                        try:
                            v = r.get('Achievement', None)
                            if v is None:
                                v = r.get('ACHIEVEMENT', None)
                            if v is None:
                                v = r.get('ACCHIVEMENT', None)
                            if v is not None:
                                r['ACCHIVEMENT'] = round((float(v) / 1000000.0), 2)
                                if include_legacy:
                                    r['Achievement'] = r['ACCHIVEMENT']
                                else:
                                    r.pop('Achievement', None)
                        except Exception:
                            pass
                        scaled.append(r)
                    else:
                        scaled.append(row)
                data = scaled
            if group_by_param == 'emp':
                grouped = {}
                for r in (data or []):
                    if isinstance(r, dict):
                        eid = r.get('EMPID')
                        if eid is None:
                            continue
                        if eid not in grouped:
                            grouped[eid] = {
                                'EMPID': eid,
                                'SALES_TARGET': 0.0,
                                'ACCHIVEMENT': 0.0,
                                'TERRITORYID': 0,
                                'TERRITORYNAME': 'All Territories',
                                'F_REFDATE': r.get('F_REFDATE'),
                                'T_REFDATE': r.get('T_REFDATE'),
                            }
                        st = r.get('SALES_TARGET') or 0.0
                        ac = r.get('ACCHIVEMENT') or 0.0
                        try:
                            grouped[eid]['SALES_TARGET'] += float(st)
                        except Exception:
                            pass
                        try:
                            grouped[eid]['ACCHIVEMENT'] += float(ac)
                        except Exception:
                            pass
                        f = r.get('F_REFDATE')
                        t = r.get('T_REFDATE')
                        if f and (grouped[eid]['F_REFDATE'] is None or str(f) < str(grouped[eid]['F_REFDATE'])):
                            grouped[eid]['F_REFDATE'] = f
                        if t and (grouped[eid]['T_REFDATE'] is None or str(t) > str(grouped[eid]['T_REFDATE'])):
                            grouped[eid]['T_REFDATE'] = t
                agg = []
                for _, g in grouped.items():
                    row = {
                        'EMPID': g['EMPID'],
                        'TERRITORYID': g['TERRITORYID'],
                        'TERRITORYNAME': g['TERRITORYNAME'],
                        'SALES_TARGET': g['SALES_TARGET'],
                        'ACCHIVEMENT': g['ACCHIVEMENT'],
                        'F_REFDATE': g['F_REFDATE'],
                        'T_REFDATE': g['T_REFDATE'],
                    }
                    if include_legacy:
                        row['Sales_Target'] = row['SALES_TARGET']
                        row['Achievement'] = row['ACCHIVEMENT']
                    agg.append(row)
                data = agg
            page_param = (request.query_params.get('page') or '1').strip()
            page_size_param = (request.query_params.get('page_size') or '').strip()
            try:
                page_num = int(page_param) if page_param else 1
            except Exception:
                page_num = 1
            default_page_size = 10
            try:
                default_page_size = int(getattr(settings, 'REST_FRAMEWORK', {}).get('PAGE_SIZE', 10) or 10)
            except Exception:
                default_page_size = 10
            try:
                page_size = int(page_size_param) if page_size_param else default_page_size
            except Exception:
                page_size = default_page_size
            paginator = Paginator(list(data or []), page_size)
            try:
                page_obj = paginator.page(page_num)
                paged_rows = list(page_obj.object_list)
            except Exception:
                paged_rows = list(data or [])
                page_obj = None
            pagination = {
                'page': (page_obj.number if page_obj else 1),
                'num_pages': (paginator.num_pages if paginator else 1),
                'has_next': (page_obj.has_next() if page_obj else False),
                'has_prev': (page_obj.has_previous() if page_obj else False),
                'next_page': ((page_obj.next_page_number() if page_obj and page_obj.has_next() else None)),
                'prev_page': ((page_obj.previous_page_number() if page_obj and page_obj.has_previous() else None)),
                'count': (paginator.count if paginator else len(data or [])),
                'page_size': page_size,
            }
            return Response({'success': True, 'count': (paginator.count if paginator else len(data or [])), 'data': paged_rows, 'pagination': pagination}, status=status.HTTP_200_OK)
        finally:
            try:
                conn.close()
            except Exception:
                pass
    except Exception as e:
        return Response({'success': False, 'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@swagger_auto_schema(tags=['SAP'], 
    method='get',
    operation_description="Territory summary data",
    manual_parameters=[
        openapi.Parameter('database', openapi.IN_QUERY, description="Database/schema", type=openapi.TYPE_STRING, enum=['4B-BIO-app', '4B-ORANG-app'], default='4B-BIO-app'),
        openapi.Parameter('start_date', openapi.IN_QUERY, description="Start date YYYY-MM-DD", type=openapi.TYPE_STRING),
        openapi.Parameter('end_date', openapi.IN_QUERY, description="End date YYYY-MM-DD", type=openapi.TYPE_STRING),
        openapi.Parameter('territory', openapi.IN_QUERY, description="Territory name", type=openapi.TYPE_STRING),
        openapi.Parameter('emp_id', openapi.IN_QUERY, description="Employee ID", type=openapi.TYPE_INTEGER),
        openapi.Parameter('sum_all', openapi.IN_QUERY, description="Aggregate totals across territories", type=openapi.TYPE_BOOLEAN),
        openapi.Parameter('group_by', openapi.IN_QUERY, description="Aggregation level: 'month' or 'territory'", type=openapi.TYPE_STRING, default='territory'),
    ],
    responses={200: openapi.Response(description="OK"), 400: openapi.Response(description="Bad Request"), 500: openapi.Response(description="Server Error")}
)
@api_view(['GET'])
def territory_summary_api(request):
    try:
        _hana_load_env_file(os.path.join(os.path.dirname(__file__), '.env'))
        _hana_load_env_file(os.path.join(str(settings.BASE_DIR), '.env'))
        _hana_load_env_file(os.path.join(str(Path(settings.BASE_DIR).parent), '.env'))
        _hana_load_env_file(os.path.join(os.getcwd(), '.env'))
    except Exception:
        pass
    cfg = {
        'host': os.environ.get('HANA_HOST') or '',
        'port': os.environ.get('HANA_PORT') or '30015',
        'user': os.environ.get('HANA_USER') or '',
        'schema': os.environ.get('HANA_SCHEMA') or '4B-BIO_APP',
        'encrypt': os.environ.get('HANA_ENCRYPT') or '',
        'ssl_validate': os.environ.get('HANA_SSL_VALIDATE') or '',
    }
    db_param = (request.query_params.get('database') or '').strip()
    if db_param:
        norm = db_param.strip().upper().replace('-APP', '_APP')
        if '4B-BIO' in norm:
            cfg['schema'] = '4B-BIO_APP'
        elif '4B-ORANG' in norm:
            cfg['schema'] = '4B-ORANG_APP'
        else:
            cfg['schema'] = db_param
    else:
        cfg['schema'] = '4B-BIO_APP'
    start_date = (request.query_params.get('start_date') or '').strip()
    end_date = (request.query_params.get('end_date') or '').strip()
    territory = (request.query_params.get('territory') or '').strip()
    emp_id_param = request.query_params.get('emp_id')
    sum_all_param = (request.query_params.get('sum_all') or '').strip().lower()
    group_by_param = (request.query_params.get('group_by') or 'territory').strip().lower()
    do_sum_all = (sum_all_param in ('true','1','yes','y'))
    emp_id = None
    if emp_id_param:
        try:
            emp_id = int(emp_id_param)
        except Exception:
            return Response({'success': False, 'error': 'Invalid emp_id'}, status=status.HTTP_400_BAD_REQUEST)
    try:
        from hdbcli import dbapi
        pwd = os.environ.get('HANA_PASSWORD','')
        kwargs = {'address': cfg['host'], 'port': int(cfg['port']), 'user': cfg['user'] or '', 'password': pwd or ''}
        if str(cfg['encrypt']).strip().lower() in ('true','1','yes'):
            kwargs['encrypt'] = True
            if cfg['ssl_validate']:
                kwargs['sslValidateCertificate'] = (str(cfg['ssl_validate']).strip().lower() in ('true','1','yes'))
        conn = dbapi.connect(**kwargs)
        try:
            if cfg['schema']:
                sch = cfg['schema']
                cur = conn.cursor()
                cur.execute(f'SET SCHEMA "{sch}"')
                cur.close()
            data = territory_summary(conn, emp_id, territory or None, None, None, start_date or None, end_date or None)
            if group_by_param == 'territory' and not do_sum_all:
                grouped = {}
                for r in (data or []):
                    if isinstance(r, dict):
                        tid = r.get('TERRITORYID') or r.get('TerritoryId') or r.get('territoryid') or r.get('territoryId')
                        tname = r.get('TERRITORYNAME') or r.get('TerritoryName') or r.get('DESCRIPT') or r.get('descript')
                        k = (tid, tname)
                        if k not in grouped:
                            grouped[k] = {'COLLETION_TARGET': 0.0, 'DOCTOTAL': 0.0, 'TERRITORYID': tid, 'TERRITORYNAME': tname, 'F_REFDATE': r.get('F_REFDATE'), 'T_REFDATE': r.get('T_REFDATE')}
                        st = r.get('COLLETION_TARGET') or r.get('COLLECTION_TARGET') or r.get('colletion_Target') or r.get('colletion_target') or 0.0
                        ac = r.get('DOCTOTAL') or r.get('DocTotal') or 0.0
                        try:
                            grouped[k]['COLLETION_TARGET'] += float(st)
                        except Exception:
                            pass
                        try:
                            grouped[k]['DOCTOTAL'] += float(ac)
                        except Exception:
                            pass
                        f = r.get('F_REFDATE')
                        t = r.get('T_REFDATE')
                        if f and (grouped[k]['F_REFDATE'] is None or str(f) < str(grouped[k]['F_REFDATE'])):
                            grouped[k]['F_REFDATE'] = f
                        if t and (grouped[k]['T_REFDATE'] is None or str(t) > str(grouped[k]['T_REFDATE'])):
                            grouped[k]['T_REFDATE'] = t
                data = []
                for k, g in grouped.items():
                    row = {'TERRITORYID': g['TERRITORYID'] or 0, 'TERRITORYNAME': g['TERRITORYNAME'] or '', 'COLLETION_TARGET': g['COLLETION_TARGET'], 'DOCTOTAL': g['DOCTOTAL'], 'F_REFDATE': g['F_REFDATE'], 'T_REFDATE': g['T_REFDATE']}
                    data.append(row)
            if do_sum_all:
                if group_by_param == 'month':
                    grouped = {}
                    for r in (data or []):
                        if isinstance(r, dict):
                            k = (r.get('F_REFDATE'), r.get('T_REFDATE'))
                            if k not in grouped:
                                grouped[k] = {'COLLETION_TARGET': 0.0, 'DOCTOTAL': 0.0, 'F_REFDATE': k[0], 'T_REFDATE': k[1]}
                            st = r.get('COLLETION_TARGET') or r.get('COLLECTION_TARGET') or r.get('colletion_Target') or r.get('colletion_target') or 0.0
                            ac = r.get('DOCTOTAL') or r.get('DocTotal') or 0.0
                            try:
                                grouped[k]['COLLETION_TARGET'] += float(st)
                            except Exception:
                                pass
                            try:
                                grouped[k]['DOCTOTAL'] += float(ac)
                            except Exception:
                                pass
                    agg = []
                    for k, g in grouped.items():
                        row = {'TERRITORYID': 0, 'TERRITORYNAME': 'All Territories', 'COLLETION_TARGET': g['COLLETION_TARGET'], 'DOCTOTAL': g['DOCTOTAL'], 'F_REFDATE': g['F_REFDATE'], 'T_REFDATE': g['T_REFDATE']}
                        agg.append(row)
                    data = agg
                elif group_by_param == 'territory':
                    grouped = {}
                    for r in (data or []):
                        if isinstance(r, dict):
                            tid = r.get('TERRITORYID') or r.get('TerritoryId') or r.get('territoryid') or r.get('territoryId')
                            tname = r.get('TERRITORYNAME') or r.get('TerritoryName') or r.get('DESCRIPT') or r.get('descript')
                            k = (tid, tname)
                            if k not in grouped:
                                grouped[k] = {'COLLETION_TARGET': 0.0, 'DOCTOTAL': 0.0, 'TERRITORYID': tid, 'TERRITORYNAME': tname, 'F_REFDATE': r.get('F_REFDATE'), 'T_REFDATE': r.get('T_REFDATE')}
                            st = r.get('COLLETION_TARGET') or r.get('COLLECTION_TARGET') or r.get('colletion_Target') or r.get('colletion_target') or 0.0
                            ac = r.get('DOCTOTAL') or r.get('DocTotal') or 0.0
                            try:
                                grouped[k]['COLLETION_TARGET'] += float(st)
                            except Exception:
                                pass
                            try:
                                grouped[k]['DOCTOTAL'] += float(ac)
                            except Exception:
                                pass
                            f = r.get('F_REFDATE')
                            t = r.get('T_REFDATE')
                            if f and (grouped[k]['F_REFDATE'] is None or str(f) < str(grouped[k]['F_REFDATE'])):
                                grouped[k]['F_REFDATE'] = f
                            if t and (grouped[k]['T_REFDATE'] is None or str(t) > str(grouped[k]['T_REFDATE'])):
                                grouped[k]['T_REFDATE'] = t
                    data = []
                    for k, g in grouped.items():
                        row = {'TERRITORYID': g['TERRITORYID'] or 0, 'TERRITORYNAME': g['TERRITORYNAME'] or '', 'COLLETION_TARGET': g['COLLETION_TARGET'], 'DOCTOTAL': g['DOCTOTAL'], 'F_REFDATE': g['F_REFDATE'], 'T_REFDATE': g['T_REFDATE']}
                        data.append(row)
                else:
                    total_st = 0.0
                    total_ac = 0.0
                    min_f = None
                    max_t = None
                    for r in (data or []):
                        if isinstance(r, dict):
                            st = r.get('COLLETION_TARGET') or r.get('COLLECTION_TARGET') or r.get('colletion_Target') or r.get('colletion_target') or 0.0
                            ac = r.get('DOCTOTAL') or r.get('DocTotal') or 0.0
                            try:
                                total_st += float(st)
                            except Exception:
                                pass
                            try:
                                total_ac += float(ac)
                            except Exception:
                                pass
                            f = r.get('F_REFDATE')
                            t = r.get('T_REFDATE')
                            if f and (min_f is None or str(f) < str(min_f)):
                                min_f = f
                            if t and (max_t is None or str(t) > str(max_t)):
                                max_t = t
                    one = {'TERRITORYID': 0, 'TERRITORYNAME': 'All Territories', 'COLLETION_TARGET': total_st, 'DOCTOTAL': total_ac, 'F_REFDATE': (start_date or min_f), 'T_REFDATE': (end_date or max_t)}
                    data = [one]
            return Response({'success': True, 'count': len(data or []), 'data': data}, status=status.HTTP_200_OK)
        finally:
            try:
                conn.close()
            except Exception:
                pass
    except Exception as e:
        return Response({'success': False, 'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@swagger_auto_schema(tags=['SAP'], 
    method='get',
    operation_description="Products catalog with images based on database. Supports search and item group filters.",
    manual_parameters=[
        openapi.Parameter('database', openapi.IN_QUERY, description="Database name (e.g., 4B-BIO_APP, 4B-ORANG_APP). Uses default from env if not provided.", type=openapi.TYPE_STRING, required=False),
        openapi.Parameter('search', openapi.IN_QUERY, description="Search ItemCode, ItemName, GenericName, or BrandName", type=openapi.TYPE_STRING, required=False),
        openapi.Parameter('item_group', openapi.IN_QUERY, description="Filter by item group code", type=openapi.TYPE_STRING, required=False),
        openapi.Parameter('page', openapi.IN_QUERY, description="Page number", type=openapi.TYPE_INTEGER, required=False),
        openapi.Parameter('page_size', openapi.IN_QUERY, description="Items per page", type=openapi.TYPE_INTEGER, required=False),
    ],
    responses={200: openapi.Response(description="OK"), 500: openapi.Response(description="Server Error")}
)
@api_view(['GET'])
def products_catalog_api(request):
    try:
        _hana_load_env_file(os.path.join(os.path.dirname(__file__), '.env'))
        _hana_load_env_file(os.path.join(str(settings.BASE_DIR), '.env'))
        _hana_load_env_file(os.path.join(str(Path(settings.BASE_DIR).parent), '.env'))
        _hana_load_env_file(os.path.join(os.getcwd(), '.env'))
    except Exception:
        pass
    
    # Get database parameter from query string
    db_name = request.GET.get('database', os.environ.get('HANA_SCHEMA') or '')
    search = (request.GET.get('search') or '').strip() or None
    item_group = (request.GET.get('item_group') or '').strip() or None
    page_param = (request.GET.get('page') or '1').strip()
    page_size_param = (request.GET.get('page_size') or '').strip()
    
    try:
        page_num = int(page_param) if page_param else 1
    except Exception:
        page_num = 1
    default_page_size = 50
    try:
        default_page_size = int(getattr(settings, 'REST_FRAMEWORK', {}).get('PAGE_SIZE', 50) or 50)
    except Exception:
        default_page_size = 50
    try:
        page_size = int(page_size_param) if page_size_param else default_page_size
    except Exception:
        page_size = default_page_size
    
    cfg = {
        'host': os.environ.get('HANA_HOST') or '',
        'port': os.environ.get('HANA_PORT') or '30015',
        'user': os.environ.get('HANA_USER') or '',
        'schema': db_name,  # Use database parameter or default from env
        'encrypt': os.environ.get('HANA_ENCRYPT') or '',
        'ssl_validate': os.environ.get('HANA_SSL_VALIDATE') or '',
    }
    try:
        from hdbcli import dbapi
        pwd = os.environ.get('HANA_PASSWORD','')
        kwargs = {'address': cfg['host'], 'port': int(cfg['port']), 'user': cfg['user'] or '', 'password': pwd or ''}
        if str(cfg['encrypt']).strip().lower() in ('true','1','yes'):
            kwargs['encrypt'] = True
            if cfg['ssl_validate']:
                kwargs['sslValidateCertificate'] = (str(cfg['ssl_validate']).strip().lower() in ('true','1','yes'))
        conn = dbapi.connect(**kwargs)
        try:
            if cfg['schema']:
                sch = cfg['schema']
                cur = conn.cursor()
                cur.execute(f'SET SCHEMA "{sch}"')
                cur.close()
            # Pass the connection and schema name to products_catalog for image URL generation
            data = products_catalog(conn, cfg['schema'], search, item_group)
            paginator = Paginator(data or [], page_size)
            page_obj = paginator.get_page(page_num)
            return Response({'success': True, 'page': page_obj.number, 'page_size': page_size, 'num_pages': paginator.num_pages, 'count': paginator.count, 'database': cfg['schema'], 'data': list(page_obj.object_list)}, status=status.HTTP_200_OK)
        finally:
            try:
                conn.close()
            except Exception:
                pass
    except Exception as e:
        return Response({'success': False, 'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

# Core function that handles both list all and specific card_code
def get_policy_customer_balance_data(request, card_code=None):
    """
    Core function to fetch policy customer balance.
    If card_code is None, returns all policies or filtered by user if user parameter is provided.
    If card_code is provided, returns balance for that specific customer.
    If user parameter is provided, returns balance for customers assigned to that user.
    """
    try:
        _hana_load_env_file(os.path.join(os.path.dirname(__file__), '.env'))
        _hana_load_env_file(os.path.join(str(settings.BASE_DIR), '.env'))
        _hana_load_env_file(os.path.join(str(Path(settings.BASE_DIR).parent), '.env'))
        _hana_load_env_file(os.path.join(os.getcwd(), '.env'))
    except Exception:
        pass
    cfg = {
        'host': os.environ.get('HANA_HOST') or '',
        'port': os.environ.get('HANA_PORT') or '30015',
        'user': os.environ.get('HANA_USER') or '',
        'schema': os.environ.get('HANA_SCHEMA') or '',
        'encrypt': os.environ.get('HANA_ENCRYPT') or '',
        'ssl_validate': os.environ.get('HANA_SSL_VALIDATE') or '',
    }
    db_param = (getattr(request, 'query_params', {}).get('database') if hasattr(request, 'query_params') else None) or request.GET.get('database', '')
    db_param = (db_param or '').strip()
    if db_param:
        norm = db_param.strip().upper().replace('-APP', '_APP')
        if '4B-BIO' in norm:
            cfg['schema'] = '4B-BIO_APP'
        elif '4B-ORANG' in norm:
            cfg['schema'] = '4B-ORANG_APP'
        else:
            cfg['schema'] = db_param
    else:
        try:
            from preferences.models import Setting
            s = Setting.objects.filter(slug='SAP_COMPANY_DB').first()
            if s and s.value:
                cfg['schema'] = str(s.value).strip()
            else:
                cfg['schema'] = os.environ.get('SAP_COMPANY_DB') or cfg['schema'] or '4B-BIO_APP'
        except Exception:
            cfg['schema'] = os.environ.get('SAP_COMPANY_DB') or cfg['schema'] or '4B-BIO_APP'
    try:
        from hdbcli import dbapi
        pwd = os.environ.get('HANA_PASSWORD','')
        kwargs = {'address': cfg['host'], 'port': int(cfg['port']), 'user': cfg['user'] or '', 'password': pwd or ''}
        if str(cfg['encrypt']).strip().lower() in ('true','1','yes'):
            kwargs['encrypt'] = True
            if cfg['ssl_validate']:
                kwargs['sslValidateCertificate'] = (str(cfg['ssl_validate']).strip().lower() in ('true','1','yes'))
        conn = dbapi.connect(**kwargs)
        try:
            if cfg['schema']:
                sch = cfg['schema']
                cur = conn.cursor()
                cur.execute(f'SET SCHEMA "{sch}"')
                cur.close()
            
            # Determine limit from query params
            limit = 200
            try:
                limit_param = request.query_params.get('limit', '200')
                limit = int(limit_param)
            except:
                limit = 200
            
            # Check for user parameter to filter by user's customers
            user_param = (getattr(request, 'query_params', {}).get('user') if hasattr(request, 'query_params') else None) or request.GET.get('user', '')
            user_param = (user_param or '').strip()
            
            # Call appropriate function based on parameters
            if card_code:
                # Specific card code requested
                data = policy_customer_balance(conn, card_code)
            elif user_param:
                # Filter by user's assigned customers
                try:
                    from accounts.models import User
                    from FieldAdvisoryService.models import Dealer
                    
                    # Try to get user by ID or username
                    user_obj = None
                    try:
                        user_id = int(user_param)
                        user_obj = User.objects.get(id=user_id)
                    except (ValueError, User.DoesNotExist):
                        user_obj = User.objects.filter(username=user_param).first()
                    
                    if user_obj:
                        # Get dealer card codes for this user
                        dealers = Dealer.objects.filter(user=user_obj).values_list('card_code', flat=True).exclude(card_code__isnull=True).exclude(card_code='')
                        dealer_card_codes = list(dealers)
                        
                        if dealer_card_codes:
                            # Fetch balance for each dealer's card code
                            data = []
                            for cc in dealer_card_codes:
                                try:
                                    balance = policy_customer_balance(conn, cc)
                                    if balance:
                                        data.extend(balance)
                                except Exception:
                                    pass
                        else:
                            data = []
                    else:
                        return Response({'success': False, 'error': f'User "{user_param}" not found'}, status=status.HTTP_404_NOT_FOUND)
                except Exception as e:
                    return Response({'success': False, 'error': f'Error fetching user customers: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            else:
                # Get all customers
                data = policy_customer_balance_all(conn, limit)
            
            return Response({'success': True, 'count': len(data or []), 'data': data}, status=status.HTTP_200_OK)
        finally:
            try:
                conn.close()
            except Exception:
                pass
    except Exception as e:
        return Response({'success': False, 'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

# Wrapper for list all policies customer balance (no card_code required)
@swagger_auto_schema(tags=['SAP'], 
    method='get',
    operation_summary="Policy Customer Balance",
    operation_description="Get policy-wise customer balance. **NO REQUIRED FIELDS**. Flexible filtering options: (1) All balances - send no parameters, (2) By card_code - use card_code query parameter, (3) By user - use user parameter to get user's customers, (4) Combinations - use multiple filters together. Also see legacy path-based endpoint /policy-customer-balance/{card_code}/ for backward compatibility.",
    manual_parameters=[
        openapi.Parameter('card_code', openapi.IN_QUERY, description="Optional: Filter by customer card code (e.g., ORC00002)", type=openapi.TYPE_STRING, required=False),
        openapi.Parameter('database', openapi.IN_QUERY, description="Optional: Database/schema (4B-BIO_APP or 4B-ORANG_APP). If not provided, uses default from settings.", type=openapi.TYPE_STRING, enum=['4B-BIO-app', '4B-ORANG-app'], required=False),
        openapi.Parameter('user', openapi.IN_QUERY, description="Optional: User ID or username. Returns customers assigned to this user.", type=openapi.TYPE_STRING, required=False),
        openapi.Parameter('limit', openapi.IN_QUERY, description="Optional: Max records (default: 200). Only applies when not filtering by specific card_code.", type=openapi.TYPE_INTEGER, required=False)
    ],
    responses={200: openapi.Response(description="OK"), 404: openapi.Response(description="User not found"), 500: openapi.Response(description="Server Error")}
)
@api_view(['GET'])
def policy_customer_balance_list(request):
    """
    Flexible policy customer balance endpoint with no required fields.
    Supports multiple filtering options:
    - No parameters: returns all balances
    - card_code: returns balance for specific customer
    - user: returns balances for user's assigned customers
    - Combinations: card_code + user validates that user owns the card_code
    """
    # Check for optional card_code query parameter
    card_code_param = (getattr(request, 'query_params', {}).get('card_code') if hasattr(request, 'query_params') else None) or request.GET.get('card_code', '')
    card_code_param = (card_code_param or '').strip()
    
    if card_code_param:
        # If card_code is provided as query param, validate user if provided
        user_param = (getattr(request, 'query_params', {}).get('user') if hasattr(request, 'query_params') else None) or request.GET.get('user', '')
        user_param = (user_param or '').strip()
        
        if user_param:
            # Validate that card_code belongs to user
            try:
                from accounts.models import User
                from FieldAdvisoryService.models import Dealer
                
                user_obj = None
                try:
                    user_id = int(user_param)
                    user_obj = User.objects.get(id=user_id)
                except (ValueError, User.DoesNotExist):
                    user_obj = User.objects.filter(username=user_param).first()
                
                if not user_obj:
                    return Response({'success': False, 'error': f'User "{user_param}" not found'}, status=status.HTTP_404_NOT_FOUND)
                
                dealer = Dealer.objects.filter(user=user_obj, card_code=card_code_param).first()
                
                if not dealer:
                    return Response(
                        {'success': False, 'error': f'Card code "{card_code_param}" does not belong to user "{user_param}"'}, 
                        status=status.HTTP_403_FORBIDDEN
                    )
            except Exception as e:
                return Response({'success': False, 'error': f'Error validating user: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        # Fetch balance for the card_code
        return get_policy_customer_balance_data(request, card_code=card_code_param)
    else:
        # No card_code provided, use list logic
        return get_policy_customer_balance_data(request, card_code=None)

# Path-based endpoint with user validation
@swagger_auto_schema(tags=['SAP'], 
    method='get',
    operation_summary="Policy Customer Balance by CardCode",
    operation_description="Get policy-wise customer balance for a specific customer. Provide user parameter to validate that the card_code belongs to that user. Returns 403 if card_code doesn't belong to the specified user.",
    manual_parameters=[
        openapi.Parameter('database', openapi.IN_QUERY, description="Optional: Database/schema (4B-BIO_APP or 4B-ORANG_APP)", type=openapi.TYPE_STRING, enum=['4B-BIO-app', '4B-ORANG-app'], required=False),
        openapi.Parameter('user', openapi.IN_QUERY, description="Optional: User ID or username to validate card_code belongs to this user. Returns 403 if validation fails.", type=openapi.TYPE_STRING, required=False)
    ],
    responses={200: openapi.Response(description="OK"), 403: openapi.Response(description="Forbidden - Card code does not belong to user"), 404: openapi.Response(description="User not found"), 500: openapi.Response(description="Server Error")}
)
@api_view(['GET'])
def policy_customer_balance_detail(request, card_code):
    """
    Get policy customer balance for a specific card_code (legacy route).
    Kept for backward compatibility.
    Optionally validates that the card_code belongs to a specified user.
    """
    # Validate user if provided
    user_param = (getattr(request, 'query_params', {}).get('user') if hasattr(request, 'query_params') else None) or request.GET.get('user', '')
    user_param = (user_param or '').strip()
    
    if user_param:
        try:
            from accounts.models import User
            from FieldAdvisoryService.models import Dealer
            
            user_obj = None
            try:
                user_id = int(user_param)
                user_obj = User.objects.get(id=user_id)
            except (ValueError, User.DoesNotExist):
                user_obj = User.objects.filter(username=user_param).first()
            
            if not user_obj:
                return Response({'success': False, 'error': f'User "{user_param}" not found'}, status=status.HTTP_404_NOT_FOUND)
            
            dealer = Dealer.objects.filter(user=user_obj, card_code=card_code).first()
            
            if not dealer:
                return Response(
                    {'success': False, 'error': f'Card code "{card_code}" does not belong to user "{user_param}"'}, 
                    status=status.HTTP_403_FORBIDDEN
                )
        except Exception as e:
            return Response({'success': False, 'error': f'Error validating user: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    # Delegate to get_policy_customer_balance_data with the card_code
    return get_policy_customer_balance_data(request, card_code=card_code)

@swagger_auto_schema(tags=['SAP'], 
    method='get',
    operation_description="HANA health",
    responses={200: openapi.Response(description="OK"), 500: openapi.Response(description="Server Error")}
)
@api_view(['GET'])
def hana_health_api(request):
    try:
        _hana_load_env_file(os.path.join(os.path.dirname(__file__), '.env'))
        _hana_load_env_file(os.path.join(str(settings.BASE_DIR), '.env'))
        _hana_load_env_file(os.path.join(str(Path(settings.BASE_DIR).parent), '.env'))
        _hana_load_env_file(os.path.join(os.getcwd(), '.env'))
    except Exception:
        pass
    cfg = {
        'host': os.environ.get('HANA_HOST') or '',
        'port': os.environ.get('HANA_PORT') or '30015',
        'user': os.environ.get('HANA_USER') or '',
        'schema': os.environ.get('HANA_SCHEMA') or '',
        'encrypt': os.environ.get('HANA_ENCRYPT') or '',
        'ssl_validate': os.environ.get('HANA_SSL_VALIDATE') or '',
    }
    try:
        from hdbcli import dbapi
        pwd = os.environ.get('HANA_PASSWORD','')
        kwargs = {'address': cfg['host'], 'port': int(cfg['port']), 'user': cfg['user'] or '', 'password': pwd or ''}
        if str(cfg['encrypt']).strip().lower() in ('true','1','yes'):
            kwargs['encrypt'] = True
            if cfg['ssl_validate']:
                kwargs['sslValidateCertificate'] = (str(cfg['ssl_validate']).strip().lower() in ('true','1','yes'))
        conn = dbapi.connect(**kwargs)
        try:
            cur = conn.cursor()
            cur.execute('SELECT CURRENT_UTCTIMESTAMP AS TS FROM DUMMY')
            rows = cur.fetchall()
            cols = [d[0] for d in cur.description] if cur.description else []
            data = []
            for r in rows:
                row = {}
                for i, c in enumerate(cols):
                    try:
                        row[c] = r[i]
                    except Exception:
                        row[c] = None
                data.append(row)
            cur.close()
            return Response({'success': True, 'count': len(data or []), 'data': data}, status=status.HTTP_200_OK)
        finally:
            try:
                conn.close()
            except Exception:
                pass
    except Exception as e:
        return Response({'success': False, 'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@swagger_auto_schema(tags=['SAP'], 
    method='get',
    operation_description="Count HANA tables",
    responses={200: openapi.Response(description="OK"), 500: openapi.Response(description="Server Error")}
)
@api_view(['GET'])
def hana_count_tables_api(request):
    try:
        _hana_load_env_file(os.path.join(os.path.dirname(__file__), '.env'))
        _hana_load_env_file(os.path.join(str(settings.BASE_DIR), '.env'))
        _hana_load_env_file(os.path.join(str(Path(settings.BASE_DIR).parent), '.env'))
        _hana_load_env_file(os.path.join(os.getcwd(), '.env'))
    except Exception:
        pass
    cfg = {
        'host': os.environ.get('HANA_HOST') or '',
        'port': os.environ.get('HANA_PORT') or '30015',
        'user': os.environ.get('HANA_USER') or '',
        'schema': os.environ.get('HANA_SCHEMA') or '',
        'encrypt': os.environ.get('HANA_ENCRYPT') or '',
        'ssl_validate': os.environ.get('HANA_SSL_VALIDATE') or '',
    }
    try:
        from hdbcli import dbapi
        pwd = os.environ.get('HANA_PASSWORD','')
        kwargs = {'address': cfg['host'], 'port': int(cfg['port']), 'user': cfg['user'] or '', 'password': pwd or ''}
        if str(cfg['encrypt']).strip().lower() in ('true','1','yes'):
            kwargs['encrypt'] = True
            if cfg['ssl_validate']:
                kwargs['sslValidateCertificate'] = (str(cfg['ssl_validate']).strip().lower() in ('true','1','yes'))
        conn = dbapi.connect(**kwargs)
        try:
            cur = conn.cursor()
            if cfg['schema']:
                cur.execute('SELECT COUNT(*) AS TABLE_COUNT FROM SYS.TABLES WHERE SCHEMA_NAME = CURRENT_SCHEMA')
            else:
                cur.execute('SELECT COUNT(*) AS TABLE_COUNT FROM SYS.TABLES')
            r = cur.fetchone()
            val = None
            if r is not None:
                try:
                    val = int(r[0])
                except Exception:
                    val = None
            cur.close()
            return Response({'success': True, 'data': {'table_count': val}}, status=status.HTTP_200_OK)
        finally:
            try:
                conn.close()
            except Exception:
                pass
    except Exception as e:
        return Response({'success': False, 'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@swagger_auto_schema(tags=['SAP'], 
    method='get',
    operation_description="Select sample from OITM",
    responses={200: openapi.Response(description="OK"), 500: openapi.Response(description="Server Error")}
)
@api_view(['GET'])
def select_oitm_api(request):
    try:
        _hana_load_env_file(os.path.join(os.path.dirname(__file__), '.env'))
        _hana_load_env_file(os.path.join(str(settings.BASE_DIR), '.env'))
        _hana_load_env_file(os.path.join(str(Path(settings.BASE_DIR).parent), '.env'))
        _hana_load_env_file(os.path.join(os.getcwd(), '.env'))
    except Exception:
        pass
    cfg = {
        'host': os.environ.get('HANA_HOST') or '',
        'port': os.environ.get('HANA_PORT') or '30015',
        'user': os.environ.get('HANA_USER') or '',
        'schema': os.environ.get('HANA_SCHEMA') or '',
        'encrypt': os.environ.get('HANA_ENCRYPT') or '',
        'ssl_validate': os.environ.get('HANA_SSL_VALIDATE') or '',
    }
    try:
        from hdbcli import dbapi
        pwd = os.environ.get('HANA_PASSWORD','')
        kwargs = {'address': cfg['host'], 'port': int(cfg['port']), 'user': cfg['user'] or '', 'password': pwd or ''}
        if str(cfg['encrypt']).strip().lower() in ('true','1','yes'):
            kwargs['encrypt'] = True
            if cfg['ssl_validate']:
                kwargs['sslValidateCertificate'] = (str(cfg['ssl_validate']).strip().lower() in ('true','1','yes'))
        conn = dbapi.connect(**kwargs)
        try:
            if cfg['schema']:
                sch = cfg['schema']
                cur = conn.cursor()
                cur.execute(f'SET SCHEMA "{sch}"')
                cur.close()
            cur = conn.cursor()
            sql = f'SELECT * FROM "{cfg["schema"]}"."OITM"' if cfg['schema'] else 'SELECT * FROM "OITM"'
            cur.execute(sql)
            rows = cur.fetchmany(10)
            cols = [d[0] for d in cur.description] if cur.description else []
            data = []
            for r in rows:
                row = {}
                for i, c in enumerate(cols):
                    try:
                        row[c] = r[i]
                    except Exception:
                        row[c] = None
                data.append(row)
            cur.close()
            return Response({'success': True, 'count': len(data or []), 'data': data}, status=status.HTTP_200_OK)
        finally:
            try:
                conn.close()
            except Exception:
                pass
    except Exception as e:
        return Response({'success': False, 'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@swagger_auto_schema(tags=['SAP'], 
    method='get',
    operation_summary="Warehouse list for item",
    operation_description="List warehouses for a specific ItemCode; when ItemCode is empty, returns all warehouses. Supports pagination and search.",
    manual_parameters=[
        openapi.Parameter('database', openapi.IN_QUERY, description="Database/schema", type=openapi.TYPE_STRING, enum=['4B-BIO-app', '4B-ORANG-app'], required=False),
        openapi.Parameter('item_code', openapi.IN_QUERY, description="ItemCode (optional)", type=openapi.TYPE_STRING, required=False),
        openapi.Parameter('search', openapi.IN_QUERY, description="Search WhsCode or WhsName", type=openapi.TYPE_STRING, required=False),
        openapi.Parameter('page', openapi.IN_QUERY, description="Page number", type=openapi.TYPE_INTEGER, required=False),
        openapi.Parameter('page_size', openapi.IN_QUERY, description="Items per page", type=openapi.TYPE_INTEGER, required=False),
    ],
    responses={200: openapi.Response(description="OK"), 500: openapi.Response(description="Server Error")}
)
@api_view(['GET'])
def warehouse_for_item_api(request):
    try:
        _hana_load_env_file(os.path.join(os.path.dirname(__file__), '.env'))
        _hana_load_env_file(os.path.join(str(settings.BASE_DIR), '.env'))
        _hana_load_env_file(os.path.join(str(Path(settings.BASE_DIR).parent), '.env'))
        _hana_load_env_file(os.path.join(os.getcwd(), '.env'))
    except Exception:
        pass
    cfg = {
        'host': os.environ.get('HANA_HOST') or '',
        'port': os.environ.get('HANA_PORT') or '30015',
        'user': os.environ.get('HANA_USER') or '',
        'schema': os.environ.get('HANA_SCHEMA') or '4B-BIO_APP',
        'encrypt': os.environ.get('HANA_ENCRYPT') or '',
        'ssl_validate': os.environ.get('HANA_SSL_VALIDATE') or '',
    }
    # Handle database parameter
    db_param = (request.GET.get('database') or '').strip()
    if db_param:
        norm = db_param.strip().upper().replace('-APP', '_APP')
        if '4B-BIO' in norm:
            cfg['schema'] = '4B-BIO_APP'
        elif '4B-ORANG' in norm:
            cfg['schema'] = '4B-ORANG_APP'
        else:
            cfg['schema'] = db_param
    
    item_code = (request.GET.get('item_code') or '').strip()
    search = (request.GET.get('search') or '').strip() or None
    page_param = (request.GET.get('page') or '1').strip()
    page_size_param = (request.GET.get('page_size') or '').strip()
    try:
        page_num = int(page_param) if page_param else 1
    except Exception:
        page_num = 1
    default_page_size = 10
    try:
        default_page_size = int(getattr(settings, 'REST_FRAMEWORK', {}).get('PAGE_SIZE', 10) or 10)
    except Exception:
        default_page_size = 10
    try:
        page_size = int(page_size_param) if page_size_param else default_page_size
    except Exception:
        page_size = default_page_size
    try:
        from hdbcli import dbapi
        pwd = os.environ.get('HANA_PASSWORD','')
        kwargs = {'address': cfg['host'], 'port': int(cfg['port']), 'user': cfg['user'] or '', 'password': pwd or ''}
        if str(cfg['encrypt']).strip().lower() in ('true','1','yes'):
            kwargs['encrypt'] = True
            if cfg['ssl_validate']:
                kwargs['sslValidateCertificate'] = (str(cfg['ssl_validate']).strip().lower() in ('true','1','yes'))
        conn = dbapi.connect(**kwargs)
        try:
            if cfg['schema']:
                sch = cfg['schema']
                cur = conn.cursor()
                cur.execute(f'SET SCHEMA "{sch}"')
                cur.close()
            from .hana_connect import warehouses_all
            if not item_code:
                data = warehouses_all(conn, 500, search)
            else:
                data = warehouse_for_item(conn, item_code, search)
            paginator = Paginator(data or [], page_size)
            page_obj = paginator.get_page(page_num)
            return Response({'success': True, 'page': page_obj.number, 'page_size': page_size, 'num_pages': paginator.num_pages, 'count': paginator.count, 'data': list(page_obj.object_list)}, status=status.HTTP_200_OK)
        finally:
            try:
                conn.close()
            except Exception:
                pass
    except Exception as e:
        return Response({'success': False, 'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@swagger_auto_schema(tags=['SAP'], 
    method='get',
    operation_summary="Contact persons",
    operation_description="List contact persons. When both CardCode and ContactCode are empty or show_all=true, returns all. When CardCode only is provided, returns contacts for that BP. When both are provided, returns a single record.",
    manual_parameters=[
        openapi.Parameter(
            'database',
            openapi.IN_QUERY,
            description="HANA database/schema to query. Accepts Company name values (e.g., 4B-BIO_APP, 4B-ORANG_APP) or company keys (e.g., 4B-BIO, 4B-ORANG). If not provided, falls back to session or first active company.",
            type=openapi.TYPE_STRING,
            required=False
        ),
        openapi.Parameter('card_code', openapi.IN_QUERY, description="Business Partner code (optional)", type=openapi.TYPE_STRING, required=False),
        openapi.Parameter('contact_code', openapi.IN_QUERY, description="Contact code (optional)", type=openapi.TYPE_STRING, required=False),
        openapi.Parameter('show_all', openapi.IN_QUERY, description="Show all contacts", type=openapi.TYPE_BOOLEAN, required=False),
        openapi.Parameter('page', openapi.IN_QUERY, description="Page number", type=openapi.TYPE_INTEGER, required=False),
        openapi.Parameter('page_size', openapi.IN_QUERY, description="Items per page", type=openapi.TYPE_INTEGER, required=False),
    ],
    responses={200: openapi.Response(description="OK"), 500: openapi.Response(description="Server Error")}
)
@api_view(['GET'])
def contact_persons_api(request):
    try:
        _hana_load_env_file(os.path.join(os.path.dirname(__file__), '.env'))
        _hana_load_env_file(os.path.join(str(settings.BASE_DIR), '.env'))
        _hana_load_env_file(os.path.join(str(Path(settings.BASE_DIR).parent), '.env'))
        _hana_load_env_file(os.path.join(os.getcwd(), '.env'))
    except Exception:
        pass
    cfg = {
        'host': os.environ.get('HANA_HOST') or '',
        'port': os.environ.get('HANA_PORT') or '30015',
        'user': os.environ.get('HANA_USER') or '',
        'schema': os.environ.get('HANA_SCHEMA') or '4B-BIO_APP',
        'encrypt': os.environ.get('HANA_ENCRYPT') or '',
        'ssl_validate': os.environ.get('HANA_SSL_VALIDATE') or '',
    }
    
    # Resolve HANA schema using shared helper for consistency
    hana_schema = get_hana_schema_from_request(request)
    cfg['schema'] = hana_schema
    
    card_code = (request.GET.get('card_code') or '').strip()
    contact_code = (request.GET.get('contact_code') or '').strip()
    show_all = (request.GET.get('show_all') or '').strip().lower() in ('true','1','yes')
    page_param = (request.GET.get('page') or '1').strip()
    page_size_param = (request.GET.get('page_size') or '').strip()
    try:
        page_num = int(page_param) if page_param else 1
    except Exception:
        page_num = 1
    default_page_size = 10
    try:
        default_page_size = int(getattr(settings, 'REST_FRAMEWORK', {}).get('PAGE_SIZE', 10) or 10)
    except Exception:
        default_page_size = 10
    try:
        page_size = int(page_size_param) if page_size_param else default_page_size
    except Exception:
        page_size = default_page_size
    try:
        from hdbcli import dbapi
        pwd = os.environ.get('HANA_PASSWORD','')
        kwargs = {'address': cfg['host'], 'port': int(cfg['port']), 'user': cfg['user'] or '', 'password': pwd or ''}
        if str(cfg['encrypt']).strip().lower() in ('true','1','yes'):
            kwargs['encrypt'] = True
            if cfg['ssl_validate']:
                kwargs['sslValidateCertificate'] = (str(cfg['ssl_validate']).strip().lower() in ('true','1','yes'))
        conn = dbapi.connect(**kwargs)
        try:
            if cfg['schema']:
                sch = cfg['schema']
                cur = conn.cursor()
                cur.execute(f'SET SCHEMA "{sch}"')
                cur.close()
            from .hana_connect import contacts_all, contacts_by_card
            if show_all or (not card_code and not contact_code):
                data = contacts_all(conn)
            elif card_code and not contact_code:
                data = contacts_by_card(conn, card_code)
            elif card_code and contact_code:
                one = contact_person_name(conn, card_code, contact_code)
                data = []
                if one:
                    data = [{
                        'CardCode': card_code,
                        'ContactCode': contact_code,
                        'Name': one.get('Name') if isinstance(one, dict) else one
                    }]
            else:
                data = []
            paginator = Paginator(data or [], page_size)
            page_obj = paginator.get_page(page_num)
            return Response({'success': True, 'page': page_obj.number, 'page_size': page_size, 'num_pages': paginator.num_pages, 'count': paginator.count, 'data': list(page_obj.object_list)}, status=status.HTTP_200_OK)
        finally:
            try:
                conn.close()
            except Exception:
                pass
    except Exception as e:
        return Response({'success': False, 'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@swagger_auto_schema(tags=['SAP'], 
    method='get',
    operation_summary="Project balance",
    operation_description="Return project balances. When project_code is empty or show_all=true, returns balances for all projects. Otherwise returns specific project balance.",
    manual_parameters=[
        openapi.Parameter('project_code', openapi.IN_QUERY, description="Project code (optional)", type=openapi.TYPE_STRING, required=False),
        openapi.Parameter('show_all', openapi.IN_QUERY, description="Show all projects", type=openapi.TYPE_BOOLEAN, required=False),
        openapi.Parameter('page', openapi.IN_QUERY, description="Page number", type=openapi.TYPE_INTEGER, required=False),
        openapi.Parameter('page_size', openapi.IN_QUERY, description="Items per page", type=openapi.TYPE_INTEGER, required=False),
    ],
    responses={200: openapi.Response(description="OK"), 500: openapi.Response(description="Server Error")}
)
@api_view(['GET'])
def project_balance_api(request):
    try:
        _hana_load_env_file(os.path.join(os.path.dirname(__file__), '.env'))
        _hana_load_env_file(os.path.join(str(settings.BASE_DIR), '.env'))
        _hana_load_env_file(os.path.join(str(Path(settings.BASE_DIR).parent), '.env'))
        _hana_load_env_file(os.path.join(os.getcwd(), '.env'))
    except Exception:
        pass
    cfg = {
        'host': os.environ.get('HANA_HOST') or '',
        'port': os.environ.get('HANA_PORT') or '30015',
        'user': os.environ.get('HANA_USER') or '',
        'schema': os.environ.get('HANA_SCHEMA') or '4B-BIO_APP',
        'encrypt': os.environ.get('HANA_ENCRYPT') or '',
        'ssl_validate': os.environ.get('HANA_SSL_VALIDATE') or '',
    }
    # Handle database parameter
    db_param = (request.GET.get('database') or '').strip()
    if db_param:
        norm = db_param.strip().upper().replace('-APP', '_APP')
        if '4B-BIO' in norm:
            cfg['schema'] = '4B-BIO_APP'
        elif '4B-ORANG' in norm:
            cfg['schema'] = '4B-ORANG_APP'
        else:
            cfg['schema'] = db_param
    
    project_code = (request.GET.get('project_code') or '').strip()
    show_all = (request.GET.get('show_all') or '').strip().lower() in ('true','1','yes')
    page_param = (request.GET.get('page') or '1').strip()
    page_size_param = (request.GET.get('page_size') or '').strip()
    try:
        page_num = int(page_param) if page_param else 1
    except Exception:
        page_num = 1
    default_page_size = 10
    try:
        default_page_size = int(getattr(settings, 'REST_FRAMEWORK', {}).get('PAGE_SIZE', 10) or 10)
    except Exception:
        default_page_size = 10
    try:
        page_size = int(page_size_param) if page_size_param else default_page_size
    except Exception:
        page_size = default_page_size
    try:
        from hdbcli import dbapi
        pwd = os.environ.get('HANA_PASSWORD','')
        kwargs = {'address': cfg['host'], 'port': int(cfg['port']), 'user': cfg['user'] or '', 'password': pwd or ''}
        if str(cfg['encrypt']).strip().lower() in ('true','1','yes'):
            kwargs['encrypt'] = True
            if cfg['ssl_validate']:
                kwargs['sslValidateCertificate'] = (str(cfg['ssl_validate']).strip().lower() in ('true','1','yes'))
        conn = dbapi.connect(**kwargs)
        try:
            if cfg['schema']:
                sch = cfg['schema']
                cur = conn.cursor()
                cur.execute(f'SET SCHEMA "{sch}"')
                cur.close()
            from .hana_connect import project_balances_all
            if show_all or not project_code:
                data = project_balances_all(conn)
            else:
                one = project_balance(conn, project_code)
                data = []
                if one:
                    data = [one]
            paginator = Paginator(data or [], page_size)
            page_obj = paginator.get_page(page_num)
            return Response({'success': True, 'page': page_obj.number, 'page_size': page_size, 'num_pages': paginator.num_pages, 'count': paginator.count, 'data': list(page_obj.object_list)}, status=status.HTTP_200_OK)
        finally:
            try:
                conn.close()
            except Exception:
                pass
    except Exception as e:
        return Response({'success': False, 'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@swagger_auto_schema(tags=['SAP'], 
    method='get',
    operation_summary="Customer addresses",
    operation_description="Return default billing addresses. When card_code is empty or show_all=true, returns all BPs' default billing addresses. Otherwise returns specific BP address.",
    manual_parameters=[
        openapi.Parameter('card_code', openapi.IN_QUERY, description="Business Partner code (optional)", type=openapi.TYPE_STRING, required=False),
        openapi.Parameter('show_all', openapi.IN_QUERY, description="Show all addresses", type=openapi.TYPE_BOOLEAN, required=False),
        openapi.Parameter('page', openapi.IN_QUERY, description="Page number", type=openapi.TYPE_INTEGER, required=False),
        openapi.Parameter('page_size', openapi.IN_QUERY, description="Items per page", type=openapi.TYPE_INTEGER, required=False),
    ],
    responses={200: openapi.Response(description="OK"), 500: openapi.Response(description="Server Error")}
)
@api_view(['GET'])
def customer_addresses_api(request):
    try:
        _hana_load_env_file(os.path.join(os.path.dirname(__file__), '.env'))
        _hana_load_env_file(os.path.join(str(settings.BASE_DIR), '.env'))
        _hana_load_env_file(os.path.join(str(Path(settings.BASE_DIR).parent), '.env'))
        _hana_load_env_file(os.path.join(os.getcwd(), '.env'))
    except Exception:
        pass
    cfg = {
        'host': os.environ.get('HANA_HOST') or '',
        'port': os.environ.get('HANA_PORT') or '30015',
        'user': os.environ.get('HANA_USER') or '',
        'schema': os.environ.get('HANA_SCHEMA') or '4B-BIO_APP',
        'encrypt': os.environ.get('HANA_ENCRYPT') or '',
        'ssl_validate': os.environ.get('HANA_SSL_VALIDATE') or '',
    }
    # Handle database parameter
    db_param = (request.GET.get('database') or '').strip()
    if db_param:
        norm = db_param.strip().upper().replace('-APP', '_APP')
        if '4B-BIO' in norm:
            cfg['schema'] = '4B-BIO_APP'
        elif '4B-ORANG' in norm:
            cfg['schema'] = '4B-ORANG_APP'
        else:
            cfg['schema'] = db_param
    
    card_code = (request.GET.get('card_code') or '').strip()
    show_all = (request.GET.get('show_all') or '').strip().lower() in ('true','1','yes')
    page_param = (request.GET.get('page') or '1').strip()
    page_size_param = (request.GET.get('page_size') or '').strip()
    try:
        page_num = int(page_param) if page_param else 1
    except Exception:
        page_num = 1
    default_page_size = 10
    try:
        default_page_size = int(getattr(settings, 'REST_FRAMEWORK', {}).get('PAGE_SIZE', 10) or 10)
    except Exception:
        default_page_size = 10
    try:
        page_size = int(page_size_param) if page_size_param else default_page_size
    except Exception:
        page_size = default_page_size
    try:
        from hdbcli import dbapi
        pwd = os.environ.get('HANA_PASSWORD','')
        kwargs = {'address': cfg['host'], 'port': int(cfg['port']), 'user': cfg['user'] or '', 'password': pwd or ''}
        if str(cfg['encrypt']).strip().lower() in ('true','1','yes'):
            kwargs['encrypt'] = True
            if cfg['ssl_validate']:
                kwargs['sslValidateCertificate'] = (str(cfg['ssl_validate']).strip().lower() in ('true','1','yes'))
        conn = dbapi.connect(**kwargs)
        try:
            if cfg['schema']:
                sch = cfg['schema']
                cur = conn.cursor()
                cur.execute(f'SET SCHEMA "{sch}"')
                cur.close()
            from .hana_connect import customer_addresses_all
            if show_all or not card_code:
                data = customer_addresses_all(conn)
            else:
                data = customer_addresses(conn, card_code)
            paginator = Paginator(data or [], page_size)
            page_obj = paginator.get_page(page_num)
            return Response({'success': True, 'page': page_obj.number, 'page_size': page_size, 'num_pages': paginator.num_pages, 'count': paginator.count, 'data': list(page_obj.object_list)}, status=status.HTTP_200_OK)
        finally:
            try:
                conn.close()
            except Exception:
                pass
    except Exception as e:
        return Response({'success': False, 'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@swagger_auto_schema(tags=['SAP'], 
    method='get',
    operation_summary="Territories (full)",
    operation_description="List territories with optional status filter and pagination.",
    manual_parameters=[
        openapi.Parameter('status', openapi.IN_QUERY, description="Status: active/inactive", type=openapi.TYPE_STRING, required=False),
        openapi.Parameter('limit', openapi.IN_QUERY, description="Max records (default 500)", type=openapi.TYPE_INTEGER, required=False),
        openapi.Parameter('page', openapi.IN_QUERY, description="Page number", type=openapi.TYPE_INTEGER, required=False),
        openapi.Parameter('page_size', openapi.IN_QUERY, description="Items per page", type=openapi.TYPE_INTEGER, required=False),
    ],
    responses={200: openapi.Response(description="OK"), 500: openapi.Response(description="Server Error")}
)
@api_view(['GET'])
def territories_full_api(request):
    try:
        _hana_load_env_file(os.path.join(os.path.dirname(__file__), '.env'))
        _hana_load_env_file(os.path.join(str(settings.BASE_DIR), '.env'))
        _hana_load_env_file(os.path.join(str(Path(settings.BASE_DIR).parent), '.env'))
        _hana_load_env_file(os.path.join(os.getcwd(), '.env'))
    except Exception:
        pass
    cfg = {
        'host': os.environ.get('HANA_HOST') or '',
        'port': os.environ.get('HANA_PORT') or '30015',
        'user': os.environ.get('HANA_USER') or '',
        'schema': os.environ.get('HANA_SCHEMA') or '4B-BIO_APP',
        'encrypt': os.environ.get('HANA_ENCRYPT') or '',
        'ssl_validate': os.environ.get('HANA_SSL_VALIDATE') or '',
    }
    # Handle database parameter
    db_param = (request.GET.get('database') or '').strip()
    if db_param:
        norm = db_param.strip().upper().replace('-APP', '_APP')
        if '4B-BIO' in norm:
            cfg['schema'] = '4B-BIO_APP'
        elif '4B-ORANG' in norm:
            cfg['schema'] = '4B-ORANG_APP'
        else:
            cfg['schema'] = db_param
    
    status_param = (request.GET.get('status') or '').strip().lower()
    limit_param = (request.GET.get('limit') or '').strip()
    page_param = (request.GET.get('page') or '1').strip()
    page_size_param = (request.GET.get('page_size') or '').strip()
    try:
        page_num = int(page_param) if page_param else 1
    except Exception:
        page_num = 1
    default_page_size = 10
    try:
        default_page_size = int(getattr(settings, 'REST_FRAMEWORK', {}).get('PAGE_SIZE', 10) or 10)
    except Exception:
        default_page_size = 10
    try:
        page_size = int(page_size_param) if page_size_param else default_page_size
    except Exception:
        page_size = default_page_size
    try:
        from hdbcli import dbapi
        pwd = os.environ.get('HANA_PASSWORD','')
        kwargs = {'address': cfg['host'], 'port': int(cfg['port']), 'user': cfg['user'] or '', 'password': pwd or ''}
        if str(cfg['encrypt']).strip().lower() in ('true','1','yes'):
            kwargs['encrypt'] = True
            if cfg['ssl_validate']:
                kwargs['sslValidateCertificate'] = (str(cfg['ssl_validate']).strip().lower() in ('true','1','yes'))
        conn = dbapi.connect(**kwargs)
        try:
            if cfg['schema']:
                sch = cfg['schema']
                cur = conn.cursor()
                cur.execute(f'SET SCHEMA "{sch}"')
                cur.close()
            from .hana_connect import territories_all_full
            limit_val = 500
            try:
                if limit_param:
                    limit_val = int(limit_param)
            except Exception:
                limit_val = 500
            if status_param not in ('active','inactive',''):
                status_param = ''
            data = territories_all_full(conn, limit_val, status_param or None)
            paginator = Paginator(data or [], page_size)
            page_obj = paginator.get_page(page_num)
            return Response({'success': True, 'page': page_obj.number, 'page_size': page_size, 'num_pages': paginator.num_pages, 'count': paginator.count, 'data': list(page_obj.object_list)}, status=status.HTTP_200_OK)
        finally:
            try:
                conn.close()
            except Exception:
                pass
    except Exception as e:
        return Response({'success': False, 'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@swagger_auto_schema(tags=['SAP'], 
    method='get',
    operation_summary="CWL (full)",
    operation_description="List CWL rows with limit and pagination.",
    manual_parameters=[
        openapi.Parameter('limit', openapi.IN_QUERY, description="Max records (default 500)", type=openapi.TYPE_INTEGER, required=False),
        openapi.Parameter('page', openapi.IN_QUERY, description="Page number", type=openapi.TYPE_INTEGER, required=False),
        openapi.Parameter('page_size', openapi.IN_QUERY, description="Items per page", type=openapi.TYPE_INTEGER, required=False),
    ],
    responses={200: openapi.Response(description="OK"), 500: openapi.Response(description="Server Error")}
)
@api_view(['GET'])
def cwl_full_api(request):
    try:
        _hana_load_env_file(os.path.join(os.path.dirname(__file__), '.env'))
        _hana_load_env_file(os.path.join(str(settings.BASE_DIR), '.env'))
        _hana_load_env_file(os.path.join(str(Path(settings.BASE_DIR).parent), '.env'))
        _hana_load_env_file(os.path.join(os.getcwd(), '.env'))
    except Exception:
        pass
    cfg = {
        'host': os.environ.get('HANA_HOST') or '',
        'port': os.environ.get('HANA_PORT') or '30015',
        'user': os.environ.get('HANA_USER') or '',
        'schema': os.environ.get('HANA_SCHEMA') or '4B-BIO_APP',
        'encrypt': os.environ.get('HANA_ENCRYPT') or '',
        'ssl_validate': os.environ.get('HANA_SSL_VALIDATE') or '',
    }
    # Handle database parameter
    db_param = (request.GET.get('database') or '').strip()
    if db_param:
        norm = db_param.strip().upper().replace('-APP', '_APP')
        if '4B-BIO' in norm:
            cfg['schema'] = '4B-BIO_APP'
        elif '4B-ORANG' in norm:
            cfg['schema'] = '4B-ORANG_APP'
        else:
            cfg['schema'] = db_param
    
    limit_param = (request.GET.get('limit') or '').strip()
    page_param = (request.GET.get('page') or '1').strip()
    page_size_param = (request.GET.get('page_size') or '').strip()
    try:
        page_num = int(page_param) if page_param else 1
    except Exception:
        page_num = 1
    default_page_size = 10
    try:
        default_page_size = int(getattr(settings, 'REST_FRAMEWORK', {}).get('PAGE_SIZE', 10) or 10)
    except Exception:
        default_page_size = 10
    try:
        page_size = int(page_size_param) if page_size_param else default_page_size
    except Exception:
        page_size = default_page_size
    try:
        from hdbcli import dbapi
        pwd = os.environ.get('HANA_PASSWORD','')
        kwargs = {'address': cfg['host'], 'port': int(cfg['port']), 'user': cfg['user'] or '', 'password': pwd or ''}
        if str(cfg['encrypt']).strip().lower() in ('true','1','yes'):
            kwargs['encrypt'] = True
            if cfg['ssl_validate']:
                kwargs['sslValidateCertificate'] = (str(cfg['ssl_validate']).strip().lower() in ('true','1','yes'))
        conn = dbapi.connect(**kwargs)
        try:
            if cfg['schema']:
                sch = cfg['schema']
                cur = conn.cursor()
                cur.execute(f'SET SCHEMA "{sch}"')
                cur.close()
            from .hana_connect import cwl_all_full
            limit_val = 500
            try:
                if limit_param:
                    limit_val = int(limit_param)
            except Exception:
                limit_val = 500
            data = cwl_all_full(conn, limit_val)
            paginator = Paginator(data or [], page_size)
            page_obj = paginator.get_page(page_num)
            return Response({'success': True, 'page': page_obj.number, 'page_size': page_size, 'num_pages': paginator.num_pages, 'count': paginator.count, 'data': list(page_obj.object_list)}, status=status.HTTP_200_OK)
        finally:
            try:
                conn.close()
            except Exception:
                pass
    except Exception as e:
        return Response({'success': False, 'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@swagger_auto_schema(tags=['SAP'], 
    method='get',
    operation_summary="Customer LOV",
    operation_description="List customers with optional search and pagination.",
    manual_parameters=[
        openapi.Parameter('search', openapi.IN_QUERY, description="Search CardCode or CardName", type=openapi.TYPE_STRING, required=False),
        openapi.Parameter('page', openapi.IN_QUERY, description="Page number", type=openapi.TYPE_INTEGER, required=False),
        openapi.Parameter('page_size', openapi.IN_QUERY, description="Items per page", type=openapi.TYPE_INTEGER, required=False),
        openapi.Parameter('limit', openapi.IN_QUERY, description="Max records to fetch (alias: top)", type=openapi.TYPE_INTEGER, required=False),
        openapi.Parameter('top', openapi.IN_QUERY, description="Max records to fetch (alias: limit)", type=openapi.TYPE_INTEGER, required=False),
    ],
    responses={200: openapi.Response(description="OK"), 500: openapi.Response(description="Server Error")}
)
@api_view(['GET'])
def customer_lov_api(request):
    try:
        _hana_load_env_file(os.path.join(os.path.dirname(__file__), '.env'))
        _hana_load_env_file(os.path.join(str(settings.BASE_DIR), '.env'))
        _hana_load_env_file(os.path.join(str(Path(settings.BASE_DIR).parent), '.env'))
        _hana_load_env_file(os.path.join(os.getcwd(), '.env'))
    except Exception:
        pass
    cfg = {
        'host': os.environ.get('HANA_HOST') or '',
        'port': os.environ.get('HANA_PORT') or '30015',
        'user': os.environ.get('HANA_USER') or '',
        'schema': os.environ.get('HANA_SCHEMA') or '4B-BIO_APP',
        'encrypt': os.environ.get('HANA_ENCRYPT') or '',
        'ssl_validate': os.environ.get('HANA_SSL_VALIDATE') or '',
    }
    # Handle database parameter
    db_param = (request.GET.get('database') or '').strip()
    if db_param:
        norm = db_param.strip().upper().replace('-APP', '_APP')
        if '4B-BIO' in norm:
            cfg['schema'] = '4B-BIO_APP'
        elif '4B-ORANG' in norm:
            cfg['schema'] = '4B-ORANG_APP'
        else:
            cfg['schema'] = db_param
    
    search = (request.GET.get('search') or '').strip()
    page_param = (request.GET.get('page') or '1').strip()
    page_size_param = (request.GET.get('page_size') or '').strip()
    limit_param = (request.GET.get('top') or request.GET.get('limit') or '').strip()
    try:
        page_num = int(page_param) if page_param else 1
    except Exception:
        page_num = 1
    default_page_size = 10
    try:
        default_page_size = int(getattr(settings, 'REST_FRAMEWORK', {}).get('PAGE_SIZE', 10) or 10)
    except Exception:
        default_page_size = 10
    try:
        page_size = int(page_size_param) if page_size_param else default_page_size
    except Exception:
        page_size = default_page_size
    limit_val = 1000
    try:
        if limit_param:
            limit_val = int(limit_param)
    except Exception:
        limit_val = 1000
    try:
        from hdbcli import dbapi
        pwd = os.environ.get('HANA_PASSWORD','')
        kwargs = {'address': cfg['host'], 'port': int(cfg['port']), 'user': cfg['user'] or '', 'password': pwd or ''}
        if str(cfg['encrypt']).strip().lower() in ('true','1','yes'):
            kwargs['encrypt'] = True
            if cfg['ssl_validate']:
                kwargs['sslValidateCertificate'] = (str(cfg['ssl_validate']).strip().lower() in ('true','1','yes'))
        conn = dbapi.connect(**kwargs)
        try:
            if cfg['schema']:
                sch = cfg['schema']
                cur = conn.cursor()
                cur.execute(f'SET SCHEMA "{sch}"')
                cur.close()
            from .hana_connect import customer_lov
            data = customer_lov(conn, search or None, limit=limit_val)
            paginator = Paginator(data or [], page_size)
            page_obj = paginator.get_page(page_num)
            return Response({'success': True, 'page': page_obj.number, 'page_size': page_size, 'num_pages': paginator.num_pages, 'count': paginator.count, 'data': list(page_obj.object_list)}, status=status.HTTP_200_OK)
        finally:
            try:
                conn.close()
            except Exception:
                pass
    except Exception as e:
        return Response({'success': False, 'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@swagger_auto_schema(tags=['SAP'], 
    method='get',
    operation_summary="Item LOV",
    operation_description="List items with optional search and pagination.",
    manual_parameters=[
        openapi.Parameter('database', openapi.IN_QUERY, description="Database/schema", type=openapi.TYPE_STRING, enum=['4B-BIO-app', '4B-ORANG-app'], required=False),
        openapi.Parameter('search', openapi.IN_QUERY, description="Search ItemCode or ItemName", type=openapi.TYPE_STRING, required=False),
        openapi.Parameter('page', openapi.IN_QUERY, description="Page number", type=openapi.TYPE_INTEGER, required=False),
        openapi.Parameter('page_size', openapi.IN_QUERY, description="Items per page", type=openapi.TYPE_INTEGER, required=False),
    ],
    responses={200: openapi.Response(description="OK"), 500: openapi.Response(description="Server Error")}
)
@api_view(['GET'])
def item_lov_api(request):
    try:
        _hana_load_env_file(os.path.join(os.path.dirname(__file__), '.env'))
        _hana_load_env_file(os.path.join(str(settings.BASE_DIR), '.env'))
        _hana_load_env_file(os.path.join(str(Path(settings.BASE_DIR).parent), '.env'))
        _hana_load_env_file(os.path.join(os.getcwd(), '.env'))
    except Exception:
        pass
    cfg = {
        'host': os.environ.get('HANA_HOST') or '',
        'port': os.environ.get('HANA_PORT') or '30015',
        'user': os.environ.get('HANA_USER') or '',
        'schema': os.environ.get('HANA_SCHEMA') or '4B-BIO_APP',
        'encrypt': os.environ.get('HANA_ENCRYPT') or '',
        'ssl_validate': os.environ.get('HANA_SSL_VALIDATE') or '',
    }
    # Handle database parameter
    db_param = (request.GET.get('database') or '').strip()
    if db_param:
        norm = db_param.strip().upper().replace('-APP', '_APP')
        if '4B-BIO' in norm:
            cfg['schema'] = '4B-BIO_APP'
        elif '4B-ORANG' in norm:
            cfg['schema'] = '4B-ORANG_APP'
        else:
            cfg['schema'] = db_param
    
    search = (request.GET.get('search') or '').strip()
    page_param = (request.GET.get('page') or '1').strip()
    page_size_param = (request.GET.get('page_size') or '').strip()
    try:
        page_num = int(page_param) if page_param else 1
    except Exception:
        page_num = 1
    default_page_size = 10
    try:
        default_page_size = int(getattr(settings, 'REST_FRAMEWORK', {}).get('PAGE_SIZE', 10) or 10)
    except Exception:
        default_page_size = 10
    try:
        page_size = int(page_size_param) if page_size_param else default_page_size
    except Exception:
        page_size = default_page_size
    try:
        from hdbcli import dbapi
        pwd = os.environ.get('HANA_PASSWORD','')
        kwargs = {'address': cfg['host'], 'port': int(cfg['port']), 'user': cfg['user'] or '', 'password': pwd or ''}
        if str(cfg['encrypt']).strip().lower() in ('true','1','yes'):
            kwargs['encrypt'] = True
            if cfg['ssl_validate']:
                kwargs['sslValidateCertificate'] = (str(cfg['ssl_validate']).strip().lower() in ('true','1','yes'))
        conn = dbapi.connect(**kwargs)
        try:
            if cfg['schema']:
                sch = cfg['schema']
                cur = conn.cursor()
                cur.execute(f'SET SCHEMA "{sch}"')
                cur.close()
            from .hana_connect import item_lov
            data = item_lov(conn, search or None)
            paginator = Paginator(data or [], page_size)
            page_obj = paginator.get_page(page_num)
            return Response({'success': True, 'page': page_obj.number, 'page_size': page_size, 'num_pages': paginator.num_pages, 'count': paginator.count, 'data': list(page_obj.object_list)}, status=status.HTTP_200_OK)
        finally:
            try:
                conn.close()
            except Exception:
                pass
    except Exception as e:
        return Response({'success': False, 'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@swagger_auto_schema(tags=['SAP Sales Order Form'],
    method='get',
    operation_summary="Item Price by Policy",
    operation_description="""Get unit price (U_frp) for a specific item in a policy. Use this when item is selected to auto-fill unit price in sales order form.
    
    **Response Structure:**
    ```json
    {
        "success": true,
        "data": {
            "doc_entry": "37",
            "item_code": "FG00319",
            "unit_price": 1250.50
        }
    }
    ```
    
    **If no price found:**
    ```json
    {
        "success": true,
        "data": null,
        "message": "No price found for given DocEntry and ItemCode"
    }
    ```
    
    **Usage in Form:**
    - Called automatically when user selects an item from dropdown
    - Auto-fills the unit_price field with returned value
    - Quantity * unit_price calculates line total
    - Price is policy-specific (different policies may have different prices for same item)
    
    **Price Source:** Queries @PLR4 table joining with policy and item data to get U_frp (Final Rate Price).
    """,
    manual_parameters=[
        openapi.Parameter(
            'database',
            openapi.IN_QUERY,
            description="HANA database/schema to query. Accepts Company name values (e.g., 4B-BIO_APP, 4B-ORANG_APP) or company keys (e.g., 4B-BIO, 4B-ORANG). If not provided, falls back to session or first active company.",
            type=openapi.TYPE_STRING,
            required=False
        ),
        openapi.Parameter('doc_entry', openapi.IN_QUERY, description="Policy DocEntry (required, e.g., 37)", type=openapi.TYPE_STRING, required=True),
        openapi.Parameter('item_code', openapi.IN_QUERY, description="ItemCode (required, e.g., FG00319)", type=openapi.TYPE_STRING, required=True),
    ],
    responses={200: openapi.Response(description="OK - price found or null"), 400: openapi.Response(description="Bad Request - missing doc_entry or item_code"), 500: openapi.Response(description="Server Error")}
)
@api_view(['GET'])
def item_price_api(request):
    try:
        _hana_load_env_file(os.path.join(os.path.dirname(__file__), '.env'))
        _hana_load_env_file(os.path.join(str(settings.BASE_DIR), '.env'))
        _hana_load_env_file(os.path.join(str(Path(settings.BASE_DIR).parent), '.env'))
        _hana_load_env_file(os.path.join(os.getcwd(), '.env'))
    except Exception:
        pass

    cfg = {
        'host': os.environ.get('HANA_HOST') or '',
        'port': os.environ.get('HANA_PORT') or '30015',
        'user': os.environ.get('HANA_USER') or '',
        'schema': os.environ.get('HANA_SCHEMA') or '4B-BIO_APP',
        'encrypt': os.environ.get('HANA_ENCRYPT') or '',
        'ssl_validate': os.environ.get('HANA_SSL_VALIDATE') or '',
    }

    # Resolve HANA schema using shared helper
    hana_schema = get_hana_schema_from_request(request)
    cfg['schema'] = hana_schema
    
    logger.info(f"[ITEM_PRICE] Using HANA schema: {hana_schema}")

    doc_entry = (request.GET.get('doc_entry') or '').strip()
    item_code = (request.GET.get('item_code') or '').strip()

    if not doc_entry or not item_code:
        return Response({'success': False, 'error': 'doc_entry and item_code are required'}, status=status.HTTP_400_BAD_REQUEST)

    try:
        from hdbcli import dbapi
        pwd = os.environ.get('HANA_PASSWORD','')
        kwargs = {'address': cfg['host'], 'port': int(cfg['port']), 'user': cfg['user'] or '', 'password': pwd or ''}
        if str(cfg['encrypt']).strip().lower() in ('true','1','yes'):
            kwargs['encrypt'] = True
            if cfg['ssl_validate']:
                kwargs['sslValidateCertificate'] = (str(cfg['ssl_validate']).strip().lower() in ('true','1','yes'))
        conn = dbapi.connect(**kwargs)
        try:
            if cfg['schema']:
                sch = cfg['schema']
                cur = conn.cursor()
                cur.execute(f'SET SCHEMA "{sch}"')
                cur.close()
            price_row = unit_price_by_policy(conn, doc_entry, item_code)
            if not price_row:
                return Response({'success': True, 'data': None, 'message': 'No price found for given DocEntry and ItemCode'}, status=status.HTTP_200_OK)
            price_val = price_row.get('U_frp') if isinstance(price_row, dict) else None
            try:
                price_val = float(price_val) if price_val is not None else price_val
            except Exception:
                pass
            return Response({'success': True, 'data': {'doc_entry': doc_entry, 'item_code': item_code, 'unit_price': price_val}}, status=status.HTTP_200_OK)
        finally:
            try:
                conn.close()
            except Exception:
                pass
    except Exception as e:
        return Response({'success': False, 'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@swagger_auto_schema(tags=['SAP Sales Order Form'],
    method='get',
    operation_summary="Policy Items (LOV)",
    operation_description="""Get all items in a specific policy. Use this when policy is selected to populate item dropdown in sales order form.
    
    **Response Structure:**
    ```json
    {
        "success": true,
        "page": 1,
        "page_size": 10,
        "num_pages": 1,
        "count": 1,
        "data": [
            {
                "POLICY_DOC_ENTRY": 37,
                "ITEMCODE": "FG00319",
                "ItemName": "Dhamaka 0.4G - 4Kg",
                "UNIT_PRICE": -1.0,
                "UNIT_OF_MEASURE": "No"
            }
        ]
    }
    ```
    
    **Usage in Form:**
    - Use ITEMCODE as dropdown value
    - Display "ITEMCODE - ItemName" in dropdown
    - Auto-fill ItemName to description field
    - Auto-fill UNIT_OF_MEASURE to measure_unit field
    - Use UNIT_PRICE or fetch via item-price endpoint for accurate pricing
    
    **Note:** If ITEMCODE is null, the policy has no items configured.
    """,
    manual_parameters=[
        openapi.Parameter(
            'database',
            openapi.IN_QUERY,
            description="HANA database/schema to query. Accepts Company name values (e.g., 4B-BIO_APP, 4B-ORANG_APP) or company keys (e.g., 4B-BIO, 4B-ORANG). If not provided, falls back to session or first active company.",
            type=openapi.TYPE_STRING,
            required=False
        ),
        openapi.Parameter('doc_entry', openapi.IN_QUERY, description="Policy DocEntry (required, e.g., 37)", type=openapi.TYPE_STRING, required=True),
        openapi.Parameter('card_code', openapi.IN_QUERY, description="Business Partner CardCode (optional, for future filtering)", type=openapi.TYPE_STRING, required=False),
        openapi.Parameter('page', openapi.IN_QUERY, description="Page number (default 1)", type=openapi.TYPE_INTEGER, required=False),
        openapi.Parameter('page_size', openapi.IN_QUERY, description="Items per page (default 10)", type=openapi.TYPE_INTEGER, required=False),
    ],
    responses={200: openapi.Response(description="OK"), 400: openapi.Response(description="Bad Request - missing doc_entry"), 500: openapi.Response(description="Server Error")}
)
@api_view(['GET'])
def policy_items_for_customer_api(request):
    """
    Get all items in a specific policy, optionally filtered by customer CardCode.
    Query parameters:
        - database: Company database schema (accepts variants like 4B-ORANG, 4B-ORANG_APP, etc.)
        - doc_entry: Policy DocEntry (required)
        - card_code: Business Partner CardCode (optional)
        - page: Page number (optional)
        - page_size: Items per page (optional)
    """
    try:
        _hana_load_env_file(os.path.join(os.path.dirname(__file__), '.env'))
        _hana_load_env_file(os.path.join(str(settings.BASE_DIR), '.env'))
        _hana_load_env_file(os.path.join(str(Path(settings.BASE_DIR).parent), '.env'))
        _hana_load_env_file(os.path.join(os.getcwd(), '.env'))
    except Exception:
        pass

    cfg = {
        'host': os.environ.get('HANA_HOST') or '',
        'port': os.environ.get('HANA_PORT') or '30015',
        'user': os.environ.get('HANA_USER') or '',
        'schema': os.environ.get('HANA_SCHEMA') or '4B-BIO_APP',
        'encrypt': os.environ.get('HANA_ENCRYPT') or '',
        'ssl_validate': os.environ.get('HANA_SSL_VALIDATE') or '',
    }

    # Resolve HANA schema using shared helper
    hana_schema = get_hana_schema_from_request(request)
    cfg['schema'] = hana_schema
    
    logger.info(f"[POLICY_ITEMS] Using HANA schema: {hana_schema}")

    doc_entry = (request.GET.get('doc_entry') or '').strip()
    card_code = (request.GET.get('card_code') or '').strip()

    if not doc_entry:
        return Response({'success': False, 'error': 'doc_entry parameter is required'}, status=status.HTTP_400_BAD_REQUEST)

    page_param = (request.GET.get('page') or '1').strip()
    page_size_param = (request.GET.get('page_size') or '').strip()
    try:
        page_num = int(page_param) if page_param else 1
    except Exception:
        page_num = 1
    default_page_size = 50
    try:
        default_page_size = int(getattr(settings, 'REST_FRAMEWORK', {}).get('PAGE_SIZE', 50) or 50)
    except Exception:
        default_page_size = 50
    try:
        page_size = int(page_size_param) if page_size_param else default_page_size
    except Exception:
        page_size = default_page_size

    try:
        from hdbcli import dbapi
        pwd = os.environ.get('HANA_PASSWORD', '')
        kwargs = {
            'address': cfg['host'],
            'port': int(cfg['port']),
            'user': cfg['user'] or '',
            'password': pwd or ''
        }
        if str(cfg['encrypt']).strip().lower() in ('true', '1', 'yes'):
            kwargs['encrypt'] = True
            if cfg['ssl_validate']:
                kwargs['sslValidateCertificate'] = (str(cfg['ssl_validate']).strip().lower() in ('true', '1', 'yes'))

        conn = dbapi.connect(**kwargs)
        try:
            if cfg['schema']:
                sch = cfg['schema']
                cur = conn.cursor()
                cur.execute(f'SET SCHEMA "{sch}"')
                cur.close()

            cursor = conn.cursor()
            
            # Query to get policy items with optional customer filter
            # @PLR4 uses U_itc for ItemCode, U_frp for price
            # Join with OITM for item details
            if card_code:
                sql_query = """
                    SELECT 
                        h."DocEntry" AS policy_doc_entry,
                        l."U_itc" AS ItemCode,
                        i."ItemName",
                        l."U_frp" AS unit_price,
                        i."SalUnitMsr" AS unit_of_measure,
                        r."U_bp" AS bp_code
                    FROM "@PL1" h
                    INNER JOIN "@PLR4" l ON h."DocEntry" = l."DocEntry"
                    INNER JOIN "@PLR8" r ON h."DocEntry" = r."DocEntry"
                    LEFT JOIN OITM i ON i."ItemCode" = l."U_itc"
                    WHERE h."DocEntry" = ?
                    AND r."U_bp" = ?
                    ORDER BY l."U_itc"
                """
                params = [doc_entry, card_code]
            else:
                sql_query = """
                    SELECT 
                        h."DocEntry" AS policy_doc_entry,
                        l."U_itc" AS ItemCode,
                        i."ItemName",
                        l."U_frp" AS unit_price,
                        i."SalUnitMsr" AS unit_of_measure
                    FROM "@PL1" h
                    INNER JOIN "@PLR4" l ON h."DocEntry" = l."DocEntry"
                    LEFT JOIN OITM i ON i."ItemCode" = l."U_itc"
                    WHERE h."DocEntry" = ?
                    ORDER BY l."U_itc"
                """
                params = [doc_entry]
            
            cursor.execute(sql_query, params)
            columns = [desc[0] for desc in cursor.description]
            rows = cursor.fetchall()
            cursor.close()

            # Convert rows to list of dicts
            data = []
            for row in rows:
                item_dict = {}
                for idx, col in enumerate(columns):
                    val = row[idx]
                    # Convert date/datetime to string
                    if hasattr(val, 'isoformat'):
                        val = val.isoformat()
                    item_dict[col] = val
                data.append(item_dict)

            # Check if no records found
            if not data:
                return Response({
                    'success': True,
                    'message': 'No items found for the specified policy and customer',
                    'page': 1,
                    'page_size': page_size,
                    'num_pages': 0,
                    'count': 0,
                    'data': []
                }, status=status.HTTP_200_OK)

            # Paginate results
            from django.core.paginator import Paginator
            paginator = Paginator(data, page_size)
            page_obj = paginator.get_page(page_num)

            return Response({
                'success': True,
                'page': page_obj.number,
                'page_size': page_size,
                'num_pages': paginator.num_pages,
                'count': paginator.count,
                'data': list(page_obj.object_list)
            }, status=status.HTTP_200_OK)

        finally:
            try:
                conn.close()
            except Exception:
                pass
    except Exception as e:
        return Response({'success': False, 'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@swagger_auto_schema(tags=['SAP'],
    method='get',
    operation_summary="Policy Project Link",
    operation_description="Get projects linked to policies for a specific Business Partner/Customer. Shows policy-project relationships with project details.",
    manual_parameters=[
        openapi.Parameter(
            'database',
            openapi.IN_QUERY,
            description="HANA database/schema to query. Accepts Company name values (e.g., 4B-BIO_APP, 4B-ORANG_APP) or company keys (e.g., 4B-BIO, 4B-ORANG). If not provided, falls back to session or first active company.",
            type=openapi.TYPE_STRING,
            required=False
        ),
        openapi.Parameter('card_code', openapi.IN_QUERY, description="Business Partner CardCode (required)", type=openapi.TYPE_STRING, required=True),
        openapi.Parameter('page', openapi.IN_QUERY, description="Page number", type=openapi.TYPE_INTEGER, required=False),
        openapi.Parameter('page_size', openapi.IN_QUERY, description="Items per page", type=openapi.TYPE_INTEGER, required=False),
    ],
    responses={200: openapi.Response(description="OK"), 400: openapi.Response(description="Bad Request"), 500: openapi.Response(description="Server Error")}
)
@api_view(['GET'])
def policy_project_link_api(request):
    """
    Get projects linked to policies for a specific customer.
    
    SQL Query:
    SELECT T1."DocEntry", T1."U_proj", T2."PrjName"
    FROM "@PLR8" T0
    INNER JOIN "@PL1" T1 ON T0."DocEntry" = T1."DocEntry"
    INNER JOIN OPRJ T2 ON T2."PrjCode" = T1."U_proj"
    WHERE T0."U_bp" = ?
    AND T2."Active" = 'Y'
    AND T2."ValidTo" >= CURRENT_DATE
    """
    try:
        _hana_load_env_file(os.path.join(os.path.dirname(__file__), '.env'))
        _hana_load_env_file(os.path.join(str(settings.BASE_DIR), '.env'))
        _hana_load_env_file(os.path.join(str(Path(settings.BASE_DIR).parent), '.env'))
        _hana_load_env_file(os.path.join(os.getcwd(), '.env'))
    except Exception:
        pass

    cfg = {
        'host': os.environ.get('HANA_HOST') or '',
        'port': os.environ.get('HANA_PORT') or '30015',
        'user': os.environ.get('HANA_USER') or '',
        'schema': os.environ.get('HANA_SCHEMA') or '4B-BIO_APP',
        'encrypt': os.environ.get('HANA_ENCRYPT') or '',
        'ssl_validate': os.environ.get('HANA_SSL_VALIDATE') or '',
    }

    # Resolve HANA schema using shared helper for consistency across endpoints
    hana_schema = get_hana_schema_from_request(request)
    cfg['schema'] = hana_schema

    card_code = (request.GET.get('card_code') or '').strip()
    
    if not card_code:
        return Response({'success': False, 'error': 'card_code parameter is required'}, status=status.HTTP_400_BAD_REQUEST)

    page_param = (request.GET.get('page') or '1').strip()
    page_size_param = (request.GET.get('page_size') or '').strip()
    try:
        page_num = int(page_param) if page_param else 1
    except Exception:
        page_num = 1
    default_page_size = 50
    try:
        default_page_size = int(getattr(settings, 'REST_FRAMEWORK', {}).get('PAGE_SIZE', 50) or 50)
    except Exception:
        default_page_size = 50
    try:
        page_size = int(page_size_param) if page_size_param else default_page_size
    except Exception:
        page_size = default_page_size

    try:
        from hdbcli import dbapi
        pwd = os.environ.get('HANA_PASSWORD', '')
        kwargs = {
            'address': cfg['host'],
            'port': int(cfg['port']),
            'user': cfg['user'] or '',
            'password': pwd or ''
        }
        if str(cfg['encrypt']).strip().lower() in ('true', '1', 'yes'):
            kwargs['encrypt'] = True
            if cfg['ssl_validate']:
                kwargs['sslValidateCertificate'] = (str(cfg['ssl_validate']).strip().lower() in ('true', '1', 'yes'))

        conn = dbapi.connect(**kwargs)
        try:
            if cfg['schema']:
                sch = cfg['schema']
                cur = conn.cursor()
                cur.execute(f'SET SCHEMA "{sch}"')
                cur.close()

            cursor = conn.cursor()
            
            # Query to get policy-project links for a specific Business Partner
            sql_query = """
                SELECT 
                    T1."DocEntry" AS policy_doc_entry,
                    T1."U_proj" AS project_code,
                    T2."PrjName" AS project_name,
                    T2."Active" AS project_active,
                    T2."ValidTo" AS project_valid_to,
                    T0."U_bp" AS bp_code
                FROM "@PLR8" T0
                INNER JOIN "@PL1" T1 ON T0."DocEntry" = T1."DocEntry"
                INNER JOIN OPRJ T2 ON T2."PrjCode" = T1."U_proj"
                WHERE T0."U_bp" = ?
                AND T2."Active" = 'Y'
                AND T2."ValidTo" >= CURRENT_DATE
                ORDER BY T1."DocEntry", T2."PrjCode"
            """
            
            cursor.execute(sql_query, [card_code])
            columns = [desc[0] for desc in cursor.description]
            rows = cursor.fetchall()
            cursor.close()

            # Convert rows to list of dicts
            data = []
            for row in rows:
                item_dict = {}
                for idx, col in enumerate(columns):
                    val = row[idx]
                    # Convert date/datetime to string
                    if hasattr(val, 'isoformat'):
                        val = val.isoformat()
                    item_dict[col] = val
                data.append(item_dict)

            # Paginate results
            from django.core.paginator import Paginator
            paginator = Paginator(data, page_size)
            page_obj = paginator.get_page(page_num)

            return Response({
                'success': True,
                'page': page_obj.number,
                'page_size': page_size,
                'num_pages': paginator.num_pages,
                'count': paginator.count,
                'data': list(page_obj.object_list)
            }, status=status.HTTP_200_OK)

        finally:
            try:
                conn.close()
            except Exception:
                pass
    except Exception as e:
        return Response({'success': False, 'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@swagger_auto_schema(tags=['SAP'], 
    method='get',
    operation_summary="Projects LOV",
    operation_description="List projects with optional search and pagination.",
    manual_parameters=[
        openapi.Parameter('search', openapi.IN_QUERY, description="Search ProjectCode or ProjectName", type=openapi.TYPE_STRING, required=False),
        openapi.Parameter('page', openapi.IN_QUERY, description="Page number", type=openapi.TYPE_INTEGER, required=False),
        openapi.Parameter('page_size', openapi.IN_QUERY, description="Items per page", type=openapi.TYPE_INTEGER, required=False),
    ],
    responses={200: openapi.Response(description="OK"), 500: openapi.Response(description="Server Error")}
)
@api_view(['GET'])
def projects_lov_api(request):
    try:
        _hana_load_env_file(os.path.join(os.path.dirname(__file__), '.env'))
        _hana_load_env_file(os.path.join(str(settings.BASE_DIR), '.env'))
        _hana_load_env_file(os.path.join(str(Path(settings.BASE_DIR).parent), '.env'))
        _hana_load_env_file(os.path.join(os.getcwd(), '.env'))
    except Exception:
        pass
    cfg = {
        'host': os.environ.get('HANA_HOST') or '',
        'port': os.environ.get('HANA_PORT') or '30015',
        'user': os.environ.get('HANA_USER') or '',
        'schema': os.environ.get('HANA_SCHEMA') or '4B-BIO_APP',
        'encrypt': os.environ.get('HANA_ENCRYPT') or '',
        'ssl_validate': os.environ.get('HANA_SSL_VALIDATE') or '',
    }
    # Handle database parameter
    db_param = (request.GET.get('database') or '').strip()
    if db_param:
        norm = db_param.strip().upper().replace('-APP', '_APP')
        if '4B-BIO' in norm:
            cfg['schema'] = '4B-BIO_APP'
        elif '4B-ORANG' in norm:
            cfg['schema'] = '4B-ORANG_APP'
        else:
            cfg['schema'] = db_param
    
    search = (request.GET.get('search') or '').strip()
    page_param = (request.GET.get('page') or '1').strip()
    page_size_param = (request.GET.get('page_size') or '').strip()
    try:
        page_num = int(page_param) if page_param else 1
    except Exception:
        page_num = 1
    default_page_size = 10
    try:
        default_page_size = int(getattr(settings, 'REST_FRAMEWORK', {}).get('PAGE_SIZE', 10) or 10)
    except Exception:
        default_page_size = 10
    try:
        page_size = int(page_size_param) if page_size_param else default_page_size
    except Exception:
        page_size = default_page_size
    try:
        from hdbcli import dbapi
        pwd = os.environ.get('HANA_PASSWORD','')
        kwargs = {'address': cfg['host'], 'port': int(cfg['port']), 'user': cfg['user'] or '', 'password': pwd or ''}
        if str(cfg['encrypt']).strip().lower() in ('true','1','yes'):
            kwargs['encrypt'] = True
            if cfg['ssl_validate']:
                kwargs['sslValidateCertificate'] = (str(cfg['ssl_validate']).strip().lower() in ('true','1','yes'))
        conn = dbapi.connect(**kwargs)
        try:
            if cfg['schema']:
                sch = cfg['schema']
                cur = conn.cursor()
                cur.execute(f'SET SCHEMA "{sch}"')
                cur.close()
            from .hana_connect import projects_lov
            data = projects_lov(conn, search or None)
            paginator = Paginator(data or [], page_size)
            page_obj = paginator.get_page(page_num)
            return Response({'success': True, 'page': page_obj.number, 'page_size': page_size, 'num_pages': paginator.num_pages, 'count': paginator.count, 'data': list(page_obj.object_list)}, status=status.HTTP_200_OK)
        finally:
            try:
                conn.close()
            except Exception:
                pass
    except Exception as e:
        return Response({'success': False, 'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@swagger_auto_schema(tags=['SAP'], 
    method='get',
    operation_summary="Crop LOV",
    operation_description="List crops with optional search and pagination.",
    manual_parameters=[
        openapi.Parameter('database', openapi.IN_QUERY, description="Database/schema", type=openapi.TYPE_STRING, enum=['4B-BIO-app', '4B-ORANG-app'], required=False),
        openapi.Parameter('search', openapi.IN_QUERY, description="Search Code or Name", type=openapi.TYPE_STRING, required=False),
        openapi.Parameter('page', openapi.IN_QUERY, description="Page number", type=openapi.TYPE_INTEGER, required=False),
        openapi.Parameter('page_size', openapi.IN_QUERY, description="Items per page", type=openapi.TYPE_INTEGER, required=False),
    ],
    responses={200: openapi.Response(description="OK"), 500: openapi.Response(description="Server Error")}
)
@api_view(['GET'])
def crop_lov_api(request):
    try:
        _hana_load_env_file(os.path.join(os.path.dirname(__file__), '.env'))
        _hana_load_env_file(os.path.join(str(settings.BASE_DIR), '.env'))
        _hana_load_env_file(os.path.join(str(Path(settings.BASE_DIR).parent), '.env'))
        _hana_load_env_file(os.path.join(os.getcwd(), '.env'))
    except Exception:
        pass
    cfg = {
        'host': os.environ.get('HANA_HOST') or '',
        'port': os.environ.get('HANA_PORT') or '30015',
        'user': os.environ.get('HANA_USER') or '',
        'schema': os.environ.get('HANA_SCHEMA') or '4B-BIO_APP',
        'encrypt': os.environ.get('HANA_ENCRYPT') or '',
        'ssl_validate': os.environ.get('HANA_SSL_VALIDATE') or '',
    }
    # Handle database parameter
    db_param = (request.GET.get('database') or '').strip()
    if db_param:
        norm = db_param.strip().upper().replace('-APP', '_APP')
        if '4B-BIO' in norm:
            cfg['schema'] = '4B-BIO_APP'
        elif '4B-ORANG' in norm:
            cfg['schema'] = '4B-ORANG_APP'
        else:
            cfg['schema'] = db_param
    
    search = (request.GET.get('search') or '').strip()
    page_param = (request.GET.get('page') or '1').strip()
    page_size_param = (request.GET.get('page_size') or '').strip()
    try:
        page_num = int(page_param) if page_param else 1
    except Exception:
        page_num = 1
    default_page_size = 10
    try:
        default_page_size = int(getattr(settings, 'REST_FRAMEWORK', {}).get('PAGE_SIZE', 10) or 10)
    except Exception:
        default_page_size = 10
    try:
        page_size = int(page_size_param) if page_size_param else default_page_size
    except Exception:
        page_size = default_page_size
    try:
        from hdbcli import dbapi
        pwd = os.environ.get('HANA_PASSWORD','')
        kwargs = {'address': cfg['host'], 'port': int(cfg['port']), 'user': cfg['user'] or '', 'password': pwd or ''}
        if str(cfg['encrypt']).strip().lower() in ('true','1','yes'):
            kwargs['encrypt'] = True
            if cfg['ssl_validate']:
                kwargs['sslValidateCertificate'] = (str(cfg['ssl_validate']).strip().lower() in ('true','1','yes'))
        conn = dbapi.connect(**kwargs)
        try:
            if cfg['schema']:
                sch = cfg['schema']
                cur = conn.cursor()
                cur.execute(f'SET SCHEMA "{sch}"')
                cur.close()
            from .hana_connect import crop_lov
            data = crop_lov(conn, search or None)
            paginator = Paginator(data or [], page_size)
            page_obj = paginator.get_page(page_num)
            return Response({'success': True, 'page': page_obj.number, 'page_size': page_size, 'num_pages': paginator.num_pages, 'count': paginator.count, 'data': list(page_obj.object_list)}, status=status.HTTP_200_OK)
        finally:
            try:
                conn.close()
            except Exception:
                pass
    except Exception as e:
        return Response({'success': False, 'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@swagger_auto_schema(tags=['SAP'], 
    method='get',
    operation_summary="Sales orders",
    operation_description="List sales orders with optional filters and pagination. Returns order header with customer contact, policies, and crops.",
    manual_parameters=[
        openapi.Parameter(
            'database',
            openapi.IN_QUERY,
            description="HANA database/schema to query. Accepts Company name values (e.g., 4B-BIO_APP, 4B-ORANG_APP) or company keys (e.g., 4B-BIO, 4B-ORANG). If not provided, falls back to session or first active company.",
            type=openapi.TYPE_STRING,
            required=False
        ),
        openapi.Parameter('card_code', openapi.IN_QUERY, description="Customer CardCode", type=openapi.TYPE_STRING, required=False),
        openapi.Parameter('doc_status', openapi.IN_QUERY, description="Document Status: O (Open) or C (Closed)", type=openapi.TYPE_STRING, required=False),
        openapi.Parameter('from_date', openapi.IN_QUERY, description="From date YYYY-MM-DD", type=openapi.TYPE_STRING, required=False),
        openapi.Parameter('to_date', openapi.IN_QUERY, description="To date YYYY-MM-DD", type=openapi.TYPE_STRING, required=False),
        openapi.Parameter('limit', openapi.IN_QUERY, description="Max records (default 100)", type=openapi.TYPE_INTEGER, required=False),
        openapi.Parameter('page', openapi.IN_QUERY, description="Page number", type=openapi.TYPE_INTEGER, required=False),
        openapi.Parameter('page_size', openapi.IN_QUERY, description="Items per page", type=openapi.TYPE_INTEGER, required=False),
    ],
    responses={200: openapi.Response(description="OK"), 500: openapi.Response(description="Server Error")}
)
@api_view(['GET'])
def sales_orders_api(request):
    try:
        _hana_load_env_file(os.path.join(os.path.dirname(__file__), '.env'))
        _hana_load_env_file(os.path.join(str(settings.BASE_DIR), '.env'))
        _hana_load_env_file(os.path.join(str(Path(settings.BASE_DIR).parent), '.env'))
        _hana_load_env_file(os.path.join(os.getcwd(), '.env'))
    except Exception:
        pass
    cfg = {
        'host': os.environ.get('HANA_HOST') or '',
        'port': os.environ.get('HANA_PORT') or '30015',
        'user': os.environ.get('HANA_USER') or '',
        'schema': os.environ.get('HANA_SCHEMA') or '4B-BIO_APP',
        'encrypt': os.environ.get('HANA_ENCRYPT') or '',
        'ssl_validate': os.environ.get('HANA_SSL_VALIDATE') or '',
    }
    
    # Resolve HANA schema using shared helper for consistency
    hana_schema = get_hana_schema_from_request(request)
    cfg['schema'] = hana_schema
    
    card_code = (request.GET.get('card_code') or '').strip()
    doc_status = (request.GET.get('doc_status') or '').strip().upper()
    from_date = (request.GET.get('from_date') or '').strip()
    to_date = (request.GET.get('to_date') or '').strip()
    limit_param = (request.GET.get('limit') or '').strip()
    page_param = (request.GET.get('page') or '1').strip()
    page_size_param = (request.GET.get('page_size') or '').strip()
    try:
        page_num = int(page_param) if page_param else 1
    except Exception:
        page_num = 1
    default_page_size = 10
    try:
        default_page_size = int(getattr(settings, 'REST_FRAMEWORK', {}).get('PAGE_SIZE', 10) or 10)
    except Exception:
        default_page_size = 10
    try:
        page_size = int(page_size_param) if page_size_param else default_page_size
    except Exception:
        page_size = default_page_size
    try:
        from hdbcli import dbapi
        pwd = os.environ.get('HANA_PASSWORD','')
        kwargs = {'address': cfg['host'], 'port': int(cfg['port']), 'user': cfg['user'] or '', 'password': pwd or ''}
        if str(cfg['encrypt']).strip().lower() in ('true','1','yes'):
            kwargs['encrypt'] = True
            if cfg['ssl_validate']:
                kwargs['sslValidateCertificate'] = (str(cfg['ssl_validate']).strip().lower() in ('true','1','yes'))
        conn = dbapi.connect(**kwargs)
        try:
            if cfg['schema']:
                sch = cfg['schema']
                cur = conn.cursor()
                cur.execute(f'SET SCHEMA "{sch}"')
                cur.close()
            from .hana_connect import sales_orders_all
            limit_val = 100
            try:
                if limit_param:
                    limit_val = int(limit_param)
            except Exception:
                limit_val = 100
            if doc_status not in ('O','C',''):
                doc_status = ''
            data = sales_orders_all(conn, limit=limit_val, card_code=(card_code or None), doc_status=(doc_status or None), from_date=(from_date or None), to_date=(to_date or None))
            paginator = Paginator(data or [], page_size)
            page_obj = paginator.get_page(page_num)
            return Response({'success': True, 'page': page_obj.number, 'page_size': page_size, 'num_pages': paginator.num_pages, 'count': paginator.count, 'data': list(page_obj.object_list)}, status=status.HTTP_200_OK)
        finally:
            try:
                conn.close()
            except Exception:
                pass
    except Exception as e:
        return Response({'success': False, 'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)



@staff_member_required
def set_database(request):
    """Handle database selection from global selector."""
    from django.shortcuts import redirect
    from urllib.parse import urlparse, parse_qs, urlencode, urlunparse
    import logging
    logger = logging.getLogger(__name__)
    
    if request.method == 'POST':
        db_key = request.POST.get('database', '4B-BIO')
        request.session['selected_db'] = db_key
        request.session.modified = True  # Force session save
        
        logger.info(f"Database switched to: {db_key}")
        logger.info(f"Session key: {request.session.session_key}")
        logger.info(f"Session data: {dict(request.session.items())}")
        
        next_url = request.POST.get('next', request.META.get('HTTP_REFERER', '/admin/'))
        
        # Update the company_db parameter in the URL if it exists
        parsed = urlparse(next_url)
        query_params = parse_qs(parsed.query)
        
        # Update or add company_db parameter
        query_params['company_db'] = [db_key]
        
        # Rebuild the URL
        new_query = urlencode(query_params, doseq=True)
        new_url = urlunparse((
            parsed.scheme,
            parsed.netloc,
            parsed.path,
            parsed.params,
            new_query,
            parsed.fragment
        ))
        
        logger.info(f"Redirecting to: {new_url}")
        
        return redirect(new_url)
    return redirect('/admin/')


@swagger_auto_schema(tags=['SAP Sales Order Form'],
    method='get',
    operation_summary="Customer Policies",
    operation_description="""Get all policies linked to a specific customer. Use this when customer is selected to populate policy dropdown in sales order form.
    
    **Response Structure:**
    ```json
    {
        "success": true,
        "page": 1,
        "page_size": 10,
        "num_pages": 1,
        "count": 3,
        "data": [
            {
                "POLICY_DOC_ENTRY": 27,
                "PROJECT_CODE": "0323040",
                "PROJECT_NAME": "Orange Protection Policy",
                "CUSTOMER_CODE": "ORC00004"
            }
        ]
    }
    ```
    
    **Usage in Form:**
    - Use POLICY_DOC_ENTRY as the key identifier
    - Display PROJECT_NAME (DocEntry: POLICY_DOC_ENTRY) in dropdown
    - Pass POLICY_DOC_ENTRY to policy-items-lov endpoint to get items
    """,
    manual_parameters=[
        openapi.Parameter(
            'database',
            openapi.IN_QUERY,
            description="HANA database/schema to query. Accepts Company name values (e.g., 4B-BIO_APP, 4B-ORANG_APP) or company keys (e.g., 4B-BIO, 4B-ORANG). If not provided, falls back to session or first active company.",
            type=openapi.TYPE_STRING,
            required=False
        ),
        openapi.Parameter('card_code', openapi.IN_QUERY, description="Customer CardCode (required, e.g., ORC00001)", type=openapi.TYPE_STRING, required=True),
        openapi.Parameter('page', openapi.IN_QUERY, description="Page number (default 1)", type=openapi.TYPE_INTEGER, required=False),
        openapi.Parameter('page_size', openapi.IN_QUERY, description="Items per page (default 10)", type=openapi.TYPE_INTEGER, required=False),
    ],
    responses={200: openapi.Response(description="OK"), 400: openapi.Response(description="Bad Request - missing card_code"), 500: openapi.Response(description="Server Error")}
)
@api_view(['GET'])
def customer_policies_api(request):
    """
    Get all policies for a specific customer from @PLR8 and @PL1 tables.
    Returns DocEntry and project code (U_proj) for each policy.
    
    Example: /api/sap/customer-policies/?card_code=ORC00001&database=4B-ORANG
    """
    try:
        _hana_load_env_file(os.path.join(os.path.dirname(__file__), '.env'))
        _hana_load_env_file(os.path.join(str(settings.BASE_DIR), '.env'))
        _hana_load_env_file(os.path.join(str(Path(settings.BASE_DIR).parent), '.env'))
        _hana_load_env_file(os.path.join(os.getcwd(), '.env'))
    except Exception:
        pass

    cfg = {
        'host': os.environ.get('HANA_HOST') or '',
        'port': os.environ.get('HANA_PORT') or '30015',
        'user': os.environ.get('HANA_USER') or '',
        'schema': os.environ.get('HANA_SCHEMA') or '4B-BIO_APP',
        'encrypt': os.environ.get('HANA_ENCRYPT') or '',
        'ssl_validate': os.environ.get('HANA_SSL_VALIDATE') or '',
    }

    # Resolve HANA schema using shared helper
    hana_schema = get_hana_schema_from_request(request)
    cfg['schema'] = hana_schema
    
    logger.info(f"[CUSTOMER_POLICIES] Using HANA schema: {hana_schema}")

    card_code = (request.GET.get('card_code') or '').strip()
    
    if not card_code:
        return Response({'success': False, 'error': 'card_code parameter is required'}, status=status.HTTP_400_BAD_REQUEST)

    page_param = (request.GET.get('page') or '1').strip()
    page_size_param = (request.GET.get('page_size') or '').strip()
    try:
        page_num = int(page_param) if page_param else 1
    except Exception:
        page_num = 1
    default_page_size = 50
    try:
        default_page_size = int(getattr(settings, 'REST_FRAMEWORK', {}).get('PAGE_SIZE', 50) or 50)
    except Exception:
        default_page_size = 50
    try:
        page_size = int(page_size_param) if page_size_param else default_page_size
    except Exception:
        page_size = default_page_size

    try:
        from hdbcli import dbapi
        pwd = os.environ.get('HANA_PASSWORD', '')
        kwargs = {
            'address': cfg['host'],
            'port': int(cfg['port']),
            'user': cfg['user'] or '',
            'password': pwd or ''
        }
        if str(cfg['encrypt']).strip().lower() in ('true', '1', 'yes'):
            kwargs['encrypt'] = True
            if cfg['ssl_validate']:
                kwargs['sslValidateCertificate'] = (str(cfg['ssl_validate']).strip().lower() in ('true', '1', 'yes'))

        conn = dbapi.connect(**kwargs)
        try:
            if cfg['schema']:
                sch = cfg['schema']
                cur = conn.cursor()
                cur.execute(f'SET SCHEMA "{sch}"')
                cur.close()

            cursor = conn.cursor()
            
            # Query to get all policies linked to a customer
            sql_query = """
                SELECT DISTINCT
                    T1."DocEntry" AS policy_doc_entry,
                    T1."U_proj" AS project_code,
                    T2."PrjName" AS project_name,
                    T0."U_bp" AS customer_code
                FROM "@PLR8" T0
                INNER JOIN "@PL1" T1 ON T0."DocEntry" = T1."DocEntry"
                LEFT JOIN OPRJ T2 ON T2."PrjCode" = T1."U_proj"
                WHERE T0."U_bp" = ?
                ORDER BY T1."DocEntry"
            """
            
            logger.info(f"[CUSTOMER_POLICIES] Querying policies for CardCode: {card_code}")
            
            cursor.execute(sql_query, [card_code])
            columns = [desc[0] for desc in cursor.description]
            rows = cursor.fetchall()
            cursor.close()

            # Convert rows to list of dicts
            data = []
            for row in rows:
                item_dict = {}
                for idx, col in enumerate(columns):
                    val = row[idx]
                    # Convert date/datetime to string
                    if hasattr(val, 'isoformat'):
                        val = val.isoformat()
                    item_dict[col] = val
                data.append(item_dict)

            logger.info(f"[CUSTOMER_POLICIES] Found {len(data)} policies for {card_code}")

            # Check if no records found
            if not data:
                return Response({
                    'success': True,
                    'message': f'No policies found for customer {card_code}',
                    'page': 1,
                    'page_size': page_size,
                    'num_pages': 0,
                    'count': 0,
                    'data': []
                }, status=status.HTTP_200_OK)

            # Paginate results
            from django.core.paginator import Paginator
            paginator = Paginator(data, page_size)
            page_obj = paginator.get_page(page_num)

            return Response({
                'success': True,
                'page': page_obj.number,
                'page_size': page_size,
                'num_pages': paginator.num_pages,
                'count': paginator.count,
                'data': list(page_obj.object_list)
            }, status=status.HTTP_200_OK)

        finally:
            try:
                conn.close()
            except Exception:
                pass
    except Exception as e:
        logger.error(f"[CUSTOMER_POLICIES] Error: {str(e)}")
        return Response({'success': False, 'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

