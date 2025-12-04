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
        operation_description="Retrieve a list of all meeting schedules with staff assignments and location details.",
        responses={
            200: openapi.Response(
                description='List of meeting schedules',
                examples={
                    'application/json': [
                        {
                            'id': 1,
                            'staff': 1,
                            'date': '2024-02-15',
                            'location': 'Community Center, Village ABC',
                            'min_farmers_required': 10,
                            'confirmed_attendees': 8
                        }
                    ]
                }
            )
        },
        tags=["14. MeetingSchedules"]
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_description="Get detailed information of a specific meeting schedule including staff and attendance details.",
        responses={
            200: openapi.Response(
                description='Meeting schedule details',
                examples={
                    'application/json': {
                        'id': 1,
                        'staff': 1,
                        'date': '2024-02-15',
                        'location': 'Community Center, Village ABC',
                        'min_farmers_required': 10,
                        'confirmed_attendees': 8
                    }
                }
            ),
            404: 'Meeting schedule not found'
        },
        tags=["14. MeetingSchedules"]
    )
    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_description="Schedule a new meeting with farmers by assigning staff, date, and location.",
        request_body=MeetingScheduleSerializer,
        responses={
            201: 'Meeting schedule created successfully',
            400: 'Bad Request - Invalid data provided'
        },
        tags=["14. MeetingSchedules"]
    )
    def create(self, request, *args, **kwargs):
        return super().create(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_description="Update all details of an existing meeting schedule (full update).",
        responses={
            200: 'Meeting schedule updated successfully',
            404: 'Meeting schedule not found',
            400: 'Bad Request - Invalid data provided'
        },
        tags=["14. MeetingSchedules"]
    )
    def update(self, request, *args, **kwargs):
        return super().update(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_description="Update specific fields of a meeting schedule (partial update).",
        request_body=MeetingScheduleSerializer,
        responses={
            200: 'Meeting schedule updated successfully',
            404: 'Meeting schedule not found',
            400: 'Bad Request - Invalid data provided'
        },
        tags=["14. MeetingSchedules"]
    )
    def partial_update(self, request, *args, **kwargs):
        return super().partial_update(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_description="Cancel and permanently delete a meeting schedule.",
        responses={
            204: 'Meeting schedule deleted successfully',
            404: 'Meeting schedule not found'
        },
        tags=["14. MeetingSchedules"]
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
        operation_description="Retrieve a list of all sales orders with their status, dealer, and meeting schedule information.",
        responses={
            200: openapi.Response(
                description='List of sales orders',
                examples={
                    'application/json': [
                        {
                            'id': 1,
                            'schedule': 1,
                            'staff': 1,
                            'dealer': 1,
                            'status': 'pending',
                            'created_at': '2024-01-15T10:30:00Z'
                        }
                    ]
                }
            )
        },
        tags=["15. SalesOrders"]
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_description="Get detailed information of a specific sales order including all related data.",
        responses={
            200: openapi.Response(
                description='Sales order details',
                examples={
                    'application/json': {
                        'id': 1,
                        'schedule': 1,
                        'staff': 1,
                        'dealer': 1,
                        'status': 'entertained',
                        'created_at': '2024-01-15T10:30:00Z'
                    }
                }
            ),
            404: 'Sales order not found'
        },
        tags=["15. SalesOrders"]
    )
    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_description="Create a new sales order linking a dealer with a meeting schedule.",
        request_body=SalesOrderSerializer,
        responses={
            201: 'Sales order created successfully',
            400: 'Bad Request - Invalid data provided'
        },
        tags=["15. SalesOrders"]
    )
    def create(self, request, *args, **kwargs):
        return super().create(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_description="Update all details of an existing sales order (full update).",
        responses={
            200: 'Sales order updated successfully',
            404: 'Sales order not found',
            400: 'Bad Request - Invalid data provided'
        },
        tags=["15. SalesOrders"]
    )
    def update(self, request, *args, **kwargs):
        return super().update(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_description="Update specific fields of a sales order, typically used for status changes.",
        request_body=SalesOrderSerializer,
        responses={
            200: 'Sales order updated successfully',
            404: 'Sales order not found',
            400: 'Bad Request - Invalid status value'
        },
        tags=["15. SalesOrders"]
    )
    def partial_update(self, request, *args, **kwargs):
        return super().partial_update(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_description="Permanently delete a sales order from the system.",
        responses={
            204: 'Sales order deleted successfully',
            404: 'Sales order not found'
        },
        tags=["15. SalesOrders"]
    )
    def destroy(self, request, *args, **kwargs):
        return super().destroy(request, *args, **kwargs)


