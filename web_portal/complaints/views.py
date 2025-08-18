from rest_framework import generics, permissions, filters
from .models import Complaint
from .serializers import ComplaintSerializer
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.pagination import PageNumberPagination
import uuid
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from rest_framework.parsers import MultiPartParser, FormParser

from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response

from accounts.permissions import HasRolePermission
from rest_framework.permissions import IsAuthenticated

# ✅ List + Create View
class ComplaintPagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = 'page_size'
    max_page_size = 100


# class ComplaintListCreateView(generics.ListCreateAPIView):
#     serializer_class = ComplaintSerializer
#     filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
#     filterset_fields = ['status']
#     ordering_fields = ['created_at']
#     parser_classes = [MultiPartParser, FormParser]
#     pagination_class = ComplaintPagination

#     def get_queryset(self):
#         user = self.request.user

#         if not user.is_authenticated:
#             return Complaint.objects.none()

#         # If ?user_id is provided, filter by that user
#         user_id = self.request.query_params.get('user_id')
#         if user_id:
#             # Only staff or the same user can see this
#             if user.is_staff or str(user.id) == str(user_id):
#                 return Complaint.objects.filter(user_id=user_id).order_by('-created_at')
#             else:
#                 raise PermissionDenied("You can only see your own complaints or be an admin.")

#         # Default behavior
#         if user.is_staff:
#             return Complaint.objects.all().order_by('-created_at')

#         return Complaint.objects.filter(user=user).order_by('-created_at')

#     def get_permissions(self):
#         if self.request.method == 'POST':
#             return [permissions.IsAuthenticated()]
#         return [IsAuthenticated(), HasRolePermission()]  # All authenticated users can list; admins see all
#         # return [permissions.IsAuthenticated()]  # All authenticated users can list; admins see all

#     def perform_create(self, serializer):
#         complaint_id = f"FB{uuid.uuid4().hex[:8].upper()}"
#         serializer.save(user=self.request.user, complaint_id=complaint_id)

#     @swagger_auto_schema(
#         operation_description="List all complaints. Admins see all complaints. Users see only their own. Supports filtering, ordering, and pagination.",
#         manual_parameters=[
#             openapi.Parameter('status', openapi.IN_QUERY, type=openapi.TYPE_STRING, description="Filter by complaint status"),
#             openapi.Parameter('ordering', openapi.IN_QUERY, type=openapi.TYPE_STRING, description="Order by created_at"),
#             openapi.Parameter('page', openapi.IN_QUERY, type=openapi.TYPE_INTEGER, description="Page number"),
#             openapi.Parameter('page_size', openapi.IN_QUERY, type=openapi.TYPE_INTEGER, description="Page size"),
#         ],
#         responses={200: ComplaintSerializer(many=True)},
#         tags=["Complaints"]
#     )
#     def get(self, request, *args, **kwargs):
#         return super().get(request, *args, **kwargs)

#     @swagger_auto_schema(
#         operation_description="Create a new complaint (authenticated users only).",
#         manual_parameters=[
#             openapi.Parameter('message', openapi.IN_FORM, type=openapi.TYPE_STRING, description='Complaint message', required=True),
#             openapi.Parameter('image', openapi.IN_FORM, type=openapi.TYPE_FILE, description='Optional image upload', required=False),
#         ],
#         responses={201: ComplaintSerializer},
#         tags=["Complaints"]
#     )
#     def post(self, request, *args, **kwargs):
#         return super().post(request, *args, **kwargs)


