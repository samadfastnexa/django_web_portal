from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.core.validators import RegexValidator
from .models import Role
from .models import User, SalesStaffProfile
from FieldAdvisoryService.models import Region, Zone, Territory,Company
from FieldAdvisoryService.serializers import CompanySerializer, RegionSerializer, ZoneSerializer, TerritorySerializer
from django.db import transaction
User = get_user_model()

# ----------------------
# User Listing (Read-Only)
# ----------------------
class UserListSerializer(serializers.ModelSerializer):
    profile_image = serializers.SerializerMethodField()
    
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name', 'profile_image']
    
    def get_profile_image(self, obj):
        try:
            if obj.profile_image and hasattr(obj.profile_image, 'url'):
                return obj.profile_image.url
        except (ValueError, FileNotFoundError, OSError):
            pass
        return None

# ----------------------
# User Signup (Public Registration)
# ----------------------
class SalesStaffSerializer(serializers.ModelSerializer):
    class Meta:
        model = SalesStaffProfile
        fields = [
            'id', 'user', 'employee_code', 'phone_number',
            'address', 'designation', 'companies', 'regions', 'zones', 'territories',
            'hod', 'master_hod',
            'sick_leave_quota', 'casual_leave_quota', 'others_leave_quota'
        ]

class UserSignupSerializer(serializers.ModelSerializer):
    # User fields
    password = serializers.CharField(write_only=True, min_length=6)
    first_name = serializers.CharField(
        required=True,
        validators=[RegexValidator(r'^[A-Za-z\s]+$', 'Only letters and spaces are allowed.')]
    )
    last_name = serializers.CharField(
        required=True,
        validators=[RegexValidator(r'^[A-Za-z\s]+$', 'Only letters and spaces are allowed.')]
    )
    profile_image = serializers.ImageField(required=False)
    is_sales_staff = serializers.BooleanField(required=False)

    # Sales staff fields (optional, allow blank/null)
    employee_code = serializers.CharField(write_only=True, required=False, allow_blank=True)
    phone_number = serializers.CharField(write_only=True, required=False, allow_blank=True)
    # ✅ FIX: HODs must be ForeignKeys, not CharFields
    hod = serializers.PrimaryKeyRelatedField(queryset=SalesStaffProfile.objects.all(), write_only=True, required=False, allow_null=True)
    master_hod = serializers.PrimaryKeyRelatedField(queryset=SalesStaffProfile.objects.all(), write_only=True, required=False, allow_null=True)
   
    address = serializers.CharField(write_only=True, required=False, allow_blank=True)
    designation = serializers.CharField(write_only=True, required=False, allow_blank=True)
    company = serializers.PrimaryKeyRelatedField(
        queryset=Company.objects.all(), write_only=True, required=False, allow_null=True
    )
    region = serializers.PrimaryKeyRelatedField(
        queryset=Region.objects.all(), write_only=True, required=False, allow_null=True
    )
    zone = serializers.PrimaryKeyRelatedField(
        queryset=Zone.objects.all(), write_only=True, required=False, allow_null=True
    )
    territory = serializers.PrimaryKeyRelatedField(
        queryset=Territory.objects.all(), write_only=True, required=False, allow_null=True
    )
    sick_leave_quota = serializers.IntegerField(write_only=True, required=False, default=0)
    casual_leave_quota = serializers.IntegerField(write_only=True, required=False, default=0)
    others_leave_quota = serializers.IntegerField(write_only=True, required=False, default=0)
    class Meta:
        model = User
        fields = [
            'id', 'username', 'email', 'password',
            'first_name', 'last_name', 'profile_image',
            'role', 'is_active', 'is_staff',
            'is_sales_staff','date_joined',
            # SalesStaffProfile fields
            'employee_code', 'phone_number', 'address', 'designation','company','hod', 'master_hod',
            'region', 'zone', 'territory','sick_leave_quota', 'casual_leave_quota', 'others_leave_quota'
        ]
        read_only_fields = ['id', 'is_staff']

    def validate_email(self, value):
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError("A user with this email already exists.")
        return value

    def validate_username(self, value):
        if User.objects.filter(username=value).exists():
            raise serializers.ValidationError("This username is already taken.")
        return value

    def validate(self, data):
        if data.get('is_sales_staff'):
            required_fields = ['employee_code', 'phone_number', 'address', 'designation', 'region', 'zone', 'territory','company']
            missing = []
            blank = []
            for field in required_fields:
                value = data.get(field)
                if value is None:
                    missing.append(field)
                elif isinstance(value, str) and value.strip() == '':
                    blank.append(field)

            errors = {}
            if missing:
                errors['missing_fields'] = f"Missing required fields when is_sales_staff=True: {', '.join(missing)}"
            if blank:
                errors['blank_fields'] = f"Fields cannot be blank when is_sales_staff=True: {', '.join(blank)}"

            if errors:
                raise serializers.ValidationError(errors)
        return data


    def create(self, validated_data):
        is_sales = validated_data.pop('is_sales_staff', False)

        # Always remove sales staff–only fields from User data
        sales_staff_fields = [
            'employee_code', 'phone_number', 'address', 'designation',
            'company', 'region', 'zone', 'territory',
            'hod', 'master_hod',
            'sick_leave_quota', 'casual_leave_quota', 'others_leave_quota'
        ]
        sales_staff_data = {field: validated_data.pop(field, None) for field in sales_staff_fields}

        password = validated_data.pop('password')
        user = User(**validated_data)
        user.set_password(password)
        user.is_sales_staff = is_sales
        user.save()

        if is_sales:
            # Extract ManyToMany field data
            company = sales_staff_data.pop('company', None)
            region = sales_staff_data.pop('region', None)
            zone = sales_staff_data.pop('zone', None)
            territory = sales_staff_data.pop('territory', None)
            
            # Create the profile without ManyToMany fields
            profile = SalesStaffProfile.objects.create(user=user, **sales_staff_data)
            
            # Set ManyToMany relationships
            if company:
                profile.companies.set([company])
            if region:
                profile.regions.set([region])
            if zone:
                profile.zones.set([zone])
            if territory:
                profile.territories.set([territory])

        return user