class DealerViewSet(viewsets.ModelViewSet):
    queryset = Dealer.objects.all()
    serializer_class = DealerSerializer

    @swagger_auto_schema(
        operation_description="List all dealers",
        responses={200: DealerSerializer(many=True)},
        tags=["16. Dealers"]
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_description="Retrieve a single dealer by ID",
        responses={200: DealerSerializer},
        tags=["16. Dealers"]
    )
    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_description="Create a new dealer",
        responses={201: DealerSerializer},
        tags=["16. Dealers"]
    )
    def create(self, request, *args, **kwargs):
        return super().create(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_description="Update an existing dealer",
        responses={200: DealerSerializer},
        tags=["16. Dealers"]
    )
    def update(self, request, *args, **kwargs):
        return super().update(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_description="Partially update an existing dealer",
        responses={200: DealerSerializer},
        tags=["16. Dealers"]
    )
    def partial_update(self, request, *args, **kwargs):
        return super().partial_update(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_description="Delete a dealer",
        responses={204: 'No Content'},
        tags=["16. Dealers"]
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
        operation_description="Submit a new dealer registration request with all required documentation and business details.",
        request_body=DealerRequestSerializer,
        responses={
            201: 'Dealer request submitted successfully',
            400: 'Bad Request - Invalid data or missing required fields'
        },
        tags=["17. Dealer Requests"]
    )
    def create(self, request, *args, **kwargs):
        return super().create(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_description="Retrieve a list of dealer requests. Admins can see all requests, while users can only see their own submissions.",
        responses={
            200: openapi.Response(
                description='List of dealer requests',
                examples={
                    'application/json': [
                        {
                            'id': 1,
                            'owner_name': 'Ahmed Ali Khan',
                            'business_name': 'Khan Agro Store',
                            'contact_number': '+92-300-1234567',
                            'status': 'pending',
                            'filer_status': 'filer',
                            'minimum_investment': 500000,
                            'created_at': '2024-01-15T10:30:00Z'
                        }
                    ]
                }
            )
        },
        tags=["17. Dealer Requests"]
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_description="Retrieve detailed information of a specific dealer request including all submitted documents and status.",
        responses={
            200: openapi.Response(
                description='Dealer request details',
                examples={
                    'application/json': {
                        'id': 1,
                        'owner_name': 'Ahmed Ali Khan',
                        'business_name': 'Khan Agro Store',
                        'contact_number': '+92-300-1234567',
                        'address': 'Main Bazaar, Village ABC',
                        'cnic_number': '12345-6789012-3',
                        'status': 'approved',
                        'filer_status': 'filer',
                        'minimum_investment': 500000,
                        'created_at': '2024-01-15T10:30:00Z',
                        'reviewed_at': '2024-01-20T14:30:00Z'
                    }
                }
            ),
            404: 'Dealer request not found',
            403: 'Forbidden - You can only view your own requests'
        },
        tags=["17. Dealer Requests"]
    )
    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_description="Update a dealer request (typically used by admins to approve/reject requests).",
        request_body=DealerRequestSerializer,
        responses={
            200: 'Dealer request updated successfully',
            404: 'Dealer request not found',
            403: 'Forbidden - Insufficient permissions'
        },
        tags=["17. Dealer Requests"]
    )
    def update(self, request, *args, **kwargs):
        return super().update(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_description="Partially update specific fields of a dealer request.",
        responses={
            200: 'Dealer request updated successfully',
            404: 'Dealer request not found',
            403: 'Forbidden - Insufficient permissions'
        },
        tags=["17. Dealer Requests"]
    )
    def partial_update(self, request, *args, **kwargs):
        return super().partial_update(request, *args, **kwargs)


