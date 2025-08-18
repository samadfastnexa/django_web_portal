# from rest_framework import viewsets, permissions
# from rest_framework.permissions import IsAuthenticated
# from rest_framework.parsers import MultiPartParser, FormParser
# from rest_framework.response import Response
# from rest_framework import status
# from .serializers import UserSerializer
# from django.contrib.auth import get_user_model
# from drf_yasg.utils import swagger_auto_schema
# from accounts.permissions import HasRolePermission 
# from drf_yasg import openapi
# User = get_user_model()

# class IsOwnerOrAdmin(permissions.BasePermission):
#     def has_object_permission(self, request, view, obj):
#         return request.user.is_superuser or obj == request.user

# class UserViewSet(viewsets.ModelViewSet):
#     queryset = User.objects.all()
#     serializer_class = UserSerializer
#     parser_classes = [MultiPartParser, FormParser]
#     # permission_classes = [IsAuthenticated]
#     permission_classes = [IsAuthenticated, HasRolePermission]
#     def get_permissions(self):
#         if self.action == 'destroy':
#             return [permissions.IsAdminUser()]
#         return [IsAuthenticated(), IsOwnerOrAdmin()]

#     def get_queryset(self):
#         # Superusers can view all; others can view only themselves
#         if self.request.user.is_superuser:
#             return User.objects.all()
#         return User.objects.filter(id=self.request.user.id)

#     def perform_destroy(self, instance):
#         # Only superuser can delete
#         if not self.request.user.is_superuser:
#             return Response({'detail': 'Not allowed to delete.'}, status=status.HTTP_403_FORBIDDEN)
#         instance.delete()

#     @swagger_auto_schema(tags=["User"])
    
#     def list(self, request, *args, **kwargs):
#         return super().list(request, *args, **kwargs)

#     @swagger_auto_schema(
#         manual_parameters=[
#             openapi.Parameter('username', openapi.IN_FORM, type=openapi.TYPE_STRING, description="Username"),
#             openapi.Parameter('email', openapi.IN_FORM, type=openapi.TYPE_STRING, description="Email"),
#             openapi.Parameter('password', openapi.IN_FORM, type=openapi.TYPE_STRING, description="Password"),
#             openapi.Parameter('first_name', openapi.IN_FORM, type=openapi.TYPE_STRING, description="First name"),
#             openapi.Parameter('last_name', openapi.IN_FORM, type=openapi.TYPE_STRING, description="Last name"),
#             openapi.Parameter('profile_image', openapi.IN_FORM, type=openapi.TYPE_FILE, description="Profile image"),
#             # Add other fields here...
#         ],
#         responses={201: UserSerializer},
#         tags=["User"]
#     )
#     def create(self, request, *args, **kwargs):
#         return super().create(request, *args, **kwargs)

#     @swagger_auto_schema(tags=["User"])
#     def retrieve(self, request, *args, **kwargs):
#         return super().retrieve(request, *args, **kwargs)

#     @swagger_auto_schema(tags=["User"])
#     def update(self, request, *args, **kwargs):
#         return super().update(request, *args, **kwargs)

#     @swagger_auto_schema(tags=["User"])
#     def partial_update(self, request, *args, **kwargs):
#         return super().partial_update(request, *args, **kwargs)

#     @swagger_auto_schema(tags=["User"])
#     def destroy(self, request, *args, **kwargs):
#         return super().destroy(request, *args, **kwargs)

from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import OrderingFilter, SearchFilter

from rest_framework import viewsets, permissions, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.response import Response
from django.contrib.auth import get_user_model
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from django.core.exceptions import PermissionDenied
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import OrderingFilter

from .serializers import UserSerializer, UserUpdateSerializer
from accounts.permissions import HasRolePermission

User = get_user_model()


