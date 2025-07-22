from rest_framework import generics, permissions, viewsets
from rest_framework.permissions import AllowAny, IsAdminUser, BasePermission,IsAuthenticated
from rest_framework_simplejwt.views import TokenObtainPairView
from django.contrib.auth import get_user_model

from .models import Role
from .serializers import (
    UserSignupSerializer,
    UserListSerializer,
    RoleSerializer
)
from .permissions import IsAdmin, IsEditor, IsViewer  # ✅ Custom permissions
from .token_serializers import MyTokenObtainPairSerializer

User = get_user_model()

# ✅ Signup View
class SignupView(generics.CreateAPIView):
    queryset = User.objects.all()
    permission_classes = [AllowAny]
    serializer_class = UserSignupSerializer

# ✅ Custom Token View (Login)
class MyTokenObtainPairView(TokenObtainPairView):
    serializer_class = MyTokenObtainPairSerializer

# ✅ List all users (admin use only)
class UserListAPIView(generics.ListAPIView):
    queryset = User.objects.all()
    serializer_class = UserListSerializer
    # permission_classes = [IsAdmin]
    permission_classes = [IsAuthenticated] 

# ✅ Role ViewSet
class RoleViewSet(viewsets.ModelViewSet):
    queryset = Role.objects.all()
    serializer_class = RoleSerializer
    permission_classes = [IsAdminUser]

# ✅ Permission Based on Role Permissions
class HasRolePermission(BasePermission):
    def has_permission(self, request, view):
        user = request.user
        if user and user.is_authenticated and user.role:
            required_codename = getattr(view, 'required_permission', None)
            return user.role.permissions.filter(codename=required_codename).exists()
        return False
