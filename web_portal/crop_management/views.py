from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Q, Avg, Sum, Count
from django.utils.translation import gettext_lazy as _
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from drf_yasg.inspectors import SwaggerAutoSchema


class FormDataAutoSchema(SwaggerAutoSchema):
    """Custom schema to handle form data in Swagger UI"""
    
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

from .models import Crop, CropVariety, YieldData, FarmingPractice, CropResearch
from .serializers import (
    CropSerializer, CropDetailSerializer, CropSummarySerializer,
    CropVarietySerializer, CropVarietyDetailSerializer,
    YieldDataSerializer, FarmingPracticeSerializer,
    CropResearchSerializer, YieldAnalyticsSerializer
)
from .filters import CropFilter, CropVarietyFilter, YieldDataFilter, FarmingPracticeFilter, CropResearchFilter
from .permissions import (
    IsRDTeamOrMISOrReadOnly, CanViewAnalytics, CanManageResearch,
    CanManageFarmingPractices, IsMISTeamOnly
)


class CropViewSet(viewsets.ModelViewSet):
    """ViewSet for managing crops"""
    
    queryset = Crop.objects.filter(is_active=True)
    serializer_class = CropSerializer
    permission_classes = [IsRDTeamOrMISOrReadOnly]
    parser_classes = [MultiPartParser, FormParser, JSONParser]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_class = CropFilter
    search_fields = ['name', 'scientific_name', 'description']
    ordering_fields = ['name', 'category', 'growth_cycle_days', 'created_at']
    ordering = ['name']
    
    def get_serializer_class(self):
        if self.action == 'retrieve':
            return CropDetailSerializer
        elif self.action == 'summary':
            return CropSummarySerializer
        return CropSerializer
    
    @swagger_auto_schema(
        operation_description="Create a new crop with form data support. Supports multipart/form-data and application/x-www-form-urlencoded.",
        auto_schema=FormDataAutoSchema,
        consumes=['multipart/form-data', 'application/x-www-form-urlencoded'],
        tags=['crop-management']
    )
    def create(self, request, *args, **kwargs):
        return super().create(request, *args, **kwargs)
    
    @swagger_auto_schema(
        operation_description="Update crop information (full update) with form data support. Supports multipart/form-data and application/x-www-form-urlencoded.",
        auto_schema=FormDataAutoSchema,
        consumes=['multipart/form-data', 'application/x-www-form-urlencoded'],
        tags=['crop-management']
    )
    def update(self, request, *args, **kwargs):
        return super().update(request, *args, **kwargs)
    
    @swagger_auto_schema(
        operation_description="Partially update crop information with form data support. Supports multipart/form-data and application/x-www-form-urlencoded.",
        auto_schema=FormDataAutoSchema,
        consumes=['multipart/form-data', 'application/x-www-form-urlencoded'],
        tags=['crop-management']
    )
    def partial_update(self, request, *args, **kwargs):
        return super().partial_update(request, *args, **kwargs)
    
    @swagger_auto_schema(
        method='get',
        operation_description="Get summary statistics for all crops",
        responses={200: CropSummarySerializer(many=True)}
    )
    @action(detail=False, methods=['get'])
    def summary(self, request):
        """Get crop summary statistics"""
        crops = self.filter_queryset(self.get_queryset())
        serializer = self.get_serializer(crops, many=True)
        return Response(serializer.data)
    
    @swagger_auto_schema(
        method='get',
        operation_description="Get crops by category",
        manual_parameters=[
            openapi.Parameter(
                'category',
                openapi.IN_QUERY,
                description="Crop category",
                type=openapi.TYPE_STRING,
                enum=['cereal', 'vegetable', 'fruit', 'legume', 'oilseed', 'fiber', 'spice', 'medicinal', 'fodder', 'other']
            )
        ]
    )
    @action(detail=False, methods=['get'])
    def by_category(self, request):
        """Get crops grouped by category"""
        category = request.query_params.get('category')
        if category:
            crops = self.get_queryset().filter(category=category)
        else:
            crops = self.get_queryset()
        
        serializer = self.get_serializer(crops, many=True)
        return Response(serializer.data)
    
    @swagger_auto_schema(
        method='get',
        operation_description="Get crops by growth season",
        manual_parameters=[
            openapi.Parameter(
                'season',
                openapi.IN_QUERY,
                description="Growth season",
                type=openapi.TYPE_STRING,
                enum=['kharif', 'rabi', 'zaid', 'perennial']
            )
        ]
    )
    @action(detail=False, methods=['get'])
    def by_season(self, request):
        """Get crops by growth season"""
        season = request.query_params.get('season')
        if season:
            crops = self.get_queryset().filter(growth_season=season)
        else:
            crops = self.get_queryset()
        
        serializer = self.get_serializer(crops, many=True)
        return Response(serializer.data)


