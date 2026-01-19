
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
    
    # Dealer-specific parameters
    dealer_parameters = [
    openapi.Parameter(
        "is_dealer",
        openapi.IN_FORM,
        description="Set to true if user is a dealer",
        type=openapi.TYPE_BOOLEAN,
        required=False
    ),
    openapi.Parameter(
        "dealer_business_name",
        openapi.IN_FORM,
        description="Business/Company Name (required if is_dealer=true)",
        type=openapi.TYPE_STRING,
        required=False
    ),
    openapi.Parameter(
        "dealer_cnic_number",
        openapi.IN_FORM,
        description="CNIC Number (13 or 15 digits, required if is_dealer=true)",
        type=openapi.TYPE_STRING,
        required=False
    ),
    openapi.Parameter(
        "dealer_contact_number",
        openapi.IN_FORM,
        description="Primary Contact Number (required if is_dealer=true)",
        type=openapi.TYPE_STRING,
        required=False
    ),
    openapi.Parameter(
        "dealer_mobile_phone",
        openapi.IN_FORM,
        description="Mobile/WhatsApp Number",
        type=openapi.TYPE_STRING,
        required=False
    ),
    openapi.Parameter(
        "dealer_company_id",
        openapi.IN_FORM,
        description="Company ID (required if is_dealer=true)",
        type=openapi.TYPE_INTEGER,
        required=False
    ),
    openapi.Parameter(
        "dealer_region_id",
        openapi.IN_FORM,
        description="Region ID",
        type=openapi.TYPE_INTEGER,
        required=False
    ),
    openapi.Parameter(
        "dealer_zone_id",
        openapi.IN_FORM,
        description="Zone ID",
        type=openapi.TYPE_INTEGER,
        required=False
    ),
    openapi.Parameter(
        "dealer_territory_id",
        openapi.IN_FORM,
        description="Territory ID",
        type=openapi.TYPE_INTEGER,
        required=False
    ),
    openapi.Parameter(
        "dealer_address",
        openapi.IN_FORM,
        description="Full Address (required if is_dealer=true)",
        type=openapi.TYPE_STRING,
        required=False
    ),
    openapi.Parameter(
        "dealer_city",
        openapi.IN_FORM,
        description="City",
        type=openapi.TYPE_STRING,
        required=False
    ),
    openapi.Parameter(
        "dealer_state",
        openapi.IN_FORM,
        description="State/Province",
        type=openapi.TYPE_STRING,
        required=False
    ),
    openapi.Parameter(
        "dealer_federal_tax_id",
        openapi.IN_FORM,
        description="NTN Number (National Tax Number)",
        type=openapi.TYPE_STRING,
        required=False
    ),
    openapi.Parameter(
        "dealer_filer_status",
        openapi.IN_FORM,
        description="Tax Filer Status",
        type=openapi.TYPE_STRING,
        required=False,
        enum=['01', '02']
    ),
    openapi.Parameter(
        "dealer_govt_license_number",
        openapi.IN_FORM,
        description="Government License Number",
        type=openapi.TYPE_STRING,
        required=False
    ),
    openapi.Parameter(
        "dealer_license_expiry",
        openapi.IN_FORM,
        description="License Expiry Date (YYYY-MM-DD)",
        type=openapi.TYPE_STRING,
        format='date',
        required=False
    ),
    openapi.Parameter(
        "dealer_minimum_investment",
        openapi.IN_FORM,
        description="Minimum Investment Amount",
        type=openapi.TYPE_INTEGER,
        required=False
    ),
    openapi.Parameter(
        "dealer_cnic_front_image",
        openapi.IN_FORM,
        description="CNIC Front Image (JPEG, PNG)",
        type=openapi.TYPE_FILE,
        required=False
    ),
    openapi.Parameter(
        "dealer_cnic_back_image",
        openapi.IN_FORM,
        description="CNIC Back Image (JPEG, PNG)",
        type=openapi.TYPE_FILE,
        required=False
    ),
]
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
        # Check if user is authenticated before filtering
        if user.is_authenticated and not user.is_superuser:
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
    
    # ----------------------
    # Swagger: list
    # ----------------------
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


    @swagger_auto_schema(
        tags=["02. User Management"],
        manual_parameters=m2m_parameters + dealer_parameters,
        request_body=None,  # ⛔ important: avoid conflicts with serializer
        responses={201: UserSerializer}
    )
    @transaction.atomic
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        # Extract is_sales_staff and is_dealer flags
        is_sales_staff = serializer.validated_data.pop('is_sales_staff', False)
        is_dealer = serializer.validated_data.pop('is_dealer', False)

        # ✅ Use request.data.getlist for M2M fields
        m2m_data = {
            'companies': request.data.getlist('companies'),
            'regions': request.data.getlist('regions'),
            'zones': request.data.getlist('zones'),
            'territories': request.data.getlist('territories'),
        }

        # Remove M2M fields from validated_data (they belong to SalesStaffProfile, not User)
        for field in ['companies', 'regions', 'zones', 'territories']:
            serializer.validated_data.pop(field, None)

        # Extract profile fields
        profile_fields = [
            'employee_code', 'phone_number', 'address', 'designation',
            'hod', 'master_hod', 'date_of_joining',
            'sick_leave_quota', 'casual_leave_quota', 'others_leave_quota'
        ]
        profile_data = {f: serializer.validated_data.pop(f, None) for f in profile_fields}

        # Extract dealer fields from validated_data
        dealer_fields = [
            'dealer_business_name', 'dealer_cnic_number', 'dealer_contact_number', 'dealer_mobile_phone',
            'dealer_company_id', 'dealer_region_id', 'dealer_zone_id', 'dealer_territory_id',
            'dealer_address', 'dealer_city', 'dealer_state', 'dealer_federal_tax_id', 'dealer_filer_status',
            'dealer_govt_license_number', 'dealer_license_expiry', 'dealer_minimum_investment',
            'dealer_cnic_front_image', 'dealer_cnic_back_image'
        ]
        dealer_data = {}
        dealer_fields_mapping = {
            'dealer_business_name': 'business_name',
            'dealer_cnic_number': 'cnic_number',
            'dealer_contact_number': 'contact_number',
            'dealer_mobile_phone': 'mobile_phone',
            'dealer_company_id': 'company_id',
            'dealer_region_id': 'region_id',
            'dealer_zone_id': 'zone_id',
            'dealer_territory_id': 'territory_id',
            'dealer_address': 'address',
            'dealer_city': 'city',
            'dealer_state': 'state',
            'dealer_federal_tax_id': 'federal_tax_id',
            'dealer_filer_status': 'filer_status',
            'dealer_govt_license_number': 'govt_license_number',
            'dealer_license_expiry': 'license_expiry',
            'dealer_minimum_investment': 'minimum_investment',
            'dealer_cnic_front_image': 'cnic_front_image',
            'dealer_cnic_back_image': 'cnic_back_image',
        }
        for request_field, model_field in dealer_fields_mapping.items():
            value = serializer.validated_data.pop(request_field, None)
            if value is not None:
                dealer_data[model_field] = value

        # Extract password
        password = serializer.validated_data.pop('password', None)

        # Create user
        user = User(**serializer.validated_data)
        if password:
            user.set_password(password)
        user.is_sales_staff = is_sales_staff
        user.is_dealer = is_dealer
        user.save()

        # Create sales profile if needed
        if is_sales_staff:
            profile = SalesStaffProfile.objects.create(user=user, **profile_data)
            # ✅ Assign M2M relations
            for field, values in m2m_data.items():
                if values:  # convert string IDs -> int IDs
                    getattr(profile, field).set(map(int, values))

        # Create dealer profile if needed
        if is_dealer and dealer_data:
            from FieldAdvisoryService.models import Dealer
            
            # Ensure required fields are present
            if not dealer_data.get('company_id'):
                # Company is required for Dealer - skip creation if not provided
                pass
            else:
                dealer_data['user'] = user
                dealer_data['name'] = f"{user.first_name} {user.last_name}".strip() or user.username
                
                # Handle file fields separately
                cnic_front = dealer_data.pop('cnic_front_image', None)
                cnic_back = dealer_data.pop('cnic_back_image', None)
                
                # Create dealer instance
                dealer = Dealer.objects.create(**dealer_data)
                
                if cnic_front:
                    dealer.cnic_front_image = cnic_front
                if cnic_back:
                    dealer.cnic_back_image = cnic_back
                
                dealer.save()

        return Response(self.get_serializer(user).data, status=status.HTTP_201_CREATED)

    @swagger_auto_schema(
        tags=["02. User Management"],
        operation_description=(
            "Update a user (PUT /users/{id}/).\n\n"
            "**Note:** PUT requires all fields. Use PATCH for partial updates.\n\n"
            "**Profile Image Upload:**\n"
            "- Supported formats: JPG, JPEG, PNG\n"
            "- Maximum size: 5MB\n"
            "- Send as multipart/form-data\n\n"
            "**Admin/Superuser Restrictions:**\n"
            "- Only admin/superuser can update `role`, `is_active`, `is_staff`\n"
            "- Regular users can only update: `first_name`, `last_name`, `profile_image`, `password`\n\n"
            "**Authorization:** Regular users can only update their own profile."
        ),
        request_body=UserSerializer,
        manual_parameters=[
            openapi.Parameter(
                'profile_image',
                openapi.IN_FORM,
                description='Profile image file (JPG/PNG, max 5MB)',
                type=openapi.TYPE_FILE,
                required=False
            )
        ] + m2m_parameters + dealer_parameters
    )
    @transaction.atomic
    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)

        is_sales_staff = serializer.validated_data.pop('is_sales_staff', instance.is_sales_staff)
        is_dealer = serializer.validated_data.pop('is_dealer', instance.is_dealer)

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

        # Extract dealer fields
        dealer_fields_mapping = {
            'dealer_business_name': 'business_name',
            'dealer_cnic_number': 'cnic_number',
            'dealer_contact_number': 'contact_number',
            'dealer_mobile_phone': 'mobile_phone',
            'dealer_company_id': 'company_id',
            'dealer_region_id': 'region_id',
            'dealer_zone_id': 'zone_id',
            'dealer_territory_id': 'territory_id',
            'dealer_address': 'address',
            'dealer_city': 'city',
            'dealer_state': 'state',
            'dealer_federal_tax_id': 'federal_tax_id',
            'dealer_filer_status': 'filer_status',
            'dealer_govt_license_number': 'govt_license_number',
            'dealer_license_expiry': 'license_expiry',
            'dealer_minimum_investment': 'minimum_investment',
            'dealer_cnic_front_image': 'cnic_front_image',
            'dealer_cnic_back_image': 'cnic_back_image',
        }
        dealer_data = {}
        for request_field, model_field in dealer_fields_mapping.items():
            value = serializer.validated_data.pop(request_field, None)
            if value is not None:
                dealer_data[model_field] = value

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
        instance.is_dealer = is_dealer
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

        # Handle dealer profile
        from FieldAdvisoryService.models import Dealer
        dealer = getattr(instance, 'dealer', None)
        if is_dealer:
            if not dealer:
                # Create new dealer if doesn't exist
                if dealer_data.get('company_id'):
                    dealer_data['user'] = instance
                    dealer_data['name'] = f"{instance.first_name} {instance.last_name}".strip() or instance.username
                    
                    # Handle file fields separately
                    cnic_front = dealer_data.pop('cnic_front_image', None)
                    cnic_back = dealer_data.pop('cnic_back_image', None)
                    
                    dealer = Dealer.objects.create(**dealer_data)
                    
                    if cnic_front:
                        dealer.cnic_front_image = cnic_front
                    if cnic_back:
                        dealer.cnic_back_image = cnic_back
                    
                    dealer.save()
            else:
                # Update existing dealer
                for field, value in dealer_data.items():
                    if field in ['cnic_front_image', 'cnic_back_image']:
                        # Handle file fields
                        if value:
                            setattr(dealer, field, value)
                    elif value is not None:
                        setattr(dealer, field, value)
                dealer.save()
        else:
            # If is_dealer is set to false, optionally delete dealer profile
            # For now, we'll keep the dealer record but mark user as non-dealer
            pass

        return Response(self.get_serializer(instance).data, status=status.HTTP_200_OK)
    # ----------------------
    # Swagger: partial_update (PATCH)
    # ----------------------
    @swagger_auto_schema(
        tags=["02. User Management"],
        operation_description=(
            "Partially update a user profile (PATCH /users/{id}/).\n\n"
            "**All fields are optional** - only send the fields you want to update.\n\n"
            "**Profile Image Upload:**\n"
            "- Supported formats: JPG, JPEG, PNG\n"
            "- Maximum size: 5MB\n"
            "- Send as multipart/form-data\n\n"
            "**Updatable Fields:**\n"
            "- `first_name`: User's first name\n"
            "- `last_name`: User's last name\n"
            "- `profile_image`: Profile picture (image file)\n"
            "- `password`: New password (will be hashed)\n\n"
            "**Admin/Superuser Only Fields:**\n"
            "- `role`: User's role ID\n"
            "- `is_active`: Account active status\n"
            "- `is_staff`: Staff status\n"
            "- `email`: Email address\n"
            "- `username`: Username\n\n"
            "**Sales Staff Fields** (if `is_sales_staff=true`):\n"
            "- `employee_code`, `phone_number`, `address`, `designation`\n"
            "- `hod`, `master_hod`, `date_of_joining`\n"
            "- `companies`, `regions`, `zones`, `territories` (M2M relations)\n\n"
            "**Dealer Fields** (if `is_dealer=true`):\n"
            "- `dealer_business_name`, `dealer_cnic_number`, `dealer_contact_number`\n"
            "- `dealer_company_id`, `dealer_region_id`, `dealer_zone_id`, `dealer_territory_id`\n"
            "- `dealer_address`, `dealer_city`, `dealer_state`\n"
            "- `dealer_federal_tax_id`, `dealer_filer_status`, `dealer_govt_license_number`\n"
            "- `dealer_license_expiry`, `dealer_minimum_investment`\n"
            "- `dealer_cnic_front_image`, `dealer_cnic_back_image`\n\n"
            "**Authorization:** Regular users can only update their own profile. "
            "Admins can update any user."
        ),
        request_body=UserSerializer,
        manual_parameters=[
            openapi.Parameter(
                'profile_image',
                openapi.IN_FORM,
                description='Profile image file (JPG/PNG, max 5MB)',
                type=openapi.TYPE_FILE,
                required=False
            )
        ] + m2m_parameters + dealer_parameters
    )
    def partial_update(self, request, *args, **kwargs):
        """
        PATCH endpoint for updating user profile.
        No fields are required - send only what needs to be updated.
        """
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