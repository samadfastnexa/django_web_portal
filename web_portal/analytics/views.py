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
        
        # Initialize response data
        dashboard_data = {}
        
        # 1. Get Sales vs Achievement from SAP
        sales_data = self._get_sales_vs_achievement(
            emp_id_param, start_date_param, end_date_param, 
            company_param, region_param, zone_param, territory_param, in_millions
        )
        if sales_data:
            dashboard_data.update(sales_data)
        
        # 1b. Get Collection vs Achievement from SAP
        collection_data = self._get_collection_vs_achievement(
            emp_id_param, start_date_param, end_date_param, 
            company_param, region_param, zone_param, territory_param, in_millions,
            group_by_date=False, ignore_emp_filter=False
        )
        if collection_data:
            dashboard_data.update(collection_data)
        
        # 2. Get Farmer Statistics
        farmer_stats = self._get_farmer_stats(user)
        dashboard_data['farmer_stats'] = farmer_stats
        
        # 3. Get Today's Activities
        activity_data = self._get_todays_activities(user)
        dashboard_data.update(activity_data)
        
        # 4. Get Pending Sales Orders
        dashboard_data['pending_sales_orders'] = self._get_pending_sales_orders(user)
        
        return Response(dashboard_data, status=status.HTTP_200_OK)
    
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
                            schema = mapping.get(company.strip(), schema)
            except Exception:
                pass
            
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
        operation_description="Get detailed collection vs achievement analytics with various filters",
        manual_parameters=[
            openapi.Parameter('database', openapi.IN_QUERY, description="Database/schema (e.g. 4B-BIO-app)", type=openapi.TYPE_STRING, required=False),
            openapi.Parameter('emp_id', openapi.IN_QUERY, description="Employee ID", type=openapi.TYPE_INTEGER, required=False),
            openapi.Parameter('start_date', openapi.IN_QUERY, description="Start date (YYYY-MM-DD)", type=openapi.TYPE_STRING, required=False),
            openapi.Parameter('end_date', openapi.IN_QUERY, description="End date (YYYY-MM-DD)", type=openapi.TYPE_STRING, required=False),
            openapi.Parameter('region', openapi.IN_QUERY, description="Region filter", type=openapi.TYPE_STRING, required=False),
            openapi.Parameter('zone', openapi.IN_QUERY, description="Zone filter", type=openapi.TYPE_STRING, required=False),
            openapi.Parameter('territory', openapi.IN_QUERY, description="Territory filter", type=openapi.TYPE_STRING, required=False),
            openapi.Parameter('group_by_date', openapi.IN_QUERY, description="Group by date range", type=openapi.TYPE_BOOLEAN, required=False),
            openapi.Parameter('ignore_emp_filter', openapi.IN_QUERY, description="Ignore employee filter (Admin only)", type=openapi.TYPE_BOOLEAN, required=False),
            openapi.Parameter('in_millions', openapi.IN_QUERY, description="Convert to millions", type=openapi.TYPE_BOOLEAN, required=False),
            openapi.Parameter('page', openapi.IN_QUERY, description="Page number", type=openapi.TYPE_INTEGER, default=1),
            openapi.Parameter('page_size', openapi.IN_QUERY, description="Page size", type=openapi.TYPE_INTEGER, default=10),
        ],
        responses={
            200: openapi.Response(
                description="Collection analytics data",
                schema=CollectionAnalyticsResponseSerializer
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
            
            # Get database options from settings
            db_options = {}
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
            
            # Fallback
            if not db_options:
                db_options = {'4B-ORANG': '4B-ORANG_APP', '4B-BIO': '4B-BIO_APP'}
                
            # Clean options
            cleaned_options = {}
            for k, v in db_options.items():
                cleaned_options[str(k).strip().strip('"').strip("'")] = str(v).strip().strip('"').strip("'")
            db_options = cleaned_options
            
            if db_param and db_param in db_options:
                cfg['schema'] = db_options[db_param]
            elif db_param:
                norm = db_param.strip().upper().replace('-APP', '_APP')
                if '4B-BIO' in norm:
                    cfg['schema'] = '4B-BIO_APP'
                elif '4B-ORANG' in norm:
                    cfg['schema'] = '4B-ORANG_APP'
                else:
                    cfg['schema'] = db_param
            else:
                cfg['schema'] = '4B-BIO_APP'
            
            # Parameters
            start_date = (request.GET.get('start_date') or '').strip()
            end_date = (request.GET.get('end_date') or '').strip()
            region = (request.GET.get('region') or '').strip()
            zone = (request.GET.get('zone') or '').strip()
            territory = (request.GET.get('territory') or '').strip()
            in_millions = (request.GET.get('in_millions') or '').strip().lower() in ('true', '1', 'yes', 'y')
            group_by_date = (request.GET.get('group_by_date') or '').strip().lower() in ('true', '1', 'yes', 'y')
            ignore_emp_filter = (request.GET.get('ignore_emp_filter') or '').strip().lower() in ('true', '1', 'yes', 'y')
            emp_id_param = request.GET.get('emp_id', '').strip()
            
            emp_val = None
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
                
                # Fetch data using sales_vs_achievement_geo_inv (SAP endpoint logic)
                data = sales_vs_achievement_geo_inv(
                    conn,
                    emp_id=sap_emp_id,
                    region=region or None,
                    zone=zone or None,
                    territory=territory or None,
                    start_date=start_date or None,
                    end_date=end_date or None,
                    group_by_date=group_by_date,
                    group_by_emp=False 
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
                
                # Build Hierarchy
                hierarchy = {}
                for row in (data or []):
                    if not isinstance(row, dict):
                        continue
                    
                    reg = row.get('Region') or 'Unknown Region'
                    zon = row.get('Zone') or 'Unknown Zone'
                    ter = row.get('TerritoryName') or row.get('Territory') or 'Unknown Territory'
                    
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
                
                return Response({
                    'success': True,
                    'count': (paginator.count if paginator else len(final_list or [])),
                    'data': paged_rows,
                    'pagination': pagination,
                    'filters': {
                        'company': db_param,
                        'region': region,
                        'zone': zone,
                        'territory': territory
                    }
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
