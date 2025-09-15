from rest_framework import generics, viewsets, filters, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Q
from .models import Farmer, FarmingHistory
from .serializers import (
    FarmerSerializer, FarmerListSerializer, FarmerDetailSerializer,
    FarmerCreateUpdateSerializer, FarmingHistorySerializer
)
from .filters import FarmerFilter, FarmingHistoryFilter

from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

# ✅ Comprehensive Farmer ViewSet with Search and Filtering
class FarmerViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing farmers with comprehensive search and filtering capabilities.
    
    Provides:
    - List farmers with search and filtering
    - Create new farmers
    - Retrieve farmer details
    - Update farmer information
    - Delete farmers
    - Custom actions for statistics and farming history
    """
    queryset = Farmer.objects.all().select_related('registered_by').prefetch_related('farming_history')
    parser_classes = [MultiPartParser, FormParser]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_class = FarmerFilter
    search_fields = [
        'farmer_id', 'first_name', 'last_name', 'father_name',
        'primary_phone', 'email', 'village', 'district', 'province',
        'main_crops_grown', 'farming_methods', 'national_id'
    ]
    ordering_fields = [
        'registration_date', 'first_name', 'last_name', 'total_land_area',
        'farming_experience', 'years_of_farming', 'is_verified'
    ]
    ordering = ['-registration_date']
    
    def get_serializer_class(self):
        """Return appropriate serializer based on action"""
        if self.action == 'list':
            return FarmerListSerializer
        elif self.action in ['create', 'update', 'partial_update']:
            return FarmerCreateUpdateSerializer
        else:
            return FarmerDetailSerializer
    
    def get_queryset(self):
        """Optimize queryset based on action"""
        queryset = super().get_queryset()
        
        if self.action == 'list':
            # For list view, we don't need farming history
            return queryset.select_related('registered_by')
        else:
            # For detail views, include farming history
            return queryset.select_related('registered_by').prefetch_related('farming_history')
    
    @swagger_auto_schema(
        operation_description="Retrieve a searchable and filterable list of farmers",
        manual_parameters=[
            openapi.Parameter('search', openapi.IN_QUERY, description="Search across multiple fields", type=openapi.TYPE_STRING),
            openapi.Parameter('village', openapi.IN_QUERY, description="Filter by village", type=openapi.TYPE_STRING),
            openapi.Parameter('district', openapi.IN_QUERY, description="Filter by district", type=openapi.TYPE_STRING),
            openapi.Parameter('gender', openapi.IN_QUERY, description="Filter by gender", type=openapi.TYPE_STRING),
            openapi.Parameter('farming_experience', openapi.IN_QUERY, description="Filter by farming experience", type=openapi.TYPE_STRING),
            openapi.Parameter('is_verified', openapi.IN_QUERY, description="Filter by verification status", type=openapi.TYPE_BOOLEAN),
            openapi.Parameter('total_land_area_min', openapi.IN_QUERY, description="Minimum land area", type=openapi.TYPE_NUMBER),
            openapi.Parameter('total_land_area_max', openapi.IN_QUERY, description="Maximum land area", type=openapi.TYPE_NUMBER),
            openapi.Parameter('ordering', openapi.IN_QUERY, description="Order by field (prefix with - for descending)", type=openapi.TYPE_STRING),
        ],
        responses={
            200: FarmerListSerializer(many=True)
        },
        tags=["06. Farmers"]
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)
    
    @swagger_auto_schema(
        operation_description="Create a new farmer with detailed information",
        request_body=FarmerCreateUpdateSerializer,
        responses={
            201: FarmerDetailSerializer,
            400: 'Bad Request - Invalid data provided'
        },
        tags=["06. Farmers"]
    )
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        # Set the registered_by field to current user if available
        if hasattr(request, 'user') and request.user.is_authenticated:
            serializer.save(registered_by=request.user)
        else:
            serializer.save()
        
        # Return detailed serializer for response
        farmer = serializer.instance
        response_serializer = FarmerDetailSerializer(farmer)
        return Response(response_serializer.data, status=status.HTTP_201_CREATED)
    
    @swagger_auto_schema(
        operation_description="Retrieve detailed information of a specific farmer",
        responses={
            200: FarmerDetailSerializer,
            404: 'Farmer not found'
        },
        tags=["06. Farmers"]
    )
    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)
    
    @swagger_auto_schema(
        operation_description="Update farmer information",
        request_body=FarmerCreateUpdateSerializer,
        responses={
            200: FarmerDetailSerializer,
            400: 'Bad Request - Invalid data provided',
            404: 'Farmer not found'
        },
        tags=["06. Farmers"]
    )
    def update(self, request, *args, **kwargs):
        return super().update(request, *args, **kwargs)
    
    @swagger_auto_schema(
        operation_description="Partially update farmer information",
        request_body=FarmerCreateUpdateSerializer,
        responses={
            200: FarmerDetailSerializer,
            400: 'Bad Request - Invalid data provided',
            404: 'Farmer not found'
        },
        tags=["06. Farmers"]
    )
    def partial_update(self, request, *args, **kwargs):
        return super().partial_update(request, *args, **kwargs)
    
    @swagger_auto_schema(
        operation_description="Delete a farmer record",
        responses={
            204: 'Farmer deleted successfully',
            404: 'Farmer not found'
        },
        tags=["06. Farmers"]
    )
    def destroy(self, request, *args, **kwargs):
        return super().destroy(request, *args, **kwargs)
    
    @action(detail=True, methods=['get'])
    @swagger_auto_schema(
        operation_description="Get farming history for a specific farmer",
        responses={
            200: FarmingHistorySerializer(many=True),
            404: 'Farmer not found'
        },
        tags=["06. Farmers"]
    )
    def farming_history(self, request, pk=None):
        """Get farming history for a specific farmer"""
        farmer = self.get_object()
        history = farmer.farming_history.all().order_by('-year', '-season')
        serializer = FarmingHistorySerializer(history, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    @swagger_auto_schema(
        operation_description="Get farmer statistics and summary",
        responses={
            200: openapi.Response(
                description='Farmer statistics',
                examples={
                    'application/json': {
                        'total_farmers': 150,
                        'verified_farmers': 120,
                        'active_farmers': 140,
                        'total_land_area': 2500.5,
                        'average_land_per_farmer': 16.67,
                        'farmers_by_district': {
                            'Lahore': 50,
                            'Faisalabad': 30,
                            'Multan': 25
                        },
                        'farmers_by_experience': {
                            'beginner': 20,
                            'intermediate': 80,
                            'experienced': 50
                        }
                    }
                }
            )
        },
        tags=["06. Farmers"]
    )
    def statistics(self, request):
        """Get comprehensive farmer statistics"""
        from django.db.models import Count, Sum, Avg
        
        queryset = self.get_queryset()
        
        # Basic counts
        total_farmers = queryset.count()
        verified_farmers = queryset.filter(is_verified=True).count()
        active_farmers = queryset.filter(is_active=True).count()
        
        # Land statistics
        land_stats = queryset.aggregate(
            total_land=Sum('total_land_area'),
            average_land=Avg('total_land_area'),
            total_cultivated=Sum('cultivated_area'),
            average_cultivated=Avg('cultivated_area')
        )
        
        # Distribution by district
        farmers_by_district = dict(
            queryset.values('district')
            .annotate(count=Count('id'))
            .values_list('district', 'count')
        )
        
        # Distribution by experience
        farmers_by_experience = dict(
            queryset.values('farming_experience')
            .annotate(count=Count('id'))
            .values_list('farming_experience', 'count')
        )
        
        # Distribution by gender
        farmers_by_gender = dict(
            queryset.values('gender')
            .annotate(count=Count('id'))
            .values_list('gender', 'count')
        )
        
        return Response({
            'total_farmers': total_farmers,
            'verified_farmers': verified_farmers,
            'active_farmers': active_farmers,
            'total_land_area': land_stats['total_land'] or 0,
            'average_land_per_farmer': round(land_stats['average_land'] or 0, 2),
            'total_cultivated_area': land_stats['total_cultivated'] or 0,
            'average_cultivated_per_farmer': round(land_stats['average_cultivated'] or 0, 2),
            'farmers_by_district': farmers_by_district,
            'farmers_by_experience': farmers_by_experience,
            'farmers_by_gender': farmers_by_gender,
        })

# ✅ Farming History ViewSet
class FarmingHistoryViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing farming history records with search and filtering.
    
    Provides CRUD operations for farming history records with comprehensive
    filtering by farmer, year, season, crop, and financial metrics.
    """
    queryset = FarmingHistory.objects.all().select_related('farmer')
    serializer_class = FarmingHistorySerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_class = FarmingHistoryFilter
    search_fields = [
        'crop_name', 'farming_practices_used', 'challenges_faced',
        'notes', 'farmer__first_name', 'farmer__last_name', 'farmer__farmer_id'
    ]
    ordering_fields = [
        'year', 'season', 'crop_name', 'area_cultivated', 'total_yield',
        'yield_per_acre', 'total_income', 'profit_loss', 'created_at'
    ]
    ordering = ['-year', '-season']
    
    @swagger_auto_schema(
        operation_description="List farming history records with filtering",
        manual_parameters=[
            openapi.Parameter('farmer', openapi.IN_QUERY, description="Filter by farmer ID", type=openapi.TYPE_INTEGER),
            openapi.Parameter('year', openapi.IN_QUERY, description="Filter by year", type=openapi.TYPE_INTEGER),
            openapi.Parameter('season', openapi.IN_QUERY, description="Filter by season", type=openapi.TYPE_STRING),
            openapi.Parameter('crop_name', openapi.IN_QUERY, description="Filter by crop name", type=openapi.TYPE_STRING),
            openapi.Parameter('search', openapi.IN_QUERY, description="Search across multiple fields", type=openapi.TYPE_STRING),
            openapi.Parameter('year_from', openapi.IN_QUERY, description="Filter from year", type=openapi.TYPE_INTEGER),
            openapi.Parameter('year_to', openapi.IN_QUERY, description="Filter to year", type=openapi.TYPE_INTEGER),
            openapi.Parameter('profit_loss_min', openapi.IN_QUERY, description="Minimum profit/loss", type=openapi.TYPE_NUMBER),
            openapi.Parameter('profit_loss_max', openapi.IN_QUERY, description="Maximum profit/loss", type=openapi.TYPE_NUMBER),
        ],
        responses={
            200: FarmingHistorySerializer(many=True)
        },
        tags=["06. Farmers - History"]
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)
    
    @swagger_auto_schema(
        operation_description="Create a new farming history record",
        request_body=FarmingHistorySerializer,
        responses={
            201: FarmingHistorySerializer,
            400: 'Bad Request - Invalid data provided'
        },
        tags=["06. Farmers - History"]
    )
    def create(self, request, *args, **kwargs):
        return super().create(request, *args, **kwargs)
    
    @swagger_auto_schema(
        operation_description="Retrieve a specific farming history record",
        responses={
            200: FarmingHistorySerializer,
            404: 'Farming history record not found'
        },
        tags=["06. Farmers - History"]
    )
    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)
    
    @swagger_auto_schema(
        operation_description="Update a farming history record",
        request_body=FarmingHistorySerializer,
        responses={
            200: FarmingHistorySerializer,
            400: 'Bad Request - Invalid data provided',
            404: 'Farming history record not found'
        },
        tags=["06. Farmers - History"]
    )
    def update(self, request, *args, **kwargs):
        return super().update(request, *args, **kwargs)
    
    @swagger_auto_schema(
        operation_description="Partially update a farming history record",
        request_body=FarmingHistorySerializer,
        responses={
            200: FarmingHistorySerializer,
            400: 'Bad Request - Invalid data provided',
            404: 'Farming history record not found'
        },
        tags=["06. Farmers - History"]
    )
    def partial_update(self, request, *args, **kwargs):
        return super().partial_update(request, *args, **kwargs)
    
    @swagger_auto_schema(
        operation_description="Delete a farming history record",
        responses={
            204: 'Farming history record deleted successfully',
            404: 'Farming history record not found'
        },
        tags=["06. Farmers - History"]
    )
    def destroy(self, request, *args, **kwargs):
        return super().destroy(request, *args, **kwargs)


# ✅ Legacy views for backward compatibility
class FarmerListCreateView(generics.ListCreateAPIView):
    """Legacy view - use FarmerViewSet instead"""
    queryset = Farmer.objects.all()
    serializer_class = FarmerSerializer
    parser_classes = [MultiPartParser, FormParser]


class FarmerDetailView(generics.RetrieveUpdateDestroyAPIView):
    """Legacy view - use FarmerViewSet instead"""
    queryset = Farmer.objects.all()
    serializer_class = FarmerSerializer
    parser_classes = [MultiPartParser, FormParser]
