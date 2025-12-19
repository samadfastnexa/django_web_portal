from rest_framework import generics, permissions, viewsets, status
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.response import Response
from rest_framework.exceptions import PermissionDenied
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from rest_framework.decorators import action
from .models import Attendance, AttendanceRequest
from .serializers import AttendanceSerializer, AttendanceRequestSerializer,AttendanceReportSerializer,EmptySerializer, AttendanceCheckInSerializer, AttendanceCheckOutSerializer
from rest_framework.permissions import IsAuthenticated
from accounts.permissions import HasRolePermission
from rest_framework.exceptions import ValidationError
from rest_framework.views import APIView
from .services import mark_attendance
from django.utils.timezone import now
from datetime import timedelta
from .models import LeaveRequest
from .serializers import LeaveRequestSerializer
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import OrderingFilter, SearchFilter
from rest_framework import viewsets, status, permissions
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.exceptions import PermissionDenied
from drf_yasg.utils import swagger_auto_schema
from .models import AttendanceRequest, Attendance
from .serializers import AttendanceRequestSerializer
from rest_framework import serializers
from django.utils import timezone
from django.contrib.auth import get_user_model
import logging
logger = logging.getLogger(__name__)
User = get_user_model() 



# ✅ List All Attendance Records
class AttendanceListView(generics.ListAPIView):
    queryset = Attendance.objects.all()
    serializer_class = AttendanceSerializer
    permission_classes = [IsAuthenticated, HasRolePermission]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['attendee', 'user', 'source']
    search_fields = ['attendee__username', 'attendee__email', 'user__username']
    ordering_fields = ['created_at', 'check_in_time', 'check_out_time']

    @swagger_auto_schema(
        operation_description="Get a list of all attendance records with optional filtering.",
        responses={
            200: openapi.Response(
                description='List of attendance records',
                schema=AttendanceSerializer(many=True),
            )
        },
        tags=["08. Attendance"]
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

# ✅ Individual Attendance Record
class AttendanceIndividualView(generics.RetrieveAPIView):
    queryset = Attendance.objects.all()
    serializer_class = AttendanceSerializer
    permission_classes = [IsAuthenticated, HasRolePermission]
    lookup_field = 'pk'

    @swagger_auto_schema(
        operation_description="Get a single attendance record by ID.",
        responses={
            200: openapi.Response(
                description='Attendance record',
                examples={
                    'application/json': {
                        'id': 1,
                        'attendee': 1,
                        'check_in_time': '2024-01-15T09:00:00Z',
                        'check_out_time': '2024-01-15T17:30:00Z',
                        'latitude': '31.5204',
                        'longitude': '74.3587',
                        'check_in_image': '/media/attendance_checkin/photo_123.jpg',
                        'check_out_image': '/media/attendance_checkout/photo_124.jpg',
                        'created_at': '2024-01-15T09:00:00Z'
                    }
                }
            ),
            404: 'Attendance record not found'
        },
        tags=["08. Attendance"]
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs) 

# ✅ Check-in Endpoint (POST)
class AttendanceCheckInView(generics.CreateAPIView):
    serializer_class = AttendanceCheckInSerializer
    permission_classes = [IsAuthenticated, HasRolePermission]
    parser_classes = [MultiPartParser, FormParser]
    
    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):
            return Attendance.objects.none()
        return Attendance.objects.all()
    
    @swagger_auto_schema(
        operation_description="Check-in with image upload. Creates a new attendance record with check-in time and image. Expects multipart/form-data with fields: attendee (integer), check_in_time (datetime), check_in_latitude (number), check_in_longitude (number), check_in_image (file).",
        request_body=AttendanceCheckInSerializer,
        responses={
            201: openapi.Response(
                description='Check-in successful',
                schema=AttendanceCheckInSerializer,
                examples={
                    'application/json': {
                        'id': 1,
                        'attendee': 1,
                        'check_in_time': '2024-01-15T09:00:00Z',
                        'check_in_latitude': '31.5204',
                        'check_in_longitude': '74.3587',
                        'check_in_image': '/media/attendance_checkin/photo_123.jpg'
                    }
                }
            ),
            400: 'Bad Request - Invalid data or check-in time required'
        },
        tags=["08. Attendance"]
    )
    def post(self, request, *args, **kwargs):
        return super().post(request, *args, **kwargs)
    
    def perform_create(self, serializer):
        user = self.request.user
        attendee = serializer.validated_data.get('attendee', user)
        
        serializer.save(user=user, attendee=attendee)


