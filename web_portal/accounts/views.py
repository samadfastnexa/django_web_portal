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
from rest_framework.decorators import action
from .token_serializers import MyTokenObtainPairSerializer
from .permissions import IsOwnerOrAdmin
from .filters import UserFilter  # ✅ Import your custom filter class
from django_filters.rest_framework import DjangoFilterBackend

User = get_user_model()


class RoleViewSet(viewsets.ModelViewSet):
    queryset = Role.objects.all()
    serializer_class = RoleSerializer
    permission_classes = [IsAuthenticated, HasRolePermission]

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
                        'is_active': True,
                        'date_joined': '2024-01-15T10:30:00Z',
                        'sales_profile': {
                            'employee_code': 'EMP001',
                            'designation': 'MTO',
                            'phone_number': '+1234567890'
                        }
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
        operation_description="Authenticate user and obtain JWT tokens",
        request_body=MyTokenObtainPairSerializer,
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
