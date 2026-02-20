
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import OrderingFilter, SearchFilter
from rest_framework import viewsets, permissions
from rest_framework.permissions import IsAuthenticated
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.decorators import action, permission_classes
from django.contrib.auth import get_user_model
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from django.core.exceptions import PermissionDenied
from .filters import UserFilter
from .serializers import UserSerializer, UserUpdateSerializer
from accounts.permissions import HasRolePermission
from accounts.hierarchy_permissions import CanViewHierarchy, CanManageHierarchy
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
        description="[SALES STAFF FIELD] List of company IDs (required if is_sales_staff=true)",
        type=openapi.TYPE_ARRAY,
        items=openapi.Items(type=openapi.TYPE_INTEGER),
        required=False
    ),
    openapi.Parameter(
        "regions",
        openapi.IN_FORM,
        description="[SALES STAFF FIELD] List of region IDs (required if is_sales_staff=true)",
        type=openapi.TYPE_ARRAY,
        items=openapi.Items(type=openapi.TYPE_INTEGER),
        required=False
    ),
    openapi.Parameter(
        "zones",
        openapi.IN_FORM,
        description="[SALES STAFF FIELD] List of zone IDs (required if is_sales_staff=true)",
        type=openapi.TYPE_ARRAY,
        items=openapi.Items(type=openapi.TYPE_INTEGER),
        required=False
    ),
    openapi.Parameter(
        "territories",
        openapi.IN_FORM,
        description="[SALES STAFF FIELD] List of territory IDs (required if is_sales_staff=true)",
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
        description="[USER FIELD] Set to true if user is a dealer",
        type=openapi.TYPE_BOOLEAN,
        required=False
    ),
    openapi.Parameter(
        "dealer_business_name",
        openapi.IN_FORM,
        description="[DEALER FIELD] Business/Company Name (required if is_dealer=true)",
        type=openapi.TYPE_STRING,
        required=False
    ),
    openapi.Parameter(
        "dealer_cnic_number",
        openapi.IN_FORM,
        description="[DEALER FIELD] CNIC Number (13 or 15 digits, required if is_dealer=true)",
        type=openapi.TYPE_STRING,
        required=False
    ),
    openapi.Parameter(
        "dealer_contact_number",
        openapi.IN_FORM,
        description="[DEALER FIELD] Primary Contact Number (required if is_dealer=true)",
        type=openapi.TYPE_STRING,
        required=False
    ),
    openapi.Parameter(
        "dealer_mobile_phone",
        openapi.IN_FORM,
        description="[DEALER FIELD] Mobile/WhatsApp Number",
        type=openapi.TYPE_STRING,
        required=False
    ),
    openapi.Parameter(
        "dealer_company_id",
        openapi.IN_FORM,
        description="[DEALER FIELD] Company ID (required if is_dealer=true)",
        type=openapi.TYPE_INTEGER,
        required=False
    ),
    openapi.Parameter(
        "dealer_region_id",
        openapi.IN_FORM,
        description="[DEALER FIELD] Region ID",
        type=openapi.TYPE_INTEGER,
        required=False
    ),
    openapi.Parameter(
        "dealer_zone_id",
        openapi.IN_FORM,
        description="[DEALER FIELD] Zone ID",
        type=openapi.TYPE_INTEGER,
        required=False
    ),
    openapi.Parameter(
        "dealer_territory_id",
        openapi.IN_FORM,
        description="[DEALER FIELD] Territory ID",
        type=openapi.TYPE_INTEGER,
        required=False
    ),
    openapi.Parameter(
        "dealer_address",
        openapi.IN_FORM,
        description="[DEALER FIELD] Full Address (required if is_dealer=true)",
        type=openapi.TYPE_STRING,
        required=False
    ),
    openapi.Parameter(
        "dealer_city",
        openapi.IN_FORM,
        description="[DEALER FIELD] City",
        type=openapi.TYPE_STRING,
        required=False
    ),
    openapi.Parameter(
        "dealer_state",
        openapi.IN_FORM,
        description="[DEALER FIELD] State/Province",
        type=openapi.TYPE_STRING,
        required=False
    ),
    openapi.Parameter(
        "dealer_federal_tax_id",
        openapi.IN_FORM,
        description="[DEALER FIELD] NTN Number (National Tax Number)",
        type=openapi.TYPE_STRING,
        required=False
    ),
    openapi.Parameter(
        "dealer_filer_status",
        openapi.IN_FORM,
        description="[DEALER FIELD] Tax Filer Status ('01' or '02')",
        type=openapi.TYPE_STRING,
        required=False,
        enum=['01', '02']
    ),
    openapi.Parameter(
        "dealer_govt_license_number",
        openapi.IN_FORM,
        description="[DEALER FIELD] Government License Number",
        type=openapi.TYPE_STRING,
        required=False
    ),
    openapi.Parameter(
        "dealer_license_expiry",
        openapi.IN_FORM,
        description="[DEALER FIELD] License Expiry Date (YYYY-MM-DD)",
        type=openapi.TYPE_STRING,
        format='date',
        required=False
    ),
    openapi.Parameter(
        "dealer_minimum_investment",
        openapi.IN_FORM,
        description="[DEALER FIELD] Minimum Investment Amount",
        type=openapi.TYPE_INTEGER,
        required=False
    ),
    openapi.Parameter(
        "dealer_cnic_front_image",
        openapi.IN_FORM,
        description="[DEALER FIELD] CNIC Front Image (JPEG, PNG)",
        type=openapi.TYPE_FILE,
        required=False
    ),
    openapi.Parameter(
        "dealer_cnic_back_image",
        openapi.IN_FORM,
        description="[DEALER FIELD] CNIC Back Image (JPEG, PNG)",
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
        operation_description="""
        List all users with pagination, filtering, and search support.
        
        **Filtering Options:**
        - `is_active`: Filter by active status (true/false)
        - `role`: Filter by role ID
        - `is_sales_staff`: Filter by sales staff status
        - `is_dealer`: Filter by dealer status
        - `companies`, `regions`, `zones`, `territories`: Filter by location assignments
        
        **Search:** Search by username, email, first_name, last_name, phone_number
        
        **Ordering:** Order by id, username, email, first_name, last_name, is_active, role
        """,
        manual_parameters=[
            openapi.Parameter('is_active', openapi.IN_QUERY, type=openapi.TYPE_BOOLEAN, description="Filter by active status", enum=[True, False]),
            openapi.Parameter('role', openapi.IN_QUERY, type=openapi.TYPE_INTEGER, description="Filter by role ID"),
            openapi.Parameter('is_sales_staff', openapi.IN_QUERY, type=openapi.TYPE_BOOLEAN, description="Filter by sales staff", enum=[True, False]),
            openapi.Parameter('is_dealer', openapi.IN_QUERY, type=openapi.TYPE_BOOLEAN, description="Filter by dealer status", enum=[True, False]),
            openapi.Parameter('search', openapi.IN_QUERY, type=openapi.TYPE_STRING, description="Search by username, email, name, or phone number"),
            openapi.Parameter('ordering', openapi.IN_QUERY, type=openapi.TYPE_STRING, description="Order by field (e.g., 'id', '-email', 'username')"),
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
        ],
        responses={
            200: openapi.Response(
                description='List of users',
                examples={
                    'application/json': {
                        'count': 2,
                        'next': None,
                        'previous': None,
                        'results': [
                            {
                                'id': 1,
                                'username': 'admin',
                                'email': 'admin@example.com',
                                'phone_number': '03001111111',
                                'company': 1,
                                'company_name': '4B-BIO',
                                'first_name': 'Admin',
                                'last_name': 'User',
                                'role': 1,
                                'is_active': True,
                                'is_sales_staff': False,
                                'is_dealer': False,
                                'profile_image': 'http://localhost:8000/media/profile_images/admin.jpg'
                            },
                            {
                                'id': 2,
                                'username': 'sales_user',
                                'email': 'sales@example.com',
                                'phone_number': '03002222222',
                                'company': 1,
                                'company_name': '4B-BIO',
                                'first_name': 'Sales',
                                'last_name': 'Staff',
                                'role': 2,
                                'is_active': True,
                                'is_sales_staff': True,
                                'is_dealer': False,
                                'profile_image': None
                            }
                        ]
                    }
                }
            )
        }
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)


    @swagger_auto_schema(
        tags=["02. User Management"],
        operation_description="""
        Create a new user account with optional sales staff or dealer profile.
        
        ---
        
        ## 👤 USER FIELDS (Required for all users)
        
        | Field | Type | Required | Description |
        |-------|------|----------|-------------|
        | `username` | string | ✅ Yes | Unique username |
        | `email` | string | ✅ Yes | Email address |
        | `password` | string | ✅ Yes | Password (min 6 characters) |
        | `first_name` | string | ✅ Yes | First name (letters only) |
        | `last_name` | string | ✅ Yes | Last name (letters only) |
        | `phone_number` | string | ⚪ Optional | Phone number for login (e.g., 03001234567) |
        | `company` | integer | ⚪ Optional | Company ID this user belongs to |
        | `profile_image` | file | ⚪ Optional | Profile picture (JPG/PNG, max 5MB) |
        | `role` | integer | ⚪ Optional | Role ID |
        | `is_active` | boolean | ⚪ Optional | Active status (default: true) |
        | `is_sales_staff` | boolean | ⚪ Optional | Create as sales staff (default: false) |
        | `is_dealer` | boolean | ⚪ Optional | Create as dealer (default: false) |
        
        ---
        
        ## 💼 SALES STAFF FIELDS (Only if `is_sales_staff=true`)
        
        **Basic Information:**
        | Field | Type | Required | Description |
        |-------|------|----------|-------------|
        | `employee_code` | string | ✅ Yes | Employee code |
        | `address` | string | ✅ Yes | Full address |
        | `designation` | string | ✅ Yes | Job designation (CEO, NSM, RSL, etc.) |
        | `date_of_joining` | date | ⚪ Optional | Joining date (YYYY-MM-DD) |
        
        **Location Assignment (M2M Relations):**
        | Field | Type | Required | Description |
        |-------|------|----------|-------------|
        | `companies` | array[int] | ✅ Yes | Company IDs (at least one) |
        | `regions` | array[int] | ✅ Yes | Region IDs (at least one) |
        | `zones` | array[int] | ✅ Yes | Zone IDs (at least one) |
        | `territories` | array[int] | ✅ Yes | Territory IDs (at least one) |
        
        **Reporting Hierarchy:**
        | Field | Type | Required | Description |
        |-------|------|----------|-------------|
        | `manager` | integer | ⚪ Optional | Direct manager (SalesStaffProfile ID) |
        | `hod` | integer | ⚪ Optional | Head of Department (SalesStaffProfile ID) |
        | `master_hod` | integer | ⚪ Optional | Master HOD (SalesStaffProfile ID) |
        
        **Leave Quotas:**
        | Field | Type | Required | Description |
        |-------|------|----------|-------------|
        | `sick_leave_quota` | integer | ⚪ Optional | Sick leave quota (default: 0) |
        | `casual_leave_quota` | integer | ⚪ Optional | Casual leave quota (default: 0) |
        | `others_leave_quota` | integer | ⚪ Optional | Other leave quota (default: 0) |
        
        ---
        
        ## 🏪 DEALER FIELDS (Only if `is_dealer=true`)
        
        **Basic Information:**
        | Field | Type | Required | Description |
        |-------|------|----------|-------------|
        | `dealer_business_name` | string | ✅ Yes | Business/Company name |
        | `dealer_cnic_number` | string | ✅ Yes | CNIC number (13 or 15 digits) |
        | `dealer_contact_number` | string | ✅ Yes | Primary contact number |
        | `dealer_mobile_phone` | string | ⚪ Optional | Mobile/WhatsApp number |
        | `dealer_address` | string | ✅ Yes | Full address |
        | `dealer_city` | string | ⚪ Optional | City |
        | `dealer_state` | string | ⚪ Optional | State/Province |
        
        **Location Assignment:**
        | Field | Type | Required | Description |
        |-------|------|----------|-------------|
        | `dealer_company_id` | integer | ✅ Yes | Company ID |
        | `dealer_region_id` | integer | ⚪ Optional | Region ID |
        | `dealer_zone_id` | integer | ⚪ Optional | Zone ID |
        | `dealer_territory_id` | integer | ⚪ Optional | Territory ID |
        
        **Tax & Legal:**
        | Field | Type | Required | Description |
        |-------|------|----------|-------------|
        | `dealer_federal_tax_id` | string | ⚪ Optional | NTN number |
        | `dealer_filer_status` | string | ⚪ Optional | Tax filer status ('01' or '02') |
        | `dealer_govt_license_number` | string | ⚪ Optional | Government license number |
        | `dealer_license_expiry` | date | ⚪ Optional | License expiry date (YYYY-MM-DD) |
        
        **Financial:**
        | Field | Type | Required | Description |
        |-------|------|----------|-------------|
        | `dealer_minimum_investment` | integer | ⚪ Optional | Minimum investment amount |
        
        **CNIC Images:**
        | Field | Type | Required | Description |
        |-------|------|----------|-------------|
        | `dealer_cnic_front_image` | file | ⚪ Optional | CNIC front image (JPEG, PNG) |
        | `dealer_cnic_back_image` | file | ⚪ Optional | CNIC back image (JPEG, PNG) |
        
        ---
        
        **Authorization:** Requires authentication
        """,
        manual_parameters=[
            openapi.Parameter('is_active', openapi.IN_FORM, type=openapi.TYPE_BOOLEAN, description="[USER FIELD] Set user active status (default: true)", required=False),
            openapi.Parameter('phone_number', openapi.IN_FORM, type=openapi.TYPE_STRING, description="[USER FIELD] Phone number for login (e.g., 03001234567)", required=False),
            openapi.Parameter('company', openapi.IN_FORM, type=openapi.TYPE_INTEGER, description="[USER FIELD] Company ID this user belongs to", required=False),
        ] + m2m_parameters + dealer_parameters,
        request_body=None,  # ⛔ important: avoid conflicts with serializer
        responses={
            201: openapi.Response(
                description='User created successfully',
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'id': openapi.Schema(type=openapi.TYPE_INTEGER, description='User ID', example=123),
                        'username': openapi.Schema(type=openapi.TYPE_STRING, description='Username', example='john_doe'),
                        'email': openapi.Schema(type=openapi.TYPE_STRING, description='Email address', example='john@example.com'),
                        'phone_number': openapi.Schema(type=openapi.TYPE_STRING, description='Phone number', example='03001234567', nullable=True),
                        'company': openapi.Schema(type=openapi.TYPE_INTEGER, description='Company ID', example=1, nullable=True),
                        'company_name': openapi.Schema(type=openapi.TYPE_STRING, description='Company name', example='4B-BIO', nullable=True),
                        'first_name': openapi.Schema(type=openapi.TYPE_STRING, description='First name', example='John'),
                        'last_name': openapi.Schema(type=openapi.TYPE_STRING, description='Last name', example='Doe'),
                        'role': openapi.Schema(type=openapi.TYPE_INTEGER, description='Role ID', example=1, nullable=True),
                        'is_active': openapi.Schema(type=openapi.TYPE_BOOLEAN, description='Active status', example=True),
                        'is_sales_staff': openapi.Schema(type=openapi.TYPE_BOOLEAN, description='Is sales staff', example=False),
                        'is_dealer': openapi.Schema(type=openapi.TYPE_BOOLEAN, description='Is dealer', example=False),
                        'profile_image': openapi.Schema(type=openapi.TYPE_STRING, description='Profile image URL', example='http://localhost:8000/media/profile_images/user.jpg', nullable=True),
                    }
                ),
                examples={
                    'application/json': {
                        'id': 123,
                        'username': 'john_doe',
                        'email': 'john@example.com',
                        'phone_number': '03001234567',
                        'company': 1,
                        'company_name': '4B-BIO',
                        'first_name': 'John',
                        'last_name': 'Doe',
                        'role': 1,
                        'is_active': True,
                        'is_sales_staff': False,
                        'is_dealer': False,
                        'profile_image': 'http://localhost:8000/media/profile_images/john_doe.jpg'
                    }
                }
            ),
            400: openapi.Response(
                description='Bad Request - Validation errors',
                examples={
                    'application/json': {
                        'username': ['A user with that username already exists.'],
                        'email': ['User with this email already exists.'],
                        'phone_number': ['User with this phone number already exists.'],
                        'password': ['This field is required.']
                    }
                }
            )
        }
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
            'hod', 'master_hod', 'manager', 'date_of_joining',
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
        operation_description="""
        Update a user (PUT /users/{id}/).
        
        **⚠️ Note:** PUT requires all fields. Use PATCH for partial updates.
        
        ---
        
        ## 👤 USER FIELDS
        All user fields can be updated (username, email, first_name, last_name, phone_number, company, profile_image, password, role, is_active).
        
        **Regular User Permissions:**
        - Can update: `first_name`, `last_name`, `profile_image`, `password`, `phone_number`, `company`
        
        **Admin/Superuser Only:**
        - Can update: `role`, `is_active`, `is_staff`, `username`, `email`
        
        ---
        
        ## 💼 SALES STAFF FIELDS (if `is_sales_staff=true`)
        Update sales profile fields including employee_code, address, designation, companies, regions, zones, territories, hod, master_hod.
        
        ---
        
        ## 🏪 DEALER FIELDS (if `is_dealer=true`)
        Update dealer profile fields including business_name, cnic_number, contact information, location assignment, tax details.
        
        ---
        
        **Profile Image Upload:**
        - Supported formats: JPG, JPEG, PNG
        - Maximum size: 5MB
        - Send as multipart/form-data
        
        **Authorization:** Regular users can only update their own profile.
        """,
        request_body=UserSerializer,
        manual_parameters=[
            openapi.Parameter(
                'profile_image',
                openapi.IN_FORM,
                description='[USER FIELD] Profile image file (JPG/PNG, max 5MB)',
                type=openapi.TYPE_FILE,
                required=False
            ),
            openapi.Parameter('phone_number', openapi.IN_FORM, type=openapi.TYPE_STRING, description="[USER FIELD] Phone number for login (e.g., 03001234567)", required=False),
            openapi.Parameter('company', openapi.IN_FORM, type=openapi.TYPE_INTEGER, description="[USER FIELD] Company ID this user belongs to", required=False),
        ] + m2m_parameters + dealer_parameters,
        responses={
            200: openapi.Response(
                description='User updated successfully',
                examples={
                    'application/json': {
                        'id': 123,
                        'username': 'john_doe',
                        'email': 'john@example.com',
                        'phone_number': '03001234567',
                        'company': 1,
                        'company_name': '4B-BIO',
                        'first_name': 'John',
                        'last_name': 'Doe',
                        'role': 1,
                        'is_active': True,
                        'is_sales_staff': False,
                        'is_dealer': False,
                        'profile_image': 'http://localhost:8000/media/profile_images/john_doe.jpg'
                    }
                }
            ),
            400: openapi.Response(
                description='Bad Request - Validation errors',
                examples={
                    'application/json': {
                        'email': ['User with this email already exists.'],
                        'phone_number': ['User with this phone number already exists.']
                    }
                }
            )
        }
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
            'hod', 'master_hod', 'manager', 'date_of_joining',
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
        operation_description="""
        Partially update a user profile (PATCH /users/{id}/).
        
        **✅ All fields are optional** - only send the fields you want to update.
        
        ---
        
        ## 👤 USER FIELDS (Basic Information)
        
        **Regular User Can Update:**
        - `first_name` - First name
        - `last_name` - Last name
        - `profile_image` - Profile picture (JPG/PNG, max 5MB)
        - `password` - New password (will be hashed)
        - `phone_number` - Phone number for login
        - `company` - Company ID this user belongs to
        
        **Admin/Superuser Only:**
        - `role` - User's role ID
        - `is_active` - Account active status
        - `is_staff` - Staff status
        - `email` - Email address
        - `username` - Username
        - `is_sales_staff` - Change sales staff status
        - `is_dealer` - Change dealer status
        
        ---
        
        ## 💼 SALES STAFF FIELDS (Only if `is_sales_staff=true`)
        
        **Profile Information:**
        - `employee_code` - Employee code
        - `address` - Full address
        - `designation` - Job designation
        - `date_of_joining` - Joining date
        
        **Location Assignment:**
        - `companies` - Company IDs (M2M)
        - `regions` - Region IDs (M2M)
        - `zones` - Zone IDs (M2M)
        - `territories` - Territory IDs (M2M)
        
        **Reporting Hierarchy:**
        - `manager` - Direct manager ID
        - `hod` - Head of Department ID
        - `master_hod` - Master HOD ID
        
        **Leave Quotas:**
        - `sick_leave_quota`, `casual_leave_quota`, `others_leave_quota`
        
        ---
        
        ## 🏪 DEALER FIELDS (Only if `is_dealer=true`)
        
        **Basic Information:**
        - `dealer_business_name` - Business name
        - `dealer_cnic_number` - CNIC number
        - `dealer_contact_number` - Contact number
        - `dealer_mobile_phone` - Mobile/WhatsApp
        - `dealer_address`, `dealer_city`, `dealer_state`
        
        **Location Assignment:**
        - `dealer_company_id`, `dealer_region_id`, `dealer_zone_id`, `dealer_territory_id`
        
        **Tax & Legal:**
        - `dealer_federal_tax_id` - NTN number
        - `dealer_filer_status` - Tax filer status
        - `dealer_govt_license_number`, `dealer_license_expiry`
        
        **Financial:**
        - `dealer_minimum_investment`
        
        **Documents:**
        - `dealer_cnic_front_image`, `dealer_cnic_back_image`
        
        ---
        
        **Authorization:** Regular users can only update their own profile. Admins can update any user.
        """,
        request_body=UserSerializer,
        manual_parameters=[
            openapi.Parameter(
                'profile_image',
                openapi.IN_FORM,
                description='[USER FIELD] Profile image file (JPG/PNG, max 5MB)',
                type=openapi.TYPE_FILE,
                required=False
            ),
            openapi.Parameter('phone_number', openapi.IN_FORM, type=openapi.TYPE_STRING, description="[USER FIELD] Phone number for login (e.g., 03001234567)", required=False),
            openapi.Parameter('company', openapi.IN_FORM, type=openapi.TYPE_INTEGER, description="[USER FIELD] Company ID this user belongs to", required=False),
        ] + m2m_parameters + dealer_parameters,
        responses={
            200: openapi.Response(
                description='User updated successfully',
                examples={
                    'application/json': {
                        'id': 123,
                        'username': 'john_doe',
                        'email': 'john@example.com',
                        'phone_number': '03001234567',
                        'company': 1,
                        'company_name': '4B-BIO',
                        'first_name': 'John',
                        'last_name': 'Doe Updated',
                        'role': 1,
                        'is_active': True,
                        'is_sales_staff': False,
                        'is_dealer': False,
                        'profile_image': 'http://localhost:8000/media/profile_images/john_doe.jpg'
                    }
                }
            ),
            400: openapi.Response(
                description='Bad Request - Validation errors',
                examples={
                    'application/json': {
                        'phone_number': ['User with this phone number already exists.']
                    }
                }
            )
        }
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
    
    # ==================== HIERARCHY ENDPOINTS ====================
    
    @swagger_auto_schema(
        tags=["02. User Management"],
        operation_description="Get all subordinates (direct + indirect) of the current user",
        responses={
            200: openapi.Response(
                description='List of subordinate users with their profiles',
                examples={
                    'application/json': {
                        'count': 3,
                        'subordinates': [
                            {
                                'id': 5,
                                'username': 'john.doe',
                                'email': 'john@example.com',
                                'first_name': 'John',
                                'last_name': 'Doe',
                                'designation': 'FSM',
                                'territories': [1, 2]
                            }
                        ]
                    }
                }
            )
        }
    )
    @action(detail=False, methods=['get'], url_path='my-team', permission_classes=[IsAuthenticated, CanViewHierarchy])
    def my_team(self, request):
        """
        Get all subordinates (direct and indirect) of the current user.
        Returns full user details with sales profile.
        """
        sales_profile = getattr(request.user, 'sales_profile', None)
        if not sales_profile:
            return Response(
                {'error': 'Only sales staff can view their team'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        subordinates = sales_profile.get_all_subordinates(include_self=False)
        subordinate_users = User.objects.filter(
            sales_profile__in=subordinates
        ).select_related('sales_profile')
        
        serializer = UserSerializer(subordinate_users, many=True)
        
        return Response({
            'count': subordinate_users.count(),
            'subordinates': serializer.data
        })
    
    @swagger_auto_schema(
        tags=["02. User Management"],
        operation_description="Get the upward reporting chain (manager → manager's manager → CEO)",
        responses={
            200: openapi.Response(
                description='Reporting chain from current user to top-level manager',
                examples={
                    'application/json': {
                        'chain': [
                            {
                                'id': 3,
                                'name': 'Ahmed Ali',
                                'designation': 'ZM',
                                'level': 0
                            },
                            {
                                'id': 2,
                                'name': 'Sara Khan',
                                'designation': 'RSL',
                                'level': 1
                            },
                            {
                                'id': 1,
                                'name': 'CEO',
                                'designation': 'CEO',
                                'level': 2
                            }
                        ]
                    }
                }
            )
        }
    )
    @action(detail=False, methods=['get'], url_path='my-reporting-chain', permission_classes=[IsAuthenticated, CanViewHierarchy])
    def my_reporting_chain(self, request):
        """
        Get the upward reporting chain (self → manager → manager's manager → ... → CEO).
        Shows who this user reports to, all the way up the hierarchy.
        """
        sales_profile = getattr(request.user, 'sales_profile', None)
        if not sales_profile:
            return Response(
                {'error': 'Only sales staff have reporting chains'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        chain = sales_profile.get_reporting_chain(include_self=True)
        
        chain_data = []
        for level, profile in enumerate(chain):
            chain_data.append({
                'id': profile.id,
                'user_id': profile.user.id if profile.user else None,
                'name': str(profile),
                'designation': profile.designation,
                'level': level,
                'is_self': (level == 0)
            })
        
        return Response({'chain': chain_data})
    
    @swagger_auto_schema(
        tags=["02. User Management"],
        operation_description="Get complete hierarchy view: subordinates + reporting chain",
        responses={
            200: openapi.Response(
                description='Complete hierarchy showing both upward and downward relationships',
                examples={
                    'application/json': {
                        'self': {
                            'id': 3,
                            'name': 'Ahmed Ali',
                            'designation': 'ZM'
                        },
                        'manager': {
                            'id': 2,
                            'name': 'Sara Khan',
                            'designation': 'RSL'
                        },
                        'subordinates_count': 3,
                        'subordinates': [
                            {
                                'id': 5,
                                'name': 'John Doe',
                                'designation': 'FSM'
                            }
                        ]
                    }
                }
            )
        }
    )
    @action(detail=False, methods=['get'], url_path='my-hierarchy', permission_classes=[IsAuthenticated, CanViewHierarchy])
    def my_hierarchy(self, request):
        """
        Get a complete hierarchy view: manager, self, and subordinates.
        Useful for organization charts and understanding position in hierarchy.
        """
        sales_profile = getattr(request.user, 'sales_profile', None)
        if not sales_profile:
            return Response(
                {'error': 'Only sales staff have hierarchies'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        subordinates = sales_profile.get_all_subordinates(include_self=False)
        
        hierarchy_data = {
            'self': {
                'id': sales_profile.id,
                'user_id': request.user.id,
                'name': str(sales_profile),
                'designation': sales_profile.designation,
                'employee_code': sales_profile.employee_code,
            },
            'manager': None,
            'subordinates_count': subordinates.count(),
            'subordinates': []
        }
        
        # Add manager info
        if sales_profile.manager:
            hierarchy_data['manager'] = {
                'id': sales_profile.manager.id,
                'user_id': sales_profile.manager.user.id if sales_profile.manager.user else None,
                'name': str(sales_profile.manager),
                'designation': sales_profile.manager.designation,
            }
        
        # Add subordinates
        for sub in subordinates:
            hierarchy_data['subordinates'].append({
                'id': sub.id,
                'user_id': sub.user.id if sub.user else None,
                'name': str(sub),
                'designation': sub.designation,
                'is_direct': (sub.manager_id == sales_profile.id)
            })
        
        return Response(hierarchy_data)