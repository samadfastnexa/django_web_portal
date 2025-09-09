
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import OrderingFilter, SearchFilter
from rest_framework import viewsets, permissions
from rest_framework.permissions import IsAuthenticated
from rest_framework.parsers import MultiPartParser, FormParser
from django.contrib.auth import get_user_model
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from django.core.exceptions import PermissionDenied
from .filters import UserFilter
from .serializers import UserSerializer, UserUpdateSerializer
from accounts.permissions import HasRolePermission
from django.db.models import Prefetch
from FieldAdvisoryService.models import Company, Region, Zone, Territory
from django.db import transaction
from rest_framework import viewsets, status
from rest_framework.response import Response
from .models import SalesStaffProfile
User = get_user_model()


# ----------------------
# Custom permission: Only owner or superuser
# ----------------------
class IsOwnerOrAdmin(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        # Superusers can access all, others only their own user object
        return request.user.is_superuser or obj == request.user

# # ----------------------
# # UserViewSet
# # ----------------------
class UserViewSet(viewsets.ModelViewSet):
    """
    CRUD endpoint for users.
    Supports nested sales_profile, sales staff creation/update,
    filtering, ordering, search, and Swagger documentation.
    """
    # Remove the problematic prefetch_related from the class level
    queryset = User.objects.select_related("sales_profile").all()
    parser_classes = [MultiPartParser, FormParser]
    permission_classes = [IsAuthenticated, HasRolePermission]

    filter_backends = [DjangoFilterBackend, OrderingFilter, SearchFilter]
    filterset_class = UserFilter # ✅ use central filter class

    search_fields = [
        'username', 'email', 'first_name', 'last_name',
        'sales_profile__employee_code', 'sales_profile__designation'
    ]
    # ✅ Ordering restricted to scalar fields only (no M2M)
    ordering_fields = [
        'id', 'username', 'email', 'first_name', 'last_name',
        'is_active', 'role',
        'sales_profile__employee_code', 'sales_profile__designation'
    ]
    ordering = ['id']  # default
    
    m2m_parameters = [
    openapi.Parameter(
        "companies",
        openapi.IN_FORM,
        description="List of company IDs",
        type=openapi.TYPE_ARRAY,
        items=openapi.Items(type=openapi.TYPE_INTEGER),
        required=False
    ),
    openapi.Parameter(
        "regions",
        openapi.IN_FORM,
        description="List of region IDs",
        type=openapi.TYPE_ARRAY,
        items=openapi.Items(type=openapi.TYPE_INTEGER),
        required=False
    ),
    openapi.Parameter(
        "zones",
        openapi.IN_FORM,
        description="List of zone IDs",
        type=openapi.TYPE_ARRAY,
        items=openapi.Items(type=openapi.TYPE_INTEGER),
        required=False
    ),
    openapi.Parameter(
        "territories",
        openapi.IN_FORM,
        description="List of territory IDs",
        type=openapi.TYPE_ARRAY,
        items=openapi.Items(type=openapi.TYPE_INTEGER),
        required=False
    ),
]
# ----------------------
#     # Dynamic serializer based on action
#     # ----------------------
    def get_serializer_class(self):
        if self.action in ['update', 'partial_update']:
            return UserUpdateSerializer
        return UserSerializer

#     # ----------------------
#     # Restrict queryset based on user permissions
#     # ----------------------    
    def get_queryset(self):
        # Start with the base queryset
        qs = super().get_queryset()
        
        # Use explicit Prefetch objects for better control
        qs = qs.prefetch_related(
            Prefetch('sales_profile__companies', queryset=Company.objects.all()),
            Prefetch('sales_profile__regions', queryset=Region.objects.all()),
            Prefetch('sales_profile__zones', queryset=Zone.objects.all()),
            Prefetch('sales_profile__territories', queryset=Territory.objects.all()),
        )
        
        user = self.request.user
        if not user.is_superuser:
            qs = qs.filter(id=user.id)
        # Get M2M filters from query params
        # Apply filters
        company_ids = self.request.query_params.getlist('companies')
        if company_ids:
            qs = qs.filter(sales_profile__companies__id__in=company_ids)

        region_ids = self.request.query_params.getlist('regions')
        if region_ids:
            qs = qs.filter(sales_profile__regions__id__in=region_ids)

        zone_ids = self.request.query_params.getlist('zones')
        if zone_ids:
            qs = qs.filter(sales_profile__zones__id__in=zone_ids)

        territory_ids = self.request.query_params.getlist('territories')
        if territory_ids:
            qs = qs.filter(sales_profile__territories__id__in=territory_ids)

        return qs.distinct()
   # ----------------------
   # Override permissions per action
   # ----------------------
    def get_permissions(self):
        if self.action == 'destroy':
            return [permissions.IsAdminUser()]
        return [IsAuthenticated(), IsOwnerOrAdmin()]
    
#     # ----------------------
#     # Swagger: list
#     # ----------------------
    # Swagger documentation
    @swagger_auto_schema(
        tags=["02. User Management"],
        manual_parameters=[
            openapi.Parameter('is_active', openapi.IN_QUERY, type=openapi.TYPE_BOOLEAN, description="Filter by active status", enum=[True, False]),
            openapi.Parameter('role', openapi.IN_QUERY, type=openapi.TYPE_INTEGER, description="Filter by role ID"),
            openapi.Parameter('is_sales_staff', openapi.IN_QUERY, type=openapi.TYPE_BOOLEAN, description="Filter by sales staff", enum=[True, False]),
            openapi.Parameter(
                'companies', 
                openapi.IN_QUERY, 
                type=openapi.TYPE_ARRAY,
                items=openapi.Items(type=openapi.TYPE_INTEGER),
                description="Filter by company IDs"
            ),
            openapi.Parameter(
                'regions', 
                openapi.IN_QUERY, 
                type=openapi.TYPE_ARRAY,
                items=openapi.Items(type=openapi.TYPE_INTEGER),
                description="Filter by region IDs"
            ),
            openapi.Parameter(
                'zones', 
                openapi.IN_QUERY, 
                type=openapi.TYPE_ARRAY,
                items=openapi.Items(type=openapi.TYPE_INTEGER),
                description="Filter by zone IDs"
            ),
            openapi.Parameter(
                'territories', 
                openapi.IN_QUERY, 
                type=openapi.TYPE_ARRAY,
                items=openapi.Items(type=openapi.TYPE_INTEGER),
                description="Filter by territory IDs"
            ),
        ]
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    # @swagger_auto_schema(
    #     tags=["User CRUD"],
    #     manual_parameters=[
    #         openapi.Parameter(
    #             'profile_image', openapi.IN_FORM,
    #             type=openapi.TYPE_FILE, description="Profile image"
    #         ),
    #         openapi.Parameter(
    #             'companies', openapi.IN_FORM,
    #             description="List of company IDs (use multiple values)",
    #             type=openapi.TYPE_ARRAY,
    #             items=openapi.Items(type=openapi.TYPE_INTEGER),
    #             collection_format='multi'  # ✅ lets Swagger show + button
    #         ),
    #         openapi.Parameter(
    #             'regions', openapi.IN_FORM,
    #             description="List of region IDs (use multiple values)",
    #             type=openapi.TYPE_ARRAY,
    #             items=openapi.Items(type=openapi.TYPE_INTEGER),
    #             collection_format='multi'
    #         ),
    #         openapi.Parameter(
    #             'zones', openapi.IN_FORM,
    #             description="List of zone IDs (use multiple values)",
    #             type=openapi.TYPE_ARRAY,
    #             items=openapi.Items(type=openapi.TYPE_INTEGER),
    #             collection_format='multi'
    #         ),
    #         openapi.Parameter(
    #             'territories', openapi.IN_FORM,
    #             description="List of territory IDs (use multiple values)",
    #             type=openapi.TYPE_ARRAY,
    #             items=openapi.Items(type=openapi.TYPE_INTEGER),
    #             collection_format='multi'
    #         ),
    #     ],
    #     responses={201: UserSerializer}
    # )
    # @transaction.atomic
    # def create(self, request, *args, **kwargs):
    #     serializer = self.get_serializer(data=request.data)
    #     serializer.is_valid(raise_exception=True)

    #     # Extract is_sales_staff flag
    #     is_sales_staff = serializer.validated_data.get('is_sales_staff', False)

    #     # Extract M2M fields before creating profile
    #     m2m_fields = ['companies', 'regions', 'zones', 'territories']
    #     m2m_data = {field: serializer.validated_data.pop(field, []) for field in m2m_fields}

    #     # Extract profile fields
    #     profile_fields = [
    #         'employee_code', 'phone_number', 'address', 'designation',
    #         'hod', 'master_hod','date_of_joining',
    #         'sick_leave_quota', 'casual_leave_quota', 'others_leave_quota'
    #     ]
    #     profile_data = {f: serializer.validated_data.pop(f, None) for f in profile_fields}

    #     # Extract password
    #     password = serializer.validated_data.pop('password', None)

    #     # Create user
    #     user = User(**serializer.validated_data)
    #     if password:
    #         user.set_password(password)
    #     user.is_sales_staff = is_sales_staff
    #     user.save()

    #     # Create sales profile if needed
    #     if is_sales_staff:
    #         profile = SalesStaffProfile.objects.create(user=user, **profile_data)
    #         # Assign M2M relationships
    #         for field, values in m2m_data.items():
    #             getattr(profile, field).set(values)

    #     return Response(self.get_serializer(user).data, status=status.HTTP_201_CREATED)
    @swagger_auto_schema(
    tags=["02. User Management"],
    manual_parameters=m2m_parameters,
    request_body=None  # ⛔ important: avoid conflicts with serializer
    # manual_parameters=[
    #     openapi.Parameter(
    #         'profile_image', openapi.IN_FORM,
    #         type=openapi.TYPE_FILE, description="Profile image"
    #     ),
    #     openapi.Parameter(
    #         'companies', openapi.IN_FORM,
    #         description="List of company IDs (use multiple values)",
    #         type=openapi.TYPE_ARRAY,
    #         items=openapi.Items(type=openapi.TYPE_INTEGER),
    #         collection_format='multi'
    #     ),
    #     openapi.Parameter(
    #         'regions', openapi.IN_FORM,
    #         description="List of region IDs (use multiple values)",
    #         type=openapi.TYPE_ARRAY,
    #         items=openapi.Items(type=openapi.TYPE_INTEGER),
    #         collection_format='multi'
    #     ),
    #     openapi.Parameter(
    #         'zones', openapi.IN_FORM,
    #         description="List of zone IDs (use multiple values)",
    #         type=openapi.TYPE_ARRAY,
    #         items=openapi.Items(type=openapi.TYPE_INTEGER),
    #         collection_format='multi'
    #     ),
    #     openapi.Parameter(
    #         'territories', openapi.IN_FORM,
    #         description="List of territory IDs (use multiple values)",
    #         type=openapi.TYPE_ARRAY,
    #         items=openapi.Items(type=openapi.TYPE_INTEGER),
    #         collection_format='multi'
    #     ),
    # ]
    ,
    responses={201: UserSerializer}
)
    @transaction.atomic
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        # Extract is_sales_staff flag
        is_sales_staff = serializer.validated_data.get('is_sales_staff', False)

        # ✅ Use request.data.getlist for M2M fields
        m2m_data = {
            'companies': request.data.getlist('companies'),
            'regions': request.data.getlist('regions'),
            'zones': request.data.getlist('zones'),
            'territories': request.data.getlist('territories'),
        }

        # Extract profile fields
        profile_fields = [
            'employee_code', 'phone_number', 'address', 'designation',
            'hod', 'master_hod', 'date_of_joining',
            'sick_leave_quota', 'casual_leave_quota', 'others_leave_quota'
        ]
        profile_data = {f: serializer.validated_data.pop(f, None) for f in profile_fields}

        # Extract password
        password = serializer.validated_data.pop('password', None)

        # Create user
        user = User(**serializer.validated_data)
        if password:
            user.set_password(password)
        user.is_sales_staff = is_sales_staff
        user.save()

        # Create sales profile if needed
        if is_sales_staff:
            profile = SalesStaffProfile.objects.create(user=user, **profile_data)
            # ✅ Assign M2M relations
            for field, values in m2m_data.items():
                if values:  # convert string IDs -> int IDs
                    getattr(profile, field).set(map(int, values))

        return Response(self.get_serializer(user).data, status=status.HTTP_201_CREATED)

    @swagger_auto_schema(tags=["02. User Management"],
                         operation_description=(
            "Update a user.\n\n"
            "**Note:** Only admin/superuser can update `role` and `is_active`.\n"
            "Regular users can only update their own profile fields (`first_name`, `last_name`, `profile_image`)."
        ),request_body=UserSerializer)
    @transaction.atomic
    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)

        is_sales_staff = serializer.validated_data.get('is_sales_staff', instance.is_sales_staff)

        # Extract M2M fields
        m2m_fields = ['companies', 'regions', 'zones', 'territories']
        m2m_data = {field: serializer.validated_data.pop(field, None) for field in m2m_fields}

        # Extract profile fields
        profile_fields = [
            'employee_code', 'phone_number', 'address', 'designation',
            'hod', 'master_hod','date_of_joining',
            'sick_leave_quota', 'casual_leave_quota', 'others_leave_quota'
        ]
        profile_data = {f: serializer.validated_data.pop(f, None) for f in profile_fields}

        # Password update
        password = serializer.validated_data.pop('password', None)
        if password:
            instance.set_password(password)

        # Restrict certain fields for non-admins
        if not (request.user.is_staff or request.user.is_superuser):
            for field in ['role', 'is_active', 'is_staff']:
                serializer.validated_data.pop(field, None)

        # Update user fields
        for attr, value in serializer.validated_data.items():
            setattr(instance, attr, value)
        instance.is_sales_staff = is_sales_staff
        instance.save()

        # Handle sales profile
        profile = getattr(instance, 'sales_profile', None)
        if is_sales_staff:
            if not profile:
                profile = SalesStaffProfile.objects.create(user=instance)

            # Update regular profile fields
            for field, value in profile_data.items():
                if value is not None:
                    setattr(profile, field, value)

            # Update M2M fields
            for field, values in m2m_data.items():
                if values is not None:
                    getattr(profile, field).set(values)

            profile.save()
        else:
            # Soft detach if user is no longer sales staff
            if profile:
                profile.is_vacant = True
                profile.save()

        return Response(self.get_serializer(instance).data, status=status.HTTP_200_OK)
#     # ----------------------
#     # Swagger: partial_update
#     # ----------------------
    @swagger_auto_schema(tags=["02. User Management"],
                         operation_description=(
            "Partially update a user.\n\n"
            "**Note:** Only admin/superuser can update `role` and `is_active`.\n"
            "Regular users can only update their own profile fields (`first_name`, `last_name`, `profile_image`)."
        ),request_body=UserSerializer)
    def partial_update(self, request, *args, **kwargs):
        kwargs['partial'] = True
        return self.update(request, *args, **kwargs)

    @swagger_auto_schema(tags=["02. User Management"])
    def destroy(self, request, *args, **kwargs):
        """
        Soft delete a user.
        Only superusers are allowed to perform this action.
        """
        if not request.user.is_superuser:
            raise PermissionDenied("Only superusers can delete users.")

        instance = self.get_object()
        instance.is_active = False
        instance.save()

        # if SalesProfile exists, mark as vacant
        if hasattr(instance, "sales_profile"):
            instance.sales_profile.is_vacant = True
            instance.sales_profile.save()

        return Response(
            {"detail": f"User {instance.username} soft deleted."},
            status=status.HTTP_204_NO_CONTENT
        )