class CompanyViewSet(viewsets.ModelViewSet):
    queryset = Company.objects.all()
    serializer_class = CompanySerializer
    # permission_classes = [IsAdminOrReadOnly]
    permission_classes = [IsAuthenticated, HasRolePermission]
    filter_backends = [filters.SearchFilter]
    search_fields = ['name']
    

    @swagger_auto_schema(
        operation_description="Retrieve a list of all companies in the system.",
        responses={
            200: openapi.Response(
                description='List of companies',
                examples={
                    'application/json': [
                        {
                            'id': 1,
                            'name': 'ABC Agriculture Ltd.',
                            'code': 'ABC001',
                            'address': '123 Business District, Lahore',
                            'contact_number': '+92-42-1234567',
                            'email': 'info@abcagriculture.com'
                        }
                    ]
                }
            )
        },
        tags=["18. Companies"]
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)
    @swagger_auto_schema(
        operation_description="Create a new company in the system with all required business information.",
        request_body=CompanySerializer,
        responses={
            201: 'Company created successfully',
            400: 'Bad Request - Invalid data or duplicate code'
        },
        tags=["18. Companies"]
    )
    def create(self, request, *args, **kwargs):
        return super().create(request, *args, **kwargs)

    @swagger_auto_schema(tags=["18. Company"])
    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)

    @swagger_auto_schema(tags=["18. Company"])
    def update(self, request, *args, **kwargs):
        return super().update(request, *args, **kwargs)

    @swagger_auto_schema(tags=["18. Company"])
    def partial_update(self, request, *args, **kwargs):
        return super().partial_update(request, *args, **kwargs)

    @swagger_auto_schema(tags=["18. Company"])
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

    @swagger_auto_schema(
        operation_description="Retrieve a list of all regions, optionally filtered by company.",
        responses={
            200: openapi.Response(
                description='List of regions',
                examples={
                    'application/json': [
                        {
                            'id': 1,
                            'name': 'Punjab Region',
                            'code': 'PUN001',
                            'company': 1,
                            'company_name': 'ABC Agriculture Ltd.'
                        }
                    ]
                }
            )
        },
        tags=["19. Regions"]
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_description="Create a new region within a company's operational area.",
        request_body=RegionSerializer,
        responses={
            201: 'Region created successfully',
            400: 'Bad Request - Invalid data or duplicate code'
        },
        tags=["19. Regions"]
    )
    def create(self, request, *args, **kwargs):
        return super().create(request, *args, **kwargs)


class ZoneViewSet(viewsets.ModelViewSet):
    queryset = Zone.objects.all()
    serializer_class = ZoneSerializer
    # permission_classes = [IsAdminOrReadOnly]
    permission_classes = [IsAuthenticated, HasRolePermission]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ['region']
    search_fields = ['name']

    @swagger_auto_schema(
        operation_description="Retrieve a list of all zones, optionally filtered by region.",
        responses={
            200: openapi.Response(
                description='List of zones',
                examples={
                    'application/json': [
                        {
                            'id': 1,
                            'name': 'Lahore Zone',
                            'code': 'LAH001',
                            'region': 1,
                            'region_name': 'Punjab Region'
                        }
                    ]
                }
            )
        },
        tags=["20. Zones"]
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_description="Create a new zone within a region's operational area.",
        request_body=ZoneSerializer,
        responses={
            201: 'Zone created successfully',
            400: 'Bad Request - Invalid data or duplicate code'
        },
        tags=["20. Zones"]
    )
    def create(self, request, *args, **kwargs):
        return super().create(request, *args, **kwargs)


class TerritoryViewSet(viewsets.ModelViewSet):
    queryset = Territory.objects.all()
    serializer_class = TerritorySerializer
    # permission_classes = [IsAdminOrReadOnly]
    permission_classes = [IsAuthenticated, HasRolePermission]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ['zone']
    search_fields = ['name']

    @swagger_auto_schema(
        operation_description="Retrieve a list of all territories, optionally filtered by zone.",
        responses={
            200: openapi.Response(
                description='List of territories',
                examples={
                    'application/json': [
                        {
                            'id': 1,
                            'name': 'Model Town Territory',
                            'code': 'MT001',
                            'zone': 1,
                            'zone_name': 'Lahore Zone'
                        }
                    ]
                }
            )
        },
        tags=["21. Territories"]
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)


class CompanyNestedViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = CompanyNestedSerializer
    queryset = Company.objects.prefetch_related(
        'regions__zones__territories'
    ).all()

    @swagger_auto_schema(tags=["22. Companies (Nested View)"])
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)
    
    @swagger_auto_schema(tags=["22. Companies (Nested View)"])
    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)

class RegionNestedViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = RegionNestedSerializer
    queryset = Region.objects.prefetch_related(
        'zones__territories'
    ).all()

    @swagger_auto_schema(tags=["23. Regions (Nested View)"])
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

class ZoneNestedViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = ZoneNestedSerializer
    queryset = Zone.objects.prefetch_related(
        'territories'
    ).all()

    @swagger_auto_schema(tags=["24. Zones (Nested View)"])
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)
    
class TerritoryNestedViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = TerritoryNestedSerializer
    queryset = Territory.objects.select_related('company', 'zone__company', 'zone__region').all()

    @swagger_auto_schema(tags=["25. Territories (Nested View)"])
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)


# SAP LOV API endpoints for admin form dropdowns
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from sap_integration import hana_connect
import os

def _load_env_file(path: str) -> None:
    """Load environment variables from .env file"""
    try:
        if os.path.isfile(path) and os.access(path, os.R_OK):
            with open(path, 'r', encoding='utf-8') as f:
                for line in f:
                    s = line.strip()
                    if s == '' or s.startswith('#') or '=' not in s:
                        continue
                    k, v = s.split('=', 1)
                    k = k.strip()
                    v = v.strip()
                    if v != '' and ((v[0] == '"' and v[-1] == '"') or (v[0] == "'" and v[-1] == "'")):
                        v = v[1:-1]
                    if k != '' and not os.environ.get(k):
                        os.environ[k] = v
    except Exception:
        pass

def get_hana_connection():
    """Get HANA database connection"""
    try:
        # Load .env file
        _load_env_file(os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), '.env'))
        
        from hdbcli import dbapi
        from preferences.models import Setting
        
        # Get database name from settings
        try:
            db_setting = Setting.objects.filter(slug='SAP_COMPANY_DB').first()
            if db_setting and hasattr(db_setting, 'value'):
                # If value is a dict, get the current selected schema
                if isinstance(db_setting.value, dict):
                    schema = list(db_setting.value.values())[0] if db_setting.value else '4B-BIO_APP'
                else:
                    schema = str(db_setting.value)
            else:
                schema = os.environ.get('SAP_COMPANY_DB', '4B-BIO_APP')
        except Exception as e:
            print(f"Error getting schema from settings: {e}")
            schema = os.environ.get('SAP_COMPANY_DB', '4B-BIO_APP')
        
        # Strip quotes if present
        schema = schema.strip('"\'')
        
        # Connection parameters
        host = os.environ.get('HANA_HOST', '').strip()
        port = int(os.environ.get('HANA_PORT', 30015))
        user = os.environ.get('HANA_USER', '').strip()
        password = os.environ.get('HANA_PASSWORD', '').strip()
        
        if not host or not user:
            return None
        
        # Connect
        conn = dbapi.connect(address=host, port=port, user=user, password=password)
        
        # Set schema
        cursor = conn.cursor()
        cursor.execute(f'SET SCHEMA "{schema}"')
        cursor.close()
        
        return conn
    except Exception as e:
        print(f"Error connecting to HANA: {e}")
        return None

@require_http_methods(["GET"])
def api_warehouse_for_item(request):
    """Get warehouses for a specific item"""
    item_code = request.GET.get('item_code')
    if not item_code:
        return JsonResponse({'error': 'item_code parameter required'}, status=400)
    
    try:
        db = get_hana_connection()
        if not db:
            return JsonResponse({'error': 'Database connection failed'}, status=500)
        
        warehouses = hana_connect.warehouse_for_item(db, item_code)
        db.close()
        return JsonResponse({'warehouses': warehouses})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@require_http_methods(["GET"])
