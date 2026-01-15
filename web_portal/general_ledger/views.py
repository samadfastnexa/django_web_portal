"""
General Ledger API Views and Admin Interface
"""
from rest_framework.response import Response
from rest_framework.decorators import api_view
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from django.contrib.admin.views.decorators import staff_member_required
from django.shortcuts import render
from django.core.paginator import Paginator
from django.http import JsonResponse, HttpResponse
import json
import logging
import csv
import re
from datetime import datetime
from io import BytesIO
try:
    from openpyxl import Workbook
    from openpyxl.styles import Font, Alignment, PatternFill
    OPENPYXL_AVAILABLE = True
except ImportError:
    OPENPYXL_AVAILABLE = False
from io import BytesIO
try:
    from openpyxl import Workbook
    from openpyxl.styles import Font, Alignment, PatternFill
    OPENPYXL_AVAILABLE = True
except ImportError:
    OPENPYXL_AVAILABLE = False

try:
    from reportlab.lib.pagesizes import letter, landscape
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak
    from reportlab.lib import colors
    from reportlab.lib.enums import TA_CENTER, TA_RIGHT, TA_LEFT
    REPORTLAB_AVAILABLE = True
except ImportError:
    REPORTLAB_AVAILABLE = False

from . import hana_queries
from .utils import (
    get_hana_connection,
    get_company_options,
    calculate_running_balance,
    group_by_account,
    calculate_totals
)

logger = logging.getLogger("general_ledger")


# ============================================================================
# REST API Views for Mobile/React App
# ============================================================================

@swagger_auto_schema(
    method='get',
    tags=['General Ledger'],
    operation_summary='Get General Ledger Report',
    operation_description='Fetch general ledger transactions. **NO REQUIRED FIELDS**. All parameters are optional filters for account range, date range, business partner, and project. Use user parameter to filter by user\'s assigned customers.',
    manual_parameters=[
        openapi.Parameter('company', openapi.IN_QUERY, type=openapi.TYPE_STRING, description='Optional: Company database key', default='4B-ORANG_APP', enum=['4B-BIO_APP', '4B-ORANG_APP'], required=False),
        openapi.Parameter('account_from', openapi.IN_QUERY, type=openapi.TYPE_STRING, description='Optional: Start of account range', required=False),
        openapi.Parameter('account_to', openapi.IN_QUERY, type=openapi.TYPE_STRING, description='Optional: End of account range', required=False),
        openapi.Parameter('from_date', openapi.IN_QUERY, type=openapi.TYPE_STRING, description='Optional: Start date (YYYY-MM-DD)', required=False),
        openapi.Parameter('to_date', openapi.IN_QUERY, type=openapi.TYPE_STRING, description='Optional: End date (YYYY-MM-DD)', required=False),
        openapi.Parameter('bp_code', openapi.IN_QUERY, type=openapi.TYPE_STRING, description='Optional: Business Partner CardCode. If user parameter is provided, validates that bp_code belongs to that user.', required=False),
        openapi.Parameter('user', openapi.IN_QUERY, type=openapi.TYPE_STRING, description='Optional: User ID or username. Filters transactions to only user\'s assigned customers. Can be combined with bp_code for validation.', required=False),
        openapi.Parameter('project_code', openapi.IN_QUERY, type=openapi.TYPE_STRING, description='Optional: Project Code', required=False),
        openapi.Parameter('trans_type', openapi.IN_QUERY, type=openapi.TYPE_STRING, description='Optional: Transaction Type (e.g., 13, 30)', required=False),
        openapi.Parameter('page', openapi.IN_QUERY, type=openapi.TYPE_INTEGER, description='Optional: Page number', default=1, required=False),
        openapi.Parameter('page_size', openapi.IN_QUERY, type=openapi.TYPE_INTEGER, description='Optional: Records per page', default=50, required=False),
        openapi.Parameter('group_by_account', openapi.IN_QUERY, type=openapi.TYPE_BOOLEAN, description='Optional: Group results by account with opening/closing balances', default=False, required=False),
    ],
    responses={
        200: openapi.Response(
            description='Success',
            examples={
                'application/json': {
                    'success': True,
                    'data': {
                        'accounts': [
                            {
                                'Account': '11010100',
                                'AccountName': 'Cash in Hand',
                                'OpeningBalance': 1000.00,
                                'transactions': [],
                                'TotalDebit': 5000.00,
                                'TotalCredit': 3000.00,
                                'ClosingBalance': 3000.00
                            }
                        ],
                        'grand_total': {
                            'TotalDebit': 50000.00,
                            'TotalCredit': 50000.00,
                            'Difference': 0.00
                        }
                    },
                    'pagination': {
                        'page': 1,
                        'page_size': 50,
                        'total_records': 234,
                        'total_pages': 5
                    }
                }
            }
        ),
        500: 'Error fetching ledger data'
    }
)
@api_view(['GET'])
def general_ledger_api(request):
    """
    GET /api/general-ledger/
    
    Fetch general ledger transactions with optional filters.
    Supports grouping by account with opening/closing balances.
    Supports user-based filtering to show only user's assigned customers.
    """
    try:
        # Extract query parameters
        company = request.GET.get('company', '4B-ORANG_APP')
        account_from = request.GET.get('account_from', '').strip()
        account_to = request.GET.get('account_to', '').strip()
        from_date = request.GET.get('from_date', '').strip()
        to_date = request.GET.get('to_date', '').strip()
        bp_code = request.GET.get('bp_code', '').strip()
        user_param = request.GET.get('user', '').strip()
        project_code = request.GET.get('project_code', '').strip()
        trans_type = request.GET.get('trans_type', '').strip()
        page = int(request.GET.get('page', 1))
        page_size = int(request.GET.get('page_size', 50))
        group_by_account_flag = request.GET.get('group_by_account', 'false').lower() == 'true'
        
        # Handle user-based filtering
        if user_param:
            try:
                from accounts.models import User
                from FieldAdvisoryService.models import Dealer
                
                # Get user object
                user_obj = None
                try:
                    user_id = int(user_param)
                    user_obj = User.objects.get(id=user_id)
                except (ValueError, User.DoesNotExist):
                    user_obj = User.objects.filter(username=user_param).first()
                
                if not user_obj:
                    return Response({'success': False, 'error': f'User "{user_param}" not found'}, status=404)
                
                # Get dealer card codes for this user
                dealers = Dealer.objects.filter(user=user_obj).values_list('card_code', flat=True).exclude(card_code__isnull=True).exclude(card_code='')
                dealer_card_codes = list(dealers)
                
                if not dealer_card_codes:
                    return Response({'success': True, 'data': {'transactions': [], 'grand_total': {'TotalDebit': 0, 'TotalCredit': 0, 'Balance': 0}}, 'pagination': {'page': page, 'page_size': page_size, 'total_records': 0, 'total_pages': 0}})
                
                # If bp_code is provided, validate it belongs to user
                if bp_code:
                    if bp_code not in dealer_card_codes:
                        return Response({'success': False, 'error': f'Business Partner "{bp_code}" does not belong to user "{user_param}"'}, status=403)
                    # Use only the specified bp_code
                    bp_code = bp_code
                else:
                    # Use all dealer card codes as a list
                    bp_code = dealer_card_codes
                    
            except Exception as e:
                return Response({'success': False, 'error': f'Error processing user filter: {str(e)}'}, status=500)
        
        # Connect to HANA
        conn = get_hana_connection(company)
        
        # Get total count for pagination
        total_count = hana_queries.general_ledger_count(
            conn,
            account_from=account_from or None,
            account_to=account_to or None,
            from_date=from_date or None,
            to_date=to_date or None,
            bp_code=bp_code or None,
            project_code=project_code or None,
            trans_type=trans_type or None
        )
        
        # Calculate offset
        offset = (page - 1) * page_size
        
        # Fetch transactions
        transactions = hana_queries.general_ledger_report(
            conn,
            account_from=account_from or None,
            account_to=account_to or None,
            from_date=from_date or None,
            to_date=to_date or None,
            bp_code=bp_code or None,
            project_code=project_code or None,
            trans_type=trans_type or None,
            limit=page_size,
            offset=offset
        )
        
        conn.close()
        
        # Prepare response
        if group_by_account_flag:
            # Group by account and calculate opening/closing balances
            grouped = group_by_account(transactions)
            accounts_list = []
            grand_total = {'TotalDebit': 0, 'TotalCredit': 0}
            
            for account_code, account_data in grouped.items():
                # Calculate opening balance if date range provided
                opening_balance = 0
                if from_date:
                    conn = get_hana_connection(company)
                    opening = hana_queries.account_opening_balance(
                        conn,
                        account_code,
                        from_date,
                        bp_code=bp_code or None
                    )
                    conn.close()
                    opening_balance = float(opening.get('Balance', 0))
                
                # Calculate running balance
                account_data['transactions'] = calculate_running_balance(
                    account_data['transactions']
                )
                
                # Calculate totals
                totals = calculate_totals(account_data['transactions'])
                
                accounts_list.append({
                    'Account': account_data['Account'],
                    'AccountName': account_data['AccountName'],
                    'OpeningBalance': opening_balance,
                    'transactions': account_data['transactions'],
                    'TotalDebit': totals['TotalDebit'],
                    'TotalCredit': totals['TotalCredit'],
                    'ClosingBalance': opening_balance + totals['Balance']
                })
                
                grand_total['TotalDebit'] += totals['TotalDebit']
                grand_total['TotalCredit'] += totals['TotalCredit']
            
            grand_total['Difference'] = grand_total['TotalDebit'] - grand_total['TotalCredit']
            
            response_data = {
                'accounts': accounts_list,
                'grand_total': grand_total
            }
        else:
            # Return flat list with running balance
            transactions = calculate_running_balance(transactions)
            grand_total = calculate_totals(transactions)
            
            response_data = {
                'transactions': transactions,
                'grand_total': grand_total
            }
        
        return Response({
            'success': True,
            'data': response_data,
            'pagination': {
                'page': page,
                'page_size': page_size,
                'total_records': total_count,
                'total_pages': (total_count + page_size - 1) // page_size
            }
        }, status=200)
        
    except Exception as e:
        logger.exception("Error in general_ledger_api")
        return Response({
            'success': False,
            'error': str(e)
        }, status=500)


