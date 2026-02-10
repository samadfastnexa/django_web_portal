import os
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from django.utils import timezone
from datetime import timedelta
from django.db.models import Count, Sum, Avg, Q
from django.conf import settings

from .serializers import (
    DashboardOverviewSerializer,
    SalesVsAchievementSerializer,
    CollectionVsAchievementSerializer,
    FarmerStatsSerializer,
    TargetSerializer,
    PerformanceMetricSerializer,
    CollectionAnalyticsResponseSerializer
)

# Import models from other apps
from farmers.models import Farmer
from FieldAdvisoryService.models import MeetingSchedule, SalesOrder
from farmerMeetingDataEntry.models import Meeting, FieldDay
from preferences.models import Setting

# Import SAP functions
try:
    from sap_integration.hana_connect import (
        sales_vs_achievement_by_emp,
        sales_vs_achievement_geo_inv,
        collection_vs_achievement,
        _load_env_file as _hana_load_env_file
    )
    SAP_AVAILABLE = True
except ImportError:
    SAP_AVAILABLE = False


class DashboardOverviewView(APIView):
    """
    Comprehensive Dashboard Overview API
    
    Aggregates data from multiple sources:
    - Sales vs Achievement from SAP
    - Targets and Performance
    - Farmer Statistics
    - Today's Activities
    """
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        tags=["Analytics Dashboard"],
        operation_description="""
        Get comprehensive dashboard overview with all key metrics:
        - Sales vs Achievements (SAP Integration)
        - Targets and Performance
        - Farmer Statistics
        - Today's Visits and Activities
        - Pending Sales Orders
        """,
        manual_parameters=[
            openapi.Parameter('emp_id', openapi.IN_QUERY, description="Employee ID for SAP data", type=openapi.TYPE_INTEGER, required=False),
            openapi.Parameter('start_date', openapi.IN_QUERY, description="Start date (YYYY-MM-DD)", type=openapi.TYPE_STRING, required=False),
            openapi.Parameter('end_date', openapi.IN_QUERY, description="End date (YYYY-MM-DD)", type=openapi.TYPE_STRING, required=False),
            openapi.Parameter('company', openapi.IN_QUERY, description="Company key (e.g., 4B-BIO)", type=openapi.TYPE_STRING, required=False),
            openapi.Parameter('region', openapi.IN_QUERY, description="Region filter", type=openapi.TYPE_STRING, required=False),
            openapi.Parameter('zone', openapi.IN_QUERY, description="Zone filter", type=openapi.TYPE_STRING, required=False),
            openapi.Parameter('territory', openapi.IN_QUERY, description="Territory filter", type=openapi.TYPE_STRING, required=False),
            openapi.Parameter('in_millions', openapi.IN_QUERY, description="Convert values to millions", type=openapi.TYPE_BOOLEAN, required=False),
        ],
        responses={
            200: openapi.Response(
                description="Dashboard overview data",
                schema=DashboardOverviewSerializer
            )
        }
    )
    def get(self, request):
        """Get comprehensive dashboard overview"""
        user = request.user
        
        # Get query parameters
        emp_id_param = request.GET.get('emp_id', '').strip()
        start_date_param = request.GET.get('start_date', '').strip()
        end_date_param = request.GET.get('end_date', '').strip()
        company_param = request.GET.get('company', '').strip()
        region_param = request.GET.get('region', '').strip()
        zone_param = request.GET.get('zone', '').strip()
        territory_param = request.GET.get('territory', '').strip()
        in_millions = request.GET.get('in_millions', '').strip().lower() in ('true', '1', 'yes', 'y')
        
        # Default collection window: 1 Nov 2025 - 30 Nov 2025 when no dates provided
        if not start_date_param and not end_date_param:
            start_date_param = '2025-11-01'
            end_date_param = '2025-11-30'
        
        # Fetch SAP sales data (includes company options mapping)
        sales_data = self._get_sales_vs_achievement(
            emp_id_param, start_date_param, end_date_param,
            company_param, region_param, zone_param, territory_param, in_millions
        ) or {}
        sales_list = sales_data.get('sales_vs_achievement', []) or []

        # Fetch SAP collection data
        collection_data = self._get_collection_vs_achievement(
            emp_id_param, start_date_param, end_date_param,
            company_param, region_param, zone_param, territory_param, in_millions,
            group_by_date=False, ignore_emp_filter=False
        ) or {}
        collection_list = collection_data.get('collection_vs_achievement', []) or []

        # Aggregate sales into combined view
        total_target = 0.0
        total_achievement = 0.0
        min_from = None
        max_to = None
        for rec in sales_list:
            try:
                total_target += float(rec.get('sales_target', 0) or 0)
            except Exception:
                pass
            try:
                total_achievement += float(rec.get('achievement', 0) or 0)
            except Exception:
                pass
            f_ref = rec.get('from_date')
            t_ref = rec.get('to_date')
            if f_ref and (min_from is None or str(f_ref) < str(min_from)):
                min_from = f_ref
            if t_ref and (max_to is None or str(t_ref) > str(max_to)):
                max_to = t_ref

        # Aggregate collection into combined view
        col_target = 0.0
        col_achievement = 0.0
        col_min_from = None
        col_max_to = None
        for rec in collection_list:
            try:
                col_target += float(rec.get('collection_target', 0) or 0)
            except Exception:
                pass
            try:
                col_achievement += float(rec.get('collection_achievement', 0) or 0)
            except Exception:
                pass
            f_ref = rec.get('from_date')
            t_ref = rec.get('to_date')
            if f_ref and (col_min_from is None or str(f_ref) < str(col_min_from)):
                col_min_from = f_ref
            if t_ref and (col_max_to is None or str(t_ref) > str(col_max_to)):
                col_max_to = t_ref

        # Farmer statistics
        farmer_stats = self._get_farmer_stats(user) or {}
        total_farmers = farmer_stats.get('total_count', 0) or 0

        # Today's activities
        activity_data = self._get_todays_activities(user) or {}
        visits_today = activity_data.get('visits_today', 0) or 0

        # Pending sales orders
        pending_sales = self._get_pending_sales_orders(user) or 0

        # Build response to match requested structure
        response_data = {
            'todays_visits': {
                'current_value': visits_today,
                'last_month_value': 0
            },
            'pending_sales_orders': {
                'current_value': pending_sales,
                'last_month_value': 0
            },
            'total_farmers': {
                'current_value': total_farmers,
                'last_month_value': 0
            },
            'sales_combined': {
                'EMPID': 0,
                'TERRITORYID': 0,
                'TERRITORYNAME': 'All Territories',
                'SALES_TARGET': total_target,
                'ACCHIVEMENT': total_achievement,
                'F_REFDATE': min_from,
                'T_REFDATE': max_to,
                'SALES_TARGET_LAST_MONTH': 0,
                'ACCHIVEMENT_LAST_MONTH': 0
            },
            'collection_combined': {
                'TERRITORYNAME': 'All Territories',
                'COLLECTION_TARGET': col_target,
                'COLLECTION_ACHIEVEMENT': col_achievement,
                'F_REFDATE': col_min_from,
                'T_REFDATE': col_max_to,
                'COLLECTION_TARGET_LAST_MONTH': 0,
                'COLLECTION_ACHIEVEMENT_LAST_MONTH': 0
            },
            'company_options': sales_data.get('company_options') or collection_data.get('company_options', []),
            'selected_company': sales_data.get('selected_company', company_param)
        }

        return Response(response_data, status=status.HTTP_200_OK)
    
    def _get_sales_vs_achievement(self, emp_id, start_date, end_date, company, region, zone, territory, in_millions):
        """Get sales vs achievement data from SAP"""
        if not SAP_AVAILABLE:
            return {'error': 'SAP integration not available'}
        
        result = {
            'sales_vs_achievement': [],
            'company_options': [],
            'selected_company': company
        }
        
        try:
            # Load environment variables
            for path in [
                os.path.join(os.path.dirname(__file__), '..', 'sap_integration', '.env'),
                os.path.join(str(settings.BASE_DIR), '.env'),
                os.path.join(str(settings.BASE_DIR), '..', '.env'),
                os.path.join(os.getcwd(), '.env')
            ]:
                try:
                    _hana_load_env_file(path)
                except Exception:
                    pass
            
            from hdbcli import dbapi
            
            # Get connection parameters
            host = os.environ.get('HANA_HOST', '')
            port = os.environ.get('HANA_PORT', '30015')
            user_name = os.environ.get('HANA_USER', '')
            password = os.environ.get('HANA_PASSWORD', '')
            schema = os.environ.get('HANA_SCHEMA', '')
            
            # Get company schema mapping / default schema, prefer SAP_COMPANY_DB over HANA_SCHEMA/FASTAPP
            try:
                db_setting = Setting.objects.filter(slug='SAP_COMPANY_DB').first()
                mapping = {}
                if db_setting:
                    if isinstance(db_setting.value, dict):
                        mapping = db_setting.value
                    else:
                        raw_schema = str(db_setting.value or '').strip()
                        if raw_schema:
                            schema = raw_schema
                if mapping:
                    result['company_options'] = [
                        {"key": k.strip(), "schema": str(v).strip()}
                        for k, v in mapping.items()
                    ]
                    if company:
                        mapped = mapping.get(company.strip())
                        if mapped:
                            schema = str(mapped).strip()
                env_schema = os.environ.get('SAP_COMPANY_DB')
                if env_schema and not mapping and not db_setting:
                    schema = str(env_schema).strip()
                if not schema:
                    schema = '4B-BIO_APP'
            except Exception:
                if not schema:
                    schema = '4B-BIO_APP'
            
            # Connect to HANA
            encrypt = str(os.environ.get('HANA_ENCRYPT', '')).strip().lower() in ('true', '1', 'yes')
            ssl_validate = str(os.environ.get('HANA_SSL_VALIDATE', '')).strip().lower() in ('true', '1', 'yes')
            
            kwargs = {
                'address': host,
                'port': int(port),
                'user': user_name,
                'password': password
            }
            if encrypt:
                kwargs['encrypt'] = True
                kwargs['sslValidateCertificate'] = ssl_validate
            
            conn = dbapi.connect(**kwargs)
            
            if schema:
                cur = conn.cursor()
                cur.execute(f'SET SCHEMA "{schema}"')
                cur.close()
            
            # Parse emp_id
            emp_val = None
            if emp_id:
                try:
                    emp_val = int(emp_id)
                except Exception:
                    pass
            
            # Get sales vs achievement data
            if region or zone or territory:
                # Use geo-based function
                data = sales_vs_achievement_geo_inv(
                    conn,
                    emp_id=emp_val,
                    region=region or None,
                    zone=zone or None,
                    territory=territory or None,
                    start_date=start_date or None,
                    end_date=end_date or None,
                    group_by_emp=bool(emp_val)
                )
            else:
                # Use employee-based function
                data = sales_vs_achievement_by_emp(
                    conn,
                    emp_val,
                    None,
                    None,
                    None,
                    start_date or None,
                    end_date or None
                )
            
            # Process and format data
            sales_list = []
            for record in (data or []):
                if isinstance(record, dict):
                    sales_target = float(record.get('SALES_TARGET', 0) or 0)
                    achievement = float(record.get('ACCHIVEMENT', 0) or record.get('ACHIEVEMENT', 0) or 0)
                    
                    if in_millions:
                        sales_target = round(sales_target / 1000000.0, 2)
                        achievement = round(achievement / 1000000.0, 2)
                    
                    percentage = round((achievement / sales_target * 100), 2) if sales_target > 0 else 0
                    
                    sales_list.append({
                        'emp_id': record.get('EMPID'),
                        'territory_id': record.get('TERRITORYID'),
                        'territory_name': record.get('TERRITORYNAME'),
                        'sales_target': sales_target,
                        'achievement': achievement,
                        'from_date': record.get('F_REFDATE'),
                        'to_date': record.get('T_REFDATE'),
                        'percentage': percentage
                    })
            
            result['sales_vs_achievement'] = sales_list
            
            conn.close()
            
        except Exception as e:
            result['error'] = str(e)
        
        return result
    
    def _get_collection_vs_achievement(self, emp_id, start_date, end_date, company, region, zone, territory, in_millions, group_by_date, ignore_emp_filter):
        """Get collection vs achievement data from SAP"""
        if not SAP_AVAILABLE:
            return {'error': 'SAP integration not available'}
        
        result = {
            'collection_vs_achievement': [],
            'company_options': [],
            'selected_company': company,
            'selected_region': region,
            'selected_zone': zone,
            'selected_territory': territory
        }
        
        try:
            # Load environment variables
            for path in [
                os.path.join(os.path.dirname(__file__), '..', 'sap_integration', '.env'),
                os.path.join(str(settings.BASE_DIR), '.env'),
                os.path.join(str(settings.BASE_DIR), '..', '.env'),
                os.path.join(os.getcwd(), '.env')
            ]:
                try:
                    _hana_load_env_file(path)
                except Exception:
                    pass
            
            from hdbcli import dbapi
            
            # Get connection parameters
            host = os.environ.get('HANA_HOST', '')
            port = os.environ.get('HANA_PORT', '30015')
            user_name = os.environ.get('HANA_USER', '')
            password = os.environ.get('HANA_PASSWORD', '')
            schema = os.environ.get('HANA_SCHEMA', '4B-BIO_APP')
            
            # Get company schema mapping
            try:
                db_setting = Setting.objects.filter(slug='SAP_COMPANY_DB').first()
                if db_setting:
                    mapping = db_setting.value if isinstance(db_setting.value, dict) else {}
                    if mapping:
                        result['company_options'] = [
                            {"key": k.strip(), "schema": str(v).strip()}
                            for k, v in mapping.items()
                        ]
                        if company:
                            # Try to match company key
                            schema = mapping.get(company.strip(), schema)
                    elif isinstance(db_setting.value, str):
                        # Try to parse string JSON
                        import json
                        try:
                            mapping = json.loads(db_setting.value)
                            result['company_options'] = [
                                {"key": k.strip(), "schema": str(v).strip()}
                                for k, v in mapping.items()
                            ]
                            if company:
                                schema = mapping.get(company.strip(), schema)
                        except:
                            pass
            except Exception:
                pass
            
            # Fallback for schema selection if not found in mapping but company param is present
            if company and not any(opt['key'] == company for opt in result['company_options']):
                norm = company.strip().upper().replace('-APP', '_APP')
                if '4B-BIO' in norm:
                    schema = '4B-BIO_APP'
                elif '4B-ORANG' in norm:
                    schema = '4B-ORANG_APP'
                else:
                    schema = company
            
            # Connect to HANA
            encrypt = str(os.environ.get('HANA_ENCRYPT', '')).strip().lower() in ('true', '1', 'yes')
            ssl_validate = str(os.environ.get('HANA_SSL_VALIDATE', '')).strip().lower() in ('true', '1', 'yes')
            
            kwargs = {
                'address': host,
                'port': int(port),
                'user': user_name,
                'password': password
            }
            if encrypt:
                kwargs['encrypt'] = True
                kwargs['sslValidateCertificate'] = ssl_validate
                # Fix for self-signed certificates
                if not ssl_validate:
                    kwargs['sslValidateCertificate'] = False
            
            conn = dbapi.connect(**kwargs)
            
            if schema:
                cur = conn.cursor()
                cur.execute(f'SET SCHEMA "{schema}"')
                cur.close()
            
            # Parse emp_id
            emp_val = None
            if emp_id:
                try:
                    emp_val = int(emp_id)
                except Exception:
                    pass
            
            # Get collection vs achievement data using robust geo function
            data = sales_vs_achievement_geo_inv(
                conn,
                emp_id=emp_val,
                region=region or None,
                zone=zone or None,
                territory=territory or None,
                start_date=start_date or None,
                end_date=end_date or None,
                group_by_date=group_by_date,
                group_by_emp=False
            )
            
            # Process and format data
            collection_list = []
            for record in (data or []):
                if isinstance(record, dict):
                    target = float(record.get('Collection_Target', 0) or 0)
                    achievement = float(record.get('Collection_Achievement', 0) or 0)
                    
                    if in_millions:
                        target = round(target / 1000000.0, 2)
                        achievement = round(achievement / 1000000.0, 2)
                    
                    percentage = round((achievement / target * 100), 2) if target > 0 else 0
                    
                    collection_list.append({
                        'region': record.get('Region'),
                        'zone': record.get('Zone'),
                        'territory_id': record.get('TerritoryId'),
                        'territory_name': record.get('Territory') or record.get('TerritoryName'),
                        'collection_target': target,
                        'collection_achievement': achievement,
                        'from_date': record.get('From_Date'),
                        'to_date': record.get('To_Date'),
                        'percentage': percentage
                    })
            
            result['collection_vs_achievement'] = collection_list
            
            conn.close()
            
        except Exception as e:
            result['error'] = str(e)
        
        return result

    def _get_farmer_stats(self, user):
        """Get farmer statistics"""
        # Get all farmers (admin) or user's farmers
        if user.is_staff:
            farmers = Farmer.objects.all()
        else:
            farmers = Farmer.objects.filter(registered_by=user)
        
        total_count = farmers.count()
        # Note: Farmer model might not have is_active field, so we count all
        active_count = total_count
        
        # Group by district
        by_district = dict(
            farmers.values('district')
            .annotate(count=Count('id'))
            .values_list('district', 'count')
        )
        
        # Group by education
        by_education = dict(
            farmers.values('education_level')
            .annotate(count=Count('id'))
            .values_list('education_level', 'count')
        )
        
        # Group by landholding size
        by_landholding = {
            'small (< 5 acres)': farmers.filter(total_land_area__lt=5).count(),
            'medium (5-25 acres)': farmers.filter(total_land_area__gte=5, total_land_area__lte=25).count(),
            'large (> 25 acres)': farmers.filter(total_land_area__gt=25).count(),
        }
        
        # Aggregate land area
        land_stats = farmers.aggregate(
            total_land=Sum('total_land_area'),
            avg_land=Avg('total_land_area')
        )
        
        return {
            'total_count': total_count,
            'active_count': active_count,
            'by_district': by_district,
            'by_education': by_education,
            'by_landholding': by_landholding,
            'total_land_area': float(land_stats['total_land'] or 0),
            'average_land_per_farmer': float(land_stats['avg_land'] or 0)
        }
    
    def _get_todays_activities(self, user):
        """Get today's activities"""
        today = timezone.localdate()
        
        # Count today's visits (meetings + field days + scheduled meetings)
        visits_today = (
            MeetingSchedule.objects.filter(staff=user, date=today).count() +
            Meeting.objects.filter(user_id=user, date__date=today, is_active=True).count() +
            FieldDay.objects.filter(user=user, date__date=today, is_active=True).count()
        )
        
        return {
            'visits_today': visits_today,
            'date': today.isoformat()
        }
    
    def _get_pending_sales_orders(self, user):
        """Get pending sales orders count"""
        return SalesOrder.objects.filter(staff=user, status='pending').count()


