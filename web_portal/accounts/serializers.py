from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.core.validators import RegexValidator
from .models import Role

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
class UserSignupSerializer(serializers.ModelSerializer):
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

    class Meta:
        model = User
        fields = [
            'username', 'email', 'password', 'role',
            'first_name', 'last_name', 'profile_image'
        ]

    def validate_email(self, value):
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError("A user with this email already exists.")
        return value

    def validate_username(self, value):
        if User.objects.filter(username=value).exists():
            raise serializers.ValidationError("This username is already taken.")
        return value

    def create(self, validated_data):
        # Role can be None – should be handled in the model manager
        return User.objects.create_user(
            username=validated_data['username'],
            email=validated_data['email'],
            password=validated_data['password'],
            role=validated_data.get('role'),
            first_name=validated_data['first_name'],
            last_name=validated_data['last_name'],
            profile_image=validated_data['profile_image'],
            is_active=False,
            is_staff=False
        )

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

# ----------------------
# Admin: Change User Status
# ----------------------
class AdminUserStatusSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['is_active']

# ----------------------
# Admin: Full User View/Update (password is optional)
# ----------------------
class UserSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=6, required=False)

    class Meta:
        model = User
        fields = [
            'id', 'username', 'email', 'password', 'first_name', 'last_name',
            'profile_image', 'role', 'is_active', 'is_staff'
        ]
        read_only_fields = ['email', 'username', 'is_staff', 'is_active']  # Optional: remove is_active if needed

    def update(self, instance, validated_data):
        password = validated_data.pop('password', None)
        if password:
            instance.set_password(password)
        return super().update(instance, validated_data)

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
        