from rest_framework import generics, permissions, filters
from .models import Complaint
from .serializers import ComplaintSerializer
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.pagination import PageNumberPagination

import uuid
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from drf_yasg.openapi import TYPE_STRING, TYPE_FILE, Schema

# ✅ Pagination class
class ComplaintPagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = 'page_size'
    max_page_size = 100


# ✅ Complaint List and Create API
class ComplaintListCreateView(generics.ListCreateAPIView):
    queryset = Complaint.objects.all().order_by('-created_at')
    serializer_class = ComplaintSerializer
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['status']
    ordering_fields = ['created_at']
    pagination_class = ComplaintPagination  # ✅ Enable pagination

    def get_permissions(self):
        if self.request.method == 'POST':
            return [permissions.IsAuthenticated()]
        return [permissions.IsAdminUser()]

    @swagger_auto_schema(
        operation_description="List all complaints (admin only). Supports filtering, ordering, and pagination.",
        manual_parameters=[
            openapi.Parameter(
                'status', openapi.IN_QUERY, description="Filter by complaint status",
                type=openapi.TYPE_STRING
            ),
            openapi.Parameter(
                'ordering', openapi.IN_QUERY, description="Order by created_at (e.g. ?ordering=created_at or -created_at)",
                type=openapi.TYPE_STRING
            ),
            openapi.Parameter(
                'page', openapi.IN_QUERY, description="Page number",
                type=openapi.TYPE_INTEGER
            ),
            openapi.Parameter(
                'page_size', openapi.IN_QUERY, description="Number of results per page",
                type=openapi.TYPE_INTEGER
            ),
        ],
        responses={200: ComplaintSerializer(many=True)},
        tags=["Complaints"]
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    @swagger_auto_schema(
    operation_description="Create a new complaint (authenticated users only).",
    manual_parameters=[],
    request_body=openapi.Schema(
        type=openapi.TYPE_OBJECT,
        required=['message'],
        properties={
            'message': openapi.Schema(type=TYPE_STRING, description='Complaint message'),
            'image': openapi.Schema(type=TYPE_FILE, description='Optional image upload'),
        },
    ),
    responses={201: ComplaintSerializer},
    tags=["Complaints"]
)
    def post(self, request, *args, **kwargs):
        return super().post(request, *args, **kwargs)

    def perform_create(self, serializer):
        complaint_id = f"FB{uuid.uuid4().hex[:8].upper()}"
        serializer.save(user=self.request.user, complaint_id=complaint_id)
