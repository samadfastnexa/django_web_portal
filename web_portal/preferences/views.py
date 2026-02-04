
from rest_framework.permissions import IsAuthenticated
from accounts.permissions import HasRolePermission
from rest_framework.views import APIView
from django.conf import settings
import requests  # ✅ Required to make the HTTP call
from rest_framework import viewsets
from .models import Setting
from .serializers import SettingSerializer
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from rest_framework.response import Response
from rest_framework import status
from FieldAdvisoryService.models import Zone, Territory
from FieldAdvisoryService.serializers import ZoneNestedSerializer, TerritoryNestedSerializer
from django.db.models import Q
from django.utils import timezone
from datetime import timedelta
from FieldAdvisoryService.models import MeetingSchedule, SalesOrder
from farmers.models import Farmer
from farmerMeetingDataEntry.models import Meeting, FieldDay
import os
from sap_integration.hana_connect import sales_vs_achievement_by_emp
from sap_integration.hana_connect import _load_env_file as _hana_load_env_file

class SettingViewSet(viewsets.ModelViewSet):
    queryset = Setting.objects.all()
    serializer_class = SettingSerializer
    # permission_classes = [IsAuthenticated]
    permission_classes = [IsAuthenticated, HasRolePermission]
    @swagger_auto_schema(
        operation_description="Create a new setting",
        tags=["26. Settings"],
        request_body=SettingSerializer,
        responses={
            201: 'Setting created successfully',
            400: 'Bad Request - Invalid data'
        }
    )
    def create(self, request, *args, **kwargs):
        return super().create(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_description="Retrieve a list of all user settings. Each setting contains configuration data for different application features.",
        responses={
            200: openapi.Response(
                description='List of settings',
                examples={
                    'application/json': [
                        {
                            'id': 1,
                            'user': 1,
                            'slug': 'company_timings',
                            'value': {
                                'opening-time': '9:00',
                                'closing-time': '6:00'
                            },
                            'created_at': '2024-01-15T10:30:00Z'
                        },
                        {
                            'id': 2,
                            'user': 1,
                            'slug': 'notification_preferences',
                            'value': {
                                'email_notifications': True,
                                'sms_notifications': False
                            },
                            'created_at': '2024-01-16T11:00:00Z'
                        }
                    ]
                }
            )
        },
        tags=["26. Settings"]
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    # @swagger_auto_schema(
    #     operation_description="Create a new setting",
    #     tags=["26. Settings"]
    # )
    # def create(self, request, *args, **kwargs):
    #     return super().create(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_description="Retrieve detailed information of a specific setting by its ID.",
        responses={
            200: openapi.Response(
                description='Setting details',
                examples={
                    'application/json': {
                        'id': 1,
                        'user': 1,
                        'slug': 'company_timings',
                        'value': {
                            'opening-time': '9:00',
                            'closing-time': '6:00'
                        },
                        'created_at': '2024-01-15T10:30:00Z',
                        'updated_at': '2024-01-15T10:30:00Z'
                    }
                }
            ),
            404: 'Setting not found'
        },
        tags=["26. Settings"]
    )
    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_description="Update all fields of an existing setting with new configuration data.",
        request_body=SettingSerializer,
        responses={
            200: 'Setting updated successfully',
            400: 'Bad Request - Invalid data',
            404: 'Setting not found'
        },
        tags=["26. Settings"]
    )
    def update(self, request, *args, **kwargs):
        return super().update(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_description="Partially update specific fields of a setting without affecting other fields.",
        request_body=SettingSerializer,
        responses={
            200: 'Setting updated successfully',
            400: 'Bad Request - Invalid data',
            404: 'Setting not found'
        },
        tags=["26. Settings"]
    )
    def partial_update(self, request, *args, **kwargs):
        return super().partial_update(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_description="Permanently delete a setting and all its configuration data.",
        responses={
            204: 'Setting deleted successfully',
            404: 'Setting not found',
            403: 'Forbidden - You can only delete your own settings'
        },
        tags=["26. Settings"]
    )
    def destroy(self, request, *args, **kwargs):
        return super().destroy(request, *args, **kwargs)
    

