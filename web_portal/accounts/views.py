from rest_framework import generics, permissions, viewsets
from rest_framework.permissions import AllowAny, IsAuthenticated, BasePermission,DjangoModelPermissions
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from rest_framework.exceptions import PermissionDenied
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from rest_framework.filters import OrderingFilter
from .models import Role
from rest_framework import status
from rest_framework.response import Response
from .serializers import (
    UserSignupSerializer,
    UserListSerializer,
    RoleSerializer,
    UserSerializer,
    AdminUserStatusSerializer,
    UserUpdateSerializer,
    PermissionSerializer,
    SalesStaffSerializer
)
from .models import SalesStaffProfile
from rest_framework.permissions import IsAuthenticated
from .permissions import HasRolePermission
from rest_framework.decorators import action, api_view, permission_classes, parser_classes
from .token_serializers import MyTokenObtainPairSerializer
from .permissions import IsOwnerOrAdmin
from .filters import UserFilter
from django_filters.rest_framework import DjangoFilterBackend
import re

User = get_user_model()


class RoleViewSet(viewsets.ModelViewSet):
    queryset = Role.objects.all()
    serializer_class = RoleSerializer
    permission_classes = [IsAuthenticated, HasRolePermission]


@swagger_auto_schema(
    method='get',
    operation_summary="User territories and SAP empID",
    operation_description=(
        "Given a portal user ID, return the user's sales territories from the local DB "
        "and the SAP empID derived from SalesStaffProfile.employee_code. "
        "Returns nested structure: Company > Region > Zone > Territories."
    ),
    manual_parameters=[
        openapi.Parameter(
            'user_id',
            openapi.IN_PATH,
            description='Portal user ID (primary key of accounts.User)',
            type=openapi.TYPE_INTEGER,
            required=True,
        ),
    ],
    responses={
        200: openapi.Response(description="Nested territories structure with empID for the given user"),
        404: openapi.Response(description="User or sales profile not found"),
        403: openapi.Response(description="Forbidden"),
    },
    tags=["02. User Management"],
)
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def user_territories_emp_api(request, user_id: int):
    try:
        profile = (
            SalesStaffProfile.objects
            .select_related('user')
            .prefetch_related(
                'companies',
                'regions__company',
                'zones__region__company',
                'territories__zone__region__company'
            )
            .get(user_id=user_id)
        )
    except SalesStaffProfile.DoesNotExist:
        return Response(
            {'success': False, 'error': 'Sales profile not found for this user'},
            status=status.HTTP_404_NOT_FOUND,
        )

    if not (request.user.is_staff or request.user.is_superuser) and request.user.id != user_id:
        raise PermissionDenied("You are not allowed to view territories for this user")

    emp_id = user_id

    # Build nested hierarchy: Company > Region > Zone > Territory
    companies_dict = {}
    
    # Process territories and build hierarchy
    for territory in profile.territories.all():
        zone = getattr(territory, 'zone', None)
        if not zone:
            continue
            
        region = getattr(zone, 'region', None)
        if not region:
            continue
            
        company = getattr(region, 'company', None)
        if not company:
            continue
        
        # Initialize company if not exists
        if company.id not in companies_dict:
            companies_dict[company.id] = {
                'id': company.id,
                'name': company.name,
                'regions': {}
            }
        
        # Initialize region if not exists
        if region.id not in companies_dict[company.id]['regions']:
            companies_dict[company.id]['regions'][region.id] = {
                'id': region.id,
                'name': region.name,
                'zones': {}
            }
        
        # Initialize zone if not exists
        if zone.id not in companies_dict[company.id]['regions'][region.id]['zones']:
            companies_dict[company.id]['regions'][region.id]['zones'][zone.id] = {
                'id': zone.id,
                'name': zone.name,
                'territories': []
            }
        
        # Add territory
        companies_dict[company.id]['regions'][region.id]['zones'][zone.id]['territories'].append({
            'id': territory.id,
            'name': territory.name,
        })
    
    # Convert nested dicts to lists
    companies_list = []
    for company_data in companies_dict.values():
        regions_list = []
        for region_data in company_data['regions'].values():
            zones_list = []
            for zone_data in region_data['zones'].values():
                zones_list.append(zone_data)
            region_data['zones'] = zones_list
            regions_list.append(region_data)
        company_data['regions'] = regions_list
        companies_list.append(company_data)

    return Response({
        'success': True,
        'user_id': user_id,
        'employee_code': profile.employee_code,
        'emp_id': emp_id,
        'companies': companies_list,
    }, status=status.HTTP_200_OK)