def api_customer_address(request):
    """Get address for a specific customer"""
    card_code = request.GET.get('card_code')
    if not card_code:
        return JsonResponse({'error': 'card_code parameter required'}, status=400)
    
    try:
        db = get_hana_connection()
        if not db:
            return JsonResponse({'error': 'Database connection failed'}, status=500)
        
        # Query for address
        query = f"""
        SELECT T0."Address", T0."Street" 
        FROM CRD1 T0 
        WHERE T0."CardCode" = '{card_code}'
        """
        cursor = db.cursor()
        cursor.execute(query)
        result = cursor.fetchone()
        
        db.close()
        
        if result:
            return JsonResponse({
                'address': result[0],
                'street': result[1]
            })
        else:
            return JsonResponse({'address': '', 'street': ''})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@require_http_methods(["GET"])
def api_policy_link(request):
    """Get policy link for a project"""
    project_code = request.GET.get('project_code')
    if not project_code:
        return JsonResponse({'error': 'project_code parameter required'}, status=400)
    
    try:
        db = get_hana_connection()
        if not db:
            return JsonResponse({'error': 'Database connection failed'}, status=500)
        
        query = f"""
        SELECT a."DocEntry" 
        FROM "@PL1" a 
        WHERE a."U_proj" = '{project_code}'
        """
        cursor = db.cursor()
        cursor.execute(query)
        result = cursor.fetchone()
        
        db.close()
        return JsonResponse({'policy_link': result[0] if result else None})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@require_http_methods(["GET"])
def api_discounts(request):
    """Get discounts (U_AD, U_EXD) for policy, item, and policy link"""
    policy = request.GET.get('policy')
    item_code = request.GET.get('item_code')
    pl = request.GET.get('pl')
    
    if not all([policy, item_code, pl]):
        return JsonResponse({'error': 'policy, item_code, and pl parameters required'}, status=400)
    
    try:
        db = get_hana_connection()
        if not db:
            return JsonResponse({'error': 'Database connection failed'}, status=500)
        
        # Get U_AD
        query_ad = f"""
        SELECT b."U_ad" 
        FROM "@PL1" a 
        INNER JOIN "@PLR4" b ON a."DocEntry" = b."DocEntry" 
        WHERE a."U_proj" = '{policy}' 
        AND b."U_itc" = '{item_code}' 
        AND a."DocEntry" = {pl}
        """
        
        # Get U_EXD
        query_exd = f"""
        SELECT b."U_ed" 
        FROM "@PL1" a 
        INNER JOIN "@PLR4" b ON a."DocEntry" = b."DocEntry" 
        WHERE a."U_proj" = '{policy}' 
        AND b."U_itc" = '{item_code}' 
        AND a."DocEntry" = {pl}
        """
        
        cursor = db.cursor()
        cursor.execute(query_ad)
        result_ad = cursor.fetchone()
        
        cursor.execute(query_exd)
        result_exd = cursor.fetchone()
        
        db.close()
        
        return JsonResponse({
            'u_ad': float(result_ad[0]) if result_ad and result_ad[0] else 0.0,
            'u_exd': float(result_exd[0]) if result_exd and result_exd[0] else 0.0
        })
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@require_http_methods(["GET"])
def api_project_balance(request):
    """Get project balance (U_BP)"""
    project_code = request.GET.get('project_code')
    if not project_code:
        return JsonResponse({'error': 'project_code parameter required'}, status=400)
    
    try:
        db = get_hana_connection()
        if not db:
            return JsonResponse({'error': 'Database connection failed'}, status=500)
        
        query = f"""
        SELECT IFNULL(SUM(a."Debit" - a."Credit"), 0) 
        FROM jdt1 a 
        WHERE a."Project" = '{project_code}'
        """
        cursor = db.cursor()
        cursor.execute(query)
        result = cursor.fetchone()
        
        db.close()
        
        return JsonResponse({'u_bp': float(result[0]) if result else 0.0})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)