@swagger_auto_schema(
    method='get',
    tags=['General Ledger'],
    operation_summary='Get Chart of Accounts',
    operation_description='Fetch chart of accounts for dropdown/filter',
    manual_parameters=[
        openapi.Parameter('company', openapi.IN_QUERY, type=openapi.TYPE_STRING, description='Optional: Company database key', default='4B-ORANG_APP', enum=['4B-BIO_APP', '4B-ORANG_APP']),
        openapi.Parameter('account_type', openapi.IN_QUERY, type=openapi.TYPE_STRING, description='Account type filter (A=Assets, L=Liabilities, E=Equity, I=Income, O=Expense)'),
    ],
    responses={
        200: 'Success',
        500: 'Error fetching chart of accounts'
    }
)
@api_view(['GET'])
def chart_of_accounts_api(request):
    """
    GET /api/chart-of-accounts/
    
    Fetch chart of accounts for dropdowns and filters.
    """
    try:
        company = request.GET.get('company', '4B-ORANG_APP')
        account_type = request.GET.get('account_type', '').strip()
        
        conn = get_hana_connection(company)
        accounts = hana_queries.chart_of_accounts_list(
            conn,
            account_type=account_type or None
        )
        conn.close()
        
        return Response({
            'success': True,
            'data': accounts
        }, status=200)
        
    except Exception as e:
        logger.exception("Error in chart_of_accounts_api")
        return Response({
            'success': False,
            'error': str(e)
        }, status=500)


@swagger_auto_schema(
    method='get',
    tags=['General Ledger'],
    operation_summary='Get Transaction Types',
    operation_description='Get list of SAP B1 transaction types for filter dropdown',
    responses={200: 'Success', 500: 'Error'}
)
@api_view(['GET'])
def transaction_types_api(request):
    """
    GET /api/transaction-types/
    
    Get list of transaction types for dropdown filter.
    """
    try:
        conn = get_hana_connection()
        trans_types = hana_queries.transaction_types_lov(conn)
        conn.close()
        
        return Response({
            'success': True,
            'data': trans_types
        }, status=200)
        
    except Exception as e:
        logger.exception("Error in transaction_types_api")
        return Response({
            'success': False,
            'error': str(e)
        }, status=500)