# ✅ Signup View
class SignupView(generics.CreateAPIView):
    queryset = User.objects.all()
    serializer_class = UserSignupSerializer
    permission_classes = [AllowAny]
    parser_classes = [MultiPartParser, FormParser]

    @swagger_auto_schema(
        operation_description="Register a new user account. For sales staff registration, set is_sales_staff=true and provide all required sales profile information including designation, employee details, and geographical assignments.",
        manual_parameters=[
            openapi.Parameter(
                'username',
                openapi.IN_FORM,
                description='Unique username for login (3-150 characters, letters, digits, @/./+/-/_ only)',
                type=openapi.TYPE_STRING,
                required=True
            ),
            openapi.Parameter(
                'email',
                openapi.IN_FORM,
                description='Valid email address for account verification and communication',
                type=openapi.TYPE_STRING,
                required=True
            ),
            openapi.Parameter(
                'password',
                openapi.IN_FORM,
                description='Strong password (minimum 8 characters recommended)',
                type=openapi.TYPE_STRING,
                required=True
            ),
            openapi.Parameter(
                'first_name',
                openapi.IN_FORM,
                description='User\'s first name (letters and spaces only)',
                type=openapi.TYPE_STRING,
                required=True
            ),
            openapi.Parameter(
                'last_name',
                openapi.IN_FORM,
                description='User\'s last name (letters and spaces only)',
                type=openapi.TYPE_STRING,
                required=True
            ),
            openapi.Parameter(
                'profile_image',
                openapi.IN_FORM,
                description='Optional profile picture (JPEG, PNG formats supported)',
                type=openapi.TYPE_FILE,
                required=False
            ),
            openapi.Parameter(
                'role',
                openapi.IN_FORM,
                description='Role ID for user permissions (get available roles from /api/roles/)',
                type=openapi.TYPE_INTEGER,
                required=False
            ),
            openapi.Parameter(
                'is_sales_staff',
                openapi.IN_FORM,
                description='Set to true if registering a sales staff member (requires additional fields below)',
                type=openapi.TYPE_BOOLEAN,
                required=False
            ),
            openapi.Parameter(
                'is_dealer',
                openapi.IN_FORM,
                description='Set to true if registering a dealer account',
                type=openapi.TYPE_BOOLEAN,
                required=False
            ),
            # Dealer-specific fields (required if is_dealer=true)
            openapi.Parameter(
                'dealer_business_name',
                openapi.IN_FORM,
                description='Business/Company Name (required if is_dealer=true)',
                type=openapi.TYPE_STRING,
                required=False
            ),
            openapi.Parameter(
                'dealer_cnic_number',
                openapi.IN_FORM,
                description='CNIC Number (13 or 15 digits, required if is_dealer=true)',
                type=openapi.TYPE_STRING,
                required=False
            ),
            openapi.Parameter(
                'dealer_contact_number',
                openapi.IN_FORM,
                description='Primary Contact Number (required if is_dealer=true)',
                type=openapi.TYPE_STRING,
                required=False
            ),
            openapi.Parameter(
                'dealer_mobile_phone',
                openapi.IN_FORM,
                description='Mobile/WhatsApp Number',
                type=openapi.TYPE_STRING,
                required=False
            ),
            openapi.Parameter(
                'dealer_company_id',
                openapi.IN_FORM,
                description='Company ID (required if is_dealer=true)',
                type=openapi.TYPE_INTEGER,
                required=False
            ),
            openapi.Parameter(
                'dealer_region_id',
                openapi.IN_FORM,
                description='Region ID',
                type=openapi.TYPE_INTEGER,
                required=False
            ),
            openapi.Parameter(
                'dealer_zone_id',
                openapi.IN_FORM,
                description='Zone ID',
                type=openapi.TYPE_INTEGER,
                required=False
            ),
            openapi.Parameter(
                'dealer_territory_id',
                openapi.IN_FORM,
                description='Territory ID',
                type=openapi.TYPE_INTEGER,
                required=False
            ),
            openapi.Parameter(
                'dealer_address',
                openapi.IN_FORM,
                description='Full Address (required if is_dealer=true)',
                type=openapi.TYPE_STRING,
                required=False
            ),
            openapi.Parameter(
                'dealer_city',
                openapi.IN_FORM,
                description='City',
                type=openapi.TYPE_STRING,
                required=False
            ),
            openapi.Parameter(
                'dealer_state',
                openapi.IN_FORM,
                description='State/Province',
                type=openapi.TYPE_STRING,
                required=False
            ),
            openapi.Parameter(
                'dealer_federal_tax_id',
                openapi.IN_FORM,
                description='NTN Number (National Tax Number)',
                type=openapi.TYPE_STRING,
                required=False
            ),
            openapi.Parameter(
                'dealer_filer_status',
                openapi.IN_FORM,
                description='Tax Filer Status',
                type=openapi.TYPE_STRING,
                required=False,
                enum=['01', '02']
            ),
            openapi.Parameter(
                'dealer_govt_license_number',
                openapi.IN_FORM,
                description='Government License Number',
                type=openapi.TYPE_STRING,
                required=False
            ),
            openapi.Parameter(
                'dealer_license_expiry',
                openapi.IN_FORM,
                description='License Expiry Date (YYYY-MM-DD)',
                type=openapi.TYPE_STRING,
                format='date',
                required=False
            ),
            openapi.Parameter(
                'dealer_minimum_investment',
                openapi.IN_FORM,
                description='Minimum Investment Amount',
                type=openapi.TYPE_INTEGER,
                required=False
            ),
            openapi.Parameter(
                'dealer_cnic_front_image',
                openapi.IN_FORM,
                description='CNIC Front Image (JPEG, PNG)',
                type=openapi.TYPE_FILE,
                required=False
            ),
            openapi.Parameter(
                'dealer_cnic_back_image',
                openapi.IN_FORM,
                description='CNIC Back Image (JPEG, PNG)',
                type=openapi.TYPE_FILE,
                required=False
            ),
            openapi.Parameter(
                'employee_code',
                openapi.IN_FORM,
                description='Unique employee identification code (required if is_sales_staff=true)',
                type=openapi.TYPE_STRING,
                required=False
            ),
            openapi.Parameter(
                'phone_number',
                openapi.IN_FORM,
                description='Contact phone number (required if is_sales_staff=true)',
                type=openapi.TYPE_STRING,
                required=False
            ),
            openapi.Parameter(
                'address',
                openapi.IN_FORM,
                description='Full address (required if is_sales_staff=true)',
                type=openapi.TYPE_STRING,
                required=False
            ),
            openapi.Parameter(
                'designation',
                openapi.IN_FORM,
                description='Job designation (required if is_sales_staff=true). Valid choices: CEO, NSM, RSL, DRSL, ZM, DPL, SR_PL, PL, SR_FSM, FSM, SR_MTO, MTO',
                type=openapi.TYPE_STRING,
                required=False,
                enum=['CEO', 'NSM', 'RSL', 'DRSL', 'ZM', 'DPL', 'SR_PL', 'PL', 'SR_FSM', 'FSM', 'SR_MTO', 'MTO']
            ),
            openapi.Parameter(
                'companies',
                openapi.IN_FORM,
                description='List of company IDs assigned to this sales staff (comma-separated)',
                type=openapi.TYPE_STRING,
                required=False
            ),
            openapi.Parameter(
                'regions',
                openapi.IN_FORM,
                description='List of region IDs assigned to this sales staff (comma-separated)',
                type=openapi.TYPE_STRING,
                required=False
            ),
            openapi.Parameter(
                'zones',
                openapi.IN_FORM,
                description='List of zone IDs assigned to this sales staff (comma-separated)',
                type=openapi.TYPE_STRING,
                required=False
            ),
            openapi.Parameter(
                'territories',
                openapi.IN_FORM,
                description='List of territory IDs assigned to this sales staff (comma-separated)',
                type=openapi.TYPE_STRING,
                required=False
            ),
            openapi.Parameter(
                'hod',
                openapi.IN_FORM,
                description='Head of Department - ID of supervising sales staff member',
                type=openapi.TYPE_INTEGER,
                required=False
            ),
            openapi.Parameter(
                'master_hod',
                openapi.IN_FORM,
                description='Master Head of Department - ID of senior supervising sales staff member',
                type=openapi.TYPE_INTEGER,
                required=False
            ),
            openapi.Parameter(
                'sick_leave_quota',
                openapi.IN_FORM,
                description='Annual sick leave quota in days (default: 10)',
                type=openapi.TYPE_INTEGER,
                required=False
            ),
            openapi.Parameter(
                'casual_leave_quota',
                openapi.IN_FORM,
                description='Annual casual leave quota in days (default: 15)',
                type=openapi.TYPE_INTEGER,
                required=False
            ),
            openapi.Parameter(
                'others_leave_quota',
                openapi.IN_FORM,
                description='Annual other leave quota in days (default: 5)',
                type=openapi.TYPE_INTEGER,
                required=False
            )
        ],
        responses={
            201: openapi.Response(
                description='User registered successfully',
                examples={
                    'application/json': {
                        'id': 123,
                        'username': 'john_doe123',
                        'email': 'john.doe@company.com',
                        'first_name': 'John',
                        'last_name': 'Doe',
                        'is_sales_staff': True,
                        'is_dealer': False,
                        'is_active': True,
                        'date_joined': '2024-01-15T10:30:00Z',
                        'sales_profile': {
                            'employee_code': 'EMP001',
                            'designation': 'MTO',
                            'phone_number': '+1234567890'
                        },
                        'dealer': None
                    }
                }
            ),
            400: openapi.Response(
                description='Bad Request - Validation errors',
                examples={
                    'application/json': {
                        'username': ['A user with that username already exists.'],
                        'email': ['User with this email already exists.'],
                        'designation': ['Value "invalid_choice" is not a valid choice.']
                    }
                }
            )
        },
        tags=["01. Authentication"]
    )
    def post(self, request, *args, **kwargs):
        return self.create(request, *args, **kwargs)


