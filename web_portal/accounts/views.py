from rest_framework import generics, permissions, viewsets
from rest_framework.permissions import AllowAny, IsAuthenticated, BasePermission,DjangoModelPermissions
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.exceptions import PermissionDenied
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from rest_framework.filters import OrderingFilter
from .models import Role
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

# ✅ Role-based dynamic permission check
# class HasRolePermission(BasePermission):
#     def has_permission(self, request, view):
#         user = request.user
#         if not user or not user.is_authenticated or not user.role:
#             return False
#         required_codename = getattr(view, 'required_permission', None)
#         if required_codename:
#             return user.role.permissions.filter(codename=required_codename).exists()
#         return True
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
        operation_description="Register a new user",
        request_body=UserSignupSerializer,
        tags=["Authentication"]
    )
    def post(self, request, *args, **kwargs):
        return self.create(request, *args, **kwargs)


# ✅ JWT Login View
class MyTokenObtainPairView(TokenObtainPairView):
    serializer_class = MyTokenObtainPairSerializer

    @swagger_auto_schema(
        operation_description="Authenticate user and obtain JWT tokens",
        tags=["Authentication"]
    )
    def post(self, request, *args, **kwargs):
        return super().post(request, *args, **kwargs)


# ✅ List all users (requires view_user permission)
class UserListAPIView(generics.ListAPIView):
    queryset = User.objects.all()
    serializer_class = UserListSerializer
    permission_classes = [IsAuthenticated, HasRolePermission]
    required_permission = 'view_user'
    # ✅ Add filter backend and filter class
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_class = UserFilter
    ordering_fields = ['id', 'email', 'username', 'first_name', 'last_name', 'is_active', 'role']
    ordering = ['id']  # Optional: default ordering
    @swagger_auto_schema(
    tags=["User management"],
    manual_parameters=[
        openapi.Parameter('email', openapi.IN_QUERY, type=openapi.TYPE_STRING, description="Filter by email"),
        openapi.Parameter('username', openapi.IN_QUERY, type=openapi.TYPE_STRING, description="Filter by username"),
        openapi.Parameter('is_active', openapi.IN_QUERY, type=openapi.TYPE_BOOLEAN, description="Filter by active status (true/false)"),
        openapi.Parameter('role', openapi.IN_QUERY, type=openapi.TYPE_INTEGER, description="Filter by role ID"),
        openapi.Parameter('page', openapi.IN_QUERY, type=openapi.TYPE_INTEGER, description="Page number for pagination"),
   openapi.Parameter(
            'ordering',
            openapi.IN_QUERY,
            type=openapi.TYPE_STRING,
            description=(
                "Order by fields. Use a minus sign (-) for descending.\n\n"
                "**Examples:**\n"
                "`ordering=email` (ascending)\n"
                "`ordering=-email` (descending)\n"
                "`ordering=role` (ascending by role)\n"
                "`ordering=-id` (latest users first)"
            )
        )
    ]
)
    def get(self, request, *args, **kwargs):
        return self.list(request, *args, **kwargs)


