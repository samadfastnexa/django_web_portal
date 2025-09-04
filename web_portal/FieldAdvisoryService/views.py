from rest_framework import viewsets,permissions,filters
from django_filters.rest_framework import DjangoFilterBackend

from .models import Dealer, MeetingSchedule, SalesOrder
from .serializers import DealerSerializer, DealerRequestSerializer,MeetingScheduleSerializer, SalesOrderSerializer
from .serializers import CompanySerializer, RegionSerializer, ZoneSerializer, TerritorySerializer,DealerRequestSerializer,CompanyNestedSerializer,RegionNestedSerializer,ZoneNestedSerializer,TerritoryNestedSerializer
from .models import DealerRequest
from .models import Company, Region, Zone, Territory
from drf_yasg.utils import swagger_auto_schema
from .permissions import IsAdminOrReadOnly
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.permissions import IsAuthenticated
from accounts.permissions import HasRolePermission
from rest_framework import viewsets

from drf_yasg import openapi


class MeetingScheduleViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing Meeting Schedules.
    Supports list, retrieve, create, update, partial update, and delete.
    """
    queryset = MeetingSchedule.objects.all()
    serializer_class = MeetingScheduleSerializer

    @swagger_auto_schema(
        operation_description="List all meeting schedules.",
        responses={200: MeetingScheduleSerializer(many=True)},
        tags=["MeetingSchedules"]
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_description="Retrieve a specific meeting schedule by ID.",
        responses={200: MeetingScheduleSerializer},
        tags=["MeetingSchedules"]
    )
    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_description="Create a new meeting schedule.",
        responses={201: MeetingScheduleSerializer},
        tags=["MeetingSchedules"]
    )
    def create(self, request, *args, **kwargs):
        return super().create(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_description="Update an existing meeting schedule.",
        responses={200: MeetingScheduleSerializer},
        tags=["MeetingSchedules"]
    )
    def update(self, request, *args, **kwargs):
        return super().update(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_description="Partially update a meeting schedule.",
        responses={200: MeetingScheduleSerializer},
        tags=["MeetingSchedules"]
    )
    def partial_update(self, request, *args, **kwargs):
        return super().partial_update(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_description="Delete a meeting schedule.",
        responses={204: 'No Content'},
        tags=["MeetingSchedules"]
    )
    def destroy(self, request, *args, **kwargs):
        return super().destroy(request, *args, **kwargs)


class SalesOrderViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing Sales Orders.
    Supports list, retrieve, create, update, partial update, and delete.
    """
    queryset = SalesOrder.objects.all()
    serializer_class = SalesOrderSerializer

    @swagger_auto_schema(
        operation_description="List all sales orders.",
        responses={200: SalesOrderSerializer(many=True)},
        tags=["SalesOrders"]
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_description="Retrieve a specific sales order by ID.",
        responses={200: SalesOrderSerializer},
        tags=["SalesOrders"]
    )
    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_description="Create a new sales order.",
        responses={201: SalesOrderSerializer},
        tags=["SalesOrders"]
    )
    def create(self, request, *args, **kwargs):
        return super().create(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_description="Update an existing sales order.",
        responses={200: SalesOrderSerializer},
        tags=["SalesOrders"]
    )
    def update(self, request, *args, **kwargs):
        return super().update(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_description="Partially update a sales order.",
        responses={200: SalesOrderSerializer},
        tags=["SalesOrders"]
    )
    def partial_update(self, request, *args, **kwargs):
        return super().partial_update(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_description="Delete a sales order.",
        responses={204: 'No Content'},
        tags=["SalesOrders"]
    )
    def destroy(self, request, *args, **kwargs):
        return super().destroy(request, *args, **kwargs)


class DealerViewSet(viewsets.ModelViewSet):
    queryset = Dealer.objects.all()
    serializer_class = DealerSerializer

    @swagger_auto_schema(
        operation_description="List all dealers",
        responses={200: DealerSerializer(many=True)},
        tags=["Dealers"]
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_description="Retrieve a single dealer by ID",
        responses={200: DealerSerializer},
        tags=["Dealers"]
    )
    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_description="Create a new dealer",
        responses={201: DealerSerializer},
        tags=["Dealers"]
    )
    def create(self, request, *args, **kwargs):
        return super().create(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_description="Update an existing dealer",
        responses={200: DealerSerializer},
        tags=["Dealers"]
    )
    def update(self, request, *args, **kwargs):
        return super().update(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_description="Partially update an existing dealer",
        responses={200: DealerSerializer},
        tags=["Dealers"]
    )
    def partial_update(self, request, *args, **kwargs):
        return super().partial_update(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_description="Delete a dealer",
        responses={204: 'No Content'},
        tags=["Dealers"]
    )
    def destroy(self, request, *args, **kwargs):
        return super().destroy(request, *args, **kwargs)
    
