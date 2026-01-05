# from django.urls import path, include

# from rest_framework.routers import DefaultRouter
# from .views import (
#     SignupView,
#     MyTokenObtainPairView,
#     UserListAPIView,
#     RoleViewSet,
#     AdminUserStatusUpdateView,
#     UserCreateAPIView,
#     # UserViewSet,
#     PermissionListAPIView

# )
# from .UserViewSet import UserViewSet
# from rest_framework_simplejwt.views import TokenRefreshView


# router = DefaultRouter()
# router.register(r'roles', RoleViewSet)
# router.register('users', UserViewSet, basename='users')
# urlpatterns = [
#     path('signup/', SignupView.as_view(), name='signup'),
#     path('login/', MyTokenObtainPairView.as_view(), name='login'),
#     path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
#     # path('users/', UserListAPIView.as_view(), name='user-list'),
#     path('users/list/', UserListAPIView.as_view(), name='user-list'),  # ✅ add back
#     # path('user/add/', UserCreateAPIView.as_view(), name='user-create'),
#     path('', include(router.urls)),
#     path('admin/users/<int:pk>/status/', AdminUserStatusUpdateView.as_view(), name='admin-user-status'),
#     path('permissions/', PermissionListAPIView.as_view(), name='permission-list'),
    
# ]

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenRefreshView

from .views import (
    SignupView,
    MyTokenObtainPairView,
    RoleViewSet,
    AdminUserStatusUpdateView,
    PermissionListAPIView,
    user_territories_emp_api,
)
from .UserViewSet import UserViewSet

# ✅ Router for ViewSets
router = DefaultRouter()
router.register(r'roles', RoleViewSet)
router.register(r'users', UserViewSet, basename='users')

urlpatterns = [
    # ----------------------
    # Authentication
    # ----------------------
    path('signup/', SignupView.as_view(), name='signup'),
    path('login/', MyTokenObtainPairView.as_view(), name='login'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),

    # ----------------------
    # Admin-only controls
    # ----------------------
    path(
        'admin/users/<int:pk>/status/',
        AdminUserStatusUpdateView.as_view(),
        name='admin-user-status'
    ),

    # ----------------------
    # Permission management
    # ----------------------
    path('permissions/', PermissionListAPIView.as_view(), name='permission-list'),

    # ----------------------
    # Sales staff helpers
    # ----------------------
    path(
        'users/<int:user_id>/territories-emp/',
        user_territories_emp_api,
        name='user-territories-emp',
    ),

    # ----------------------
    # Include all router ViewSets (Users, Roles)
    # ----------------------
    path('', include(router.urls)),
]