@swagger_auto_schema(
    method='get',
    tags=['General Ledger'],
    operation_summary='Get Business Partners LOV',
    operation_description='Get business partners for dropdown filter',
    manual_parameters=[
        openapi.Parameter('company', openapi.IN_QUERY, type=openapi.TYPE_STRING, description='Optional: Company database key', default='4B-ORANG_APP', enum=['4B-BIO_APP', '4B-ORANG_APP']),
        openapi.Parameter('bp_type', openapi.IN_QUERY, type=openapi.TYPE_STRING, description='BP type (C=Customer, S=Supplier)'),
    ],
    responses={200: 'Success', 500: 'Error'}
)
@api_view(['GET'])
def business_partners_api(request):
    """
    GET /api/business-partners/
    
    Get business partners for dropdown filter.
    """
    try:
        company = request.GET.get('company', '4B-ORANG_APP')
        bp_type = request.GET.get('bp_type', '').strip()
        
        conn = get_hana_connection(company)
        partners = hana_queries.business_partner_lov(
            conn,
            bp_type=bp_type or None
        )
        conn.close()
        
        return Response({
            'success': True,
            'data': partners
        }, status=200)
        
    except Exception as e:
        logger.exception("Error in business_partners_api")
        return Response({
            'success': False,
            'error': str(e)
        }, status=500)


@swagger_auto_schema(
    method='get',
    tags=['General Ledger'],
    operation_summary='Get Projects LOV',
    operation_description='Get projects for dropdown filter',
    manual_parameters=[
        openapi.Parameter('company', openapi.IN_QUERY, type=openapi.TYPE_STRING, description='Optional: Company database key', default='4B-ORANG_APP', enum=['4B-BIO_APP', '4B-ORANG_APP']),
    ],
    responses={200: 'Success', 500: 'Error'}
)
@api_view(['GET'])
def projects_api(request):
    """
    GET /api/projects/
    
    Get projects for dropdown filter.
    """
    try:
        company = request.GET.get('company', '4B-ORANG_APP')
        
        conn = get_hana_connection(company)
        projects = hana_queries.projects_lov(conn)
        conn.close()
        
        return Response({
            'success': True,
            'data': projects
        }, status=200)
        
    except Exception as e:
        logger.exception("Error in projects_api")
        return Response({
            'success': False,
            'error': str(e)
        }, status=500)


