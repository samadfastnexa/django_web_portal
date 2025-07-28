from rest_framework import generics
from .models import Farmer
from .serializers import FarmerSerializer

from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

# ✅ List and Create Farmers
class FarmerListCreateView(generics.ListCreateAPIView):
    queryset = Farmer.objects.all()
    serializer_class = FarmerSerializer

    @swagger_auto_schema(
        operation_description="Retrieve the list of all farmers.",
        tags=["Farmers"]
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_description="Create a new farmer.",
        tags=["Farmers"]
    )
    def post(self, request, *args, **kwargs):
        return super().post(request, *args, **kwargs)

# ✅ Retrieve, Update, and Delete a Single Farmer
class FarmerDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Farmer.objects.all()
    serializer_class = FarmerSerializer

    @swagger_auto_schema(
        operation_description="Get details of a specific farmer by ID.",
        tags=["Farmers"]
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_description="Update a specific farmer by ID.",
        tags=["Farmers"]
    )
    def put(self, request, *args, **kwargs):
        return super().put(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_description="Partially update a specific farmer by ID.",
        tags=["Farmers"]
    )
    def patch(self, request, *args, **kwargs):
        return super().patch(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_description="Delete a specific farmer by ID.",
        tags=["Farmers"]
    )
    def delete(self, request, *args, **kwargs):
        return super().delete(request, *args, **kwargs)
