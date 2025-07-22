from rest_framework import generics, permissions
from .models import Attendance
from .serializers import AttendanceSerializer
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.response import Response

# List all or create new attendance
class AttendanceListCreateView(generics.ListCreateAPIView):
    queryset = Attendance.objects.all()
    serializer_class = AttendanceSerializer
    permission_classes = [permissions.IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def perform_create(self, serializer):
        serializer.save()

# Retrieve, update, or delete a single attendance record
class AttendanceDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Attendance.objects.all()
    serializer_class = AttendanceSerializer
    permission_classes = [permissions.IsAuthenticated]