# ✅ Attendance Update/Delete View (PUT, PATCH, DELETE)
class AttendanceUpdateView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = AttendanceSerializer
    permission_classes = [IsAuthenticated, HasRolePermission]
    parser_classes = [MultiPartParser, FormParser]
    lookup_field = 'attendee_id'
    lookup_url_kwarg = 'attendee_id'
    
    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):
            return Attendance.objects.none()
        attendee_id = self.kwargs.get('attendee_id')
        return Attendance.objects.filter(attendee_id=attendee_id)
    
    def get_object(self):
        """Override to return the latest attendance record for the attendee"""
        queryset = self.get_queryset()
        if not queryset.exists():
            from django.http import Http404
            raise Http404("No attendance records found for this attendee")
        # Return the latest attendance record based on created_at
        return queryset.order_by('-created_at').first()
    
    def get_serializer_class(self):
        if self.request.method == 'PATCH':
            return AttendanceCheckOutSerializer
        return AttendanceSerializer
    
    @swagger_auto_schema(
        operation_description="Retrieve attendance record details by attendee ID.",
        responses={
            200: openapi.Response(
                description='Attendance record details for the specified attendee',
                examples={
                    'application/json': {
                        'id': 1,
                        'attendee': 1,
                        'check_in_time': '2024-01-15T09:00:00Z',
                        'check_out_time': '2024-01-15T17:30:00Z',
                        'latitude': '31.5204',
                        'longitude': '74.3587',
                        'check_in_image': '/media/attendance_checkin/photo_123.jpg',
                        'check_out_image': '/media/attendance_checkout/photo_124.jpg',
                        'created_at': '2024-01-15T09:00:00Z'
                    }
                }
            ),
            404: 'Attendance record not found for this attendee'
        },
        tags=["08. Attendance"]
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)
    
    @swagger_auto_schema(
        operation_description="Update all fields of an attendance record for a specific attendee. Requires multipart/form-data for image uploads.",
        request_body=AttendanceSerializer,
        responses={
            200: openapi.Response(
                description='Attendance record updated successfully',
                schema=AttendanceSerializer,
                examples={
                    'application/json': {
                        'id': 1,
                        'attendee': 1,
                        'check_in_time': '2024-01-15T09:00:00Z',
                        'check_out_time': '2024-01-15T17:30:00Z',
                        'latitude': '31.5204',
                        'longitude': '74.3587',
                        'check_in_image': '/media/attendance_checkin/photo_123.jpg',
                        'check_out_image': '/media/attendance_checkout/photo_124.jpg'
                    }
                }
            ),
            400: 'Bad Request - Invalid data provided',
            404: 'Attendance record not found for this attendee'
        },
        tags=["08. Attendance"]
    )
    def put(self, request, *args, **kwargs):
        return super().put(request, *args, **kwargs)
    
    @swagger_auto_schema(
        operation_description="Check-out only: Update check-out time, location, and image for an existing attendance record of a specific attendee. Requires multipart/form-data for image upload.",
        request_body=AttendanceCheckOutSerializer,
        responses={
            200: openapi.Response(
                description='Check-out successful',
                schema=AttendanceCheckOutSerializer,
                examples={
                    'application/json': {
                        'id': 1,
                        'check_out_time': '2024-01-15T17:30:00Z',
                        'check_out_latitude': '31.5204',
                        'check_out_longitude': '74.3587',
                        'check_out_image': '/media/attendance_checkout/photo_124.jpg'
                    }
                }
            ),
            400: 'Bad Request - Invalid check-out data or missing check-in',
            404: 'Attendance record not found for this attendee'
        },
        tags=["08. Attendance"]
    )
    def patch(self, request, *args, **kwargs):
        return super().patch(request, *args, **kwargs)
    
    @swagger_auto_schema(
        operation_description="Permanently delete an attendance record for a specific attendee from the system.",
        responses={
            204: 'Attendance record deleted successfully',
            404: 'Attendance record not found for this attendee'
        },
        tags=["08. Attendance"]
    )
    def delete(self, request, *args, **kwargs):
        return super().delete(request, *args, **kwargs)

