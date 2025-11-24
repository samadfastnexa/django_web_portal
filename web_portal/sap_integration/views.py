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
from .hana_connect import _load_env_file as _hana_load_env_file, territory_summary, products_catalog, policy_customer_balance, sales_vs_achievement, territory_names
from django.conf import settings
from pathlib import Path
import sys

@staff_member_required
def hana_connect_admin(request):
    try:
        _hana_load_env_file(os.path.join(os.path.dirname(__file__), '.env'))
        _hana_load_env_file(os.path.join(str(settings.BASE_DIR), '.env'))
        _hana_load_env_file(os.path.join(str(Path(settings.BASE_DIR).parent), '.env'))
        _hana_load_env_file(os.path.join(os.getcwd(), '.env'))
    except Exception:
        pass
    cfg = {
        'dsn': os.environ.get('HANA_DSN') or '',
        'host': os.environ.get('HANA_HOST') or '',
        'port': os.environ.get('HANA_PORT') or '30015',
        'schema': os.environ.get('HANA_SCHEMA') or '',
        'database': os.environ.get('HANA_DATABASE') or '',
        'encrypt': os.environ.get('HANA_ENCRYPT') or '',
        'ssl_validate': os.environ.get('HANA_SSL_VALIDATE') or '',
        'user': os.environ.get('HANA_USER') or '',
        'driver': os.environ.get('HANA_DRIVER') or 'HDBCLI',
    }
    action = request.GET.get('action') or 'health'
    result = None
    error = None
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
                        sch = cfg['schema'] if re.match(r'^[A-Za-z0-9_]+$', cfg['schema']) else '"' + cfg['schema'].replace('"','""') + '"'
                        cur = conn.cursor()
                        cur.execute('SET SCHEMA ' + sch)
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
                    elif action == 'policy_customer_balance':
                        try:
                            cc = request.GET.get('card_code') or 'BIC00315'
                            data = policy_customer_balance(conn, cc)
                            result = data
                            if isinstance(result, list) and len(result) == 0:
                                error = 'No rows found for the given CardCode'
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
            'is_tabular': (action in ('territory_summary','sales_vs_achievement')),
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
