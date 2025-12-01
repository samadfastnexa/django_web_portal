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
from .hana_connect import _load_env_file as _hana_load_env_file, territory_summary, products_catalog, policy_customer_balance, policy_customer_balance_all, sales_vs_achievement, territory_names, territories_all, territories_all_full, cwl_all_full, table_columns
from django.conf import settings
from pathlib import Path
import sys
from django.utils.safestring import mark_safe

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
                                request._territory_options = territory_options
                        except Exception as e_ts:
                            error = str(e_ts)
                    elif action == 'products_catalog':
                        try:
                            data = products_catalog(conn)
                            result = data
                        except Exception as e_pc:
                            error = str(e_pc)
                    elif action == 'list_territories':
                        try:
                            data = territories_all(conn)
                            result = data
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
                                request._territory_options = territory_options
                        except Exception as e_sa:
                            error = str(e_sa)
                finally:
                    try:
                        conn.close()
                    except Exception:
                        pass
        except Exception as e:
            error = _sanitize_error(e)
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
    result_rows = result if isinstance(result, list) else []
    result_cols = []
    if isinstance(result_rows, list) and len(result_rows) > 0 and isinstance(result_rows[0], dict):
        try:
            result_cols = list(result_rows[0].keys())
        except Exception:
            result_cols = []
    table_rows = []
    if result_cols:
        for row in result_rows:
            if isinstance(row, dict):
                values = []
                for c in result_cols:
                    values.append(row.get(c))
                table_rows.append(values)
    return render(
        request,
        'admin/sap_integration/hana_connect.html',
        {
            'result_json': result_json,
            'error': error,
            'diagnostics_json': diag_json,
            'territory_options': territory_options,
            'selected_territory': selected_territory,
            'current_action': action,
            'current_emp_id': current_emp_id,
            'current_year': current_year,
            'current_month': current_month,
            'current_start_date': current_start_date,
            'current_end_date': current_end_date,
            'months': [],
            'result_rows': result_rows,
            'result_cols': result_cols,
            'table_rows': table_rows,
            'is_tabular': (action in ('territory_summary','sales_vs_achievement','policy_customer_balance','list_territories','list_territories_full','list_cwl')),
            'current_card_code': (request.GET.get('card_code') or '').strip(),
            'db_options': db_options,
            'selected_db_key': selected_db_key,
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
                
                client = SAPClient()
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
            client = SAPClient()
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


# Unified API for Frontend
@swagger_auto_schema(
    method='get',
    operation_description="Get Business Partner data by CardCode - Unified API for Frontend",
    manual_parameters=[
        openapi.Parameter(
            'card_code',
            openapi.IN_PATH,
            description="Business Partner Card Code (e.g., BIC00001)",
            type=openapi.TYPE_STRING,
            required=True
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
        400: openapi.Response(
            description="Invalid card code",
            examples={
                "application/json": {
                    "success": False,
                    "error": "Invalid card code format",
                    "message": "Card code is required"
                }
            }
        ),
        404: openapi.Response(
            description="Business partner not found",
            examples={
                "application/json": {
                    "success": False,
                    "error": "Business partner not found",
                    "message": "No business partner found with the provided card code"
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
def get_business_partner_data(request, card_code):
    """
    Unified API endpoint for frontend to get business partner data.
    This endpoint handles all SAP integration internally and returns clean data.
    
    Usage: GET /api/sap/business-partner/{card_code}/
    Example: GET /api/sap/business-partner/BIC00001/
    """
    
    # Validate card_code
    if not card_code or not card_code.strip():
        return Response({
            "success": False,
            "error": "Invalid card code format",
            "message": "Card code is required"
        }, status=status.HTTP_400_BAD_REQUEST)
    try:
        # Initialize SAP client
        sap_client = SAPClient()
        
        # Get business partner details with specific fields
        bp_data = sap_client.get_bp_details(card_code.strip())
        
        # Return formatted response for frontend
        return Response({
            "success": True,
            "data": bp_data,
            "message": "Business partner data retrieved successfully"
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

# List endpoint for Business Partners when no CardCode is provided
@swagger_auto_schema(
    method='get',
    operation_description="List Business Partners (omit CardCode)",
    manual_parameters=[
        openapi.Parameter(
            'top',
            openapi.IN_QUERY,
            description="Max items to return (default 100)",
            type=openapi.TYPE_INTEGER,
            required=False
        )
    ]
)
@api_view(['GET'])
def get_business_partners_list(request):
    try:
        sap_client = SAPClient()
        top_param = request.query_params.get('top')
        top_val = 100
        if top_param is not None:
            try:
                top_val = int(top_param)
            except Exception:
                top_val = 100
        rows = sap_client.list_business_partners(top=top_val, select='CardCode,CardName,GroupCode,VatGroup') or []
        return Response({
            "success": True,
            "count": len(rows),
            "data": rows,
            "message": "Business partners retrieved successfully"
        }, status=status.HTTP_200_OK)
    except Exception as e:
        return Response({
            "success": False,
            "error": "SAP integration failed",
            "message": str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@swagger_auto_schema(
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
        sap_client = SAPClient()
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
@swagger_auto_schema(
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
@swagger_auto_schema(
    method='post',
    operation_description="Sync policies from SAP Projects (UDF U_pol) into the database.",
    responses={
        200: openapi.Response(description="Sync completed")
    }
)
@api_view(['POST'])
def sync_policies(request):
    client = SAPClient()
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

@swagger_auto_schema(
    method='get',
    operation_description="Sales vs Achievement data",
    manual_parameters=[
        openapi.Parameter('start_date', openapi.IN_QUERY, description="Start date YYYY-MM-DD", type=openapi.TYPE_STRING),
        openapi.Parameter('end_date', openapi.IN_QUERY, description="End date YYYY-MM-DD", type=openapi.TYPE_STRING),
        openapi.Parameter('territory', openapi.IN_QUERY, description="Territory name", type=openapi.TYPE_STRING),
        openapi.Parameter('emp_id', openapi.IN_QUERY, description="Employee ID", type=openapi.TYPE_INTEGER),
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
        'schema': os.environ.get('HANA_SCHEMA') or '',
        'encrypt': os.environ.get('HANA_ENCRYPT') or '',
        'ssl_validate': os.environ.get('HANA_SSL_VALIDATE') or '',
    }
    start_date = (request.query_params.get('start_date') or '').strip()
    end_date = (request.query_params.get('end_date') or '').strip()
    territory = (request.query_params.get('territory') or '').strip()
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
            data = sales_vs_achievement(conn, emp_id, territory or None, None, None, start_date or None, end_date or None)
            return Response({'success': True, 'count': len(data or []), 'data': data}, status=status.HTTP_200_OK)
        finally:
            try:
                conn.close()
            except Exception:
                pass
    except Exception as e:
        return Response({'success': False, 'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@swagger_auto_schema(
    method='get',
    operation_description="Territory summary data",
    manual_parameters=[
        openapi.Parameter('start_date', openapi.IN_QUERY, description="Start date YYYY-MM-DD", type=openapi.TYPE_STRING),
        openapi.Parameter('end_date', openapi.IN_QUERY, description="End date YYYY-MM-DD", type=openapi.TYPE_STRING),
        openapi.Parameter('territory', openapi.IN_QUERY, description="Territory name", type=openapi.TYPE_STRING),
        openapi.Parameter('emp_id', openapi.IN_QUERY, description="Employee ID", type=openapi.TYPE_INTEGER),
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
        'schema': os.environ.get('HANA_SCHEMA') or '',
        'encrypt': os.environ.get('HANA_ENCRYPT') or '',
        'ssl_validate': os.environ.get('HANA_SSL_VALIDATE') or '',
    }
    start_date = (request.query_params.get('start_date') or '').strip()
    end_date = (request.query_params.get('end_date') or '').strip()
    territory = (request.query_params.get('territory') or '').strip()
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
            data = territory_summary(conn, emp_id, territory or None, None, None, start_date or None, end_date or None)
            return Response({'success': True, 'count': len(data or []), 'data': data}, status=status.HTTP_200_OK)
        finally:
            try:
                conn.close()
            except Exception:
                pass
    except Exception as e:
        return Response({'success': False, 'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@swagger_auto_schema(
    method='get',
    operation_description="Products catalog",
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
            data = products_catalog(conn)
            return Response({'success': True, 'count': len(data or []), 'data': data}, status=status.HTTP_200_OK)
        finally:
            try:
                conn.close()
            except Exception:
                pass
    except Exception as e:
        return Response({'success': False, 'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@swagger_auto_schema(
    method='get',
    operation_description="Policy customer balance",
    manual_parameters=[openapi.Parameter('card_code', openapi.IN_QUERY, description="BP CardCode", type=openapi.TYPE_STRING)],
    responses={200: openapi.Response(description="OK"), 400: openapi.Response(description="Bad Request"), 500: openapi.Response(description="Server Error")}
)
@api_view(['GET'])
def policy_customer_balance_api(request):
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
    card_code = (request.query_params.get('card_code') or '').strip()
    if not card_code:
        return Response({'success': False, 'error': 'card_code is required'}, status=status.HTTP_400_BAD_REQUEST)
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
            data = policy_customer_balance(conn, card_code)
            return Response({'success': True, 'count': len(data or []), 'data': data}, status=status.HTTP_200_OK)
        finally:
            try:
                conn.close()
            except Exception:
                pass
    except Exception as e:
        return Response({'success': False, 'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@swagger_auto_schema(
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

@swagger_auto_schema(
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

@swagger_auto_schema(
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
