from rest_framework import viewsets,permissions
from .models import Dealer, MeetingSchedule, SalesOrder
from .serializers import DealerSerializer, MeetingScheduleSerializer, SalesOrderSerializer
from .models import DealerRequest
from .serializers import DealerRequestSerializer
from drf_yasg.utils import swagger_auto_schema
from rest_framework.response import Response
from django.utils import timezone

class DealerViewSet(viewsets.ModelViewSet):
    queryset = Dealer.objects.all()
    serializer_class = DealerSerializer

class MeetingScheduleViewSet(viewsets.ModelViewSet):
    queryset = MeetingSchedule.objects.all()
    serializer_class = MeetingScheduleSerializer

class SalesOrderViewSet(viewsets.ModelViewSet):
    queryset = SalesOrder.objects.all()
    serializer_class = SalesOrderSerializer


class DealerRequestViewSet(viewsets.ModelViewSet):
    queryset = DealerRequest.objects.all()
    serializer_class = DealerRequestSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.is_superuser or getattr(user.role, 'name', '') == 'Admin':
            return DealerRequest.objects.all()
        return DealerRequest.objects.filter(requested_by=user)

    def perform_create(self, serializer):
        serializer.save(requested_by=self.request.user)

    @swagger_auto_schema(
        operation_description="Get all dealer requests (admin) or only your own (sales staff).",
        tags=["Dealer Request"]
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_description="Submit a new dealer request.",
        tags=["Dealer Request"]
    )
    def create(self, request, *args, **kwargs):
        return super().create(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_description="Retrieve a specific dealer request.",
        tags=["Dealer Request"]
    )
    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_description="Update a dealer request. Only admins can approve/reject.",
        tags=["Dealer Request"]
    )
    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        new_status = request.data.get('status')
        is_admin = request.user.is_superuser or getattr(request.user.role, 'name', '') == 'Admin'

        if new_status in ['approved', 'rejected']:
            if not is_admin:
                return Response({'detail': 'Not allowed to change status.'}, status=status.HTTP_403_FORBIDDEN)

            instance.status = new_status
            instance.reviewed_by = request.user
            instance.reviewed_at = timezone.now()
            instance.save()

            return Response(self.get_serializer(instance).data)

        return super().update(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_description="Partially update a dealer request (admin only for status changes).",
        tags=["Dealer Request"]
    )
    def partial_update(self, request, *args, **kwargs):
        return self.update(request, *args, **kwargs)  # reuse same permission logic

    @swagger_auto_schema(
        operation_description="Delete a dealer request.",
        tags=["Dealer Request"]
    )
    def destroy(self, request, *args, **kwargs):
        return super().destroy(request, *args, **kwargs)