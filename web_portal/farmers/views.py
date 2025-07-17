from rest_framework import generics
from .models import Farmer
from .serializers import FarmerSerializer

# ✅ List and Create Farmers
class FarmerListCreateView(generics.ListCreateAPIView):
    queryset = Farmer.objects.all()
    serializer_class = FarmerSerializer

# ✅ Retrieve, Update, and Delete a Single Farmer
class FarmerDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Farmer.objects.all()
    serializer_class = FarmerSerializer