# ----------------------
# Custom permission: Only owner or superuser
# ----------------------
class IsOwnerOrAdmin(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        # Superusers can access all, others only their own user object
        return request.user.is_superuser or obj == request.user


# ----------------------
# UserViewSet
# ----------------------
class UserViewSet(viewsets.ModelViewSet):
    """
    CRUD endpoint for users.
    Supports nested sales_profile, sales staff creation/update,
    filtering, ordering, and Swagger documentation.
    """
    queryset = User.objects.select_related(
        'sales_profile__company',
        'sales_profile__region',
        'sales_profile__zone',
        'sales_profile__territory'
    ).all()
    parser_classes = [MultiPartParser, FormParser]
    permission_classes = [IsAuthenticated, HasRolePermission]

    # Filtering & ordering
    
    filter_backends = [DjangoFilterBackend, OrderingFilter, SearchFilter]

    # Filters on User fields
    filterset_fields = {
    'is_active': ['exact'],
    'role': ['exact'],
    'is_sales_staff': ['exact'],
    'sales_profile__company': ['exact'],
    'sales_profile__region': ['exact'],
    'sales_profile__zone': ['exact'],
    'sales_profile__territory': ['exact'],
}

    # Filters on related sales_profile fields
    filterset_fields.update({
        'sales_profile__company': ['exact'],
        'sales_profile__region': ['exact'],
        'sales_profile__zone': ['exact'],
        'sales_profile__territory': ['exact'],
    })

    # Searchable fields
    search_fields = ['username', 'email', 'first_name', 'last_name', 
                    'sales_profile__employee_code', 'sales_profile__designation']

    # Ordering fields
    ordering_fields = ['id', 'username', 'email', 'first_name', 'last_name', 'role',
                    'sales_profile__company', 'sales_profile__region', 
                    'sales_profile__zone', 'sales_profile__territory']

    # ----------------------
    # Dynamic serializer based on action
    # ----------------------
    def get_serializer_class(self):
        if self.action in ['update', 'partial_update']:
            return UserUpdateSerializer
        return UserSerializer

    # ----------------------
    # Restrict queryset based on user permissions
    # ----------------------
    def get_queryset(self):
        user = self.request.user
        if user.is_superuser:
            return self.queryset
        return self.queryset.filter(id=user.id)

    # ----------------------
    # Restrict delete: only superuser can delete any user
    # ----------------------
    def perform_destroy(self, instance):
        if not self.request.user.is_superuser:
            raise PermissionDenied("You can only delete your own account.")
        instance.delete()

    # ----------------------
    # Override permissions per action
    # ----------------------
    def get_permissions(self):
        if self.action == 'destroy':
            return [permissions.IsAdminUser()]
        return [IsAuthenticated(), IsOwnerOrAdmin()]

    # ----------------------
    # Swagger documentation for list
    # ----------------------
    @swagger_auto_schema(tags=["User CRUD"])
    def list(self, request, *args, **kwargs):
        """
        List all users.
        Superusers see all users.
        Others see only themselves.
        Supports filtering by `is_sales_staff`.
        """
        return super().list(request, *args, **kwargs)

    # ----------------------
    # Swagger documentation for retrieve
    # ----------------------
    @swagger_auto_schema(tags=["User CRUD"])
    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)

    # ----------------------
    # Swagger documentation for create
    # ----------------------
    @swagger_auto_schema(
        manual_parameters=[
            openapi.Parameter('username', openapi.IN_FORM, type=openapi.TYPE_STRING, description="Username"),
            openapi.Parameter('email', openapi.IN_FORM, type=openapi.TYPE_STRING, description="Email"),
            openapi.Parameter('password', openapi.IN_FORM, type=openapi.TYPE_STRING, description="Password"),
            openapi.Parameter('first_name', openapi.IN_FORM, type=openapi.TYPE_STRING, description="First name"),
            openapi.Parameter('last_name', openapi.IN_FORM, type=openapi.TYPE_STRING, description="Last name"),
            openapi.Parameter('profile_image', openapi.IN_FORM, type=openapi.TYPE_FILE, description="Profile image"),
            openapi.Parameter('is_sales_staff', openapi.IN_FORM, type=openapi.TYPE_BOOLEAN, description="Create sales profile"),
            # SalesStaff fields
            openapi.Parameter('employee_code', openapi.IN_FORM, type=openapi.TYPE_STRING),
            openapi.Parameter('phone_number', openapi.IN_FORM, type=openapi.TYPE_STRING),
            openapi.Parameter('address', openapi.IN_FORM, type=openapi.TYPE_STRING),
            openapi.Parameter('designation', openapi.IN_FORM, type=openapi.TYPE_STRING),
            openapi.Parameter('company', openapi.IN_FORM, type=openapi.TYPE_INTEGER),
            openapi.Parameter('region', openapi.IN_FORM, type=openapi.TYPE_INTEGER),
            openapi.Parameter('zone', openapi.IN_FORM, type=openapi.TYPE_INTEGER),
            openapi.Parameter('territory', openapi.IN_FORM, type=openapi.TYPE_INTEGER),
            openapi.Parameter('sick_leave_quota', openapi.IN_FORM, type=openapi.TYPE_INTEGER),
            openapi.Parameter('casual_leave_quota', openapi.IN_FORM, type=openapi.TYPE_INTEGER),
            openapi.Parameter('others_leave_quota', openapi.IN_FORM, type=openapi.TYPE_INTEGER),
        ],
        responses={201: UserSerializer},
        tags=["User CRUD"]
    )
    def create(self, request, *args, **kwargs):
        """
        Create a new user.
        If `is_sales_staff=True`, sales profile is also created.
        """
        return super().create(request, *args, **kwargs)

    # ----------------------
    # Swagger documentation for update
    # ----------------------
    @swagger_auto_schema(tags=["User CRUD"])
    def update(self, request, *args, **kwargs):
        return super().update(request, *args, **kwargs)

    @swagger_auto_schema(tags=["User CRUD"])
    def partial_update(self, request, *args, **kwargs):
        return super().partial_update(request, *args, **kwargs)

    @swagger_auto_schema(tags=["User CRUD"])
    def destroy(self, request, *args, **kwargs):
        return super().destroy(request, *args, **kwargs)
