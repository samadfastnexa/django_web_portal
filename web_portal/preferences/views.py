
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

class SettingViewSet(viewsets.ModelViewSet):
    queryset = Setting.objects.all()
    serializer_class = SettingSerializer
    # permission_classes = [IsAuthenticated]
    permission_classes = [IsAuthenticated, HasRolePermission]
    @swagger_auto_schema(
        operation_description="Create a new setting",
        tags=["Settings"],
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'user': openapi.Schema(type=openapi.TYPE_INTEGER, example=1),
                'slug': openapi.Schema(type=openapi.TYPE_STRING, example='company_timmings'),
                'value': openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    example={
                        "opening-time": "9:00",
                        "closing-time": "6:00"
                    }
                ),
            },
            required=['user', 'slug', 'value']
        )
    )
    def create(self, request, *args, **kwargs):
        return super().create(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_description="List all settings",
        tags=["Settings"]
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    # @swagger_auto_schema(
    #     operation_description="Create a new setting",
    #     tags=["Settings"]
    # )
    # def create(self, request, *args, **kwargs):
    #     return super().create(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_description="Retrieve a setting",
        tags=["Settings"]
    )
    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_description="Update a setting",
        tags=["Settings"]
    )
    def update(self, request, *args, **kwargs):
        return super().update(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_description="Partially update a setting",
        tags=["Settings"]
    )
    def partial_update(self, request, *args, **kwargs):
        return super().partial_update(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_description="Delete a setting",
        tags=["Settings"]
    )
    def destroy(self, request, *args, **kwargs):
        return super().destroy(request, *args, **kwargs)
    
class WeatherTestView(APIView):
    def get(self, request):
        city = request.query_params.get('city', 'Lahore')
        api_key = settings.WEATHER_API_KEY
        url = f"http://api.weatherapi.com/v1/current.json?key={api_key}&q={city}"

        try:
            response = requests.get(url)
            data = response.json()
            return Response(data)
        except Exception as e:
            return Response({"error": str(e)}, status=500)