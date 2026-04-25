from rest_framework.response import Response
from rest_framework import status
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from rest_framework.decorators import api_view

from .sap_client import SAPClient
from .models import Policy, DiseaseIdentification, RecommendedProduct
from .serializers import (
    PolicySerializer, 
    DiseaseIdentificationSerializer,
    DiseaseIdentificationListSerializer,
    RecommendedProductSerializer
)
from pathlib import Path
from django.views.decorators.csrf import ensure_csrf_cookie
from django.shortcuts import render
from django.contrib.admin.views.decorators import staff_member_required
from django.http import JsonResponse, FileResponse, HttpResponse
from django.db import models
from django.db.models import Q
import os
import json
import re
import logging
import mimetypes
from .hana_connect import _load_env_file as _hana_load_env_file, territory_summary, products_catalog, policy_customer_balance, policy_customer_balance_all, sales_vs_achievement, territory_names, territories_all, territories_all_full, cwl_all_full, table_columns, sales_orders_all, customer_lov, customer_addresses, contact_person_name, item_lov, warehouse_for_item, sales_tax_codes, projects_lov, policy_link, project_balance, policy_balance_by_customer, crop_lov, child_card_code, sales_vs_achievement_geo, sales_vs_achievement_geo_inv, geo_options, sales_vs_achievement_geo_profit, collection_vs_achievement, sales_vs_achievement_territory, unit_price_by_policy, territories_lov
from django.conf import settings
from pathlib import Path
import sys
from django.utils.safestring import mark_safe
from django.core.paginator import Paginator
from FieldAdvisoryService.models import Company, Region, Zone, Territory

#logger = logging.getLogger(__name__)


def get_company_schema_options():
    """
    Get dynamic schema options from Company model
    Returns dict mapping Company_name to schema name (name field)
    """
    try:
        companies = Company.objects.filter(is_active=True)
        return {comp.Company_name: comp.name for comp in companies}
    except Exception:
        return {}


def get_default_schema():
    """
    Get the default schema dynamically from the first active company
    """
    try:
        first_company = Company.objects.filter(is_active=True).first()
        if first_company and first_company.name:
            return first_company.name
        # If no companies found, try environment variable with no hardcoded fallback
        return os.environ.get('HANA_SCHEMA', '')
    except Exception:
        return os.environ.get('HANA_SCHEMA', '')


def get_default_company_key():
    """
    Get the default company key (Company_name) from the first active company
    """
    try:
        first_company = Company.objects.filter(is_active=True).first()
        if first_company and first_company.Company_name:
            return first_company.Company_name
        # Fallback to a default
        return ''
    except Exception:
        return ''


def resolve_company_to_schema(company_param: str) -> str:
    """
    Directly resolve company parameter to schema name.
    - If given display name (e.g., '4B-AGRI'), returns schema_name (e.g., '4B-AGRI_LIVE')
    - If given schema name directly, returns it as-is
    
    Company model has:
      - Company_name: Display name (e.g., "4B-AGRI")
      - name: Schema name (e.g., "4B-AGRI_LIVE")
    """
    if not company_param or not company_param.strip():
        return ''
    
    company_param = company_param.strip()
    token = company_param.upper()
    
    # 1. Try direct case-insensitive match on Company_name (display name)
    try:
        company = Company.objects.get(Company_name__iexact=company_param, is_active=True)
        return company.name  # Return the schema_name field
    except Company.DoesNotExist:
        pass
    
    # 2. Try direct case-insensitive match on name field (schema name)
    try:
        company = Company.objects.get(name__iexact=company_param, is_active=True)
        return company.name
    except Company.DoesNotExist:
        pass
    
    # 3. Try with dash/underscore variants on Company_name
    variants = set()
    variants.add(token)
    variants.add(token.replace('-', '_'))
    variants.add(token.replace('_', '-'))
    
    for candidate in variants:
        try:
            company = Company.objects.get(Company_name__iexact=candidate, is_active=True)
            return company.name
        except Company.DoesNotExist:
            pass
        try:
            company = Company.objects.get(name__iexact=candidate, is_active=True)
            return company.name
        except Company.DoesNotExist:
            pass
    
    # 4. Fallback: search by company type keyword in Company_name
    # Get all matching companies and prefer longer schema names
    if 'ORANG' in token:
        companies = list(Company.objects.filter(is_active=True, Company_name__icontains='ORANG'))
        if companies:
            # Return the one with longest schema name (more specific)
            company = sorted(companies, key=lambda c: len(c.name), reverse=True)[0]
            return company.name
    if 'BIO' in token:
        companies = list(Company.objects.filter(is_active=True, Company_name__icontains='BIO'))
        if companies:
            company = sorted(companies, key=lambda c: len(c.name), reverse=True)[0]
            return company.name
    if 'AGRI' in token:
        companies = list(Company.objects.filter(is_active=True, Company_name__icontains='AGRI'))
        if companies:
            company = sorted(companies, key=lambda c: len(c.name), reverse=True)[0]
            return company.name
    
    # 5. Last resort: return first active company's schema
    try:
        company = Company.objects.filter(is_active=True).first()
        if company:
            return company.name
    except Exception:
        pass
    
    # If nothing found, return the original parameter
    return company_param.strip()

def get_hana_schema_from_request(request):
    """
    Resolve HANA schema from query param, session, or first active company.
    Returns the actual schema field from Company.name
    (e.g., '4B-BIO_APP', '4B-AGRI_LIVE').
    """
    def _schema_from_company(company_obj):
        if not company_obj:
            return None
        # Company.name is the schema key used for HANA connections.
        return (getattr(company_obj, 'name', None) or getattr(company_obj, 'Company_name', None) or '').strip() or None

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
        # Ensure LIVE suffix when missing
        if not token.endswith('_LIVE') and not token.endswith('-LIVE'):
            variants.add(f"{token}_LIVE")
            variants.add(f"{token}-LIVE")
        # Try exact/case-insensitive matches against active companies
        for candidate in list(variants):
            try:
                company = Company.objects.get(name=candidate, is_active=True)
                return _schema_from_company(company)
            except Company.DoesNotExist:
                pass
            try:
                company = Company.objects.get(name__iexact=candidate, is_active=True)
                return _schema_from_company(company)
            except Company.DoesNotExist:
                pass
            try:
                company = Company.objects.get(Company_name=candidate, is_active=True)
                return _schema_from_company(company)
            except Company.DoesNotExist:
                pass
            try:
                company = Company.objects.get(Company_name__iexact=candidate, is_active=True)
                return _schema_from_company(company)
            except Company.DoesNotExist:
                pass

        # If still not found, map common keys like '4B-ORANG'/'4B-BIO'/'4B-AGRI' to active companies
        if 'ORANG' in token:
            company = Company.objects.filter(is_active=True).filter(Q(name__icontains='ORANG') | Q(Company_name__icontains='ORANG')).first()
            if company:
                return _schema_from_company(company)
        if 'BIO' in token:
            company = Company.objects.filter(is_active=True).filter(Q(name__icontains='BIO') | Q(Company_name__icontains='BIO')).first()
            if company:
                return _schema_from_company(company)
        if 'AGRI' in token:
            company = Company.objects.filter(is_active=True).filter(Q(name__icontains='AGRI') | Q(Company_name__icontains='AGRI')).first()
            if company:
                return _schema_from_company(company)

    session_db = request.session.get('selected_db', '').strip()
    if session_db:
        try:
            company = Company.objects.get(name=session_db, is_active=True)
            return _schema_from_company(company)
        except Company.DoesNotExist:
            pass
        try:
            company = Company.objects.get(Company_name=session_db, is_active=True)
            return _schema_from_company(company)
        except Company.DoesNotExist:
            pass

    try:
        company = Company.objects.filter(is_active=True).first()
        if company:
            return _schema_from_company(company)
    except Exception:
        pass

    # Only use Company model - no environment variable fallback
    try:
        company = Company.objects.filter(is_active=True).first()
        if company:
            return _schema_from_company(company)
    except Exception:
        pass
    
    # logger.warning("[DB RESOLVER] No active company found in Company model. Database operations may fail.")
    return None