class DealerRequestViewSet(viewsets.ModelViewSet):
    serializer_class = DealerRequestSerializer
    permission_classes = [IsAuthenticated, HasRolePermission]
    parser_classes = [MultiPartParser, FormParser]  # Accept form-data

    def get_queryset(self):
        user = self.request.user

        # Prevent error during swagger schema generation
        if getattr(self, 'swagger_fake_view', False):
            return DealerRequest.objects.none()

        if not user or not user.is_authenticated:
            # Return empty queryset for anonymous users or unauthenticated requests
            return DealerRequest.objects.none()

        if user.is_superuser or (hasattr(user, 'role') and user.role.name == 'Admin'):
            return DealerRequest.objects.all()

        return DealerRequest.objects.filter(requested_by=user)

    @swagger_auto_schema(
        operation_description="Create Dealer Request",
        request_body=DealerRequestSerializer,
        tags=["Dealer Requests"]
    )
    def create(self, request, *args, **kwargs):
        return super().create(request, *args, **kwargs)

    @swagger_auto_schema(tags=["Dealer Requests"])
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @swagger_auto_schema(tags=["Dealer Requests"])
    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)

    @swagger_auto_schema(tags=["Dealer Requests"])
    def update(self, request, *args, **kwargs):
        return super().update(request, *args, **kwargs)

    @swagger_auto_schema(tags=["Dealer Requests"])
    def partial_update(self, request, *args, **kwargs):
        return super().partial_update(request, *args, **kwargs)


class CompanyViewSet(viewsets.ModelViewSet):
    queryset = Company.objects.all()
    serializer_class = CompanySerializer
    # permission_classes = [IsAdminOrReadOnly]
    permission_classes = [IsAuthenticated, HasRolePermission]
    filter_backends = [filters.SearchFilter]
    search_fields = ['name']
    

    @swagger_auto_schema(tags=["Company"])
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)
    @swagger_auto_schema(tags=["Company"])
    def create(self, request, *args, **kwargs):
        return super().create(request, *args, **kwargs)

    @swagger_auto_schema(tags=["Company"])
    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)

    @swagger_auto_schema(tags=["Company"])
    def update(self, request, *args, **kwargs):
        return super().update(request, *args, **kwargs)

    @swagger_auto_schema(tags=["Company"])
    def partial_update(self, request, *args, **kwargs):
        return super().partial_update(request, *args, **kwargs)

    @swagger_auto_schema(tags=["Company"])
    def destroy(self, request, *args, **kwargs):
        return super().destroy(request, *args, **kwargs)

class RegionViewSet(viewsets.ModelViewSet):
    queryset = Region.objects.all()
    serializer_class = RegionSerializer
    # permission_classes = [IsAdminOrReadOnly]
    permission_classes = [IsAuthenticated, HasRolePermission]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ['company']
    search_fields = ['name']

    @swagger_auto_schema(tags=["Region"])
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

class ZoneViewSet(viewsets.ModelViewSet):
    queryset = Zone.objects.all()
    serializer_class = ZoneSerializer
    # permission_classes = [IsAdminOrReadOnly]
    permission_classes = [IsAuthenticated, HasRolePermission]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ['region']
    search_fields = ['name']

    @swagger_auto_schema(tags=["Zone"])
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

class TerritoryViewSet(viewsets.ModelViewSet):
    queryset = Territory.objects.all()
    serializer_class = TerritorySerializer
    # permission_classes = [IsAdminOrReadOnly]
    permission_classes = [IsAuthenticated, HasRolePermission]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ['zone']
    search_fields = ['name']

    @swagger_auto_schema(tags=["Territory"])
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)


class CompanyNestedViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = CompanyNestedSerializer
    queryset = Company.objects.prefetch_related(
        'regions__zones__territories'
    ).all()

    @swagger_auto_schema(tags=["Company (Nested View)"])
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)
    
    @swagger_auto_schema(tags=["Company (Nested View)"])
    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)

class RegionNestedViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = RegionNestedSerializer
    queryset = Region.objects.prefetch_related(
        'zones__territories'
    ).all()

    @swagger_auto_schema(tags=["Region (Nested View)"])
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

class ZoneNestedViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = ZoneNestedSerializer
    queryset = Zone.objects.prefetch_related(
        'territories'
    ).all()

    @swagger_auto_schema(tags=["Zone (Nested View)"])
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)
    
class TerritoryNestedViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = TerritoryNestedSerializer
    queryset = Territory.objects.select_related('company', 'zone__company', 'zone__region').all()

    @swagger_auto_schema(tags=["Territory (Nested View)"])
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)