class WeatherTestView(APIView):
    # permission_classes = [IsAuthenticated]
    
    @swagger_auto_schema(
        manual_parameters=[
            openapi.Parameter(
                'q',
                openapi.IN_QUERY,
                description="Search by Zone/Territory name or latitude,longitude (decimal degrees). "
                           "Examples: 'MULTAN', 'DG Khan', 'Lahore' or '30.1575,71.5249' for coordinates",
                type=openapi.TYPE_STRING,
                required=True,
                examples={
                    "application/json": {
                        "MULTAN": "MULTAN",
                        "DG Khan": "DG Khan",
                        "Lahore": "Lahore",
                        "Karachi": "Karachi",
                        "Coordinates": "30.1575,71.5249"
                    }
                }
            )
        ],
        tags=["27. Weather"],
        responses={
            200: openapi.Response(
                description="Successful response with weather data",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'location': openapi.Schema(
                            type=openapi.TYPE_STRING,
                            description='Name of the found location (Zone or Territory)'
                        ),
                        'weather_location': openapi.Schema(
                            type=openapi.TYPE_STRING,
                            description='Actual location name used for weather data from WeatherAPI'
                        ),
                        'current_weather': openapi.Schema(
                            type=openapi.TYPE_OBJECT,
                            description='Current weather conditions from WeatherAPI.com',
                            properties={
                                'temperature': openapi.Schema(type=openapi.TYPE_STRING, description='Current temperature in Celsius'),
                                'condition': openapi.Schema(type=openapi.TYPE_STRING, description='Current weather condition'),
                                'humidity': openapi.Schema(type=openapi.TYPE_STRING, description='Current humidity percentage'),
                                'icon': openapi.Schema(type=openapi.TYPE_STRING, description='Weather icon path from WeatherAPI.com'),
                                'icon_url': openapi.Schema(type=openapi.TYPE_STRING, description='Full HTTPS URL to weather icon')
                            }
                        ),
                        'forecast': openapi.Schema(
                            type=openapi.TYPE_ARRAY,
                            description='3-day weather forecast from WeatherAPI.com',
                            items=openapi.Schema(
                                type=openapi.TYPE_OBJECT,
                                properties={
                                    'day': openapi.Schema(type=openapi.TYPE_STRING, description='Day number (Day 1, Day 2, Day 3)'),
                                    'temperature': openapi.Schema(type=openapi.TYPE_STRING, description='Maximum temperature for the day'),
                                    'condition': openapi.Schema(type=openapi.TYPE_STRING, description='Weather condition for the day'),
                                    'icon': openapi.Schema(type=openapi.TYPE_STRING, description='Weather icon path from WeatherAPI.com'),
                                    'icon_url': openapi.Schema(type=openapi.TYPE_STRING, description='Full HTTPS URL to weather icon')
                                }
                            )
                        )
                    }
                ),
                examples={
                    "application/json": {
                        "location": "Zone: MULTAN",
                        "weather_location": "Multan",
                        "current_weather": {
                            "temperature": "28°C",
                            "condition": "Partly cloudy",
                            "humidity": "62%",
                            "icon": "//cdn.weatherapi.com/weather/64x64/day/116.png",
                            "icon_url": "https://cdn.weatherapi.com/weather/64x64/day/116.png"
                        },
                        "forecast": [
                            {
                                "day": "Day 1",
                                "temperature": "30°C",
                                "condition": "Sunny",
                                "icon": "//cdn.weatherapi.com/weather/64x64/day/113.png",
                                "icon_url": "https://cdn.weatherapi.com/weather/64x64/day/113.png"
                            },
                            {
                                "day": "Day 2",
                                "temperature": "27°C",
                                "condition": "Light rain",
                                "icon": "//cdn.weatherapi.com/weather/64x64/day/296.png",
                                "icon_url": "https://cdn.weatherapi.com/weather/64x64/day/296.png"
                            },
                            {
                                "day": "Day 3",
                                "temperature": "29°C",
                                "condition": "Partly cloudy",
                                "icon": "//cdn.weatherapi.com/weather/64x64/day/116.png",
                                "icon_url": "https://cdn.weatherapi.com/weather/64x64/day/116.png"
                            }
                        ]
                    }
                }
            ),
            400: openapi.Response(
                description="Bad Request - Missing query parameter",
                examples={
                    "application/json": {
                        "error": "Please provide ?q=ZoneName, TerritoryName, or latitude,longitude"
                    }
                }
            ),
            404: openapi.Response(
                description="Not Found - Location not found",
                examples={
                    "application/json": {
                        "error": "No Zone/Territory found matching 'NonexistentLocation'"
                    }
                }
            )
        },
        operation_description="Get real-time weather information for a specific Zone, Territory, or coordinates using WeatherAPI.com. "
                             "Search by name using the 'q' parameter or provide latitude,longitude (decimal degrees). "
                             "The API will first check if the query is coordinates, then search for Zones, then Territories if no Zone is found, "
                             "then fetch current weather and 3-day forecast from WeatherAPI.com. "
                             "Examples: /api/weather/?q=MULTAN or /api/weather/?q=30.1575,71.5249"
    )
    def get(self, request, *args, **kwargs):
        from django.conf import settings
        import requests
        import re
        
        query = request.GET.get("q", "")

        if not query:
            return Response({"error": "Please provide ?q=ZoneName, TerritoryName, or latitude,longitude"}, status=400)

        # 🌍 Check if query is in latitude,longitude format (e.g., "48.8567,2.3508")
        lat_lon_pattern = r'^-?\d+\.?\d*,-?\d+\.?\d*$'
        if re.match(lat_lon_pattern, query.strip()):
            location_name = f"Coordinates: {query}"
            location_for_weather = query.strip()
        else:
            # 🔎 Search for Zone
            zone = Zone.objects.filter(name__icontains=query).first()
            location_for_weather = None

            if zone:
                location_name = f"Zone: {zone.name}"
                # Use the original query for weather API
                location_for_weather = query
            else:
                # 🔎 Search for Territory
                territory = Territory.objects.filter(name__icontains=query).select_related("zone").first()
                if territory:
                    location_name = f"Territory: {territory.name} (Zone: {territory.zone.name})"
                    # Use latitude,longitude if available, otherwise use the original query
                    if territory.latitude and territory.longitude:
                        location_for_weather = f"{territory.latitude},{territory.longitude}"
                    else:
                        location_for_weather = query
                else:
                    return Response({"error": f"No Zone/Territory found matching '{query}'"}, status=404)

        # 🌤️ Get real weather data from WeatherAPI.com
        try:
            api_key = settings.WEATHER_API_KEY
            
            # Debug: Print the location being used for weather API
            print(f"[DEBUG] Weather API - Location query: '{location_for_weather}'")
            print(f"[DEBUG] Weather API - Location name: '{location_name}'")
            
            url = f"http://api.weatherapi.com/v1/forecast.json?key={api_key}&q={location_for_weather}&days=3&aqi=no&alerts=no"
            print(f"[DEBUG] Weather API - Full URL: {url.replace(api_key, '***HIDDEN***')}")
            
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            weather_api_data = response.json()
            
            # Extract current weather
            current = weather_api_data.get("current", {})
            location_data = weather_api_data.get("location", {})
            forecast_data = weather_api_data.get("forecast", {}).get("forecastday", [])
            
            # Format current weather with icon
            current_weather = {
                "temperature": f"{current.get('temp_c', 'N/A')}°C",
                "condition": current.get("condition", {}).get("text", "Unknown"),
                "humidity": f"{current.get('humidity', 'N/A')}%",
                "icon": current.get("condition", {}).get("icon", ""),
                "icon_url": f"https:{current.get('condition', {}).get('icon', '')}" if current.get('condition', {}).get('icon') else ""
            }
            
            # Format 3-day forecast with icons
            forecast = []
            for i, day_data in enumerate(forecast_data[:3]):
                day_info = day_data.get("day", {})
                condition_info = day_info.get("condition", {})
                forecast.append({
                    "day": f"Day {i + 1}",
                    "temperature": f"{day_info.get('maxtemp_c', 'N/A')}°C",
                    "condition": condition_info.get("text", "Unknown"),
                    "icon": condition_info.get("icon", ""),
                    "icon_url": f"https:{condition_info.get('icon', '')}" if condition_info.get('icon') else ""
                })
            
            weather_data = {
                "location": location_name,
                "weather_location": location_data.get("name", location_for_weather),
                "current_weather": current_weather,
                "forecast": forecast
            }
            
            return Response(weather_data)
            
        except requests.exceptions.RequestException as e:
            return Response({
                "error": "Failed to fetch weather data",
                "details": str(e),
                "location": location_name
            }, status=503)
        except Exception as e:
            return Response({
                "error": "An unexpected error occurred",
                "details": str(e),
                "location": location_name
            }, status=500)
    