class ComplaintListCreateView(generics.ListCreateAPIView):
    serializer_class = ComplaintSerializer
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['status']
    ordering_fields = ['created_at']
    parser_classes = [MultiPartParser, FormParser]
    pagination_class = ComplaintPagination

    def get_queryset(self):
        user = self.request.user

        if not user.is_authenticated:
            return Complaint.objects.none()

        qs = Complaint.objects.all()

        # ✅ Filter by user_id (admin or self)
        user_id = self.request.query_params.get('user_id')
        if user_id:
            if user.is_staff or str(user.id) == str(user_id):
                qs = qs.filter(user_id=user_id)
            else:
                raise PermissionDenied("You can only view your own complaints unless you are an admin.")
        elif not user.is_staff:
            qs = qs.filter(user=user)

        # ✅ Filter by status
        status_param = self.request.query_params.get('status')
        if status_param:
            qs = qs.filter(status=status_param)

        # ✅ Date range filter
        start_date = self.request.query_params.get('start_date')  # YYYY-MM-DD
        end_date = self.request.query_params.get('end_date')      # YYYY-MM-DD
        if start_date:
            qs = qs.filter(created_at__date__gte=start_date)
        if end_date:
            qs = qs.filter(created_at__date__lte=end_date)

        # ✅ Ordering handled by OrderingFilter
        return qs.order_by('-created_at')

    def get_permissions(self):
        if self.request.method == 'POST':
            return [permissions.IsAuthenticated()]
        return [IsAuthenticated(), HasRolePermission()]

    def perform_create(self, serializer):
        complaint_id = f"FB{uuid.uuid4().hex[:8].upper()}"
        serializer.save(user=self.request.user, complaint_id=complaint_id)

    @swagger_auto_schema(
        operation_description="List complaints. Admins see all, users see their own. "
                              "Supports filtering by status, user_id (admin or self), date range, ordering, and pagination.",
        manual_parameters=[
            openapi.Parameter('status', openapi.IN_QUERY, type=openapi.TYPE_STRING, description="Filter by complaint status"),
            openapi.Parameter('user_id', openapi.IN_QUERY, type=openapi.TYPE_INTEGER, description="Filter by specific user ID (admin only for others)"),
            openapi.Parameter('start_date', openapi.IN_QUERY, type=openapi.TYPE_STRING, format='date', description="Filter complaints created on or after this date (YYYY-MM-DD)"),
            openapi.Parameter('end_date', openapi.IN_QUERY, type=openapi.TYPE_STRING, format='date', description="Filter complaints created on or before this date (YYYY-MM-DD)"),
            openapi.Parameter('ordering', openapi.IN_QUERY, type=openapi.TYPE_STRING, description="Order by created_at, e.g., 'created_at' or '-created_at'"),
            openapi.Parameter('page', openapi.IN_QUERY, type=openapi.TYPE_INTEGER, description="Page number"),
            openapi.Parameter('page_size', openapi.IN_QUERY, type=openapi.TYPE_INTEGER, description="Page size"),
        ],
        responses={200: ComplaintSerializer(many=True)},
        tags=["Complaints"]
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_description="Create a new complaint (authenticated users only).",
        manual_parameters=[
            openapi.Parameter('message', openapi.IN_FORM, type=openapi.TYPE_STRING, description='Complaint message', required=True),
            openapi.Parameter('image', openapi.IN_FORM, type=openapi.TYPE_FILE, description='Optional image upload', required=False),
        ],
        responses={201: ComplaintSerializer},
        tags=["Complaints"]
    )
    def post(self, request, *args, **kwargs):
        return super().post(request, *args, **kwargs)



# # ✅ Retrieve + Update View (for viewing/updating individual complaints)
# class ComplaintRetrieveUpdateView(generics.RetrieveUpdateAPIView):
#     queryset = Complaint.objects.all()
#     serializer_class = ComplaintSerializer
#     # permission_classes = [permissions.IsAuthenticated]
#     permission_classes = [IsAuthenticated, HasRolePermission]
#     def get_permissions(self):
#         return [permissions.IsAuthenticated()]

#     def get_object(self):
#         obj = super().get_object()
#         if not self.request.user.is_staff and obj.user != self.request.user:
#             raise PermissionDenied("You can only view your own complaints.")
#         return obj

#     @swagger_auto_schema(
#         operation_description="Retrieve a single complaint. Users can only see their own complaints.",
#         responses={200: ComplaintSerializer},
#         tags=["Complaints"]
#     )
#     def get(self, request, *args, **kwargs):
#         return super().get(request, *args, **kwargs)

