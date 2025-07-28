from rest_framework import generics, permissions, viewsets
from rest_framework.permissions import AllowAny, IsAuthenticated, BasePermission
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework.parsers import MultiPartParser, FormParser
from django.contrib.auth import get_user_model
from .serializers import AdminUserStatusSerializer
from drf_yasg.utils import swagger_auto_schema
from .models import Role
from .serializers import (
    UserSignupSerializer,
    UserListSerializer,
    RoleSerializer,
    UserSerializer,
    AdminUserStatusSerializer
)
from .token_serializers import MyTokenObtainPairSerializer
from .serializers import UserSignupSerializer  # use your custom user creation serializer
from .permissions import IsOwnerOrAdmin  # we'll define this below

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


class UserCreateAPIView(generics.CreateAPIView):
    serializer_class = UserSignupSerializer
    parser_classes = [MultiPartParser, FormParser]  # 👈 Important

    @swagger_auto_schema(
        operation_description="user CRUD",
        request_body=UserSignupSerializer,
        tags=["User CRUD"]
    )
    def post(self, request, *args, **kwargs):
        return self.create(request, *args, **kwargs)

class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated, IsOwnerOrAdmin]
    http_method_names = ['get', 'put', 'patch', 'delete']

    def get_queryset(self):
        user = self.request.user
        if user.is_superuser or user.is_staff:
            return User.objects.all()
        return User.objects.filter(id=user.id)

    def perform_destroy(self, instance):
        if instance != self.request.user and not self.request.user.is_superuser:
            raise PermissionDenied("You can only delete your own account.")
        instance.delete()

    # ✅ Swagger docs customization
    @swagger_auto_schema(tags=["User CRUD"])
    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)

    @swagger_auto_schema(tags=["User CRUD"])
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @swagger_auto_schema(tags=["User CRUD"])
    def update(self, request, *args, **kwargs):
        return super().update(request, *args, **kwargs)

    @swagger_auto_schema(tags=["User CRUD"])
    def partial_update(self, request, *args, **kwargs):
        return super().partial_update(request, *args, **kwargs)

    @swagger_auto_schema(tags=["User CRUD"])
    def destroy(self, request, *args, **kwargs):
        return super().destroy(request, *args, **kwargs)