class CropVarietyViewSet(viewsets.ModelViewSet):
    """ViewSet for managing crop varieties"""
    
    queryset = CropVariety.objects.filter(is_active=True)
    serializer_class = CropVarietySerializer
    permission_classes = [IsRDTeamOrMISOrReadOnly]
    parser_classes = [MultiPartParser, FormParser, JSONParser]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_class = CropVarietyFilter
    search_fields = ['name', 'variety_code', 'description', 'developed_by']
    ordering_fields = ['name', 'crop__name', 'yield_potential', 'maturity_days', 'release_year']
    ordering = ['crop__name', 'name']
    
    def get_serializer_class(self):
        if self.action == 'retrieve':
            return CropVarietyDetailSerializer
        return CropVarietySerializer
    
    @swagger_auto_schema(
        operation_description="Create a new crop variety with form data support. Supports multipart/form-data and application/x-www-form-urlencoded.",
        auto_schema=FormDataAutoSchema,
        consumes=['multipart/form-data', 'application/x-www-form-urlencoded'],
        tags=['crop-management']
    )
    def create(self, request, *args, **kwargs):
        return super().create(request, *args, **kwargs)
    
    @swagger_auto_schema(
        operation_description="Update crop variety information (full update) with form data support. Supports multipart/form-data and application/x-www-form-urlencoded.",
        auto_schema=FormDataAutoSchema,
        consumes=['multipart/form-data', 'application/x-www-form-urlencoded'],
        tags=['crop-management']
    )
    def update(self, request, *args, **kwargs):
        return super().update(request, *args, **kwargs)
    
    @swagger_auto_schema(
        operation_description="Partially update crop variety information with form data support. Supports multipart/form-data and application/x-www-form-urlencoded.",
        auto_schema=FormDataAutoSchema,
        consumes=['multipart/form-data', 'application/x-www-form-urlencoded'],
        tags=['crop-management']
    )
    def partial_update(self, request, *args, **kwargs):
        return super().partial_update(request, *args, **kwargs)
    
    @swagger_auto_schema(
        method='get',
        operation_description="Get varieties for a specific crop",
        manual_parameters=[
            openapi.Parameter(
                'crop_id',
                openapi.IN_QUERY,
                description="Crop ID",
                type=openapi.TYPE_INTEGER
            )
        ]
    )
    @action(detail=False, methods=['get'])
    def by_crop(self, request):
        """Get varieties for a specific crop"""
        crop_id = request.query_params.get('crop_id')
        if crop_id:
            varieties = self.get_queryset().filter(crop_id=crop_id)
        else:
            varieties = self.get_queryset()
        
        serializer = self.get_serializer(varieties, many=True)
        return Response(serializer.data)
    
    @swagger_auto_schema(
        method='get',
        operation_description="Get high-yielding varieties",
        manual_parameters=[
            openapi.Parameter(
                'min_yield',
                openapi.IN_QUERY,
                description="Minimum yield potential (kg/ha)",
                type=openapi.TYPE_NUMBER
            )
        ]
    )
    @action(detail=False, methods=['get'])
    def high_yielding(self, request):
        """Get high-yielding varieties"""
        min_yield = request.query_params.get('min_yield', 5000)
        varieties = self.get_queryset().filter(
            yield_potential__gte=min_yield
        ).order_by('-yield_potential')
        
        serializer = self.get_serializer(varieties, many=True)
        return Response(serializer.data)


