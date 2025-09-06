
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
    
# ✅ Place the function here, above your view
# def get_zone_territory_choices():
#     choices = []
#     zones = Zone.objects.prefetch_related('territories').all()
    
#     for zone in zones:
#         # Add zone itself
#         choices.append((zone.name, zone.name))
        
#         # Add territories under the zone
#         for terr in zone.territories.all():
#             choices.append((f"{zone.name} -> {terr.name}", f"{zone.name} -> {terr.name}"))
    
#     return choices
# # Example list of cities for dropdown
# CITIES = ["Karachi", "Lahore", "Islamabad", "Multan", "Peshawar", "Quetta"]

# class WeatherTestView(APIView):
#     """
#     Fetch current weather + 3-day forecast for a city.
#     Query param: ?q=CityName
#     """

#     @swagger_auto_schema(
#         manual_parameters=[
#             openapi.Parameter(
#                 name="q",
#                 in_=openapi.IN_QUERY,
#                 type=openapi.TYPE_STRING,
#                 description="City to get weather for",
#                 enum=CITIES  # dropdown options
#             )
#         ],
#         responses={200: "Current weather + 3-day forecast"}
#     )
#     def get(self, request):
#         city = request.query_params.get('q', 'Lahore')
#         api_key = settings.WEATHER_API_KEY
#         url = f"http://api.weatherapi.com/v1/forecast.json?key={api_key}&q={city}&days=3&aqi=no&alerts=no"

#         try:
#             response = requests.get(url)
#             data = response.json()

#             # Current weather
#             current = {
#                 "temperature_c": data["current"]["temp_c"],
#                 "condition": data["current"]["condition"]["text"],
#                 "humidity": data["current"]["humidity"],
#                 "wind_kph": data["current"]["wind_kph"],
#             }

#             # 3-day forecast
#             forecast_days = []
#             for day in data["forecast"]["forecastday"]:
#                 forecast_days.append({
#                     "date": day["date"],
#                     "max_temp_c": day["day"]["maxtemp_c"],
#                     "min_temp_c": day["day"]["mintemp_c"],
#                     "condition": day["day"]["condition"]["text"],
#                     "chance_of_rain": day["day"].get("daily_chance_of_rain"),
#                 })

#             return Response({
#                 "city": data["location"]["name"],
#                 "region": data["location"]["region"],
#                 "country": data["location"]["country"],
#                 "localtime": data["location"]["localtime"],
#                 "current": current,
#                 "forecast": forecast_days
#             }, status=status.HTTP_200_OK)

#         except Exception as e:
#             return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class WeatherTestView(APIView):
    # permission_classes = [IsAuthenticated]
    
    @swagger_auto_schema(
        manual_parameters=[
            openapi.Parameter(
                'q',
                openapi.IN_QUERY,
                description="Search by Zone or Territory name (typeahead style). Examples: 'MULTAN', 'DG Khan', 'Lahore', 'Territory A'",
                type=openapi.TYPE_STRING,
                required=True,
                examples={
                    "application/json": {
                        "MULTAN": "MULTAN",
                        "DG Khan": "DG Khan",
                        "Lahore": "Lahore",
                        "Karachi": "Karachi"
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
                        'current_weather': openapi.Schema(
                            type=openapi.TYPE_OBJECT,
                            description='Current weather conditions',
                            properties={
                                'temperature': openapi.Schema(type=openapi.TYPE_STRING),
                                'condition': openapi.Schema(type=openapi.TYPE_STRING),
                                'humidity': openapi.Schema(type=openapi.TYPE_STRING)
                            }
                        ),
                        'forecast': openapi.Schema(
                            type=openapi.TYPE_ARRAY,
                            description='Weather forecast for upcoming days',
                            items=openapi.Schema(
                                type=openapi.TYPE_OBJECT,
                                properties={
                                    'day': openapi.Schema(type=openapi.TYPE_STRING),
                                    'temperature': openapi.Schema(type=openapi.TYPE_STRING),
                                    'condition': openapi.Schema(type=openapi.TYPE_STRING)
                                }
                            )
                        )
                    }
                ),
                examples={
                    "application/json": {
                        "location": "Zone: MULTAN",
                        "current_weather": {
                            "temperature": "32°C",
                            "condition": "Sunny",
                            "humidity": "45%"
                        },
                        "forecast": [
                            {
                                "day": "Day 1",
                                "temperature": "34°C",
                                "condition": "Partly Cloudy"
                            },
                            {
                                "day": "Day 2",
                                "temperature": "31°C",
                                "condition": "Rain Showers"
                            },
                            {
                                "day": "Day 3",
                                "temperature": "33°C",
                                "condition": "Sunny"
                            }
                        ]
                    }
                }
            ),
            400: openapi.Response(
                description="Bad Request - Missing query parameter",
                examples={
                    "application/json": {
                        "error": "Please provide ?q=ZoneName or TerritoryName"
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
        operation_description="Get weather information for a specific Zone or Territory. "
                             "Search by name using the 'q' parameter. "
                             "The API will first search for Zones, then Territories if no Zone is found. "
                             "Example: /api/weather/?q=MULTAN"
    )
    def get(self, request, *args, **kwargs):
        query = request.GET.get("q", "")

        if not query:
            return Response({"error": "Please provide ?q=ZoneName or TerritoryName"}, status=400)

        # 🔎 Search for Zone
        zone = Zone.objects.filter(name__icontains=query).first()

        if zone:
            location_name = f"Zone: {zone.name}"
        else:
            # 🔎 Search for Territory
            territory = Territory.objects.filter(name__icontains=query).select_related("zone").first()
            if territory:
                location_name = f"Territory: {territory.name} (Zone: {territory.zone.name})"
            else:
                return Response({"error": f"No Zone/Territory found matching '{query}'"}, status=404)

        # ✅ Dummy weather data
        weather_data = {
            "location": location_name,
            "current_weather": {
                "temperature": "32°C",
                "condition": "Sunny",
                "humidity": "45%"
            },
            "forecast": [
                {"day": "Day 1", "temperature": "34°C", "condition": "Partly Cloudy"},
                {"day": "Day 2", "temperature": "31°C", "condition": "Rain Showers"},
                {"day": "Day 3", "temperature": "33°C", "condition": "Sunny"}
            ]
        }

        return Response(weather_data)
    
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