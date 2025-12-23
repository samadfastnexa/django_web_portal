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
    FarmerStatsSerializer,
    TargetSerializer,
    PerformanceMetricSerializer
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
                if ssl_validate:
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