class AvailableLocationsView(APIView):
    @swagger_auto_schema(
        tags=["27. Weather"],
        responses={
            200: openapi.Response(
                description="List of all available Zones and Territories",
                examples={
                    "application/json": {
                        "zones": [
                            {"id": 1, "name": "MULTAN"},
                            {"id": 2, "name": "LAHORE"},
                            {"id": 3, "name": "KARACHI"}
                        ],
                        "territories": [
                            {"id": 1, "name": "DG Khan", "zone": "MULTAN"},
                            {"id": 2, "name": "Territory A", "zone": "LAHORE"},
                            {"id": 3, "name": "Territory B", "zone": "KARACHI"}
                        ]
                    }
                }
            )
        },
        operation_description="Get a list of all available Zones and Territories that can be used with the weather API."
    )
    def get(self, request, *args, **kwargs):
        zones = Zone.objects.all().values('id', 'name')
        territories = Territory.objects.select_related('zone').all()
        
        territory_list = []
        for territory in territories:
            territory_list.append({
                "id": territory.id,
                "name": territory.name,
                "zone": territory.zone.name
            })
            
        return Response({
            "zones": zones,
            "territories": territory_list
        })

class UserAnalyticsView(APIView):
    permission_classes = [IsAuthenticated]
    @swagger_auto_schema(
        tags=["27. Analytics"],
        operation_description="Get sales overview analytics for the authenticated user: Targets vs Achievements (optional), Today's Visits, Pending Sales Orders, and Total Farmers. Values include comparison against last month.",
        manual_parameters=[
            openapi.Parameter('emp_id', openapi.IN_QUERY, description="Employee ID to filter SAP sales overview", type=openapi.TYPE_INTEGER, required=False),
            openapi.Parameter('start_date', openapi.IN_QUERY, description="Start date YYYY-MM-DD (optional for SAP totals)", type=openapi.TYPE_STRING, required=False),
            openapi.Parameter('end_date', openapi.IN_QUERY, description="End date YYYY-MM-DD (optional for SAP totals)", type=openapi.TYPE_STRING, required=False),
            openapi.Parameter('company', openapi.IN_QUERY, description="Company key mapped to HANA schema via settings (e.g., 4B-BIO)", type=openapi.TYPE_STRING, required=False),
            openapi.Parameter('in_millions', openapi.IN_QUERY, description="Scale numeric values to millions", type=openapi.TYPE_BOOLEAN, required=False),
        ],
        responses={
            200: openapi.Response(
                description="Analytics overview for the user",
                examples={
                    "application/json": {
                        "todays_visits": {
                            "current_value": 5,
                            "last_month_value": 7
                        },
                        "pending_sales_orders": {
                            "current_value": 64,
                            "last_month_value": 60
                        },
                        "total_farmers": {
                            "current_value": 220,
                            "last_month_value": 210
                        },
                        "sales_target": {
                            "current_value": 1000000.00,
                            "last_month_value": 900000.00
                        },
                        "achievement": {
                            "current_value": 950000.00,
                            "last_month_value": 850000.00
                        }
                    }
                }
            )
        }
    )
    def get(self, request, *args, **kwargs):
        user = request.user
        today = timezone.localdate()
        last_month_day = today - timedelta(days=30)
        
        # Today's Visits (meetings + field days + scheduled meetings)
        visits_today = (
            MeetingSchedule.objects.filter(staff=user, date=today).count() +
            Meeting.objects.filter(user_id=user, date__date=today, is_active=True).count() +
            FieldDay.objects.filter(user=user, date__date=today, is_active=True).count()
        )
        visits_last_month = (
            MeetingSchedule.objects.filter(staff=user, date=last_month_day).count() +
            Meeting.objects.filter(user_id=user, date__date=last_month_day, is_active=True).count() +
            FieldDay.objects.filter(user=user, date__date=last_month_day, is_active=True).count()
        )
        
        # Pending Sales Orders (current vs created around last month day)
        pending_current = SalesOrder.objects.filter(staff=user, status='pending').count()
        pending_last_month = SalesOrder.objects.filter(
            staff=user, status='pending', created_at__date=last_month_day
        ).count()
        
        # Total Farmers (current total vs total as of last month day)
        total_farmers_current = Farmer.objects.filter(registered_by=user).count()
        total_farmers_last_month = Farmer.objects.filter(
            registered_by=user, registration_date__date__lte=last_month_day
        ).count()
        
        # Sales Target and Achievement (SAP) with optional emp_id filter
        emp_id_param = (self.request.GET.get('emp_id') or '').strip()

        start_date_param = (self.request.GET.get('start_date') or '').strip()
        end_date_param = (self.request.GET.get('end_date') or '').strip()
        company_param = (self.request.GET.get('company') or '').strip()
        in_millions_param = (self.request.GET.get('in_millions') or '').strip().lower()
        sales_target_current = None
        achievement_current = None
        sales_target_last = None
        achievement_last = None
        sales_combined = None
        company_options = []
        try:
            try:
                _hana_load_env_file(os.path.join(os.path.dirname(__file__), '..', 'sap_integration', '.env'))
            except Exception:
                pass
            try:
                _hana_load_env_file(os.path.join(str(settings.BASE_DIR), '.env'))
            except Exception:
                pass
            try:
                _hana_load_env_file(os.path.join(str(settings.BASE_DIR), '..', '.env'))
            except Exception:
                pass
            try:
                _hana_load_env_file(os.path.join(os.getcwd(), '.env'))
            except Exception:
                pass
            from hdbcli import dbapi
            host = os.environ.get('HANA_HOST') or ''
            port = os.environ.get('HANA_PORT') or '30015'
            user_name = os.environ.get('HANA_USER') or ''
            password = os.environ.get('HANA_PASSWORD', '')
            schema = os.environ.get('HANA_SCHEMA') or ''
            
            # Get company options from Company model (dynamic)
            try:
                from FieldAdvisoryService.models import Company
                companies = Company.objects.filter(is_active=True).order_by('Company_name')
                
                if companies.exists():
                    # Build options from Company model
                    # Key: Company_name (display name), Schema: name (schema field)
                    company_options = [
                        {
                            "key": company.Company_name.strip().strip('"').strip("'"),
                            "schema": company.name.strip().strip('"').strip("'")
                        }
                        for company in companies
                        if company.Company_name and company.name
                    ]
                    
                    # If company_param is provided, find matching schema
                    if company_param:
                        selected_key = company_param.strip().strip('"').strip("'")
                        matching_company = companies.filter(Company_name=selected_key).first()
                        if matching_company and matching_company.name:
                            schema = matching_company.name.strip().strip('"').strip("'")
            except Exception:
                pass
            
            # Fallback: Try to get from Settings if Company model didn't work
            if not company_options:
                try:
                    db_setting = Setting.objects.filter(slug='SAP_COMPANY_DB').first()
                    mapping = {}
                    if db_setting:
                        if isinstance(db_setting.value, dict):
                            mapping = db_setting.value
                        elif isinstance(db_setting.value, str):
                            import json as _json
                            try:
                                mapping = _json.loads(db_setting.value)
                            except Exception:
                                mapping = {}
                    if mapping:
                        company_options = [
                            {"key": k.strip().strip('"').strip("'"), "schema": str(v).strip().strip('"').strip("'")}
                            for k, v in mapping.items()
                        ]
                        if company_param:
                            selected_key = company_param.strip().strip('"').strip("'")
                            val = mapping.get(selected_key)
                            if isinstance(val, str) and val.strip() != '':
                                schema = val.strip().strip('"').strip("'")
                except Exception:
                    pass
            encrypt = (str(os.environ.get('HANA_ENCRYPT') or '').strip().lower() in ('true','1','yes'))
            ssl_validate = (str(os.environ.get('HANA_SSL_VALIDATE') or '').strip().lower() in ('true','1','yes'))
            kwargs = {'address': host, 'port': int(port), 'user': user_name or '', 'password': password or ''}
            if encrypt:
                kwargs['encrypt'] = True
                if os.environ.get('HANA_SSL_VALIDATE'):
                    kwargs['sslValidateCertificate'] = ssl_validate
            conn = dbapi.connect(**kwargs)
            if schema:
                cur = conn.cursor()
                cur.execute(f'SET SCHEMA "{schema}"')
                cur.close()
            emp_val = None
            if emp_id_param:
                try:
                    emp_val = int(emp_id_param)
                except Exception:
                    emp_val = None
            data = sales_vs_achievement_by_emp(conn, emp_val, None, None, None, (start_date_param or None), (end_date_param or None))
            st_sum = 0.0
            ac_sum = 0.0
            min_f = None
            max_t = None
            for r in (data or []):
                if isinstance(r, dict):
                    try:
                        st_sum += float(r.get('SALES_TARGET') or 0.0)
                    except Exception:
                        pass
                    try:
                        ac_sum += float(r.get('ACCHIVEMENT') or r.get('ACHIEVEMENT') or 0.0)
                    except Exception:
                        pass
                    try:
                        f = r.get('F_REFDATE')
                        t = r.get('T_REFDATE')
                        if f and (min_f is None or str(f) < str(min_f)):
                            min_f = f
                        if t and (max_t is None or str(t) > str(max_t)):
                            max_t = t
                    except Exception:
                        pass
            sales_target_current = st_sum
            achievement_current = ac_sum
            
            sales_combined = {
                "EMPID": emp_val if emp_val is not None else 0,
                "TERRITORYID": 0,
                "TERRITORYNAME": "All Territories",
                "SALES_TARGET": st_sum,
                "ACCHIVEMENT": ac_sum,
                "F_REFDATE": min_f,
                "T_REFDATE": max_t
            }

            lm_start = (last_month_day - timedelta(days=29)).isoformat()
            lm_end = last_month_day.isoformat()
            data_last = sales_vs_achievement_by_emp(conn, emp_val, None, None, None, lm_start, lm_end)
            st_last = 0.0
            ac_last = 0.0
            for r in (data_last or []):
                if isinstance(r, dict):
                    try:
                        st_last += float(r.get('SALES_TARGET') or 0.0)
                    except Exception:
                        pass
                    try:
                        ac_last += float(r.get('ACCHIVEMENT') or r.get('ACHIEVEMENT') or 0.0)
                    except Exception:
                        pass
            sales_target_last = st_last
            achievement_last = ac_last
            
            # Add last month comparison to sales_combined
            sales_combined["SALES_TARGET_LAST_MONTH"] = st_last
            sales_combined["ACCHIVEMENT_LAST_MONTH"] = ac_last

            if in_millions_param in ('true','1','yes','y'):
                try:
                    sales_target_current = round((float(sales_target_current or 0.0) / 1000000.0), 2)
                    achievement_current = round((float(achievement_current or 0.0) / 1000000.0), 2)
                    sales_target_last = round((float(sales_target_last or 0.0) / 1000000.0), 2)
                    achievement_last = round((float(achievement_last or 0.0) / 1000000.0), 2)
                    if sales_combined is not None:
                        sales_combined["SALES_TARGET"] = sales_target_current
                        sales_combined["ACCHIVEMENT"] = achievement_current
                        sales_combined["SALES_TARGET_LAST_MONTH"] = sales_target_last
                        sales_combined["ACCHIVEMENT_LAST_MONTH"] = achievement_last
                except Exception:
                    pass
            try:
                conn.close()
            except Exception:
                pass
        except Exception:
            pass
        
        analytics = {
            "todays_visits": {
                "current_value": visits_today,
                "last_month_value": visits_last_month
            },
            "pending_sales_orders": {
                "current_value": pending_current,
                "last_month_value": pending_last_month
            },
            "total_farmers": {
                "current_value": total_farmers_current,
                "last_month_value": total_farmers_last_month
            }
        }
        # Always include sales_combined and company_options
        if sales_combined is None:
            sales_combined = {
                "EMPID": 0,
                "TERRITORYID": 0,
                "TERRITORYNAME": "All Territories",
                "SALES_TARGET": 0,
                "ACCHIVEMENT": 0,
                "F_REFDATE": None,
                "T_REFDATE": None,
                "SALES_TARGET_LAST_MONTH": 0,
                "ACCHIVEMENT_LAST_MONTH": 0
            }
        analytics["sales_combined"] = sales_combined
        analytics["company_options"] = company_options  # Will be empty list if not populated
        analytics["selected_company"] = company_param or ''
        
        return Response(analytics)
