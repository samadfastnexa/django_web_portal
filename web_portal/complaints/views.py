from rest_framework import generics, permissions, filters
from .models import Complaint
from .serializers import ComplaintSerializer
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.pagination import PageNumberPagination
import uuid

class ComplaintListCreateView(generics.ListCreateAPIView):
    queryset = Complaint.objects.all().order_by('-created_at')
    serializer_class = ComplaintSerializer
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['status']
    ordering_fields = ['created_at']

    def get_permissions(self):
        if self.request.method == 'POST':
            return [permissions.IsAuthenticated()]
        return [permissions.IsAdminUser()]

    def perform_create(self, serializer):
        complaint_id = f"FB{uuid.uuid4().hex[:8].upper()}"
        serializer.save(user=self.request.user, complaint_id=complaint_id)