# ✅ Attendance Records by Attendee with Time Filtering
class AttendanceByAttendeeView(generics.ListAPIView):
    serializer_class = AttendanceSerializer
    permission_classes = [IsAuthenticated, HasRolePermission]
    lookup_url_kwarg = 'attendee_id'
    
    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):
            return Attendance.objects.none()
        
        attendee_id = self.request.query_params.get('attendee_id')
        filter_type = self.request.query_params.get('filter', 'daily')
        
        # If attendee_id is None (not provided), return all records; otherwise filter by attendee_id
        if attendee_id is None:
            queryset = Attendance.objects.all()
        else:
            queryset = Attendance.objects.filter(attendee_id=attendee_id)
        
        from django.utils import timezone
        from datetime import timedelta
        
        today = timezone.now().date()
        
        if filter_type == 'daily':
            # Get today's attendance records
            queryset = queryset.filter(check_in_time__date=today)
        elif filter_type == 'weekly':
            # Get this week's attendance records (Monday to Sunday)
            start_of_week = today - timedelta(days=today.weekday())
            end_of_week = start_of_week + timedelta(days=6)
            queryset = queryset.filter(
                check_in_time__date__gte=start_of_week,
                check_in_time__date__lte=end_of_week
            )
        elif filter_type == 'monthly':
            # Get this month's attendance records
            queryset = queryset.filter(
                check_in_time__year=today.year,
                check_in_time__month=today.month
            )
        
        return queryset.order_by('-check_in_time')
    
    @swagger_auto_schema(
        operation_description="Get attendance records with time-based filtering (daily, weekly, monthly). If attendee_id is provided as a query parameter, returns records for that specific user. If attendee_id is not provided, returns all attendance records for all users.",
        manual_parameters=[
            openapi.Parameter(
                'attendee_id',
                openapi.IN_QUERY,
                description='Optional: Attendee ID to filter records for a specific user. If not provided, returns all users.',
                type=openapi.TYPE_INTEGER,
                required=False
            ),
            openapi.Parameter(
                'filter',
                openapi.IN_QUERY,
                description='Filter type: daily (today), weekly (this week), or monthly (this month)',
                type=openapi.TYPE_STRING,
                enum=['daily', 'weekly', 'monthly'],
                default='daily'
            )
        ],
        responses={
            200: openapi.Response(
                description='List of attendance records. Returns all users when attendee_id is not provided, or specific user records when attendee_id is provided as a query parameter.',
                schema=AttendanceSerializer(many=True),
                examples={
                    'application/json': [
                        {
                            'id': 1,
                            'attendee': 1,
                            'check_in_time': '2024-01-15T09:00:00Z',
                            'check_out_time': '2024-01-15T17:30:00Z',
                            'latitude': '31.5204',
                            'longitude': '74.3587',
                            'check_in_image': '/media/attendance_checkin/photo_123.jpg',
                            'check_out_image': '/media/attendance_checkout/photo_124.jpg',
                            'created_at': '2024-01-15T09:00:00Z'
                        }
                    ]
                }
            ),
            404: 'No attendance records found'
        },
        tags=["08. Attendance"]
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

# ✅ Attendance Status Check for Today
class AttendanceStatusView(APIView):
    permission_classes = [IsAuthenticated]
    
    @swagger_auto_schema(
        operation_description="Check attendance status for today. If attendee_id is provided, check for that specific attendee (requires admin permissions). Otherwise, check for the current user.",
        manual_parameters=[
            openapi.Parameter(
                'attendee_id',
                openapi.IN_QUERY,
                description='Optional: Check attendance status for specific attendee ID (admin only)',
                type=openapi.TYPE_INTEGER,
                required=False
            )
        ],
        responses={
            200: openapi.Response(
                description='Attendance status for today',
                examples={
                    'application/json': {
                        'date': '2024-01-15',
                        'attendee_id': 1,
                        'has_checked_in': True,
                        'has_checked_out': False,
                        'check_in_time': '2024-01-15T09:00:00Z',
                        'check_out_time': None,
                        'attendance_id': 1,
                        'status': 'checked_in'
                    }
                }
            ),
            403: 'Forbidden - Admin permissions required to check other users attendance',
            404: 'Attendee not found'
        },
        tags=["08. Attendance"]
    )
    def get(self, request):
        from django.utils import timezone
        from rest_framework.response import Response
        
        # Ensure user is authenticated
        if not request.user.is_authenticated:
            return Response({'error': 'Authentication required'}, status=401)
        
        attendee_id = request.query_params.get('attendee_id')
        today = timezone.now().date()
        
        # Determine which user to check attendance for
        if attendee_id:
            # Check if current user has admin permissions to view other users' attendance
            if not (request.user.is_staff or request.user.is_superuser):
                return Response({'error': 'Admin permissions required to check other users attendance'}, status=403)
            
            try:
                target_user = User.objects.get(id=attendee_id)
            except User.DoesNotExist:
                return Response({'error': 'Attendee not found'}, status=404)
        else:
            target_user = request.user
            attendee_id = request.user.id
        
        # Get today's attendance record for the target user
        # Check both user and attendee fields to cover all cases
        attendance = Attendance.objects.filter(
            attendee=target_user,
            check_in_time__date=today
        ).first()
        
        if not attendance:
            # Also check if user is the one who marked attendance
            attendance = Attendance.objects.filter(
                user=target_user,
                check_in_time__date=today
            ).first()
        
        if attendance:
            has_checked_in = attendance.check_in_time is not None
            has_checked_out = attendance.check_out_time is not None
            
            if has_checked_in and has_checked_out:
                status = 'completed'
            elif has_checked_in:
                status = 'checked_in'
            else:
                status = 'partial'
        else:
            has_checked_in = False
            has_checked_out = False
            status = 'not_marked'
        
        response_data = {
            'date': today.isoformat(),
            'attendee_id': attendee_id,
            'has_checked_in': has_checked_in,
            'has_checked_out': has_checked_out,
            'check_in_time': attendance.check_in_time.isoformat() if attendance and attendance.check_in_time else None,
            'check_out_time': attendance.check_out_time.isoformat() if attendance and attendance.check_out_time else None,
            'attendance_id': attendance.id if attendance else None,
            'status': status
        }
        
        return Response(response_data)

# views.py (at the top, before your viewset)
# ----------------------------------
# Serializers for action responses
# ----------------------------------
class AttendanceRequestActionSerializer(serializers.Serializer):
    id = serializers.IntegerField(read_only=True)  # ✅ Add request ID in response
    status = serializers.CharField(read_only=True)
    detail = serializers.CharField(read_only=True)


class EmptySerializer(serializers.Serializer):
    """Used for Swagger to show no input fields"""
    pass


class AttendanceRequestViewSet(viewsets.ModelViewSet):
    serializer_class = AttendanceRequestSerializer
    permission_classes = [permissions.IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def get_serializer_class(self):
        # Use EmptySerializer for approve/reject actions to avoid validation issues
        if self.action in ['approve', 'reject']:
            return EmptySerializer
        return AttendanceRequestSerializer

    # --------------------------
    # Queryset
    # --------------------------
    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):
            return AttendanceRequest.objects.none()
        user = self.request.user
        if self._has_approval_permission(user):
            return AttendanceRequest.objects.all()
        return AttendanceRequest.objects.filter(user=user)

    # --------------------------
    # Create
    # --------------------------
    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    # --------------------------
    # Permission helpers
    # --------------------------
    def _check_status_change_permission(self, request):
        instance = self.get_object()
        incoming_status = request.data.get("status")
        if incoming_status and incoming_status != instance.status:
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

    # --------------------------
    # Default CRUD actions with Swagger
    # --------------------------
    @swagger_auto_schema(
        operation_description="Retrieve a paginated list of attendance requests. Admins can view all requests, while regular users can only see their own submissions.",
        responses={
            200: openapi.Response(
                description='List of attendance requests',
                examples={
                    'application/json': [
                        {
                            'id': 1,
                            'user': 1,
                            'request_type': 'late_arrival',
                            'date': '2024-01-15',
                            'reason': 'Traffic jam due to road construction',
                            'status': 'pending',
                            'attachment': '/media/requests/proof_123.jpg',
                            'created_at': '2024-01-15T08:30:00Z',
                            'updated_at': '2024-01-15T08:30:00Z'
                        }
                    ]
                }
            )
        },
        tags=["09. Attendance Request"]
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_description="Submit a new attendance request for late arrival, early departure, or missed attendance with supporting documentation.",
        request_body=AttendanceRequestSerializer,
        responses={
            201: openapi.Response(
                description='Attendance request created successfully',
                examples={
                    'application/json': {
                        'id': 1,
                        'user': 1,
                        'request_type': 'late_arrival',
                        'date': '2024-01-15',
                        'reason': 'Traffic jam due to road construction',
                        'status': 'pending',
                        'created_at': '2024-01-15T08:30:00Z'
                    }
                }
            ),
            400: 'Bad Request - Invalid data or missing required fields'
        },
        tags=["09. Attendance Request"]
    )
    def create(self, request, *args, **kwargs):
        return super().create(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_description="Retrieve detailed information of a specific attendance request including status and approval history.",
        responses={
            200: openapi.Response(
                description='Attendance request details',
                examples={
                    'application/json': {
                        'id': 1,
                        'user': 1,
                        'request_type': 'late_arrival',
                        'date': '2024-01-15',
                        'reason': 'Traffic jam due to road construction on main highway',
                        'status': 'approved',
                        'attachment': '/media/requests/proof_123.jpg',
                        'approved_by': 2,
                        'approval_date': '2024-01-15T10:00:00Z',
                        'created_at': '2024-01-15T08:30:00Z',
                        'updated_at': '2024-01-15T10:00:00Z'
                    }
                }
            ),
            404: 'Attendance request not found'
        },
        tags=["09. Attendance Request"]
    )
    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_description="Update all fields of an attendance request. Status changes require admin permissions.",
        responses={
            200: 'Attendance request updated successfully',
            404: 'Attendance request not found',
            403: 'Forbidden - Insufficient permissions to change status',
            400: 'Bad Request - Invalid data provided'
        },
        tags=["09. Attendance Request"]
    )
    def update(self, request, *args, **kwargs):
        self._check_status_change_permission(request)
        return super().update(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_description="Update specific fields of an attendance request. Status changes require admin permissions.",
        responses={
            200: 'Attendance request updated successfully',
            404: 'Attendance request not found',
            403: 'Forbidden - Insufficient permissions to change status',
            400: 'Bad Request - Invalid data provided'
        },
        tags=["09. Attendance Request"]
    )
    def partial_update(self, request, *args, **kwargs):
        self._check_status_change_permission(request)
        return super().partial_update(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_description="Permanently delete an attendance request from the system.",
        responses={
            204: 'Attendance request deleted successfully',
            404: 'Attendance request not found'
        },
        tags=["09. Attendance Request"]
    )
    def destroy(self, request, *args, **kwargs):
        return super().destroy(request, *args, **kwargs)

    # --------------------------
    # Approve action
    # --------------------------
    # @action(
    #     detail=True,
    #     methods=['post'],
    #     url_path='approve',
    #     permission_classes=[permissions.IsAdminUser]
    # )
    # @swagger_auto_schema(
    #     request_body=EmptySerializer,
    #     responses={
    #         200: openapi.Response(
    #             description="Request approved and attendance recorded.",
    #             schema=AttendanceRequestActionSerializer()
    #         ),
    #         400: openapi.Response(
    #             description="Already approved or invalid request.",
    #             schema=AttendanceRequestActionSerializer()
    #         ),
    #     },
    #     operation_description="Approve an attendance request. Admin does not need to provide any time.",
    #     tags=["Attendance Request"]
    # )
    # -----------------------
    # Approve Attendance Request
    # -----------------------
   
    @action(detail=True, methods=["post"], url_path="approve")
    def approve(self, request, pk=None):
        attendance_request = self.get_object()

        # ✅ Permission check
        if not self._has_approval_permission(request.user):
            return Response(
                {"error": "You are not allowed to approve requests."},
                status=status.HTTP_403_FORBIDDEN
            )

        if attendance_request.status == AttendanceRequest.STATUS_APPROVED:
            return Response(
                {"error": "This request is already approved."},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            # 1️⃣ Mark attendance
            attendance = mark_attendance(
                user=request.user,  # Admin/staff approving
                attendee=attendance_request.user,  # Original requester
                check_type=attendance_request.check_type,
                timestamp=attendance_request.check_in_time or attendance_request.check_out_time,
                latitude=getattr(attendance_request, "latitude", None),
                longitude=getattr(attendance_request, "longitude", None),
                check_in_image=getattr(attendance_request, "attachment", None) if attendance_request.check_type == AttendanceRequest.CHECK_IN else None,
                check_out_image=getattr(attendance_request, "attachment", None) if attendance_request.check_type == AttendanceRequest.CHECK_OUT else None,
                source="request"
            )

            # 2️⃣ Update request status
            attendance_request.status = AttendanceRequest.STATUS_APPROVED
            attendance_request.attendance = attendance
            attendance_request.save()

            return Response({
                "message": "Request approved successfully",
                "attendance_id": attendance.id,
            }, status=status.HTTP_200_OK)

        except ValidationError as ve:
            return Response({"error": ve.message_dict if hasattr(ve, "message_dict") else str(ve)},
                            status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.exception("Error approving attendance request")
            return Response({"error": ["An unexpected error occurred while marking attendance."]},
                            status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
# ✅ Attendance Report View (Daily, Weekly, Monthly, Custom)
# This view allows users to get attendance reports based on different time periods.
class AttendanceReportView(APIView):
    # permission_classes = [IsAuthenticated]
    permission_classes = [IsAuthenticated, HasRolePermission]
    # 🔹 Swagger parameters
    @swagger_auto_schema(
        operation_description="Get attendance report (daily, weekly, monthly, or custom)",
        tags=["10. Attendance Report"],
        manual_parameters=[
            openapi.Parameter(
                "type",
                openapi.IN_QUERY,
                description="Report type (daily, weekly, monthly, or custom)",
                type=openapi.TYPE_STRING,
                enum=["daily", "weekly", "monthly", "custom"],
                required=False
            ),
            openapi.Parameter(
                "start_date",
                openapi.IN_QUERY,
                description="Custom start date (YYYY-MM-DD) — only works if type=custom",
                type=openapi.TYPE_STRING,
                required=False
            ),
            openapi.Parameter(
                "end_date",
                openapi.IN_QUERY,
                description="Custom end date (YYYY-MM-DD) — only works if type=custom",
                type=openapi.TYPE_STRING,
                required=False
            ),
            openapi.Parameter(
                "user_id",
                openapi.IN_QUERY,
                description="Filter by attendee user ID",
                type=openapi.TYPE_INTEGER,
                required=False
            ),
        ],
        responses={200: AttendanceReportSerializer(many=True)},
    )
    def get(self, request):
        report_type = request.query_params.get("type", "weekly")
        user_id = request.query_params.get("user_id")
        start_date_param = request.query_params.get("start_date")
        end_date_param = request.query_params.get("end_date")

        today = now().date()

        # 🔹 Handle date ranges
        if report_type == "daily":
            start_date, end_date = today, today
        elif report_type == "weekly":
            start_date, end_date = today - timedelta(days=7), today
        elif report_type == "monthly":
            start_date, end_date = today - timedelta(days=30), today
        elif report_type == "custom" and start_date_param and end_date_param:
            from datetime import datetime
            try:
                start_date = datetime.strptime(start_date_param, "%Y-%m-%d").date()
                end_date = datetime.strptime(end_date_param, "%Y-%m-%d").date()
            except ValueError:
                return Response({"error": "Invalid date format, use YYYY-MM-DD"}, status=400)
        else:
            return Response({"error": "Invalid or incomplete report parameters"}, status=400)

        # 🔹 Filter attendance
        qs = Attendance.objects.filter(check_in_time__date__gte=start_date,
                                       check_in_time__date__lte=end_date)

        if user_id:
            qs = qs.filter(attendee_id=user_id)

        serializer = AttendanceReportSerializer(qs, many=True)
        return Response({
            "report_type": report_type,
            "start_date": str(start_date),
            "end_date": str(end_date),
            "records": serializer.data
        })
        
# ✅ Enum values
LEAVE_TYPE_CHOICES = ["sick", "casual", "annual"]
STATUS_CHOICES = ["pending", "approved", "rejected"]

# ✅ Swagger Request Schema
leave_request_example = openapi.Schema(
    type=openapi.TYPE_OBJECT,
    properties={
        "leave_type": openapi.Schema(
            type=openapi.TYPE_STRING,
            enum=LEAVE_TYPE_CHOICES,
            example="sick"
        ),
        "start_date": openapi.Schema(
            type=openapi.TYPE_STRING,
            format="date",
            example="2025-08-20"
        ),
        "end_date": openapi.Schema(
            type=openapi.TYPE_STRING,
            format="date",
            example="2025-08-25"
        ),
        "reason": openapi.Schema(
            type=openapi.TYPE_STRING,
            example="Medical leave due to illness"
        ),
        "status": openapi.Schema(
            type=openapi.TYPE_STRING,
            enum=STATUS_CHOICES,
            example="pending"
        ),
    },
    required=["leave_type", "start_date", "end_date", "reason"]
)

# ✅ Swagger Response Example
leave_response_example = {
    "id": 12,
    "user": 3,
    "leave_type": "sick",
    "start_date": "2025-08-20",
    "end_date": "2025-08-25",
    "reason": "Medical leave due to illness",
    "status": "pending",
    "created_at": "2025-08-18T10:30:00Z",
    "updated_at": "2025-08-18T10:30:00Z"
}

# ✅ Query params for filtering
leave_filter_params = [
    openapi.Parameter(
        "status", openapi.IN_QUERY, description="Filter by status",
        type=openapi.TYPE_STRING, enum=STATUS_CHOICES
    ),
    openapi.Parameter(
        "leave_type", openapi.IN_QUERY, description="Filter by leave type",
        type=openapi.TYPE_STRING, enum=LEAVE_TYPE_CHOICES
    ),
    openapi.Parameter(
        "start_date", openapi.IN_QUERY, description="Filter by start_date (YYYY-MM-DD)",
        type=openapi.TYPE_STRING, format="date"
    ),
    openapi.Parameter(
        "end_date", openapi.IN_QUERY, description="Filter by end_date (YYYY-MM-DD)",
        type=openapi.TYPE_STRING, format="date"
    ),
    openapi.Parameter(
        "user", openapi.IN_QUERY, description="Filter by user ID",
        type=openapi.TYPE_INTEGER
    ),
]


# ✅ List + Create View
class LeaveRequestListCreateView(generics.ListCreateAPIView):
    serializer_class = LeaveRequestSerializer
    permission_classes = [IsAuthenticated, HasRolePermission]

    filter_backends = [DjangoFilterBackend, OrderingFilter, SearchFilter]
    filterset_fields = ["status", "leave_type", "start_date", "end_date", "user"]
    ordering_fields = ["start_date", "end_date", "status", "created_at"]
    search_fields = ["reason", "user__username", "user__email"]

    def get_queryset(self):
        user = self.request.user
        if getattr(self, "swagger_fake_view", False):
            return LeaveRequest.objects.none()
        if not (user.is_staff or user.is_superuser):
            return LeaveRequest.objects.filter(user=user)
        return LeaveRequest.objects.all()

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    # ✅ Swagger for GET
    @swagger_auto_schema(
        manual_parameters=leave_filter_params,
        responses={200: LeaveRequestSerializer(many=True)},
        operation_summary="List all leave requests",
        operation_description="Admins see all leave requests, normal users only see their own.",
        tags=["11. Leave Requests"]
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    # ✅ Swagger for POST
    @swagger_auto_schema(
        request_body=leave_request_example,
        responses={
            201: openapi.Response(
                "Created",
                LeaveRequestSerializer,
                examples={"application/json": leave_response_example}
            )
        },
        operation_summary="Create a new leave request",
        operation_description="Submit a new leave request with leave_type, start_date, end_date, and reason.",
        tags=["11. Leave Requests"]
    )
    def post(self, request, *args, **kwargs):
        return super().post(request, *args, **kwargs)


# ✅ Retrieve + Update + Delete View
class LeaveRequestDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = LeaveRequestSerializer
    permission_classes = [IsAuthenticated, HasRolePermission]

    def get_queryset(self):
        user = self.request.user
        if getattr(self, "swagger_fake_view", False):
            return LeaveRequest.objects.none()
        if not (user.is_staff or user.is_superuser):
            return LeaveRequest.objects.filter(user=user)
        return LeaveRequest.objects.all()

    # ✅ Swagger GET by ID
    @swagger_auto_schema(
        responses={200: LeaveRequestSerializer()},
        operation_summary="Retrieve leave request by ID",
        operation_description="Admins can retrieve any request, users only their own.",
        tags=["11. Leave Requests"]
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    # ✅ Swagger PUT
    @swagger_auto_schema(
        request_body=leave_request_example,
        responses={200: LeaveRequestSerializer()},
        operation_summary="Update leave request",
        operation_description="Update all fields of a leave request (only owner or admin).",
        tags=["11. Leave Requests"]
    )
    def put(self, request, *args, **kwargs):
        return super().put(request, *args, **kwargs)

    # ✅ Swagger PATCH
    @swagger_auto_schema(
        request_body=leave_request_example,
        responses={200: LeaveRequestSerializer()},
        operation_summary="Partially update leave request",
        operation_description="Update selected fields of a leave request (only owner or admin).",
        tags=["11. Leave Requests"]
    )
    def patch(self, request, *args, **kwargs):
        return super().patch(request, *args, **kwargs)

    # ✅ Swagger DELETE
    @swagger_auto_schema(
        responses={204: "No Content"},
        operation_summary="Delete leave request",
        operation_description="Delete a leave request (only owner or admin).",
        tags=["11. Leave Requests"]
    )
    def delete(self, request, *args, **kwargs):
        return super().delete(request, *args, **kwargs)