def get_valid_company_schemas():
    """Return list of active company schemas for documentation."""
    try:
        schemas = list(Company.objects.filter(is_active=True).values_list('Company_name', flat=True))
        if schemas:
            return schemas
    except Exception:
        pass
    
    # Return empty list if no companies found - no hardcoded defaults
    # logger.warning("[VALID_SCHEMAS] No active companies found in database")
    return []

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
            selected_db = request.session.get('selected_db', get_default_company_key())
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
    
    # Get database options from Company model
    db_options = {}
    selected_db_key = request.GET.get('company_db', '')
    
    try:
        # Fetch active companies from database
        companies = Company.objects.filter(is_active=True).order_by('name')
        
        # Build db_options dictionary from companies
        # The 'name' field contains the schema (e.g., '4B-BIO_APP', '4B-ORANG_APP')
        for company in companies:
            if company.name:
                # Use the schema name as both key and value
                # This allows direct schema selection
                db_options[company.name] = company.name
        
    except Exception as e:
        # Fallback to default options if Company model not accessible
        pass
    
    # Set default selected key if not provided
    if not selected_db_key and db_options:
        # Use first company from database
        selected_db_key = list(db_options.keys())[0]
    
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
    selected_schema = db_options.get(selected_db_key, '')
    
    # If not found in db_options, use the selected_db_key directly as the schema
    # This allows using schema names like 4B-AGRI_LIVE even if not in Company model
    if not selected_schema and selected_db_key:
        selected_schema = selected_db_key
    
    # Final fallback to environment variable
    if not selected_schema:
        selected_schema = os.environ.get('HANA_SCHEMA', '')
    
    # DEBUG: schema selection details
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
    territories = []
    
    # Extract filter parameters for diagnostics
    emp_id_param = (request.GET.get('emp_id') or '').strip()
    user_id_param = (request.GET.get('user_id') or '').strip()
    period_param = (request.GET.get('period') or '').strip()
    start_date_param = (request.GET.get('start_date') or '').strip()
    end_date_param = (request.GET.get('end_date') or '').strip()
    region_param = (request.GET.get('region') or '').strip()
    zone_param = (request.GET.get('zone') or '').strip()
    territory_param = (request.GET.get('territory') or '').strip()
    in_millions_param = (request.GET.get('in_millions') or '').strip().lower()
    group_by_date_param = (request.GET.get('group_by_date') or '').strip().lower()
    ignore_emp_filter_param = (request.GET.get('ignore_emp_filter') or '').strip().lower()
    
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
        'emp_id': emp_id_param,
        'user_id': user_id_param,
        'period': period_param,
        'start_date': start_date_param,
        'end_date': end_date_param,
        'region': region_param,
        'zone': zone_param,
        'territory': territory_param,
        'in_millions': (in_millions_param in ('true','1','yes','y')),
        'group_by_date': (group_by_date_param in ('true','1','yes','y')),
        'ignore_emp_filter': (ignore_emp_filter_param in ('true','1','yes','y')),
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
                                diagnostics['in_millions'] = (in_millions_param in ('true','1','yes','y'))
                                request._territory_options = territory_options
                        except Exception as e_ts:
                            error = str(e_ts)
                    elif action == 'products_catalog':
                        try:
                            # Extract pagination parameters
                            page_param = request.GET.get('page', '1')
                            page_size_param = request.GET.get('page_size', '')

                            try:
                                page_num = int(page_param)
                                if page_num < 1:
                                    page_num = 1
                            except (ValueError, TypeError):
                                page_num = 1

                            try:
                                page_size = int(page_size_param) if page_size_param else 50
                                if page_size < 1:
                                    page_size = 50
                                elif page_size > 10000:
                                    page_size = 10000
                            except (ValueError, TypeError):
                                page_size = 50

                            # Only filter by category server-side; search is handled client-side
                            # so all matching products are available in the DOM for instant filtering
                            item_group_param = (request.GET.get('item_group') or '').strip() or None
                            item_groups_param = (request.GET.get('item_groups') or '').strip() or None
                            is_active_param = (request.GET.get('is_active') or 'Y').strip()
                            search_param = (request.GET.get('search') or '').strip() or None

                            # Calculate offset for pagination
                            offset = (page_num - 1) * page_size

                            # Apply pagination to the database query
                            catalog_result = products_catalog(
                                conn,
                                selected_schema,
                                search=search_param,
                                item_group=item_group_param,
                                item_groups=item_groups_param,
                                is_active=is_active_param,
                                limit=page_size,
                                offset=offset
                            )

                            # Handle new dictionary format - extract products list for backward compatibility
                            data = catalog_result.get('products', []) if isinstance(catalog_result, dict) else catalog_result
                            total_count = catalog_result.get('total_count', 0) if isinstance(catalog_result, dict) else len(data)

                            result = data

                            # Add pagination info to diagnostics for template
                            diagnostics['pagination'] = {
                                'page': page_num,
                                'page_size': page_size,
                                'total_count': total_count,
                                'total_pages': (total_count + page_size - 1) // page_size,
                                'has_previous': page_num > 1,
                                'has_next': page_num * page_size < total_count,
                                'start_index': offset + 1 if total_count > 0 else 0,
                                'end_index': min(offset + page_size, total_count)
                            }

                            # Store the correct total count for products_catalog to fix double-pagination bug
                            # The generic pagination logic below creates a Django Paginator from the already-paginated
                            # result_rows, which gives wrong count. We need to use the database total_count instead.
                            request._products_catalog_total_count = total_count

                            # print(f"DEBUG products_catalog result: {len(result) if result else 0} products, total_count: {total_count}, page {page_num} of {diagnostics['pagination']['total_pages']}")
                        except Exception as e_pc:
                            error = str(e_pc)
                            # print(f"DEBUG products_catalog ERROR: {error}")
                    elif action == 'list_territories':
                        try:
                            data = territories_all(conn)
                            # Helper function to clean region/zone/territory names
                            def clean_geo_name(name):
                                if not name or not isinstance(name, str):
                                    return name
                                # Remove common suffixes (case-insensitive, preserve original case for the rest)
                                for suffix in [' Region', ' Zone', ' Territory']:
                                    if name.endswith(suffix):
                                        return name[:-len(suffix)].strip()
                                return name
                            
                            # Build hierarchical Region -> Zone -> Territory structure with aggregated totals
                            hierarchy = {}
                            for row in (data or []):
                                if not isinstance(row, dict):
                                    continue
                                reg = row.get('Region', 'Unknown Region')
                                zon = row.get('Zone', 'Unknown Zone')
                                ter = row.get('Territory', 'Unknown Territory')
                                
                                # Clean the names
                                reg = clean_geo_name(reg)
                                zon = clean_geo_name(zon)
                                ter = clean_geo_name(ter)
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
                                if cfg['schema']:
                                    diagnostics['oter_columns'] = table_columns(conn, cfg['schema'], 'OTER')
                                    diagnostics['schema_used'] = cfg['schema']
                                else:
                                    diagnostics['oter_columns'] = []
                                    diagnostics['schema_used'] = 'No schema set'
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
                            
                            # Handle database parameter for admin view - Get schema from Company model
                            if db_param:
                                schema_from_db = None
                                try:
                                    companies = Company.objects.filter(is_active=True)
                                    for company in companies:
                                        if company.Company_name == db_param or company.name == db_param:
                                            schema_from_db = company.name
                                            break
                                except Exception:
                                    pass
                                
                                # Use schema from Company model if found, otherwise use db_param directly
                                cfg['schema'] = schema_from_db if schema_from_db else db_param
                                
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
                                diagnostics['in_millions'] = (in_millions_param in ('true','1','yes','y'))
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
                                if in_millions_param in ('true','1','yes','y'):
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
                                    # Get geo options from HANA OTER table
                                    hana_geo = geo_options(conn)
                                    if hana_geo:
                                        regions = sorted(set(r.get('Region') for r in hana_geo if r.get('Region')))
                                        zones = sorted(set(r.get('Zone') for r in hana_geo if r.get('Zone')))
                                        territories = sorted(set(r.get('Territory') for r in hana_geo if r.get('Territory')))
                                        request._geo_options = {'regions': regions, 'zones': zones, 'territories': territories}
                                    else:
                                        # Fallback to Django models if HANA returns empty
                                        from FieldAdvisoryService.models import Region, Zone, Territory
                                        regions = list(Region.objects.order_by('name').values_list('name', flat=True).distinct())
                                        zones = list(Zone.objects.order_by('name').values_list('name', flat=True).distinct())
                                        territories = list(Territory.objects.order_by('name').values_list('name', flat=True).distinct())
                                        request._geo_options = {'regions': regions, 'zones': zones, 'territories': territories}
                                except Exception as e:
                                    print(f"DEBUG: geo_options error: {e}")
                                    # Fallback to Django models
                                    try:
                                        from FieldAdvisoryService.models import Region, Zone, Territory
                                        regions = list(Region.objects.order_by('name').values_list('name', flat=True).distinct())
                                        zones = list(Zone.objects.order_by('name').values_list('name', flat=True).distinct())
                                        territories = list(Territory.objects.order_by('name').values_list('name', flat=True).distinct())
                                        request._geo_options = {'regions': regions, 'zones': zones, 'territories': territories}
                                    except Exception:
                                        request._geo_options = {'regions': [], 'zones': [], 'territories': []}
                                    
                                diagnostics['emp_id'] = emp_val
                                diagnostics['start_date'] = (start_date_param or '').strip()
                                diagnostics['end_date'] = (end_date_param or '').strip()
                                diagnostics['region'] = (region_param or '').strip()
                                diagnostics['zone'] = (zone_param or '').strip()
                                diagnostics['territory'] = (territory_param or '').strip()
                                diagnostics['in_millions'] = (in_millions_param in ('true','1','yes','y'))
                                
                        except Exception as e_geo:
                            error = str(e_geo)
                    elif action == 'collection_vs_achievement':
                        try:
                            emp_id_param = request.GET.get('emp_id')
                            user_id_param = request.GET.get('user_id')
                            region_param = request.GET.get('region')
                            zone_param = request.GET.get('zone')
                            territory_param = request.GET.get('territory')
                            period_param = (request.GET.get('period') or 'monthly').strip().lower()
                            start_date_param = request.GET.get('start_date')
                            end_date_param = request.GET.get('end_date')
                            in_millions_param = (request.GET.get('in_millions') or '').strip().lower()
                            detailed_view_param = (request.GET.get('detailed_view') or '').strip().lower()
                            
                            is_detailed = detailed_view_param in ('true', '1', 'yes', 'on')
                            
                            # Handle period parameter - only set dates if they're not explicitly provided
                            from datetime import date
                            today = date.today()
                            
                            # Only apply period-based dates if start_date and end_date are not provided
                            if period_param and not start_date_param and not end_date_param:
                                if period_param == 'today':
                                    start_date_param = today.strftime('%Y-%m-%d')
                                    end_date_param = today.strftime('%Y-%m-%d')
                                elif period_param == 'monthly':
                                    # First day of current month to today
                                    start_date_param = today.replace(day=1).strftime('%Y-%m-%d')
                                    end_date_param = today.strftime('%Y-%m-%d')
                                elif period_param == 'yearly':
                                    # First day of current year to today
                                    start_date_param = today.replace(month=1, day=1).strftime('%Y-%m-%d')
                                    end_date_param = today.strftime('%Y-%m-%d')
                            
                            # Handle user_id parameter to fetch employee_code from sales_profile
                            emp_val = None
                            if user_id_param:
                                try:
                                    from accounts.models import User
                                    user_id_int = int(user_id_param)
                                    target_user = User.objects.select_related('sales_profile').get(id=user_id_int)
                                    if hasattr(target_user, 'sales_profile') and target_user.sales_profile:
                                        employee_code = target_user.sales_profile.employee_code
                                        if employee_code:
                                            try:
                                                emp_val = int(employee_code)
                                            except ValueError:
                                                pass
                                except Exception as e_user:
                                    error = f'Invalid user_id: {str(e_user)}'
                            
                            # emp_id overrides user_id if both provided
                            if emp_id_param is not None and emp_id_param != '':
                                try:
                                    emp_val = int(emp_id_param)
                                except Exception:
                                    error = 'Invalid emp_id'
                            
                            if error is None:
                                data = collection_vs_achievement(
                                    conn,
                                    emp_id=emp_val,
                                    region=(region_param or '').strip() or None,
                                    zone=(zone_param or '').strip() or None,
                                    territory=(territory_param or '').strip() or None,
                                    start_date=(start_date_param or '').strip() or None,
                                    end_date=(end_date_param or '').strip() or None,
                                    group_by_date=is_detailed,
                                    ignore_emp_filter=False
                                )
                                
                                if in_millions_param in ('true','1','yes','y'):
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

                                # Helper function to clean region/zone/territory names
                                def clean_geo_name(name):
                                    if not name or not isinstance(name, str):
                                        return name
                                    # Remove common suffixes (case-insensitive, preserve original case for the rest)
                                    for suffix in [' Region', ' Zone', ' Territory']:
                                        if name.endswith(suffix):
                                            return name[:-len(suffix)].strip()
                                    return name

                                # Hierarchical Transformation
                                # If source is already hierarchical (name/sales/achievement/zones), use it directly.
                                if isinstance(data, list) and data and isinstance(data[0], dict) and isinstance(data[0].get('zones'), list):
                                    final_list = []
                                    for region_row in data:
                                        region_copy = dict(region_row)
                                        region_copy['name'] = clean_geo_name(region_copy.get('name') or 'Unknown Region')
                                        region_copy['sales'] = round(float(region_copy.get('sales') or 0.0), 2)
                                        region_copy['achievement'] = round(float(region_copy.get('achievement') or 0.0), 2)
                                        zones_in = region_copy.get('zones') or []
                                        zones_out = []
                                        for zone_row in zones_in:
                                            zone_copy = dict(zone_row)
                                            zone_copy['name'] = clean_geo_name(zone_copy.get('name') or 'Unknown Zone')
                                            zone_copy['sales'] = round(float(zone_copy.get('sales') or 0.0), 2)
                                            zone_copy['achievement'] = round(float(zone_copy.get('achievement') or 0.0), 2)
                                            terr_in = zone_copy.get('territories') or []
                                            terr_out = []
                                            for terr_row in terr_in:
                                                terr_copy = dict(terr_row)
                                                terr_copy['name'] = clean_geo_name(terr_copy.get('name') or 'Unknown Territory')
                                                terr_copy['sales'] = float(terr_copy.get('sales') or 0.0)
                                                terr_copy['achievement'] = float(terr_copy.get('achievement') or 0.0)
                                                terr_copy.setdefault('date_range', '')
                                                terr_out.append(terr_copy)
                                            zone_copy['territories'] = sorted(terr_out, key=lambda x: x.get('name') or '')
                                            zones_out.append(zone_copy)
                                        region_copy['zones'] = sorted(zones_out, key=lambda x: x.get('name') or '')
                                        final_list.append(region_copy)
                                    final_list = sorted(final_list, key=lambda x: x.get('name') or '')
                                else:
                                    hierarchy = {}
                                    for row in (data or []):
                                        if not isinstance(row, dict):
                                            continue
                                        reg = row.get('Region') or row.get('REGION') or row.get('region') or 'Unknown Region'
                                        zon = row.get('Zone') or row.get('ZONE') or row.get('zone') or 'Unknown Zone'
                                        ter = row.get('TerritoryName') or row.get('TERRITORYNAME') or row.get('Territory') or row.get('TERRITORY') or row.get('territory') or 'Unknown Territory'

                                        # Clean the names
                                        reg = clean_geo_name(reg)
                                        zon = clean_geo_name(zon)
                                        ter = clean_geo_name(ter)

                                        # Handle Date Range
                                        date_range_str = ""
                                        fd = row.get('From_Date') or row.get('FROM_DATE')
                                        td = row.get('To_Date') or row.get('TO_DATE')
                                        if fd and td:
                                            date_range_str = f"{fd} to {td}"
                                        elif fd:
                                            date_range_str = f"From {fd}"
                                        elif td:
                                            date_range_str = f"To {td}"

                                        sal = 0.0
                                        ach = 0.0
                                        try:
                                            v = row.get('Collection_Target')
                                            if v is None: v = row.get('COLLECTION_TARGET')
                                            if v is None: v = row.get('colletion_Target')
                                            if v is None: v = row.get('sales')
                                            sal = float(v or 0.0)
                                        except Exception:
                                            pass
                                        try:
                                            v = row.get('Collection_Achievement')
                                            if v is None: v = row.get('COLLECTION_ACHIEVEMENT')
                                            if v is None: v = row.get('DocTotal')
                                            if v is None: v = row.get('achievement')
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
                                    # Get geo options from HANA OTER table
                                    hana_geo = geo_options(conn)
                                    if hana_geo:
                                        regions = sorted(set(r.get('Region') for r in hana_geo if r.get('Region')))
                                        zones = sorted(set(r.get('Zone') for r in hana_geo if r.get('Zone')))
                                        territories = sorted(set(r.get('Territory') for r in hana_geo if r.get('Territory')))
                                        request._geo_options = {'regions': regions, 'zones': zones, 'territories': territories}
                                    else:
                                        # Fallback to Django models if HANA returns empty
                                        from FieldAdvisoryService.models import Region, Zone, Territory
                                        regions = list(Region.objects.order_by('name').values_list('name', flat=True).distinct())
                                        zones = list(Zone.objects.order_by('name').values_list('name', flat=True).distinct())
                                        territories = list(Territory.objects.order_by('name').values_list('name', flat=True).distinct())
                                        request._geo_options = {'regions': regions, 'zones': zones, 'territories': territories}
                                except Exception as e:
                                    print(f"DEBUG: geo_options error: {e}")
                                    # Fallback to Django models
                                    try:
                                        from FieldAdvisoryService.models import Region, Zone, Territory
                                        regions = list(Region.objects.order_by('name').values_list('name', flat=True).distinct())
                                        zones = list(Zone.objects.order_by('name').values_list('name', flat=True).distinct())
                                        territories = list(Territory.objects.order_by('name').values_list('name', flat=True).distinct())
                                        request._geo_options = {'regions': regions, 'zones': zones, 'territories': territories}
                                    except Exception:
                                        request._geo_options = {'regions': [], 'zones': [], 'territories': []}
                                    
                                diagnostics['emp_id'] = emp_val
                                diagnostics['user_id'] = user_id_param or ''
                                diagnostics['period'] = period_param
                                diagnostics['start_date'] = (start_date_param or '').strip()
                                diagnostics['end_date'] = (end_date_param or '').strip()
                                diagnostics['region'] = (region_param or '').strip()
                                diagnostics['zone'] = (zone_param or '').strip()
                                diagnostics['territory'] = (territory_param or '').strip()
                                diagnostics['in_millions'] = (in_millions_param in ('true','1','yes','y'))
                                diagnostics['detailed_view'] = is_detailed
                                
                        except Exception as e_coll:
                            error = str(e_coll)
                    elif action == 'sales_vs_achievement_geo_inv':
                        try:
                            emp_id_param = request.GET.get('emp_id')
                            region_param = request.GET.get('region')
                            zone_param = request.GET.get('zone')
                            territory_param = request.GET.get('territory')
                            period_param = (request.GET.get('period') or '').strip().lower()
                            start_date_param = request.GET.get('start_date')
                            end_date_param = request.GET.get('end_date')
                            in_millions_param = (request.GET.get('in_millions') or '').strip().lower()
                            group_by_emp_param = request.GET.get('group_by_emp')

                            # Priority order: period > custom dates > default
                            # When period is explicitly set (today/monthly/yearly), it takes precedence
                            if period_param in ('today', 'monthly', 'yearly'):
                                from datetime import date
                                from calendar import monthrange
                                today = date.today()
                                if period_param == 'today':
                                    start_date_param = today.strftime('%Y-%m-%d')
                                    end_date_param = today.strftime('%Y-%m-%d')
                                elif period_param == 'monthly':
                                    start_date_param = today.replace(day=1).strftime('%Y-%m-%d')
                                    last_day = monthrange(today.year, today.month)[1]
                                    end_date_param = today.replace(day=last_day).strftime('%Y-%m-%d')
                                elif period_param == 'yearly':
                                    start_date_param = today.replace(month=1, day=1).strftime('%Y-%m-%d')
                                    end_date_param = today.replace(month=12, day=31).strftime('%Y-%m-%d')
                            
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
                            if in_millions_param in ('true','1','yes','y'):
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
                            # Helper function to clean region/zone/territory names
                            def clean_geo_name(name):
                                if not name or not isinstance(name, str):
                                    return name
                                # Remove common suffixes
                                for suffix in [' Region', ' Zone', ' Territory']:
                                    if name.endswith(suffix):
                                        return name[:-len(suffix)].strip()
                                return name
                            
                            hierarchy = {}
                            for row in (data or []):
                                if not isinstance(row, dict):
                                    continue
                                reg = row.get('Region', 'Unknown Region')
                                zon = row.get('Zone', 'Unknown Zone')
                                ter = row.get('Territory', 'Unknown Territory')
                                
                                # Clean the names
                                reg = clean_geo_name(reg)
                                zon = clean_geo_name(zon)
                                ter = clean_geo_name(ter)
                                
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
                                # Get geo options from HANA OTER table
                                hana_geo = geo_options(conn)
                                if hana_geo:
                                    regions = sorted(set(r.get('Region') for r in hana_geo if r.get('Region')))
                                    zones = sorted(set(r.get('Zone') for r in hana_geo if r.get('Zone')))
                                    territories = sorted(set(r.get('Territory') for r in hana_geo if r.get('Territory')))
                                    request._geo_options = {'regions': regions, 'zones': zones, 'territories': territories}
                                else:
                                    from FieldAdvisoryService.models import Region, Zone, Territory
                                    regions = list(Region.objects.order_by('name').values_list('name', flat=True).distinct())
                                    zones = list(Zone.objects.order_by('name').values_list('name', flat=True).distinct())
                                    territories = list(Territory.objects.order_by('name').values_list('name', flat=True).distinct())
                                    request._geo_options = {'regions': regions, 'zones': zones, 'territories': territories}
                            except Exception as e:
                                print(f"DEBUG: geo_options error: {e}")
                                try:
                                    from FieldAdvisoryService.models import Region, Zone, Territory
                                    regions = list(Region.objects.order_by('name').values_list('name', flat=True).distinct())
                                    zones = list(Zone.objects.order_by('name').values_list('name', flat=True).distinct())
                                    territories = list(Territory.objects.order_by('name').values_list('name', flat=True).distinct())
                                    request._geo_options = {'regions': regions, 'zones': zones, 'territories': territories}
                                except Exception:
                                    request._geo_options = {'regions': [], 'zones': [], 'territories': []}
                                
                            diagnostics['emp_id'] = emp_val
                            diagnostics['start_date'] = (start_date_param or '').strip()
                            diagnostics['end_date'] = (end_date_param or '').strip()
                            diagnostics['region'] = (region_param or '').strip()
                            diagnostics['zone'] = (zone_param or '').strip()
                            diagnostics['territory'] = (territory_param or '').strip()
                            diagnostics['period'] = period_param
                            diagnostics['in_millions'] = (in_millions_param in ('true','1','yes','y'))
                            diagnostics['group_by_emp'] = group_by_emp
                            
                        except Exception as e_geo_inv:
                            error = str(e_geo_inv)
                    elif action == 'sales_vs_achievement_territory':
                        try:
                            emp_id_param = request.GET.get('emp_id')
                            user_id_param = request.GET.get('user_id')
                            region_param = request.GET.get('region')
                            zone_param = request.GET.get('zone')
                            territory_param = request.GET.get('territory')
                            period_param = (request.GET.get('period') or '').strip().lower()
                            start_date_param = request.GET.get('start_date')
                            end_date_param = request.GET.get('end_date')
                            year_param = (request.GET.get('year') or '').strip()
                            month_param = (request.GET.get('month') or '').strip()
                            in_millions_param = (request.GET.get('in_millions') or '').strip().lower()

                            from datetime import date
                            from calendar import monthrange
                            today = date.today()
                            
                            # DEBUG: Log incoming parameters
                            print(f"DEBUG sales_vs_achievement_territory: period={period_param}, start_date={start_date_param}, end_date={end_date_param}")
                            print(f"DEBUG: Server date.today() = {today}, today.strftime = {today.strftime('%Y-%m-%d')}")

                            # Priority order: period > year+month > year > custom dates > default to current month
                            # When period is explicitly set (today/monthly/yearly), it overrides everything
                            if period_param in ('today', 'monthly', 'yearly'):
                                if period_param == 'today':
                                    start_date_param = today.strftime('%Y-%m-%d')
                                    end_date_param = today.strftime('%Y-%m-%d')
                                elif period_param == 'monthly':
                                    start_date_param = today.replace(day=1).strftime('%Y-%m-%d')
                                    last_day = monthrange(today.year, today.month)[1]
                                    end_date_param = today.replace(day=last_day).strftime('%Y-%m-%d')
                                elif period_param == 'yearly':
                                    start_date_param = today.replace(month=1, day=1).strftime('%Y-%m-%d')
                                    end_date_param = today.replace(month=12, day=31).strftime('%Y-%m-%d')
                                print(f"DEBUG: After period calc: start_date={start_date_param}, end_date={end_date_param}")
                            elif not start_date_param and not end_date_param and year_param and month_param:
                                try:
                                    year_val = int(year_param)
                                    month_val = int(month_param)
                                    if 1 <= month_val <= 12:
                                        start_date_param = date(year_val, month_val, 1).strftime('%Y-%m-%d')
                                        last_day = monthrange(year_val, month_val)[1]
                                        end_date_param = date(year_val, month_val, last_day).strftime('%Y-%m-%d')
                                except Exception:
                                    pass
                            elif not start_date_param and not end_date_param and year_param:
                                try:
                                    year_val = int(year_param)
                                    start_date_param = date(year_val, 1, 1).strftime('%Y-%m-%d')
                                    end_date_param = date(year_val, 12, 31).strftime('%Y-%m-%d')
                                except Exception:
                                    pass

                            # Default to current month if no date parameters provided
                            if not period_param and not start_date_param and not end_date_param and not year_param:
                                start_date_param = today.replace(day=1).strftime('%Y-%m-%d')
                                last_day = monthrange(today.year, today.month)[1]
                                end_date_param = today.replace(day=last_day).strftime('%Y-%m-%d')

                            emp_val = None
                            employee_code = None

                            if user_id_param:
                                try:
                                    from accounts.models import User
                                    user_id_int = int(user_id_param)
                                    target_user = User.objects.select_related('sales_profile').get(id=user_id_int)
                                    if hasattr(target_user, 'sales_profile') and target_user.sales_profile:
                                        employee_code = target_user.sales_profile.employee_code
                                        if employee_code:
                                            try:
                                                emp_val = int(employee_code)
                                            except ValueError:
                                                pass
                                except Exception:
                                    pass

                            if emp_id_param is not None and emp_id_param != '':
                                try:
                                    employee_code = str(emp_id_param)
                                    emp_val = int(emp_id_param)
                                except Exception:
                                    error = 'Invalid emp_id'

                            ignore_emp_filter = False
                            if employee_code == '00':
                                ignore_emp_filter = True
                                emp_val = None

                            data = sales_vs_achievement_territory(
                                conn,
                                emp_id=emp_val,
                                region=(region_param or '').strip() or None,
                                zone=(zone_param or '').strip() or None,
                                territory=(territory_param or '').strip() or None,
                                start_date=(start_date_param or '').strip() or None,
                                end_date=(end_date_param or '').strip() or None,
                                group_by_date=False,
                                ignore_emp_filter=ignore_emp_filter,
                                group_by_emp=False
                            )
                            
                            if in_millions_param in ('true','1','yes','y'):
                                scaled = []
                                for row in data or []:
                                    if isinstance(row, dict):
                                        r = dict(row)
                                        try:
                                            v = r.get('Sales_Target')
                                            if v is None: v = r.get('SALES_TARGET')
                                            if v is not None:
                                                r['Sales_Target'] = round((float(v) / 1000000.0), 2)
                                        except Exception:
                                            pass
                                        try:
                                            v = r.get('Sales_Achievement')
                                            if v is None: v = r.get('SALES_ACHIEVEMENT')
                                            if v is not None:
                                                r['Sales_Achievement'] = round((float(v) / 1000000.0), 2)
                                        except Exception:
                                            pass
                                        scaled.append(r)
                                    else:
                                        scaled.append(row)
                                data = scaled
                            
                            # Helper function to clean region/zone/territory names
                            def clean_geo_name(name):
                                if not name or not isinstance(name, str):
                                    return name
                                # Remove common suffixes (case-insensitive, preserve original case for the rest)
                                for suffix in [' Region', ' Zone', ' Territory']:
                                    if name.endswith(suffix):
                                        return name[:-len(suffix)].strip()
                                return name
                            
                            hierarchy = {}
                            for row in (data or []):
                                if not isinstance(row, dict):
                                    continue
                                if row.get('Region') == 'GRAND TOTAL':
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
                                
                                # Clean the names
                                reg = clean_geo_name(reg)
                                zon = clean_geo_name(zon)
                                ter = clean_geo_name(ter)
                                sal = 0.0
                                ach = 0.0
                                try:
                                    v = row.get('Sales_Target')
                                    if v is None: v = row.get('SALES_TARGET')
                                    sal = float(v or 0.0)
                                except Exception:
                                    pass
                                try:
                                    v = row.get('Sales_Achievement')
                                    if v is None: v = row.get('SALES_ACHIEVEMENT')
                                    if v is None: v = row.get('ACHIEVEMENT')
                                    ach = float(v or 0.0)
                                except Exception:
                                    pass
                                if reg not in hierarchy:
                                    hierarchy[reg] = {'name': reg or 'Unknown', 'sales': 0.0, 'achievement': 0.0, 'zones': {}}
                                hierarchy[reg]['sales'] += sal
                                hierarchy[reg]['achievement'] += ach
                                if zon not in hierarchy[reg]['zones']:
                                    hierarchy[reg]['zones'][zon] = {'name': zon or 'Unknown', 'sales': 0.0, 'achievement': 0.0, 'territories': []}
                                hierarchy[reg]['zones'][zon]['sales'] += sal
                                hierarchy[reg]['zones'][zon]['achievement'] += ach
                                hierarchy[reg]['zones'][zon]['territories'].append({'name': ter or 'Unknown', 'sales': sal, 'achievement': ach})
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
                                # Get geo options from HANA OTER table
                                hana_geo = geo_options(conn)
                                if hana_geo:
                                    regions = sorted(set(r.get('Region') for r in hana_geo if r.get('Region')))
                                    zones = sorted(set(r.get('Zone') for r in hana_geo if r.get('Zone')))
                                    territories = sorted(set(r.get('Territory') for r in hana_geo if r.get('Territory')))
                                    request._geo_options = {'regions': regions, 'zones': zones, 'territories': territories}
                                else:
                                    from FieldAdvisoryService.models import Region, Zone, Territory
                                    regions = list(Region.objects.order_by('name').values_list('name', flat=True).distinct())
                                    zones = list(Zone.objects.order_by('name').values_list('name', flat=True).distinct())
                                    territories = list(Territory.objects.order_by('name').values_list('name', flat=True).distinct())
                                    request._geo_options = {'regions': regions, 'zones': zones, 'territories': territories}
                            except Exception as e:
                                print(f"DEBUG: geo_options error: {e}")
                                try:
                                    from FieldAdvisoryService.models import Region, Zone, Territory
                                    regions = list(Region.objects.order_by('name').values_list('name', flat=True).distinct())
                                    zones = list(Zone.objects.order_by('name').values_list('name', flat=True).distinct())
                                    territories = list(Territory.objects.order_by('name').values_list('name', flat=True).distinct())
                                    request._geo_options = {'regions': regions, 'zones': zones, 'territories': territories}
                                except Exception:
                                    request._geo_options = {'regions': [], 'zones': [], 'territories': []}
                            
                            diagnostics['start_date'] = (start_date_param or '').strip()
                            diagnostics['end_date'] = (end_date_param or '').strip()
                            diagnostics['period'] = period_param
                            diagnostics['year'] = year_param
                            diagnostics['month'] = month_param
                            diagnostics['region'] = (region_param or '').strip()
                            diagnostics['zone'] = (zone_param or '').strip()
                            diagnostics['territory'] = (territory_param or '').strip()
                            diagnostics['in_millions'] = (in_millions_param in ('true','1','yes','y'))
                        except Exception as e_svat:
                            error = str(e_svat)
                    elif action == 'collection_vs_achievement':
                        try:
                            emp_id_param = request.GET.get('emp_id')
                            region_param = request.GET.get('region')
                            zone_param = request.GET.get('zone')
                            territory_param = request.GET.get('territory')
                            period_param = (request.GET.get('period') or '').strip().lower()
                            start_date_param = request.GET.get('start_date')
                            end_date_param = request.GET.get('end_date')
                            in_millions_param = (request.GET.get('in_millions') or '').strip().lower()
                            group_by_date_param = (request.GET.get('group_by_date') or '').strip().lower()
                            ignore_emp_filter_param = (request.GET.get('ignore_emp_filter') or '').strip().lower()
                            
                            from datetime import date
                            from calendar import monthrange
                            today = date.today()
                            
                            # DEBUG: Log incoming parameters
                            print(f"DEBUG collection_vs_achievement: period={period_param}, start_date={start_date_param}, end_date={end_date_param}")
                            print(f"DEBUG: Server date.today() = {today}, today.strftime = {today.strftime('%Y-%m-%d')}")
                            
                            # Handle period parameter to auto-calculate date range
                            # When period is explicitly set (today/monthly/yearly), it takes precedence over manual dates
                            if period_param in ('today', 'monthly', 'yearly'):
                                if period_param == 'today':
                                    start_date_param = today.strftime('%Y-%m-%d')
                                    end_date_param = today.strftime('%Y-%m-%d')
                                elif period_param == 'monthly':
                                    start_date_param = today.replace(day=1).strftime('%Y-%m-%d')
                                    last_day = monthrange(today.year, today.month)[1]
                                    end_date_param = today.replace(day=last_day).strftime('%Y-%m-%d')
                                elif period_param == 'yearly':
                                    start_date_param = today.replace(month=1, day=1).strftime('%Y-%m-%d')
                                    end_date_param = today.replace(month=12, day=31).strftime('%Y-%m-%d')
                                print(f"DEBUG: After period calc: start_date={start_date_param}, end_date={end_date_param}")
                            
                            # Default to monthly if no date parameters provided
                            if not period_param and not start_date_param and not end_date_param:
                                start_date_param = today.replace(day=1).strftime('%Y-%m-%d')
                                last_day = monthrange(today.year, today.month)[1]
                                end_date_param = today.replace(day=last_day).strftime('%Y-%m-%d')
                            
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
                            
                            if in_millions_param in ('true','1','yes','y'):
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

                            # Helper function to clean region/zone/territory names
                            def clean_geo_name(name):
                                if not name or not isinstance(name, str):
                                    return name
                                # Remove common suffixes (case-insensitive, preserve original case for the rest)
                                for suffix in [' Region', ' Zone', ' Territory']:
                                    if name.endswith(suffix):
                                        return name[:-len(suffix)].strip()
                                return name

                            hierarchy = {}
                            for row in (data or []):
                                if not isinstance(row, dict):
                                    continue
                                reg = row.get('Region', 'Unknown Region')
                                zon = row.get('Zone', 'Unknown Zone')
                                ter = row.get('TerritoryName', 'Unknown Territory')
                                
                                # Clean the names
                                reg = clean_geo_name(reg)
                                zon = clean_geo_name(zon)
                                ter = clean_geo_name(ter)
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
                                # Get geo options from HANA OTER table
                                hana_geo = geo_options(conn)
                                if hana_geo:
                                    regions = sorted(set(r.get('Region') for r in hana_geo if r.get('Region')))
                                    zones = sorted(set(r.get('Zone') for r in hana_geo if r.get('Zone')))
                                    territories = sorted(set(r.get('Territory') for r in hana_geo if r.get('Territory')))
                                    request._geo_options = {'regions': regions, 'zones': zones, 'territories': territories}
                                else:
                                    from FieldAdvisoryService.models import Region, Zone, Territory
                                    regions = list(Region.objects.order_by('name').values_list('name', flat=True).distinct())
                                    zones = list(Zone.objects.order_by('name').values_list('name', flat=True).distinct())
                                    territories = list(Territory.objects.order_by('name').values_list('name', flat=True).distinct())
                                    request._geo_options = {'regions': regions, 'zones': zones, 'territories': territories}
                            except Exception as e:
                                print(f"DEBUG: geo_options error: {e}")
                                try:
                                    from FieldAdvisoryService.models import Region, Zone, Territory
                                    regions = list(Region.objects.order_by('name').values_list('name', flat=True).distinct())
                                    zones = list(Zone.objects.order_by('name').values_list('name', flat=True).distinct())
                                    territories = list(Territory.objects.order_by('name').values_list('name', flat=True).distinct())
                                    request._geo_options = {'regions': regions, 'zones': zones, 'territories': territories}
                                except Exception:
                                    request._geo_options = {'regions': [], 'zones': [], 'territories': []}
                            
                            diagnostics['emp_id'] = emp_val
                            diagnostics['start_date'] = (start_date_param or '').strip()
                            diagnostics['end_date'] = (end_date_param or '').strip()
                            diagnostics['period'] = period_param
                            diagnostics['region'] = (region_param or '').strip()
                            diagnostics['zone'] = (zone_param or '').strip()
                            diagnostics['territory'] = (territory_param or '').strip()
                            diagnostics['in_millions'] = (in_millions_param in ('true','1','yes','y'))
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
                            if in_millions_param in ('true','1','yes','y'):
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
                            # Helper function to clean region/zone/territory names
                            def clean_geo_name(name):
                                if not name or not isinstance(name, str):
                                    return name
                                # Remove common suffixes
                                for suffix in [' Region', ' Zone', ' Territory']:
                                    if name.endswith(suffix):
                                        return name[:-len(suffix)].strip()
                                return name
                            
                            hierarchy = {}
                            for row in (data or []):
                                if not isinstance(row, dict):
                                    continue
                                reg = row.get('Region', 'Unknown Region')
                                zon = row.get('Zone', 'Unknown Zone')
                                ter = row.get('Territory', 'Unknown Territory')
                                
                                # Clean the names
                                reg = clean_geo_name(reg)
                                zon = clean_geo_name(zon)
                                ter = clean_geo_name(ter)
                                
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
                                # Get geo options from HANA OTER table
                                hana_geo = geo_options(conn)
                                if hana_geo:
                                    regions = sorted(set(r.get('Region') for r in hana_geo if r.get('Region')))
                                    zones = sorted(set(r.get('Zone') for r in hana_geo if r.get('Zone')))
                                    territories = sorted(set(r.get('Territory') for r in hana_geo if r.get('Territory')))
                                    request._geo_options = {'regions': regions, 'zones': zones, 'territories': territories}
                                else:
                                    from FieldAdvisoryService.models import Region, Zone, Territory
                                    regions = list(Region.objects.order_by('name').values_list('name', flat=True).distinct())
                                    zones = list(Zone.objects.order_by('name').values_list('name', flat=True).distinct())
                                    territories = list(Territory.objects.order_by('name').values_list('name', flat=True).distinct())
                                    request._geo_options = {'regions': regions, 'zones': zones, 'territories': territories}
                            except Exception as e:
                                print(f"DEBUG: geo_options error: {e}")
                                try:
                                    from FieldAdvisoryService.models import Region, Zone, Territory
                                    regions = list(Region.objects.order_by('name').values_list('name', flat=True).distinct())
                                    zones = list(Zone.objects.order_by('name').values_list('name', flat=True).distinct())
                                    territories = list(Territory.objects.order_by('name').values_list('name', flat=True).distinct())
                                    request._geo_options = {'regions': regions, 'zones': zones, 'territories': territories}
                                except Exception:
                                    request._geo_options = {'regions': [], 'zones': [], 'territories': []}
                                
                            diagnostics['emp_id'] = emp_val
                            diagnostics['start_date'] = (start_date_param or '').strip()
                            diagnostics['end_date'] = (end_date_param or '').strip()
                            diagnostics['region'] = (region_param or '').strip()
                            diagnostics['zone'] = (zone_param or '').strip()
                            diagnostics['territory'] = (territory_param or '').strip()
                            diagnostics['in_millions'] = (in_millions_param in ('true','1','yes','y'))
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
                                
                                # Build hierarchical structure for geo display
                                # Build Territory → Zone → Region mapping from Django models
                                territory_map = {}
                                try:
                                    company = Company.objects.filter(Company_name=selected_db_key).first()
                                    if company:
                                        from FieldAdvisoryService.models import Territory as TerritoryModel
                                        territories_qs = TerritoryModel.objects.filter(company=company).select_related('zone', 'zone__region')
                                        for t in territories_qs:
                                            # Map territory name to its zone and region
                                            territory_map[t.name] = {
                                                'zone': t.zone.name if t.zone else 'Unknown Zone',
                                                'region': t.zone.region.name if t.zone and t.zone.region else 'Unknown Region'
                                            }
                                except Exception:
                                    pass
                                
                                # Transform flat data into hierarchical structure
                                hierarchy = {}
                                for row in (data or []):
                                    if not isinstance(row, dict):
                                        continue
                                    
                                    ter_name = row.get('TERRITORYNAME', 'Unknown Territory')
                                    # Clean territory name (remove " Territory" suffix if present)
                                    if ter_name and isinstance(ter_name, str) and ter_name.endswith(' Territory'):
                                        ter_name = ter_name[:-10].strip()
                                    
                                    # Get employee name from EMPID if available
                                    emp_id = row.get('EMPID')
                                    emp_name = ''
                                    if emp_id:
                                        try:
                                            from accounts.models import User as StaffUser
                                            user = StaffUser.objects.filter(sales_profile__employee_code=str(emp_id)).first()
                                            if user:
                                                emp_name = user.get_full_name() or user.username
                                        except Exception:
                                            pass
                                    
                                    # Look up zone and region from territory map
                                    geo_info = territory_map.get(ter_name, {'zone': 'Unknown Zone', 'region': 'Unknown Region'})
                                    reg = geo_info['region']
                                    zon = geo_info['zone']
                                    ter = ter_name
                                    
                                    # Get sales and achievement values
                                    sal = 0.0
                                    ach = 0.0
                                    try:
                                        v = row.get('SALES_TARGET')
                                        sal = float(v or 0.0)
                                    except: pass
                                    try:
                                        v = row.get('ACCHIVEMENT')
                                        ach = float(v or 0.0)
                                    except: pass
                                    
                                    # Build hierarchy
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
                                        'employee_name': emp_name
                                    })
                                
                                # Convert dicts to sorted lists for rendering
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
                                
                                # Round totals after aggregation
                                for r in final_list:
                                    r['sales'] = round(r['sales'], 2)
                                    r['achievement'] = round(r['achievement'], 2)
                                    for z in r['zones']:
                                        z['sales'] = round(z['sales'], 2)
                                        z['achievement'] = round(z['achievement'], 2)
                                
                                result = final_list
                                
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
                                diagnostics['in_millions'] = (in_millions_param in ('true','1','yes','y'))
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

                            limit_val = 500
                            try:
                                if limit_param:
                                    limit_val = int(limit_param)
                            except Exception:
                                limit_val = 500

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
                            status_param = (request.GET.get('status') or 'active').strip().lower()
                            territory_param = request.GET.get('territory')
                            top_param = request.GET.get('top') or request.GET.get('limit')
                            lim = None
                            try:
                                if top_param:
                                    lim = int(str(top_param).strip())
                            except Exception:
                                lim = None
                            data = customer_lov(
                                conn,
                                (search_param or '').strip() or None,
                                limit=(lim or 5000),
                                status=(status_param or 'active'),
                                territory=(territory_param or '').strip() or None
                            )
                            result = data
                            # Get territories for filter dropdown
                            try:
                                territories = territories_lov(conn)
                            except Exception:
                                territories = []
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
                            
                            # Handle database parameter for admin view - Get schema from Company model
                            if db_param:
                                schema_from_db = None
                                try:
                                    companies = Company.objects.filter(is_active=True)
                                    for company in companies:
                                        if company.Company_name == db_param or company.name == db_param:
                                            schema_from_db = company.name
                                            break
                                except Exception:
                                    pass
                                
                                # Use schema from Company model if found, otherwise use db_param directly
                                cfg['schema'] = schema_from_db if schema_from_db else db_param
                                
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
                                    price_val = price_row.get('U_np') if isinstance(price_row, dict) else None
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
                        # logger.error(f"Failed to load customer list: {e}")
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
    current_user_id = (request.GET.get('user_id') or '').strip()
    current_period = (request.GET.get('period') or '').strip()
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
                    schema_name = cfg['schema']
                    cur.execute(f'SET SCHEMA "{schema_name}"')
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
                    schema_name = cfg['schema']
                    cur.execute(f'SET SCHEMA "{schema_name}"')
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
                    schema_name = cfg['schema']
                    cur.execute(f'SET SCHEMA "{schema_name}"')
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
        default_page_size = 50
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

    geo_totals = None
    try:
        if isinstance(result_rows, list) and result_rows and isinstance(result_rows[0], dict) and isinstance(result_rows[0].get('zones'), list):
            total_sales = 0.0
            total_achievement = 0.0
            total_regions = 0
            total_zones = 0
            total_territories = 0
            for region_row in result_rows:
                total_regions += 1
                try:
                    total_sales += float(region_row.get('sales') or 0.0)
                except Exception:
                    pass
                try:
                    total_achievement += float(region_row.get('achievement') or 0.0)
                except Exception:
                    pass
                for zone_row in (region_row.get('zones') or []):
                    total_zones += 1
                    total_territories += len(zone_row.get('territories') or [])
            geo_totals = {
                'sales': round(total_sales, 2),
                'achievement': round(total_achievement, 2),
                'regions': total_regions,
                'zones': total_zones,
                'territories': total_territories,
            }
    except Exception:
        geo_totals = None

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
    
    # Build product_categories from result_rows for the filter sidebar
    product_categories = []
    if action == 'products_catalog' and result_rows:
        seen_groups = {}
        for row in result_rows:
            if isinstance(row, dict):
                grp_cod = row.get('ItmsGrpCod')
                grp_nam = row.get('ItmsGrpNam', '')
                if grp_cod and grp_cod not in seen_groups:
                    seen_groups[grp_cod] = {'ItmsGrpCod': grp_cod, 'ItmsGrpNam': grp_nam, 'ProductCount': 0}
                if grp_cod:
                    seen_groups[grp_cod]['ProductCount'] += 1
        product_categories = sorted(seen_groups.values(), key=lambda x: x.get('ItmsGrpNam', ''))

    def _safe_int(value, default):
        try:
            if value is None:
                return default
            return int(value)
        except (ValueError, TypeError):
            return default

    req_page = _safe_int(request.GET.get('page'), 1)
    req_page_size = _safe_int(request.GET.get('page_size'), 50)
    
    import json as _json
    try:
        result_rows_json = _json.dumps(paged_rows, default=str)
    except Exception:
        result_rows_json = '[]'

    return render(
        request,
        'admin/sap_integration/hana_connect.html',
        {
            'result_rows_json': result_rows_json,
            'result_json': result_json,
            'error': error,
            'diagnostics': diagnostics,
            'diagnostics_json': diag_json,
            'territories': territories,
            'territory_options': territory_options,
            'geo_options': geo_options,
            'selected_territory': selected_territory,
            'current_action': action,
            'current_emp_id': current_emp_id,
            'current_user_id': current_user_id,
            'current_period': current_period,
            'current_year': current_year,
            'current_month': current_month,
            'current_start_date': current_start_date,
            'current_end_date': current_end_date,
            'months': [],
            'result_rows': paged_rows,
            'result_cols': result_cols,
            'table_rows': table_rows,
            'product_categories': product_categories,
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
            'geo_totals': geo_totals,
            'pagination': {
                'page': (page_obj.number if page_obj else 1) if action != 'products_catalog' else req_page,
                # Fix num_pages calculation for products_catalog to use correct total_count
                'num_pages': ((getattr(request, '_products_catalog_total_count', 0) + page_size - 1) // page_size
                             if action == 'products_catalog' and hasattr(request, '_products_catalog_total_count')
                             else (paginator.num_pages if paginator else 1)),
                # Fix has_next/has_prev for products_catalog to use correct total_count
                'has_next': ((req_page * page_size < getattr(request, '_products_catalog_total_count', 0))
                            if action == 'products_catalog' and hasattr(request, '_products_catalog_total_count')
                            else (page_obj.has_next() if page_obj else False)),
                'has_prev': ((req_page > 1)
                            if action == 'products_catalog' and hasattr(request, '_products_catalog_total_count')
                            else (page_obj.has_previous() if page_obj else False)),
                'next_page': ((req_page + 1 if req_page * page_size < getattr(request, '_products_catalog_total_count', 0) else None)
                             if action == 'products_catalog' and hasattr(request, '_products_catalog_total_count')
                             else (page_obj.next_page_number() if page_obj and page_obj.has_next() else None)),
                'prev_page': ((req_page - 1 if req_page > 1 else None)
                             if action == 'products_catalog' and hasattr(request, '_products_catalog_total_count')
                             else (page_obj.previous_page_number() if page_obj and page_obj.has_previous() else None)),
                # Fix double-pagination bug for products_catalog: use database total_count instead of Django paginator count
                'count': (getattr(request, '_products_catalog_total_count', None) if action == 'products_catalog'
                         else (paginator.count if paginator else len(result_rows))),
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
                
                selected_db = request.session.get('selected_db', get_default_company_key())
                client = SAPClient(company_db_key=selected_db)
                try:
                    # Log the payload for debugging
                    import logging
                    logger = logging.getLogger('sap')
                    # logger.info(f"SAP BP Payload: {json.dumps(payload, indent=2)}")
                    # logger.info(f"SAP Session: {client.get_session_id()}")
                    
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
            selected_db = request.session.get('selected_db', get_default_company_key())
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
        top_param = request.query_params.get('top')
        card_type_param = request.query_params.get('card_type', 'C')
        max_records = 500
        if top_param is not None:
            try:
                max_records = int(top_param)
                if max_records == 0:
                    max_records = 10000
            except Exception:
                max_records = 500

        # Get HANA schema from database parameter, session, or company model
        db_param_received = request.GET.get('database', 'NOT PROVIDED')
        # logger.info(f"[BUSINESS_PARTNER] Received database parameter: {db_param_received}")
        
        hana_schema = get_hana_schema_from_request(request)
        # logger.info(f"[BUSINESS_PARTNER] Using HANA schema: {hana_schema}")

        def _fetch_bp_from_hana(target_card_code=None):
            """Fallback path when SAP Service Layer is unavailable."""
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
                'schema': hana_schema or '',
                'encrypt': os.environ.get('HANA_ENCRYPT') or '',
                'ssl_validate': os.environ.get('HANA_SSL_VALIDATE') or '',
            }

            from hdbcli import dbapi
            pwd = os.environ.get('HANA_PASSWORD', '')
            kwargs = {
                'address': cfg['host'],
                'port': int(cfg['port']),
                'user': cfg['user'] or '',
                'password': pwd or '',
            }
            if str(cfg['encrypt']).strip().lower() in ('true', '1', 'yes'):
                kwargs['encrypt'] = True
                if cfg['ssl_validate']:
                    kwargs['sslValidateCertificate'] = (str(cfg['ssl_validate']).strip().lower() in ('true', '1', 'yes'))

            conn = dbapi.connect(**kwargs)
            try:
                if cfg['schema']:
                    sch = cfg['schema'].replace('"', '""')
                    cur = conn.cursor()
                    cur.execute(f'SET SCHEMA "{sch}"')
                    cur.close()

                card_type_upper = (card_type_param or '').strip().upper()
                query_parts = [
                    'SELECT "CardCode", "CardName", "CardType", "GroupCode", "VatGroup", "Balance" AS "CurrentAccountBalance"',
                    'FROM "OCRD"'
                ]
                where_clauses = []
                params = []

                if target_card_code:
                    where_clauses.append('"CardCode" = ?')
                    params.append(target_card_code)
                elif card_type_upper in ('C', 'S', 'L'):
                    where_clauses.append('"CardType" = ?')
                    params.append(card_type_upper)

                if where_clauses:
                    query_parts.append('WHERE ' + ' AND '.join(where_clauses))

                query_parts.append('ORDER BY "CardCode"')
                if not target_card_code and max_records > 0:
                    query_parts.append(f'LIMIT {int(max_records)}')

                sql = ' '.join(query_parts)
                cur = conn.cursor()
                cur.execute(sql, params)
                columns = [desc[0] for desc in cur.description] if cur.description else []
                rows = cur.fetchall() or []
                cur.close()

                out = []
                card_type_map = {'C': 'cCustomer', 'S': 'cSupplier', 'L': 'cLid'}
                for row in rows:
                    item = {}
                    for idx, col in enumerate(columns):
                        item[col] = row[idx]
                    ct = str(item.get('CardType') or '').strip().upper()
                    if ct in card_type_map:
                        item['CardType'] = card_type_map[ct]
                    try:
                        bal = item.get('CurrentAccountBalance')
                        item['CurrentAccountBalance'] = float(bal) if bal is not None else 0.0
                    except Exception:
                        pass
                    out.append(item)
                return out
            finally:
                try:
                    conn.close()
                except Exception:
                    pass
        
        # Map HANA schema to company_db_key for SAPClient
        # Find matching company from the schema name
        company_db_key = get_default_company_key()
        try:
            # Look up company by schema name (name field)
            company = Company.objects.filter(is_active=True, name=hana_schema).first()
            if company and company.Company_name:
                company_db_key = company.Company_name
            else:
                # Try partial matching for backward compatibility
                if 'BIO' in hana_schema.upper():
                    bio_company = Company.objects.filter(is_active=True, Company_name__icontains='BIO').first()
                    if bio_company:
                        company_db_key = bio_company.Company_name
                elif 'ORANG' in hana_schema.upper():
                    orang_company = Company.objects.filter(is_active=True, Company_name__icontains='ORANG').first()
                    if orang_company:
                        company_db_key = orang_company.Company_name
                elif 'AGRI' in hana_schema.upper():
                    agri_company = Company.objects.filter(is_active=True, Company_name__icontains='AGRI').first()
                    if agri_company:
                        company_db_key = agri_company.Company_name
        except Exception:
            pass
        
        # logger.info(f"[BUSINESS_PARTNER] Using company_db_key: {company_db_key}")
        
        # Create SAP client with logging
        try:
            sap_client = SAPClient(company_db_key=company_db_key)
            # logger.info(f"[BUSINESS_PARTNER] SAPClient created successfully with CompanyDB: {sap_client.company_db}")
        except Exception as e:
            # logger.error(f"[BUSINESS_PARTNER] Failed to create SAPClient: {str(e)}")
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
            # Include CardType in select to enable filtering
            # logger.info(f"[BUSINESS_PARTNER] Fetching business partners (limit: {max_records})")
            
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
                    # logger.info(f"[BUSINESS_PARTNER] End of records reached at skip={skip}")
                    break
                    
                all_rows.extend(batch)
                batch_count += 1
                
                # Log every 10 batches to reduce spam
                if batch_count % 10 == 0 or len(batch) < batch_size:
                    pass  # logger.info(f"[BUSINESS_PARTNER] Fetched {batch_count} batches, total: {len(all_rows)} records")
                
                skip += batch_size
                
                # Safety check
                if batch_count > 500:
                    # logger.warning(f"[BUSINESS_PARTNER] Reached max batch limit (500)")
                    break
            
            rows = all_rows
            # logger.info(f"[BUSINESS_PARTNER] Total retrieved: {len(rows)} records from SAP in {batch_count} batches")
            
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
                # logger.info(f"[BUSINESS_PARTNER] After CardType={card_type_param} filter: {len(rows)} of {original_count} records")
            
            return Response({
                "success": True,
                "count": len(rows),
                "data": rows,
                "message": "Business partners retrieved successfully"
            }, status=status.HTTP_200_OK)
        
    except Exception as e:
        error_message = str(e)

        # Fallback to direct HANA query when SAP Service Layer is unavailable.
        lower_msg = error_message.lower()
        should_fallback = (
            'ssl' in lower_msg or
            'service layer' in lower_msg or
            'tlsv1_alert_internal_error' in lower_msg or
            'alert internal error' in lower_msg
        )
        if should_fallback:
            try:
                fallback_rows = _fetch_bp_from_hana(card_code.strip() if card_code and card_code.strip() else None)
                if card_code and card_code.strip():
                    if not fallback_rows:
                        return Response({
                            "success": False,
                            "error": "Business partner not found",
                            "message": f"No business partner found with card code: {card_code}"
                        }, status=status.HTTP_404_NOT_FOUND)
                    return Response({
                        "success": True,
                        "data": fallback_rows[0],
                        "message": "Business partner data retrieved successfully (HANA fallback)"
                    }, status=status.HTTP_200_OK)

                return Response({
                    "success": True,
                    "count": len(fallback_rows),
                    "data": fallback_rows,
                    "message": "Business partners retrieved successfully (HANA fallback)"
                }, status=status.HTTP_200_OK)
            except Exception as fallback_error:
                return Response({
                    "success": False,
                    "error": "SAP integration failed",
                    "message": (
                        f"Unable to retrieve business partner data. Service Layer error: {error_message}. "
                        f"HANA fallback also failed: {str(fallback_error)}"
                    )
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
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
    operation_description="""
    List all policies from SAP Projects (UDF U_pol).
    
    **Default Behavior**: Returns only VALID policies (where U_InvEndDate or U_Ct has not passed).
    
    **is_valid Field**: Automatically calculated based on U_InvEndDate and U_Ct (custom fields):
    - `true`: Policy is still valid (U_InvEndDate >= current date OR U_Ct >= current date)
    - `false`: Policy has expired (both U_InvEndDate and U_Ct < current date)
    
    **Note**: Uses U_InvEndDate or U_Ct (not ValidTo) for validity checks.
    
    **Query Parameters**:
    - `database` or `company`: Specify company database (e.g., 4B-BIO_APP, 4B-AGRI_LIVE)
    - `active`: Filter by Active status in SAP (true/false)
    - `is_valid`: Filter by validity (true/false). Default: true
    
    **Examples**:
    - `/api/sap/policies/?database=4B-AGRI_LIVE` - Only valid policies (default)
    - `/api/sap/policies/?database=4B-AGRI_LIVE&is_valid=false` - Only expired policies
    - `/api/sap/policies/?database=4B-AGRI_LIVE&active=true` - Only active AND valid policies
    """,
    manual_parameters=[
        openapi.Parameter(
            'database',
            openapi.IN_QUERY,
            description="Company database (e.g., 4B-BIO_APP, 4B-AGRI_LIVE, 4B-ORANG_APP)",
            type=openapi.TYPE_STRING,
            required=False
        ),
        openapi.Parameter(
            'company',
            openapi.IN_QUERY,
            description="Company database key (alternative to 'database' parameter for backward compatibility)",
            type=openapi.TYPE_STRING,
            required=False
        ),
        openapi.Parameter(
            'active',
            openapi.IN_QUERY,
            description="Filter by Active status in SAP Projects (true/false). Independent of is_valid filter.",
            type=openapi.TYPE_BOOLEAN,
            required=False
        ),
        openapi.Parameter(
            'is_valid',
            openapi.IN_QUERY,
            description="Filter by policy validity based on U_InvEndDate or U_Ct. Default: true (only returns policies where U_InvEndDate >= current date OR U_Ct >= current date). Set to false to get expired policies only.",
            type=openapi.TYPE_BOOLEAN,
            required=False,
            default=True
        )
    ],
    responses={
        200: openapi.Response(
            description="Policies retrieved successfully. Each policy includes is_valid field with calculated validity status.",
            examples={
                "application/json": {
                    "success": True,
                    "count": 2,
                    "database": "4B-AGRI_LIVE",
                    "data": [
                        {
                            "code": "0123003",
                            "name": "Current Policy 2026",
                            "valid_from": "2026-01-01T00:00:00",
                            "valid_to": "2027-12-31T00:00:00",
                            "u_inv_end_date": "2027-12-31T00:00:00",
                            "u_ct": "2027-12-31T00:00:00",
                            "active": "tYES",
                            "policy": "05",
                            "is_valid": True
                        },
                        {
                            "code": "0123001",
                            "name": "Expired Policy 2022",
                            "valid_from": "2023-01-01T00:00:00",
                            "valid_to": "2025-12-31T00:00:00",
                            "u_inv_end_date": "2025-12-31T00:00:00",
                            "u_ct": "2025-12-31T00:00:00",
                            "active": "tYES",
                            "policy": "03",
                            "is_valid": False
                        }
                    ],
                    "message": "Policies retrieved successfully"
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
    Optional parameters:
    - company: Company database (e.g., 4B-BIO_APP, 4B-ORANG_APP)
    - database: Alias for company parameter (backward compatibility)
    - active: Filter by active status (true/false)
    - is_valid: Filter by validity based on U_InvEndDate or U_Ct (true/false). Default: true
    
    By default, only returns policies where is_valid=true (not expired based on U_InvEndDate or U_Ct).
    To see all policies including expired: ?is_valid=false or pass no filter
    """
    import logging
    import socket
    import json
    
    logger = logging.getLogger(__name__)
    
    try:
        # Priority: 1. company parameter, 2. database parameter (backward compatibility), 3. Session, 4. Default
        company_param = request.GET.get('company') or request.query_params.get('company')
        database_param = request.GET.get('database') or request.query_params.get('database')
        
        # Normalize company parameter (remove _APP suffix for SAPClient)
        if company_param:
            selected_db = company_param.replace('_APP', '').replace('-APP', '')
        elif database_param:
            selected_db = database_param.replace('_APP', '').replace('-APP', '')
        else:
            selected_db = request.session.get('selected_db', get_default_company_key())
        
        # logger.info(f"[SAP POLICIES] Fetching policies for database: {selected_db}")
        
        sap_client = SAPClient(company_db_key=selected_db)
        policies = sap_client.get_all_policies()

        # Filter by active status if provided
        active_param = request.query_params.get('active')
        if active_param is not None:
            active_val = str(active_param).lower() in ('true', '1', 'yes')
            policies = [p for p in policies if bool(p.get('active')) == active_val]
        
        # Filter by is_valid (default: true - only show valid policies)
        is_valid_param = request.query_params.get('is_valid')
        if is_valid_param is None:
            # Default behavior: only show valid policies
            policies = [p for p in policies if p.get('is_valid', True)]
        else:
            # Explicit filter provided
            is_valid_val = str(is_valid_param).lower() in ('true', '1', 'yes')
            policies = [p for p in policies if p.get('is_valid', True) == is_valid_val]

        return Response({
            "success": True,
            "count": len(policies),
            "database": selected_db,
            "data": policies,
            "message": "Policies retrieved successfully"
        }, status=status.HTTP_200_OK)

    except socket.timeout:
        # logger.error(f"[SAP POLICIES] Connection timeout - SAP server not responding")
        return Response({
            "success": False,
            "error": "Connection Timeout",
            "message": "SAP server is not responding. The server may be down or network connection is slow. Please contact your system administrator.",
            "troubleshooting": [
                "Check if SAP server is running",
                "Verify network/VPN connection",
                "Check firewall settings",
                "Run diagnose_sap_policies.py for detailed diagnostics"
            ]
        }, status=status.HTTP_504_GATEWAY_TIMEOUT)
    except socket.error as e:
        error_msg = str(e)
        # logger.error(f"[SAP POLICIES] Network error: {error_msg}")
        
        # WinError 10060 is connection timeout
        if "10060" in error_msg or "timed out" in error_msg.lower():
            return Response({
                "success": False,
                "error": "Connection Timeout",
                "message": "Cannot connect to SAP server. Connection timed out after 60 seconds.",
                "details": error_msg,
                "troubleshooting": [
                    "Verify SAP server is accessible",
                    "Check network connectivity",
                    "Ensure you are connected to the correct network/VPN",
                    "Check if firewall is blocking the connection",
                    "Run: python diagnose_sap_policies.py"
                ]
            }, status=status.HTTP_504_GATEWAY_TIMEOUT)
        else:
            return Response({
                "success": False,
                "error": "Network Error",
                "message": f"Network error while connecting to SAP: {error_msg}",
                "troubleshooting": [
                    "Check network connection",
                    "Verify SAP server status",
                    "Run: python diagnose_sap_policies.py"
                ]
            }, status=status.HTTP_502_BAD_GATEWAY)
    except Exception as e:
        error_msg = str(e)
        # logger.error(f"[SAP POLICIES] Error: {error_msg}")
        
        # Check for cache refresh failure (SAP internal error)
        if 'cache refresh failure' in error_msg.lower():
            return Response({
                "success": False,
                "error": "SAP Cache Error",
                "message": "SAP server cache refresh failed. This is usually temporary.",
                "details": error_msg,
                "troubleshooting": [
                    "Wait a few seconds and try again",
                    "Try with database parameter: ?database=4B-BIO or ?database=4B-ORANG",
                    "Clear your browser cache/cookies",
                    "Check if SAP server is under heavy load",
                    "Contact SAP administrator if issue persists"
                ],
                "retry_suggestion": "Try: /api/sap/policies/?database=4B-BIO"
            }, status=status.HTTP_503_SERVICE_UNAVAILABLE)
        
        # Check if it's a timeout-related error
        if any(keyword in error_msg.lower() for keyword in ['timeout', '10060', 'timed out']):
            return Response({
                "success": False,
                "error": "Connection Timeout",
                "message": "SAP server connection timed out. Server may be slow or unreachable.",
                "details": error_msg,
                "troubleshooting": [
                    "Check SAP server status",
                    "Verify network connection",
                    "Run diagnostic: python diagnose_sap_policies.py"
                ]
            }, status=status.HTTP_504_GATEWAY_TIMEOUT)
        
        # Check for session/authentication errors
        if any(keyword in error_msg.lower() for keyword in ['invalid session', 'authentication', 'unauthorized', 'session timeout']):
            return Response({
                "success": False,
                "error": "SAP Authentication Error",
                "message": "SAP authentication failed or session expired.",
                "details": error_msg,
                "troubleshooting": [
                    "Check SAP credentials in settings",
                    "Verify SAP user permissions",
                    "Run diagnostic: python diagnose_sap_policies.py"
                ]
            }, status=status.HTTP_401_UNAUTHORIZED)
        
        return Response({
            "success": False,
            "error": "SAP integration failed",
            "message": error_msg,
            "selected_database": selected_db,
            "troubleshooting": "Run: python diagnose_sap_policies.py for detailed diagnostics"
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
    manual_parameters=[
        openapi.Parameter(
            'database',
            openapi.IN_QUERY,
            description="Company database (e.g., 4B-BIO_APP, 4B-ORANG_APP)",
            type=openapi.TYPE_STRING,
            required=False
        ),
        openapi.Parameter(
            'company',
            openapi.IN_QUERY,
            description="Company database key (alternative to 'database' parameter)",
            type=openapi.TYPE_STRING,
            required=False
        )
    ],
    responses={
        200: openapi.Response(description="Sync completed")
    }
)
@api_view(['POST'])
def sync_policies(request):
    # Priority: 1. company parameter, 2. database parameter (backward compatibility), 3. Session, 4. Default
    company_param = request.GET.get('company') or request.query_params.get('company')
    database_param = request.GET.get('database') or request.query_params.get('database')
    
    # Normalize company parameter (remove _APP suffix for SAPClient)
    if company_param:
        selected_db = company_param.replace('_APP', '').replace('-APP', '')
    elif database_param:
        selected_db = database_param.replace('_APP', '').replace('-APP', '')
    else:
        selected_db = request.session.get('selected_db', get_default_company_key())
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
        openapi.Parameter('database', openapi.IN_QUERY, description="Database/schema (e.g., 4B-BIO, 4B-ORANG, 4B-BIO_APP, 4B-ORANG_APP)", type=openapi.TYPE_STRING, required=False),
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
        'schema': os.environ.get('HANA_SCHEMA') or '',
        'encrypt': os.environ.get('HANA_ENCRYPT') or '',
        'ssl_validate': os.environ.get('HANA_SSL_VALIDATE') or '',
    }
    
    # Get database options from Company model
    db_param = (request.query_params.get('database') or '').strip()
    db_options = {}
    try:
        companies = Company.objects.filter(is_active=True)
        for company in companies:
            # Map Company_name to schema name (name field)
            db_options[company.Company_name] = company.name
    except Exception:
        pass
    
    # Select schema based on db_param
    if db_param and db_param in db_options:
        cfg['schema'] = db_options[db_param]
    elif db_param:
        # Try to use db_param directly as schema name
        cfg['schema'] = db_param
    else:
        # Use first available company schema
        cfg['schema'] = list(db_options.values())[0] if db_options else ''
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
        openapi.Parameter('database', openapi.IN_QUERY, description="Database/schema (e.g., 4B-BIO, 4B-ORANG, 4B-BIO_APP, 4B-ORANG_APP)", type=openapi.TYPE_STRING, required=False),
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
    cfg = {'host': os.environ.get('HANA_HOST') or '', 'port': os.environ.get('HANA_PORT') or '30015', 'user': os.environ.get('HANA_USER') or '', 'schema': os.environ.get('HANA_SCHEMA') or '', 'encrypt': os.environ.get('HANA_ENCRYPT') or '', 'ssl_validate': os.environ.get('HANA_SSL_VALIDATE') or ''}
    
    # Get database options from Company model
    db_param = (request.query_params.get('database') or '').strip()
    db_options = {}
    try:
        companies = Company.objects.filter(is_active=True)
        for company in companies:
            # Map Company_name to schema name (name field)
            db_options[company.Company_name] = company.name
    except Exception:
        pass
    
    # Select schema based on db_param
    if db_param and db_param in db_options:
        cfg['schema'] = db_options[db_param]
    elif db_param:
        # Try to use db_param directly as schema name
        cfg['schema'] = db_param
    else:
        # Use first available company schema
        cfg['schema'] = list(db_options.values())[0] if db_options else ''
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
    operation_summary="Sales Analytics - Orders/Invoices vs Target",
    operation_description="""
    📈 **SALES ANALYTICS** - Track sales orders and invoices against sales targets
    
    🔑 **What This Endpoint Measures:**
    - ✅ **Sales Target**: Expected sales/order value targets
    - ✅ **Sales Achievement**: Actual sales orders placed/invoiced
    - ✅ **Focus**: Orders OUT (sales orders, invoices, bookings)
    - ✅ **Use Case**: Track sales performance, order volume, revenue generation
    - ✅ **Data Source**: B4_SALES_TARGET table in SAP HANA
    
    ⚠️ **Not For Collection Data** - Use `/analytics/collection/` for payment receipts/collections
    
    Get Sales vs Achievement data with hierarchical structure (Region → Zone → Territory).
    
    **User & Employee Tracking:**
    - Response includes `user_id` (portal user) and `employee_id` (from sales_profile)
    - Use `user_id` parameter to fetch data for a specific portal user (auto-fetches employee_code)
    - Use `emp_id` parameter for direct SAP employee ID lookup
    
    **Date Filtering Options (Priority Order):**
    
    1. *Custom Date Range (Highest Priority):*
       - `start_date` and `end_date` (YYYY-MM-DD format)
       - Example: `?start_date=2026-01-01&end_date=2026-01-31`
    
    2. *Year/Month Filters:*
       - `year=2026` - Full year (Jan 1 - Dec 31, 2026)
       - `year=2026&month=3` - Specific month (March 2026)
       - Example: `?year=2026&month=3`
    
    3. *Quick Period Filters:*
       - `period=today` - Today's data
       - `period=monthly` - Current month to date
       - `period=yearly` - Current year to date
    
    4. *Default:* Current month if no date parameters provided
    
    **Usage Examples:**
    - Full year: `?database=4B-AGRI_LIVE&year=2026`
    - Specific month: `?database=4B-AGRI_LIVE&year=2026&month=3`
    - Today: `?database=4B-BIO&period=today`
    - User's monthly: `?database=4B-BIO&user_id=123&period=monthly`
    - Date range: `?database=4B-BIO&start_date=2026-01-01&end_date=2026-03-31`
    - Region filter: `?database=4B-BIO&region=North&period=yearly&in_millions=true`
    """,
    manual_parameters=[
        openapi.Parameter('database', openapi.IN_QUERY, description="Database/schema (e.g., 4B-BIO, 4B-ORANG, 4B-BIO_APP, 4B-ORANG_APP)", type=openapi.TYPE_STRING, required=False),
        openapi.Parameter('user_id', openapi.IN_QUERY, description="Portal User ID - Auto-fetches employee_code. Example: user_id=123", type=openapi.TYPE_INTEGER, required=False),
        openapi.Parameter('emp_id', openapi.IN_QUERY, description="SAP Employee ID - Overrides user_id. Example: emp_id=456", type=openapi.TYPE_INTEGER, required=False),
        openapi.Parameter('year', openapi.IN_QUERY, description="Year filter (YYYY). Example: 2026. Can be combined with month. Takes priority over period parameter.", type=openapi.TYPE_INTEGER, required=False),
        openapi.Parameter('month', openapi.IN_QUERY, description="Month filter (1-12). Must be used with year parameter. Example: month=3 for March", type=openapi.TYPE_INTEGER, required=False),
        openapi.Parameter('period', openapi.IN_QUERY, description="Quick date filter - 'today', 'monthly', or 'yearly'. Overrides start_date/end_date.", type=openapi.TYPE_STRING, enum=['today', 'monthly', 'yearly'], required=False),
        openapi.Parameter('start_date', openapi.IN_QUERY, description="Start date (YYYY-MM-DD). Ignored if 'period' or 'year' provided. Example: 2026-01-01", type=openapi.TYPE_STRING),
        openapi.Parameter('end_date', openapi.IN_QUERY, description="End date (YYYY-MM-DD). Ignored if 'period' or 'year' provided. Example: 2026-01-31", type=openapi.TYPE_STRING),
        openapi.Parameter('region', openapi.IN_QUERY, description="Filter by region name", type=openapi.TYPE_STRING),
        openapi.Parameter('zone', openapi.IN_QUERY, description="Filter by zone name", type=openapi.TYPE_STRING),
        openapi.Parameter('territory', openapi.IN_QUERY, description="Filter by territory name", type=openapi.TYPE_STRING),
        openapi.Parameter('in_millions', openapi.IN_QUERY, description="Convert values to millions for readability. Default: false", type=openapi.TYPE_BOOLEAN),
        openapi.Parameter('group_by_emp', openapi.IN_QUERY, description="Group results by employee. Returns employee-wise breakdown. Default: false", type=openapi.TYPE_BOOLEAN, default=False),
        openapi.Parameter('page', openapi.IN_QUERY, description="Page number. Default: 1", type=openapi.TYPE_INTEGER, default=1),
        openapi.Parameter('page_size', openapi.IN_QUERY, description="Items per page. Default: 10", type=openapi.TYPE_INTEGER, default=10),
    ],
    responses={200: openapi.Response(description="Sales data with user_id and employee_id"), 400: openapi.Response(description="Bad Request"), 500: openapi.Response(description="Server Error")}
)
@api_view(['GET'])
def sales_vs_achievement_territory_api(request):
    print("\n🚨🚨🚨 EMERGENCY DEBUG: sales_vs_achievement_territory_api() WAS CALLED! 🚨🚨🚨")
    print(f"🚨 If you see this message, the debugging is working! Full URL: {request.get_full_path()}")
    print("🚨🚨🚨🚨🚨🚨🚨🚨🚨🚨🚨🚨🚨🚨🚨🚨🚨🚨🚨🚨🚨🚨🚨🚨🚨🚨🚨🚨")

    try:
        _hana_load_env_file(os.path.join(os.path.dirname(__file__), '.env'))
        _hana_load_env_file(os.path.join(str(settings.BASE_DIR), '.env'))
        _hana_load_env_file(os.path.join(str(Path(settings.BASE_DIR).parent), '.env'))
        _hana_load_env_file(os.path.join(os.getcwd(), '.env'))
    except Exception:
        pass
    cfg = {'host': os.environ.get('HANA_HOST') or '', 'port': os.environ.get('HANA_PORT') or '30015', 'user': os.environ.get('HANA_USER') or '', 'schema': os.environ.get('HANA_SCHEMA') or '', 'encrypt': os.environ.get('HANA_ENCRYPT') or '', 'ssl_validate': os.environ.get('HANA_SSL_VALIDATE') or ''}
    
    # Get database options from Company model
    db_param = (request.query_params.get('database') or '').strip()
    db_options = {}
    try:
        from FieldAdvisoryService.models import Company
        companies = Company.objects.filter(is_active=True)
        for company in companies:
            # Map Company_name to schema name (name field)
            db_options[company.Company_name] = company.name
    except Exception:
        pass
    
    # Select schema based on db_param
    if db_param and db_param in db_options:
        cfg['schema'] = db_options[db_param]
    elif db_param:
        # Try to use db_param directly as schema name
        cfg['schema'] = db_param
    else:
        # Use first available company schema or default
        cfg['schema'] = list(db_options.values())[0] if db_options else get_default_schema()
    
    # Handle period parameter
    period = (request.query_params.get('period') or '').strip().lower()
    start_date = (request.query_params.get('start_date') or '').strip()
    end_date = (request.query_params.get('end_date') or '').strip()
    year_param = (request.query_params.get('year') or '').strip()
    month_param = (request.query_params.get('month') or '').strip()
    
    # Calculate dates based on period (only if period explicitly provided)
    from datetime import datetime, date
    from calendar import monthrange
    today = date.today()
    
    # Priority 1: Explicit start_date and end_date provided
    # Priority 2: year and month parameters
    # Priority 3: period parameter
    # Priority 4: Default to current month
    
    if not start_date and not end_date and year_param and month_param:
        # Year and month parameters provided
        try:
            year_val = int(year_param)
            month_val = int(month_param)
            if 1 <= month_val <= 12:
                start_date = date(year_val, month_val, 1).strftime('%Y-%m-%d')
                last_day = monthrange(year_val, month_val)[1]
                end_date = date(year_val, month_val, last_day).strftime('%Y-%m-%d')
        except Exception:
            pass
    elif not start_date and not end_date and year_param:
        # Only year parameter provided - use full year
        try:
            year_val = int(year_param)
            start_date = date(year_val, 1, 1).strftime('%Y-%m-%d')
            end_date = date(year_val, 12, 31).strftime('%Y-%m-%d')
        except Exception:
            pass
    elif period and not start_date and not end_date:
        # Period parameter explicitly provided - use it
        if period == 'today':
            start_date = today.strftime('%Y-%m-%d')
            end_date = today.strftime('%Y-%m-%d')
        elif period == 'monthly':
            start_date = today.replace(day=1).strftime('%Y-%m-%d')
            last_day = monthrange(today.year, today.month)[1]
            end_date = today.replace(day=last_day).strftime('%Y-%m-%d')
        elif period == 'yearly':
            start_date = today.replace(month=1, day=1).strftime('%Y-%m-%d')
            end_date = today.replace(month=12, day=31).strftime('%Y-%m-%d')
    
    # If no period and no dates provided, default to current month
    if not period and not start_date and not end_date and not year_param:
        start_date = today.replace(day=1).strftime('%Y-%m-%d')
        last_day = monthrange(today.year, today.month)[1]
        end_date = today.replace(day=last_day).strftime('%Y-%m-%d')
    
    # Handle user_id and emp_id parameters
    user_id_param = request.query_params.get('user_id', '').strip()
    emp_id_param = request.query_params.get('emp_id', '').strip()
    
    emp_val = None
    employee_code = None  # Track original employee_code for CEO check
    
    # If user_id provided, fetch employee_code from sales_profile
    if user_id_param:
        try:
            from accounts.models import User
            user_id_int = int(user_id_param)
            target_user = User.objects.select_related('sales_profile').get(id=user_id_int)
            if hasattr(target_user, 'sales_profile') and target_user.sales_profile:
                employee_code = target_user.sales_profile.employee_code
                if employee_code:
                    try:
                        emp_val = int(employee_code)
                    except ValueError:
                        pass
        except Exception:
            pass
    
    # emp_id overrides user_id if both provided
    if emp_id_param:
        try:
            employee_code = emp_id_param  # Track the string value
            emp_val = int(emp_id_param)
        except Exception:
            pass
    
    region = (request.query_params.get('region') or '').strip()
    zone = (request.query_params.get('zone') or '').strip()
    territory = (request.query_params.get('territory') or '').strip()
    in_millions_param = (request.query_params.get('in_millions') or '').strip().lower()
    
    # Handle group_by_emp parameter for employee-wise grouping
    group_by_emp_param = (request.query_params.get('group_by_emp') or '').strip().lower()
    group_by_emp = group_by_emp_param in ('true', '1', 'yes', 'y')
    
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
            
            # DEBUG: sales territory parameters
            print(f"[DEBUG sales_vs_achievement_territory_api] schema={cfg['schema']}, emp_id={emp_val}, dates={start_date} to {end_date}, period={period if period else 'None'}")
            
            # CEO special case: employee_code='00' should see ALL territories
            # When employee_code is '00', ignore employee filter to show organization-wide data
            ignore_emp_filter = False
            if employee_code == '00':
                ignore_emp_filter = True
                emp_val = None  # Don't pass emp_id to query
            
            # Use the new sales_vs_achievement_territory function with B4_SALES_TARGET

            # DEBUG: Log API call parameters
            print("\n" + "="*100)
            print("DEBUG: API ENDPOINT - sales_vs_achievement_territory_api() called")
            print("="*100)
            print(f"DEBUG: Request URL: {request.get_full_path()}")
            print(f"DEBUG: Database schema: {cfg.get('schema', 'N/A')}")
            print(f"DEBUG: Connection established: {conn is not None}")
            print(f"DEBUG: Parameters being passed to hana_connect function:")
            print(f"  - emp_id: {emp_val}")
            print(f"  - region: {region or None}")
            print(f"  - zone: {zone or None}")
            print(f"  - territory: {territory or None}")
            print(f"  - start_date: {start_date or None}")
            print(f"  - end_date: {end_date or None}")
            print(f"  - group_by_date: False")
            print(f"  - ignore_emp_filter: {ignore_emp_filter}")
            print(f"  - group_by_emp: {group_by_emp}")
            print(f"DEBUG: Employee special handling:")
            print(f"  - employee_code from request: {employee_code}")
            print(f"  - CEO mode (code='00'): {employee_code == '00'}")
            print(f"  - emp_val after processing: {emp_val}")
            print("="*100)

            data = sales_vs_achievement_territory(conn, emp_id=emp_val, region=region or None, zone=zone or None, territory=territory or None, start_date=start_date or None, end_date=end_date or None, group_by_date=False, ignore_emp_filter=ignore_emp_filter, group_by_emp=group_by_emp)
            
            # DEBUG: row data structure
            if data and len(data) > 0:
                print(f"[DEBUG sales_vs_achievement_territory_api] Total rows returned: {len(data)}")
                print(f"[DEBUG sales_vs_achievement_territory_api] First row: {data[0] if data else 'No data'}")
                if len(data) > 1:
                    print(f"[DEBUG sales_vs_achievement_territory_api] Second row: {data[1]}")
            
            if in_millions_param in ('true','1','yes','y'):
                scaled = []
                for row in data or []:
                    if isinstance(row, dict):
                        r = dict(row)
                        try:
                            v = r.get('Sales_Target')
                            if v is not None:
                                r['Sales_Target'] = round((float(v) / 1000000.0), 2)
                        except Exception:
                            pass
                        try:
                            v = r.get('Sales_Achievement')
                            if v is not None:
                                r['Sales_Achievement'] = round((float(v) / 1000000.0), 2)
                        except Exception:
                            pass
                        try:
                            v = r.get('Zone_Sales_Target')
                            if v is not None:
                                r['Zone_Sales_Target'] = round((float(v) / 1000000.0), 2)
                        except Exception:
                            pass
                        try:
                            v = r.get('Zone_Sales_Achievement')
                            if v is not None:
                                r['Zone_Sales_Achievement'] = round((float(v) / 1000000.0), 2)
                        except Exception:
                            pass
                        try:
                            v = r.get('Region_Sales_Target')
                            if v is not None:
                                r['Region_Sales_Target'] = round((float(v) / 1000000.0), 2)
                        except Exception:
                            pass
                        try:
                            v = r.get('Region_Sales_Achievement')
                            if v is not None:
                                r['Region_Sales_Achievement'] = round((float(v) / 1000000.0), 2)
                        except Exception:
                            pass
                        scaled.append(r)
                    else:
                        scaled.append(row)
                data = scaled
            
            # Helper function to clean region/zone/territory names
            def clean_geo_name(name):
                """Remove ' Region', ' Zone', ' Territory' suffixes from location names"""
                if not name or not isinstance(name, str):
                    return name
                # Remove common suffixes
                for suffix in [' Region', ' Zone', ' Territory']:
                    if name.endswith(suffix):
                        return name[:-len(suffix)].strip()
                return name
            
            # Handle employee-wise grouping differently
            if group_by_emp:
                # For employee-wise data, return a flat list with employee details
                emp_list = []
                total_sales = 0.0
                total_achievement = 0.0
                
                for row in (data or []):
                    if not isinstance(row, dict):
                        continue
                    
                    emp_id_val = row.get('EmpId')
                    reg = row.get('Region') or 'N/A'
                    zon = row.get('Zone') or 'N/A'
                    ter = row.get('TerritoryName') or 'N/A'
                    
                    # Clean the names to remove suffixes
                    reg = clean_geo_name(reg)
                    zon = clean_geo_name(zon)
                    ter = clean_geo_name(ter)
                    
                    sal = 0.0
                    ach = 0.0
                    try:
                        sal = float(row.get('Sales_Target') or 0.0)
                    except Exception:
                        pass
                    try:
                        ach = float(row.get('Sales_Achievement') or 0.0)
                    except Exception:
                        pass
                    
                    total_sales += sal
                    total_achievement += ach
                    
                    emp_list.append({
                        'emp_id': emp_id_val,
                        'region': reg,
                        'zone': zon,
                        'territory': ter,
                        'sales_target': round(sal, 2),
                        'sales_achievement': round(ach, 2),
                        'variance': round(ach - sal, 2),
                        'variance_pct': round((ach - sal) / sal * 100, 2) if sal > 0 else 0,
                        'from_date': row.get('From_Date'),
                        'to_date': row.get('To_Date'),
                    })
                
                final_list = emp_list
            else:
                # Original hierarchical grouping
                hierarchy = {}
                total_sales = 0.0
                total_achievement = 0.0
                for row in (data or []):
                    if not isinstance(row, dict):
                        continue
                    # Skip the GRAND TOTAL row in hierarchy building (will add separately)
                    if row.get('Region') == 'GRAND TOTAL':
                        continue
                        
                    reg = row.get('Region') or 'Unknown Region'
                    zon = row.get('Zone') or 'Unknown Zone'
                    ter = row.get('TerritoryName') or row.get('Territory') or 'Unknown Territory'
                    
                    # Clean the names to remove suffixes
                    reg = clean_geo_name(reg)
                    zon = clean_geo_name(zon)
                    ter = clean_geo_name(ter)
                    
                    # Territory-level values
                    sal = 0.0
                    ach = 0.0
                    try:
                        v = row.get('Sales_Target')
                        sal = float(v or 0.0)
                    except Exception:
                        pass
                    try:
                        v = row.get('Sales_Achievement')
                        ach = float(v or 0.0)
                    except Exception:
                        pass
                    
                    # Window function values (pre-calculated by SQL)
                    zone_sal = 0.0
                    zone_ach = 0.0
                    region_sal = 0.0
                    region_ach = 0.0
                    try:
                        zone_sal = float(row.get('Zone_Sales_Target') or 0.0)
                    except Exception:
                        pass
                    try:
                        zone_ach = float(row.get('Zone_Sales_Achievement') or 0.0)
                    except Exception:
                        pass
                    try:
                        region_sal = float(row.get('Region_Sales_Target') or 0.0)
                    except Exception:
                        pass
                    try:
                        region_ach = float(row.get('Region_Sales_Achievement') or 0.0)
                    except Exception:
                        pass
                    
                    total_sales += sal
                    total_achievement += ach
                    
                    # Use window function values for region totals (not summing)
                    if reg not in hierarchy:
                        hierarchy[reg] = {'name': reg, 'sales': region_sal, 'achievement': region_ach, 'zones': {}}
                    
                    # Use window function values for zone totals (not summing)
                    if zon not in hierarchy[reg]['zones']:
                        hierarchy[reg]['zones'][zon] = {'name': zon, 'sales': zone_sal, 'achievement': zone_ach, 'territories': []}
                    
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
            
            # Build response with user and employee information
            response_data = {
                'success': True,
                'count': (paginator.count if paginator else len(final_list or [])),
                'data': paged_rows,
                'pagination': pagination,
                'totals': {
                    'sales': round(total_sales, 2),
                    'achievement': round(total_achievement, 2),
                },
            }
            
            # Add user and employee info if user_id or emp_id was provided
            if user_id_param:
                response_data['user_id'] = int(user_id_param) if user_id_param else None
                response_data['employee_id'] = emp_val  # The fetched employee code
            elif emp_id_param:
                response_data['employee_id'] = emp_val
            
            return Response(response_data, status=status.HTTP_200_OK)
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
        openapi.Parameter('database', openapi.IN_QUERY, description="Database/schema (e.g., 4B-BIO, 4B-ORANG, 4B-BIO_APP, 4B-ORANG_APP)", type=openapi.TYPE_STRING, required=False),
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
        'schema': '',
        'encrypt': os.environ.get('HANA_ENCRYPT') or '',
        'ssl_validate': os.environ.get('HANA_SSL_VALIDATE') or '',
    }
    # Use shared helper to resolve schema from Company model
    cfg['schema'] = get_hana_schema_from_request(request)
    
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
        # DEBUG: Enhanced error logging for B4_SALES_TARGET issues
        print("\n" + "!"*100)
        print("DEBUG: EXCEPTION CAUGHT in sales_vs_achievement_territory_api")
        print("!"*100)
        print(f"DEBUG: Exception type: {type(e).__name__}")
        print(f"DEBUG: Exception message: {str(e)}")
        print(f"DEBUG: Request URL: {request.get_full_path()}")

        # Check if it's the B4_SALES_TARGET error
        if "B4_SALES_TARGET" in str(e):
            print("DEBUG: This is the B4_SALES_TARGET missing table error!")
            print("DEBUG: Root cause: The table B4_SALES_TARGET does not exist in your SAP HANA database")
            print("DEBUG: Possible solutions:")
            print("  1. Create B4_SALES_TARGET table in SAP Business One")
            print("  2. Use an alternative existing table")
            print("  3. Check if data should come from a different source")

        # Print stack trace for debugging
        import traceback
        print("DEBUG: Full stack trace:")
        traceback.print_exc()
        print("!"*100)

        return Response({'success': False, 'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@swagger_auto_schema(tags=['SAP'], 
    method='get',
    operation_description="Territory summary data",
    manual_parameters=[
        openapi.Parameter('database', openapi.IN_QUERY, description="Database/schema (e.g., 4B-BIO, 4B-ORANG, 4B-BIO_APP, 4B-ORANG_APP)", type=openapi.TYPE_STRING, required=False),
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
        'schema': '',
        'encrypt': os.environ.get('HANA_ENCRYPT') or '',
        'ssl_validate': os.environ.get('HANA_SSL_VALIDATE') or '',
    }
    # Use shared helper to resolve schema from Company model
    cfg['schema'] = get_hana_schema_from_request(request)
    
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

@swagger_auto_schema(tags=['SAP - Products'], 
    method='get',
    operation_description="""Products catalog with images and document links based on database. 
    
    Features:
    - Product images from media/product_images/{database}/
    - Document description links (for products with Word documents)
    - Search and filter by category
    - Pagination support
    
    Each product includes:
    - product_image_url: URL to product image
    - product_description_urdu_url: URL to download Word document
    - document_detail_url: URL to view formatted document (if available)
    - document_detail_page_url: Full URL to document detail page
    """,
    manual_parameters=[
        openapi.Parameter('database', openapi.IN_QUERY, description="Database name (e.g., 4B-BIO_APP, 4B-ORANG_APP). Uses default from env if not provided.", type=openapi.TYPE_STRING, required=False),
        openapi.Parameter('search', openapi.IN_QUERY, description="Search by ItemCode, ItemName, GenericName, or BrandName (e.g., 'baap', 'roshan', 'FG00023')", type=openapi.TYPE_STRING, required=False),
        openapi.Parameter('item_group', openapi.IN_QUERY, description="Filter by item group code", type=openapi.TYPE_STRING, required=False),
        openapi.Parameter('is_active', openapi.IN_QUERY, description="Filter by active status: 'Y' for active (default), 'N' for inactive, or leave empty for all products", type=openapi.TYPE_STRING, required=False, default='Y'),
        openapi.Parameter('only_priced', openapi.IN_QUERY, description="Show only products with price > 0 (true/false)", type=openapi.TYPE_BOOLEAN, required=False),
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
    is_active = (request.GET.get('is_active') or 'Y').strip() or 'Y'  # Default to 'Y' (active products)
    only_priced = request.GET.get('only_priced', '').strip().lower() in ('true', '1', 'yes')
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
            
            # Pass pagination parameters to products_catalog for database-level pagination
            result = products_catalog(conn, cfg['schema'], search, item_group, limit=page_size, offset=(page_num-1)*page_size, fetch_prices=True, only_priced=only_priced, is_active=is_active)
            
            # Extract data from result dictionary
            data = result.get('products', [])
            total_count = result.get('total_count', 0)
            
            # Add document detail URLs to each product (optimize by pre-computing base_url)
            from django.urls import reverse
            base_url = request.build_absolute_uri('/').rstrip('/')
            
            for product in data:
                if product.get('Product_Urdu_Name') and product.get('Product_Urdu_Ext'):
                    # Add API endpoint URL for document detail
                    product['document_detail_url'] = reverse('product_document_detail', kwargs={'item_code': product['ItemCode']})
                    # Add full page URL with database parameter
                    product['document_detail_page_url'] = f"{base_url}{product['document_detail_url']}?database={cfg['schema']}"
                    product['has_document'] = True
                else:
                    product['document_detail_url'] = None
                    product['document_detail_page_url'] = None
                    product['has_document'] = False
            
            # Calculate pagination metadata
            num_pages = (total_count + page_size - 1) // page_size if page_size > 0 else 1
            
            return Response({
                'success': True, 
                'page': page_num, 
                'page_size': page_size, 
                'num_pages': num_pages, 
                'count': total_count, 
                'database': cfg['schema'], 
                'data': data
            }, status=status.HTTP_200_OK)
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
        'schema': '',
        'encrypt': os.environ.get('HANA_ENCRYPT') or '',
        'ssl_validate': os.environ.get('HANA_SSL_VALIDATE') or '',
    }
    # Honor explicit schema values exactly as provided (e.g., 4B-AGRI_LIVE),
    # then fall back to resolver for legacy/company-key flows.
    explicit_schema = (
        (request.GET.get('database') or '').strip()
        or (request.GET.get('company') or '').strip()
    )
    if explicit_schema:
        cfg['schema'] = explicit_schema
    elif not cfg['schema']:
        cfg['schema'] = get_hana_schema_from_request(request)
    
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
        openapi.Parameter('database', openapi.IN_QUERY, description="Optional: Database/schema (e.g., 4B-BIO, 4B-ORANG, 4B-BIO_APP, 4B-ORANG_APP). If not provided, uses default from settings.", type=openapi.TYPE_STRING, required=False),
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
    operation_description="Get policy-wise customer balance. card_code is optional — omit it to return all balances. Provide user parameter to validate that the card_code belongs to that user. Returns 403 if card_code doesn't belong to the specified user.",
    manual_parameters=[
        openapi.Parameter('card_code', openapi.IN_QUERY, description="Optional: Customer CardCode (e.g., ORC00002). If omitted, returns all balances.", type=openapi.TYPE_STRING, required=False),
        openapi.Parameter('database', openapi.IN_QUERY, description="Optional: Database/schema (e.g., 4B-BIO, 4B-ORANG, 4B-BIO_APP, 4B-ORANG_APP)", type=openapi.TYPE_STRING, required=False),
        openapi.Parameter('user', openapi.IN_QUERY, description="Optional: User ID or username to validate card_code belongs to this user. Returns 403 if validation fails.", type=openapi.TYPE_STRING, required=False),
        openapi.Parameter('limit', openapi.IN_QUERY, description="Optional: Max records when no card_code is provided (default: 200)", type=openapi.TYPE_INTEGER, required=False),
    ],
    responses={200: openapi.Response(description="OK"), 403: openapi.Response(description="Forbidden - Card code does not belong to user"), 404: openapi.Response(description="User not found"), 500: openapi.Response(description="Server Error")}
)
@api_view(['GET'])
def policy_customer_balance_detail(request, card_code=None):
    """
    Get policy customer balance.
    card_code can be provided via URL path or as a query parameter — both are optional.
    If neither is provided, returns all balances (or filtered by user).
    """
    # card_code from path param takes precedence; fall back to query param
    if not card_code:
        card_code = (getattr(request, 'query_params', {}).get('card_code') if hasattr(request, 'query_params') else None) or request.GET.get('card_code', '')
        card_code = (card_code or '').strip() or None

    # Validate user if provided
    user_param = (getattr(request, 'query_params', {}).get('user') if hasattr(request, 'query_params') else None) or request.GET.get('user', '')
    user_param = (user_param or '').strip()
    
    if user_param and card_code:
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
    
    # Delegate to get_policy_customer_balance_data
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
            sch = cfg['schema']
            sql = f'SELECT * FROM "{sch}"."OITM"' if cfg['schema'] else 'SELECT * FROM "OITM"'
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

@swagger_auto_schema(tags=['SAP - Products'], 
    method='get',
    operation_summary="Get Product Description",
    operation_description="""Retrieve product description (FreeText field) from SAP HANA for a specific ItemCode.
    
This endpoint queries the OITM (Items Master) and ATC1 (Attachments) tables to retrieve:
- Product ItemCode and ItemName
- Product description from the FreeText field (searches all attachment lines)
- Image files (PNG, JPG)
- Urdu document files (DOCX, PDF)
- Complete list of all attachments

**Note**: Products can have multiple attachment lines in ATC1. This API searches all lines to find the FreeText description.

**Use Case**: Display detailed product information and descriptions in mobile/web applications.

**Example Request**: 
```
GET /api/sap/product-description/?item_code=FG00055&database=4B-AGRI_LIVE
```

**SQL Query**:
```sql
SELECT
    T0."ItemCode",
    T0."ItemName",
    T0."AtcEntry",
    A1."Line",
    A1."FreeText",     -- Product description (may be on different lines)
    A1."FileName",
    A1."FileExt",
    A1."U_IMG_C"       -- Attachment category
FROM OITM T0
LEFT JOIN ATC1 A1 ON A1."AbsEntry" = T0."AtcEntry"
WHERE T0."ItemCode" = ?
ORDER BY A1."Line"
```
""",
    manual_parameters=[
        openapi.Parameter(
            'item_code', 
            openapi.IN_QUERY, 
            description="Product Item Code (e.g., FG00055, FG00123). **Required**.", 
            type=openapi.TYPE_STRING, 
            required=True
        ),
        openapi.Parameter(
            'database', 
            openapi.IN_QUERY, 
            description="SAP HANA database/schema name (e.g., 4B-BIO_APP, 4B-ORANG_APP). If not provided, uses default from session or settings.", 
            type=openapi.TYPE_STRING, 
            required=False
        ),
    ],
    responses={
        200: openapi.Response(
            description="Product description retrieved successfully",
            examples={
                "application/json": {
                    "success": True,
                    "data": {
                        "item_code": "FG00055",
                        "item_name": "Black Gold 5G - 7-Kgs.",
                        "description": "بلیک گولڈایک مختلف دانے دار زہر ہے، جو بوررز پر بہترین اثر دکھاتا ہے۔",
                        "atc_entry": 974,
                        "image_file": "Black-Gold",
                        "image_ext": "png",
                        "urdu_file": "بلیک گولڈ 5",
                        "urdu_ext": "docx",
                        "attachments": [
                            {
                                "line": 1,
                                "file_name": "Black-Gold",
                                "file_ext": "png",
                                "category": "Product Image",
                                "has_description": False
                            },
                            {
                                "line": 2,
                                "file_name": "بلیک گولڈ 5",
                                "file_ext": "docx",
                                "category": "Product Description Urdu",
                                "has_description": True
                            }
                        ]
                    }
                }
            }
        ),
        400: openapi.Response(
            description="Bad request - missing required parameters",
            examples={
                "application/json": {
                    "success": False,
                    "error": "item_code parameter is required"
                }
            }
        ),
        404: openapi.Response(
            description="Product not found",
            examples={
                "application/json": {
                    "success": False,
                    "error": "Product with ItemCode FG00055 not found"
                }
            }
        ),
        500: openapi.Response(
            description="Server error - database connection or query failed",
            examples={
                "application/json": {
                    "success": False,
                    "error": "Database connection failed: [error details]"
                }
            }
        )
    }
)
@api_view(['GET'])
def get_product_description_api(request):
    """
    Get product description from SAP HANA
    
    Retrieves product information including the FreeText field which contains
    the detailed product description. Queries OITM and ATC1 tables.
    
    Query Parameters:
        - item_code (required): Product ItemCode
        - database (optional): SAP HANA schema name
    
    Returns:
        JSON response with product information and description
    """
    try:
        # Load environment variables
        try:
            _hana_load_env_file(os.path.join(os.path.dirname(__file__), '.env'))
            _hana_load_env_file(os.path.join(str(settings.BASE_DIR), '.env'))
            _hana_load_env_file(os.path.join(str(Path(settings.BASE_DIR).parent), '.env'))
            _hana_load_env_file(os.path.join(os.getcwd(), '.env'))
        except Exception:
            pass
        
        # Get parameters from request
        item_code = request.GET.get('item_code', '').strip()
        
        # Validate item_code parameter
        if not item_code:
            return Response({
                'success': False,
                'error': 'item_code parameter is required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Use database param directly (same as products_catalog_api) to get the actual HANA schema name
        database = (request.GET.get('database') or os.environ.get('HANA_SCHEMA') or '').strip()
        
        # logger.info(f"Fetching product description for ItemCode: {item_code}, Database: {database}")
        
        # Get SAP HANA connection configuration
        cfg = {
            'host': os.environ.get('HANA_HOST', ''),
            'port': os.environ.get('HANA_PORT', '30015'),
            'user': os.environ.get('HANA_USER', ''),
            'encrypt': os.environ.get('HANA_ENCRYPT', ''),
            'ssl_validate': os.environ.get('HANA_SSL_VALIDATE', ''),
            'schema': database
        }
        
        pwd = os.environ.get('HANA_PASSWORD', '')
        
        # Validate configuration
        if not all([cfg['host'], cfg['port'], cfg['user'], pwd]):
            # logger.error("SAP HANA configuration incomplete")
            return Response({
                'success': False,
                'error': 'SAP HANA configuration is incomplete'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        # Connect to SAP HANA
        from hdbcli import dbapi
        
        kwargs = {
            'address': cfg['host'],
            'port': int(cfg['port']),
            'user': cfg['user'],
            'password': pwd
        }
        
        if str(cfg['encrypt']).strip().lower() in ('true', '1', 'yes'):
            kwargs['encrypt'] = True
            if cfg['ssl_validate']:
                kwargs['sslValidateCertificate'] = (str(cfg['ssl_validate']).strip().lower() in ('true', '1', 'yes'))
        
        try:
            conn = dbapi.connect(**kwargs)
        except Exception as e:
            # logger.error(f"Failed to connect to SAP HANA: {e}")
            return Response({
                'success': False,
                'error': f'Database connection failed: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        try:
            # Set schema
            cur = conn.cursor()
            if cfg['schema']:
                # Quote schema name properly (schema names can contain hyphens in HANA)
                from sap_integration.hana_connect import quote_ident
                schema_name = cfg['schema']
                set_schema_sql = f'SET SCHEMA {quote_ident(schema_name)}'
                cur.execute(set_schema_sql)
            
            # Query product description - match image by file extension (same as products-catalog)
            # and urdu by U_IMG_C category. Join ATC1 directly (no OATC intermediate).
            sql = """
            SELECT
                T0."ItemCode",
                T0."ItemName",
                T0."AtcEntry",
                MAX(
                    CASE
                        WHEN A."U_IMG_C" = 'Product Image'
                        THEN A."FreeText"
                    END
                ) AS "Description",
                MIN(
                    CASE
                        WHEN LOWER(TRIM(A."FileExt")) IN ('jpeg', 'jpg', 'png')
                        THEN A."FileName" || '.' || A."FileExt"
                    END
                ) AS "Product_Image",
                MAX(
                    CASE
                        WHEN A."U_IMG_C" = 'Product Description Urdu'
                        THEN A."FileName" || '.' || A."FileExt"
                    END
                ) AS "Product_Description_Urdu"
            FROM OITM T0
            LEFT JOIN ATC1 A
                ON A."AbsEntry" = T0."AtcEntry"
            WHERE
                T0."ItemCode" = ?
            GROUP BY
                T0."ItemCode",
                T0."ItemName",
                T0."AtcEntry"
            """
            
            cur.execute(sql, (item_code,))
            rows = cur.fetchall()
            
            if not rows or not rows[0][0]:
                # logger.warning(f"Product not found: {item_code}")
                return Response({
                    'success': False,
                    'error': f'Product with ItemCode {item_code} not found'
                }, status=status.HTTP_404_NOT_FOUND)
            
            row = rows[0]
            item_code_result = row[0]
            item_name        = row[1]
            atc_entry        = row[2]
            description      = row[3]          # FreeText from Product Image line
            product_image    = row[4]          # e.g. "Black-Gold.png"
            product_desc_urdu = row[5]         # e.g. "بلیک گولڈ 5.docx"

            # Split combined FileName.FileExt back into parts for backward-compat fields
            def _split_file(combined):
                if not combined:
                    return None, None
                parts = combined.rsplit('.', 1)
                return (parts[0], parts[1]) if len(parts) == 2 else (parts[0], None)

            image_file, image_ext = _split_file(product_image)
            urdu_file,  urdu_ext  = _split_file(product_desc_urdu)

            # Extract folder name from schema/database name (e.g., "4B-AGRI_LIVE" -> "4B-AGRI")
            folder_name = 'default'
            if database:
                folder_name = database.replace('_APP', '').replace('_LIVE', '').replace('_TEST', '').strip()
            
            # Construct URLs directly from the combined Product_Image / Product_Description_Urdu values
            product_image_url = f'/media/product_images/{folder_name}/{product_image}' if product_image else None
            product_description_urdu_url = f'/media/product_images/{folder_name}/{product_desc_urdu}' if product_desc_urdu else None

            all_attachments = []
            if product_image:
                all_attachments.append({'file_name': image_file, 'file_ext': image_ext, 'category': 'Product Image', 'has_description': bool(description)})
            if product_desc_urdu:
                all_attachments.append({'file_name': urdu_file, 'file_ext': urdu_ext, 'category': 'Product Description Urdu', 'has_description': False})
            
            # Fetch price from @PLR4 for this item
            price = 0.0
            try:
                from sap_integration.hana_connect import _fetch_all
                price_rows = _fetch_all(conn, 
                    'SELECT T1."U_np" AS "Price" '
                    'FROM "@PLR4" T1 '
                    'INNER JOIN "@PL1" T0 ON T0."DocEntry" = T1."DocEntry" '
                    'WHERE T1."U_itc" = ?',
                    (item_code,)
                )
                if price_rows:
                    # Get the highest price if multiple entries exist
                    for pr in price_rows:
                        price_val = pr.get('Price', 0)
                        try:
                            price_val = float(price_val) if price_val is not None else 0.0
                        except (ValueError, TypeError):
                            price_val = 0.0
                        if price_val > price:
                            price = price_val
            except Exception:
                pass  # If price fetch fails, use 0
            
            result = {
                'item_code': item_code_result,
                'item_name': item_name,
                'description': description,  # FreeText - Product Description
                'price': price,  # Price from @PLR4 or 0 if not found
                'atc_entry': atc_entry,
                'product_image': product_image,          # e.g. "Black-Gold.png"  (FileName.FileExt)
                'product_description_urdu': product_desc_urdu,  # e.g. "بلیک گولڈ 5.docx"
                'image_file': image_file,
                'image_ext': image_ext,
                'urdu_file': urdu_file,
                'urdu_ext': urdu_ext,
                'product_image_url': product_image_url,  # Full URL to product image
                'product_description_urdu_url': product_description_urdu_url,  # Full URL to Urdu description
                'has_document': bool(description or urdu_file),  # True if has description or Urdu file
                'attachments': all_attachments  # All attachment details
            }
            
            # logger.info(f"Product found: {item_code}, Description: {'Yes' if description else 'No'}")
            return Response({
                'success': True,
                'data': result
            }, status=status.HTTP_200_OK)
                
        finally:
            try:
                cur.close()
                conn.close()
            except Exception:
                pass
            
    except Exception as e:
        # logger.error(f"Error in get_product_description_api: {e}", exc_info=True)
        return Response({
            'success': False,
            'error': f'An error occurred: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@swagger_auto_schema(
    tags=['SAP - Products'], 
    method='get',
    operation_summary="Download Product Description Document",
    operation_description="""Download the product description document file (DOCX/PDF) for a specific ItemCode.

This endpoint:
1. Queries SAP HANA to find the product's Urdu description document
2. Locates the file in the media/product_images directory
3. Serves the file for download if it exists
4. Returns JSON error if the file is not found

**File Location**: `media/product_images/{company_folder}/{filename}.{extension}`

**Supported Formats**: DOCX, DOC, PDF

**Use Case**: Allow users to download detailed product documentation in Urdu or other languages.

**Note**: This endpoint returns a binary file for download, not JSON.

**Example Request**: 
```
GET /api/sap/product-description-download/?item_code=FG00055&database=4B-AGRI_LIVE
```

**Success Response**: Binary file download (DOCX/PDF)

**Error Response**: JSON with error details
""",
    manual_parameters=[
        openapi.Parameter(
            'item_code', 
            openapi.IN_QUERY, 
            description='Product Item Code (e.g., FG00055). **Required**.', 
            type=openapi.TYPE_STRING, 
            required=True
        ),
        openapi.Parameter(
            'database', 
            openapi.IN_QUERY, 
            description='SAP HANA database/schema name (e.g., 4B-AGRI_LIVE, 4B-ORANG_APP)', 
            type=openapi.TYPE_STRING, 
            required=False
        ),
    ],
    responses={
        200: openapi.Response(
            description="File download successful - Returns binary file (DOCX/DOC/PDF)",
            schema=openapi.Schema(
                type=openapi.TYPE_FILE,
                format='binary'
            )
        ),
        404: openapi.Response(
            description="Product or file not found",
            schema=openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    'success': openapi.Schema(type=openapi.TYPE_BOOLEAN, example=False),
                    'error': openapi.Schema(type=openapi.TYPE_STRING, example='File not found: بلیک گولڈ 5.docx'),
                    'file_name': openapi.Schema(type=openapi.TYPE_STRING, example='بلیک گولڈ 5'),
                    'file_ext': openapi.Schema(type=openapi.TYPE_STRING, example='docx'),
                    'item_name': openapi.Schema(type=openapi.TYPE_STRING, example='Black Gold 5G - 7-Kgs.'),
                }
            )
        ),
        500: openapi.Response(
            description="Server error",
            schema=openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    'success': openapi.Schema(type=openapi.TYPE_BOOLEAN, example=False),
                    'error': openapi.Schema(type=openapi.TYPE_STRING, example='Database connection failed'),
                }
            )
        )
    },
    produces=['application/vnd.openxmlformats-officedocument.wordprocessingml.document', 'application/pdf', 'application/msword', 'application/json']
)
@api_view(['GET'])
def download_product_description_api(request):
    """
    Download product description document file
    
    Query Parameters:
        - item_code (required): Product ItemCode
        - database (optional): SAP HANA schema name
    
    Returns:
        File download response or JSON error
    """
    try:
        # Load environment variables
        try:
            _hana_load_env_file(os.path.join(os.path.dirname(__file__), '.env'))
            _hana_load_env_file(os.path.join(str(settings.BASE_DIR), '.env'))
            _hana_load_env_file(os.path.join(str(Path(settings.BASE_DIR).parent), '.env'))
            _hana_load_env_file(os.path.join(os.getcwd(), '.env'))
        except Exception:
            pass
        
        # Get parameters from request
        item_code = request.GET.get('item_code', '').strip()
        
        # Validate item_code parameter
        if not item_code:
            return JsonResponse({
                'success': False,
                'error': 'item_code parameter is required'
            }, status=400)
        
        # Use database param directly (same as products_catalog_api) to get the actual HANA schema name
        database = (request.GET.get('database') or os.environ.get('HANA_SCHEMA') or '').strip()
        
        # logger.info(f"Downloading product description for ItemCode: {item_code}, Database: {database}")
        
        # Get SAP HANA connection configuration
        cfg = {
            'host': os.environ.get('HANA_HOST', ''),
            'port': os.environ.get('HANA_PORT', '30015'),
            'user': os.environ.get('HANA_USER', ''),
            'encrypt': os.environ.get('HANA_ENCRYPT', ''),
            'ssl_validate': os.environ.get('HANA_SSL_VALIDATE', ''),
            'schema': database
        }
        
        pwd = os.environ.get('HANA_PASSWORD', '')
        
        # Validate configuration
        if not all([cfg['host'], cfg['port'], cfg['user'], pwd]):
            # logger.error("SAP HANA configuration incomplete")
            return JsonResponse({
                'success': False,
                'error': 'SAP HANA configuration is incomplete'
            }, status=500)
        
        # Connect to SAP HANA
        from hdbcli import dbapi
        
        kwargs = {
            'address': cfg['host'],
            'port': int(cfg['port']),
            'user': cfg['user'],
            'password': pwd
        }
        
        if str(cfg['encrypt']).strip().lower() in ('true', '1', 'yes'):
            kwargs['encrypt'] = True
            if cfg['ssl_validate']:
                kwargs['sslValidateCertificate'] = (str(cfg['ssl_validate']).strip().lower() in ('true', '1', 'yes'))
        
        try:
            conn = dbapi.connect(**kwargs)
        except Exception as e:
            #logger.error(f"Failed to connect to SAP HANA: {e}")
            return JsonResponse({
                'success': False,
                'error': f'Database connection failed: {str(e)}'
            }, status=500)
        
        try:
            # Set schema
            cur = conn.cursor()
            if cfg['schema']:
                # Quote schema name properly (schema names can contain hyphens in HANA)
                from sap_integration.hana_connect import quote_ident
                schema_name = cfg['schema']
                set_schema_sql = f'SET SCHEMA {quote_ident(schema_name)}'
                cur.execute(set_schema_sql)
            
            # Query product attachment information
            sql = """
            SELECT
                T0."ItemCode",
                T0."ItemName",
                A1."Line",
                A1."FreeText",
                A1."FileName",
                A1."FileExt",
                A1."U_IMG_C"
            FROM OITM T0
            LEFT JOIN ATC1 A1
                ON A1."AbsEntry" = T0."AtcEntry"
            WHERE
                T0."ItemCode" = ?
            ORDER BY A1."Line"
            """
            
            cur.execute(sql, (item_code,))
            rows = cur.fetchall()
            
            if not rows or not rows[0][0]:
               # logger.warning(f"Product not found: {item_code}")
                return JsonResponse({
                    'success': False,
                    'error': f'Product with ItemCode {item_code} not found'
                }, status=404)
            
            # Look for the description document file (DOCX, DOC, PDF)
            doc_file = None
            doc_ext = None
            item_name = rows[0][1]
            
            for row in rows:
                file_name = row[4]
                file_ext = row[5]
                img_category = row[6] if len(row) > 6 else None
                free_text = row[3]
                
                # Look for document files with FreeText (description)
                if file_ext and file_ext.lower() in ['doc', 'docx', 'pdf']:
                    # Prefer files with FreeText content
                    if free_text and not doc_file:
                        doc_file = file_name
                        doc_ext = file_ext
                    # Or files marked as description
                    elif img_category and 'description' in img_category.lower() and not doc_file:
                        doc_file = file_name
                        doc_ext = file_ext
                    # Or any document file as fallback
                    elif not doc_file:
                        doc_file = file_name
                        doc_ext = file_ext
            
            if not doc_file or not doc_ext:
               # logger.warning(f"No description document found for product: {item_code}")
                return JsonResponse({
                    'success': False,
                    'error': f'No description document found for product {item_code}. Product may only have images.',
                    'item_name': item_name
                }, status=404)
            
            # Dynamically determine folder name from database schema
            # Examples: 4B-BIO_APP -> 4B-BIO, 4B-ORANG_APP -> 4B-ORANG, 4B-AGRI_LIVE -> 4B-AGRI
            possible_folders = []
            
            if database:
                # Extract folder name by removing common suffixes
                folder_name = database.replace('_APP', '').replace('_LIVE', '').replace('_TEST', '').strip()
                folder_path = os.path.join(settings.MEDIA_ROOT, 'product_images', folder_name)
                
                # If extracted folder exists, prioritize it
                if os.path.exists(folder_path) and os.path.isdir(folder_path):
                    possible_folders.append(folder_name)
            
            # Get all available folders in product_images directory dynamically
            product_images_dir = os.path.join(settings.MEDIA_ROOT, 'product_images')
            try:
                all_folders = [d for d in os.listdir(product_images_dir) 
                              if os.path.isdir(os.path.join(product_images_dir, d)) and not d.startswith('.')]
                # Add any folders not already in the list
                for folder in all_folders:
                    if folder not in possible_folders:
                        possible_folders.append(folder)
            except Exception:
                # Fallback: if we can't read directory, try company folders
                if not possible_folders:
                    try:
                        companies = Company.objects.filter(is_active=True)
                        possible_folders = [comp.name.replace('_APP', '').replace('_LIVE', '').replace('_TEST', '').strip() for comp in companies if comp.name]
                        # Remove duplicates
                        possible_folders = list(set(possible_folders))
                    except Exception:
                        # Last resort fallback
                        possible_folders = ['default']
            
            # Try to find the file in possible folders
            file_name_with_ext = f"{doc_file}.{doc_ext}"
            file_path = None
            folder_name_used = None
            
            for folder in possible_folders:
                test_path = os.path.join(settings.MEDIA_ROOT, 'product_images', folder, file_name_with_ext)
                # logger.info(f"Checking path: {test_path}")
                if os.path.exists(test_path):
                    file_path = test_path
                    folder_name_used = folder
                    break
            
            if not file_path:
                # File not found in any folder
               # logger.error(f"File not found in any folder: {file_name_with_ext}")
                searched_paths = [os.path.join(settings.MEDIA_ROOT, 'product_images', f, file_name_with_ext) for f in possible_folders]
                return JsonResponse({
                    'success': False,
                    'error': f'File not found: {file_name_with_ext}',
                    'file_name': doc_file,
                    'file_ext': doc_ext,
                    'searched_folders': possible_folders,
                    'searched_paths': searched_paths,
                    'item_name': item_name,
                    'note': 'The file may not have been uploaded to the media/product_images folder yet.'
                }, status=404)
            
            # Determine content type
            content_type, _ = mimetypes.guess_type(file_path)
            if not content_type:
                # Default content types for common formats
                ext_lower = doc_ext.lower()
                if ext_lower == 'docx':
                    content_type = 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
                elif ext_lower == 'doc':
                    content_type = 'application/msword'
                elif ext_lower == 'pdf':
                    content_type = 'application/pdf'
                else:
                    content_type = 'application/octet-stream'
            
            # Open and serve the file
            try:
                file_handle = open(file_path, 'rb')
                response = FileResponse(file_handle, content_type=content_type)
                
                # Set download filename (sanitize for ASCII)
                safe_filename = f"product_{item_code}_description.{doc_ext}"
                response['Content-Disposition'] = f'attachment; filename="{safe_filename}"'
                
                # logger.info(f"Successfully serving file: {file_name_with_ext}")
                return response
                
            except Exception as e:
                #logger.error(f"Error opening file {file_path}: {e}")
                return JsonResponse({
                    'success': False,
                    'error': f'Error reading file: {str(e)}'
                }, status=500)
                
        finally:
            try:
                cur.close()
                conn.close()
            except Exception:
                pass
            
    except Exception as e:
        #logger.error(f"Error in download_product_description_api: {e}", exc_info=True)
        return JsonResponse({
            'success': False,
            'error': f'An error occurred: {str(e)}'
        }, status=500)

@swagger_auto_schema(tags=['SAP'], 
    method='get',
    operation_summary="Warehouse list for item",
    operation_description="List warehouses for a specific ItemCode; when ItemCode is empty, returns all warehouses. Supports pagination and search.",
    manual_parameters=[
        openapi.Parameter('database', openapi.IN_QUERY, description="Database/schema (e.g., 4B-BIO, 4B-ORANG, 4B-BIO_APP, 4B-ORANG_APP)", type=openapi.TYPE_STRING, required=False),
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
        'schema': '',
        'encrypt': os.environ.get('HANA_ENCRYPT') or '',
        'ssl_validate': os.environ.get('HANA_SSL_VALIDATE') or '',
    }
    # Use shared helper to resolve schema from Company model
    cfg['schema'] = get_hana_schema_from_request(request)
    
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
        'schema': '',
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
        'schema': '',
        'encrypt': os.environ.get('HANA_ENCRYPT') or '',
        'ssl_validate': os.environ.get('HANA_SSL_VALIDATE') or '',
    }
    # Use shared helper to resolve schema from Company model
    cfg['schema'] = get_hana_schema_from_request(request)
    
    project_code = (request.GET.get('project_code') or '').strip()
    show_all = (request.GET.get('show_all') or '').strip().lower() in ('true','1','yes')
    page_param = (request.GET.get('page') or '1').strip()
    page_size_param = (request.GET.get('page_size') or '').strip()
    try:
        page_num = int(page_param)
        if page_num < 1:
            page_num = 1
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
        openapi.Parameter('company', openapi.IN_QUERY, description="Optional: Company database key", type=openapi.TYPE_STRING, required=False),
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
        'schema': '',
        'encrypt': os.environ.get('HANA_ENCRYPT') or '',
        'ssl_validate': os.environ.get('HANA_SSL_VALIDATE') or '',
    }
    
    # Read the 'company' parameter (not 'database') and resolve schema
    company_param = (request.GET.get('company') or '').strip()
    if company_param:
        # Create a modified request.GET to use with the helper function
        from django.http import QueryDict
        modified_get = request.GET.copy()
        modified_get['database'] = company_param
        # Temporarily replace request.GET
        original_get = request.GET
        request.GET = modified_get
        cfg['schema'] = get_hana_schema_from_request(request)
        request.GET = original_get
    else:
        # No company param provided, use default resolution
        cfg['schema'] = get_hana_schema_from_request(request)
    
    card_code = (request.GET.get('card_code') or '').strip()
    show_all = (request.GET.get('show_all') or '').strip().lower() in ('true','1','yes')
    page_param = (request.GET.get('page') or '1').strip()
    page_size_param = (request.GET.get('page_size') or '').strip()
    try:
        page_num = int(page_param)
        if page_num < 1:
            page_num = 1
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
    operation_summary="General Ledger",
    operation_description="Fetch general ledger transactions. NO REQUIRED FIELDS. All parameters are optional filters for account range, date range, business partner, and project. Use user parameter to filter by user's assigned customers.",
    manual_parameters=[
        openapi.Parameter('company', openapi.IN_QUERY, description="Optional: Company database key", type=openapi.TYPE_STRING, required=False),
        openapi.Parameter('start_date', openapi.IN_QUERY, description="Start date filter (YYYY-MM-DD format)", type=openapi.TYPE_STRING, required=False),
        openapi.Parameter('end_date', openapi.IN_QUERY, description="End date filter (YYYY-MM-DD format)", type=openapi.TYPE_STRING, required=False),
        openapi.Parameter('account_from', openapi.IN_QUERY, description="Filter by Account code range start (optional)", type=openapi.TYPE_STRING, required=False),
        openapi.Parameter('account_to', openapi.IN_QUERY, description="Filter by Account code range end (optional)", type=openapi.TYPE_STRING, required=False),
        openapi.Parameter('account', openapi.IN_QUERY, description="Filter by specific Account code (optional)", type=openapi.TYPE_STRING, required=False),
        openapi.Parameter('business_partner', openapi.IN_QUERY, description="Filter by Business Partner CardCode (optional)", type=openapi.TYPE_STRING, required=False),
        openapi.Parameter('project', openapi.IN_QUERY, description="Filter by Project code (optional)", type=openapi.TYPE_STRING, required=False),
        openapi.Parameter('user', openapi.IN_QUERY, description="Optional: User ID or username to filter by user's assigned customers", type=openapi.TYPE_STRING, required=False),
        openapi.Parameter('search', openapi.IN_QUERY, description="Search in Account, LineMemo, or Ref1", type=openapi.TYPE_STRING, required=False),
        openapi.Parameter('page', openapi.IN_QUERY, description="Page number (default 1)", type=openapi.TYPE_INTEGER, required=False),
        openapi.Parameter('page_size', openapi.IN_QUERY, description="Items per page (default 50)", type=openapi.TYPE_INTEGER, required=False),
    ],
    responses={200: openapi.Response(description="OK"), 400: openapi.Response(description="Bad Request"), 500: openapi.Response(description="Server Error")}
)
@api_view(['GET'])
def general_ledger_api(request):
    """
    Get General Ledger Report from SAP HANA.
    NO REQUIRED FIELDS - all parameters are optional filters.
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
        'schema': '',
        'encrypt': os.environ.get('HANA_ENCRYPT') or '',
        'ssl_validate': os.environ.get('HANA_SSL_VALIDATE') or '',
    }
    
    # Read the 'company' parameter and resolve schema
    company_param = (request.GET.get('company') or '').strip()
    if company_param:
        from django.http import QueryDict
        modified_get = request.GET.copy()
        modified_get['database'] = company_param
        original_get = request.GET
        request.GET = modified_get
        cfg['schema'] = get_hana_schema_from_request(request)
        request.GET = original_get
    else:
        cfg['schema'] = get_hana_schema_from_request(request)
    
    # Get query parameters
    start_date = (request.GET.get('start_date') or '').strip()
    end_date = (request.GET.get('end_date') or '').strip()
    account = (request.GET.get('account') or '').strip()
    account_from = (request.GET.get('account_from') or '').strip()
    account_to = (request.GET.get('account_to') or '').strip()
    business_partner = (request.GET.get('business_partner') or '').strip()
    project = (request.GET.get('project') or '').strip()
    user_param = (request.GET.get('user') or '').strip()
    search = (request.GET.get('search') or '').strip()
    page_param = (request.GET.get('page') or '1').strip()
    page_size_param = (request.GET.get('page_size') or '50').strip()
    
    try:
        page_num = int(page_param)
        if page_num < 1:
            page_num = 1
    except Exception:
        page_num = 1
    
    try:
        page_size = int(page_size_param) if page_size_param else 50
        if page_size < 1:
            page_size = 50
    except Exception:
        page_size = 50
    
    # Handle user parameter - get assigned customers
    user_customers = []
    if user_param:
        try:
            from django.contrib.auth import get_user_model
            User = get_user_model()
            try:
                user_id = int(user_param)
                user_obj = User.objects.get(id=user_id)
            except ValueError:
                user_obj = User.objects.get(username=user_param)
            
            # Get user's assigned customers
            if hasattr(user_obj, 'customer_assignments') and hasattr(user_obj.customer_assignments, 'all'):
                user_customers = list(user_obj.customer_assignments.all().values_list('card_code', flat=True))
        except Exception:
            pass
    
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
            
            # Build the query - join with OCRD to get business partner info
            query = '''
                SELECT 
                    J."TransId",
                    J."Line_ID",
                    J."Account",
                    J."Debit",
                    J."Credit",
                    J."RefDate",
                    J."Ref1",
                    J."Ref2",
                    J."LineMemo",
                    J."Project",
                    J."ContraAct",
                    J."FCDebit",
                    J."FCCredit",
                    J."FCCurrency",
                    J."ShortName"
                FROM "JDT1" J
                WHERE 1=1
            '''
            
            params = []
            
            # Add date filters
            if start_date:
                query += ' AND J."RefDate" >= ?'
                params.append(start_date)
            
            if end_date:
                query += ' AND J."RefDate" <= ?'
                params.append(end_date)
            
            # Add account filter (specific account)
            if account:
                query += ' AND J."Account" = ?'
                params.append(account)
            
            # Add account range filter
            if account_from:
                query += ' AND J."Account" >= ?'
                params.append(account_from)
            
            if account_to:
                query += ' AND J."Account" <= ?'
                params.append(account_to)
            
            # Add business partner filter
            if business_partner:
                query += ' AND J."ShortName" = ?'
                params.append(business_partner)
            
            # Add user's customers filter
            if user_customers:
                placeholders = ','.join(['?' for _ in user_customers])
                query += f' AND J."ShortName" IN ({placeholders})'
                params.extend(user_customers)
            
            # Add project filter
            if project:
                query += ' AND J."Project" = ?'
                params.append(project)
            
            # Add search filter
            if search:
                query += ' AND (J."Account" LIKE ? OR J."LineMemo" LIKE ? OR J."Ref1" LIKE ?)'
                search_pattern = f'%{search}%'
                params.extend([search_pattern, search_pattern, search_pattern])
            
            query += ' ORDER BY J."RefDate" DESC, J."TransId" DESC, J."Line_ID"'
            
            cur = conn.cursor()
            if params:
                cur.execute(query, params)
            else:
                cur.execute(query)
            
            columns = [desc[0] for desc in cur.description]
            rows = cur.fetchall()
            cur.close()
            
            data = []
            for row in rows:
                row_dict = {}
                for idx, col in enumerate(columns):
                    val = row[idx]
                    # Convert date objects to string
                    if hasattr(val, 'isoformat'):
                        val = val.isoformat()
                    # Convert Decimal to float
                    elif hasattr(val, '__float__'):
                        try:
                            val = float(val)
                        except:
                            pass
                    row_dict[col] = val
                data.append(row_dict)
            
            # Paginate results
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
        'schema': '',
        'encrypt': os.environ.get('HANA_ENCRYPT') or '',
        'ssl_validate': os.environ.get('HANA_SSL_VALIDATE') or '',
    }
    
    # Use shared helper to resolve schema from Company model
    cfg['schema'] = get_hana_schema_from_request(request)
    
    status_param = (request.GET.get('status') or '').strip().lower()
    limit_param = (request.GET.get('limit') or '').strip()
    page_param = (request.GET.get('page') or '1').strip()
    page_size_param = (request.GET.get('page_size') or '').strip()
    try:
        page_num = int(page_param)
        if page_num < 1:
            page_num = 1
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
        'schema': '',
        'encrypt': os.environ.get('HANA_ENCRYPT') or '',
        'ssl_validate': os.environ.get('HANA_SSL_VALIDATE') or '',
    }
    
    # Use shared helper to resolve schema from Company model
    cfg['schema'] = get_hana_schema_from_request(request)
    
    limit_param = (request.GET.get('limit') or '').strip()
    page_param = (request.GET.get('page') or '1').strip()
    page_size_param = (request.GET.get('page_size') or '').strip()
    try:
        page_num = int(page_param)
        if page_num < 1:
            page_num = 1
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
    operation_description="List customers with optional search, territory, status and pagination. Can filter by user_id to get the user's territory automatically.",
    manual_parameters=[
        openapi.Parameter('company', openapi.IN_QUERY, description="Optional: Company database key", type=openapi.TYPE_STRING, required=False),
        openapi.Parameter('user_id', openapi.IN_QUERY, description="Optional: Portal User ID - Gets territory assigned to the user. If provided, shows only customers from that user's territory", type=openapi.TYPE_INTEGER, required=False),
        openapi.Parameter('status', openapi.IN_QUERY, description="Filter by status: active, inactive, or all", type=openapi.TYPE_STRING, required=False),
        openapi.Parameter('territory', openapi.IN_QUERY, description="Filter by territory ID (overridden by user_id if both provided)", type=openapi.TYPE_STRING, required=False),
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
        'schema': '',
        'encrypt': os.environ.get('HANA_ENCRYPT') or '',
        'ssl_validate': os.environ.get('HANA_SSL_VALIDATE') or '',
    }
    
    # Read the 'company' parameter and resolve schema directly
    company_param = (request.GET.get('company') or '').strip()
    if company_param:
        cfg['schema'] = resolve_company_to_schema(company_param)
    else:
        # No company param provided, try database param or use default
        db_param = (request.GET.get('database') or '').strip()
        if db_param:
            cfg['schema'] = resolve_company_to_schema(db_param)
        else:
            cfg['schema'] = get_hana_schema_from_request(request)
    
    search = (request.GET.get('search') or '').strip()
    status_param = (request.GET.get('status') or 'active').strip().lower()
    territory_param = (request.GET.get('territory') or '').strip()
    user_id_param = (request.GET.get('user_id') or '').strip()
    page_param = (request.GET.get('page') or '1').strip()
    page_size_param = (request.GET.get('page_size') or '').strip()
    limit_param = (request.GET.get('top') or request.GET.get('limit') or '').strip()
    
    # If user_id is provided, get the user's territory/territories
    user_territories = []
    hana_territory_id_param = None
    if user_id_param:
        try:
            user_id_val = int(user_id_param)
            # Import the custom User model from accounts app
            from accounts.models import User
            target_user = User.objects.get(id=user_id_val)
            # Get the user's sales profile and territories
            if hasattr(target_user, 'sales_profile') and target_user.sales_profile:
                territories = target_user.sales_profile.territories.all()
                if territories.exists():
                    # Get first territory with hana_territory_id mapping
                    first_territory = territories.first()
                    if first_territory and first_territory.hana_territory_id:
                        hana_territory_id_param = first_territory.hana_territory_id
                        user_territories = [{'id': first_territory.id, 'name': first_territory.name, 'hana_id': first_territory.hana_territory_id}]
                        import sys
                        print(f"[DEBUG] customer_lov_api: User {user_id_val} - Using territory '{first_territory.name}' (HANA ID: {hana_territory_id_param})", file=sys.stderr)
                    else:
                        # Territory doesn't have HANA mapping
                        import sys
                        print(f"[DEBUG] customer_lov_api: User {user_id_val} - First territory '{first_territory.name}' has NO hana_territory_id mapping", file=sys.stderr)
                        # Return all territories assigned but indicate mapping is missing
                        user_territories = [{'id': t.id, 'name': t.name, 'hana_id': t.hana_territory_id} for t in territories]
                else:
                    import sys
                    print(f"[DEBUG] customer_lov_api: User {user_id_val} has no territories assigned", file=sys.stderr)
            else:
                import sys
                print(f"[DEBUG] customer_lov_api: User {user_id_val} has no sales profile", file=sys.stderr)
        except (ValueError, User.DoesNotExist) as e:
            import sys
            print(f"[DEBUG] customer_lov_api: Error fetching user territory: {str(e)}", file=sys.stderr)
            pass
    
    # Validate schema resolution
    if not cfg['schema']:
        # Try to get list of available companies for the error message
        available_companies = []
        try:
            available_companies = list(Company.objects.filter(is_active=True).values_list('Company_name', flat=True))
        except Exception:
            pass
        
        if company_param:
            error_msg = f"Could not resolve company '{company_param}' to a valid schema."
            if available_companies:
                error_msg += f" Available companies: {', '.join(available_companies)}"
            else:
                error_msg += " No active companies configured in the system."
            return Response({'success': False, 'error': error_msg, 'available_companies': available_companies}, status=status.HTTP_400_BAD_REQUEST)
        else:
            error_msg = "No schema configured. Please provide a 'company' parameter."
            if available_companies:
                error_msg += f" Available companies: {', '.join(available_companies)}"
            return Response({'success': False, 'error': error_msg, 'available_companies': available_companies}, status=status.HTTP_400_BAD_REQUEST)
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
                sch = cfg['schema'].strip()
                # Log for debugging
                import sys
                print(f"[DEBUG] customer_lov_api: Using schema: '{sch}'", file=sys.stderr)
                cur = conn.cursor()
                cur.execute(f'SET SCHEMA "{sch}"')
                cur.close()
            from .hana_connect import customer_lov
            # Use hana_territory_id if from user_id, otherwise use territory or territory_name
            data = customer_lov(
                conn, 
                search or None, 
                limit=limit_val, 
                status=status_param or 'active', 
                territory=territory_param or None if not hana_territory_id_param else None,
                territory_name=None,  # Don't use territory_name anymore
                hana_territory_id=hana_territory_id_param
            )
            paginator = Paginator(data or [], page_size)
            page_obj = paginator.get_page(page_num)
            
            # Build response
            response_data = {
                'success': True,
                'page': page_obj.number,
                'page_size': page_size,
                'num_pages': paginator.num_pages,
                'count': paginator.count,
                'data': list(page_obj.object_list)
            }
            
            # Include user territory info if user_id was provided
            if user_id_param and user_territories:
                response_data['user_id'] = int(user_id_param)
                response_data['assigned_territories'] = user_territories  # Already in dict format with hana_id
                if hana_territory_id_param:
                    response_data['filtered_by_hana_territory_id'] = hana_territory_id_param
                    response_data['warning'] = 'Make sure all territories have hana_territory_id mapping set' if not all(t.get('hana_id') for t in user_territories) else None
            elif territory_param:
                response_data['filtered_by_territory_code'] = territory_param
            
            return Response(response_data, status=status.HTTP_200_OK)
        finally:
            try:
                conn.close()
            except Exception:
                pass
    except Exception as e:
        import sys
        error_msg = str(e)
        print(f"[DEBUG] customer_lov_api ERROR: {error_msg}", file=sys.stderr)
        print(f"[DEBUG] Resolved schema: '{cfg['schema']}'", file=sys.stderr)
        print(f"[DEBUG] Company param: '{company_param}'", file=sys.stderr)
        if user_id_param:
            print(f"[DEBUG] User ID: '{user_id_param}', Territories: {user_territories}", file=sys.stderr)
        return Response({'success': False, 'error': error_msg, 'debug': {'schema': cfg['schema'], 'company_param': company_param, 'user_id': user_id_param if user_id_param else None}}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@swagger_auto_schema(tags=['SAP'], 
    method='get',
    operation_summary="Item LOV",
    operation_description="List items with optional search and pagination.",
    manual_parameters=[
        openapi.Parameter('database', openapi.IN_QUERY, description="Database/schema (e.g., 4B-BIO, 4B-ORANG, 4B-BIO_APP, 4B-ORANG_APP)", type=openapi.TYPE_STRING, required=False),
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
        'schema': '',
        'encrypt': os.environ.get('HANA_ENCRYPT') or '',
        'ssl_validate': os.environ.get('HANA_SSL_VALIDATE') or '',
    }
    
    # Use shared helper to resolve schema from Company model
    cfg['schema'] = get_hana_schema_from_request(request)
    
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
    operation_description="""Get unit price (U_np) for a specific item in a policy. Use this when item is selected to auto-fill unit price in sales order form.
    
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
    
    **Price Source:** Queries @PLR4 table joining with policy and item data to get U_np (Net Price).
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
        'schema': '',  # Will be set dynamically below
        'encrypt': os.environ.get('HANA_ENCRYPT') or '',
        'ssl_validate': os.environ.get('HANA_SSL_VALIDATE') or '',
    }

    # Resolve HANA schema using shared helper
    hana_schema = get_hana_schema_from_request(request)
    cfg['schema'] = hana_schema
    
    # logger.info(f"[ITEM_PRICE] Using HANA schema: {hana_schema}")

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
            price_val = price_row.get('U_np') if isinstance(price_row, dict) else None
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
        'schema': '',  # Will be set dynamically below
        'encrypt': os.environ.get('HANA_ENCRYPT') or '',
        'ssl_validate': os.environ.get('HANA_SSL_VALIDATE') or '',
    }

    # Resolve HANA schema using shared helper
    hana_schema = get_hana_schema_from_request(request)
    cfg['schema'] = hana_schema
    
    # logger.info(f"[POLICY_ITEMS] Using HANA schema: {hana_schema}")

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
            # @PLR4 uses U_itc for ItemCode, U_np for price
            # Join with OITM for item details
            if card_code:
                sql_query = """
                    SELECT 
                        h."DocEntry" AS policy_doc_entry,
                        l."U_itc" AS ItemCode,
                        i."ItemName",
                        l."U_np" AS unit_price,
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
                        l."U_np" AS unit_price,
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
        'schema': '',  # Will be set dynamically below
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
        'schema': '',
        'encrypt': os.environ.get('HANA_ENCRYPT') or '',
        'ssl_validate': os.environ.get('HANA_SSL_VALIDATE') or '',
    }
    
    # Use shared helper to resolve schema from Company model
    cfg['schema'] = get_hana_schema_from_request(request)
    
    search = (request.GET.get('search') or '').strip()
    page_param = (request.GET.get('page') or '1').strip()
    page_size_param = (request.GET.get('page_size') or '').strip()
    try:
        page_num = int(page_param)
        if page_num < 1:
            page_num = 1
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
        openapi.Parameter('database', openapi.IN_QUERY, description="Database/schema (e.g., 4B-BIO, 4B-ORANG, 4B-BIO_APP, 4B-ORANG_APP)", type=openapi.TYPE_STRING, required=False),
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
        'schema': '',
        'encrypt': os.environ.get('HANA_ENCRYPT') or '',
        'ssl_validate': os.environ.get('HANA_SSL_VALIDATE') or '',
    }
    
    # Use shared helper to resolve schema from Company model
    cfg['schema'] = get_hana_schema_from_request(request)
    
    search = (request.GET.get('search') or '').strip()
    page_param = (request.GET.get('page') or '1').strip()
    page_size_param = (request.GET.get('page_size') or '').strip()
    try:
        page_num = int(page_param)
        if page_num < 1:
            page_num = 1
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
        'schema': '',  # Will be set dynamically below
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
   # logger = logging.getLogger(__name__)
    
    if request.method == 'POST':
        db_key = request.POST.get('database', get_default_company_key())
        request.session['selected_db'] = db_key
        request.session.modified = True  # Force session save
        
        # logger.info(f"Database switched to: {db_key}")
        # logger.info(f"Session key: {request.session.session_key}")
        # logger.info(f"Session data: {dict(request.session.items())}")
        
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
        
        # logger.info(f"Redirecting to: {new_url}")
        
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
        'schema': '',  # Will be set dynamically below
        'encrypt': os.environ.get('HANA_ENCRYPT') or '',
        'ssl_validate': os.environ.get('HANA_SSL_VALIDATE') or '',
    }

    # Resolve HANA schema using shared helper
    hana_schema = get_hana_schema_from_request(request)
    cfg['schema'] = hana_schema
    
    # logger.info(f"[CUSTOMER_POLICIES] Using HANA schema: {hana_schema}")

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
            
            # logger.info(f"[CUSTOMER_POLICIES] Querying policies for CardCode: {card_code}")
            
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

            # logger.info(f"[CUSTOMER_POLICIES] Found {len(data)} policies for {card_code}")

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
        #logger.error(f"[CUSTOMER_POLICIES] Error: {str(e)}")
        return Response({'success': False, 'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# ========================================
# Disease Identification & Recommended Products Endpoints
# ========================================

@swagger_auto_schema(
    tags=['Disease Management'],
    method='get',
    operation_description="""
    Get all disease identifications.
    
    Returns a list of all diseases with basic information and count of recommended products.
    """,
    manual_parameters=[
        openapi.Parameter(
            'is_active',
            openapi.IN_QUERY,
            description="Filter by active status (true/false)",
            type=openapi.TYPE_BOOLEAN,
            required=False
        ),
        openapi.Parameter(
            'search',
            openapi.IN_QUERY,
            description="Search by disease name or item code",
            type=openapi.TYPE_STRING,
            required=False
        ),
    ],
    responses={
        200: openapi.Response(
            description="List of diseases retrieved successfully",
            examples={
                "application/json": {
                    "success": True,
                    "count": 10,
                    "data": [
                        {
                            "id": 1,
                            "item_code": "FG00259",
                            "item_name": "FG00259",
                            "disease_name": "Potato virus Y",
                            "is_active": True,
                            "recommended_products_count": 3
                        }
                    ]
                }
            }
        )
    }
)
@api_view(['GET'])
def disease_list_api(request):
    """Get all disease identifications"""
    try:
        # Get query parameters
        is_active = request.GET.get('is_active')
        search = request.GET.get('search', '').strip()
        
        # Base queryset
        queryset = DiseaseIdentification.objects.all()
        
        # Apply filters
        if is_active is not None:
            is_active_bool = is_active.lower() in ['true', '1', 'yes']
            queryset = queryset.filter(is_active=is_active_bool)
        
        if search:
            from django.db.models import Q
            queryset = queryset.filter(
                Q(disease_name__icontains=search) |
                Q(item_code__icontains=search) |
                Q(item_name__icontains=search)
            )
        
        # Serialize
        serializer = DiseaseIdentificationListSerializer(queryset, many=True)
        
        return Response({
            'success': True,
            'count': queryset.count(),
            'data': serializer.data
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
       # logger.error(f"[DISEASE_LIST] Error: {str(e)}")
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@swagger_auto_schema(
    tags=['Disease Management'],
    method='get',
    operation_description="""
    Get disease details by ID or item code.
    
    Returns complete disease information including all recommended products.
    """,
    manual_parameters=[
        openapi.Parameter(
            'item_code',
            openapi.IN_QUERY,
            description="Disease item code (e.g., FG00259). Use this OR disease_id.",
            type=openapi.TYPE_STRING,
            required=False
        ),
    ],
    responses={
        200: openapi.Response(
            description="Disease details retrieved successfully",
            examples={
                "application/json": {
                    "success": True,
                    "data": {
                        "id": 1,
                        "doc_entry": "1235",
                        "item_code": "FG00259",
                        "item_name": "FG00259",
                        "description": "Potato virus Y (PVY) is one of the most serious viral diseases...",
                        "disease_name": "Potato virus Y",
                        "is_active": True,
                        "recommended_products_count": 2,
                        "recommended_products": [
                            {
                                "id": 1,
                                "product_item_code": "FG00100",
                                "product_name": "Antiviral Spray",
                                "dosage": "500ml per acre",
                                "priority": 1,
                                "effectiveness_rating": 8.5
                            }
                        ]
                    }
                }
            }
        ),
        404: "Disease not found"
    }
)
@api_view(['GET'])
def disease_detail_api(request, disease_id=None):
    """Get disease details with recommended products"""
    try:
        # Get disease by ID or item_code
        if disease_id:
            try:
                disease = DiseaseIdentification.objects.get(pk=disease_id)
            except DiseaseIdentification.DoesNotExist:
                return Response({
                    'success': False,
                    'error': f'Disease with ID {disease_id} not found'
                }, status=status.HTTP_404_NOT_FOUND)
        else:
            item_code = request.GET.get('item_code', '').strip()
            if not item_code:
                return Response({
                    'success': False,
                    'error': 'Either disease_id in URL or item_code parameter is required'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            try:
                disease = DiseaseIdentification.objects.get(item_code=item_code)
            except DiseaseIdentification.DoesNotExist:
                return Response({
                    'success': False,
                    'error': f'Disease with item code {item_code} not found'
                }, status=status.HTTP_404_NOT_FOUND)
        
        # Serialize
        serializer = DiseaseIdentificationSerializer(disease)
        
        return Response({
            'success': True,
            'data': serializer.data
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        #logger.error(f"[DISEASE_DETAIL] Error: {str(e)}")
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@swagger_auto_schema(
    method='get',
    tags=['Disease Management'],
    operation_id='recommended_products_list',
    operation_description="""
    Get recommended products for a specific disease with product images from HANA catalog.
    
    **How it works:**
    - Queries SAP @ODID table where each row maps: Product (U_ItemCode) → Disease (U_Disease)
    - For a disease name search, returns ALL products that treat that disease
    - Supports partial matching (e.g., "Downy mildew" matches "Downy mildew, Late blight")
    - Can search by product codes (comma-separated): "FG00051,FG00015,FG00041"
    
    **Returns:**
    - Multiple products if multiple products treat the same disease
    - Product images from HANA product catalog (OITM table)
    - Product descriptions (Urdu), item groups, generic names, brand names
    - Units of measure
    """,
    manual_parameters=[
        openapi.Parameter(
            'disease_id',
            openapi.IN_QUERY,
            description='Disease ID from Django database (optional if item_code or disease_name is provided)',
            type=openapi.TYPE_INTEGER,
            required=False
        ),
        openapi.Parameter(
            'item_code',
            openapi.IN_QUERY,
            description='Product code(s) from @ODID table. Can be single (FG00021) or comma-separated (FG00051,FG00015,FG00041)',
            type=openapi.TYPE_STRING,
            required=False
        ),
        openapi.Parameter(
            'disease_name',
            openapi.IN_QUERY,
            description='Disease name to search (partial match). Examples: "Downy mildew", "Late blight", "Wheat rusts"',
            type=openapi.TYPE_STRING,
            required=False
        ),
        openapi.Parameter(
            'database',
            openapi.IN_QUERY,
            description='Database/Company name (e.g., 4B-BIO_APP, 4B-ORANG_APP) for fetching product images and details from HANA catalog',
            type=openapi.TYPE_STRING,
            required=False,
            default=get_default_schema()
        ),
        openapi.Parameter(
            'include_inactive',
            openapi.IN_QUERY,
            description='Include inactive products (default: false)',
            type=openapi.TYPE_BOOLEAN,
            required=False,
            default=False
        ),
    ],
    responses={
        200: openapi.Response(
            description='List of recommended products with HANA catalog data',
            examples={
                'application/json': {
                    "success": True,
                    "disease_name": "Downy mildew",
                    "disease_item_code": "FG00021",
                    "database": "4B-BIO_APP",
                    "count": 3,
                    "data": [
                        {
                            "priority": 1,
                            "product_item_code": "FG00021",
                            "product_name": "Keeper 50 WP - 500-Gms.",
                            "dosage": "As per product label",
                            "application_method": "Follow product instructions",
                            "timing": "At first symptoms or preventively",
                            "product_image_url": "/media/product_images/4B-BIO/Keeper.jpg",
                            "product_description_urdu_url": "/media/product_images/4B-BIO/Keeper-urdu.jpg",
                            "item_group_name": "Fungicides",
                            "generic_name": "Copper Oxychloride 50% WP",
                            "brand_name": "Keeper",
                            "unit_of_measure": "500 GMS"
                        },
                        {
                            "priority": 2,
                            "product_item_code": "FG00041",
                            "product_name": "Shield Plus - 1-Ltr.",
                            "dosage": "As per product label",
                            "application_method": "Follow product instructions",
                            "timing": "At first symptoms or preventively",
                            "product_image_url": "/media/product_images/4B-BIO/Shield.jpg",
                            "product_description_urdu_url": "/media/product_images/4B-BIO/Shield-urdu.jpg",
                            "item_group_name": "Fungicides",
                            "generic_name": "Mancozeb 75% WP",
                            "brand_name": "Shield Plus",
                            "unit_of_measure": "1 LTR"
                        },
                        {
                            "priority": 3,
                            "product_item_code": "FG00052",
                            "product_name": "Wilson 50 WP - 350-Gms.",
                            "dosage": "As per product label",
                            "application_method": "Follow product instructions",
                            "timing": "At first symptoms or preventively",
                            "product_image_url": "/media/product_images/4B-BIO/Wilson.jpg",
                            "product_description_urdu_url": "/media/product_images/4B-BIO/Wilson-urdu.jpg",
                            "item_group_name": "Fungicides",
                            "generic_name": "Metalaxyl 8% + Mancozeb 64% WP",
                            "brand_name": "Wilson",
                            "unit_of_measure": "350 GMS"
                        }
                    ]
                }
            }
        ),
        400: "Bad request - missing required parameters (disease_id, item_code, or disease_name)",
        404: "Disease not found"
    }
)
@api_view(['GET'])
def recommended_products_api(request):
    """Get recommended products for a disease - queries directly from SAP @ODID and OITM tables"""
    try:
        from hdbcli import dbapi
        
        disease_id = request.GET.get('disease_id')
        item_code = request.GET.get('item_code', '').strip()
        disease_name = request.GET.get('disease_name', '').strip()
        # Recommended products must follow Product Catalog visibility rules.
        # Keep query param for backward compatibility but do not relax visibility.
        include_inactive = (request.GET.get('include_inactive', '') or '').strip().lower() in ('true', '1', 'yes', 'y')
        
        # Get database parameter - always resolve via Company.name (actual HANA schema)
        db_param = (request.GET.get('database') or request.session.get('selected_db') or '').strip()
        hana_schema = resolve_company_to_schema(db_param) if db_param else ''
        if not hana_schema:
            try:
                first = Company.objects.filter(is_active=True).first()
                hana_schema = first.name if first else ''
            except Exception:
                pass
        if not hana_schema:
            return Response({
                'success': False,
                'error': 'Database parameter is required (e.g., database=4B-BIO_APP or database=4B-ORANG_APP)'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Load environment variables
        _hana_load_env_file(os.path.join(os.path.dirname(__file__), '.env'))
        _hana_load_env_file(os.path.join(str(settings.BASE_DIR), '.env'))
        _hana_load_env_file(os.path.join(str(Path(settings.BASE_DIR).parent), '.env'))
        _hana_load_env_file(os.path.join(os.getcwd(), '.env'))
        
        cfg = {
            'host': os.environ.get('HANA_HOST') or '',
            'port': os.environ.get('HANA_PORT') or '',
            'user': os.environ.get('HANA_USER') or '',
            'encrypt': os.environ.get('HANA_ENCRYPT') or '',
            'schema': hana_schema
        }
        
        pwd = os.environ.get('HANA_PASSWORD', '')
        kwargs = {
            'address': cfg['host'],
            'port': int(cfg['port']),
            'user': cfg['user'],
            'password': pwd
        }
        
        if str(cfg['encrypt']).strip().lower() in ('true', '1', 'yes'):
            kwargs['encrypt'] = True
            kwargs['sslValidateCertificate'] = False
        
        conn = dbapi.connect(**kwargs)
        
        try:
            import re as _re
            schema_name = cfg['schema']
            # Build a safely-quoted schema prefix (handles hyphens like "4B-AGRI_LIVE")
            _sch_q = schema_name if _re.match(r'^[A-Za-z0-9_]+$', schema_name) else '"' + schema_name.replace('"', '""') + '"'
            _odid  = _sch_q + '."@ODID"'
            _oitm  = _sch_q + '."OITM"'
            _oitb  = _sch_q + '."OITB"'
            _atc1  = _sch_q + '."ATC1"'

            # Query @ODID table for disease
            disease_info = None
            product_item_codes = []
            
            if item_code:
                # Query by product code(s) - can be single or comma-separated list
                # e.g., "FG00051" or "FG00051,FG00015,FG00041"
                item_codes = [code.strip() for code in item_code.split(',') if code.strip()]
                
                cur = conn.cursor()
                placeholders = ','.join(['?' for _ in item_codes])
                cur.execute(
                    f'SELECT "DocEntry", "U_ItemCode", "U_ItemName", "U_Disease" '
                    f'FROM {_odid} WHERE "U_ItemCode" IN ({placeholders})',
                    tuple(item_codes)
                )
                rows = cur.fetchall()
                if rows:
                    disease_info = {
                        'doc_entry': rows[0][0],
                        'item_code': rows[0][1],
                        'item_name': rows[0][2],
                        'disease_name': rows[0][3]
                    }
                    # Collect ALL unique product codes
                    seen = set()
                    product_item_codes = []
                    for row in rows:
                        if row[1] and row[1] not in seen:
                            seen.add(row[1])
                            product_item_codes.append(row[1])
                cur.close()
            elif disease_name:
                # Query by disease name - can return multiple product codes for same disease
                # Note: U_ItemCode in @ODID is the PRODUCT code, not disease code
                # Each row maps: Product (U_ItemCode) -> Disease (U_Disease)
                # We search U_Disease to find ALL products that treat this disease
                cur = conn.cursor()
                cur.execute(
                    f'SELECT "DocEntry", "U_ItemCode", "U_ItemName", "U_Disease" '
                    f'FROM {_odid} '
                    'WHERE UPPER("U_Disease") LIKE ? OR UPPER("U_ItemCode") = ? OR UPPER("U_ItemName") LIKE ?',
                    (f'%{disease_name.upper()}%', disease_name.upper(), f'%{disease_name.upper()}%')
                )
                rows = cur.fetchall()
                if rows:
                    # Use first row for disease info (primary disease match)
                    disease_info = {
                        'doc_entry': rows[0][0],
                        'item_code': rows[0][1],  # First product code
                        'item_name': rows[0][2],
                        'disease_name': rows[0][3]
                    }
                    # Collect ALL unique product codes (U_ItemCode) for this disease
                    # Remove duplicates while preserving order
                    seen = set()
                    product_item_codes = []
                    for row in rows:
                        if row[1] and row[1] not in seen:
                            seen.add(row[1])
                            product_item_codes.append(row[1])
                cur.close()
            else:
                conn.close()
                return Response({
                    'success': False,
                    'error': 'Either item_code or disease_name parameter is required'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            if not disease_info:
                conn.close()
                return Response({
                    'success': False,
                    'error': f'Disease not found in SAP @ODID table'
                }, status=status.HTTP_404_NOT_FOUND)
            
            # Fetch product details from OITM for all item codes
            products_data = []

            def _media_url(raw_path):
                """Return encoded relative media URL (no absolute/full URL)."""
                if not raw_path:
                    return None
                try:
                    from urllib.parse import quote
                    encoded = quote(raw_path, safe='/:._-')
                except Exception:
                    encoded = raw_path
                return encoded
            
            if product_item_codes:
                # Extract database folder name for images
                # Examples: 4B-BIO_APP -> 4B-BIO, 4B-ORANG_APP -> 4B-ORANG, 4B-AGRI_LIVE -> 4B-AGRI
                folder_name = hana_schema.replace('_APP', '').replace('_LIVE', '').replace('_TEST', '').strip()
                
                for idx, prod_code in enumerate(product_item_codes, 1):
                    try:
                        cur = conn.cursor()
                        sql = f'''
                        SELECT 
                            T0."ItemCode",
                            T0."ItemName",
                            T1."ItmsGrpNam",
                            T0."SalPackMsr",
                            T0."InvntryUom",
                            T0."U_GenericName",
                            T0."U_BrandName",
                            MIN(CASE WHEN LOWER(TRIM(A."FileExt")) IN ('jpeg', 'jpg', 'png', 'webp')
                                     THEN A."FileName" || '.' || A."FileExt" END) AS "Product_Image",
                            MAX(CASE WHEN A."U_IMG_C" = 'Product Description Urdu'
                                     THEN A."FileName" || '.' || A."FileExt" END) AS "Product_Description_Urdu"
                        FROM {_oitm} T0
                        INNER JOIN {_oitb} T1 ON T0."ItmsGrpCod" = T1."ItmsGrpCod"
                        LEFT JOIN {_atc1} A ON A."AbsEntry" = T0."AtcEntry"
                        WHERE T0."ItemCode" = ?
                                                    AND T0."Series" = '77'
                                                    AND T0."validFor" = 'Y'
                                                    AND T0."U_IsActive" = 'Y'
                        GROUP BY
                            T0."ItemCode",
                            T0."ItemName",
                            T1."ItmsGrpNam",
                            T0."SalPackMsr",
                            T0."InvntryUom",
                            T0."U_GenericName",
                            T0."U_BrandName"
                        '''
                        cur.execute(sql, (prod_code,))
                        row = cur.fetchone()
                        
                        if row:
                            # Extract product name - use only the part before " - " if exists
                            full_product_name = row[1].strip() if row[1] else prod_code
                            # Split by " - " and take first part (e.g., "Map" from "Map - 25-Kgs.")
                            product_name = full_product_name.split(' - ')[0].strip() if ' - ' in full_product_name else full_product_name
                            
                            # Build image URLs
                            product_image = row[7]
                            if product_image:
                                product_image_url = f'/media/product_images/{folder_name}/{product_image}'
                            else:
                                # Fallback to product name-based naming (e.g., Badar.jpg, Haryali.jpg, Map.jpg)
                                product_image_url = f'/media/product_images/{folder_name}/{product_name}.jpg'
                            
                            # Follow products_catalog logic: only use explicit Urdu attachment label.
                            product_desc_urdu = row[8]
                            if product_desc_urdu:
                                urdu_url = f'/media/product_images/{folder_name}/{product_desc_urdu}'
                            else:
                                urdu_url = None

                            product_image_url = _media_url(product_image_url)
                            urdu_url = _media_url(urdu_url)
                            # Keep only relative URLs in response (requested by client).
                            # product_image_url_full = request.build_absolute_uri(product_image_url)
                            # urdu_url_full = request.build_absolute_uri(urdu_url)
                            
                            product = {
                                'priority': idx,
                                'product_item_code': row[0],
                                'product_name': row[1],
                                'item_group_name': row[2],
                                'unit_of_measure': row[3] or row[4],
                                'generic_name': row[5],
                                'brand_name': row[6],
                                'product_image_url': product_image_url,
                                'product_description_urdu_url': urdu_url,
                                # Additional fields
                                'dosage': f'As per product label',
                                'application_method': 'Follow product instructions',
                                'timing': 'At first symptoms or preventively',
                            }
                            products_data.append(product)
                        
                        cur.close()
                        
                    except Exception as e:
                        #logger.warning(f"Could not fetch product {prod_code}: {str(e)}")
                        continue
            
            return Response({
                'success': True,
                'disease_name': disease_info['disease_name'],
                'disease_item_code': disease_info['item_code'],
                'database': hana_schema,
                'count': len(products_data),
                'data': products_data
            }, status=status.HTTP_200_OK)
            
        finally:
            conn.close()
        
    except Exception as e:
       # logger.error(f"[RECOMMENDED_PRODUCTS] Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@swagger_auto_schema(
    tags=['SAP Projects'], 
    method='get',
    operation_description="""
    Get list of SAP projects (OPRJ) with optional filters.
    
    **Default Behavior**: Returns only VALID policies where at least one date field is set and not expired.
    
    **Validity Logic**: Project is valid if:
    - `U_InvEndDate` IS NOT NULL AND `U_InvEndDate` >= current date, **OR**
    - `U_Ct` IS NOT NULL AND `U_Ct` >= current date
    
    **Note**: 
    - Projects where both `U_InvEndDate` and `U_Ct` are NULL are **excluded by default**
    - Uses `U_InvEndDate` or `U_Ct` (not `ValidTo`) for validity checks
    
    **Query Parameters**:
    - `database`: Specify company database (e.g., 4B-BIO_APP, 4B-AGRI_LIVE)
    - `active`: Filter by Active status (Y/N) - defaults to 'Y'
    - `is_valid`: Filter by validity (true/false) - defaults to true
    - `code`: Filter by exact project code
    - `name`: Filter by project name (partial match)
    
    **Examples**:
    - `/api/sap/policies/?database=4B-AGRI_LIVE` - Only valid & active policies (default)
    - `/api/sap/policies/?database=4B-AGRI_LIVE&is_valid=false` - Only expired policies
    - `/api/sap/policies/?database=4B-AGRI_LIVE&active=N` - Inactive policies (valid only)
    """,
    manual_parameters=[
        openapi.Parameter(
            'database',
            openapi.IN_QUERY,
            description="Company database (e.g., 4B-BIO_APP, 4B-AGRI_LIVE, 4B-ORANG_APP)",
            type=openapi.TYPE_STRING,
            required=False
        ),
        openapi.Parameter(
            'active',
            openapi.IN_QUERY,
            description="Filter by active status in SAP Projects (Y/N). Default: Y (active only)",
            type=openapi.TYPE_STRING,
            required=False,
            enum=['Y', 'N'],
            default='Y'
        ),
        openapi.Parameter(
            'is_valid',
            openapi.IN_QUERY,
            description="Filter by policy validity. Default: true (returns projects where U_InvEndDate >= current date OR U_Ct >= current date). Set to false to get expired policies. Projects with both dates NULL are excluded when is_valid=true.",
            type=openapi.TYPE_BOOLEAN,
            required=False,
            default=True
        ),
        openapi.Parameter(
            'code',
            openapi.IN_QUERY,
            description="Filter by project code (exact match)",
            type=openapi.TYPE_STRING,
            required=False
        ),
        openapi.Parameter(
            'name',
            openapi.IN_QUERY,
            description="Filter by project name (partial match, case-insensitive)",
            type=openapi.TYPE_STRING,
            required=False
        ),
    ],
    responses={
        200: openapi.Response(
            description="Projects retrieved successfully with is_valid field calculated based on U_InvEndDate and U_Ct",
            examples={
                "application/json": {
                    "success": True,
                    "count": 2,
                    "database": "4B-AGRI_LIVE",
                    "data": [
                        {
                            "code": "0123003",
                            "name": "Current Policy 2026",
                            "valid_from": "2026-01-01T00:00:00",
                            "valid_to": "2027-12-31T00:00:00",
                            "u_inv_end_date": "2027-12-31T00:00:00",
                            "u_ct": "2027-12-31T00:00:00",
                            "active": "tYES",
                            "policy": "05",
                            "is_valid": True
                        },
                        {
                            "code": "0123004",
                            "name": "DOSTI Policy 2026-27",
                            "valid_from": "2026-03-01T00:00:00",
                            "valid_to": "2027-06-30T00:00:00",
                            "u_inv_end_date": "2027-06-30T00:00:00",
                            "u_ct": "2027-06-30T00:00:00",
                            "active": "tYES",
                            "policy": "03",
                            "is_valid": True
                        }
                    ]
                }
            }
        ),
        500: openapi.Response(
            description="Database connection error",
            examples={
                "application/json": {
                    "success": False,
                    "error": "Connection failed"
                }
            }
        )
    }
)
@api_view(['GET'])
def projects_list_api(request):
    """
    Get list of SAP projects from OPRJ table.
    Endpoint: GET /api/sap/policies/
    
    By default, returns VALID policies where:
    - (U_InvEndDate IS NOT NULL AND U_InvEndDate >= current date) OR
    - (U_Ct IS NOT NULL AND U_Ct >= current date)
    
    Projects with both dates NULL are excluded by default.
    
    Query params:
    - database: Company database (e.g., 4B-BIO_APP, 4B-AGRI_LIVE)
    - active: Filter by active status (Y/N) - Default: Y
    - is_valid: Filter by validity (true/false) - Default: true
    - code: Filter by project code (exact match)
    - name: Filter by project name (partial match)
    
    Examples:
    - ?database=4B-AGRI_LIVE - Only valid & active policies (default)
    - ?database=4B-AGRI_LIVE&is_valid=false - Only expired policies
    - ?database=4B-AGRI_LIVE&active=N&is_valid=true - Inactive but valid policies
    """
    try:
        from hdbcli import dbapi
        from datetime import date, datetime
        
        # Load environment from multiple possible locations
        try:
            _hana_load_env_file(os.path.join(os.path.dirname(__file__), '.env'))
            _hana_load_env_file(os.path.join(str(settings.BASE_DIR), '.env'))
            _hana_load_env_file(os.path.join(str(Path(settings.BASE_DIR).parent), '.env'))
            _hana_load_env_file(os.path.join(os.getcwd(), '.env'))
        except Exception:
            pass
        
        # Get HANA connection parameters from environment
        hana_host = os.environ.get('HANA_HOST', '')
        hana_port = os.environ.get('HANA_PORT', '30015')
        hana_user = os.environ.get('HANA_USER', '')
        hana_password = os.environ.get('HANA_PASSWORD', '')
        
        # Use explicitly provided schema as-is (e.g., 4B-AGRI_LIVE) to avoid
        # fallback mapping that can collapse to a different company schema.
        explicit_schema = (
            (request.GET.get('database') or '').strip()
            or (request.GET.get('company') or '').strip()
        )
        schema = explicit_schema or get_hana_schema_from_request(request)
        # logger.info(f"[PROJECTS_LIST] Using schema: {schema}")
        
        # Get filter parameters
        active_filter = request.GET.get('active', 'Y').upper()  # Default to active only
        code_filter = request.GET.get('code', '').strip()
        name_filter = request.GET.get('name', '').strip()
        is_valid_param = request.GET.get('is_valid', 'true').strip().lower()  # Default to valid only
        
        if not hana_host or not hana_user or not hana_password:
            return Response({
                'success': False,
                'error': 'Missing HANA connection parameters in environment'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        # Connect without setting schema initially
        conn = dbapi.connect(
            address=hana_host,
            port=int(hana_port),
            user=hana_user,
            password=hana_password
        )
        
        try:
            # Set schema using SQL (handles special characters like hyphens)
            cursor = conn.cursor()
            cursor.execute(f'SET SCHEMA "{schema}"')
            cursor.close()
            
            # Build query with filters
            base_query = '''
                SELECT
                    P."PrjCode" AS "code",
                    P."PrjName" AS "name",
                    P."ValidFrom" AS "valid_from",
                    P."ValidTo" AS "valid_to",
                    P."U_InvEndDate" AS "u_inv_end_date",
                    P."U_Ct" AS "u_ct",
                    CASE
                        WHEN P."Active" = 'Y' THEN 'tYES'
                        ELSE 'tNO'
                    END AS "active",
                    P."U_pol" AS "policy"
                FROM OPRJ P
                WHERE 1=1
            '''
            
            params = []
            
            # Apply active filter
            if active_filter in ['Y', 'N']:
                base_query += ' AND P."Active" = ?'
                params.append(active_filter)
            
            # Apply code filter
            if code_filter:
                base_query += ' AND P."PrjCode" = ?'
                params.append(code_filter)
            
            # Apply name filter (partial match)
            if name_filter:
                base_query += ' AND UPPER(P."PrjName") LIKE ?'
                params.append(f'%{name_filter.upper()}%')
            
            # Apply validity filter at SQL level (default: only valid policies)
            # Valid if: (U_InvEndDate IS NOT NULL AND >= CURRENT_DATE) OR (U_Ct IS NOT NULL AND >= CURRENT_DATE)
            if is_valid_param in ('true', '1', 'yes', 't', 'y'):
                base_query += '''
                    AND (
                        (P."U_InvEndDate" IS NOT NULL AND P."U_InvEndDate" >= CURRENT_DATE)
                        OR (P."U_Ct" IS NOT NULL AND P."U_Ct" >= CURRENT_DATE)
                    )
                '''
            elif is_valid_param in ('false', '0', 'no', 'f', 'n'):
                # Only expired: both dates exist and both are in the past
                base_query += '''
                    AND (
                        (P."U_InvEndDate" IS NOT NULL OR P."U_Ct" IS NOT NULL)
                        AND (
                            (P."U_InvEndDate" IS NULL OR P."U_InvEndDate" < CURRENT_DATE)
                            AND (P."U_Ct" IS NULL OR P."U_Ct" < CURRENT_DATE)
                        )
                    )
                '''
            # If is_valid_param is 'all' or other value, don't apply validity filter
            
            base_query += ' ORDER BY P."PrjCode"'
            
            # logger.info(f"[PROJECTS_LIST] Executing query with params: {params}")
            cursor.execute(base_query, params)
            
            columns = [desc[0] for desc in cursor.description]
            results = []
            
            # Get current date for validation
            from datetime import date as date_class
            current_date = date_class.today()
            
            for row in cursor.fetchall():
                row_dict = {}
                inv_end_date = None
                u_ct_date = None
                
                for i, col in enumerate(columns):
                    value = row[i]
                    
                    # Store U_InvEndDate for validation (convert to date object)
                    if col == 'u_inv_end_date' and value is not None:
                        if isinstance(value, datetime):
                            inv_end_date = value.date()
                        elif isinstance(value, date):
                            inv_end_date = value
                    
                    # Store U_Ct for validation (convert to date object)
                    if col == 'u_ct' and value is not None:
                        if isinstance(value, datetime):
                            u_ct_date = value.date()
                        elif isinstance(value, date):
                            u_ct_date = value
                    
                    # Convert dates to string for JSON response
                    if isinstance(value, (date, datetime)):
                        value = value.isoformat()
                    row_dict[col] = value
                
                # Add is_valid field based on U_InvEndDate OR U_Ct
                # Valid if either U_InvEndDate >= current_date OR U_Ct >= current_date
                is_valid_by_inv_end = inv_end_date and current_date <= inv_end_date
                is_valid_by_ct = u_ct_date and current_date <= u_ct_date
                
                if is_valid_by_inv_end or is_valid_by_ct:
                    row_dict['is_valid'] = True
                elif inv_end_date or u_ct_date:
                    # If at least one date exists but neither is valid
                    row_dict['is_valid'] = False
                else:
                    # If no dates are set, consider it valid
                    row_dict['is_valid'] = True
                
                results.append(row_dict)
            
            cursor.close()
            
            # is_valid filtering is now done at SQL level, no need for post-processing
            
            return Response({
                'success': True,
                'count': len(results),
                'database': schema,
                'data': results
            }, status=status.HTTP_200_OK)
            
        finally:
            conn.close()
        
    except Exception as e:
        #logger.error(f"[PROJECTS_LIST] Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# ============= Policy Detail Endpoint =============

@swagger_auto_schema(
    tags=['SAP Policies'],
    method='get',
    operation_summary="Policy Detail",
    operation_description="""Get detailed information for a specific policy from OPLN table.
    
    **Response includes:**
    - Policy code and name
    - Validity dates
    - Active status
    - Currency information
    - Rounding and pricing rules
    - All additional policy metadata
    
    **Use this when user clicks on a policy to see more details.**
    """,
    manual_parameters=[
        openapi.Parameter(
            'database',
            openapi.IN_QUERY,
            description="Company database (e.g., 4B-BIO_APP, 4B-ORANG_APP)",
            type=openapi.TYPE_STRING,
            required=False
        ),
        openapi.Parameter(
            'code',
            openapi.IN_QUERY,
            description="Policy code/ListNum (required)",
            type=openapi.TYPE_STRING,
            required=True
        ),
    ],
    responses={
        200: openapi.Response(
            description="Policy details retrieved successfully",
            examples={
                "application/json": {
                    "success": True,
                    "database": "4B-ORANG_APP",
                    "data": {
                        "code": "1",
                        "name": "Orange Protection Closing Balance Policy 2022/23",
                        "valid_from": "2023-01-01T00:00:00",
                        "valid_to": "2025-12-31T00:00:00",
                        "active": "Y",
                        "currency": "AUD",
                        "base_num": "1",
                        "factor": "1.0",
                        "round_sys": "0",
                        "group_code": "1",
                        "is_gross_price": "N",
                        "created_date": "2022-12-01T00:00:00"
                    }
                }
            }
        ),
        400: openapi.Response(
            description="Bad Request - missing code parameter",
            examples={
                "application/json": {
                    "success": False,
                    "error": "code parameter is required"
                }
            }
        ),
        404: openapi.Response(
            description="Policy not found",
            examples={
                "application/json": {
                    "success": False,
                    "error": "Policy with code 999 not found"
                }
            }
        ),
        500: openapi.Response(
            description="Server error",
            examples={
                "application/json": {
                    "success": False,
                    "error": "Database connection failed"
                }
            }
        )
    }
)
@api_view(['GET'])
def policy_detail_api(request):
    """
    Get detailed information for a specific policy from SAP HANA OPLN table.
    
    Endpoint: GET /api/sap/policies/detail/
    Query params: ?database=4B-ORANG_APP&code=1
    """
    try:
        from hdbcli import dbapi
        from datetime import date, datetime
        
        # Get policy code from query parameters
        policy_code = request.GET.get('code', '').strip()
        
        if not policy_code:
            return Response({
                'success': False,
                'error': 'code parameter is required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Load environment from multiple possible locations
        try:
            _hana_load_env_file(os.path.join(os.path.dirname(__file__), '.env'))
            _hana_load_env_file(os.path.join(str(settings.BASE_DIR), '.env'))
            _hana_load_env_file(os.path.join(str(Path(settings.BASE_DIR).parent), '.env'))
            _hana_load_env_file(os.path.join(os.getcwd(), '.env'))
        except Exception:
            pass
        
        # Get HANA connection parameters from environment
        hana_host = os.environ.get('HANA_HOST', '')
        hana_port = os.environ.get('HANA_PORT', '30015')
        hana_user = os.environ.get('HANA_USER', '')
        hana_password = os.environ.get('HANA_PASSWORD', '')
        
        # Use explicitly provided schema as-is (e.g., 4B-AGRI_LIVE) to avoid
        # fallback mapping that can collapse to a different company schema.
        explicit_schema = (
            (request.GET.get('database') or '').strip()
            or (request.GET.get('company') or '').strip()
        )
        schema = explicit_schema or get_hana_schema_from_request(request)
        # logger.info(f"[POLICY_DETAIL] Using schema: {schema}, code: {policy_code}")
        
        if not hana_host or not hana_user or not hana_password:
            return Response({
                'success': False,
                'error': 'Missing HANA connection parameters in environment'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        # Connect to HANA
        conn = dbapi.connect(
            address=hana_host,
            port=int(hana_port),
            user=hana_user,
            password=hana_password
        )
        
        try:
            # Set schema using SQL (handles special characters like hyphens)
            cursor = conn.cursor()
            cursor.execute(f'SET SCHEMA "{schema}"')
            cursor.close()
            
            # TODO: Update this query with actual OPLN table columns after checking HANA
            query = '''
                SELECT 
                    "ListNum" AS "code",
                    "ListName" AS "name",
                    "ValidFrom" AS "valid_from",
                    "ValidTo" AS "valid_to",
                    "ValidFor" AS "active",
                    "CreateDate" AS "created_date",
                    "UpdateDate" AS "updated_date",
                    "PrimCurr" AS "currency",
                    "GroupCode" AS "group_code",
                    "Factor" AS "factor",
                    "RoundSys" AS "round_sys",
                    "IsGrossPrc" AS "is_gross_price",
                    "BASE_NUM" AS "base_num",
                    "RoundRule" AS "round_rule",
                    "ExtAmount" AS "ext_amount"
                FROM "OPLN"
                WHERE "ListNum" = ?
            '''
            
            cursor = conn.cursor()
            cursor.execute(query, (policy_code,))
            
            # Get column names
            columns = [desc[0] for desc in cursor.description]
            
            # Fetch the result
            row = cursor.fetchone()
            
            if not row:
                cursor.close()
                conn.close()
                return Response({
                    'success': False,
                    'error': f'Policy with code {policy_code} not found'
                }, status=status.HTTP_404_NOT_FOUND)
            
            # Convert row to dictionary
            policy_data = {}
            for i, col in enumerate(columns):
                value = row[i]
                # Convert dates to ISO format string
                if isinstance(value, (date, datetime)):
                    value = value.isoformat()
                policy_data[col] = value
            
            cursor.close()
            
            # logger.info(f"[POLICY_DETAIL] Successfully retrieved policy: {policy_code}")
            
            return Response({
                'success': True,
                'database': schema,
                'data': policy_data
            }, status=status.HTTP_200_OK)
            
        finally:
            conn.close()
        
    except Exception as e:
        #logger.error(f"[POLICY_DETAIL] Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# ============= Product Catalog with Document Display =============

# Removed from Swagger - this is a web page view, not an API endpoint
# Use /api/sap/product-description-download/ for file downloads
# Use /api/sap/product-description/ for JSON response with description text
def product_document_api(request, item_code):
    """View product document as formatted HTML page (for browser viewing, not API)"""
    return product_document_view(request, item_code)

def product_catalog_list_view(request):
    """
    Display products catalog with option to view detailed documents
    """
    try:
        _hana_load_env_file(os.path.join(os.path.dirname(__file__), '.env'))
        _hana_load_env_file(os.path.join(str(settings.BASE_DIR), '.env'))
        _hana_load_env_file(os.path.join(str(Path(settings.BASE_DIR).parent), '.env'))
        _hana_load_env_file(os.path.join(os.getcwd(), '.env'))
    except Exception:
        pass
    
    # Get database from query param
    database = request.GET.get('database', '').strip() or request.session.get('selected_database', '')
    search = request.GET.get('search', '').strip()
    item_group = request.GET.get('item_group', '').strip()
    
    # If no database selected, try to get from companies
    if not database:
        try:
            company = Company.objects.filter(is_active=True).first()
            if company:
                database = company.Company_name
                # logger.info(f"Using first active company: {database}")
        except Exception as e:
            pass
            # logger.warning(f"Could not get company from database: {e}")
    
    products = []
    categories = []
    error_msg = None
    
    try:
        from hdbcli import dbapi
        
        cfg = {
            'host': os.environ.get('HANA_HOST') or '',
            'port': os.environ.get('HANA_PORT') or '30015',
            'user': os.environ.get('HANA_USER') or '',
            'schema': database,
            'encrypt': os.environ.get('HANA_ENCRYPT') or '',
            'ssl_validate': os.environ.get('HANA_SSL_VALIDATE') or '',
        }
        
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
            cur = conn.cursor()
            if cfg['schema']:
                schema_name = cfg['schema']
                cur.execute(f'SET SCHEMA "{schema_name}"')
            
            # Get products
            catalog_result = products_catalog(
                conn, 
                schema_name=database,
                search=search,
                item_group=item_group
            )
            # Handle new dictionary format
            products = catalog_result.get('products', []) if isinstance(catalog_result, dict) else catalog_result
            
            # Get unique categories
            categories_dict = {}
            for product in products:
                grp_code = product.get('ItmsGrpCod')
                grp_name = product.get('ItmsGrpNam')
                if grp_code and grp_name and grp_code not in categories_dict:
                    categories_dict[grp_code] = grp_name
            
            categories = [{'code': k, 'name': v} for k, v in sorted(categories_dict.items(), key=lambda x: x[1])]
        
        finally:
            conn.close()
            
    except Exception as e:
        #logger.error(f"Error loading products: {e}")
        error_msg = str(e)
    
    context = {
        'products': products,
        'categories': categories,
        'database': database,
        'search': search,
        'selected_item_group': item_group,
        'error_msg': error_msg,
    }
    
    return render(request, 'sap_integration/product_catalog_list.html', context)


def product_document_view(request, item_code):
    """
    Display product details with parsed Word document content
    Uses the product description API to get product info and description
    """
    from .utils.document_parser import get_product_document_path
    import json
    
    # Get database from query param
    database = request.GET.get('database', '').strip() or request.session.get('selected_database', '')
    parse_method = request.GET.get('method', 'mammoth')
    
    # If no database selected, try to get from companies
    if not database:
        try:
            company = Company.objects.filter(is_active=True).first()
            if company:
                database = company.Company_name
                # logger.info(f"Using first active company: {database}")
        except Exception as e:
            # logger.warning(f"Could not get company from database: {e}")
            pass
    
    # logger.info(f"Product document view - ItemCode: {item_code}, Database: {database}")
    
    product = None
    error_msg = None
    file_path = None
    download_url = None
    doc_file_name = None
    doc_file_ext = None
    product_description = None
    
    try:
        # Call the product description API internally
        from django.test import RequestFactory
        factory = RequestFactory()
        
        # Create API request with proper GET parameters
        api_request = factory.get('/api/sap/product-description/', {
            'item_code': item_code,
            'database': database
        })
        
        # Copy session and user if they exist
        if hasattr(request, 'session'):
            api_request.session = request.session
        if hasattr(request, 'user'):
            api_request.user = request.user
        
        # logger.info(f"Calling get_product_description_api with item_code={item_code}, database={database}")
        
        # Call the API view
        api_response = get_product_description_api(api_request)
        
        # Render the response before accessing content
        api_response.render()
        
        # logger.info(f"API response status: {api_response.status_code}")
        
        if api_response.status_code == 200:
            response_data = json.loads(api_response.content)
            
            if response_data.get('success'):
                data = response_data.get('data', {})
                
                # Extract description
                product_description = data.get('description')
                
                # Extract document file info
                doc_file_name = data.get('urdu_file')
                doc_file_ext = data.get('urdu_ext')
                
                # Determine folder for image URL
                folder = database.replace('_APP', '').replace('_LIVE', '').replace('_TEST', '').strip()
                
                # Build basic product info for display
                product = {
                    'ItemCode': data.get('item_code'),
                    'ItemName': data.get('item_name'),
                    'product_image_url': f"/media/product_images/{folder}/{data.get('image_file')}.{data.get('image_ext')}" if data.get('image_file') and data.get('image_ext') else None,
                }
                
                # Build download URL only if document file exists
                if doc_file_name and doc_file_ext:
                    file_path = get_product_document_path(doc_file_name, doc_file_ext, database)
                    
                    if file_path and os.path.exists(file_path):
                        download_url = f"/api/sap/product-description-download/?item_code={item_code}&database={database}"
                        # logger.info(f"Document file found for {item_code}: {file_path}")
                    else:
                        pass
                        # logger.warning(f"Document file not found: {doc_file_name}.{doc_file_ext}")
            else:
                error_msg = response_data.get('error', 'Failed to load product description')
                # logger.error(f"API returned success=false: {error_msg}")
        else:
            # Try to extract error from response
            try:
                response_data = json.loads(api_response.content)
                error_msg = response_data.get('error', f"API returned status {api_response.status_code}")
                # logger.error(f"API error response: {response_data}")
            except Exception as parse_err:
                error_msg = f"API returned status {api_response.status_code}"
                # logger.error(f"Could not parse API error response: {parse_err}")
                # logger.error(f"Raw response: {api_response.content[:500]}")
            
    except Exception as e:
        # logger.error(f"Error loading product document: {e}")
        error_msg = str(e)
        import traceback
        traceback.print_exc()
    
    context = {
        'product': product,
        'doc_content': None,  # No longer parsing documents
        'doc_info': None,
        'database': database,
        'parse_method': parse_method,
        'error_msg': error_msg,
        'file_path': file_path,
        'download_url': download_url,
        'doc_file_name': doc_file_name,
        'doc_file_ext': doc_file_ext,
        'item_code': item_code,
        'product_description': product_description,
    }
    
    return render(request, 'sap_integration/product_document_detail.html', context)


@swagger_auto_schema(
    tags=['Analytics Dashboard'], 
    method='get',
    operation_summary="Dealer Analytics Dashboard",
    operation_description="""
    Get comprehensive analytics for a dealer user.
    
    **This endpoint provides:**
    - Dealer's card_code from user_id
    - Total complaints submitted last month
    - Total active policies for this dealer
    - Total Kindwise plant identification records
    
    **Usage:**
    - Provide user_id to get dealer analytics
    - Returns 404 if dealer not found for user_id
    - Returns 404 if no card_code assigned to dealer
    
    **Example Request:**
    ```
    GET /api/analytics/dealer-analytics/?user_id=123&database=4B-AGRI_LIVE
    ```
    
    **Example Response:**
    ```json
    {
        "success": true,
        "user_id": 123,
        "card_code": "C00123",
        "dealer_name": "John Doe",
        "business_name": "ABC Traders",
        "analytics": {
            "complaints_last_month": 5,
            "total_policies": 3,
            "total_kindwise_records": 12,
            "last_month_start": "2026-01-01",
            "last_month_end": "2026-01-31"
        }
    }
    ```
    """,
    manual_parameters=[
        openapi.Parameter(
            'user_id', 
            openapi.IN_QUERY, 
            description="Portal User ID (required). Example: 123", 
            type=openapi.TYPE_INTEGER, 
            required=True
        ),
        openapi.Parameter(
            'database', 
            openapi.IN_QUERY, 
            description="SAP HANA database/schema name (e.g., 4B-AGRI_LIVE, 4B-BIO_APP). If not provided, uses default.", 
            type=openapi.TYPE_STRING, 
            required=False
        ),
    ],
    responses={
        200: openapi.Response(
            description="Dealer analytics retrieved successfully",
            examples={
                "application/json": {
                    "success": True,
                    "user_id": 123,
                    "card_code": "C00123",
                    "dealer_name": "John Doe",
                    "business_name": "ABC Traders",
                    "analytics": {
                        "complaints_last_month": 5,
                        "total_policies": 3,
                        "total_kindwise_records": 12,
                        "last_month_start": "2026-01-01",
                        "last_month_end": "2026-01-31"
                    }
                }
            }
        ),
        400: openapi.Response(
            description="Bad request - missing user_id",
            examples={
                "application/json": {
                    "success": False,
                    "error": "user_id parameter is required"
                }
            }
        ),
        404: openapi.Response(
            description="Dealer not found",
            examples={
                "application/json": {
                    "success": False,
                    "error": "Dealer not found for user_id: 123"
                }
            }
        ),
        500: openapi.Response(
            description="Server error",
            examples={
                "application/json": {
                    "success": False,
                    "error": "Database connection failed"
                }
            }
        )
    }
)
@api_view(['GET'])
def dealer_analytics_api(request):
    """
    Get dealer analytics dashboard data
    
    Query Parameters:
        - user_id (required): Portal user ID
        - database (optional): SAP HANA schema name
    
    Returns:
        JSON response with dealer analytics
    """
    try:
        # Get user_id parameter
        user_id = request.GET.get('user_id', '').strip()
        
        # Validate user_id parameter
        if not user_id:
            return Response({
                'success': False,
                'error': 'user_id parameter is required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            user_id = int(user_id)
        except ValueError:
            return Response({
                'success': False,
                'error': 'user_id must be a valid integer'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Get dealer by user_id
        from FieldAdvisoryService.models import Dealer
        from complaints.models import Complaint
        from kindwise.models import KindwiseIdentification
        from datetime import datetime, timedelta
        
        try:
            dealer = Dealer.objects.select_related('user').get(user_id=user_id)
        except Dealer.DoesNotExist:
            return Response({
                'success': False,
                'error': f'Dealer not found for user_id: {user_id}'
            }, status=status.HTTP_404_NOT_FOUND)
        
        # Check if dealer has card_code
        if not dealer.card_code:
            return Response({
                'success': False,
                'error': f'Dealer (user_id: {user_id}) does not have a card_code assigned'
            }, status=status.HTTP_404_NOT_FOUND)
        
        # Count all complaints by this user
        complaints_count = Complaint.objects.filter(user_id=user_id).count()
        
        # Get total Kindwise records for this user
        kindwise_count = KindwiseIdentification.objects.filter(user_id=user_id).count()
        
        # Get total policies from SAP HANA
        database = get_hana_schema_from_request(request)
        
        total_policies = 0
        total_balance = 0.0
        policies_error = None
        
        try:
            # Load environment variables
            try:
                _hana_load_env_file(os.path.join(os.path.dirname(__file__), '.env'))
                _hana_load_env_file(os.path.join(str(settings.BASE_DIR), '.env'))
                _hana_load_env_file(os.path.join(str(Path(settings.BASE_DIR).parent), '.env'))
                _hana_load_env_file(os.path.join(os.getcwd(), '.env'))
            except Exception:
                pass
            
            # Get SAP HANA connection configuration
            cfg = {
                'host': os.environ.get('HANA_HOST', ''),
                'port': os.environ.get('HANA_PORT', '30015'),
                'user': os.environ.get('HANA_USER', ''),
                'encrypt': os.environ.get('HANA_ENCRYPT', ''),
                'ssl_validate': os.environ.get('HANA_SSL_VALIDATE', ''),
                'schema': database
            }
            
            pwd = os.environ.get('HANA_PASSWORD', '')
            
            if all([cfg['host'], cfg['port'], cfg['user'], pwd]):
                from hdbcli import dbapi
                
                kwargs = {
                    'address': cfg['host'],
                    'port': int(cfg['port']),
                    'user': cfg['user'],
                    'password': pwd
                }
                
                if str(cfg['encrypt']).strip().lower() in ('true', '1', 'yes'):
                    kwargs['encrypt'] = True
                    if cfg['ssl_validate']:
                        kwargs['sslValidateCertificate'] = (str(cfg['ssl_validate']).strip().lower() in ('true', '1', 'yes'))
                
                try:
                    conn = dbapi.connect(**kwargs)
                    try:
                        # Set schema
                        cur = conn.cursor()
                        if cfg['schema']:
                            from sap_integration.hana_connect import quote_ident
                            schema_name = cfg['schema']
                            set_schema_sql = f'SET SCHEMA {quote_ident(schema_name)}'
                            cur.execute(set_schema_sql)
                        
                        # Get policy count and balance sum using policy_customer_balance
                        from .hana_connect import policy_customer_balance
                        policies_data = policy_customer_balance(conn, dealer.card_code)
                        
                        if policies_data:
                            total_policies = len(policies_data)
                            total_balance = sum(float(row.get('Balance', 0) or 0) for row in policies_data)
                        
                        cur.close()
                    finally:
                        conn.close()
                        
                except Exception as e:
                    policies_error = str(e)
            else:
                policies_error = "SAP HANA configuration is incomplete"
                
        except Exception as e:
            policies_error = str(e)
        
        # Build response
        response_data = {
            'success': True,
            'user_id': user_id,
            'card_code': dealer.card_code,
            'dealer_name': dealer.name,
            'business_name': dealer.business_name or '',
            'analytics': {
                'total_complaints': complaints_count,
                'total_policies': total_policies,
                'total_kindwise_records': kindwise_count,
                'total_balance': total_balance,
            }
        }
        
        # Add error info if policies fetch failed
        if policies_error:
            response_data['analytics']['policies_error'] = policies_error
        
        return Response(response_data, status=status.HTTP_200_OK)
        
    except Exception as e:
        return Response({
            'success': False,
            'error': f'An error occurred: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)



@swagger_auto_schema(tags=['SAP - Diagnostics'],
    method='get',
    operation_summary="Test SAP HANA Connection & Table Availability",
    operation_description="""
    🔍 **SAP HANA DIAGNOSTIC ENDPOINT** - Test server connectivity and validate database
    
    This endpoint helps diagnose issues when queries fail with:
    - "Table/View not found: B4_SALES_TARGET"
    - "Table/View not found: B4_COLLECTION_TARGET"
    - Other SAP HANA table/view not found errors
    
    **What This Endpoint Tests:**
    1. ✅ Basic SAP HANA connectivity (can we reach the server?)
    2. ✅ Authentication (are credentials valid?)
    3. ✅ Schema accessibility (can we access the selected schema?)
    4. ✅ Available tables (what tables exist in this schema?)
    5. ✅ Critical tables (do B4_SALES_TARGET, B4_COLLECTION_TARGET exist?)
    6. ✅ Configuration validation (are env vars correct?)
    
    **Usage Example:**
    - Test current schema: `GET /api/sap/hana-connection-test/`
    - Test specific schema: `GET /api/sap/hana-connection-test/?database=4B-AGRI_LIVE`
    - Test with verbose output: `GET /api/sap/hana-connection-test/?verbose=true`
    
    **Troubleshooting Guidance:**
    If tables are reported as missing that you know exist:
    1. Verify you're connected to the correct SAP HANA instance
    2. Check HANA_HOST and HANA_PORT in environment settings
    3. Verify the schema name: is it "4B-AGRI_LIVE" or "4B_AGRI_LIVE"?
    4. Check if server's SAP HANA has the tables (local vs production issue)
    5. Contact IT/DevOps to confirm table existence on that server
    """,
    manual_parameters=[
        openapi.Parameter(
            'database',
            openapi.IN_QUERY,
            description="Schema to test (e.g., 4B-AGRI_LIVE, 4B-BIO_APP, 4B-ORANG_APP). If not provided, uses first active company schema.",
            type=openapi.TYPE_STRING,
            required=False
        ),
        openapi.Parameter(
            'verbose',
            openapi.IN_QUERY,
            description="Include additional debug information (true/false). Default: false",
            type=openapi.TYPE_BOOLEAN,
            required=False,
            default=False
        )
    ],
    responses={
        200: openapi.Response(
            description="Connection test completed with diagnostic results",
            examples={
                "application/json": {
                    "success": True,
                    "hostname": "sap-hana-prod.company.com",
                    "schema": "4B-AGRI_LIVE",
                    "connection": {
                        "status": "connected",
                        "message": "Successfully connected to SAP HANA"
                    },
                    "database_info": {
                        "current_time": "2026-01-15T10:30:45.123456",
                        "database_version": "4.00.000.00",
                        "database_name": "HXE"
                    },
                    "schema_details": {
                        "status": "accessible",
                        "total_tables": 85,
                        "total_views": 12
                    },
                    "critical_tables": {
                        "B4_SALES_TARGET": {"exists": True, "type": "TABLE"},
                        "B4_COLLECTION_TARGET": {"exists": True, "type": "VIEW"},
                        "OTER": {"exists": True, "type": "TABLE"},
                        "OITM": {"exists": True, "type": "TABLE"}
                    },
                    "available_tables": [
                        "B4_SALES_TARGET",
                        "B4_COLLECTION_TARGET",
                        "OTER",
                        "OITM",
                        # ... more tables
                    ],
                    "missing_critical_tables": [],
                    "troubleshooting": {
                        "all_critical_tables_present": True,
                        "explanation": "All expected tables are available in this schema"
                    }
                }
            }
        ),
        500: openapi.Response(
            description="Connection failed with error details",
            examples={
                "application/json": {
                    "success": False,
                    "error": "Connection failed",
                    "message": "Cannot connect to SAP HANA server at sap-hana-prod:30015",
                    "details": "Connection timeout after 60 seconds",
                    "hostname": "sap-hana-prod.company.com",
                    "port": "30015",
                    "troubleshooting": [
                        "Verify SAP HANA is running on sap-hana-prod:30015",
                        "Check HANA_HOST and HANA_PORT environment variables",
                        "Test network connectivity: ping sap-hana-prod",
                        "Check VPN/firewall settings",
                        "Contact SAP administrator"
                    ]
                }
            }
        )
    }
)
@api_view(['GET'])
def hana_connection_test_api(request):
    """
    API endpoint to diagnose SAP HANA connectivity and table availability.
    
    Tests connection, authentication, schema access, and lists available tables
    to help troubleshoot "Table/View not found" errors.
    """
    import logging
    
    logger = logging.getLogger(__name__)
    verbose = (request.GET.get('verbose', '').lower() in ('true', '1', 'yes', 'y'))
    
    try:
        # Load environment files
        try:
            _hana_load_env_file(os.path.join(os.path.dirname(__file__), '.env'))
            _hana_load_env_file(os.path.join(str(settings.BASE_DIR), '.env'))
            _hana_load_env_file(os.path.join(str(Path(settings.BASE_DIR).parent), '.env'))
            _hana_load_env_file(os.path.join(os.getcwd(), '.env'))
        except Exception:
            pass
        
        # Get database/schema parameter
        db_param = (request.GET.get('database', '') or '').strip()
        
        # Try to get HANA schema from request (handles various parameter forms)
        if db_param:
            # Direct use of provided parameter
            hana_schema = db_param
        else:
            # Fallback to get_hana_schema_from_request which handles Company model resolution
            hana_schema = get_hana_schema_from_request(request)
        
        # Get HANA configuration from environment
        cfg = {
            'host': os.environ.get('HANA_HOST', '').strip(),
            'port': os.environ.get('HANA_PORT', '30015').strip(),
            'user': os.environ.get('HANA_USER', '').strip(),
            'password': os.environ.get('HANA_PASSWORD', '').strip(),
            'schema': hana_schema.strip() if hana_schema else '',
            'encrypt': os.environ.get('HANA_ENCRYPT', '').strip(),
            'ssl_validate': os.environ.get('HANA_SSL_VALIDATE', '').strip(),
        }
        
        # Validate configuration
        config_valid = all([cfg['host'], cfg['port'], cfg['user']])
        
        response_data = {
            "hostname": cfg['host'],
            "port": cfg['port'],
            "schema": cfg['schema'] or 'Not specified',
            "configuration": {
                "has_host": bool(cfg['host']),
                "has_port": bool(cfg['port']),
                "has_user": bool(cfg['user']),
                "has_password": bool(cfg['password']),
                "has_schema": bool(cfg['schema']),
                "all_required_settings": config_valid
            }
        }
        
        if not config_valid:
            missing = []
            if not cfg['host']:
                missing.append("HANA_HOST")
            if not cfg['port']:
                missing.append("HANA_PORT") 
            if not cfg['user']:
                missing.append("HANA_USER")
            if not cfg['password']:
                missing.append("HANA_PASSWORD")
                
            return Response({
                "success": False,
                "error": "SAP HANA configuration is incomplete",
                "message": f"Missing required environment variables: {', '.join(missing)}",
                **response_data,
                "troubleshooting": [
                    "Set HANA_HOST environment variable (e.g., sap-hana-prod.company.com)",
                    "Set HANA_PORT environment variable (default: 30015)",
                    "Set HANA_USER environment variable (SAP HANA username)",
                    "Set HANA_PASSWORD environment variable (SAP HANA password)",
                    "Verify .env files in project root, parent directory, or /web_portal/",
                    "Restart application after updating environment variables"
                ]
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        # Try to establish connection
        try:
            from hdbcli import dbapi
            
            kwargs = {
                'address': cfg['host'],
                'port': int(cfg['port']),
                'user': cfg['user'],
                'password': cfg['password']
            }
            
            # Handle encryption settings. Explicitly pass certificate validation flag
            # because hdbcli may default to validation when encrypt=True.
            if str(cfg['encrypt']).lower() in ('true', '1', 'yes'):
                kwargs['encrypt'] = True
                kwargs['sslValidateCertificate'] = (str(cfg['ssl_validate']).lower() in ('true', '1', 'yes'))
            
            # Attempt connection
            conn = dbapi.connect(**kwargs)
            
            try:
                # Connection successful
                response_data["connection"] = {
                    "status": "connected",
                    "message": "Successfully connected to SAP HANA"
                }
                
                # Get database information with HANA-safe SQL.
                cur_info = conn.cursor()
                current_time = "Unknown"
                database_name = "Unknown"
                database_version = "Unknown"

                # 1) Always-safe timestamp query.
                cur_info.execute('SELECT CURRENT_UTCTIMESTAMP FROM DUMMY')
                ts_row = cur_info.fetchone()
                if ts_row and len(ts_row) > 0:
                    current_time = str(ts_row[0]) if ts_row[0] else "Unknown"

                # 2) Database metadata query with fallbacks for different HANA versions.
                try:
                    cur_info.execute(
                        'SELECT DATABASE_NAME AS "DB_NAME", DATABASE_VERSION AS "DB_VERSION" '
                        'FROM SYS.M_DATABASES LIMIT 1'
                    )
                    meta_row = cur_info.fetchone()
                    if meta_row:
                        database_name = str(meta_row[0]) if meta_row[0] else "Unknown"
                        database_version = str(meta_row[1]) if len(meta_row) > 1 and meta_row[1] else "Unknown"
                except Exception:
                    # Older/different revisions may expose VERSION instead of DATABASE_VERSION.
                    try:
                        cur_info.execute(
                            'SELECT DATABASE_NAME AS "DB_NAME", VERSION AS "DB_VERSION" '
                            'FROM SYS.M_DATABASES LIMIT 1'
                        )
                        meta_row = cur_info.fetchone()
                        if meta_row:
                            database_name = str(meta_row[0]) if meta_row[0] else "Unknown"
                            database_version = str(meta_row[1]) if len(meta_row) > 1 and meta_row[1] else "Unknown"
                    except Exception:
                        # Last fallback: at least try database name, keep version unknown.
                        try:
                            cur_info.execute('SELECT DATABASE_NAME FROM SYS.M_DATABASES LIMIT 1')
                            meta_row = cur_info.fetchone()
                            if meta_row and len(meta_row) > 0:
                                database_name = str(meta_row[0]) if meta_row[0] else "Unknown"
                        except Exception:
                            pass

                response_data["database_info"] = {
                    "current_time": current_time,
                    "database_name": database_name,
                    "database_version": database_version,
                }
                
                # If schema provided, set it and test access
                if cfg['schema']:
                    try:
                        cur_schema = conn.cursor()
                        set_schema_sql = f'SET SCHEMA "{cfg["schema"]}"'
                        cur_schema.execute(set_schema_sql)
                        cur_schema.close()
                        
                        response_data["schema_details"] = {
                            "status": "accessible",
                            "name": cfg['schema']
                        }
                        
                        # Get schema statistics: table and view counts
                        cur_stats = conn.cursor()
                        
                        # Count tables in schema
                        cur_stats.execute(f"""
                            SELECT COUNT(*) FROM SYS.TABLES 
                            WHERE SCHEMA_NAME = '{cfg["schema"]}'
                        """)
                        table_count = cur_stats.fetchone()
                        table_count = table_count[0] if table_count else 0
                        
                        # Count views in schema
                        cur_stats.execute(f"""
                            SELECT COUNT(*) FROM SYS.VIEWS 
                            WHERE SCHEMA_NAME = '{cfg["schema"]}'
                        """)
                        view_count = cur_stats.fetchone()
                        view_count = view_count[0] if view_count else 0
                        
                        response_data["schema_details"]["total_tables"] = int(table_count)
                        response_data["schema_details"]["total_views"] = int(view_count)
                        
                        # List all tables and views
                        cur_tables = conn.cursor()
                        cur_tables.execute(f"""
                            SELECT TABLE_NAME, 'TABLE' as TYPE FROM SYS.TABLES 
                            WHERE SCHEMA_NAME = '{cfg["schema"]}'
                            UNION ALL
                            SELECT VIEW_NAME as TABLE_NAME, 'VIEW' as TYPE FROM SYS.VIEWS
                            WHERE SCHEMA_NAME = '{cfg["schema"]}'
                            ORDER BY TABLE_NAME
                        """)
                        
                        all_items = cur_tables.fetchall()
                        available_names = []
                        items_info = {}
                        
                        for item in all_items:
                            name = item[0] if item[0] else ''
                            item_type = item[1] if len(item) > 1 else 'UNKNOWN'
                            if name:
                                available_names.append(name)
                                items_info[name] = {"type": item_type}
                        
                        response_data["available_tables"] = available_names
                        
                        # Check for critical tables that user is looking for
                        critical_tables = ['B4_SALES_TARGET', 'B4_COLLECTION_TARGET', 'OTER', 'OITM']
                        critical_status = {}
                        missing_critical = []
                        
                        for critical_name in critical_tables:
                            if critical_name in items_info:
                                critical_status[critical_name] = {
                                    "exists": True,
                                    "type": items_info[critical_name].get("type", "TABLE")
                                }
                            else:
                                critical_status[critical_name] = {
                                    "exists": False,
                                    "type": "MISSING"
                                }
                                missing_critical.append(critical_name)
                        
                        response_data["critical_tables"] = critical_status
                        response_data["missing_critical_tables"] = missing_critical
                        
                        # Troubleshooting summary
                        all_critical_present = len(missing_critical) == 0
                        response_data["troubleshooting"] = {
                            "all_critical_tables_present": all_critical_present,
                            "explanation": "All expected tables are available in this schema" if all_critical_present else f"Missing tables: {', '.join(missing_critical)}"
                        }
                        
                        if verbose and missing_critical:
                            response_data["troubleshooting"]["guidance"] = [
                                f"The following critical tables are NOT found in schema '{cfg['schema']}':",
                                f"  - {', '.join(missing_critical)}",
                                "",
                                "Possible causes:",
                                "1. Tables exist in local SAP HANA but not on production server - Check with IT/DevOps",
                                "2. Tables are in a different schema - Verify the correct schema name",
                                "3. Tables were not installed - Contact SAP support for deployment",
                                "4. Connected to wrong SAP HANA instance - Check HANA_HOST environment variable",
                                "",
                                f"Available tables in schema '{cfg['schema']}': {len(available_names)} total",
                                "Run with ?verbose=true to see full list"
                            ]
                        
                        cur_stats.close()
                        cur_tables.close()
                        
                    except Exception as e_schema:
                        response_data["schema_details"] = {
                            "status": "error",
                            "error": str(e_schema),
                            "message": f"Cannot access schema '{cfg['schema']}'"
                        }
                        return Response({
                            "success": False,
                            "error": "Schema access failed",
                            "message": f"Unable to access schema '{cfg['schema']}': {str(e_schema)}",
                            **response_data,
                            "troubleshooting": [
                                f"Verify schema name is correct: '{cfg['schema']}'",
                                "Check if user has permissions to access this schema",
                                "Verify schema exists on this SAP HANA instance",
                                "Try with a different database parameter, e.g., ?database=4B-BIO_APP"
                            ]
                        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
                
                cur_info.close()
                
                return Response({
                    "success": True,
                    **response_data
                }, status=status.HTTP_200_OK)
                
            finally:
                try:
                    conn.close()
                except Exception:
                    pass
                    
        except Exception as e_conn:
            error_msg = str(e_conn)
            
            # Determine error type
            if "timeout" in error_msg.lower() or "10060" in error_msg:
                error_type = "Connection Timeout"
                troubleshooting = [
                    f"SAP HANA server at {cfg['host']}:{cfg['port']} is not responding",
                    "Possible causes:",
                    "  1. SAP HANA service is not running",
                    "  2. Network/firewall is blocking connection",
                    "  3. VPN connection is not active",
                    "  4. Wrong host or port specified in HANA_HOST/HANA_PORT",
                    "",
                    "Actions to take:",
                    f"  1. Verify SAP HANA is running: try ping {cfg['host']}",
                    f"  2. Verify host/port: {cfg['host']}:{cfg['port']}",
                    "  3. Check VPN/network connectivity",
                    "  4. Contact IT/DevOps for SAP HANA status"
                ]
            elif "authentication" in error_msg.lower() or "invalid password" in error_msg.lower():
                error_type = "Authentication Failed"
                troubleshooting = [
                    "SAP HANA rejected the credentials",
                    "Possible causes:",
                    "  1. Incorrect username in HANA_USER",
                    "  2. Incorrect password in HANA_PASSWORD",
                    "  3. User account is locked or expired",
                    "",
                    "Actions to take:",
                    "  1. Verify HANA_USER and HANA_PASSWORD in .env files",
                    "  2. Test credentials directly with SAP HANA client tools",
                    "  3. Contact SAP administrator for password reset",
                    "  4. Ensure user has 'HNDS_USER' system privilege"
                ]
            elif "ssl certificate validation failed" in error_msg.lower() or "not trusted" in error_msg.lower():
                error_type = "SSL Certificate Validation Failed"
                troubleshooting = [
                    "SAP HANA TLS is enabled but certificate trust validation failed",
                    "For internal/self-signed certificates set HANA_SSL_VALIDATE=false",
                    "Keep HANA_ENCRYPT=true if TLS transport is required",
                    "If strict validation is required, install trusted CA chain on server",
                    "Restart Django service after updating environment variables"
                ]
            else:
                error_type = "Connection Error"
                troubleshooting = [
                    f"Failed to connect to SAP HANA: {error_msg}",
                    "Verify HANA_HOST and HANA_PORT configuration",
                    "Check network connectivity and firewall rules",
                    "Ensure SAP HANA service is running",
                    "Contact SAP administrator for assistance"
                ]
            
            return Response({
                "success": False,
                "error": error_type,
                "message": error_msg,
                **response_data,
                "troubleshooting": troubleshooting
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            
    except Exception as e:
        error_msg = str(e)
        return Response({
            "success": False,
            "error": "Unexpected error",
            "message": error_msg,
            "troubleshooting": [
                "An unexpected error occurred during diagnostics",
                "Check application logs for more details",
                "Contact your system administrator"
            ]
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