# ----------------------
# Admin: Permission Serializer
# ----------------------
class PermissionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Permission
        fields = ['id', 'codename', 'name']

# ----------------------
# Admin: Role Serializer
# ----------------------
class RoleSerializer(serializers.ModelSerializer):
    permissions = PermissionSerializer(many=True, read_only=True)
    permission_ids = serializers.PrimaryKeyRelatedField(
        queryset=Permission.objects.all(),
        many=True,
        write_only=True,
        source='permissions'
    )

    class Meta:
        model = Role
        fields = ['id', 'name', 'permissions', 'permission_ids']
        ref_name = 'RoleSerializerForAdmin'  # ✅ Unique Swagger name
# ----------------------
# Admin: Change User Status
# ----------------------
class AdminUserStatusSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['is_active']


# Nested serializers for detailed information
class RoleDetailSerializer(serializers.ModelSerializer):
    class Meta:
        model = Role
        fields = ['id', 'name']


class HODDetailSerializer(serializers.ModelSerializer):
    """Simplified serializer for HOD to avoid circular references"""
    name = serializers.SerializerMethodField()
    
    class Meta:
        model = SalesStaffProfile
        fields = ['id', 'name']
    
    def get_name(self, obj):
        if obj.user:
            full_name = f"{obj.user.first_name} {obj.user.last_name}".strip()
            return full_name if full_name else obj.user.username
        return None


class CompanyDetailSerializer(serializers.ModelSerializer):
    class Meta:
        model = Company
        fields = ['id', 'Company_name']


class RegionDetailSerializer(serializers.ModelSerializer):
    class Meta:
        model = Region
        fields = ['id', 'name']


class ZoneDetailSerializer(serializers.ModelSerializer):
    class Meta:
        model = Zone
        fields = ['id', 'name']


class TerritoryDetailSerializer(serializers.ModelSerializer):
    class Meta:
        model = Territory
        fields = ['id', 'name']


class SalesStaffProfileSerializer(serializers.ModelSerializer):
    # For write operations (create/update), accept IDs
    companies_ids = serializers.PrimaryKeyRelatedField(
        many=True, queryset=Company.objects.all(), required=False, 
        source='companies', write_only=True
    )
    regions_ids = serializers.PrimaryKeyRelatedField(
        many=True, queryset=Region.objects.all(), required=False,
        source='regions', write_only=True
    )
    zones_ids = serializers.PrimaryKeyRelatedField(
        many=True, queryset=Zone.objects.all(), required=False,
        source='zones', write_only=True
    )
    territories_ids = serializers.PrimaryKeyRelatedField(
        many=True, queryset=Territory.objects.all(), required=False,
        source='territories', write_only=True
    )
    
    # For read operations (GET), return detailed objects with id and name
    companies = CompanyDetailSerializer(many=True, read_only=True)
    regions = RegionDetailSerializer(many=True, read_only=True)
    zones = ZoneDetailSerializer(many=True, read_only=True)
    territories = TerritoryDetailSerializer(many=True, read_only=True)
    hod = HODDetailSerializer(read_only=True)
    master_hod = HODDetailSerializer(read_only=True)

    class Meta:
        model = SalesStaffProfile
        fields = "__all__"
        read_only_fields = ['id', 'user']
        