class YieldDataViewSet(viewsets.ModelViewSet):
    """ViewSet for managing yield data"""
    
    queryset = YieldData.objects.all()
    serializer_class = YieldDataSerializer
    permission_classes = [CanViewAnalytics]
    parser_classes = [MultiPartParser, FormParser, JSONParser]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_class = YieldDataFilter
    search_fields = ['crop__name', 'variety__name', 'farm__name', 'notes']
    ordering_fields = ['harvest_year', 'harvest_season', 'yield_per_hectare', 'total_yield', 'created_at']
    ordering = ['-harvest_year', '-created_at']
    
    @swagger_auto_schema(
        operation_description="Create new yield data with form data support. Supports multipart/form-data and application/x-www-form-urlencoded.",
        auto_schema=FormDataAutoSchema,
        consumes=['multipart/form-data', 'application/x-www-form-urlencoded'],
        tags=['crop-management']
    )
    def create(self, request, *args, **kwargs):
        return super().create(request, *args, **kwargs)
    
    @swagger_auto_schema(
        operation_description="Update yield data (full update) with form data support. Supports multipart/form-data and application/x-www-form-urlencoded.",
        auto_schema=FormDataAutoSchema,
        consumes=['multipart/form-data', 'application/x-www-form-urlencoded'],
        tags=['crop-management']
    )
    def update(self, request, *args, **kwargs):
        return super().update(request, *args, **kwargs)
    
    @swagger_auto_schema(
        operation_description="Partially update yield data with form data support. Supports multipart/form-data and application/x-www-form-urlencoded.",
        auto_schema=FormDataAutoSchema,
        consumes=['multipart/form-data', 'application/x-www-form-urlencoded'],
        tags=['crop-management']
    )
    def partial_update(self, request, *args, **kwargs):
        return super().partial_update(request, *args, **kwargs)
    
    @swagger_auto_schema(
        method='get',
        operation_description="Get yield analytics data",
        manual_parameters=[
            openapi.Parameter(
                'year',
                openapi.IN_QUERY,
                description="Harvest year",
                type=openapi.TYPE_INTEGER
            ),
            openapi.Parameter(
                'season',
                openapi.IN_QUERY,
                description="Harvest season",
                type=openapi.TYPE_STRING
            ),
            openapi.Parameter(
                'crop_id',
                openapi.IN_QUERY,
                description="Crop ID",
                type=openapi.TYPE_INTEGER
            )
        ]
    )
    @action(detail=False, methods=['get'])
    def analytics(self, request):
        """Get yield analytics data"""
        queryset = self.filter_queryset(self.get_queryset())
        
        # Group by crop, year, and season
        analytics_data = queryset.values(
            'crop_id', 'crop__name', 'harvest_year', 'harvest_season'
        ).annotate(
            total_area=Sum('area_cultivated'),
            total_yield=Sum('total_yield'),
            average_yield_per_hectare=Avg('yield_per_hectare'),
            farm_count=Count('farm', distinct=True),
            total_input_cost=Sum('input_cost'),
            average_market_price=Avg('market_price')
        ).order_by('-harvest_year', 'crop__name')
        
        # Format the data
        formatted_data = []
        for item in analytics_data:
            formatted_data.append({
                'crop_id': item['crop_id'],
                'crop_name': item['crop__name'],
                'year': item['harvest_year'],
                'season': item['harvest_season'],
                'total_area': item['total_area'] or 0,
                'total_yield': item['total_yield'] or 0,
                'average_yield_per_hectare': item['average_yield_per_hectare'] or 0,
                'farm_count': item['farm_count'],
                'average_quality_grade': 'N/A',  # Could be calculated separately
                'total_input_cost': item['total_input_cost'] or 0,
                'average_market_price': item['average_market_price'] or 0
            })
        
        serializer = YieldAnalyticsSerializer(formatted_data, many=True)
        return Response(serializer.data)
    
    @swagger_auto_schema(
        method='get',
        operation_description="Get yield trends for a specific crop",
        manual_parameters=[
            openapi.Parameter(
                'crop_id',
                openapi.IN_QUERY,
                description="Crop ID",
                type=openapi.TYPE_INTEGER,
                required=True
            ),
            openapi.Parameter(
                'years',
                openapi.IN_QUERY,
                description="Number of years to include (default: 5)",
                type=openapi.TYPE_INTEGER
            )
        ]
    )
    @action(detail=False, methods=['get'])
    def trends(self, request):
        """Get yield trends for a specific crop"""
        crop_id = request.query_params.get('crop_id')
        years = int(request.query_params.get('years', 5))
        
        if not crop_id:
            return Response(
                {'error': 'crop_id parameter is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Get yield data for the specified crop and years
        yield_data = self.get_queryset().filter(
            crop_id=crop_id
        ).order_by('-harvest_year')[:years * 3]  # Assuming max 3 seasons per year
        
        # Group by year and season
        trends = yield_data.values(
            'harvest_year', 'harvest_season'
        ).annotate(
            avg_yield=Avg('yield_per_hectare'),
            total_area=Sum('area_cultivated'),
            total_production=Sum('total_yield')
        ).order_by('-harvest_year', 'harvest_season')
        
        return Response(list(trends))
    
    @swagger_auto_schema(
        method='get',
        operation_description="Compare yields across different farms",
        manual_parameters=[
            openapi.Parameter(
                'crop_id',
                openapi.IN_QUERY,
                description="Crop ID",
                type=openapi.TYPE_INTEGER
            ),
            openapi.Parameter(
                'year',
                openapi.IN_QUERY,
                description="Harvest year",
                type=openapi.TYPE_INTEGER
            )
        ]
    )
    @action(detail=False, methods=['get'])
    def farm_comparison(self, request):
        """Compare yields across different farms"""
        crop_id = request.query_params.get('crop_id')
        year = request.query_params.get('year')
        
        queryset = self.get_queryset()
        if crop_id:
            queryset = queryset.filter(crop_id=crop_id)
        if year:
            queryset = queryset.filter(harvest_year=year)
        
        # Group by farm
        farm_data = queryset.values(
            'farm_id', 'farm__name', 'farm__location'
        ).annotate(
            avg_yield=Avg('yield_per_hectare'),
            total_area=Sum('area_cultivated'),
            total_production=Sum('total_yield'),
            record_count=Count('id')
        ).order_by('-avg_yield')
        
        return Response(list(farm_data))


class FarmingPracticeViewSet(viewsets.ModelViewSet):
    """ViewSet for managing farming practices"""
    
    queryset = FarmingPractice.objects.filter(is_active=True)
    serializer_class = FarmingPracticeSerializer
    permission_classes = [CanManageFarmingPractices]
    parser_classes = [MultiPartParser, FormParser, JSONParser]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_class = FarmingPracticeFilter
    search_fields = ['title', 'description', 'implementation_steps']
    ordering_fields = ['crop__name', 'practice_type', 'priority_level', 'created_at']
    ordering = ['crop__name', 'practice_type', 'priority_level']
    
    @swagger_auto_schema(
        operation_description="Create new farming practice with form data support. Supports multipart/form-data and application/x-www-form-urlencoded.",
        auto_schema=FormDataAutoSchema,
        consumes=['multipart/form-data', 'application/x-www-form-urlencoded'],
        tags=['crop-management']
    )
    def create(self, request, *args, **kwargs):
        return super().create(request, *args, **kwargs)
    
    @swagger_auto_schema(
        operation_description="Update farming practice (full update) with form data support. Supports multipart/form-data and application/x-www-form-urlencoded.",
        auto_schema=FormDataAutoSchema,
        consumes=['multipart/form-data', 'application/x-www-form-urlencoded'],
        tags=['crop-management']
    )
    def update(self, request, *args, **kwargs):
        return super().update(request, *args, **kwargs)
    
    @swagger_auto_schema(
        operation_description="Partially update farming practice with form data support. Supports multipart/form-data and application/x-www-form-urlencoded.",
        auto_schema=FormDataAutoSchema,
        consumes=['multipart/form-data', 'application/x-www-form-urlencoded'],
        tags=['crop-management']
    )
    def partial_update(self, request, *args, **kwargs):
        return super().partial_update(request, *args, **kwargs)
    
    @swagger_auto_schema(
        method='get',
        operation_description="Get practices for a specific crop",
        manual_parameters=[
            openapi.Parameter(
                'crop_id',
                openapi.IN_QUERY,
                description="Crop ID",
                type=openapi.TYPE_INTEGER
            )
        ]
    )
    @action(detail=False, methods=['get'])
    def by_crop(self, request):
        """Get practices for a specific crop"""
        crop_id = request.query_params.get('crop_id')
        if crop_id:
            practices = self.get_queryset().filter(crop_id=crop_id)
        else:
            practices = self.get_queryset()
        
        serializer = self.get_serializer(practices, many=True)
        return Response(serializer.data)
    
    @swagger_auto_schema(
        method='get',
        operation_description="Get practices by type",
        manual_parameters=[
            openapi.Parameter(
                'practice_type',
                openapi.IN_QUERY,
                description="Practice type",
                type=openapi.TYPE_STRING,
                enum=['soil_preparation', 'planting', 'irrigation', 'fertilization', 'pest_control', 'disease_management', 'weed_control', 'harvesting', 'post_harvest', 'general']
            )
        ]
    )
    @action(detail=False, methods=['get'])
    def by_type(self, request):
        """Get practices by type"""
        practice_type = request.query_params.get('practice_type')
        if practice_type:
            practices = self.get_queryset().filter(practice_type=practice_type)
        else:
            practices = self.get_queryset()
        
        serializer = self.get_serializer(practices, many=True)
        return Response(serializer.data)
    
    @swagger_auto_schema(
        method='get',
        operation_description="Get recommended practices (high priority and proven)"
    )
    @action(detail=False, methods=['get'])
    def recommended(self, request):
        """Get recommended practices"""
        practices = self.get_queryset().filter(
            Q(priority_level__in=['high', 'critical']) &
            Q(validation_status__in=['proven', 'recommended'])
        ).order_by('crop__name', 'practice_type', '-priority_level')
        
        serializer = self.get_serializer(practices, many=True)
        return Response(serializer.data)


class CropResearchViewSet(viewsets.ModelViewSet):
    """ViewSet for managing crop research"""
    
    queryset = CropResearch.objects.filter(is_active=True)
    serializer_class = CropResearchSerializer
    permission_classes = [CanManageResearch]
    parser_classes = [MultiPartParser, FormParser, JSONParser]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_class = CropResearchFilter
    search_fields = ['title', 'objective', 'findings', 'research_institution', 'principal_investigator']
    ordering_fields = ['crop__name', 'research_type', 'research_period_start', 'publication_status', 'created_at']
    ordering = ['-research_period_start', '-created_at']
    
    @swagger_auto_schema(
        operation_description="Create new crop research with form data support. Supports multipart/form-data and application/x-www-form-urlencoded.",
        auto_schema=FormDataAutoSchema,
        consumes=['multipart/form-data', 'application/x-www-form-urlencoded'],
        tags=['crop-management']
    )
    def create(self, request, *args, **kwargs):
        return super().create(request, *args, **kwargs)
    
    @swagger_auto_schema(
        operation_description="Update crop research (full update) with form data support. Supports multipart/form-data and application/x-www-form-urlencoded.",
        auto_schema=FormDataAutoSchema,
        consumes=['multipart/form-data', 'application/x-www-form-urlencoded'],
        tags=['crop-management']
    )
    def update(self, request, *args, **kwargs):
        return super().update(request, *args, **kwargs)
    
    @swagger_auto_schema(
        operation_description="Partially update crop research with form data support. Supports multipart/form-data and application/x-www-form-urlencoded.",
        auto_schema=FormDataAutoSchema,
        consumes=['multipart/form-data', 'application/x-www-form-urlencoded'],
        tags=['crop-management']
    )
    def partial_update(self, request, *args, **kwargs):
        return super().partial_update(request, *args, **kwargs)
    
    @swagger_auto_schema(
        method='get',
        operation_description="Get research for a specific crop",
        manual_parameters=[
            openapi.Parameter(
                'crop_id',
                openapi.IN_QUERY,
                description="Crop ID",
                type=openapi.TYPE_INTEGER
            )
        ]
    )
    @action(detail=False, methods=['get'])
    def by_crop(self, request):
        """Get research for a specific crop"""
        crop_id = request.query_params.get('crop_id')
        if crop_id:
            research = self.get_queryset().filter(crop_id=crop_id)
        else:
            research = self.get_queryset()
        
        serializer = self.get_serializer(research, many=True)
        return Response(serializer.data)
    
    @swagger_auto_schema(
        method='get',
        operation_description="Get research by type",
        manual_parameters=[
            openapi.Parameter(
                'research_type',
                openapi.IN_QUERY,
                description="Research type",
                type=openapi.TYPE_STRING,
                enum=['yield_improvement', 'disease_resistance', 'pest_management', 'quality_enhancement', 'climate_adaptation', 'nutrition_study', 'market_analysis', 'sustainability', 'other']
            )
        ]
    )
    @action(detail=False, methods=['get'])
    def by_type(self, request):
        """Get research by type"""
        research_type = request.query_params.get('research_type')
        if research_type:
            research = self.get_queryset().filter(research_type=research_type)
        else:
            research = self.get_queryset()
        
        serializer = self.get_serializer(research, many=True)
        return Response(serializer.data)
    
    @swagger_auto_schema(
        method='get',
        operation_description="Get published research"
    )
    @action(detail=False, methods=['get'])
    def published(self, request):
        """Get published research"""
        research = self.get_queryset().filter(
            publication_status__in=['published', 'peer_reviewed']
        ).order_by('-research_period_start')
        
        serializer = self.get_serializer(research, many=True)
        return Response(serializer.data)
    
    @swagger_auto_schema(
        method='get',
        operation_description="Get research by institution",
        manual_parameters=[
            openapi.Parameter(
                'institution',
                openapi.IN_QUERY,
                description="Research institution name",
                type=openapi.TYPE_STRING
            )
        ]
    )
    @action(detail=False, methods=['get'])
    def by_institution(self, request):
        """Get research by institution"""
        institution = request.query_params.get('institution')
        if institution:
            research = self.get_queryset().filter(
                research_institution__icontains=institution
            )
        else:
            research = self.get_queryset()
        
        serializer = self.get_serializer(research, many=True)
        return Response(serializer.data)