# ✅ Role CRUD (admin only)
class RoleViewSet(viewsets.ModelViewSet):
    queryset = Role.objects.all()
    serializer_class = RoleSerializer
    permission_classes = [IsAuthenticated, HasRolePermission]
    # required_permission = 'change_role'
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['id','name']  # 👈 enable filtering by role ID

    @swagger_auto_schema(
    tags=["Role Management"],
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

    @swagger_auto_schema(tags=["Role Management"])
    def create(self, request, *args, **kwargs):
        return super().create(request, *args, **kwargs)

    @swagger_auto_schema(tags=["Role Management"])
    def update(self, request, *args, **kwargs):
        return super().update(request, *args, **kwargs)

    @swagger_auto_schema(tags=["Role Management"])
    def destroy(self, request, *args, **kwargs):
        return super().destroy(request, *args, **kwargs)

    @action(detail=True, methods=['get'], url_path='permissions', permission_classes=[IsAuthenticated])
    @swagger_auto_schema(
        tags=["Role Management"],
        operation_id="get_role_permissions",  # 👈 unique name to identify in Swagger
        operation_description="Get all permissions assigned to a specific role."
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
        operation_description="Partially update user's status (admin only)",
        tags=["Admin Control"]
    )
    def patch(self, request, *args, **kwargs):
        return self.partial_update(request, *args, **kwargs)


# ✅ User Create (same as signup — used in API flow, not Swagger)
class UserCreateAPIView(generics.CreateAPIView):
    serializer_class = UserSignupSerializer
    parser_classes = [MultiPartParser, FormParser]

    # @swagger_auto_schema(
    #     operation_description="Create user via API",
    #     request_body=UserSignupSerializer,
    #     tags=["User CRUD"]
    # )
    # def post(self, request, *args, **kwargs):
    #     return self.create(request, *args, **kwargs)
    @swagger_auto_schema(operation_description="Create a new user (optionally sales staff)", request_body=UserSignupSerializer, tags=["User CRUD"])
    def post(self, request, *args, **kwargs):
        return self.create(request, *args, **kwargs)


# # ✅ Full user CRUD viewset
# class UserViewSet(viewsets.ModelViewSet):
#     queryset = User.objects.all()
#     # serializer_class = UserSerializer 
#     # permission_classes = [IsAuthenticated, IsOwnerOrAdmin]
#     permission_classes = [IsAuthenticated, HasRolePermission]
#     parser_classes = [MultiPartParser, FormParser]
#     http_method_names = ['get', 'put', 'patch', 'delete']

class SalesStaffViewSet(viewsets.ModelViewSet):
    # queryset = SalesStaffProfile.objects.select_related('user').all()
    queryset = User.objects.select_related('sales_profile__company', 
                                           'sales_profile__region', 
                                           'sales_profile__zone', 
                                           'sales_profile__territory').all()
    # serializer_class = UserSerializer
    serializer_class = SalesStaffSerializer
    permission_classes = [IsAuthenticated, HasRolePermission]

# ✅ Add filter backend and filter class
    filter_backends = [DjangoFilterBackend,OrderingFilter]
    filterset_class = UserFilter
    ordering_fields = ['id', 'email', 'username', 'first_name', 'last_name', 'is_active', 'role']
    ordering = ['id']  # Optional: default ordering
    def get_queryset(self):
        user = self.request.user
        if user.is_superuser or user.is_staff:
            return User.objects.all()
        return User.objects.filter(id=user.id)

    def get_serializer_class(self):
        if self.action in ['update', 'partial_update']:
            return UserUpdateSerializer
        return UserSerializer

    def perform_destroy(self, instance):
        if instance != self.request.user and not self.request.user.is_superuser:
            raise PermissionDenied("You can only delete your own account.")
        instance.delete()

    @swagger_auto_schema(tags=["User CRUD"])
    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)

    @swagger_auto_schema(tags=["User CRUD"])
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @swagger_auto_schema(tags=["User CRUD"])
    def update(self, request, *args, **kwargs):
        return super().update(request, *args, **kwargs)

    # @swagger_auto_schema(
    #     tags=["User CRUD"],
    #     operation_description="Partially update user profile. Admins can change role/status. Use multipart/form-data for image upload.",
    #     manual_parameters=[
    #         openapi.Parameter('first_name', openapi.IN_FORM, type=openapi.TYPE_STRING, required=False),
    #         openapi.Parameter('last_name', openapi.IN_FORM, type=openapi.TYPE_STRING, required=False),
    #         openapi.Parameter('role', openapi.IN_FORM, type=openapi.TYPE_INTEGER, required=False),
    #         openapi.Parameter('is_active', openapi.IN_FORM, type=openapi.TYPE_BOOLEAN, required=False),
    #         openapi.Parameter('profile_image', openapi.IN_FORM, type=openapi.TYPE_FILE, required=False),
    #     ]
    # )
    # def partial_update(self, request, *args, **kwargs):
    #     return super().partial_update(request, *args, **kwargs)
    @swagger_auto_schema(
    request_body=UserUpdateSerializer,  # your update serializer
    tags=["User CRUD"],
    operation_description="Update user profile",
)
    def partial_update(self, request, *args, **kwargs):
        return super().partial_update(request, *args, **kwargs)

    @swagger_auto_schema(tags=["User CRUD"])
    def destroy(self, request, *args, **kwargs):
        return super().destroy(request, *args, **kwargs)

class PermissionListAPIView(generics.ListAPIView):
    queryset = Permission.objects.all()
    serializer_class = PermissionSerializer
    permission_classes = [IsAuthenticated, HasRolePermission]

    @swagger_auto_schema(
        operation_description="List all system permissions. If pagination parameters (`limit`, `offset`, `page`) are not provided, all permissions will be returned.",
        tags=["Permission Management"]
    )
    def get(self, request, *args, **kwargs):
        return self.list(request, *args, **kwargs)

    def paginate_queryset(self, queryset):
        # Only paginate if any pagination query param is present
        if any(param in self.request.query_params for param in ['limit', 'offset', 'page']):
            return super().paginate_queryset(queryset)
        return None
