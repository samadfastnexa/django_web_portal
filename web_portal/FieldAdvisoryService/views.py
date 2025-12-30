from rest_framework import viewsets,permissions,filters, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.exceptions import PermissionDenied
from django_filters.rest_framework import DjangoFilterBackend
from django.core.paginator import Paginator
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.contrib.admin.views.decorators import staff_member_required

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
    queryset = MeetingSchedule.objects.select_related('region', 'zone', 'territory', 'staff').all()
    serializer_class = MeetingScheduleSerializer
    parser_classes = [MultiPartParser, FormParser]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    permission_classes = [IsAuthenticated, HasRolePermission]
    filterset_fields = ["fsm_name", "region", "zone", "territory", "location", "presence_of_zm", "presence_of_rsm", "staff"]
    search_fields = ["fsm_name", "region__name", "zone__name", "territory__name", "location", "key_topics_discussed"]
    ordering_fields = ["date", "fsm_name", "region__name", "zone__name", "territory__name", "total_attendees"]
    common_parameters = [
        openapi.Parameter('fsm_name', openapi.IN_FORM, type=openapi.TYPE_STRING, required=True, description='Field Sales Manager name'),
        openapi.Parameter('territory_id', openapi.IN_FORM, type=openapi.TYPE_INTEGER, required=False, description='Territory ID'),
        openapi.Parameter('zone_id', openapi.IN_FORM, type=openapi.TYPE_INTEGER, required=False, description='Zone ID'),
        openapi.Parameter('region_id', openapi.IN_FORM, type=openapi.TYPE_INTEGER, required=False, description='Region ID'),
        openapi.Parameter('date', openapi.IN_FORM, type=openapi.TYPE_STRING, format='date', required=True, description='Meeting date (YYYY-MM-DD)'),
        openapi.Parameter('location', openapi.IN_FORM, type=openapi.TYPE_STRING, required=True, description='Meeting location'),
        openapi.Parameter('total_attendees', openapi.IN_FORM, type=openapi.TYPE_INTEGER, required=False, description='Total number of attendees'),
        openapi.Parameter('key_topics_discussed', openapi.IN_FORM, type=openapi.TYPE_STRING, required=False, description='Key topics discussed'),
        openapi.Parameter('presence_of_zm', openapi.IN_FORM, type=openapi.TYPE_BOOLEAN, required=False, description='Presence of Zone Manager'),
        openapi.Parameter('presence_of_rsm', openapi.IN_FORM, type=openapi.TYPE_BOOLEAN, required=False, description='Presence of Regional Sales Manager'),
        openapi.Parameter('feedback_from_attendees', openapi.IN_FORM, type=openapi.TYPE_STRING, required=False, description='Feedback from attendees'),
        openapi.Parameter('suggestions_for_future', openapi.IN_FORM, type=openapi.TYPE_STRING, required=False, description='Suggestions for future'),
        openapi.Parameter('attendee_name', openapi.IN_FORM, type=openapi.TYPE_ARRAY, items=openapi.Items(type=openapi.TYPE_STRING), required=False, description='List of farmer names'),
        openapi.Parameter('attendee_contact', openapi.IN_FORM, type=openapi.TYPE_ARRAY, items=openapi.Items(type=openapi.TYPE_STRING), required=False, description='List of contact numbers'),
        openapi.Parameter('attendee_acreage', openapi.IN_FORM, type=openapi.TYPE_ARRAY, items=openapi.Items(type=openapi.TYPE_NUMBER), required=False, description='List of acreage values'),
        openapi.Parameter('attendee_crop', openapi.IN_FORM, type=openapi.TYPE_ARRAY, items=openapi.Items(type=openapi.TYPE_STRING), required=False, description='List of crops'),
        openapi.Parameter('attendee_farmer_id', openapi.IN_FORM, type=openapi.TYPE_ARRAY, items=openapi.Items(type=openapi.TYPE_STRING), required=False, description='List of farmer IDs to link existing farmers'),
    ]

    @swagger_auto_schema(
        operation_description="Retrieve a list of meeting schedules with FSM name, region, zone, territory, date, location, and attendee summary. Supports filtering by staff ID (to see specific user's records).",
        manual_parameters=[
            openapi.Parameter('staff', openapi.IN_QUERY, type=openapi.TYPE_INTEGER, required=False, description='Filter by Staff ID (User ID). Use to see specific user records.'),
            openapi.Parameter('fsm_name', openapi.IN_QUERY, type=openapi.TYPE_STRING, required=False, description='Filter by Field Sales Manager name'),
            openapi.Parameter('region', openapi.IN_QUERY, type=openapi.TYPE_INTEGER, required=False, description='Filter by Region ID'),
            openapi.Parameter('zone', openapi.IN_QUERY, type=openapi.TYPE_INTEGER, required=False, description='Filter by Zone ID'),
            openapi.Parameter('territory', openapi.IN_QUERY, type=openapi.TYPE_INTEGER, required=False, description='Filter by Territory ID'),
            openapi.Parameter('location', openapi.IN_QUERY, type=openapi.TYPE_STRING, required=False, description='Filter by Location'),
            openapi.Parameter('date', openapi.IN_QUERY, type=openapi.TYPE_STRING, format='date', required=False, description='Filter by Date (YYYY-MM-DD)'),
            openapi.Parameter('key_topics_discussed', openapi.IN_QUERY, type=openapi.TYPE_STRING, required=False, description='Filter by key topics'),
            openapi.Parameter('presence_of_zm', openapi.IN_QUERY, type=openapi.TYPE_BOOLEAN, required=False, description='Filter by presence of Zone Manager'),
            openapi.Parameter('presence_of_rsm', openapi.IN_QUERY, type=openapi.TYPE_BOOLEAN, required=False, description='Filter by presence of Regional Sales Manager'),
        ],
        responses={
            200: openapi.Response(
                description='List of meeting schedules',
                examples={
                    'application/json': [
                        {
                            'id': 1,
                            'fsm_name': 'Ahmed Ali',
                            'region_id': 1,
                            'zone_id': 1,
                            'territory_id': 1,
                            'date': '2024-01-15',
                            'location': 'Community Center',
                            'total_attendees': 25,
                            'key_topics_discussed': 'Crop rotation, pest management',
                            'presence_of_zm': True,
                            'presence_of_rsm': False,
                            'attendees': [
                                {
                                    'id': 1,
                                    'farmer_name': 'Farmer John',
                                    'contact_number': '+92-300-1234567',
                                    'acreage': 5.5,
                                    'crop': 'Wheat'
                                }
                            ]
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
        operation_description="Get detailed information of a specific meeting schedule including attendees.",
        responses={
            200: openapi.Response(
                description='Meeting schedule details',
                examples={
                    'application/json': {
                        'id': 1,
                        'fsm_name': 'Ahmed Ali',
                        'region_id': 1,
                        'zone_id': 1,
                        'territory_id': 1,
                        'date': '2024-01-15',
                        'location': 'Community Center',
                        'total_attendees': 25,
                        'key_topics_discussed': 'Crop rotation, pest management, irrigation techniques',
                        'presence_of_zm': True,
                        'presence_of_rsm': True,
                        'feedback_from_attendees': 'Informative session',
                        'suggestions_for_future': 'More demonstrations',
                        'attendees': [
                            {
                                'id': 1,
                                'farmer_name': 'Farmer John',
                                'contact_number': '+92-300-1234567',
                                'acreage': 5.5,
                                'crop': 'Wheat'
                            }
                        ]
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
        operation_description="Create a meeting schedule with FSM name, region, zone, territory, and attendees.",
        manual_parameters=common_parameters,
        request_body=None,
        responses={
            201: 'Meeting schedule created successfully',
            400: 'Bad Request - Invalid data provided'
        },
        tags=["14. MeetingSchedules"]
    )
    def create(self, request, *args, **kwargs):
        # Auto-assign the logged-in user as staff if not provided (though it's read-only now)
        # Note: In standard perform_create we usually do serializer.save(staff=self.request.user)
        return super().create(request, *args, **kwargs)

    def perform_create(self, serializer):
        user = self.request.user
        if not user or not user.is_authenticated:
            raise PermissionDenied("Authentication required to create meeting schedule.")

        if hasattr(user, "get_full_name") and callable(getattr(user, "get_full_name", None)):
            name = user.get_full_name() or getattr(user, "username", "") or getattr(user, "email", "")
        elif hasattr(user, "full_name"):
            name = getattr(user, "full_name") or getattr(user, "username", "") or getattr(user, "email", "")
        elif hasattr(user, "first_name") or hasattr(user, "last_name"):
            first = getattr(user, "first_name", "") or ""
            last = getattr(user, "last_name", "") or ""
            combined = f"{first} {last}".strip()
            name = combined or getattr(user, "username", "") or getattr(user, "email", "")
        else:
            name = getattr(user, "username", "") or getattr(user, "email", "") or str(getattr(user, "pk", ""))

        serializer.save(staff=user, fsm_name=name)

    @swagger_auto_schema(
        operation_description="Update all details of an existing meeting schedule (full update).",
        manual_parameters=common_parameters,
        request_body=None,
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
        manual_parameters=common_parameters,
        request_body=None,
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
        operation_description="""
        Create a new sales order linking a dealer with a meeting schedule.
        
        **All fields are optional** to make API easy for mobile developers.
        Provide only the fields you need - the system will handle defaults.
        
        Common fields for mobile apps:
        - staff: User ID creating the order
        - dealer: Dealer ID (optional)
        - schedule: Meeting schedule ID (optional)
        - card_code: Customer code (BP Code)
        - card_name: Customer name
        - comments: Order remarks
        
        All SAP-related fields (doc_date, doc_due_date, series, etc.) are optional.
        """,
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
        operation_description="""
        Update specific fields of a sales order (PATCH method).
        
        **All fields are optional** - send only the fields you want to update.
        Typically used for status changes, adding comments, or updating SAP posting information.
        
        Example: Update just the status
        ```json
        {
            "status": "entertained"
        }
        ```
        """,
        request_body=SalesOrderSerializer,
        responses={
            200: 'Sales order updated successfully',
            404: 'Sales order not found',
            400: 'Bad Request - Invalid data'
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

    @swagger_auto_schema(
        method='get',
        operation_description="""
        Get all sales orders created by a specific user/staff member.
        
        Pass the user ID as a URL parameter to filter sales orders by the staff who created them.
        Returns all sales orders with their details including status, customer info, and SAP posting status.
        
        Example: `/api/sales-orders/by-user/5/` returns all orders created by user with ID 5
        """,
        responses={
            200: openapi.Response(
                description='List of sales orders created by the specified user',
                schema=SalesOrderSerializer(many=True),
                examples={
                    'application/json': [
                        {
                            'id': 1,
                            'staff': 5,
                            'dealer': 2,
                            'card_code': 'C20000',
                            'card_name': 'ABC Traders',
                            'status': 'pending',
                            'is_posted_to_sap': False,
                            'created_at': '2024-01-15T10:30:00Z'
                        },
                        {
                            'id': 2,
                            'staff': 5,
                            'dealer': 3,
                            'card_code': 'C20001',
                            'card_name': 'XYZ Company',
                            'status': 'entertained',
                            'is_posted_to_sap': True,
                            'sap_doc_num': 123456,
                            'created_at': '2024-01-16T14:20:00Z'
                        }
                    ]
                }
            ),
            404: 'User not found or no orders exist for this user'
        },
        tags=["15. SalesOrders"]
    )
    @action(detail=False, methods=['get'], url_path='by-user/(?P<user_id>[^/.]+)')
    def by_user(self, request, user_id=None):
        """Get all sales orders created by a specific user"""
        try:
            # Validate user exists
            from django.contrib.auth import get_user_model
            User = get_user_model()
            
            try:
                user = User.objects.get(pk=user_id)
                # Handle different user models - some may not have get_full_name
                if hasattr(user, 'get_full_name') and callable(user.get_full_name):
                    user_name = user.get_full_name() or user.username
                elif hasattr(user, 'full_name'):
                    user_name = user.full_name or user.username
                elif hasattr(user, 'first_name') and hasattr(user, 'last_name'):
                    user_name = f"{user.first_name} {user.last_name}".strip() or user.username
                else:
                    user_name = user.username
            except User.DoesNotExist:
                return Response(
                    {'error': f'User with ID {user_id} not found'},
                    status=status.HTTP_404_NOT_FOUND
                )
            
            # Get all sales orders for this user
            orders = SalesOrder.objects.filter(staff=user).order_by('-created_at')
            
            if not orders.exists():
                return Response(
                    {
                        'message': f'No sales orders found for user {user_name} (ID: {user_id})',
                        'user_id': user_id,
                        'user_name': user_name,
                        'count': 0,
                        'orders': []
                    },
                    status=status.HTTP_200_OK
                )
            
            serializer = self.get_serializer(orders, many=True)
            
            return Response({
                'user_id': user_id,
                'user_name': user_name,
                'count': orders.count(),
                'orders': serializer.data
            }, status=status.HTTP_200_OK)
            
        except ValueError:
            return Response(
                {'error': 'Invalid user ID format. Must be a valid integer.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            return Response(
                {'error': f'Error retrieving sales orders: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


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
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['status', 'filer_status', 'card_type', 'is_posted_to_sap', 'requested_by']

    def get_queryset(self):
        user = self.request.user

        # Prevent error during swagger schema generation
        if getattr(self, 'swagger_fake_view', False):
            return DealerRequest.objects.none()

        if not user or not user.is_authenticated:
            # Return empty queryset for anonymous users or unauthenticated requests
            return DealerRequest.objects.none()

        base_qs = DealerRequest.objects.all() if (user.is_superuser or (hasattr(user, 'role') and user.role.name == 'Admin')) else DealerRequest.objects.filter(requested_by=user)

        # Support alias 'created_by' for filtering requested_by
        created_by = self.request.query_params.get('created_by')
        if created_by:
            try:
                base_qs = base_qs.filter(requested_by=int(created_by))
            except ValueError:
                base_qs = base_qs.none()

        return base_qs

    @swagger_auto_schema(
        operation_description="Submit a new dealer registration request with comprehensive business partner information including contact details, address, tax information, and SAP configuration. All fields are optional except requested_by (auto-filled).",
        request_body=DealerRequestSerializer,
        responses={
            201: openapi.Response(
                description='Dealer request submitted successfully',
                examples={
                    'application/json': {
                        'id': 1,
                        'business_name': 'Khan Agro Store',
                        'owner_name': 'Ahmed Ali Khan',
                        'contact_number': '+92-300-1234567',
                        'mobile_phone': '+92-300-1234567',
                        'email': 'ahmed@example.com',
                        'address': 'Main Bazaar, Village ABC',
                        'city': 'Lahore',
                        'state': 'Punjab',
                        'country': 'PK',
                        'cnic_number': '12345-6789012-3',
                        'federal_tax_id': 'NTN123456',
                        'filer_status': '01',
                        'status': 'draft',
                        'card_type': 'cCustomer',
                        'group_code': 100,
                        'sap_series': 70,
                        'minimum_investment': 500000,
                        'is_posted_to_sap': False,
                        'created_at': '2024-01-15T10:30:00Z'
                    }
                }
            ),
            400: 'Bad Request - Invalid data or missing required fields'
        },
        tags=["17. Dealer Requests"]
    )
    def create(self, request, *args, **kwargs):
        return super().create(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_description="Retrieve a list of dealer requests. Admins can see all requests; users only see their own. Supports filtering by status, filer_status, card_type, is_posted_to_sap, requested_by, and alias created_by.",
        manual_parameters=[
            openapi.Parameter('status', openapi.IN_QUERY, type=openapi.TYPE_STRING, description='Filter by status (draft, pending, approved, rejected, posted_to_sap)'),
            openapi.Parameter('filer_status', openapi.IN_QUERY, type=openapi.TYPE_STRING, description='Filter by filer_status (01 for Filer, 02 for Non-Filer)'),
            openapi.Parameter('card_type', openapi.IN_QUERY, type=openapi.TYPE_STRING, description='Filter by card_type (cCustomer, cSupplier, cLid)'),
            openapi.Parameter('is_posted_to_sap', openapi.IN_QUERY, type=openapi.TYPE_BOOLEAN, description='Filter by SAP posting status'),
            openapi.Parameter('requested_by', openapi.IN_QUERY, type=openapi.TYPE_INTEGER, description='Filter by requesting user ID'),
            openapi.Parameter('created_by', openapi.IN_QUERY, type=openapi.TYPE_INTEGER, description='Alias for requested_by; filters by creator user ID'),
        ],
        responses={
            200: openapi.Response(
                description='List of dealer requests',
                examples={
                    'application/json': [
                        {
                            'id': 1,
                            'business_name': 'Khan Agro Store',
                            'owner_name': 'Ahmed Ali Khan',
                            'contact_number': '+92-300-1234567',
                            'mobile_phone': '+92-300-1234567',
                            'email': 'ahmed@example.com',
                            'city': 'Lahore',
                            'state': 'Punjab',
                            'status': 'pending',
                            'filer_status': '01',
                            'card_type': 'cCustomer',
                            'is_posted_to_sap': False,
                            'sap_card_code': None,
                            'minimum_investment': 500000,
                            'created_at': '2024-01-15T10:30:00Z'
                        },
                        {
                            'id': 2,
                            'business_name': 'Modern Seeds Shop',
                            'owner_name': 'Bilal Hassan',
                            'contact_number': '+92-321-9876543',
                            'status': 'posted_to_sap',
                            'filer_status': '02',
                            'is_posted_to_sap': True,
                            'sap_card_code': 'C000123',
                            'posted_at': '2024-01-20T15:45:00Z',
                            'created_at': '2024-01-18T09:15:00Z'
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
        operation_description="Retrieve detailed information of a specific dealer request including all business partner fields, SAP configuration, integration status, and submitted documents.",
        responses={
            200: openapi.Response(
                description='Dealer request details with comprehensive SAP Business Partner information',
                examples={
                    'application/json': {
                        'id': 1,
                        'requested_by': 5,
                        'status': 'posted_to_sap',
                        'reason': 'New dealer in territory 45',
                        'business_name': 'Khan Agro Store',
                        'owner_name': 'Ahmed Ali Khan',
                        'contact_number': '+92-300-1234567',
                        'mobile_phone': '+92-300-1234567',
                        'email': 'ahmed@khanagrostore.com',
                        'address': 'Main Bazaar, Village ABC, District XYZ',
                        'city': 'Lahore',
                        'state': 'Punjab',
                        'country': 'PK',
                        'cnic_number': '12345-6789012-3',
                        'federal_tax_id': 'NTN1234567',
                        'additional_id': 'STRN9876543',
                        'unified_federal_tax_id': 'UFTN1234567',
                        'filer_status': '01',
                        'govt_license_number': 'LIC-2024-001',
                        'license_expiry': '2025-12-31',
                        'u_leg': '17-5349',
                        'cnic_front': '/media/dealer_requests/cnic_front/image1.jpg',
                        'cnic_back': '/media/dealer_requests/cnic_back/image2.jpg',
                        'company': 1,
                        'region': 5,
                        'zone': 12,
                        'territory': 45,
                        'sap_series': 70,
                        'card_type': 'cCustomer',
                        'group_code': 100,
                        'debitor_account': 'A020301001',
                        'vat_group': 'AT1',
                        'vat_liable': 'vLiable',
                        'whatsapp_messages': 'YES',
                        'minimum_investment': 500000,
                        'is_posted_to_sap': True,
                        'sap_card_code': 'C000123',
                        'sap_doc_entry': 456789,
                        'sap_error': None,
                        'posted_at': '2024-01-20T15:45:00Z',
                        'created_at': '2024-01-15T10:30:00Z',
                        'updated_at': '2024-01-20T15:45:00Z',
                        'reviewed_at': '2024-01-20T14:30:00Z',
                        'reviewed_by': 2
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
        operation_description="Update a dealer request with complete business partner information. Typically used by admins to approve/reject requests or modify SAP configuration. When status changes to 'approved' or 'posted_to_sap', the system automatically creates the Business Partner in SAP.",
        request_body=DealerRequestSerializer,
        responses={
            200: openapi.Response(
                description='Dealer request updated successfully. If approved, SAP Business Partner is created automatically.',
                examples={
                    'application/json': {
                        'id': 1,
                        'status': 'posted_to_sap',
                        'business_name': 'Khan Agro Store',
                        'is_posted_to_sap': True,
                        'sap_card_code': 'C000123',
                        'sap_doc_entry': 456789,
                        'posted_at': '2024-01-20T15:45:00Z',
                        'message': 'Dealer request approved and Business Partner created in SAP'
                    }
                }
            ),
            400: 'Bad Request - Invalid data',
            404: 'Dealer request not found',
            403: 'Forbidden - Insufficient permissions'
        },
        tags=["17. Dealer Requests"]
    )
    def update(self, request, *args, **kwargs):
        return super().update(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_description="Partially update specific fields of a dealer request. All fields are optional. Useful for updating contact info, address, tax details, or SAP configuration without sending the entire object. Status change to 'approved' or 'posted_to_sap' triggers SAP Business Partner creation.",
        request_body=DealerRequestSerializer,
        responses={
            200: openapi.Response(
                description='Dealer request fields updated successfully',
                examples={
                    'application/json': {
                        'id': 1,
                        'status': 'pending',
                        'email': 'newemail@example.com',
                        'mobile_phone': '+92-321-9999999',
                        'city': 'Karachi',
                        'updated_at': '2024-01-21T10:15:00Z'
                    }
                }
            ),
            400: 'Bad Request - Invalid field values',
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
    filterset_fields = ['zone', 'company']
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

    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):
            return Territory.objects.none()
        qs = super().get_queryset()
        company_param = self.request.query_params.get('company')
        if company_param:
            try:
                cid = int(company_param)
                return qs.filter(company_id=cid)
            except Exception:
                pass
        db_key = self.request.session.get('selected_db', '4B-BIO')
        schema = '4B-BIO_APP' if db_key == '4B-BIO' else ('4B-ORANG_APP' if db_key == '4B-ORANG' else '4B-BIO_APP')
        try:
            from FieldAdvisoryService.models import Company
            comp = Company.objects.filter(name=schema).first() or Company.objects.filter(Company_name=schema).first()
            if comp:
                return qs.filter(company=comp)
        except Exception:
            pass
        return qs


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
from django.contrib.admin.views.decorators import staff_member_required
from django.views.decorators.csrf import csrf_exempt
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

def get_hana_connection(request=None, selected_db_key=None):
    """Get HANA database connection honoring the selected DB (session/global dropdown)."""
    try:
        # Load .env file
        _load_env_file(os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), '.env'))
        try:
            from django.conf import settings as _settings
            _load_env_file(os.path.join(str(_settings.BASE_DIR), '.env'))
            from pathlib import Path as _Path
            _load_env_file(os.path.join(str(_Path(_settings.BASE_DIR).parent), '.env'))
            _load_env_file(os.path.join(os.getcwd(), '.env'))
        except Exception:
            pass
        
        from hdbcli import dbapi
        from preferences.models import Setting

        if not selected_db_key and request and hasattr(request, 'session'):
            selected_db_key = request.session.get('selected_db')

        # Get database name from settings, preferring selected_db_key when provided
        try:
            db_setting = Setting.objects.filter(slug='SAP_COMPANY_DB').first()
            raw_value = getattr(db_setting, 'value', None) if db_setting else None
            schema = os.environ.get('HANA_SCHEMA') or os.environ.get('SAP_COMPANY_DB', '4B-BIO_APP')
            db_options = {}

            if isinstance(raw_value, dict):
                db_options = raw_value
            elif isinstance(raw_value, str):
                try:
                    import json
                    parsed = json.loads(raw_value)
                    if isinstance(parsed, dict):
                        db_options = parsed
                    else:
                        schema = str(parsed)
                except Exception:
                    schema = raw_value

            cleaned = {}
            for k, v in db_options.items():
                clean_key = str(k).strip().strip('"').strip("'")
                clean_val = str(v).strip().strip('"').strip("'")
                cleaned[clean_key] = clean_val
            db_options = cleaned

            if db_options:
                if selected_db_key and selected_db_key in db_options:
                    schema = db_options[selected_db_key]
                else:
                    schema = list(db_options.values())[0]
            elif raw_value and not isinstance(raw_value, dict):
                schema = str(raw_value).strip().strip('"').strip("'")
        except Exception as e:
            print(f"Error getting schema from settings: {e}")
            schema = os.environ.get('HANA_SCHEMA') or os.environ.get('SAP_COMPANY_DB', '4B-BIO_APP')
            if selected_db_key:
                key_upper = str(selected_db_key).upper()
                if key_upper.startswith('4B-ORANG'):
                    schema = '4B-ORANG_APP'
                elif key_upper.startswith('4B-BIO'):
                    schema = '4B-BIO_APP'

        # Strip quotes if present
        schema = schema.strip('"\'')
        
        # Connection parameters
        host = os.environ.get('HANA_HOST', '').strip()
        port = int(os.environ.get('HANA_PORT', 30015))
        user = os.environ.get('HANA_USER', '').strip()
        password = os.environ.get('HANA_PASSWORD', '').strip()
        encrypt = (os.environ.get('HANA_ENCRYPT') or '').strip().lower() in ('true','1','yes')
        ssl_validate = (os.environ.get('HANA_SSL_VALIDATE') or '').strip().lower() in ('true','1','yes')
        
        if not host or not user:
            return None
        
        # Connect
        kwargs = {'address': host, 'port': port, 'user': user, 'password': password}
        if encrypt:
            kwargs['encrypt'] = True
            kwargs['sslValidateCertificate'] = ssl_validate
        conn = dbapi.connect(**kwargs)
        
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
        db = get_hana_connection(request)
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
        db = get_hana_connection(request)
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
        db = get_hana_connection(request)
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
        db = get_hana_connection(request)
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
        db = get_hana_connection(request)
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


@staff_member_required
@require_http_methods(["GET"])
def api_child_customers(request):
    """Get child customers for a parent customer (FatherCard)"""
    import logging
    logger = logging.getLogger(__name__)
    
    father_card = request.GET.get('father_card')
    search = (request.GET.get('search') or '').strip()
    page_param = (request.GET.get('page') or '1').strip()
    page_size_param = (request.GET.get('page_size') or '').strip()
    logger.info(f"API called for child customers: father_card={father_card}, search={search}, page={page_param}, page_size={page_size_param}")
    
    if not father_card:
        logger.error("No father_card provided")
        return JsonResponse({'error': 'father_card parameter required'}, status=400)
    
    try:
        db = get_hana_connection(request)
        if not db:
            logger.error("Database connection failed")
            return JsonResponse({'error': 'Database connection failed - HANA service unavailable', 'children': []}, status=200)
        
        logger.info(f"Database connected, fetching child customers for {father_card}")
        
        # Get child customers with optional search
        try:
            child_customers = hana_connect.child_card_code(db, father_card, search or None)
        except Exception as e:
            logger.error(f"Error calling child_card_code: {str(e)}")
            child_customers = []
        finally:
            try:
                db.close()
            except:
                pass

        # Return empty list if no children found
        if not child_customers:
            logger.info(f"No child customers found for {father_card}")
            return JsonResponse({
                'children': [],
                'page': 1,
                'page_size': 10,
                'num_pages': 0,
                'count': 0
            })

        # Pagination
        try:
            page_num = int(page_param) if page_param else 1
        except Exception:
            page_num = 1
        default_page_size = 10
        try:
            default_page_size = int(getattr(settings, 'REST_FRAMEWORK', {}).get('PAGE_SIZE', 10) or 10)
        except Exception:
            default_page_size = 10
        try:
            page_size = int(page_size_param) if page_size_param else default_page_size
        except Exception:
            page_size = default_page_size

        paginator = Paginator(child_customers or [], page_size)
        page_obj = paginator.get_page(page_num)
        logger.info(f"Found {paginator.count} child customers, returning page {page_obj.number}/{paginator.num_pages}")

        return JsonResponse({
            'children': list(page_obj.object_list),
            'page': page_obj.number,
            'page_size': page_size,
            'num_pages': paginator.num_pages,
            'count': paginator.count
        })
        
    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        logger.error(f"Error in api_child_customers: {str(e)}\n{error_trace}")
        return JsonResponse({'error': str(e), 'trace': error_trace, 'children': []}, status=200)

@staff_member_required
@require_http_methods(["GET"])
def api_customer_details(request):
    """Get full customer details (CardName, ContactPersonCode, FederalTaxID, PayToCode, Address)"""
    import logging
    logger = logging.getLogger(__name__)
    
    card_code = request.GET.get('card_code')
    logger.info(f"API called for customer details: card_code={card_code}")
    
    if not card_code:
        logger.error("No card_code provided")
        return JsonResponse({'error': 'card_code parameter required'}, status=400)
    
    try:
        db = get_hana_connection(request)
        if not db:
            logger.error("Database connection failed")
            return JsonResponse({'error': 'Database connection failed'}, status=500)
        
        logger.info(f"Database connected, fetching details for {card_code}")
        
        # Get customer basic info
        cursor = db.cursor()
        customer_query = """
        SELECT 
            T0."CardName", 
            T0."CntctPrsn",
            T0."LicTradNum",
            T0."BillToDef",
            T0."Address"
        FROM OCRD T0 
        WHERE T0."CardCode" = ?
        """
        cursor.execute(customer_query, (card_code,))
        customer_result = cursor.fetchone()
        
        logger.info(f"Customer query result: {customer_result}")
        
        if not customer_result:
            cursor.close()
            db.close()
            logger.warning(f"Customer not found: {card_code}")
            return JsonResponse({'error': f'Customer not found: {card_code}'}, status=404)
        
        # Get contact person code from OCPR table
        contact_code = None
        if customer_result[1]:  # If CntctPrsn (contact name) exists
            contact_query = """
            SELECT T0."CntctCode"
            FROM OCPR T0
            WHERE T0."CardCode" = ? AND T0."Name" = ?
            """
            cursor.execute(contact_query, (card_code, customer_result[1]))
            contact_result = cursor.fetchone()
            if contact_result:
                contact_code = int(contact_result[0])
        
        # Get billing address from CRD1
        address = customer_result[4]  # Use Address from OCRD first
        if not address or address.strip() == '':
            # Try to get formatted address from CRD1
            address_query = """
            SELECT 
                T0."Street"||', '||T2."Name" AS "Address"
            FROM CRD1 T0 
            INNER JOIN OCRD T1 ON T0."CardCode" = T1."CardCode" AND T0."Address" = T1."BillToDef"
            INNER JOIN OCRY T2 ON T1."Country" = T2."Code"
            WHERE T1."CardCode" = ?
            """
            cursor.execute(address_query, (card_code,))
            address_result = cursor.fetchone()
            if address_result:
                address = address_result[0]
        
        logger.info(f"Address query result: {address}")
        
        cursor.close()
        db.close()
        
        # Parse the results safely
        card_name = customer_result[0] if customer_result[0] else ''
        federal_tax_id = customer_result[2] if customer_result[2] else ''
        
        # Handle pay_to_code (BillToDef) - might be string or int
        pay_to_code = None
        if customer_result[3]:
            try:
                pay_to_code = int(customer_result[3]) if customer_result[3] else None
            except (ValueError, TypeError):
                # If it's already a string address code, keep it
                pay_to_code = customer_result[3]
        
        response_data = {
            'card_name': card_name,
            'contact_person_code': contact_code if contact_code else '',
            'federal_tax_id': federal_tax_id,
            'pay_to_code': pay_to_code if pay_to_code else '',
            'address': address if address else ''
        }
        
        logger.info(f"Returning response: {response_data}")
        return JsonResponse(response_data)
        
    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        logger.error(f"Error in api_customer_details: {str(e)}\n{error_trace}")
        return JsonResponse({'error': str(e), 'trace': error_trace}, status=500)
