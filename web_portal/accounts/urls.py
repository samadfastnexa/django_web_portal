from django.contrib import admin
from django.urls import path,include
from .views import ProductViewSet 
from rest_framework.routers import DefaultRouter
from .views import (
    SignupView,
    MyTokenObtainPairView,
    UserListAPIView,
    ProductListCreateView,
    OrderListCreateView
)
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)
from .views import UserListAPIView
from .views import ProductListCreateView, OrderListCreateView
from .views import ComplaintListCreateView
router = DefaultRouter()
router.register(r'products', ProductViewSet)  # 👈 ViewSet registration
urlpatterns = [
    # path('admin/', admin.site.urls),
    path('signup/', SignupView.as_view(), name='signup'),
    path('login/', TokenObtainPairView.as_view(), name='token_obtain_pair'),  # JWT login
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('users/', UserListAPIView.as_view(), name='user-list'),
     path('products/', ProductListCreateView.as_view(), name='product-list'),
    path('orders/', OrderListCreateView.as_view(), name='order-list'),
    path('', include(router.urls)),  # 👈 include ViewSet routes
     path('api/complaints/', ComplaintListCreateView.as_view(), name='complaint-list-create'),
]
