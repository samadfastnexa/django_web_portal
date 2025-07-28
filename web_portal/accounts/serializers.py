from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.core.validators import RegexValidator
from .models import Role

User = get_user_model()

class UserListSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name', 'profile_image']

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
        return User.objects.create_user(
            username=validated_data['username'],
            email=validated_data['email'],
            password=validated_data['password'],
            role=validated_data.get('role'),  # will be set to FirstRole in manager if not provided
            first_name=validated_data['first_name'],
            last_name=validated_data['last_name'],
            profile_image=validated_data['profile_image'],
            is_active=False,
            is_staff=False
        )

class PermissionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Permission
        fields = ['id', 'codename', 'name']

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

User = get_user_model()

class AdminUserStatusSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['is_active']
class UserSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=6, required=False)

    class Meta:
        model = User
        fields = [
            'id', 'username', 'email', 'password', 'first_name', 'last_name',
            'profile_image', 'role', 'is_active', 'is_staff'
        ]
        read_only_fields = ['email', 'username', 'is_staff', 'is_active']

    def update(self, instance, validated_data):
        password = validated_data.pop('password', None)
        if password:
            instance.set_password(password)
        return super().update(instance, validated_data)