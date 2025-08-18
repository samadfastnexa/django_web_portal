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
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name', 'profile_image']

# ----------------------
# User Signup (Public Registration)
# ----------------------
class SalesStaffSerializer(serializers.ModelSerializer):
    class Meta:
        model = SalesStaffProfile
        fields = [
            'id', 'user', 'employee_code', 'phone_number',
            'address', 'designation', 'region', 'zone', 'territory',
            'hod', 'master_hod'
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
    profile_image = serializers.ImageField(required=True)
    is_sales_staff = serializers.BooleanField(required=False)

    # Sales staff fields (optional, allow blank/null)
    employee_code = serializers.CharField(write_only=True, required=False, allow_blank=True)
    phone_number = serializers.CharField(write_only=True, required=False, allow_blank=True)
    address = serializers.CharField(write_only=True, required=False, allow_blank=True)
    designation = serializers.CharField(write_only=True, required=False, allow_blank=True)
    region = serializers.PrimaryKeyRelatedField(
        queryset=Region.objects.all(), write_only=True, required=False, allow_null=True
    )
    zone = serializers.PrimaryKeyRelatedField(
        queryset=Zone.objects.all(), write_only=True, required=False, allow_null=True
    )
    territory = serializers.PrimaryKeyRelatedField(
        queryset=Territory.objects.all(), write_only=True, required=False, allow_null=True
    )

    class Meta:
        model = User
        fields = [
            'id', 'username', 'email', 'password',
            'first_name', 'last_name', 'profile_image',
            'role', 'is_active', 'is_staff',
            'is_sales_staff',
            'employee_code', 'phone_number', 'address', 'designation',
            'region', 'zone', 'territory',
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
            required_fields = ['employee_code', 'phone_number', 'address', 'designation', 'region', 'zone', 'territory']
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

        sales_staff_data = {}
        if is_sales:
            sales_staff_fields = ['employee_code', 'phone_number', 'address', 'designation', 'region', 'zone', 'territory']
            for field in sales_staff_fields:
                sales_staff_data[field] = validated_data.pop(field)

        password = validated_data.pop('password')
        user = User(**validated_data)
        user.set_password(password)
        user.is_sales_staff = is_sales
        user.save()

        if is_sales:
            SalesStaffProfile.objects.create(user=user, **sales_staff_data)

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


class SalesStaffProfileSerializer(serializers.ModelSerializer):
    company = CompanySerializer(read_only=True)
    region = RegionSerializer(read_only=True)
    zone = ZoneSerializer(read_only=True)
    territory = TerritorySerializer(read_only=True)

    class Meta:
        model = SalesStaffProfile
        fields = [
            'employee_code',
            'phone_number',
            'address',
            'designation',
            'company',
            'region',
            'zone',
            'territory',
            'sick_leave_quota',
            'casual_leave_quota',
            'others_leave_quota'
        ]
# ----------------------
# Admin: Full User View/Update (password is optional)
# ----------------------
class UserSerializer(serializers.ModelSerializer):
    # password = serializers.CharField(write_only=True, min_length=6, required=False)
    # is_sales_staff = serializers.BooleanField(write_only=True, required=False)
    # sales_staff_profile = SalesStaffProfileSerializer(write_only=True, required=False)

    # class Meta:
    #     model = User
    #     fields = [
    #         'id', 'username', 'email', 'password', 'first_name', 'last_name',
    #         'profile_image', 'role', 'is_active', 'is_staff',
    #         'is_sales_staff', 'sales_staff_profile'
    #     ]
    #     read_only_fields = ['id', 'is_staff', 'is_active']

    # def create(self, validated_data):
    #     sales_staff_flag = validated_data.pop('is_sales_staff', False)
    #     sales_staff_data = validated_data.pop('sales_staff_profile', None)

    #     password = validated_data.pop('password', None)
    #     user = User(**validated_data)

    #     if password:
    #         user.set_password(password)
    #     user.save()

    #     if sales_staff_flag:
    #         if not sales_staff_data:
    #             raise serializers.ValidationError("Sales staff details are required when is_sales_staff is true.")
    #         SalesStaffProfile.objects.create(user=user, **sales_staff_data)

    #     return user
    
    # latest is below
    # password = serializers.CharField(write_only=True, min_length=6, required=False)
    # is_sales_staff = serializers.BooleanField(write_only=True, required=False)

    # # Nested sales profile
    # sales_profile = SalesStaffProfileSerializer(read_only=True)

    # # Input fields for creating profile
    # employee_code = serializers.CharField(write_only=True, required=False)
    # designation = serializers.CharField(write_only=True, required=False)
    # region = serializers.PrimaryKeyRelatedField(queryset=Region.objects.all(), write_only=True, required=False)
    # zone = serializers.PrimaryKeyRelatedField(queryset=Zone.objects.all(), write_only=True, required=False)
    # territory = serializers.PrimaryKeyRelatedField(queryset=Territory.objects.all(), write_only=True, required=False)
    # sick_leave_quota = serializers.IntegerField(write_only=True, required=False, default=0)
    # casual_leave_quota = serializers.IntegerField(write_only=True, required=False, default=0)

    # class Meta:
    #     model = User
    #     fields = [
    #         'id', 'username', 'email', 'password', 'first_name', 'last_name',
    #         'role', 'is_active', 'is_staff', 'is_sales_staff',
    #         'sales_profile',
    #         # write-only input fields
    #         'employee_code', 'designation', 'region', 'zone', 'territory',
    #         'sick_leave_quota', 'casual_leave_quota'
    #     ]
    #     read_only_fields = ['id', 'is_staff', 'is_active']

    # def create(self, validated_data):
    #     sales_staff_flag = validated_data.pop('is_sales_staff', False)
    #     password = validated_data.pop('password', None)

    #     # Extract profile fields
    #     profile_data = {
    #         'employee_code': validated_data.pop('employee_code', None),
    #         'designation': validated_data.pop('designation', None),
    #         'region': validated_data.pop('region', None),
    #         'zone': validated_data.pop('zone', None),
    #         'territory': validated_data.pop('territory', None),
    #         'sick_leave_quota': validated_data.pop('sick_leave_quota', 0),
    #         'casual_leave_quota': validated_data.pop('casual_leave_quota', 0)
    #     }

    #     # Create user
    #     user = User(**validated_data)
    #     if password:
    #         user.set_password(password)
    #     user.save()

    #     # Create sales staff profile if flagged
    #     if sales_staff_flag:
    #         SalesStaffProfile.objects.create(user=user, **profile_data)

    #     return user
    sales_profile = SalesStaffProfileSerializer(read_only=True)
    password = serializers.CharField(write_only=True, min_length=6)
    is_sales_staff = serializers.BooleanField(write_only=True, default=False)

    # Write-only fields for creating SalesStaffProfile
    employee_code = serializers.CharField(write_only=True, required=False)
    phone_number = serializers.CharField(write_only=True, required=False)
    address = serializers.CharField(write_only=True, required=False)
    designation = serializers.CharField(write_only=True, required=False)
    company = serializers.PrimaryKeyRelatedField(queryset=Company.objects.all(), write_only=True, required=False)
    region = serializers.PrimaryKeyRelatedField(queryset=Region.objects.all(), write_only=True, required=False)
    zone = serializers.PrimaryKeyRelatedField(queryset=Zone.objects.all(), write_only=True, required=False)
    territory = serializers.PrimaryKeyRelatedField(queryset=Territory.objects.all(), write_only=True, required=False)
    sick_leave_quota = serializers.IntegerField(write_only=True, required=False, default=0)
    casual_leave_quota = serializers.IntegerField(write_only=True, required=False, default=0)
    others_leave_quota = serializers.IntegerField(write_only=True, required=False, default=0)

    class Meta:
        model = User
        fields = [
            'id', 'username', 'email', 'password', 'first_name', 'last_name',
            'role', 'is_active', 'is_staff', 'is_sales_staff',
            'sales_profile',
            'employee_code','phone_number','address','designation',
            'company','region','zone','territory',
            'sick_leave_quota','casual_leave_quota','others_leave_quota'
        ]
        read_only_fields = ['id','is_staff','is_active']

    def validate(self, attrs):
        # Ensure required fields for sales staff
        if attrs.get('is_sales_staff'):
            required_fields = ['employee_code','phone_number','address','designation','company','region','zone','territory']
            missing = [f for f in required_fields if not attrs.get(f)]
            if missing:
                raise serializers.ValidationError({f: "This field is required for sales staff." for f in missing})
        return attrs

    def create(self, validated_data):
        sales_staff_flag = validated_data.pop('is_sales_staff', False)
        password = validated_data.pop('password')

        # Extract profile fields
        profile_data = {k: validated_data.pop(k, None) for k in [
            'employee_code','phone_number','address','designation',
            'company','region','zone','territory',
            'sick_leave_quota','casual_leave_quota','others_leave_quota'
        ]}

        user = User(**validated_data)
        user.set_password(password)
        user.save()

        # Create SalesStaffProfile if flagged
        if sales_staff_flag:
            SalesStaffProfile.objects.create(user=user, **profile_data)

        return user

    def update(self, instance, validated_data):
        # Update basic user fields
        password = validated_data.pop('password', None)
        if password:
            instance.set_password(password)
        for attr, value in validated_data.items():
            if attr not in ['employee_code','phone_number','address','designation','company','region','zone','territory','sick_leave_quota','casual_leave_quota','others_leave_quota','is_sales_staff']:
                setattr(instance, attr, value)
        instance.save()

        # Update or create sales profile if flagged
        if validated_data.get('is_sales_staff', False):
            profile_data = {k: validated_data[k] for k in [
                'employee_code','phone_number','address','designation',
                'company','region','zone','territory',
                'sick_leave_quota','casual_leave_quota','others_leave_quota'
            ] if k in validated_data}
            profile, created = SalesStaffProfile.objects.get_or_create(user=instance)
            for key, value in profile_data.items():
                setattr(profile, key, value)
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
        # ✅ Allow PATCH requests with only partial fields
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
        """
        Dynamically set certain fields as read-only for non-staff users.
        """
        fields = super().get_fields()
        request = self.context.get('request')
        if request and not request.user.is_staff:
            for field in ['email', 'username', 'role', 'is_active']:
                fields[field].read_only = True
        return fields

    def validate(self, attrs):
        """
        Ensure non-staff users cannot submit restricted fields even via tools like Postman.
        """
        request = self.context.get('request')
        if request and not request.user.is_staff:
            for field in ['email', 'username', 'role', 'is_active']:
                attrs.pop(field, None)
        return attrs
    
# ----------------------
# permission serializer
class PermissionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Permission
        fields = ['id', 'name', 'codename', 'content_type']
        ref_name = 'PermissionSerializerForListing'  # ✅ Add this line
        