# farm/views.py
from rest_framework import viewsets, status, permissions, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from rest_framework.parsers import JSONParser, MultiPartParser, FormParser
from django_filters.rest_framework import DjangoFilterBackend
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from drf_yasg.inspectors import SwaggerAutoSchema
from django.utils import timezone
from django.db.models import Q
from .models import Farm
from .serializers import (
    FarmSerializer, 
    FarmCreateSerializer, 
    FarmUpdateSerializer, 
    FarmListSerializer
)
from accounts.permissions import IsOwnerOrAdmin, HasRolePermission


class FormDataAutoSchema(SwaggerAutoSchema):
    """Custom schema class to properly handle form data in Swagger UI"""
    
    def get_request_body_schema(self, serializer):
        """Override to ensure form data is properly displayed"""
        if hasattr(self.view, 'parser_classes'):
            parser_classes = getattr(self.view, 'parser_classes', [])
            if any('FormParser' in str(parser) or 'MultiPartParser' in str(parser) for parser in parser_classes):
                # For form data endpoints, let DRF handle the schema automatically
                return None
        return super().get_request_body_schema(serializer)
    
    def get_consumes(self):
        """Ensure all supported content types are listed"""
        consumes = super().get_consumes()
        if hasattr(self.view, 'parser_classes'):
            parser_classes = getattr(self.view, 'parser_classes', [])
            content_types = []
            for parser in parser_classes:
                if 'JSONParser' in str(parser):
                    content_types.append('application/json')
                elif 'MultiPartParser' in str(parser):
                    content_types.append('multipart/form-data')
                elif 'FormParser' in str(parser):
                    content_types.append('application/x-www-form-urlencoded')
            if content_types:
                return content_types
        return consumes or ['application/json']


