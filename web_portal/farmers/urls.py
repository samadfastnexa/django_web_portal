from django.urls import path
from .views import FarmerListCreateView, FarmerDetailView

urlpatterns = [
    path('', FarmerListCreateView.as_view(), name='farmer-list'),
    path('farmers/<int:pk>/', FarmerDetailView.as_view(), name='farmer-detail'),
]