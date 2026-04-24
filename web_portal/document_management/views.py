from django.db.models import Q, Count, Prefetch
from django.utils import timezone
from django.http import FileResponse, Http404
from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from django_filters.rest_framework import DjangoFilterBackend
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

from .models import Attachment, AttachmentAssignment, AttachmentDownloadLog
from .serializers import (
    AttachmentListSerializer,
    AttachmentDetailSerializer,
    AttachmentCreateUpdateSerializer,
    AttachmentAssignmentSerializer,
    AttachmentAssignmentBulkSerializer,
    AttachmentDownloadLogSerializer,
    AttachmentAcknowledgeSerializer,
)
from .permissions import (
    AttachmentAccessPermission,
    CanUploadAttachment,
    CanAssignAttachment,
)
from .filters import AttachmentFilter


def get_client_ip(request):
    """Extract client IP address from request."""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip


class AttachmentViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing attachments.
    
    - Admin/Superuser: Can CRUD all attachments
    - Regular users with permission: Can view only assigned attachments
    
    Filtering:
    - status: Filter by attachment status (active, archived, expired)
    - created_by: Filter by creator user ID
    - is_mandatory: Filter mandatory attachments
    - tags: Filter by tags (comma-separated)
    - search: Search in title and description
    """
    
    # Swagger tags for grouping
    swagger_tags = ['Document Management - Attachments']
    
    # Only multipart/form-data for file uploads
    parser_classes = [MultiPartParser, FormParser]
    
    permission_classes = [IsAuthenticated, AttachmentAccessPermission]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_class = AttachmentFilter
    search_fields = ['title', 'description', 'tags']
    ordering_fields = ['created_at', 'updated_at', 'title', 'expiry_date']
    ordering = ['-created_at']
    
    def get_queryset(self):
        """
        Filter queryset based on user role.
        - Admin/Superuser: See all attachments
        - Regular users: See only attachments assigned to them
        """
        # Return empty queryset for Swagger schema generation
        if getattr(self, 'swagger_fake_view', False):
            return Attachment.objects.none()
        
        user = self.request.user
        
        # Return empty queryset for unauthenticated users
        if not user or not user.is_authenticated:
            return Attachment.objects.none()
        
        # Optimize queries
        queryset = Attachment.objects.select_related('created_by').prefetch_related(
            'assigned_users',
            Prefetch(
                'assignments',
                queryset=AttachmentAssignment.objects.select_related('user', 'assigned_by')
            )
        )
        
        # Admins see everything
        if user.is_superuser or user.is_staff:
            return queryset
        
        # Regular users see only assigned attachments
        return queryset.filter(assigned_users=user)
    
    def get_serializer_class(self):
        """Return appropriate serializer based on action."""
        if self.action == 'list':
            return AttachmentListSerializer
        elif self.action in ['create', 'update', 'partial_update']:
            return AttachmentCreateUpdateSerializer
        return AttachmentDetailSerializer
    
    @swagger_auto_schema(
        tags=['📎 Document Management - Attachments'],
        operation_description='List all attachments. Admins see all, users see only assigned attachments.',
        manual_parameters=[
            openapi.Parameter('status', openapi.IN_QUERY, description="Filter by status (active, archived, expired)", type=openapi.TYPE_STRING),
            openapi.Parameter('file_type', openapi.IN_QUERY, description="Filter by file type (pdf, doc, docx, jpg, png)", type=openapi.TYPE_STRING),
            openapi.Parameter('is_mandatory', openapi.IN_QUERY, description="Filter mandatory attachments", type=openapi.TYPE_BOOLEAN),
            openapi.Parameter('search', openapi.IN_QUERY, description="Search in title, description, tags", type=openapi.TYPE_STRING),
            openapi.Parameter('ordering', openapi.IN_QUERY, description="Order by field (e.g., -created_at)", type=openapi.TYPE_STRING),
        ]
    )
    def list(self, request, *args, **kwargs):
        """List attachments with filtering and search."""
        return super().list(request, *args, **kwargs)
    
    def create(self, request, *args, **kwargs):
        """Create a new attachment with file upload (multipart/form-data)."""
        return super().create(request, *args, **kwargs)
    
    def retrieve(self, request, *args, **kwargs):
        """Retrieve attachment details."""
        return super().retrieve(request, *args, **kwargs)
    
    def update(self, request, *args, **kwargs):
        """Update attachment with file upload (multipart/form-data)."""
        return super().update(request, *args, **kwargs)
    
    def partial_update(self, request, *args, **kwargs):
        """Partial update attachment (multipart/form-data)."""
        return super().partial_update(request, *args, **kwargs)
    
    @swagger_auto_schema(
        tags=['📎 Document Management - Attachments'],
        operation_description='Delete an attachment. Only creator or admin can delete.'
    )
    def destroy(self, request, *args, **kwargs):
        """Delete attachment."""
        return super().destroy(request, *args, **kwargs)
    
    def perform_create(self, serializer):
        """Set created_by when creating attachment."""
        serializer.save(created_by=self.request.user)
    
    @swagger_auto_schema(
        method='post',
        tags=['📎 Document Management - Attachments'],
        request_body=AttachmentAssignmentBulkSerializer,
        responses={
            200: openapi.Response('Successfully assigned', AttachmentAssignmentSerializer(many=True)),
            400: 'Bad Request',
            403: 'Forbidden',
            404: 'Not Found',
        },
        operation_description='Assign this attachment to multiple users. Requires admin or assign permission.'
    )
    @action(
        detail=True,
        methods=['post'],
        permission_classes=[IsAuthenticated, CanAssignAttachment],
        url_path='assign-users'
    )
    def assign_users(self, request, pk=None):
        """
        Assign attachment to multiple users.
        
        Body:
        {
            "user_ids": [1, 2, 3, 4]
        }
        """
        attachment = self.get_object()
        serializer = AttachmentAssignmentBulkSerializer(data=request.data)
        
        if serializer.is_valid():
            user_ids = serializer.validated_data['user_ids']
            
            # Create assignments (skip duplicates)
            created_assignments = []
            for user_id in user_ids:
                assignment, created = AttachmentAssignment.objects.get_or_create(
                    attachment=attachment,
                    user_id=user_id,
                    defaults={'assigned_by': request.user}
                )
                if created:
                    created_assignments.append(assignment)
            
            return Response({
                'message': f'Assigned to {len(created_assignments)} new user(s)',
                'total_assigned': attachment.assigned_users.count(),
                'assignments': AttachmentAssignmentSerializer(created_assignments, many=True).data
            }, status=status.HTTP_200_OK)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @swagger_auto_schema(
        method='post',
        tags=['📎 Document Management - Attachments'],
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'user_ids': openapi.Schema(
                    type=openapi.TYPE_ARRAY,
                    items=openapi.Schema(type=openapi.TYPE_INTEGER),
                    description='List of user IDs to remove assignment from'
                )
            }
        ),
        responses={200: 'Successfully removed assignments'},
        operation_description='Remove assignment of this attachment from specified users.'
    )
    @action(
        detail=True,
        methods=['post'],
        permission_classes=[IsAuthenticated, CanAssignAttachment],
        url_path='unassign-users',
        parser_classes=[JSONParser]
    )
    def unassign_users(self, request, pk=None):
        """
        Remove attachment assignment from specified users.
        
        Body:
        {
            "user_ids": [1, 2, 3]
        }
        """
        attachment = self.get_object()
        user_ids = request.data.get('user_ids', [])
        
        if not user_ids:
            return Response(
                {'error': 'user_ids field is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        deleted_count = AttachmentAssignment.objects.filter(
            attachment=attachment,
            user_id__in=user_ids
        ).delete()[0]
        
        return Response({
            'message': f'Removed {deleted_count} assignment(s)',
            'total_assigned': attachment.assigned_users.count()
        }, status=status.HTTP_200_OK)
    
    @swagger_auto_schema(
        method='get',
        tags=['📎 Document Management - Attachments'],
        responses={
            200: openapi.Response('File download', schema=openapi.Schema(type=openapi.TYPE_FILE)),
            403: 'Forbidden - Not assigned to you',
            404: 'Not Found',
        },
        operation_description='Download the attachment file. Tracks download count and logs access.'
    )
    @action(detail=True, methods=['get'], url_path='download')
    def download(self, request, pk=None):
        """
        Download attachment file.
        Marks as viewed and increments download counter.
        """
        attachment = self.get_object()
        user = request.user
        
        # Get or verify assignment
        if not (user.is_superuser or user.is_staff):
            try:
                assignment = AttachmentAssignment.objects.get(
                    attachment=attachment,
                    user=user
                )
            except AttachmentAssignment.DoesNotExist:
                return Response(
                    {'error': 'This attachment is not assigned to you'},
                    status=status.HTTP_403_FORBIDDEN
                )
        else:
            # For admins, create a virtual tracking (optional)
            assignment, created = AttachmentAssignment.objects.get_or_create(
                attachment=attachment,
                user=user,
                defaults={'assigned_by': user}
            )
        
        # Mark as viewed
        assignment.mark_as_viewed()
        
        # Increment download count
        assignment.increment_download_count()
        
        # Log download
        AttachmentDownloadLog.objects.create(
            assignment=assignment,
            ip_address=get_client_ip(request),
            user_agent=request.META.get('HTTP_USER_AGENT', '')
        )
        
        # Serve file
        try:
            response = FileResponse(
                attachment.file.open('rb'),
                content_type='application/octet-stream'
            )
            response['Content-Disposition'] = f'attachment; filename="{attachment.file.name.split("/")[-1]}"'
            return response
        except Exception as e:
            raise Http404(f"File not found: {str(e)}")
    
    @swagger_auto_schema(
        method='post',
        tags=['📎 Document Management - Attachments'],
        request_body=AttachmentAcknowledgeSerializer,
        responses={200: 'Acknowledged successfully'},
        operation_description='Acknowledge that you have received/read this attachment.'
    )
    @action(detail=True, methods=['post'], url_path='acknowledge')
    def acknowledge_attachment(self, request, pk=None):
        """
        Mark attachment as acknowledged by current user.
        """
        attachment = self.get_object()
        user = request.user
        
        try:
            assignment = AttachmentAssignment.objects.get(
                attachment=attachment,
                user=user
            )
        except AttachmentAssignment.DoesNotExist:
            return Response(
                {'error': 'This attachment is not assigned to you'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        serializer = AttachmentAcknowledgeSerializer(data=request.data)
        if serializer.is_valid():
            assignment.acknowledged = serializer.validated_data.get('acknowledged', True)
            assignment.acknowledged_at = timezone.now()
            assignment.notes = serializer.validated_data.get('notes', '')
            assignment.save()
            
            return Response({
                'message': 'Attachment acknowledged successfully',
                'acknowledged_at': assignment.acknowledged_at
            }, status=status.HTTP_200_OK)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @swagger_auto_schema(
        method='get',
        tags=['📎 Document Management - Attachments'],
        responses={200: AttachmentAssignmentSerializer(many=True)},
        operation_description='Get all assignments for this attachment (admin only).'
    )
    @action(
        detail=True,
        methods=['get'],
        permission_classes=[IsAuthenticated, CanAssignAttachment],
        url_path='assignments'
    )
    def list_assignments(self, request, pk=None):
        """
        List all user assignments for this attachment.
        Admin only.
        """
        attachment = self.get_object()
        assignments = attachment.assignments.select_related('user', 'assigned_by').all()
        serializer = AttachmentAssignmentSerializer(assignments, many=True)
        return Response(serializer.data)
    
    @swagger_auto_schema(
        method='get',
        tags=['📎 Document Management - Attachments'],
        responses={200: 'Statistics object'},
        operation_description='Get statistics for this attachment (admin only).'
    )
    @action(
        detail=True,
        methods=['get'],
        permission_classes=[IsAuthenticated, CanAssignAttachment],
        url_path='statistics'
    )
    def get_statistics(self, request, pk=None):
        """
        Get attachment statistics.
        Admin only.
        """
        attachment = self.get_object()
        assignments = attachment.assignments.all()
        
        stats = {
            'total_assigned': assignments.count(),
            'viewed_count': assignments.filter(viewed=True).count(),
            'not_viewed_count': assignments.filter(viewed=False).count(),
            'acknowledged_count': assignments.filter(acknowledged=True).count(),
            'total_downloads': sum(a.download_count for a in assignments),
            'created_at': attachment.created_at,
            'status': attachment.status,
            'is_expired': attachment.is_expired,
        }
        
        return Response(stats)
    
    @swagger_auto_schema(
        method='get',
        tags=['📎 Document Management - Attachments'],
        responses={200: AttachmentListSerializer(many=True)},
        operation_description='Get attachments assigned to current user only.'
    )
    @action(detail=False, methods=['get'], url_path='my-attachments')
    def my_attachments(self, request):
        """
        List attachments assigned to the current user.
        Shows personal tracking info.
        """
        user = request.user
        
        attachments = Attachment.objects.filter(
            assigned_users=user
        ).select_related('created_by').prefetch_related(
            Prefetch(
                'assignments',
                queryset=AttachmentAssignment.objects.filter(user=user)
            )
        )
        
        # Apply filters
        queryset = self.filter_queryset(attachments)
        
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = AttachmentListSerializer(
                page,
                many=True,
                context={'request': request}
            )
            return self.get_paginated_response(serializer.data)
        
        serializer = AttachmentListSerializer(
            queryset,
            many=True,
            context={'request': request}
        )
        return Response(serializer.data)


class AttachmentAssignmentViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for viewing attachment assignments.
    Read-only for regular users, admins can see all.
    """
    
    # Swagger tags for grouping
    swagger_tags = ['Document Management - Assignments']
    
    permission_classes = [IsAuthenticated]
    serializer_class = AttachmentAssignmentSerializer
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['viewed', 'acknowledged', 'user', 'attachment']
    ordering_fields = ['assigned_at', 'viewed_at', 'download_count']
    ordering = ['-assigned_at']
    
    def get_queryset(self):
        """
        Filter assignments based on user role.
        """
        # Return empty queryset for Swagger schema generation
        if getattr(self, 'swagger_fake_view', False):
            return AttachmentAssignment.objects.none()
        
        user = self.request.user
        
        # Return empty queryset for unauthenticated users
        if not user or not user.is_authenticated:
            return AttachmentAssignment.objects.none()
        
        queryset = AttachmentAssignment.objects.select_related(
            'attachment',
            'user',
            'assigned_by'
        )
        
        # Admins see all assignments
        if user.is_superuser or user.is_staff:
            return queryset
        
        # Regular users see only their own assignments
        return queryset.filter(user=user)    
    @swagger_auto_schema(
        tags=['📋 Document Management - Assignments'],
        operation_description='List attachment assignments. Admins see all, users see only their own assignments.',
        manual_parameters=[
            openapi.Parameter('viewed', openapi.IN_QUERY, description="Filter by viewed status", type=openapi.TYPE_BOOLEAN),
            openapi.Parameter('acknowledged', openapi.IN_QUERY, description="Filter by acknowledged status", type=openapi.TYPE_BOOLEAN),
            openapi.Parameter('attachment', openapi.IN_QUERY, description="Filter by attachment ID", type=openapi.TYPE_INTEGER),
            openapi.Parameter('user', openapi.IN_QUERY, description="Filter by user ID", type=openapi.TYPE_INTEGER),
        ]
    )
    def list(self, request, *args, **kwargs):
        """List assignments with filtering."""
        return super().list(request, *args, **kwargs)
    
    @swagger_auto_schema(
        tags=['📋 Document Management - Assignments'],
        operation_description='Get details of a specific attachment assignment.'
    )
    def retrieve(self, request, *args, **kwargs):
        """Retrieve assignment details."""
        return super().retrieve(request, *args, **kwargs)