@swagger_auto_schema(
    method='get',
    tags=['General Ledger'],
    operation_summary='Export General Ledger to Excel',
    operation_description='Download general ledger report as Excel file with filters applied. Returns formatted XLSX file with headers and styling. Use user parameter to filter by user\'s assigned customers.',
    manual_parameters=[
        openapi.Parameter('company', openapi.IN_QUERY, type=openapi.TYPE_STRING, description='Optional: Company database key', default='4B-ORANG_APP', enum=['4B-BIO_APP', '4B-ORANG_APP']),
        openapi.Parameter('account_from', openapi.IN_QUERY, type=openapi.TYPE_STRING, description='Start of account range'),
        openapi.Parameter('account_to', openapi.IN_QUERY, type=openapi.TYPE_STRING, description='End of account range'),
        openapi.Parameter('from_date', openapi.IN_QUERY, type=openapi.TYPE_STRING, description='Start date (YYYY-MM-DD)'),
        openapi.Parameter('to_date', openapi.IN_QUERY, type=openapi.TYPE_STRING, description='End date (YYYY-MM-DD)'),
        openapi.Parameter('bp_code', openapi.IN_QUERY, type=openapi.TYPE_STRING, description='Business Partner CardCode. If user parameter is provided, validates that bp_code belongs to that user.'),
        openapi.Parameter('user', openapi.IN_QUERY, type=openapi.TYPE_STRING, description='Optional: User ID or username. Filters transactions to only user\'s assigned customers. Can be combined with bp_code for validation.'),
        openapi.Parameter('project_code', openapi.IN_QUERY, type=openapi.TYPE_STRING, description='Project Code'),
        openapi.Parameter('trans_type', openapi.IN_QUERY, type=openapi.TYPE_STRING, description='Transaction Type (e.g., 13, 30)'),
    ],
    responses={
        200: openapi.Response(
            description='Excel file download',
            schema=openapi.Schema(type=openapi.TYPE_FILE)
        ),
        500: 'Error generating Excel file'
    }
)
@api_view(['GET'])
def export_ledger_excel_api(request):
    """
    GET /api/general-ledger/export-excel/
    
    Export general ledger to Excel format for mobile app.
    Returns a downloadable XLSX file with formatted headers and data.
    """
    if not OPENPYXL_AVAILABLE:
        return Response({
            'success': False,
            'error': 'Excel export not available. Please install openpyxl package.'
        }, status=500)
    
    def sanitize_for_excel(value):
        """Remove control characters that Excel can't handle."""
        if value is None:
            return ''
        if isinstance(value, (int, float)):
            return value
        # Convert to string and remove control characters (ASCII 0-31 except tab, newline, carriage return)
        text = str(value)
        # Remove control characters except \t (9), \n (10), \r (13)
        text = re.sub(r'[\x00-\x08\x0B-\x0C\x0E-\x1F\x7F-\x9F]', '', text)
        return text
    
    try:
        # Get filter parameters
        company = request.GET.get('company', '4B-ORANG_APP')
        account_from = (request.GET.get('account_from') or '').strip()
        account_to = (request.GET.get('account_to') or '').strip()
        from_date = (request.GET.get('from_date') or '').strip()
        to_date = (request.GET.get('to_date') or '').strip()
        bp_code = (request.GET.get('bp_code') or '').strip()
        user_param = request.GET.get('user', '').strip()
        project_code = (request.GET.get('project_code') or '').strip()
        trans_type = (request.GET.get('trans_type') or '').strip()
        
        # Handle user-based filtering
        if user_param:
            try:
                from accounts.models import User
                from FieldAdvisoryService.models import Dealer
                
                # Get user object
                user_obj = None
                try:
                    user_id = int(user_param)
                    user_obj = User.objects.get(id=user_id)
                except (ValueError, User.DoesNotExist):
                    user_obj = User.objects.filter(username=user_param).first()
                
                if not user_obj:
                    return Response({'success': False, 'error': f'User "{user_param}" not found'}, status=404)
                
                # Get dealer card codes for this user
                dealers = Dealer.objects.filter(user=user_obj).values_list('card_code', flat=True).exclude(card_code__isnull=True).exclude(card_code='')
                dealer_card_codes = list(dealers)
                
                if not dealer_card_codes:
                    # Return empty list for bp_code - will result in empty export file
                    bp_code = []
                elif bp_code:
                    # If bp_code is provided, validate it belongs to user
                    if bp_code not in dealer_card_codes:
                        return Response({'success': False, 'error': f'Business Partner "{bp_code}" does not belong to user "{user_param}"'}, status=403)
                    # Use only the specified bp_code
                    bp_code = bp_code
                else:
                    # Use all dealer card codes as a list
                    bp_code = dealer_card_codes
                    
            except Exception as e:
                return Response({'success': False, 'error': f'Error processing user filter: {str(e)}'}, status=500)
        
        # Fetch all data
        conn = get_hana_connection(company)
        transactions = hana_queries.general_ledger_report(
            conn,
            account_from=account_from or None,
            account_to=account_to or None,
            from_date=from_date or None,
            to_date=to_date or None,
            bp_code=bp_code if bp_code else None,
            project_code=project_code or None,
            trans_type=trans_type or None
        )
        conn.close()
        
        # Create Excel workbook
        wb = Workbook()
        ws = wb.active
        ws.title = "General Ledger"
        
        # Define header style
        header_font = Font(bold=True, color="FFFFFF")
        header_fill = PatternFill(start_color="4472C4", end_color="4472C4", fill_type="solid")
        header_alignment = Alignment(horizontal="center", vertical="center")
        
        # Write headers
        headers = [
            'VNo.', 'VDate', 'Product Name', 'Qty', 'Price', 'Policy', 
            'Discount', 'Sale Value', 'Type', 'Debit', 'Credit', 'Balance'
        ]
        for col_num, header in enumerate(headers, 1):
            cell = ws.cell(row=1, column=col_num, value=header)
            cell.font = header_font
            cell.fill = header_fill
            cell.alignment = header_alignment
        
        # Write data rows with sanitization
        running_balance = 0
        for row_num, txn in enumerate(transactions, 2):
            debit = float(txn.get('Debit', 0))
            credit = float(txn.get('Credit', 0))
            running_balance += (debit - credit)
            
            # Format date
            posting_date = txn.get('PostingDate', '')
            try:
                date_obj = datetime.strptime(str(posting_date)[:10], '%Y-%m-%d')
                posting_date = date_obj.strftime('%-m/%-d/%Y').lstrip('0').replace('/-', '/').replace('/0', '/')
            except:
                posting_date = str(posting_date)[:10]
            
            ws.cell(row=row_num, column=1, value=sanitize_for_excel(txn.get('TransId', '')))  # VNo
            ws.cell(row=row_num, column=2, value=posting_date)  # VDate
            ws.cell(row=row_num, column=3, value=sanitize_for_excel(txn.get('Description', '')))  # Product Name
            ws.cell(row=row_num, column=4, value=txn.get('Qty', 0))  # Qty
            ws.cell(row=row_num, column=5, value=txn.get('UnitPrice', 0))  # Price
            ws.cell(row=row_num, column=6, value=sanitize_for_excel(txn.get('ExtractedProject') or txn.get('ProjectCode', '')))  # Policy/Project
            ws.cell(row=row_num, column=7, value=txn.get('Discount', 0))  # Discount
            ws.cell(row=row_num, column=8, value=txn.get('Amount', 0))  # Sale Value
            ws.cell(row=row_num, column=9, value=sanitize_for_excel(txn.get('TransTypeName') or txn.get('TransType', '')))  # Type Name
            ws.cell(row=row_num, column=10, value=debit if debit > 0 else 0)  # Debit
            ws.cell(row=row_num, column=11, value=credit if credit > 0 else 0)  # Credit
            ws.cell(row=row_num, column=12, value=running_balance)  # Balance
        
        # Auto-adjust column widths
        for col in ws.columns:
            max_length = 0
            col_letter = col[0].column_letter
            for cell in col:
                try:
                    if len(str(cell.value)) > max_length:
                        max_length = len(str(cell.value))
                except:
                    pass
            adjusted_width = min(max_length + 2, 50)
            ws.column_dimensions[col_letter].width = adjusted_width
        
        # Save to BytesIO
        output = BytesIO()
        wb.save(output)
        output.seek(0)
        
        # Create response
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        response = HttpResponse(
            output.read(),
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        response['Content-Disposition'] = f'attachment; filename="general_ledger_{company}_{timestamp}.xlsx"'
        
        return response
        
    except Exception as e:
        logger.exception("Error exporting Excel")
        return Response({
            'success': False,
            'error': str(e)
        }, status=500)


# ============================================================================
# Admin Web Interface Views
# ============================================================================

@staff_member_required
def general_ledger_admin(request):
    """
    Admin web interface for General Ledger Report.
    Displays ledger with company selector, filters, grouping, and export.
    """
    error = None
    warning = None
    result_rows = []
    accounts_grouped = []
    grand_total = None
    
    # Get company database options
    db_options = get_company_options()
    selected_db_key = request.GET.get('company', '4B-BIO')
    
    # Get filter parameters
    account_from = (request.GET.get('account_from') or '').strip()
    account_to = (request.GET.get('account_to') or '').strip()
    from_date = (request.GET.get('from_date') or '').strip()
    to_date = (request.GET.get('to_date') or '').strip()
    bp_code = (request.GET.get('bp_code') or '').strip()
    project_code = (request.GET.get('project_code') or '').strip()
    trans_type = (request.GET.get('trans_type') or '').strip()
    
    # Pagination parameters
    page_num = int(request.GET.get('page', 1))
    page_size = int(request.GET.get('page_size', 50))
    
    # Load dropdown data
    chart_of_accounts = []
    business_partners = []
    projects = []
    trans_types = []
    
    try:
        conn = get_hana_connection(selected_db_key)
        chart_of_accounts = hana_queries.chart_of_accounts_list(conn)
        business_partners = hana_queries.business_partner_lov(conn, limit=500)
        projects = hana_queries.projects_lov(conn)
        trans_types = hana_queries.transaction_types_lov(conn)
        conn.close()
    except Exception as e:
        logger.warning(f"SAP connection unavailable for dropdown data: {str(e)}")
        # Continue with empty dropdowns - user can still use manual input
        warning = "⚠️ SAP server is currently unavailable. Dropdown options are disabled, but you can still enter filter values manually."
    
    # Fetch ledger data if filters applied
    if account_from or account_to or from_date or to_date or bp_code or project_code or trans_type:
        try:
            conn = get_hana_connection(selected_db_key)
            
            # Get all transactions (we'll paginate after grouping)
            result_rows = hana_queries.general_ledger_report(
                conn,
                account_from=account_from or None,
                account_to=account_to or None,
                from_date=from_date or None,
                to_date=to_date or None,
                bp_code=bp_code or None,
                project_code=project_code or None,
                trans_type=trans_type or None
            )
            
            # Group by account
            grouped = group_by_account(result_rows)
            
            # Calculate opening/closing balances for each account
            for account_code, account_data in grouped.items():
                opening_balance = 0
                if from_date:
                    opening = hana_queries.account_opening_balance(
                        conn,
                        account_code,
                        from_date,
                        bp_code=bp_code or None
                    )
                    opening_balance = float(opening.get('Balance', 0))
                
                # Calculate running balance
                account_data['transactions'] = calculate_running_balance(
                    account_data['transactions']
                )
                
                # Calculate totals
                totals = calculate_totals(account_data['transactions'])
                
                accounts_grouped.append({
                    'Account': account_data['Account'],
                    'AccountName': account_data['AccountName'],
                    'OpeningBalance': opening_balance,
                    'transactions': account_data['transactions'],
                    'TotalDebit': totals['TotalDebit'],
                    'TotalCredit': totals['TotalCredit'],
                    'ClosingBalance': opening_balance + totals['Balance']
                })
            
            conn.close()
            
            # Calculate grand total
            if accounts_grouped:
                grand_total = {
                    'TotalDebit': sum(a['TotalDebit'] for a in accounts_grouped),
                    'TotalCredit': sum(a['TotalCredit'] for a in accounts_grouped),
                }
                grand_total['Difference'] = grand_total['TotalDebit'] - grand_total['TotalCredit']
            
        except Exception as e:
            logger.exception("Error fetching ledger data")
            error = str(e)
    
    # Pagination on accounts level
    paginator = Paginator(accounts_grouped, page_size)
    page_obj = paginator.get_page(page_num)
    
    context = {
        'db_options': db_options,
        'selected_db_key': selected_db_key,
        'chart_of_accounts': chart_of_accounts,
        'business_partners': business_partners,
        'projects': projects,
        'trans_types': trans_types,
        'accounts_grouped': list(page_obj.object_list),
        'grand_total': grand_total,
        'error': error,
        'warning': warning,
        'pagination': {
            'page': page_obj.number,
            'num_pages': paginator.num_pages,
            'has_next': page_obj.has_next(),
            'has_prev': page_obj.has_previous(),
            'next_page': (page_obj.next_page_number() if page_obj.has_next() else None),
            'prev_page': (page_obj.previous_page_number() if page_obj.has_previous() else None),
            'count': paginator.count,
            'page_size': page_size,
        },
        'filters': {
            'account_from': account_from,
            'account_to': account_to,
            'from_date': from_date,
            'to_date': to_date,
            'bp_code': bp_code,
            'project_code': project_code,
            'trans_type': trans_type,
        }
    }
    
    return render(request, 'general_ledger/general_ledger.html', context)


@staff_member_required
def export_ledger_csv(request):
    """
    Export general ledger to CSV format.
    """
    try:
        # Get filter parameters
        company = request.GET.get('company', '4B-BIO')
        account_from = (request.GET.get('account_from') or '').strip()
        account_to = (request.GET.get('account_to') or '').strip()
        from_date = (request.GET.get('from_date') or '').strip()
        to_date = (request.GET.get('to_date') or '').strip()
        bp_code = (request.GET.get('bp_code') or '').strip()
        project_code = (request.GET.get('project_code') or '').strip()
        trans_type = (request.GET.get('trans_type') or '').strip()
        
        # Fetch all data
        conn = get_hana_connection(company)
        transactions = hana_queries.general_ledger_report(
            conn,
            account_from=account_from or None,
            account_to=account_to or None,
            from_date=from_date or None,
            to_date=to_date or None,
            bp_code=bp_code or None,
            project_code=project_code or None,
            trans_type=trans_type or None
        )
        conn.close()
        
        # Create CSV response
        response = HttpResponse(content_type='text/csv')
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        response['Content-Disposition'] = f'attachment; filename="general_ledger_{company}_{timestamp}.csv"'
        
        writer = csv.writer(response)
        
        # Write header
        writer.writerow([
            'Posting Date', 'Trans ID', 'Account', 'Account Name', 'BP Code', 'BP Name',
            'Trans Type', 'Reference', 'Description', 'Debit', 'Credit', 'Project'
        ])
        
        # Write data rows
        for txn in transactions:
            writer.writerow([
                txn.get('PostingDate', ''),
                txn.get('TransId', ''),
                txn.get('Account', ''),
                txn.get('AccountName', ''),
                txn.get('BPCode', ''),
                txn.get('BPName', ''),
                txn.get('TransTypeName') or txn.get('TransType', ''),
                txn.get('Reference1', ''),
                txn.get('Description', ''),
                txn.get('Debit', 0),
                txn.get('Credit', 0),
                txn.get('ExtractedProject') or txn.get('ProjectCode', ''),
            ])
        
        return response
        
    except Exception as e:
        logger.exception("Error exporting CSV")
        return HttpResponse(f"Error exporting CSV: {str(e)}", status=500)

@swagger_auto_schema(
    method='get',
    tags=['General Ledger'],
    operation_summary='Export General Ledger to PDF',
    operation_description='Download general ledger report as PDF file with filters applied. Returns formatted PDF file with headers and styling. Use user parameter to filter by user\'s assigned customers.',
    manual_parameters=[
        openapi.Parameter('company', openapi.IN_QUERY, type=openapi.TYPE_STRING, description='Optional: Company database key', default='4B-ORANG_APP', enum=['4B-BIO_APP', '4B-ORANG_APP']),
        openapi.Parameter('account_from', openapi.IN_QUERY, type=openapi.TYPE_STRING, description='Start of account range'),
        openapi.Parameter('account_to', openapi.IN_QUERY, type=openapi.TYPE_STRING, description='End of account range'),
        openapi.Parameter('from_date', openapi.IN_QUERY, type=openapi.TYPE_STRING, description='Start date (YYYY-MM-DD)'),
        openapi.Parameter('to_date', openapi.IN_QUERY, type=openapi.TYPE_STRING, description='End date (YYYY-MM-DD)'),
        openapi.Parameter('bp_code', openapi.IN_QUERY, type=openapi.TYPE_STRING, description='Business Partner CardCode. If user parameter is provided, validates that bp_code belongs to that user.'),
        openapi.Parameter('user', openapi.IN_QUERY, type=openapi.TYPE_STRING, description='Optional: User ID or username. Filters transactions to only user\'s assigned customers. Can be combined with bp_code for validation.'),
        openapi.Parameter('project_code', openapi.IN_QUERY, type=openapi.TYPE_STRING, description='Project Code'),
        openapi.Parameter('trans_type', openapi.IN_QUERY, type=openapi.TYPE_STRING, description='Transaction Type (e.g., 13, 30)'),
    ],
    responses={
        200: openapi.Response(
            description='PDF file download',
            schema=openapi.Schema(type=openapi.TYPE_FILE)
        ),
        500: 'Error generating PDF file'
    }
)
@api_view(['GET'])
def export_ledger_pdf_api(request):
    """
    GET /api/general-ledger/export-pdf/
    
    Export general ledger to PDF format for mobile app.
    Returns a downloadable PDF file with formatted headers and data.
    """
    if not REPORTLAB_AVAILABLE:
        return Response({
            'success': False,
            'error': 'PDF export not available. Please install reportlab package.'
        }, status=500)
    
    try:
        # Get filter parameters
        company = request.GET.get('company', '4B-ORANG_APP')
        account_from = (request.GET.get('account_from') or '').strip()
        account_to = (request.GET.get('account_to') or '').strip()
        from_date = (request.GET.get('from_date') or '').strip()
        to_date = (request.GET.get('to_date') or '').strip()
        bp_code = (request.GET.get('bp_code') or '').strip()
        user_param = request.GET.get('user', '').strip()
        project_code = (request.GET.get('project_code') or '').strip()
        trans_type = (request.GET.get('trans_type') or '').strip()
        
        # Handle user-based filtering
        if user_param:
            try:
                from accounts.models import User
                from FieldAdvisoryService.models import Dealer
                
                # Get user object
                user_obj = None
                try:
                    user_id = int(user_param)
                    user_obj = User.objects.get(id=user_id)
                except (ValueError, User.DoesNotExist):
                    user_obj = User.objects.filter(username=user_param).first()
                
                if not user_obj:
                    return Response({'success': False, 'error': f'User "{user_param}" not found'}, status=404)
                
                # Get dealer card codes for this user
                dealers = Dealer.objects.filter(user=user_obj).values_list('card_code', flat=True).exclude(card_code__isnull=True).exclude(card_code='')
                dealer_card_codes = list(dealers)
                
                if not dealer_card_codes:
                    # Return empty list for bp_code - will result in empty export file
                    bp_code = []
                elif bp_code:
                    # If bp_code is provided, validate it belongs to user
                    if bp_code not in dealer_card_codes:
                        return Response({'success': False, 'error': f'Business Partner "{bp_code}" does not belong to user "{user_param}"'}, status=403)
                    # Use only the specified bp_code
                    bp_code = bp_code
                else:
                    # Use all dealer card codes as a list
                    bp_code = dealer_card_codes
                    
            except Exception as e:
                return Response({'success': False, 'error': f'Error processing user filter: {str(e)}'}, status=500)
        
        # Fetch all data
        conn = get_hana_connection(company)
        transactions = hana_queries.general_ledger_report(
            conn,
            account_from=account_from or None,
            account_to=account_to or None,
            from_date=from_date or None,
            to_date=to_date or None,
            bp_code=bp_code if bp_code else None,
            project_code=project_code or None,
            trans_type=trans_type or None
        )
        conn.close()
        
        # Create PDF response
        response = HttpResponse(content_type='application/pdf')
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        response['Content-Disposition'] = f'attachment; filename="general_ledger_{company}_{timestamp}.pdf"'
        
        # Create PDF document
        pdf_buffer = BytesIO()
        doc = SimpleDocTemplate(pdf_buffer, pagesize=landscape(letter), topMargin=0.4*inch, bottomMargin=0.4*inch)
        
        # Container for the 'Flowable' objects
        elements = []
        
        # Get styles
        styles = getSampleStyleSheet()
        
        # Create paragraph style for table cells
        cell_style = ParagraphStyle(
            'CellStyle',
            parent=styles['Normal'],
            fontSize=9,
            fontName='Helvetica',
            leading=11,
            alignment=TA_LEFT
        )
        
        # Add company name (Four Brothers Group)
        company_style = ParagraphStyle(
            'CompanyName',
            parent=styles['Normal'],
            fontSize=12,
            textColor=colors.black,
            alignment=TA_CENTER,
            fontName='Helvetica-Bold',
            spaceAfter=2
        )
        elements.append(Paragraph('Four Brothers Group', company_style))
        
        # Add title (General Ledger)
        title_style = ParagraphStyle(
            'ReportTitle',
            parent=styles['Heading1'],
            fontSize=14,
            textColor=colors.black,
            alignment=TA_CENTER,
            fontName='Helvetica-Bold',
            spaceAfter=4
        )
        elements.append(Paragraph('General Ledger', title_style))
        
        # Get company display name mapping
        company_names = {
            '4B-BIO': 'FARMING INPUTS (PVT) LTD',
            '4B-ORANG': 'ORANGE PROTECTION (PVT) LTD',
            '4B-KINDWISE': 'KINDWISE (PVT) LTD',
        }
        company_display_name = company_names.get(company, company)
        
        # Add company name from database
        comp_name_style = ParagraphStyle(
            'CompanySubName',
            parent=styles['Normal'],
            fontSize=10,
            textColor=colors.black,
            alignment=TA_LEFT,
            fontName='Helvetica-Bold',
            spaceAfter=6
        )
        elements.append(Paragraph(f'To: {company_display_name}', comp_name_style))
        
        # Prepare date range
        from_date_display = from_date if from_date else '01/01/2000'
        to_date_display = to_date if to_date else datetime.now().strftime('%m/%d/%Y')
        
        # Convert date format from YYYY-MM-DD to M/D/YYYY if needed
        try:
            if from_date and len(from_date) == 10:
                from_date_obj = datetime.strptime(from_date, '%Y-%m-%d')
                from_date_display = f"{from_date_obj.month}/{from_date_obj.day}/{from_date_obj.year}"
        except:
            pass
        
        try:
            if to_date and len(to_date) == 10:
                to_date_obj = datetime.strptime(to_date, '%Y-%m-%d')
                to_date_display = f"{to_date_obj.month}/{to_date_obj.day}/{to_date_obj.year}"
        except:
            pass
        
        # Add date range line
        date_range_style = ParagraphStyle(
            'DateRange',
            parent=styles['Normal'],
            fontSize=9,
            textColor=colors.black,
            alignment=TA_LEFT,
            spaceAfter=2
        )
        elements.append(Paragraph(f'From: {from_date_display}  To: {to_date_display}', date_range_style))
        
        # Add print date
        now = datetime.now()
        print_date = f"{now.month}/{now.day}/{now.year} {now.strftime('%I:%M:%S%p')}"
        elements.append(Paragraph(f'Print Date: {print_date}', date_range_style))
        
        elements.append(Spacer(1, 0.15*inch))
        
        # Prepare table data
        table_data = [
            ['VNo.', 'VDate', 'Narration', 'Type', 'Debit', 'Credit', 'Balance']
        ]
        
        total_debit = 0
        total_credit = 0
        running_balance = 0
        
        for txn in transactions:
            debit = float(txn.get('Debit', 0))
            credit = float(txn.get('Credit', 0))
            total_debit += debit
            total_credit += credit
            running_balance += (debit - credit)
            
            # Format date
            posting_date = str(txn.get('PostingDate', ''))[:10]
            try:
                date_obj = datetime.strptime(posting_date, '%Y-%m-%d')
                posting_date = f"{date_obj.month}/{date_obj.day}/{date_obj.year}"
            except:
                pass
            
            # Get narration text
            narration_text = str(txn.get('ProjectName', '') or txn.get('ProjectCode', ''))
            narration_para = Paragraph(narration_text, cell_style) if narration_text else ''
            
            table_data.append([
                str(txn.get('TransId', '')),  # VNo
                posting_date,  # VDate
                narration_para,  # Narration (Policy Name/Project)
                str(txn.get('TransTypeName') or txn.get('TransType', '')),  # Type Name
                f"{debit:.2f}" if debit > 0 else '',  # Debit
                f"{credit:.2f}" if credit > 0 else '',  # Credit
                f"{running_balance:.2f}",  # Balance
            ])
        
        # Add totals row
        if table_data:
            table_data.append([
                '', '', '',
                'TOTAL',
                f"{total_debit:.2f}", f"{total_credit:.2f}", f"{(total_debit - total_credit):.2f}"
            ])
        
        # Create table
        table = Table(table_data, colWidths=[0.65*inch, 0.85*inch, 2.9*inch, 0.9*inch, 1.2*inch, 1.2*inch, 1.2*inch])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#404040')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('ALIGN', (0, 1), (0, -1), 'CENTER'),
            ('ALIGN', (1, 1), (1, -1), 'CENTER'),
            ('ALIGN', (2, 1), (2, -1), 'LEFT'),
            ('ALIGN', (3, 1), (3, -1), 'CENTER'),
            ('ALIGN', (4, 1), (-1, -1), 'RIGHT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 10),
            ('TOPPADDING', (0, 0), (-1, 0), 8),
            ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor('#cccccc')),
            ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 1), (-1, -1), 9),
            ('ROWBACKGROUNDS', (0, 1), (-1, -2), [colors.white, colors.HexColor('#f5f5f5')]),
            ('LEFTPADDING', (0, 0), (-1, -1), 5),
            ('RIGHTPADDING', (0, 0), (-1, -1), 5),
            ('TOPPADDING', (0, 1), (-1, -1), 5),
            ('BOTTOMPADDING', (0, 1), (-1, -1), 5),
        ]))
        
        elements.append(table)
        
        # Build PDF
        doc.build(elements)
        
        # Return PDF
        pdf_buffer.seek(0)
        response.write(pdf_buffer.getvalue())
        return response
        
    except Exception as e:
        logger.exception("Error exporting PDF")
        return Response({
            'success': False,
            'error': f'Error exporting PDF: {str(e)}'
        }, status=500)


