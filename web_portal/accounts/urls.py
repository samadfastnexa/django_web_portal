from django.contrib import admin
from django.urls import path
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

urlpatterns = [
    # path('admin/', admin.site.urls),
    path('signup/', SignupView.as_view(), name='signup'),
    path('login/', TokenObtainPairView.as_view(), name='token_obtain_pair'),  # JWT login
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('users/', UserListAPIView.as_view(), name='user-list'),
     path('products/', ProductListCreateView.as_view(), name='product-list'),
    path('orders/', OrderListCreateView.as_view(), name='order-list'),
]