class SalesAnalyticsView(APIView):
    """
    Detailed Sales Analytics API
    Focus on sales vs achievement with various filters
    """
    permission_classes = [IsAuthenticated]
    
    @swagger_auto_schema(
        tags=["Analytics Dashboard"],
        operation_description="Get detailed sales vs achievement analytics with various filters",
        manual_parameters=[
            openapi.Parameter('emp_id', openapi.IN_QUERY, description="Employee ID", type=openapi.TYPE_INTEGER, required=False),
            openapi.Parameter('start_date', openapi.IN_QUERY, description="Start date (YYYY-MM-DD)", type=openapi.TYPE_STRING, required=False),
            openapi.Parameter('end_date', openapi.IN_QUERY, description="End date (YYYY-MM-DD)", type=openapi.TYPE_STRING, required=False),
            openapi.Parameter('region', openapi.IN_QUERY, description="Region filter", type=openapi.TYPE_STRING, required=False),
            openapi.Parameter('zone', openapi.IN_QUERY, description="Zone filter", type=openapi.TYPE_STRING, required=False),
            openapi.Parameter('territory', openapi.IN_QUERY, description="Territory filter", type=openapi.TYPE_STRING, required=False),
            openapi.Parameter('company', openapi.IN_QUERY, description="Company key", type=openapi.TYPE_STRING, required=False),
            openapi.Parameter('group_by_emp', openapi.IN_QUERY, description="Group by employee", type=openapi.TYPE_BOOLEAN, required=False),
            openapi.Parameter('in_millions', openapi.IN_QUERY, description="Convert to millions", type=openapi.TYPE_BOOLEAN, required=False),
        ],
        responses={
            200: openapi.Response(
                description="Sales analytics data",
                schema=SalesVsAchievementSerializer(many=True)
            )
        }
    )
    def get(self, request):
        """Get sales analytics"""
        dashboard_view = DashboardOverviewView()
        
        sales_data = dashboard_view._get_sales_vs_achievement(
            request.GET.get('emp_id', '').strip(),
            request.GET.get('start_date', '').strip(),
            request.GET.get('end_date', '').strip(),
            request.GET.get('company', '').strip(),
            request.GET.get('region', '').strip(),
            request.GET.get('zone', '').strip(),
            request.GET.get('territory', '').strip(),
            request.GET.get('in_millions', '').strip().lower() in ('true', '1', 'yes', 'y')
        )
        
        return Response(sales_data, status=status.HTTP_200_OK)