# ✅ JWT Login View
# class MyTokenObtainPairView(TokenObtainPairView):
#     serializer_class = MyTokenObtainPairSerializer

#     @swagger_auto_schema(
#         operation_description="Authenticate user and obtain JWT tokens",
#         request_body=MyTokenObtainPairSerializer,  # 👈 important
#         tags=["Authentication"]
#     )
#     def post(self, request, *args, **kwargs):
#         return super().post(request, *args, **kwargs)

class MyTokenObtainPairView(TokenObtainPairView):
    serializer_class = MyTokenObtainPairSerializer

    @swagger_auto_schema(
        operation_description="""
        Authenticate user and obtain JWT tokens.
        
        **Three login methods are supported:**
        
        1. **Email Login**: Use email and password (all user types)
        2. **Phone Number Login**: Use phone number and password (all user types)
        3. **Username Login**: Use username and password (farmers use phone as username)
        
        **Phone Number Sources by User Type:**
        
        | User Type | Phone Field | Example |
        |-----------|-------------|---------|
        | **Farmer** | `User.username` | Login with phone as username |
        | **Sales Staff** | `SalesStaffProfile.phone_number` | Login with profile phone |
        | **Dealer** | `Dealer.contact_number` or `mobile_phone` | Login with either phone |
        
        **Important Notes:**
        - You must provide either email OR phone_number (not both required)
        - Password is always required
        - Phone numbers must be registered in the system
        - Login is case-insensitive for email
        - Farmers: Phone auto-saved as username during registration
        
        **Default Passwords:**
        - Farmers: Last 4 digits of CNIC (auto-set)
        - Others: Set during user creation
        
        **Examples:**
        
        Farmer login with phone:
        ```json
        {
            "phone_number": "03001234567",
            "password": "1234"
        }
        ```
        
        Email login:
        ```json
        {
            "email": "user@example.com",
            "password": "your_password"
        }
        ```
        
        Phone number login:
        ```json
        {
            "phone_number": "03001234567",
            "password": "your_password"
        }
        ```
        """,
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'email': openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description='User email address (optional if phone_number is provided)',
                    example='user@example.com'
                ),
                'phone_number': openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description='User phone number - works for Farmers, Sales Staff, and Dealers (optional if email is provided)',
                    example='03001234567'
                ),
                'password': openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description='User password (required)',
                    format='password',
                    example='your_password'
                ),
            },
            required=['password'],
        ),
        responses={
            200: openapi.Response(
                description='Login successful - Returns JWT tokens and user information',
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'refresh': openapi.Schema(type=openapi.TYPE_STRING, description='Refresh token for obtaining new access tokens'),
                        'access': openapi.Schema(type=openapi.TYPE_STRING, description='Access token for API authentication'),
                        'user_id': openapi.Schema(type=openapi.TYPE_INTEGER, description='User ID'),
                        'email': openapi.Schema(type=openapi.TYPE_STRING, description='User email'),
                        'username': openapi.Schema(type=openapi.TYPE_STRING, description='Username'),
                        'phone_number': openapi.Schema(type=openapi.TYPE_STRING, description='User phone number', nullable=True),
                        'company': openapi.Schema(type=openapi.TYPE_STRING, description='Company name', nullable=True),
                        'company_id': openapi.Schema(type=openapi.TYPE_INTEGER, description='Company ID', nullable=True),
                        'role': openapi.Schema(type=openapi.TYPE_STRING, description='User role name'),
                        'permissions': openapi.Schema(
                            type=openapi.TYPE_ARRAY, 
                            description='User permissions',
                            items=openapi.Schema(type=openapi.TYPE_OBJECT)
                        ),
                        'companies': openapi.Schema(
                            type=openapi.TYPE_ARRAY, 
                            description='Associated companies',
                            items=openapi.Schema(type=openapi.TYPE_OBJECT)
                        ),
                        'default_company': openapi.Schema(type=openapi.TYPE_OBJECT, description='Default company'),
                    }
                )
            ),
            400: openapi.Response(
                description='Bad Request - Invalid credentials or missing required fields',
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'message': openapi.Schema(
                            type=openapi.TYPE_STRING, 
                            description='Error message',
                            example='Invalid email/phone number or password.'
                        )
                    }
                )
            ),
        },
        tags=["01. Authentication"]
    )
    def post(self, request, *args, **kwargs):
        return super().post(request, *args, **kwargs)

    def handle_exception(self, exc):
        response = super().handle_exception(exc)

        # Flatten {"message": ["..."]} → {"message": "..."}
        if response.status_code == status.HTTP_400_BAD_REQUEST:
            if isinstance(response.data, dict) and "message" in response.data:
                msg = response.data["message"]
                if isinstance(msg, list) and msg:
                    response.data["message"] = msg[0]
                else:
                    response.data["message"] = str(msg)

        return response


