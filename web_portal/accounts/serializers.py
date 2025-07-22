from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.core.validators import RegexValidator
from .models import Role

User = get_user_model()

# ✅ User List Serializer
class UserListSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name', 'profile_image']

# ✅ Signup Serializer with validation
class UserSignupSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=6)

    first_name = serializers.CharField(
        required=False,
        allow_blank=True,
        validators=[RegexValidator(r'^[A-Za-z\s]+$', 'Only letters and spaces are allowed.')]
    )

    last_name = serializers.CharField(
        required=False,
        allow_blank=True,
        validators=[RegexValidator(r'^[A-Za-z\s]+$', 'Only letters and spaces are allowed.')]
    )

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
            role=validated_data.get('role'),
            first_name=validated_data.get('first_name', ''),
            last_name=validated_data.get('last_name', ''),
            profile_image=validated_data.get('profile_image', None)
        )

# ✅ Role & Permission Serializers (if you still use them)
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

# # ✅ Product Serializer
# class ProductSerializer(serializers.ModelSerializer):
#     class Meta:
#         model = Product
#         fields = '__all__'

# # ✅ Order Serializer
# class OrderSerializer(serializers.ModelSerializer):
#     user = serializers.ReadOnlyField(source='user.email')  # Optional: show user's email in response

    # class Meta:
    #     model = Order
    #     fields = '__all__'