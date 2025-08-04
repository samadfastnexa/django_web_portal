from rest_framework import generics, permissions, viewsets, status
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.response import Response
from rest_framework.exceptions import PermissionDenied
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from rest_framework.decorators import action
from .models import Attendance, AttendanceRequest
from .serializers import AttendanceSerializer, AttendanceRequestSerializer
from rest_framework.permissions import IsAuthenticated


# ✅ List & Create Attendance (Only for logged-in user)
class AttendanceListCreateView(generics.ListCreateAPIView):
    serializer_class = AttendanceSerializer
    permission_classes = [permissions.IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    @swagger_auto_schema(
        operation_description="Get a list of your attendance records.",
        tags=["Attendance"]
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_description="Submit a new attendance record.",
        tags=["Attendance"]
    )
    def post(self, request, *args, **kwargs):
        return super().post(request, *args, **kwargs)

    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):
            return Attendance.objects.none()
        return Attendance.objects.filter(user_id=self.request.user)

    def perform_create(self, serializer):
        # serializer.save(user_id=self.request.user)
          serializer.save(user=self.request.user)


# ✅ Retrieve, Update, Delete Attendance (Only for logged-in user)
class AttendanceDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = AttendanceSerializer
    permission_classes = [permissions.IsAuthenticated]

    @swagger_auto_schema(
        operation_description="Retrieve a specific attendance record.",
        tags=["Attendance"]
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_description="Update an existing attendance record.",
        tags=["Attendance"]
    )
    def put(self, request, *args, **kwargs):
        return super().put(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_description="Partially update an attendance record.",
        tags=["Attendance"]
    )
    def patch(self, request, *args, **kwargs):
        return super().patch(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_description="Delete an attendance record.",
        tags=["Attendance"]
    )
    def delete(self, request, *args, **kwargs):
        return super().delete(request, *args, **kwargs)

    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):
            return Attendance.objects.none()
        return Attendance.objects.filter(user_id=self.request.user)


# ✅ AttendanceRequest ViewSet (For requests with permission-protected status changes)
class AttendanceRequestViewSet(viewsets.ModelViewSet):
    serializer_class = AttendanceRequestSerializer
    permission_classes = [permissions.IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):
            return AttendanceRequest.objects.none()

        user = self.request.user
        if self._has_approval_permission(user):
            return AttendanceRequest.objects.all()
        return AttendanceRequest.objects.filter(user=user)

    @swagger_auto_schema(
        operation_description="List all your attendance requests.",
        tags=["Attendance Request"]
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_description="Submit a new attendance request.",
        tags=["Attendance Request"]
    )
    def create(self, request, *args, **kwargs):
        return super().create(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_description="Retrieve a specific attendance request.",
        tags=["Attendance Request"]
    )
    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_description="Update an attendance request (status requires permission).",
        tags=["Attendance Request"]
    )
    def update(self, request, *args, **kwargs):
        self._check_status_change_permission(request)
        return super().update(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_description="Partially update an attendance request (status requires permission).",
        tags=["Attendance Request"]
    )
    def partial_update(self, request, *args, **kwargs):
        self._check_status_change_permission(request)
        return super().partial_update(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_description="Delete an attendance request.",
        tags=["Attendance Request"]
    )
    def destroy(self, request, *args, **kwargs):
        return super().destroy(request, *args, **kwargs)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    def _check_status_change_permission(self, request):
        instance = self.get_object()
        incoming_status = request.data.get("status")
        current_status = instance.status

        if incoming_status and incoming_status != current_status:
            if not self._has_approval_permission(request.user):
                raise PermissionDenied("You do not have permission to change the status.")

    def _has_approval_permission(self, user):
        if not user or not hasattr(user, 'role'):
            return False
        return (
            user.is_superuser or (
                user.role and
                user.role.permissions.filter(codename="approve_attendance_request").exists()
            )
        )
    @action(detail=True, methods=['post'], url_path='approve', permission_classes=[permissions.IsAdminUser])
    @swagger_auto_schema(operation_description="Approve attendance request and create attendance", tags=["Attendance Request"])
    def approve(self, request, pk=None):
        instance = self.get_object()

        if instance.status == "approved":
            return Response({"detail": "Already approved."}, status=status.HTTP_400_BAD_REQUEST)

        # ✅ Change status to approved
        instance.status = "approved"
        instance.save()

        # ✅ Create corresponding attendance entry
        Attendance.objects.create(
            # user_id=instance.user,
            user=instance.user,  
            attendee_id=instance.attendee,
            check_in_time=instance.check_in_time,
            check_out_time=instance.check_out_time,
            source="request"
        )

        return Response({"detail": "Request approved and attendance created."}, status=status.HTTP_200_OK)

class AttendanceRequestCreateAPIView(generics.CreateAPIView):
    queryset = AttendanceRequest.objects.all()
    serializer_class = AttendanceRequestSerializer
    permission_classes = [IsAuthenticated]