class FarmViewSet(viewsets.ModelViewSet):
    """
    API endpoint for managing Farms.

    - Admin can see all farms
    - Normal users can only see their own farms
    - Supports JSON, form data, and multipart form data
    """
    serializer_class = FarmSerializer
    permission_classes = [permissions.IsAuthenticated]
    parser_classes = [JSONParser, MultiPartParser, FormParser]
    queryset = Farm.objects.all().order_by("-created_at")

    # ✅ Filters & Searching
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ["soil_type", "owner", "created_at", "is_active"]
    search_fields = ["name", "address", "soil_type", "owner__username"]
    ordering_fields = ["created_at", "size", "name"]

    def get_serializer_class(self):
        """Return appropriate serializer based on action"""
        if self.action == 'create':
            return FarmCreateSerializer
        elif self.action in ['update', 'partial_update']:
            return FarmUpdateSerializer
        elif self.action == 'list':
            return FarmListSerializer
        return FarmSerializer

    def get_queryset(self):
        """Filter queryset based on user permissions and query parameters"""
        user = self.request.user
        queryset = Farm.objects.filter(deleted_at__isnull=True)
        
        # Admin users can see all farms, regular users only see their own
        if not user.is_staff:
            queryset = queryset.filter(owner=user)
        
        # Filter by active status
        is_active = self.request.query_params.get('is_active')
        if is_active is not None:
            queryset = queryset.filter(is_active=is_active.lower() == 'true')
        
        # Search functionality
        search = self.request.query_params.get('search')
        if search:
            queryset = queryset.filter(
                Q(name__icontains=search) |
                Q(address__icontains=search) |
                Q(soil_type__icontains=search) |
                Q(owner__username__icontains=search)
            )
        
        # Filter by owner
        owner_id = self.request.query_params.get('owner')
        if owner_id:
            queryset = queryset.filter(owner_id=owner_id)
        
        # Filter by soil type
        soil_type = self.request.query_params.get('soil_type')
        if soil_type:
            queryset = queryset.filter(soil_type__iexact=soil_type)
        
        return queryset.order_by('-created_at')

    # ✅ Swagger documentation
    @swagger_auto_schema(
        operation_description="Get list of farms with filtering and search capabilities",
        operation_summary="List Farms",
        manual_parameters=[
            openapi.Parameter(
                'is_active',
                openapi.IN_QUERY,
                description="Filter by active status (true/false)",
                type=openapi.TYPE_BOOLEAN,
                required=False
            ),
            openapi.Parameter(
                'search',
                openapi.IN_QUERY,
                description="Search in farm name, address, soil type, or owner username",
                type=openapi.TYPE_STRING,
                required=False
            ),
            openapi.Parameter(
                'owner',
                openapi.IN_QUERY,
                description="Filter by owner ID",
                type=openapi.TYPE_INTEGER,
                required=False
            ),
            openapi.Parameter(
                'soil_type',
                openapi.IN_QUERY,
                description="Filter by soil type (clay, sandy, silty, peaty, chalky, loamy)",
                type=openapi.TYPE_STRING,
                enum=['clay', 'sandy', 'silty', 'peaty', 'chalky', 'loamy'],
                required=False
            ),
            openapi.Parameter(
                'page',
                openapi.IN_QUERY,
                description="Page number for pagination",
                type=openapi.TYPE_INTEGER,
                required=False
            ),
            openapi.Parameter(
                'page_size',
                openapi.IN_QUERY,
                description="Number of results per page (max 100)",
                type=openapi.TYPE_INTEGER,
                required=False
            )
        ],
        responses={
            200: openapi.Response(
                description="List of farms",
                schema=FarmListSerializer(many=True)
            ),
            401: openapi.Response(description="Authentication required")
        },
        tags=['28.Farms']
    )
    def list(self, request, *args, **kwargs):
        """Get paginated list of farms with filtering"""
        return super().list(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_description="Create a new farm with comprehensive validation. Supports JSON (application/json), multipart form data (multipart/form-data), and URL-encoded form data (application/x-www-form-urlencoded). Use the 'Try it out' button and select the appropriate Content-Type in the request.",
        operation_summary="Create Farm",
        auto_schema=FormDataAutoSchema,
        consumes=['application/json', 'multipart/form-data', 'application/x-www-form-urlencoded'],
        responses={
            201: openapi.Response(
                description="Farm created successfully",
                schema=FarmSerializer,
                examples={
                    "application/json": {
                        "id": 1,
                        "name": "Green Valley Farm",
                        "owner": 1,
                        "owner_name": "john_doe",
                        "address": "123 Farm Road",
                        "size": 25.5,
                        "soil_type": "loamy",
                        "is_active": True,
                        "status_display": "Active"
                    },
                    "multipart/form-data": {
                        "id": 1,
                        "name": "Green Valley Farm",
                        "owner": 1,
                        "owner_name": "john_doe",
                        "address": "123 Farm Road",
                        "size": 25.5,
                        "soil_type": "loamy",
                        "is_active": True,
                        "status_display": "Active"
                    },
                    "application/x-www-form-urlencoded": {
                        "id": 1,
                        "name": "Green Valley Farm",
                        "owner": 1,
                        "owner_name": "john_doe",
                        "address": "123 Farm Road",
                        "size": 25.5,
                        "soil_type": "loamy",
                        "is_active": True,
                        "status_display": "Active"
                    }
                }
            ),
            400: openapi.Response(
                description="Bad request - validation errors",
                examples={
                    "application/json": {
                        "name": ["This field is required."],
                        "size": ["Farm size must be greater than 0"],
                        "soil_type": ["Select a valid choice."]
                    },
                    "multipart/form-data": {
                        "name": ["This field is required."],
                        "size": ["Farm size must be greater than 0"],
                        "soil_type": ["Select a valid choice."]
                    },
                    "application/x-www-form-urlencoded": {
                        "name": ["This field is required."],
                        "size": ["Farm size must be greater than 0"],
                        "soil_type": ["Select a valid choice."]
                    }
                }
            ),
            401: openapi.Response(description="Authentication required"),
            403: openapi.Response(description="Permission denied")
        },
        tags=['28.Farms']
    )
    def create(self, request, *args, **kwargs):
        """Create a new farm with validation"""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        farm = serializer.save()
        
        # Return full farm data
        response_serializer = FarmSerializer(farm)
        return Response(response_serializer.data, status=status.HTTP_201_CREATED)

    @swagger_auto_schema(
        operation_description="Get detailed information about a specific farm",
        operation_summary="Get Farm Details",
        responses={
            200: openapi.Response(
                description="Farm details",
                schema=FarmSerializer
            ),
            404: openapi.Response(description="Farm not found"),
            401: openapi.Response(description="Authentication required")
        },
        tags=['28.Farms']
    )
    def retrieve(self, request, *args, **kwargs):
        """Get detailed farm information"""
        return super().retrieve(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_description="Update farm information (full update). Supports JSON (application/json), multipart form data (multipart/form-data), and URL-encoded form data (application/x-www-form-urlencoded).",
        operation_summary="Update Farm",
        auto_schema=FormDataAutoSchema,
        consumes=['application/json', 'multipart/form-data', 'application/x-www-form-urlencoded'],
        responses={
            200: openapi.Response(
                description="Farm updated successfully",
                schema=FarmSerializer,
                examples={
                    "application/json": {
                        "id": 1,
                        "name": "Updated Farm Name",
                        "owner": 1,
                        "owner_name": "john_doe",
                        "address": "456 New Farm Road",
                        "size": 30.0,
                        "soil_type": "clay",
                        "is_active": True,
                        "status_display": "Active"
                    }
                }
            ),
            400: openapi.Response(
                description="Bad request - validation errors",
                examples={
                    "application/json": {
                        "name": ["This field is required."],
                        "size": ["Farm size must be greater than 0"],
                        "soil_type": ["Select a valid choice."]
                    }
                }
            ),
            404: openapi.Response(description="Farm not found"),
            401: openapi.Response(description="Authentication required"),
            403: openapi.Response(description="Permission denied")
        },
        tags=['28.Farms']
    )
    def update(self, request, *args, **kwargs):
        """Update farm with full data"""
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        farm = serializer.save()
        
        # Return full farm data
        response_serializer = FarmSerializer(farm)
        return Response(response_serializer.data)

    @swagger_auto_schema(
        operation_description="Partially update farm information. Supports JSON (application/json), multipart form data (multipart/form-data), and URL-encoded form data (application/x-www-form-urlencoded).",
        operation_summary="Partial Update Farm",
        auto_schema=FormDataAutoSchema,
        consumes=['application/json', 'multipart/form-data', 'application/x-www-form-urlencoded'],
        responses={
            200: openapi.Response(
                description="Farm updated successfully",
                schema=FarmSerializer,
                examples={
                    "application/json": {
                        "id": 1,
                        "name": "Partially Updated Farm",
                        "owner": 1,
                        "owner_name": "john_doe",
                        "address": "123 Farm Road",
                        "size": 25.5,
                        "soil_type": "sandy",
                        "is_active": False,
                        "status_display": "Inactive"
                    }
                }
            ),
            400: openapi.Response(
                description="Bad request - validation errors",
                examples={
                    "application/json": {
                        "size": ["Farm size must be greater than 0"],
                        "soil_type": ["Select a valid choice."]
                    }
                }
            ),
            404: openapi.Response(description="Farm not found"),
            401: openapi.Response(description="Authentication required"),
            403: openapi.Response(description="Permission denied")
        },
        tags=['28.Farms']
    )
    def partial_update(self, request, *args, **kwargs):
        """Partially update farm data"""
        kwargs['partial'] = True
        return self.update(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_description="Soft delete a farm (sets deleted_at timestamp and is_active to False). The farm will be hidden from normal listings but can be restored later.",
        operation_summary="Soft Delete Farm",
        responses={
            204: openapi.Response(description="Farm soft deleted successfully"),
            404: openapi.Response(description="Farm not found"),
            401: openapi.Response(description="Authentication required"),
            403: openapi.Response(description="Permission denied")
        },
        tags=['28.Farms']
    )
    def destroy(self, request, *args, **kwargs):
        """Soft delete a farm instead of hard delete"""
        instance = self.get_object()
        instance.soft_delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @swagger_auto_schema(
        operation_description="Restore a previously soft-deleted farm. This will set deleted_at to null and is_active to true, making the farm visible again in normal listings.",
        operation_summary="Restore Deleted Farm",
        responses={
            200: openapi.Response(
                description="Farm restored successfully",
                schema=FarmSerializer,
                examples={
                    "application/json": {
                        "id": 1,
                        "name": "Green Valley Farm",
                        "is_active": True,
                        "deleted_at": None,
                        "status_display": "Active"
                    }
                }
            ),
            404: openapi.Response(
                description="Farm not found",
                examples={
                    "application/json": {
                        "detail": "Farm not found."
                    }
                }
            ),
            400: openapi.Response(
                description="Farm is not deleted",
                examples={
                    "application/json": {
                        "detail": "Farm is not deleted."
                    }
                }
            ),
            401: openapi.Response(description="Authentication required"),
            403: openapi.Response(description="Permission denied")
        },
        tags=['28.Farms']
    )
    @action(detail=True, methods=['post'])
    def restore(self, request, pk=None):
        """Restore a soft-deleted farm"""
        try:
            # Get the farm including soft-deleted ones
            farm = Farm.objects.get(pk=pk)
            if not farm.is_deleted:
                return Response(
                    {"detail": "Farm is not deleted."},
                    status=status.HTTP_400_BAD_REQUEST
                )
            farm.restore()
            serializer = self.get_serializer(farm)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except Farm.DoesNotExist:
            return Response(
                {"detail": "Farm not found."},
                status=status.HTTP_404_NOT_FOUND
            )

    @swagger_auto_schema(
        operation_description="Get all farms including soft-deleted ones. This endpoint is restricted to administrators and shows the complete farm database including deleted records.",
        operation_summary="List All Farms (Including Deleted)",
        manual_parameters=[
            openapi.Parameter(
                'include_deleted',
                openapi.IN_QUERY,
                description="Include soft-deleted farms (true/false)",
                type=openapi.TYPE_BOOLEAN,
                default=True,
                required=False
            ),
            openapi.Parameter(
                'status',
                openapi.IN_QUERY,
                description="Filter by status (active, inactive, deleted, all)",
                type=openapi.TYPE_STRING,
                enum=['active', 'inactive', 'deleted', 'all'],
                required=False
            ),
            openapi.Parameter(
                'search',
                openapi.IN_QUERY,
                description="Search in farm name, address, soil type, or owner username",
                type=openapi.TYPE_STRING,
                required=False
            )
        ],
        responses={
            200: openapi.Response(
                description="List of all farms including deleted ones",
                schema=FarmSerializer(many=True),
                examples={
                    "application/json": [
                        {
                            "id": 1,
                            "name": "Active Farm",
                            "status_display": "Active",
                            "is_active": True,
                            "deleted_at": None
                        },
                        {
                            "id": 2,
                            "name": "Deleted Farm",
                            "status_display": "Deleted",
                            "is_active": False,
                            "deleted_at": "2024-01-15T10:30:00Z"
                        }
                    ]
                }
            ),
            401: openapi.Response(description="Authentication required"),
            403: openapi.Response(
                description="Admin permission required",
                examples={
                    "application/json": {
                        "detail": "You do not have permission to perform this action."
                    }
                }
            )
        },
        tags=['28.Farms', 'Admin']
    )
    @action(detail=False, methods=['get'], permission_classes=[IsAdminUser])
    def all_including_deleted(self, request):
        """List all farms including soft-deleted ones (Admin only)"""
        queryset = Farm.objects.all()
        
        # Filter by status
        status_filter = request.query_params.get('status')
        if status_filter == 'active':
            queryset = queryset.filter(is_active=True, deleted_at__isnull=True)
        elif status_filter == 'inactive':
            queryset = queryset.filter(is_active=False, deleted_at__isnull=True)
        elif status_filter == 'deleted':
            queryset = queryset.filter(deleted_at__isnull=False)
        
        # Search functionality
        search = request.query_params.get('search')
        if search:
            queryset = queryset.filter(
                Q(name__icontains=search) |
                Q(address__icontains=search) |
                Q(soil_type__icontains=search) |
                Q(owner__username__icontains=search)
            )
        
        queryset = queryset.order_by('-created_at')
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)
