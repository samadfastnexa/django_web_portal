from django.urls import path, include

from rest_framework.routers import DefaultRouter
from .views import (
    SignupView,
    MyTokenObtainPairView,
    UserListAPIView,
    RoleViewSet,
    AdminUserStatusUpdateView,
    UserCreateAPIView,
    # UserViewSet,
    PermissionListAPIView

)
from .UserViewSet import UserViewSet
from rest_framework_simplejwt.views import TokenRefreshView


router = DefaultRouter()
router.register(r'roles', RoleViewSet)
router.register('users', UserViewSet, basename='users')
urlpatterns = [
    path('signup/', SignupView.as_view(), name='signup'),
    path('login/', MyTokenObtainPairView.as_view(), name='login'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    # path('users/', UserListAPIView.as_view(), name='user-list'),
    # path('user/add/', UserCreateAPIView.as_view(), name='user-create'),
    path('', include(router.urls)),
    path('admin/users/<int:pk>/status/', AdminUserStatusUpdateView.as_view(), name='admin-user-status'),
    path('permissions/', PermissionListAPIView.as_view(), name='permission-list'),
    
]