class CollectionAnalyticsView(APIView):
    """
    Detailed Collection Analytics API
    Focus on collection vs achievement with various filters
    """
    permission_classes = [IsAuthenticated]
    
    @swagger_auto_schema(
        tags=["SAP"],
        operation_summary="Collection Analytics - Payment Receipts vs Target",
        operation_description="""
        📊 **COLLECTION ANALYTICS** - Track actual payments received against collection targets
        
        🔑 **What This Endpoint Measures:**
        - ✅ **Collection Target**: Expected payment receipts from customers
        - ✅ **Collection Achievement**: Actual payments received/collected
        - ✅ **Focus**: Money IN (customer payments, receipts)
        - ✅ **Use Case**: Track cash flow, payment collection performance, receivables
        
        ⚠️ **Not For Sales Data** - Use `/sap/sales-vs-achievement-territory/` for sales orders/invoices
        
        Get detailed collection vs achievement analytics with hierarchical data (Region → Zone → Territory).
        
        **User & Employee Tracking:**
        - Response always includes `user_id` (portal user) and `employee_id` (from sales_profile)
        - Use `user_id` parameter to fetch data for a specific portal user (auto-fetches their employee_code)
        - Use `emp_id` parameter for direct SAP employee ID lookup
        
        **Date Filtering Options:**
        
        *Quick Period Filters (Recommended):*
        - `period=today` - Today's collection data only (Feb 3, 2026)
        - `period=monthly` - Current month to date (Feb 1 - Feb 3, 2026)
        - `period=yearly` - Current year to date (Jan 1 - Feb 3, 2026)
        
        *Custom Date Range:*
        - Use `start_date` and `end_date` for specific date ranges
        - Format: YYYY-MM-DD
        - Note: `period` parameter overrides custom dates if both provided
        
        **Parameter Priority:**
        1. **Employee Filter**: `emp_id` (highest) → `user_id` → authenticated user
        2. **Date Filter**: `period` (highest) → `start_date/end_date` → default range
        
        **Usage Examples:**
        
        *Quick Date Filters:*
        - Today's performance: `?database=4B-BIO&period=today`
        - This month's data: `?database=4B-BIO&period=monthly`
        - Year-to-date: `?database=4B-BIO&period=yearly`
        
        *User-Specific Queries:*
        - User's monthly data: `?database=4B-BIO&user_id=123&period=monthly`
        - Employee's today: `?database=4B-BIO&emp_id=456&period=today`
        
        *Custom Filters:*
        - Custom date range: `?database=4B-BIO&start_date=2026-01-01&end_date=2026-01-31`
        - Regional filter: `?database=4B-BIO&region=North&zone=Zone1&period=monthly`
        - In millions: `?database=4B-BIO&period=yearly&in_millions=true`
        
        *Combined Filters:*
        - `?database=4B-BIO&user_id=123&period=monthly&region=North&in_millions=true`
        - `?database=4B-BIO&emp_id=456&period=today&zone=Zone1`
        
        **Response Structure:**
        - `user_id`: Portal user ID
        - `employee_id`: Employee code from sales_profile
        - `data`: Hierarchical collection data (Region → Zone → Territory)
        - `totals`: Grand total target and achievement across all regions
        - `pagination`: Page information and navigation
        - `filters`: Applied filters for reference
        """,
        manual_parameters=[
            openapi.Parameter('database', openapi.IN_QUERY, description="Database/schema (e.g., 4B-BIO, 4B-ORANG, 4B-BIO_APP, 4B-ORANG_APP)", type=openapi.TYPE_STRING, required=False),
            openapi.Parameter('user_id', openapi.IN_QUERY, description="Portal User ID - Automatically fetches employee_code from user's sales_profile. Example: user_id=123", type=openapi.TYPE_INTEGER, required=False),
            openapi.Parameter('emp_id', openapi.IN_QUERY, description="SAP Employee ID - Direct employee ID, overrides user_id if both provided. Example: emp_id=456", type=openapi.TYPE_INTEGER, required=False),
            openapi.Parameter('period', openapi.IN_QUERY, description="Quick date filter - 'today' (current day), 'monthly' (current month), 'yearly' (current year). Overrides start_date/end_date if provided.", type=openapi.TYPE_STRING, enum=['today', 'monthly', 'yearly'], required=False),
            openapi.Parameter('start_date', openapi.IN_QUERY, description="Start date for collection period. Format: YYYY-MM-DD. Example: 2026-01-01. Ignored if 'period' is provided.", type=openapi.TYPE_STRING, required=False),
            openapi.Parameter('end_date', openapi.IN_QUERY, description="End date for collection period. Format: YYYY-MM-DD. Example: 2026-01-31. Ignored if 'period' is provided.", type=openapi.TYPE_STRING, required=False),
            openapi.Parameter('region', openapi.IN_QUERY, description="Filter by region name. Example: North, South", type=openapi.TYPE_STRING, required=False),
            openapi.Parameter('zone', openapi.IN_QUERY, description="Filter by zone name. Example: Zone1, Zone2", type=openapi.TYPE_STRING, required=False),
            openapi.Parameter('territory', openapi.IN_QUERY, description="Filter by territory name. Example: Territory1", type=openapi.TYPE_STRING, required=False),
            openapi.Parameter('group_by_date', openapi.IN_QUERY, description="Group results by date range. Default: false", type=openapi.TYPE_BOOLEAN, required=False),
            openapi.Parameter('ignore_emp_filter', openapi.IN_QUERY, description="Ignore employee filter to get all data (Admin/Manager use). Default: false", type=openapi.TYPE_BOOLEAN, required=False),
            openapi.Parameter('in_millions', openapi.IN_QUERY, description="Convert target and achievement values to millions for readability. Default: false", type=openapi.TYPE_BOOLEAN, required=False),
            openapi.Parameter('page', openapi.IN_QUERY, description="Page number for pagination. Default: 1", type=openapi.TYPE_INTEGER, default=1),
            openapi.Parameter('page_size', openapi.IN_QUERY, description="Number of items per page. Default: 10", type=openapi.TYPE_INTEGER, default=10),
        ],
        responses={
            200: openapi.Response(
                description="Collection analytics data with user tracking and hierarchical structure",
                schema=CollectionAnalyticsResponseSerializer,
                examples={
                    'application/json': {
                        'success': True,
                        'user_id': 123,
                        'employee_id': 'EMP001',
                        'count': 3,
                        'data': [
                            {
                                'name': 'North Region',
                                'target': 1500000.00,
                                'achievement': 1200000.00,
                                'from_date': '2026-01-01',
                                'to_date': '2026-01-31',
                                'zones': [
                                    {
                                        'name': 'Zone 1',
                                        'target': 800000.00,
                                        'achievement': 650000.00,
                                        'from_date': '2026-01-01',
                                        'to_date': '2026-01-31',
                                        'territories': [
                                            {
                                                'name': 'Territory A',
                                                'target': 400000.00,
                                                'achievement': 350000.00,
                                                'from_date': '2026-01-01',
                                                'to_date': '2026-01-31'
                                            }
                                        ]
                                    }
                                ]
                            }
                        ],
                        'pagination': {
                            'page': 1,
                            'num_pages': 1,
                            'has_next': False,
                            'has_prev': False,
                            'count': 3,
                            'page_size': 10
                        },
                        'filters': {
                            'company': '4B-BIO',
                            'region': '',
                            'zone': '',
                            'territory': ''
                        },
                        'totals': {
                            'target': 1500000.00,
                            'achievement': 1200000.00
                        }
                    }
                }
            )
        }
    )
    def get(self, request):
        """Get collection analytics"""
        try:
            # Load environment variables
            for path in [
                os.path.join(os.path.dirname(__file__), '..', 'sap_integration', '.env'),
                os.path.join(str(settings.BASE_DIR), '.env'),
                os.path.join(str(settings.BASE_DIR), '..', '.env'),
                os.path.join(os.getcwd(), '.env')
            ]:
                try:
                    _hana_load_env_file(path)
                except Exception:
                    pass
            
            # Connection config
            cfg = {
                'host': os.environ.get('HANA_HOST') or '',
                'port': os.environ.get('HANA_PORT') or '30015',
                'user': os.environ.get('HANA_USER') or '',
                'schema': os.environ.get('HANA_SCHEMA') or '4B-BIO_APP',
                'encrypt': os.environ.get('HANA_ENCRYPT') or '',
                'ssl_validate': os.environ.get('HANA_SSL_VALIDATE') or ''
            }
            
            # 1. Handle database parameter for schema selection
            db_param = (request.GET.get('database') or request.GET.get('company') or '').strip()
            
            # Get database options from Company model
            db_options = {}
            try:
                from FieldAdvisoryService.models import Company
                companies = Company.objects.filter(is_active=True)
                for company in companies:
                    # Map Company_name to schema name (name field)
                    db_options[company.Company_name] = company.name
            except Exception as e:
                # Fallback to settings if Company model is not available
                try:
                    db_setting = Setting.objects.filter(slug='SAP_COMPANY_DB').first()
                    if db_setting:
                        if isinstance(db_setting.value, dict):
                            db_options = db_setting.value
                        elif isinstance(db_setting.value, str):
                            import json
                            try:
                                db_options = json.loads(db_setting.value)
                            except:
                                pass
                except Exception:
                    pass
            
            # Clean options
            cleaned_options = {}
            for k, v in db_options.items():
                cleaned_options[str(k).strip().strip('"').strip("'")] = str(v).strip().strip('"').strip("'")
            db_options = cleaned_options
            
            # Select schema based on db_param
            if db_param and db_param in db_options:
                cfg['schema'] = db_options[db_param]
            elif db_param:
                # Try to find matching company by name field
                cfg['schema'] = db_param
            else:
                # Use first available company schema or default
                cfg['schema'] = list(db_options.values())[0] if db_options else '4B-BIO_APP'
            
            # Parameters
            period = (request.GET.get('period') or 'monthly').strip().lower()
            start_date = (request.GET.get('start_date') or '').strip()
            end_date = (request.GET.get('end_date') or '').strip()
            
            # Handle period parameter (overrides start_date/end_date)
            from datetime import datetime, date
            today = date.today()
            
            if period:
                if period == 'today':
                    start_date = today.strftime('%Y-%m-%d')
                    end_date = today.strftime('%Y-%m-%d')
                elif period == 'monthly':
                    # First day of current month to today
                    start_date = today.replace(day=1).strftime('%Y-%m-%d')
                    end_date = today.strftime('%Y-%m-%d')
                elif period == 'yearly':
                    # First day of current year to today
                    start_date = today.replace(month=1, day=1).strftime('%Y-%m-%d')
                    end_date = today.strftime('%Y-%m-%d')
            
            # If no period and no dates provided, default to today
            if not start_date and not end_date:
                start_date = today.strftime('%Y-%m-%d')
                end_date = today.strftime('%Y-%m-%d')
            
            region = (request.GET.get('region') or '').strip()
            zone = (request.GET.get('zone') or '').strip()
            territory = (request.GET.get('territory') or '').strip()
            in_millions = (request.GET.get('in_millions') or '').strip().lower() in ('true', '1', 'yes', 'y')
            group_by_date = (request.GET.get('group_by_date') or '').strip().lower() in ('true', '1', 'yes', 'y')
            ignore_emp_filter = (request.GET.get('ignore_emp_filter') or '').strip().lower() in ('true', '1', 'yes', 'y')
            
            # Handle user_id parameter to fetch employee_code
            user_id_param = request.GET.get('user_id', '').strip()
            emp_id_param = request.GET.get('emp_id', '').strip()
            
            emp_val = None
            employee_code_from_user = None
            
            # If user_id is provided, fetch employee_code from that user's sales_profile
            if user_id_param:
                try:
                    from accounts.models import User
                    user_id_int = int(user_id_param)
                    target_user = User.objects.select_related('sales_profile').get(id=user_id_int)
                    if hasattr(target_user, 'sales_profile') and target_user.sales_profile:
                        employee_code_from_user = target_user.sales_profile.employee_code
                        # Convert employee_code to integer if it's numeric
                        if employee_code_from_user:
                            try:
                                emp_val = int(employee_code_from_user)
                            except ValueError:
                                # If employee_code is not numeric, try to use it as-is
                                pass
                except Exception:
                    pass
            
            # emp_id parameter overrides user_id if both are provided
            if emp_id_param:
                try:
                    emp_val = int(emp_id_param)
                except Exception:
                    pass
            
            # If ignore_emp_filter is true, we pass emp_id=None to SAP function
            sap_emp_id = None if ignore_emp_filter else emp_val
            
            # Connect to HANA
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
                # Fix for self-signed certificates if ssl_validate is empty or false
                if not cfg['ssl_validate'] or str(cfg['ssl_validate']).strip().lower() not in ('true', '1', 'yes'):
                    kwargs['sslValidateCertificate'] = False
            
            conn = dbapi.connect(**kwargs)
            
            try:
                # Set schema
                if cfg['schema']:
                    cur = conn.cursor()
                    cur.execute(f'SET SCHEMA "{cfg["schema"]}"')
                    cur.close()
                
                # Fetch data using collection_vs_achievement function
                data = collection_vs_achievement(
                    conn,
                    emp_id=sap_emp_id,
                    region=region or None,
                    zone=zone or None,
                    territory=territory or None,
                    start_date=start_date or None,
                    end_date=end_date or None,
                    group_by_date=group_by_date,
                    ignore_emp_filter=ignore_emp_filter
                )
                
                # Process data
                if in_millions:
                    scaled = []
                    for row in (data or []):
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
                
                # Debug: Log first few rows to see what data we're getting
                if data and len(data) > 0:
                    print(f"\n=== DEBUG: First row from collection_vs_achievement ===")
                    print(f"Total rows returned: {len(data)}")
                    print(f"First row keys: {list(data[0].keys())}")
                    print(f"First row data: {data[0]}")
                    if len(data) > 1:
                        print(f"Second row data: {data[1]}")
                    print(f"=== END DEBUG ===")
                
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
                
                # Build Hierarchy (Region → Zone → Territory)
                hierarchy = {}
                for row in (data or []):
                    if not isinstance(row, dict):
                        continue
                    
                    reg = row.get('Region') or 'All Regions'
                    zon = row.get('Zone') or 'All Zones'
                    ter = row.get('TerritoryName') or row.get('Territory') or 'All Territories'
                    
                    # Clean the names to remove suffixes
                    reg = clean_geo_name(reg)
                    zon = clean_geo_name(zon)
                    ter = clean_geo_name(ter)
                    
                    target = 0.0
                    ach = 0.0
                    
                    try:
                        v = row.get('Collection_Target')
                        target = float(v or 0.0)
                    except Exception:
                        pass
                    
                    try:
                        v = row.get('Collection_Achievement')
                        ach = float(v or 0.0)
                    except Exception:
                        pass
                    
                    # Date handling
                    row_from = row.get('From_Date')
                    row_to = row.get('To_Date')
                    
                    if reg not in hierarchy:
                        hierarchy[reg] = {
                            'name': reg, 
                            'target': 0.0, 
                            'achievement': 0.0, 
                            'zones': {},
                            'from_date': row_from,
                            'to_date': row_to
                        }
                    
                    # Update Region dates
                    if row_from:
                        if not hierarchy[reg]['from_date'] or str(row_from) < str(hierarchy[reg]['from_date']):
                            hierarchy[reg]['from_date'] = row_from
                    if row_to:
                        if not hierarchy[reg]['to_date'] or str(row_to) > str(hierarchy[reg]['to_date']):
                            hierarchy[reg]['to_date'] = row_to
                    
                    hierarchy[reg]['target'] += target
                    hierarchy[reg]['achievement'] += ach
                    
                    if zon not in hierarchy[reg]['zones']:
                        hierarchy[reg]['zones'][zon] = {
                            'name': zon, 
                            'target': 0.0, 
                            'achievement': 0.0, 
                            'territories': {},
                            'from_date': row_from,
                            'to_date': row_to
                        }
                    
                    # Update Zone dates
                    if row_from:
                        if not hierarchy[reg]['zones'][zon]['from_date'] or str(row_from) < str(hierarchy[reg]['zones'][zon]['from_date']):
                            hierarchy[reg]['zones'][zon]['from_date'] = row_from
                    if row_to:
                        if not hierarchy[reg]['zones'][zon]['to_date'] or str(row_to) > str(hierarchy[reg]['zones'][zon]['to_date']):
                            hierarchy[reg]['zones'][zon]['to_date'] = row_to
                    
                    hierarchy[reg]['zones'][zon]['target'] += target
                    hierarchy[reg]['zones'][zon]['achievement'] += ach
                    
                    # Territory aggregation
                    if ter not in hierarchy[reg]['zones'][zon]['territories']:
                        hierarchy[reg]['zones'][zon]['territories'][ter] = {
                            'name': ter,
                            'target': 0.0,
                            'achievement': 0.0,
                            'from_date': row_from,
                            'to_date': row_to,
                        }
                    
                    t_data = hierarchy[reg]['zones'][zon]['territories'][ter]
                    t_data['target'] += target
                    t_data['achievement'] += ach
                    
                    # Update Territory dates
                    if row_from:
                        if not t_data['from_date'] or str(row_from) < str(t_data['from_date']):
                            t_data['from_date'] = row_from
                    if row_to:
                        if not t_data['to_date'] or str(row_to) > str(t_data['to_date']):
                            t_data['to_date'] = row_to
                            
                
                # Convert hierarchy to list
                final_list = []
                for r_name in sorted(hierarchy.keys()):
                    r_data = hierarchy[r_name]
                    zones_list = []
                    for z_name in sorted(r_data['zones'].keys()):
                        z_data = r_data['zones'][z_name]
                        
                        # Convert territories dict to list
                        territories_list = []
                        for t_name in sorted(z_data['territories'].keys()):
                            t_item = z_data['territories'][t_name]
                            # Rounding for territory aggregate
                            t_item['target'] = round(t_item['target'], 2)
                            t_item['achievement'] = round(t_item['achievement'], 2)
                            territories_list.append(t_item)
                            
                        z_data['territories'] = territories_list
                        zones_list.append(z_data)
                    r_data['zones'] = zones_list
                    final_list.append(r_data)
                
                # Rounding
                for r in final_list:
                    r['target'] = round(r['target'], 2)
                    r['achievement'] = round(r['achievement'], 2)
                    for z in r['zones']:
                        z['target'] = round(z['target'], 2)
                        z['achievement'] = round(z['achievement'], 2)
                
                # Calculate Grand Total
                grand_total_target = 0.0
                grand_total_achievement = 0.0
                for r in final_list:
                    grand_total_target += r['target']
                    grand_total_achievement += r['achievement']
                
                grand_total = {
                    'target': round(grand_total_target, 2),
                    'achievement': round(grand_total_achievement, 2)
                }
                
                # Pagination
                page_param = (request.GET.get('page') or '1').strip()
                page_size_param = (request.GET.get('page_size') or '').strip()
                
                try:
                    page_num = int(page_param) if page_param else 1
                except Exception:
                    page_num = 1
                
                default_page_size = 10
                try:
                    page_size = int(page_size_param) if page_size_param else default_page_size
                except Exception:
                    page_size = default_page_size
                
                from django.core.paginator import Paginator
                paginator = Paginator(list(final_list or []), page_size)
                
                try:
                    page_obj = paginator.page(page_num)
                    paged_rows = list(page_obj.object_list)
                except Exception:
                    paged_rows = list(final_list or [])
                    page_obj = None
                
                pagination = {
                    'page': (page_obj.number if page_obj else 1),
                    'num_pages': (paginator.num_pages if paginator else 1),
                    'has_next': (page_obj.has_next() if page_obj else False),
                    'has_prev': (page_obj.has_previous() if page_obj else False),
                    'next_page': ((page_obj.next_page_number() if page_obj and page_obj.has_next() else None)),
                    'prev_page': ((page_obj.previous_page_number() if page_obj and page_obj.has_previous() else None)),
                    'count': (paginator.count if paginator else len(final_list or [])),
                    'page_size': page_size
                }
                
                # Get user_id and employee_id only if explicitly provided
                user_id = None
                employee_id = None
                
                # Return the queried user's info, not the authenticated user making the request
                if user_id_param:
                    user_id = int(user_id_param) if user_id_param else None
                    employee_id = emp_val  # The employee code we fetched from the queried user
                elif emp_id_param:
                    employee_id = emp_val  # The employee ID that was provided
                
                return Response({
                    'success': True,
                    'user_id': user_id,
                    'employee_id': employee_id,
                    'count': (paginator.count if paginator else len(final_list or [])),
                    'data': paged_rows,
                    'pagination': pagination,
                    'filters': {
                        'company': db_param,
                        'region': region,
                        'zone': zone,
                        'territory': territory
                    },
                    'totals': grand_total
                }, status=status.HTTP_200_OK)
                
            finally:
                try:
                    conn.close()
                except Exception:
                    pass
                    
        except Exception as e:
            return Response({'success': False, 'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class FarmerAnalyticsView(APIView):
    """
    Detailed Farmer Analytics API
    Focus on farmer statistics and demographics
    """
    permission_classes = [IsAuthenticated]
    
    @swagger_auto_schema(
        tags=["Analytics Dashboard"],
        operation_description="Get detailed farmer statistics and demographics",
        manual_parameters=[
            openapi.Parameter('district', openapi.IN_QUERY, description="Filter by district", type=openapi.TYPE_STRING, required=False),
            openapi.Parameter('education_level', openapi.IN_QUERY, description="Filter by education level", type=openapi.TYPE_STRING, required=False),
            openapi.Parameter('min_land_area', openapi.IN_QUERY, description="Minimum land area", type=openapi.TYPE_NUMBER, required=False),
            openapi.Parameter('max_land_area', openapi.IN_QUERY, description="Maximum land area", type=openapi.TYPE_NUMBER, required=False),
        ],
        responses={
            200: openapi.Response(
                description="Farmer analytics data",
                schema=FarmerStatsSerializer
            )
        }
    )
    def get(self, request):
        """Get farmer analytics"""
        user = request.user
        dashboard_view = DashboardOverviewView()
        
        farmer_stats = dashboard_view._get_farmer_stats(user)
        
        # Apply additional filters if provided
        district = request.GET.get('district', '').strip()
        education_level = request.GET.get('education_level', '').strip()
        
        if district or education_level:
            # Re-filter farmers based on params
            if user.is_staff:
                farmers = Farmer.objects.all()
            else:
                farmers = Farmer.objects.filter(registered_by=user)
            
            if district:
                farmers = farmers.filter(district=district)
            if education_level:
                farmers = farmers.filter(education_level=education_level)
            
            # Recalculate stats
            farmer_stats['total_count'] = farmers.count()
            farmer_stats['active_count'] = farmers.filter(is_active=True).count()
        
        return Response(farmer_stats, status=status.HTTP_200_OK)


class PerformanceMetricsView(APIView):
    """
    Performance Metrics API
    Track key performance indicators over time
    """
    permission_classes = [IsAuthenticated]
    
    @swagger_auto_schema(
        tags=["Analytics Dashboard"],
        operation_description="Get performance metrics with historical comparison",
        manual_parameters=[
            openapi.Parameter('period', openapi.IN_QUERY, description="Period: today, week, month, quarter, year", type=openapi.TYPE_STRING, required=False),
        ],
        responses={
            200: openapi.Response(
                description="Performance metrics",
                schema=PerformanceMetricSerializer(many=True)
            )
        }
    )
    def get(self, request):
        """Get performance metrics"""
        user = request.user
        period = request.GET.get('period', 'month').lower()
        
        # Calculate date ranges
        today = timezone.localdate()
        if period == 'today':
            current_start = today
            previous_start = today - timedelta(days=1)
        elif period == 'week':
            current_start = today - timedelta(days=7)
            previous_start = today - timedelta(days=14)
        elif period == 'quarter':
            current_start = today - timedelta(days=90)
            previous_start = today - timedelta(days=180)
        elif period == 'year':
            current_start = today - timedelta(days=365)
            previous_start = today - timedelta(days=730)
        else:  # month
            current_start = today - timedelta(days=30)
            previous_start = today - timedelta(days=60)
        
        metrics = []
        
        # Metric 1: Visits
        current_visits = (
            MeetingSchedule.objects.filter(staff=user, date__gte=current_start, date__lte=today).count() +
            Meeting.objects.filter(user_id=user, date__date__gte=current_start, date__date__lte=today).count() +
            FieldDay.objects.filter(user=user, date__date__gte=current_start, date__date__lte=today).count()
        )
        previous_visits = (
            MeetingSchedule.objects.filter(staff=user, date__gte=previous_start, date__lt=current_start).count() +
            Meeting.objects.filter(user_id=user, date__date__gte=previous_start, date__date__lt=current_start).count() +
            FieldDay.objects.filter(user=user, date__date__gte=previous_start, date__date__lt=current_start).count()
        )
        
        metrics.append({
            'metric_name': 'Total Visits',
            'current_value': current_visits,
            'previous_value': previous_visits,
            'unit': 'visits',
            'trend': 'up' if current_visits > previous_visits else 'down' if current_visits < previous_visits else 'stable'
        })
        
        # Metric 2: Sales Orders
        current_orders = SalesOrder.objects.filter(
            staff=user, created_at__date__gte=current_start, created_at__date__lte=today
        ).count()
        previous_orders = SalesOrder.objects.filter(
            staff=user, created_at__date__gte=previous_start, created_at__date__lt=current_start
        ).count()
        
        metrics.append({
            'metric_name': 'Sales Orders Created',
            'current_value': current_orders,
            'previous_value': previous_orders,
            'unit': 'orders',
            'trend': 'up' if current_orders > previous_orders else 'down' if current_orders < previous_orders else 'stable'
        })
        
        # Metric 3: Farmers Registered
        current_farmers = Farmer.objects.filter(
            registered_by=user, registration_date__date__gte=current_start, registration_date__date__lte=today
        ).count()
        previous_farmers = Farmer.objects.filter(
            registered_by=user, registration_date__date__gte=previous_start, registration_date__date__lt=current_start
        ).count()
        
        metrics.append({
            'metric_name': 'Farmers Registered',
            'current_value': current_farmers,
            'previous_value': previous_farmers,
            'unit': 'farmers',
            'trend': 'up' if current_farmers > previous_farmers else 'down' if current_farmers < previous_farmers else 'stable'
        })
        
        return Response(metrics, status=status.HTTP_200_OK)