# ----------------------
# Admin: Full User View/Update (password is optional)
# ----------------------
class UserSerializer(serializers.ModelSerializer):
    sales_profile = serializers.SerializerMethodField()
    profile_image_url = serializers.SerializerMethodField()
    profile_image = serializers.ImageField(write_only=True, required=False, allow_null=True)
    role = RoleDetailSerializer(read_only=True)
    role_id = serializers.PrimaryKeyRelatedField(
        queryset=Role.objects.all(), source='role', write_only=True, required=False
    )
    password = serializers.CharField(write_only=True, min_length=6, required=False)
    is_sales_staff = serializers.BooleanField(write_only=True, default=False, required=False)

    # Write-only SalesStaffProfile fields (using ManyToMany field names)
    employee_code = serializers.CharField(write_only=True, required=False)
    phone_number = serializers.CharField(write_only=True, required=False)
    address = serializers.CharField(write_only=True, required=False)
    designation = serializers.CharField(write_only=True, required=False)
    date_of_joining = serializers.DateField(write_only=True, required=False, allow_null=True)
    
    # Use plural field names to match the model's ManyToMany fields
    companies = serializers.PrimaryKeyRelatedField(
        many=True, queryset=Company.objects.all(), write_only=True, required=False
    )
    regions = serializers.PrimaryKeyRelatedField(
        many=True, queryset=Region.objects.all(), write_only=True, required=False
    )
    zones = serializers.PrimaryKeyRelatedField(
        many=True, queryset=Zone.objects.all(), write_only=True, required=False
    )
    territories = serializers.PrimaryKeyRelatedField(
        many=True, queryset=Territory.objects.all(), write_only=True, required=False
    )

    # HOD fields (profile-only)
    hod = serializers.PrimaryKeyRelatedField(
        queryset=SalesStaffProfile.objects.all(), write_only=True, required=False, allow_null=True
    )
    master_hod = serializers.PrimaryKeyRelatedField(
        queryset=SalesStaffProfile.objects.all(), write_only=True, required=False, allow_null=True
    )

    # Leave quotas (profile-only)
    sick_leave_quota = serializers.IntegerField(write_only=True, required=False, default=0)
    casual_leave_quota = serializers.IntegerField(write_only=True, required=False, default=0)
    others_leave_quota = serializers.IntegerField(write_only=True, required=False, default=0)

    class Meta:
        model = User
        fields = [
            'id', 'username', 'email', 'password', 'first_name', 'last_name',
            'profile_image', 'profile_image_url',  # Separate read/write fields
            'role', 'role_id', 'is_active', 'is_staff', 'is_sales_staff',
            'sales_profile',
            # Extra sales staff input fields (using plural names for M2M)
            'employee_code', 'phone_number', 'address', 'designation', 'date_of_joining',
            'companies', 'regions', 'zones', 'territories',  # For backward compatibility in write operations
            'hod', 'master_hod',
            'sick_leave_quota', 'casual_leave_quota', 'others_leave_quota'
        ]
        read_only_fields = ['id', 'is_staff', 'is_active', 'profile_image_url']
        extra_kwargs = {
            'username': {'required': False},
            'email': {'required': False},
            'first_name': {'required': False},
            'last_name': {'required': False},
        }
        
    def get_sales_profile(self, obj):
        profile = getattr(obj, 'sales_profile', None)
        if not profile:
            return None
        return SalesStaffProfileSerializer(profile).data
    
    def get_profile_image_url(self, obj):
        try:
            if obj.profile_image and hasattr(obj.profile_image, 'url'):
                return obj.profile_image.url
        except (ValueError, FileNotFoundError, OSError):
            pass
        return None
    
    def validate(self, attrs):
        if attrs.get('is_sales_staff'):
            required = ['employee_code', 'phone_number', 'address', 'designation']
            missing = [f for f in required if not attrs.get(f)]
            if missing:
                raise serializers.ValidationError({f: "This field is required for sales staff." for f in missing})
            
            # For M2M fields, check if they have at least one value
            m2m_required = ['companies', 'regions', 'zones', 'territories']
            for field in m2m_required:
                if field in attrs and not attrs[field]:
                    raise serializers.ValidationError({field: f"At least one {field[:-1]} is required for sales staff."})
                    
        return attrs

    def create(self, validated_data):
        sales_staff_flag = validated_data.pop('is_sales_staff', False)
        password = validated_data.pop('password', None)
        
        # Extract profile data
        profile_fields = [
            'employee_code', 'phone_number', 'address', 'designation',
            'companies', 'regions', 'zones', 'territories',
            'hod', 'master_hod',
            'sick_leave_quota', 'casual_leave_quota', 'others_leave_quota'
        ]
        
        profile_data = {f: validated_data.pop(f, None) for f in profile_fields if f in validated_data}

        # Create user
        user = User(**validated_data)
        if password:
            user.set_password(password)
        user.save()

        # Create sales profile if needed
        if sales_staff_flag:
            # Extract M2M data before creating the profile
            m2m_data = {}
            for field in ['companies', 'regions', 'zones', 'territories']:
                if field in profile_data:
                    m2m_data[field] = profile_data.pop(field)
            
            # Create profile without M2M fields first
            profile = SalesStaffProfile.objects.create(user=user, **profile_data)
            
            # Set M2M relationships
            for field, values in m2m_data.items():
                if values:
                    getattr(profile, field).set(values)
        
        return user

    def update(self, instance, validated_data):
        password = validated_data.pop('password', None)
        if password:
            instance.set_password(password)
            
        sales_staff_flag = validated_data.pop('is_sales_staff', instance.is_sales_staff)

        # Extract profile data
        profile_fields = [
            'employee_code', 'phone_number', 'address', 'designation',
            'companies', 'regions', 'zones', 'territories',
            'hod', 'master_hod',
            'sick_leave_quota', 'casual_leave_quota', 'others_leave_quota'
        ]
        
        profile_data = {f: validated_data.pop(f, None) for f in profile_fields if f in validated_data}

        # Update User fields
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        
        instance.is_sales_staff = sales_staff_flag
        instance.save()

        # Handle sales profile
        try:
            profile = instance.sales_profile
        except SalesStaffProfile.DoesNotExist:
            profile = None
            
        if sales_staff_flag:
            if not profile:
                # Create new profile if it doesn't exist
                profile = SalesStaffProfile.objects.create(user=instance)
            
            # Update profile fields
            for field in ['employee_code', 'phone_number', 'address', 'designation',
                         'hod', 'master_hod', 'sick_leave_quota', 
                         'casual_leave_quota', 'others_leave_quota']:
                if field in profile_data and profile_data[field] is not None:
                    setattr(profile, field, profile_data[field])
            
            # Update M2M fields
            for field in ['companies', 'regions', 'zones', 'territories']:
                if field in profile_data and profile_data[field] is not None:
                    getattr(profile, field).set(profile_data[field])
            
            profile.save()
        else:
            # If user is no longer sales staff, detach the profile
            if profile:
                profile.user = None
                profile.is_vacant = True
                profile.save()
        
        return instance
# ----------------------
# User (Non-admin) Profile Update
# ----------------------
class UserUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = [
            'email', 'username', 'first_name', 'last_name',
            'profile_image', 'role', 'is_active'
        ]
        extra_kwargs = {
            'email': {'required': False},
            'username': {'required': False},
            'first_name': {'required': False},
            'last_name': {'required': False},
            'profile_image': {'required': False},
            'role': {'required': False},
            'is_active': {'required': False},
        }

    def get_fields(self):
        fields = super().get_fields()
        request = self.context.get('request')

        # ❌ Important: Don’t hide fields from Swagger schema
        # Only set them as read-only at runtime if not admin
        if request and not (request.user.is_staff or request.user.is_superuser):
            for field in ['role', 'is_active']:
                fields[field].read_only = True
        return fields

    def validate(self, attrs):
        request = self.context.get('request')

        # Enforce at runtime
        if request and not (request.user.is_staff or request.user.is_superuser):
            for field in ['role', 'is_active', 'email', 'username']:
                attrs.pop(field, None)
        return attrs
    
# ----------------------
# permission serializer
class PermissionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Permission
        fields = ['id', 'name', 'codename', 'content_type']
        ref_name = 'PermissionSerializerForListing'  # ✅ Add this line
        