# # ✅ List all users (requires view_user permission)
# class UserListAPIView(generics.ListAPIView):
#     queryset = User.objects.all()
#     serializer_class = UserListSerializer
#     permission_classes = [IsAuthenticated, HasRolePermission]
#     required_permission = 'view_user'
#     # ✅ Add filter backend and filter class
#     filter_backends = [DjangoFilterBackend, OrderingFilter]
#     filterset_class = UserFilter
#     ordering_fields = ['id', 'email', 'username', 'first_name', 'last_name', 'is_active', 'role']
#     ordering = ['id']  # Optional: default ordering
#     @swagger_auto_schema(
#     tags=["User management"],
#     manual_parameters=[
#         openapi.Parameter('email', openapi.IN_QUERY, type=openapi.TYPE_STRING, description="Filter by email"),
#         openapi.Parameter('username', openapi.IN_QUERY, type=openapi.TYPE_STRING, description="Filter by username"),
#         openapi.Parameter('is_active', openapi.IN_QUERY, type=openapi.TYPE_BOOLEAN, description="Filter by active status (true/false)"),
#         openapi.Parameter('role', openapi.IN_QUERY, type=openapi.TYPE_INTEGER, description="Filter by role ID"),
#         openapi.Parameter('page', openapi.IN_QUERY, type=openapi.TYPE_INTEGER, description="Page number for pagination"),
#    openapi.Parameter(
#             'ordering',
#             openapi.IN_QUERY,
#             type=openapi.TYPE_STRING,
#             description=(
#                 "Order by fields. Use a minus sign (-) for descending.\n\n"
#                 "**Examples:**\n"
#                 "`ordering=email` (ascending)\n"
#                 "`ordering=-email` (descending)\n"
#                 "`ordering=role` (ascending by role)\n"
#                 "`ordering=-id` (latest users first)"
#             )
#         )
#     ]
# )
#     def get(self, request, *args, **kwargs):
#         return self.list(request, *args, **kwargs)


# ✅ Role CRUD (admin only)
class RoleViewSet(viewsets.ModelViewSet):
    queryset = Role.objects.all()
    serializer_class = RoleSerializer
    permission_classes = [IsAuthenticated, HasRolePermission]
    # required_permission = 'change_role'
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['id','name']  # 👈 enable filtering by role ID

    @swagger_auto_schema(
    tags=["03. Role Management"],
    operation_description="List all roles. You can filter by role ID or name using query parameters.",
    manual_parameters=[
        openapi.Parameter(
            'id',
            openapi.IN_QUERY,
            description="Filter by Role ID",
            type=openapi.TYPE_INTEGER
        ),
        openapi.Parameter(
            'name',
            openapi.IN_QUERY,
            description="Filter by Role name (exact match)",
            type=openapi.TYPE_STRING
        )
    ]
)
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_description="Create a new role with specific permissions for user access control.",
        request_body=RoleSerializer,
        responses={
            201: openapi.Response(
                description='Role created successfully',
                examples={
                    'application/json': {
                        'id': 1,
                        'name': 'Field Manager',
                        'permissions': [1, 2, 5, 8],
                        'created_at': '2024-01-15T10:30:00Z'
                    }
                }
            ),
            400: 'Bad Request - Invalid data or role name already exists'
        },
        tags=["03. Role Management"]
    )
    def create(self, request, *args, **kwargs):
        return super().create(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_description="Update all fields of an existing role including name and permissions.",
        responses={
            200: 'Role updated successfully',
            404: 'Role not found',
            400: 'Bad Request - Invalid data provided'
        },
        tags=["03. Role Management"]
    )
    def update(self, request, *args, **kwargs):
        return super().update(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_description="Permanently delete a role from the system. Users with this role will lose their permissions.",
        responses={
            204: 'Role deleted successfully',
            404: 'Role not found',
            400: 'Bad Request - Cannot delete role that is assigned to users'
        },
        tags=["03. Role Management"]
    )
    def destroy(self, request, *args, **kwargs):
        return super().destroy(request, *args, **kwargs)

    @action(detail=True, methods=['get'], url_path='permissions', permission_classes=[IsAuthenticated])
    @swagger_auto_schema(
        tags=["03. Role Management"],
        operation_id="get_role_permissions",
        operation_description="Retrieve all permissions assigned to a specific role with detailed permission information.",
        responses={
            200: openapi.Response(
                description='List of permissions for the role',
                examples={
                    'application/json': [
                        {
                            'id': 1,
                            'name': 'Can add user',
                            'codename': 'add_user',
                            'content_type': 'auth.user'
                        },
                        {
                            'id': 2,
                            'name': 'Can view attendance',
                            'codename': 'view_attendance',
                            'content_type': 'attendance.attendance'
                        }
                    ]
                }
            ),
            404: 'Role not found'
        }
    )
    
    def permissions_list(self, request, pk=None):
        role = self.get_object()
        permissions = role.permissions.all()
        serializer = PermissionSerializer(permissions, many=True)
        return Response(serializer.data)
    


