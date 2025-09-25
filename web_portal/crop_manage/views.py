from rest_framework import viewsets
from rest_framework.parsers import MultiPartParser, FormParser
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from .models import Crop, CropStage
from .serializers import CropSerializer, CropStageSerializer


class CropViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing crops with their stages.
    Supports form data, multipart, and JSON formats.
    """
    queryset = Crop.objects.all()
    serializer_class = CropSerializer
    parser_classes = [MultiPartParser, FormParser]

    def get_view_name(self):
        return "Crop Management"

    def get_view_description(self, html=False):
        return "Manage crops and their cultivation stages"

    @swagger_auto_schema(
        operation_description="Retrieve a list of all crops with their stages",
        tags=['crop_manage'],
        responses={
            200: openapi.Response(
                description="List of crops retrieved successfully",
                schema=CropSerializer(many=True)
            )
        }
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_description="Create a new crop with stages using form data format. Use nested notation for stages: stages[0][stage_name], stages[0][days_after_sowing], etc. Example form data: name=Rice, variety=Basmati-385, season=Kharif, stages[0][stage_name]=Transplanting, stages[0][days_after_sowing]=25, stages[0][brand]=Syngenta, stages[0][active_ingredient]=Chlorpyrifos, stages[0][dose_per_acre]=500ml, stages[0][purpose]=Pest control and nutrient management",
        tags=['crop_manage'],
        consumes=['application/x-www-form-urlencoded', 'multipart/form-data'],
        responses={
            201: openapi.Response(
                description="Crop created successfully",
                schema=CropSerializer
            ),
            400: openapi.Response(description="Bad request - validation errors")
        }
    )
    def create(self, request, *args, **kwargs):
        return super().create(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_description="Retrieve a specific crop by ID",
        tags=['crop_manage'],
        responses={
            200: openapi.Response(
                description="Crop retrieved successfully",
                schema=CropSerializer
            ),
            404: openapi.Response(description="Crop not found")
        }
    )
    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_description="Update a crop and its stages using form data format. Use nested notation for stages: stages[0][stage_name], stages[0][days_after_sowing], etc.",
        tags=['crop_manage'],
        consumes=['application/x-www-form-urlencoded', 'multipart/form-data'],
        responses={
            200: openapi.Response(
                description="Crop updated successfully",
                schema=CropSerializer
            ),
            400: openapi.Response(description="Bad request - validation errors"),
            404: openapi.Response(description="Crop not found")
        }
    )
    def update(self, request, *args, **kwargs):
        return super().update(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_description="Partially update a crop using form data format",
        tags=['crop_manage'],
        consumes=['application/x-www-form-urlencoded', 'multipart/form-data'],
        responses={
            200: openapi.Response(
                description="Crop partially updated successfully",
                schema=CropSerializer
            ),
            400: openapi.Response(description="Bad request - validation errors"),
            404: openapi.Response(description="Crop not found")
        }
    )
    def partial_update(self, request, *args, **kwargs):
        return super().partial_update(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_description="Delete a crop and all its stages",
        tags=['crop_manage'],
        responses={
            204: openapi.Response(description="Crop deleted successfully"),
            404: openapi.Response(description="Crop not found")
        }
    )
    def destroy(self, request, *args, **kwargs):
        return super().destroy(request, *args, **kwargs)


class CropStageViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing individual crop stages.
    Supports form data, multipart, and JSON formats.
    """
    queryset = CropStage.objects.all()
    serializer_class = CropStageSerializer
    parser_classes = [MultiPartParser, FormParser]

    def get_view_name(self):
        return "Crop Stage Management"

    def get_view_description(self, html=False):
        return "Manage individual crop cultivation stages"

    @swagger_auto_schema(
        operation_description="Retrieve a list of all crop stages",
        tags=['crop_manage'],
        responses={
            200: openapi.Response(
                description="List of crop stages retrieved successfully",
                schema=CropStageSerializer(many=True)
            )
        }
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_description="Create a new crop stage using form data format. Example form data: crop=1, stage_name=Germination, days_after_sowing=7, brand=Mahyco, active_ingredient=Thiamethoxam, dose_per_acre=100g, purpose=Seed treatment for early pest protection",
        tags=['crop_manage'],
        consumes=['application/x-www-form-urlencoded', 'multipart/form-data'],
        responses={
            201: openapi.Response(
                description="Crop stage created successfully",
                schema=CropStageSerializer
            ),
            400: openapi.Response(description="Bad request - validation errors")
        }
    )
    def create(self, request, *args, **kwargs):
        return super().create(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_description="Retrieve a specific crop stage by ID",
        tags=['crop_manage'],
        responses={
            200: openapi.Response(
                description="Crop stage retrieved successfully",
                schema=CropStageSerializer
            ),
            404: openapi.Response(description="Crop stage not found")
        }
    )
    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_description="Update a crop stage using form data format",
        tags=['crop_manage'],
        consumes=['application/x-www-form-urlencoded', 'multipart/form-data'],
        responses={
            200: openapi.Response(
                description="Crop stage updated successfully",
                schema=CropStageSerializer
            ),
            400: openapi.Response(description="Bad request - validation errors"),
            404: openapi.Response(description="Crop stage not found")
        }
    )
    def update(self, request, *args, **kwargs):
        return super().update(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_description="Partially update a crop stage using form data format",
        tags=['crop_manage'],
        consumes=['application/x-www-form-urlencoded', 'multipart/form-data'],
        responses={
            200: openapi.Response(
                description="Crop stage partially updated successfully",
                schema=CropStageSerializer
            ),
            400: openapi.Response(description="Bad request - validation errors"),
            404: openapi.Response(description="Crop stage not found")
        }
    )
    def partial_update(self, request, *args, **kwargs):
        return super().partial_update(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_description="Delete a crop stage",
        tags=['crop_manage'],
        responses={
            204: openapi.Response(description="Crop stage deleted successfully"),
            404: openapi.Response(description="Crop stage not found")
        }
    )
    def destroy(self, request, *args, **kwargs):
        return super().destroy(request, *args, **kwargs)
