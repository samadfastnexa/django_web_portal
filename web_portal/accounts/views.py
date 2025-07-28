from rest_framework import generics, permissions, viewsets
from rest_framework.permissions import AllowAny, IsAuthenticated, BasePermission
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework.parsers import MultiPartParser, FormParser
from django.contrib.auth import get_user_model
from .serializers import AdminUserStatusSerializer

from .models import Role
from .serializers import (
    UserSignupSerializer,
    UserListSerializer,
    RoleSerializer
)
from .token_serializers import MyTokenObtainPairSerializer

User = get_user_model()

# ✅ Permission: Dynamic role-based permission check
class HasRolePermission(BasePermission):
    def has_permission(self, request, view):
        user = request.user
        if not user or not user.is_authenticated or not user.role:
            return False

        required_codename = getattr(view, 'required_permission', None)
        if required_codename:
            return user.role.permissions.filter(codename=required_codename).exists()
        return True  # Allow if no permission required


# ✅ Signup View — open to anyone
class SignupView(generics.CreateAPIView):
    queryset = User.objects.all()
    serializer_class = UserSignupSerializer
    permission_classes = [AllowAny]
    parser_classes = [MultiPartParser, FormParser]  # Support file/image upload


# ✅ JWT Login View
class MyTokenObtainPairView(TokenObtainPairView):
    serializer_class = MyTokenObtainPairSerializer


# ✅ List Users — requires "view_user" permission
class UserListAPIView(generics.ListAPIView):
    queryset = User.objects.all()
    serializer_class = UserListSerializer
    permission_classes = [IsAuthenticated, HasRolePermission]
    required_permission = 'view_user'  # Codename from Django permission


# ✅ Role CRUD (Create, Update, Delete) — requires "change_role"
class RoleViewSet(viewsets.ModelViewSet):
    queryset = Role.objects.all()
    serializer_class = RoleSerializer
    permission_classes = [IsAuthenticated, HasRolePermission]
    required_permission = 'change_role'  # You can customize per-action
User = get_user_model()

class AdminUserStatusUpdateView(generics.UpdateAPIView):
    queryset = User.objects.all()
    serializer_class = AdminUserStatusSerializer
    permission_classes = [permissions.IsAdminUser]  # Only admin users can access
    http_method_names = ['patch']  # 👈 Only allow PATCH