# ✅ Admin-only status update
class AdminUserStatusUpdateView(generics.UpdateAPIView):
    queryset = User.objects.all()
    serializer_class = AdminUserStatusSerializer
    # permission_classes = [permissions.IsAdminUser]
    permission_classes = [IsAuthenticated, HasRolePermission]
    http_method_names = ['patch']

    @swagger_auto_schema(
        tags=["04. Admin Control"],
        operation_description="Update user account status (activate or deactivate) by admin. Deactivated users cannot login to the system.",
        request_body=AdminUserStatusSerializer,
        responses={
            200: openapi.Response(
                description='User status updated successfully',
                examples={
                    'application/json': {
                        'message': 'User status updated successfully',
                        'user_id': 123,
                        'is_active': True,
                        'updated_at': '2024-01-15T10:30:00Z'
                    }
                }
            ),
            404: 'User not found',
            400: 'Bad Request - Invalid data provided',
            403: 'Permission denied - Admin access required'
        }
    )
    def patch(self, request, *args, **kwargs):
        return self.partial_update(request, *args, **kwargs)


# # ✅ User Create (same as signup — used in API flow, not Swagger)
# class UserCreateAPIView(generics.CreateAPIView):
#     serializer_class = UserSignupSerializer
#     parser_classes = [MultiPartParser, FormParser]

#     # @swagger_auto_schema(
#     #     operation_description="Create user via API",
#     #     request_body=UserSignupSerializer,
#     #     tags=["User CRUD"]
#     # )


class PermissionListAPIView(generics.ListAPIView):
    queryset = Permission.objects.all()
    serializer_class = PermissionSerializer
    permission_classes = [IsAuthenticated, HasRolePermission]

    @swagger_auto_schema(
        operation_description="List all system permissions. If pagination parameters (`limit`, `offset`, `page`) are not provided, all permissions will be returned.",
        tags=["05. Permission Management"]
    )
    def get(self, request, *args, **kwargs):
        return self.list(request, *args, **kwargs)

    def paginate_queryset(self, queryset):
        # Only paginate if any pagination query param is present
        if any(param in self.request.query_params for param in ['limit', 'offset', 'page']):
            return super().paginate_queryset(queryset)
        return None


# ==================== ORGANOGRAM VIEW ====================
class OrganogramView(generics.GenericAPIView):
    """
    Organization Hierarchy/Organogram View
    
    Returns the hierarchical structure of sales staff with their reporting relationships.
    Only accessible to users with 'view_organogram' permission.
    """
    permission_classes = [IsAuthenticated]
    
    def check_permissions(self, request):
        """Check if user has view_organogram permission"""
        super().check_permissions(request)
        
        # Superuser has all permissions
        if request.user.is_superuser:
            return
        
        # Check for specific permission
        if not request.user.has_perm('accounts.view_organogram'):
            raise PermissionDenied("You don't have permission to view the organogram")
    
    @swagger_auto_schema(
        operation_description="Get organization hierarchy (organogram) showing sales staff reporting structure. Requires 'view_organogram' permission.",
        manual_parameters=[
            openapi.Parameter(
                'root_id',
                openapi.IN_QUERY,
                description='Start from specific staff member (defaults to top-level managers)',
                type=openapi.TYPE_INTEGER,
                required=False,
            ),
            openapi.Parameter(
                'depth',
                openapi.IN_QUERY,
                description='Maximum depth of hierarchy to return (default: unlimited)',
                type=openapi.TYPE_INTEGER,
                required=False,
            ),
        ],
        responses={
            200: openapi.Response(
                description='Hierarchical organization structure',
                examples={
                    'application/json': [
                        {
                            'id': 1,
                            'user_id': 10,
                            'name': 'John Doe',
                            'email': 'john@example.com',
                            'designation': 'CEO',
                            'employee_code': 'EMP001',
                            'phone_number': '+92300xxxxxxx',
                            'companies': ['4B-ORANG_APP'],
                            'regions': ['Central Region'],
                            'zones': ['Lahore Zone'],
                            'territories': ['Territory A', 'Territory B'],
                            'subordinates': [
                                {
                                    'id': 2,
                                    'name': 'Jane Smith',
                                    'designation': 'Regional Manager',
                                    'subordinates': []
                                }
                            ]
                        }
                    ]
                }
            ),
            403: 'Permission denied - requires view_organogram permission'
        },
        tags=["28. Organogram"]
    )
    def get(self, request):
        """Get organization hierarchy"""
        root_id = request.query_params.get('root_id')
        max_depth = request.query_params.get('depth')
        
        if max_depth:
            try:
                max_depth = int(max_depth)
            except ValueError:
                max_depth = None
        
        # Get the hierarchical data
        hierarchy = self._build_hierarchy(root_id, max_depth)
        
        return Response({
            'success': True,
            'data': hierarchy
        })
    
    def _build_hierarchy(self, root_id=None, max_depth=None):
        """Build hierarchical structure of sales staff"""
        
        # Get all active sales profiles with related data
        profiles = SalesStaffProfile.objects.filter(
            is_vacant=False
        ).select_related(
            'user', 'designation', 'manager'
        ).prefetch_related(
            'companies', 'regions', 'zones', 'territories'
        )
        
        if root_id:
            # Start from specific root
            try:
                root_profile = profiles.get(id=int(root_id))
                return [self._build_node(root_profile, max_depth, 0)]
            except SalesStaffProfile.DoesNotExist:
                return []
        else:
            # Find top-level managers (those with no manager)
            top_level = profiles.filter(manager__isnull=True)
            return [self._build_node(profile, max_depth, 0) for profile in top_level]
    
    def _build_node(self, profile, max_depth, current_depth):
        """Recursively build a node with its subordinates"""
        
        # Build node data
        node = {
            'id': profile.id,
            'user_id': profile.user.id if profile.user else None,
            'name': f"{profile.user.first_name} {profile.user.last_name}" if profile.user else "Vacant",
            'email': profile.user.email if profile.user else None,
            'designation': profile.designation.name if profile.designation else None,
            'designation_code': profile.designation.code if profile.designation else None,
            'employee_code': profile.employee_code,
            'phone_number': profile.phone_number,
            'companies': [c.Company_name for c in profile.companies.all()],
            'regions': [r.name for r in profile.regions.all()],
            'zones': [z.name for z in profile.zones.all()],
            'territories': [t.name for t in profile.territories.all()],
            'is_vacant': profile.is_vacant,
        }
        
        # Add subordinates if within depth limit
        if max_depth is None or current_depth < max_depth:
            subordinates = profile.subordinates.filter(is_vacant=False)
            node['subordinates'] = [
                self._build_node(sub, max_depth, current_depth + 1) 
                for sub in subordinates
            ]
        else:
            node['subordinates'] = []
            # Indicate if there are more subordinates beyond depth limit
            if profile.subordinates.exists():
                node['has_more_subordinates'] = True
        
        return node


