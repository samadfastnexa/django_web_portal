from rest_framework import generics
from rest_framework.parsers import MultiPartParser, FormParser
from .models import Farmer
from .serializers import FarmerSerializer

from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

# ✅ List and Create Farmers
class FarmerListCreateView(generics.ListCreateAPIView):
    queryset = Farmer.objects.all()
    serializer_class = FarmerSerializer
    parser_classes = [MultiPartParser, FormParser]

    @swagger_auto_schema(
        operation_description="Retrieve a paginated list of all registered farmers with their location data",
        responses={
            200: openapi.Response(
                description='List of farmers',
                examples={
                    'application/json': {
                        'count': 2,
                        'next': None,
                        'previous': None,
                        'results': [
                            {
                                'id': 1,
                                'name': 'John Smith',
                                'current_latitude': '31.520370',
                                'current_longitude': '74.358749',
                                'farm_latitude': '31.521000',
                                'farm_longitude': '74.359000'
                            },
                            {
                                'id': 2,
                                'name': 'Ahmed Ali',
                                'current_latitude': '31.582045',
                                'current_longitude': '74.329376',
                                'farm_latitude': '31.583000',
                                'farm_longitude': '74.330000'
                            }
                        ]
                    }
                }
            )
        },
        tags=["06. Farmers"]
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_description="Register a new farmer with their personal and location information",
        request_body=FarmerSerializer,
        responses={
            201: openapi.Response(
                description='Farmer created successfully',
                schema=FarmerSerializer,
                examples={
                    'application/json': {
                        'id': 3,
                        'name': 'Muhammad Hassan',
                        'current_latitude': '31.520370',
                        'current_longitude': '74.358749',
                        'farm_latitude': '31.521000',
                        'farm_longitude': '74.359000'
                    }
                }
            ),
            400: 'Bad Request - Invalid data provided'
        },
        tags=["06. Farmers"],
        consumes=['multipart/form-data', 'application/x-www-form-urlencoded']
    )
    def post(self, request, *args, **kwargs):
        return super().post(request, *args, **kwargs)

# ✅ Retrieve, Update, and Delete a Single Farmer
class FarmerDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Farmer.objects.all()
    serializer_class = FarmerSerializer
    parser_classes = [MultiPartParser, FormParser]

    @swagger_auto_schema(
        operation_description="Retrieve detailed information of a specific farmer by their unique ID",
        responses={
            200: openapi.Response(
                description='Farmer details',
                examples={
                    'application/json': {
                        'id': 1,
                        'name': 'John Smith',
                        'current_latitude': '31.520370',
                        'current_longitude': '74.358749',
                        'farm_latitude': '31.521000',
                        'farm_longitude': '74.359000'
                    }
                }
            ),
            404: 'Farmer not found'
        },
        tags=["06. Farmers"]
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_description="Update all information of a specific farmer (full update)",
        request_body=FarmerSerializer,
        responses={
            200: openapi.Response(
                description='Farmer updated successfully',
                examples={
                    'application/json': {
                        'id': 1,
                        'name': 'John Smith Updated',
                        'current_latitude': '31.525000',
                        'current_longitude': '74.360000',
                        'farm_latitude': '31.526000',
                        'farm_longitude': '74.361000'
                    }
                }
            ),
            404: 'Farmer not found',
            400: 'Bad Request - Invalid data provided'
        },
        tags=["06. Farmers"],
        consumes=['multipart/form-data', 'application/x-www-form-urlencoded']
    )
    def put(self, request, *args, **kwargs):
        return super().put(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_description="Partially update specific fields of a farmer (only provided fields will be updated)",
        request_body=FarmerSerializer,
        responses={
            200: openapi.Response(
                description='Farmer updated successfully',
                examples={
                    'application/json': {
                        'id': 1,
                        'name': 'Updated Name',
                        'current_latitude': '31.525000',
                        'current_longitude': '74.360000',
                        'farm_latitude': '31.521000',
                        'farm_longitude': '74.359000'
                    }
                }
            ),
            404: 'Farmer not found',
            400: 'Bad Request - Invalid data provided'
        },
        tags=["06. Farmers"],
        consumes=['multipart/form-data', 'application/x-www-form-urlencoded']
    )
    def patch(self, request, *args, **kwargs):
        return super().patch(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_description="Permanently delete a farmer record from the system",
        responses={
            204: 'Farmer deleted successfully',
            404: 'Farmer not found'
        },
        tags=["06. Farmers"]
    )
    def delete(self, request, *args, **kwargs):
        return super().delete(request, *args, **kwargs)
