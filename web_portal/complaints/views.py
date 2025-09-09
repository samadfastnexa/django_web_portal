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
#         tags=["07. Complaints"]
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
#         tags=["07. Complaints"]
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
        operation_description="Retrieve a paginated list of complaints with filtering and sorting options. Admins can view all complaints, while regular users can only see their own complaints.",
        manual_parameters=[
            openapi.Parameter('status', openapi.IN_QUERY, type=openapi.TYPE_STRING, description="Filter by complaint status (pending, in_progress, resolved, closed)", example="pending"),
            openapi.Parameter('user_id', openapi.IN_QUERY, type=openapi.TYPE_INTEGER, description="Filter by specific user ID (admin only for viewing other users' complaints)", example=1),
            openapi.Parameter('start_date', openapi.IN_QUERY, type=openapi.TYPE_STRING, format='date', description="Filter complaints created on or after this date (YYYY-MM-DD)", example="2024-01-01"),
            openapi.Parameter('end_date', openapi.IN_QUERY, type=openapi.TYPE_STRING, format='date', description="Filter complaints created on or before this date (YYYY-MM-DD)", example="2024-12-31"),
            openapi.Parameter('ordering', openapi.IN_QUERY, type=openapi.TYPE_STRING, description="Order by created_at field (use '-created_at' for descending)", example="-created_at"),
            openapi.Parameter('page', openapi.IN_QUERY, type=openapi.TYPE_INTEGER, description="Page number for pagination", example=1),
            openapi.Parameter('page_size', openapi.IN_QUERY, type=openapi.TYPE_INTEGER, description="Number of complaints per page (max 100)", example=10),
        ],
        responses={
            200: openapi.Response(
                description='List of complaints',
                examples={
                    'application/json': {
                        'count': 25,
                        'next': 'http://localhost:8000/api/complaints/?page=2',
                        'previous': None,
                        'results': [
                            {
                                'id': 1,
                                'complaint_id': 'FB12345678',
                                'user': 1,
                                'status': 'pending',
                                'message': 'Issue with water supply in my farm area',
                                'image': 'http://localhost:8000/media/complaint_images/farm_issue.jpg',
                                'created_at': '2024-01-15T10:30:00Z'
                            }
                        ]
                    }
                }
            )
        },
        tags=["07. Complaints"]
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_description="Submit a new complaint to the system. A unique complaint ID will be automatically generated.",
        manual_parameters=[
            openapi.Parameter('message', openapi.IN_FORM, type=openapi.TYPE_STRING, description='Detailed description of the complaint or issue', required=True, example='Water shortage in my farm area for the past week'),
            openapi.Parameter('image', openapi.IN_FORM, type=openapi.TYPE_FILE, description='Optional image evidence to support the complaint', required=False),
        ],
        responses={
            201: openapi.Response(
                description='Complaint created successfully',
                examples={
                    'application/json': {
                        'id': 1,
                        'complaint_id': 'FB12345678',
                        'user': 1,
                        'status': 'pending',
                        'message': 'Water shortage in my farm area for the past week',
                        'image': 'http://localhost:8000/media/complaint_images/evidence.jpg',
                        'created_at': '2024-01-15T10:30:00Z'
                    }
                }
            ),
            400: 'Bad Request - Invalid data provided'
        },
        tags=["07. Complaints"]
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
#         tags=["07. Complaints"]
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
#         tags=["07. Complaints"]
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
#         tags=["07. Complaints"]
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
        operation_description="Retrieve detailed information of a specific complaint by its ID. Access is restricted based on user permissions.",
        responses={
            200: openapi.Response(
                description='Complaint details',
                examples={
                    'application/json': {
                        'id': 1,
                        'complaint_id': 'FB12345678',
                        'user': 1,
                        'status': 'in_progress',
                        'message': 'Water shortage in my farm area for the past week',
                        'image': 'http://localhost:8000/media/complaint_images/evidence.jpg',
                        'created_at': '2024-01-15T10:30:00Z'
                    }
                }
            ),
            403: 'Forbidden - You can only view your own complaints',
            404: 'Complaint not found'
        },
        tags=["07. Complaints"]
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_description="Update the status of a complaint (partial update). Only authorized staff can change complaint status.",
        request_body=ComplaintSerializer,
        responses={
            200: openapi.Response(
                description='Complaint status updated successfully',
                examples={
                    'application/json': {
                        'id': 1,
                        'complaint_id': 'FB12345678',
                        'user': 1,
                        'status': 'in_progress',
                        'message': 'Water shortage in my farm area for the past week',
                        'image': 'http://localhost:8000/media/complaint_images/evidence.jpg',
                        'created_at': '2024-01-15T10:30:00Z'
                    }
                }
            ),
            403: 'Forbidden - Insufficient permissions',
            404: 'Complaint not found',
            400: 'Bad Request - Invalid status value'
        },
        tags=["07. Complaints"]
    )
    def patch(self, request, *args, **kwargs):
        return self.update(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_description="Fully update the complaint status (complete replacement). Only authorized staff can change complaint status.",
        request_body=ComplaintSerializer,
        responses={
            200: openapi.Response(
                description='Complaint status updated successfully',
                examples={
                    'application/json': {
                        'id': 1,
                        'complaint_id': 'FB12345678',
                        'user': 1,
                        'status': 'resolved',
                        'message': 'Water shortage in my farm area for the past week',
                        'image': 'http://localhost:8000/media/complaint_images/evidence.jpg',
                        'created_at': '2024-01-15T10:30:00Z'
                    }
                }
            ),
            403: 'Forbidden - Insufficient permissions',
            404: 'Complaint not found',
            400: 'Bad Request - Invalid status value'
        },
        tags=["07. Complaints"]
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
