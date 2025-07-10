from rest_framework import generics, permissions
from rest_framework.permissions import AllowAny, IsAuthenticated
from django.contrib.auth import get_user_model 
from rest_framework_simplejwt.views import TokenObtainPairView
from .token_serializers import MyTokenObtainPairSerializer

from .models import Product, Order
from .permissions import IsAdmin, IsEditor, IsViewer  # ✅ Import custom permissions
from .serializers import (
    ProductSerializer,
    OrderSerializer,
    UserSignupSerializer,
    UserListSerializer,
  
)

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
    permission_classes = [IsAdmin]

# ✅ Product: List and Create
class ProductListCreateView(generics.ListCreateAPIView):
    queryset = Product.objects.all()
    serializer_class = ProductSerializer
    permission_classes = [IsEditor]  # 🔁 Changed from IsAuthenticated to IsEditor

# ✅ Order: List and Create
class OrderListCreateView(generics.ListCreateAPIView):
    queryset = Order.objects.all()
    serializer_class = OrderSerializer
    permission_classes = [IsViewer]  # 🔁 Changed from IsAuthenticated to IsViewer

    def perform_create(self, serializer):
         # Automatically assign current user to the order
        serializer.save(user=self.request.user)