#     @swagger_auto_schema(
#         operation_description="Update complaint status (only allowed for users with permission). Only 'status' can be changed.",
#         request_body=openapi.Schema(
#             type=openapi.TYPE_OBJECT,
#             properties={
#                 'status': openapi.Schema(type=openapi.TYPE_STRING, description='New complaint status'),
#             },
#             required=['status'],
#         ),
#         responses={200: ComplaintSerializer},
#         tags=["Complaints"]
#     )
#     def patch(self, request, *args, **kwargs):
#         return self.update(request, *args, **kwargs)
#     @swagger_auto_schema(
#         operation_description="Fully update complaint status (only 'status' field allowed).",
#         request_body=openapi.Schema(
#             type=openapi.TYPE_OBJECT,
#             properties={
#                 'status': openapi.Schema(type=openapi.TYPE_STRING, description='New complaint status'),
#             },
#             required=['status'],
#         ),
#         responses={200: ComplaintSerializer},
#         tags=["Complaints"]
#     )
#     def put(self, request, *args, **kwargs):
#         return self.update(request, *args, **kwargs)
    
#     def update(self, request, *args, **kwargs):
#         if not request.user.has_perm('complaints.change_complaint'):
#             raise PermissionDenied("You don't have permission to update complaints.")

#         instance = self.get_object()
#         status = request.data.get('status')
#         if status is not None:
#             instance.status = status
#             instance.save()
#             serializer = self.get_serializer(instance)
#             return Response(serializer.data)
#         else:
#             return Response({'detail': 'Only status field can be updated.'}, status=400)

class ComplaintRetrieveUpdateView(generics.RetrieveUpdateAPIView):
    queryset = Complaint.objects.all()
    serializer_class = ComplaintSerializer
    permission_classes = [IsAuthenticated, HasRolePermission]

    def get_permissions(self):
        return [permissions.IsAuthenticated()]

    def get_object(self):
        obj = super().get_object()
        if not self.request.user.is_staff and obj.user != self.request.user:
            raise PermissionDenied("You can only view your own complaints.")
        return obj

    @swagger_auto_schema(
        operation_description=(
            "Retrieve a single complaint by ID.\n\n"
            "**Access rules:**\n"
            "- Admins: Can view any complaint.\n"
            "- Normal users: Can only view their own complaints."
        ),
        responses={200: ComplaintSerializer},
        tags=["Complaints"]
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_description=(
            "Partially update complaint status.\n\n"
            "**Access rules:**\n"
            "- Requires `complaints.change_complaint` permission.\n"
            "- Only the `status` field can be changed."
        ),
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'status': openapi.Schema(type=openapi.TYPE_STRING, description='New complaint status'),
            },
            required=['status'],
        ),
        responses={200: ComplaintSerializer},
        tags=["Complaints"]
    )
    def patch(self, request, *args, **kwargs):
        return self.update(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_description=(
            "Fully update complaint status.\n\n"
            "**Access rules:**\n"
            "- Requires `complaints.change_complaint` permission.\n"
            "- Only the `status` field is allowed in request body."
        ),
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'status': openapi.Schema(type=openapi.TYPE_STRING, description='New complaint status'),
            },
            required=['status'],
        ),
        responses={200: ComplaintSerializer},
        tags=["Complaints"]
    )
    def put(self, request, *args, **kwargs):
        return self.update(request, *args, **kwargs)

    def update(self, request, *args, **kwargs):
        if not request.user.has_perm('complaints.change_complaint'):
            raise PermissionDenied("You don't have permission to update complaints.")

        instance = self.get_object()
        status = request.data.get('status')
        if status is not None:
            instance.status = status
            instance.save()
            serializer = self.get_serializer(instance)
            return Response(serializer.data)
        else:
            return Response({'detail': 'Only status field can be updated.'}, status=400)
