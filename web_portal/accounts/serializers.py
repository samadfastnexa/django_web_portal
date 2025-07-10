from rest_framework import serializers
from django.contrib.auth import get_user_model

from .models import Product, Order  # ✅ import your models

User = get_user_model()

# ✅ Signup Serializer
class UserSignupSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = ['username', 'email', 'password', 'role']  # 👈 include 'role'

    def create(self, validated_data):
        user = User.objects.create_user(
            username=validated_data['username'],
            email=validated_data.get('email', ''),
            password=validated_data['password'],
            role=validated_data.get('role', 'viewer')  # 👈 default if not passed
        )
        return user

# ✅ User List Serializer
class UserListSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'email']

# ✅ Product Serializer
class ProductSerializer(serializers.ModelSerializer):
    class Meta:
        model = Product
        fields = '__all__'

# ✅ Order Serializer
class OrderSerializer(serializers.ModelSerializer):
    user = serializers.ReadOnlyField(source='user.email')  # Optional: show user's email in response

    class Meta:
        model = Order
        fields = '__all__'