# ==============================================================================
# FORGOT PASSWORD APIs
# ==============================================================================

from django.core.mail import send_mail
from django.conf import settings as django_settings
from django.utils import timezone
from datetime import timedelta
from .models import PasswordResetOTP


@swagger_auto_schema(
    method='post',
    tags=['Authentication'],
    operation_summary="Request Password Reset OTP",
    operation_description="""
    Send a 6-digit OTP to user's email or phone for password reset.
    
    **Input:** Provide either email OR phone_number (not both).
    
    **Process:**
    1. Find user by email or phone
    2. Generate 6-digit OTP
    3. Send OTP via email (phone SMS coming soon)
    4. OTP expires in 10 minutes
    
    **Rate Limit:** Max 3 OTP requests per hour per user.
    """,
    request_body=openapi.Schema(
        type=openapi.TYPE_OBJECT,
        properties={
            'email': openapi.Schema(type=openapi.TYPE_STRING, description='User email address'),
            'phone_number': openapi.Schema(type=openapi.TYPE_STRING, description='User phone number'),
        },
    ),
    responses={
        200: openapi.Response(
            description="OTP sent successfully",
            examples={
                "application/json": {
                    "success": True,
                    "message": "OTP sent to your email",
                    "identifier_type": "email",
                    "expires_in_minutes": 10
                }
            }
        ),
        400: "Bad request - invalid input",
        404: "User not found",
        429: "Too many requests"
    }
)
@api_view(['POST'])
@permission_classes([AllowAny])
def request_password_reset_otp(request):
    """
    Request a password reset OTP via email or phone.
    """
    email = (request.data.get('email') or '').strip().lower()
    phone = (request.data.get('phone_number') or '').strip()
    
    if not email and not phone:
        return Response({
            'success': False,
            'error': 'Please provide either email or phone_number'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    # Find user
    user = None
    identifier = None
    identifier_type = None
    
    if email:
        user = User.objects.filter(email__iexact=email).first()
        identifier = email
        identifier_type = 'email'
    elif phone:
        # Normalize phone number
        normalized_phone = re.sub(r'[\s\-\(\)\+]', '', phone)
        user = User.objects.filter(phone_number__icontains=normalized_phone[-10:]).first()
        if not user:
            user = User.objects.filter(phone_number=phone).first()
        identifier = phone
        identifier_type = 'phone'
    
    if not user:
        return Response({
            'success': False,
            'error': 'No account found with this email/phone number'
        }, status=status.HTTP_404_NOT_FOUND)
    
    # Check rate limit (max 3 per hour)
    one_hour_ago = timezone.now() - timedelta(hours=1)
    recent_otps = PasswordResetOTP.objects.filter(
        user=user,
        created_at__gte=one_hour_ago
    ).count()
    
    if recent_otps >= 3:
        return Response({
            'success': False,
            'error': 'Too many OTP requests. Please try again after 1 hour.'
        }, status=status.HTTP_429_TOO_MANY_REQUESTS)
    
    # Invalidate previous OTPs
    PasswordResetOTP.objects.filter(user=user, is_used=False).update(is_used=True)
    
    # Generate new OTP
    otp = PasswordResetOTP.generate_otp()
    expires_at = timezone.now() + timedelta(minutes=10)
    
    otp_record = PasswordResetOTP.objects.create(
        user=user,
        otp=otp,
        identifier=identifier,
        identifier_type=identifier_type,
        expires_at=expires_at
    )
    
    # Send OTP
    if identifier_type == 'email':
        try:
            send_mail(
                subject='Password Reset OTP - Four Brothers Portal',
                message=f'''
Dear {user.first_name or 'User'},

Your password reset OTP is: {otp}

This OTP will expire in 10 minutes.

If you did not request this, please ignore this email.

Regards,
Four Brothers Team
                ''',
                from_email=django_settings.DEFAULT_FROM_EMAIL,
                recipient_list=[email],
                fail_silently=False,
            )
        except Exception as e:
            otp_record.delete()
            return Response({
                'success': False,
                'error': f'Failed to send email. Please try again later.'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    else:
        # Phone SMS - placeholder for future implementation
        # For now, log the OTP (in production, integrate with SMS gateway)
        import logging
        logger = logging.getLogger(__name__)
        logger.info(f"[SMS OTP] Phone: {phone}, OTP: {otp}")
        # TODO: Integrate SMS gateway here
    
    return Response({
        'success': True,
        'message': f'OTP sent to your {identifier_type}',
        'identifier_type': identifier_type,
        'expires_in_minutes': 10
    }, status=status.HTTP_200_OK)


@swagger_auto_schema(
    method='post',
    tags=['Authentication'],
    operation_summary="Verify Password Reset OTP",
    operation_description="""
    Verify the OTP received via email/phone.
    
    **Input:** Provide the identifier (email or phone) and the 6-digit OTP.
    
    **On Success:** Returns a reset_token for the final password reset step.
    
    **Max Attempts:** 5 attempts per OTP before it gets invalidated.
    """,
    request_body=openapi.Schema(
        type=openapi.TYPE_OBJECT,
        required=['identifier', 'otp'],
        properties={
            'identifier': openapi.Schema(type=openapi.TYPE_STRING, description='Email or phone number'),
            'otp': openapi.Schema(type=openapi.TYPE_STRING, description='6-digit OTP'),
        },
    ),
    responses={
        200: openapi.Response(
            description="OTP verified successfully",
            examples={
                "application/json": {
                    "success": True,
                    "message": "OTP verified successfully",
                    "reset_token": "abc123..."
                }
            }
        ),
        400: "Invalid OTP or expired",
        404: "No OTP found"
    }
)
@api_view(['POST'])
@permission_classes([AllowAny])
def verify_password_reset_otp(request):
    """
    Verify the password reset OTP.
    """
    identifier = (request.data.get('identifier') or '').strip().lower()
    otp_code = (request.data.get('otp') or '').strip()
    
    if not identifier or not otp_code:
        return Response({
            'success': False,
            'error': 'identifier and otp are required'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    # Find the OTP record
    otp_record = PasswordResetOTP.objects.filter(
        identifier__iexact=identifier,
        otp=otp_code,
        is_used=False
    ).order_by('-created_at').first()
    
    if not otp_record:
        return Response({
            'success': False,
            'error': 'Invalid OTP or no pending reset request'
        }, status=status.HTTP_404_NOT_FOUND)
    
    # Check attempts
    if otp_record.attempts >= 5:
        otp_record.is_used = True
        otp_record.save()
        return Response({
            'success': False,
            'error': 'Too many failed attempts. Please request a new OTP.'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    # Check expiry
    if otp_record.is_expired():
        otp_record.is_used = True
        otp_record.save()
        return Response({
            'success': False,
            'error': 'OTP has expired. Please request a new one.'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    # Increment attempts
    otp_record.attempts += 1
    otp_record.save()
    
    # Verify OTP
    if otp_record.otp != otp_code:
        remaining = 5 - otp_record.attempts
        return Response({
            'success': False,
            'error': f'Invalid OTP. {remaining} attempts remaining.'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    # Generate reset token (using Django's password reset token generator)
    from django.contrib.auth.tokens import default_token_generator
    from django.utils.http import urlsafe_base64_encode
    from django.utils.encoding import force_bytes
    
    uid = urlsafe_base64_encode(force_bytes(otp_record.user.pk))
    token = default_token_generator.make_token(otp_record.user)
    reset_token = f"{uid}:{token}"
    
    # Mark OTP as used
    otp_record.is_used = True
    otp_record.save()
    
    return Response({
        'success': True,
        'message': 'OTP verified successfully',
        'reset_token': reset_token
    }, status=status.HTTP_200_OK)


@swagger_auto_schema(
    method='post',
    tags=['Authentication'],
    operation_summary="Reset Password",
    operation_description="""
    Set a new password using the reset token from OTP verification.
    
    **Input:** Provide reset_token and new_password.
    
    **Password Requirements:**
    - Minimum 8 characters
    - At least one uppercase letter
    - At least one lowercase letter
    - At least one digit
    """,
    request_body=openapi.Schema(
        type=openapi.TYPE_OBJECT,
        required=['reset_token', 'new_password'],
        properties={
            'reset_token': openapi.Schema(type=openapi.TYPE_STRING, description='Token from verify OTP step'),
            'new_password': openapi.Schema(type=openapi.TYPE_STRING, description='New password (min 8 chars)'),
            'confirm_password': openapi.Schema(type=openapi.TYPE_STRING, description='Confirm new password'),
        },
    ),
    responses={
        200: openapi.Response(
            description="Password reset successfully",
            examples={
                "application/json": {
                    "success": True,
                    "message": "Password has been reset successfully. You can now login with your new password."
                }
            }
        ),
        400: "Invalid token or password mismatch",
    }
)
@api_view(['POST'])
@permission_classes([AllowAny])
def reset_password(request):
    """
    Reset password using the reset token.
    """
    reset_token = (request.data.get('reset_token') or '').strip()
    new_password = request.data.get('new_password') or ''
    confirm_password = request.data.get('confirm_password') or ''
    
    if not reset_token or not new_password:
        return Response({
            'success': False,
            'error': 'reset_token and new_password are required'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    # Validate password
    if len(new_password) < 8:
        return Response({
            'success': False,
            'error': 'Password must be at least 8 characters long'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    if confirm_password and new_password != confirm_password:
        return Response({
            'success': False,
            'error': 'Passwords do not match'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    # Parse reset token
    try:
        uid, token = reset_token.split(':')
    except ValueError:
        return Response({
            'success': False,
            'error': 'Invalid reset token format'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    # Decode user ID
    from django.utils.http import urlsafe_base64_decode
    from django.contrib.auth.tokens import default_token_generator
    
    try:
        user_id = urlsafe_base64_decode(uid).decode()
        user = User.objects.get(pk=user_id)
    except (ValueError, User.DoesNotExist, TypeError):
        return Response({
            'success': False,
            'error': 'Invalid reset token'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    # Verify token
    if not default_token_generator.check_token(user, token):
        return Response({
            'success': False,
            'error': 'Reset token has expired or is invalid. Please request a new OTP.'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    # Set new password
    user.set_password(new_password)
    user.save()
    
    # Invalidate all OTPs for this user
    PasswordResetOTP.objects.filter(user=user).update(is_used=True)
    
    return Response({
        'success': True,
        'message': 'Password has been reset successfully. You can now login with your new password.'
    }, status=status.HTTP_200_OK)


# ==================== Account Deletion Request ====================

@swagger_auto_schema(
    method='post',
    tags=['Account Management'],
    operation_summary="Request Account Deactivation",
    operation_description="""
    **Submit a request to deactivate YOUR account.**
    
    **Important:** The request is automatically created for the authenticated user (from Bearer token).
    You can only request deactivation of your own account, not other users' accounts.
    
    Users can request to:
    - **Deactivate Account**: Temporarily disable account access
    
    **Process:**
    1. User submits request with optional reason
    2. Request is sent to admin for review (identifies user from Bearer token)
    3. Admin can approve/reject the request
    4. User is notified of the decision
    
    **Note:** This only creates a request. Admin approval is required before any action is taken.
    
    **Authentication:** Required (Bearer token) - automatically identifies which user is requesting
    
    **Example Request:**
    ```bash
    curl -X POST http://yourapi.com/api/accounts/account/deletion-request/ \\
      -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \\
      -F "user_id=123" \\
      -F "request_type=deactivate" \\
      -F "reason=Taking a break from the app"
    ```
    """,
    request_body=openapi.Schema(
        type=openapi.TYPE_OBJECT,
        required=['user_id', 'request_type'],
        properties={
            'user_id': openapi.Schema(
                type=openapi.TYPE_INTEGER,
                description="User ID whose account to deactivate. Must match authenticated user's ID (security check)."
            ),
            'request_type': openapi.Schema(
                type=openapi.TYPE_STRING,
                description="Type of request: 'deactivate' for account deactivation",
                enum=['deactivate']
            ),
            'reason': openapi.Schema(
                type=openapi.TYPE_STRING,
                description="Optional reason for the request"
            ),
        }
    ),
    responses={
        201: openapi.Response(
            description="Request created successfully",
            examples={
                'application/json': {
                    'success': True,
                    'message': 'Account deletion request submitted successfully. An admin will review your request.',
                    'data': {
                        'id': 1,
                        'user': 123,
                        'user_email': 'user@example.com',
                        'user_name': 'John Doe',
                        'request_type': 'deactivate',
                        'reason': 'Taking a break from the app',
                        'status': 'pending',
                        'created_at': '2026-03-10T10:30:00Z',
                        'updated_at': '2026-03-10T10:30:00Z'
                    }
                }
            }
        ),
        400: openapi.Response(
            description="Bad request - invalid data or pending request exists",
            examples={
                'application/json': {
                    'success': False,
                    'error': 'You already have a pending request. Please wait for admin review.'
                }
            }
        ),
        401: openapi.Response(description="Unauthorized - authentication required"),
        403: openapi.Response(
            description="Forbidden - user_id does not match authenticated user",
            examples={
                'application/json': {
                    'success': False,
                    'error': 'You can only request deletion of your own account. user_id must match your authenticated user ID.'
                }
            }
        )
    }
)
@api_view(['POST'])
@permission_classes([IsAuthenticated])
@parser_classes([MultiPartParser, FormParser, JSONParser])
def request_account_deletion(request):
    """
    API endpoint for users to request account deactivation.
    Requires authentication. Creates a request that admin can review.
    """
    from .models import AccountDeletionRequest
    from .serializers import AccountDeletionRequestSerializer
    
    authenticated_user = request.user
    
    # Get user_id from request body
    user_id = request.data.get('user_id')
    
    # Validate user_id is provided
    if not user_id:
        return Response({
            'success': False,
            'error': 'user_id is required'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    # Security check: user_id must match authenticated user
    # (Users can only request deletion of their own account)
    try:
        user_id = int(user_id)
    except (ValueError, TypeError):
        return Response({
            'success': False,
            'error': 'Invalid user_id format'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    if user_id != authenticated_user.id:
        return Response({
            'success': False,
            'error': 'You can only request deactivation of your own account. user_id must match your authenticated user ID.'
        }, status=status.HTTP_403_FORBIDDEN)
    
    # Verify user exists
    try:
        target_user = User.objects.get(id=user_id)
    except User.DoesNotExist:
        return Response({
            'success': False,
            'error': f'User with ID {user_id} not found'
        }, status=status.HTTP_404_NOT_FOUND)
    
    # Check if user already has a pending request
    existing_pending = AccountDeletionRequest.objects.filter(
        user=target_user,
        status='pending'
    ).exists()
    
    if existing_pending:
        return Response({
            'success': False,
            'error': 'You already have a pending request. Please wait for admin review.'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    # Create the request
    serializer = AccountDeletionRequestSerializer(
        data=request.data,
        context={'request': request}
    )
    
    if serializer.is_valid():
        deletion_request = serializer.save()
        
        return Response({
            'success': True,
            'message': 'Account deactivation request submitted successfully. An admin will review your request.',
            'data': serializer.data
        }, status=status.HTTP_201_CREATED)
    
    return Response({
        'success': False,
        'error': 'Invalid data',
        'details': serializer.errors
    }, status=status.HTTP_400_BAD_REQUEST)


@swagger_auto_schema(
    method='get',
    tags=['Account Management'],
    operation_summary="Get My Account Deactivation Requests",
    operation_description="""
    **Get all account deactivation requests submitted by the authenticated user.**
    
    Returns a list of all requests (pending, approved, rejected, completed) submitted by the current user.
    
    **Authentication:** Required (Bearer token)
    """,
    responses={
        200: openapi.Response(
            description="List of user's account deactivation requests",
            examples={
                'application/json': {
                    'success': True,
                    'count': 2,
                    'data': [
                        {
                            'id': 2,
                            'request_type': 'deactivate',
                            'reason': 'Taking a break',
                            'status': 'pending',
                            'created_at': '2026-03-10T10:30:00Z',
                            'updated_at': '2026-03-10T10:30:00Z'
                        },
                        {
                            'id': 1,
                            'request_type': 'delete',
                            'reason': 'No longer need the account',
                            'status': 'rejected',
                            'created_at': '2026-03-05T08:15:00Z',
                            'updated_at': '2026-03-06T09:20:00Z'
                        }
                    ]
                }
            }
        ),
        401: openapi.Response(description="Unauthorized - authentication required")
    }
)
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def my_account_deletion_requests(request):
    """
    API endpoint to retrieve all account deletion requests for the authenticated user.
    """
    from .models import AccountDeletionRequest
    from .serializers import AccountDeletionRequestSerializer
    
    user = request.user
    
    # Get all requests for this user
    requests = AccountDeletionRequest.objects.filter(user=user).order_by('-created_at')
    
    serializer = AccountDeletionRequestSerializer(requests, many=True)
    
    return Response({
        'success': True,
        'count': requests.count(),
        'data': serializer.data
    }, status=status.HTTP_200_OK)

