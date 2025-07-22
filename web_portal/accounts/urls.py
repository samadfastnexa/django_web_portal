from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    SignupView,
    MyTokenObtainPairView,
    UserListAPIView,
    RoleViewSet,
)
from rest_framework_simplejwt.views import TokenRefreshView

router = DefaultRouter()
router.register(r'roles', RoleViewSet)

urlpatterns = [
    path('signup/', SignupView.as_view(), name='signup'),
    path('login/', MyTokenObtainPairView.as_view(), name='login'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('users/', UserListAPIView.as_view(), name='user-list'),
    path('', include(router.urls)),
]