@staff_member_required
def export_ledger_pdf(request):
    """
    Export general ledger to PDF format.
    """
    if not REPORTLAB_AVAILABLE:
        return HttpResponse(
            "PDF export requires reportlab. Install it with: pip install reportlab",
            status=500
        )
    
    try:
        # Get filter parameters
        company = request.GET.get('company', '4B-BIO')
        account_from = (request.GET.get('account_from') or '').strip()
        account_to = (request.GET.get('account_to') or '').strip()
        from_date = (request.GET.get('from_date') or '').strip()
        to_date = (request.GET.get('to_date') or '').strip()
        bp_code = (request.GET.get('bp_code') or '').strip()
        project_code = (request.GET.get('project_code') or '').strip()
        trans_type = (request.GET.get('trans_type') or '').strip()
        
        # Fetch all data
        conn = get_hana_connection(company)
        transactions = hana_queries.general_ledger_report(
            conn,
            account_from=account_from or None,
            account_to=account_to or None,
            from_date=from_date or None,
            to_date=to_date or None,
            bp_code=bp_code or None,
            project_code=project_code or None,
            trans_type=trans_type or None
        )
        conn.close()
        
        # Create PDF response
        response = HttpResponse(content_type='application/pdf')
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        response['Content-Disposition'] = f'attachment; filename="general_ledger_{company}_{timestamp}.pdf"'
        
        # Create PDF document
        pdf_buffer = BytesIO()
        doc = SimpleDocTemplate(pdf_buffer, pagesize=landscape(letter), topMargin=0.4*inch, bottomMargin=0.4*inch)
        
        # Container for the 'Flowable' objects
        elements = []
        
        # Get styles
        styles = getSampleStyleSheet()
        
        # Create paragraph style for table cells
        cell_style = ParagraphStyle(
            'CellStyle',
            parent=styles['Normal'],
            fontSize=9,
            fontName='Helvetica',
            leading=11,
            alignment=TA_LEFT
        )
        
        # Add company name (Four Brothers Group)
        company_style = ParagraphStyle(
            'CompanyName',
            parent=styles['Normal'],
            fontSize=12,
            textColor=colors.black,
            alignment=TA_CENTER,
            fontName='Helvetica-Bold',
            spaceAfter=2
        )
        elements.append(Paragraph('Four Brothers Group', company_style))
        
        # Add title (General Ledger)
        title_style = ParagraphStyle(
            'ReportTitle',
            parent=styles['Heading1'],
            fontSize=14,
            textColor=colors.black,
            alignment=TA_CENTER,
            fontName='Helvetica-Bold',
            spaceAfter=4
        )
        elements.append(Paragraph('General Ledger', title_style))
        
        # Get company display name mapping
        company_names = {
            '4B-BIO': 'FARMING INPUTS (PVT) LTD',
            '4B-ORANG': 'ORANGE PROTECTION (PVT) LTD',
            '4B-KINDWISE': 'KINDWISE (PVT) LTD',
        }
        company_display_name = company_names.get(company, company)
        
        # Add company name from database
        comp_name_style = ParagraphStyle(
            'CompanySubName',
            parent=styles['Normal'],
            fontSize=10,
            textColor=colors.black,
            alignment=TA_LEFT,
            fontName='Helvetica-Bold',
            spaceAfter=6
        )
        elements.append(Paragraph(f'To: {company_display_name}', comp_name_style))
        
        # Prepare date range
        from_date_display = from_date if from_date else '01/01/2000'
        to_date_display = to_date if to_date else datetime.now().strftime('%m/%d/%Y')
        
        # Convert date format from YYYY-MM-DD to M/D/YYYY if needed
        try:
            if from_date and len(from_date) == 10:
                from_date_obj = datetime.strptime(from_date, '%Y-%m-%d')
                from_date_display = f"{from_date_obj.month}/{from_date_obj.day}/{from_date_obj.year}"
        except:
            pass
        
        try:
            if to_date and len(to_date) == 10:
                to_date_obj = datetime.strptime(to_date, '%Y-%m-%d')
                to_date_display = f"{to_date_obj.month}/{to_date_obj.day}/{to_date_obj.year}"
        except:
            pass
        
        # Add date range line
        date_range_style = ParagraphStyle(
            'DateRange',
            parent=styles['Normal'],
            fontSize=9,
            textColor=colors.black,
            alignment=TA_LEFT,
            spaceAfter=2
        )
        elements.append(Paragraph(f'From: {from_date_display}  To: {to_date_display}', date_range_style))
        
        # Add print date
        now = datetime.now()
        print_date = f"{now.month}/{now.day}/{now.year} {now.strftime('%I:%M:%S%p')}"
        elements.append(Paragraph(f'Print Date: {print_date}', date_range_style))
        
        elements.append(Spacer(1, 0.15*inch))
        
        # Prepare table data
        table_data = [
            ['VNo.', 'VDate', 'Narration', 'Type', 'Debit', 'Credit', 'Balance']
        ]
        
        total_debit = 0
        total_credit = 0
        running_balance = 0
        
        for txn in transactions:
            debit = float(txn.get('Debit', 0))
            credit = float(txn.get('Credit', 0))
            total_debit += debit
            total_credit += credit
            running_balance += (debit - credit)
            
            # Format date
            posting_date = str(txn.get('PostingDate', ''))[:10]
            try:
                date_obj = datetime.strptime(posting_date, '%Y-%m-%d')
                posting_date = f"{date_obj.month}/{date_obj.day}/{date_obj.year}"
            except:
                pass
            
            # Get narration text
            narration_text = str(txn.get('ProjectName', '') or txn.get('ProjectCode', ''))
            narration_para = Paragraph(narration_text, cell_style) if narration_text else ''
            
            table_data.append([
                str(txn.get('TransId', '')),  # VNo
                posting_date,  # VDate
                narration_para,  # Narration (Policy Name/Project)
                str(txn.get('TransTypeName') or txn.get('TransType', '')),  # Type Name
                f"{debit:.2f}" if debit > 0 else '',  # Debit
                f"{credit:.2f}" if credit > 0 else '',  # Credit
                f"{running_balance:.2f}",  # Balance
            ])
        
        # Add totals row
        if table_data:
            table_data.append([
                '', '', '',
                'TOTAL',
                f"{total_debit:.2f}", f"{total_credit:.2f}", f"{(total_debit - total_credit):.2f}"
            ])
        
        # Create table
        table = Table(table_data, colWidths=[0.65*inch, 0.85*inch, 2.9*inch, 0.9*inch, 1.2*inch, 1.2*inch, 1.2*inch])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#404040')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('ALIGN', (0, 1), (0, -1), 'CENTER'),
            ('ALIGN', (1, 1), (1, -1), 'CENTER'),
            ('ALIGN', (2, 1), (2, -1), 'LEFT'),
            ('ALIGN', (3, 1), (3, -1), 'CENTER'),
            ('ALIGN', (4, 1), (-1, -1), 'RIGHT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 10),
            ('TOPPADDING', (0, 0), (-1, 0), 8),
            ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor('#cccccc')),
            ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 1), (-1, -1), 9),
            ('ROWBACKGROUNDS', (0, 1), (-1, -2), [colors.white, colors.HexColor('#f5f5f5')]),
            ('LEFTPADDING', (0, 0), (-1, -1), 5),
            ('RIGHTPADDING', (0, 0), (-1, -1), 5),
            ('TOPPADDING', (0, 1), (-1, -1), 5),
            ('BOTTOMPADDING', (0, 1), (-1, -1), 5),
        ]))
        
        elements.append(table)
        
        # Build PDF
        doc.build(elements)
        
        # Return PDF
        pdf_buffer.seek(0)
        response.write(pdf_buffer.getvalue())
        return response
        
    except Exception as e:
        logger.exception("Error exporting PDF")
        return HttpResponse(f"Error exporting PDF: {str(e)}", status=500)
