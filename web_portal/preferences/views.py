from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import PermissionDenied
from django.db import models

from .models import UserSetting
from .serializers import UserSettingSerializer

from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

from rest_framework.views import APIView
from django.conf import settings
import requests  # ✅ Required to make the HTTP call
class UserSettingListCreateView(generics.ListCreateAPIView):
    serializer_class = UserSettingSerializer
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_description="List user-specific and global settings. Global settings are listed first.",
        responses={200: openapi.Response("Success", UserSettingSerializer(many=True))}
    )
    def get(self, request, *args, **kwargs):
        return self.list(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_description="Create a new setting. Use `is_global=true` to create a global setting (superuser only).",
        request_body=UserSettingSerializer,
        responses={201: UserSettingSerializer}
    )
    def post(self, request, *args, **kwargs):
        return self.create(request, *args, **kwargs)

    def get_queryset(self):
        global_settings = UserSetting.objects.filter(user__isnull=True)
        user_settings = UserSetting.objects.filter(user=self.request.user)
        return global_settings.union(user_settings).order_by('slug', 'user_id')

    def perform_create(self, serializer):
        if self.request.data.get('is_global', False):
            if not self.request.user.is_superuser:
                raise PermissionDenied("Only superusers can create global settings")
            serializer.save(user=None)
        else:
            serializer.save(user=self.request.user)

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        global_settings = []
        user_settings = []

        for setting in queryset:
            serialized_data = self.get_serializer(setting).data
            if setting.user is None:
                serialized_data['type'] = 'global'
                global_settings.append(serialized_data)
            else:
                serialized_data['type'] = 'user'
                user_settings.append(serialized_data)

        return Response({
            'global_settings': global_settings,
            'user_settings': user_settings,
            'count': len(global_settings) + len(user_settings)
        })


class GlobalSettingListCreateView(generics.ListCreateAPIView):
    serializer_class = UserSettingSerializer
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_description="List global settings only (superusers only).",
        responses={200: openapi.Response("Success", UserSettingSerializer(many=True))}
    )
    def get(self, request, *args, **kwargs):
        return self.list(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_description="Create a global setting (superusers only).",
        request_body=UserSettingSerializer,
        responses={201: UserSettingSerializer}
    )
    def post(self, request, *args, **kwargs):
        return self.create(request, *args, **kwargs)

    def get_queryset(self):
        return UserSetting.objects.filter(user__isnull=True)

    def perform_create(self, serializer):
        if not self.request.user.is_superuser:
            raise PermissionDenied("Only superusers can manage global settings")
        serializer.save(user=None)

    def get_permissions(self):
        if self.request.user.is_authenticated and self.request.user.is_superuser:
            return [IsAuthenticated()]
        else:
            raise PermissionDenied("Only superusers can access global settings")


class UserSpecificSettingView(generics.ListCreateAPIView):
    serializer_class = UserSettingSerializer
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_description="List user-specific settings only.",
        responses={200: openapi.Response("Success", UserSettingSerializer(many=True))}
    )
    def get(self, request, *args, **kwargs):
        return self.list(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_description="Create a user-specific setting.",
        request_body=UserSettingSerializer,
        responses={201: UserSettingSerializer}
    )
    def post(self, request, *args, **kwargs):
        return self.create(request, *args, **kwargs)

    def get_queryset(self):
        return UserSetting.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class SettingsView(generics.ListCreateAPIView):
    serializer_class = UserSettingSerializer
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        manual_parameters=[
            openapi.Parameter(
                'type', openapi.IN_QUERY, description="Filter by type: global, user, or all",
                type=openapi.TYPE_STRING, enum=['global', 'user', 'all']
            )
        ],
        operation_description="Unified endpoint to fetch all, global, or user settings.",
        responses={200: openapi.Response("Success", UserSettingSerializer(many=True))}
    )
    def get(self, request, *args, **kwargs):
        return self.list(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_description="Create a setting (global if is_global=true, user-specific otherwise).",
        request_body=UserSettingSerializer,
        responses={201: UserSettingSerializer}
    )
    def post(self, request, *args, **kwargs):
        return self.create(request, *args, **kwargs)

    def get_queryset(self):
        setting_type = self.request.query_params.get('type', 'all')

        if setting_type == 'global':
            return UserSetting.objects.filter(user__isnull=True)
        elif setting_type == 'user':
            return UserSetting.objects.filter(user=self.request.user)
        else:
            global_settings = UserSetting.objects.filter(user__isnull=True)
            user_settings = UserSetting.objects.filter(user=self.request.user)
            return global_settings.union(user_settings)

    def perform_create(self, serializer):
        is_global = self.request.data.get('is_global', False)

        if is_global:
            if not self.request.user.is_superuser:
                raise PermissionDenied("Only superusers can create global settings")
            serializer.save(user=None)
        else:
            serializer.save(user=self.request.user)

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)

        for item in serializer.data:
            if 'user' in item and item['user'] is None:
                item['type'] = 'global'
            else:
                item['type'] = 'user'

        return Response({
            'results': serializer.data,
            'count': len(serializer.data)
        })

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