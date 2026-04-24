from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.utils import timezone
from .models import Attachment, AttachmentAssignment, AttachmentDownloadLog

User = get_user_model()


class UserMinimalSerializer(serializers.ModelSerializer):
    """Minimal user serializer for nested representations."""
    
    class Meta:
        model = User
        fields = ['id', 'username', 'first_name', 'last_name', 'email']
        read_only_fields = fields


class AttachmentAssignmentSerializer(serializers.ModelSerializer):
    """Serializer for attachment assignments."""
    
    user_details = UserMinimalSerializer(source='user', read_only=True)
    assigned_by_details = UserMinimalSerializer(source='assigned_by', read_only=True)
    attachment_title = serializers.CharField(source='attachment.title', read_only=True)
    
    class Meta:
        model = AttachmentAssignment
        fields = [
            'id',
            'attachment',
            'attachment_title',
            'user',
            'user_details',
            'assigned_by',
            'assigned_by_details',
            'assigned_at',
            'viewed',
            'viewed_at',
            'download_count',
            'last_downloaded_at',
            'acknowledged',
            'acknowledged_at',
            'notes',
        ]
        read_only_fields = [
            'id',
            'assigned_by',
            'assigned_at',
            'viewed',
            'viewed_at',
            'download_count',
            'last_downloaded_at',
        ]


class AttachmentAssignmentBulkSerializer(serializers.Serializer):
    """Serializer for bulk assignment operations."""
    
    user_ids = serializers.ListField(
        child=serializers.IntegerField(),
        allow_empty=False,
        help_text='List of user IDs to assign this attachment to'
    )
    
    def validate_user_ids(self, value):
        """Validate that all user IDs exist."""
        existing_users = User.objects.filter(id__in=value).values_list('id', flat=True)
        missing_ids = set(value) - set(existing_users)
        
        if missing_ids:
            raise serializers.ValidationError(
                f"The following user IDs do not exist: {', '.join(map(str, missing_ids))}"
            )
        
        return value


class AttachmentListSerializer(serializers.ModelSerializer):
    """
    Lightweight serializer for listing attachments.
    Used in list views to avoid unnecessary data transfer.
    """
    
    created_by_name = serializers.SerializerMethodField()
    assigned_count = serializers.SerializerMethodField()
    is_expired = serializers.ReadOnlyField()
    formatted_file_size = serializers.ReadOnlyField()
    
    class Meta:
        model = Attachment
        fields = [
            'id',
            'title',
            'description',
            'file',
            'file_type',
            'formatted_file_size',
            'status',
            'created_by',
            'created_by_name',
            'created_at',
            'updated_at',
            'expiry_date',
            'is_expired',
            'is_mandatory',
            'tags',
            'assigned_count',
        ]
        read_only_fields = [
            'id',
            'created_by',
            'created_at',
            'updated_at',
            'file_type',
        ]
    
    def get_created_by_name(self, obj):
        """Get creator's full name or username."""
        if obj.created_by:
            return obj.created_by.get_full_name() or obj.created_by.username
        return "Unknown"
    
    def get_assigned_count(self, obj):
        """Get count of assigned users."""
        return obj.assigned_users.count()


class AttachmentDetailSerializer(serializers.ModelSerializer):
    """
    Detailed serializer for single attachment views.
    Includes assignment details and tracking information.
    """
    
    created_by_details = UserMinimalSerializer(source='created_by', read_only=True)
    assignments = serializers.SerializerMethodField()
    is_expired = serializers.ReadOnlyField()
    formatted_file_size = serializers.ReadOnlyField()
    file_extension = serializers.ReadOnlyField()
    
    # User-specific fields (for assigned users)
    user_viewed = serializers.SerializerMethodField()
    user_download_count = serializers.SerializerMethodField()
    user_acknowledged = serializers.SerializerMethodField()
    
    class Meta:
        model = Attachment
        fields = [
            'id',
            'title',
            'description',
            'file',
            'file_size',
            'formatted_file_size',
            'file_type',
            'file_extension',
            'status',
            'expiry_date',
            'is_expired',
            'is_mandatory',
            'tags',
            'created_by',
            'created_by_details',
            'created_at',
            'updated_at',
            'assignments',
            'user_viewed',
            'user_download_count',
            'user_acknowledged',
        ]
        read_only_fields = [
            'id',
            'created_by',
            'created_at',
            'updated_at',
            'file_size',
            'file_type',
        ]
    
    def get_assignments(self, obj):
        """Get assignment details (admin only or limited for users)."""
        request = self.context.get('request')
        
        # Admins see all assignments
        if request and (request.user.is_staff or request.user.is_superuser):
            assignments = obj.assignments.select_related('user', 'assigned_by').all()
            return AttachmentAssignmentSerializer(assignments, many=True).data
        
        # Regular users see only their own assignment
        if request and request.user.is_authenticated:
            assignment = obj.assignments.filter(user=request.user).first()
            if assignment:
                return [AttachmentAssignmentSerializer(assignment).data]
        
        return []
    
    def get_user_viewed(self, obj):
        """Check if current user has viewed this attachment."""
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            assignment = obj.assignments.filter(user=request.user).first()
            return assignment.viewed if assignment else False
        return False
    
    def get_user_download_count(self, obj):
        """Get download count for current user."""
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            assignment = obj.assignments.filter(user=request.user).first()
            return assignment.download_count if assignment else 0
        return 0
    
    def get_user_acknowledged(self, obj):
        """Check if current user has acknowledged this attachment."""
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            assignment = obj.assignments.filter(user=request.user).first()
            return assignment.acknowledged if assignment else False
        return False


class AttachmentCreateUpdateSerializer(serializers.ModelSerializer):
    """
    Serializer for creating and updating attachments.
    Includes file validation.
    Note: To assign users, use the separate /assign-users/ endpoint.
    """
    
    class Meta:
        model = Attachment
        fields = [
            'id',
            'title',
            'description',
            'file',
            'status',
            'expiry_date',
            'is_mandatory',
            'tags',
        ]
        read_only_fields = ['id']
    
    def validate_file(self, value):
        """Validate file type and size."""
        if not value:
            return value
        
        # Validate file extension
        allowed_extensions = ['pdf', 'doc', 'docx', 'jpg', 'jpeg', 'png']
        ext = value.name.split('.')[-1].lower()
        
        if ext not in allowed_extensions:
            raise serializers.ValidationError(
                f"File type '.{ext}' is not supported. "
                f"Allowed types: {', '.join(allowed_extensions)}"
            )
        
        # Validate file size (10MB max)
        max_size = 10 * 1024 * 1024  # 10MB in bytes
        if value.size > max_size:
            raise serializers.ValidationError(
                f"File size ({value.size} bytes) exceeds maximum allowed size (10MB)."
            )
        
        return value
    
    def validate_expiry_date(self, value):
        """Ensure expiry date is in the future."""
        if value and value < timezone.now():
            raise serializers.ValidationError("Expiry date must be in the future.")
        return value
    
    def create(self, validated_data):
        """Create attachment. Use /assign-users/ endpoint to assign users."""
        attachment = Attachment.objects.create(**validated_data)
        return attachment
    
    def update(self, instance, validated_data):
        """Update attachment fields. Use /assign-users/ endpoint to change assignments."""
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        return instance


class AttachmentDownloadLogSerializer(serializers.ModelSerializer):
    """Serializer for download logs."""
    
    user_username = serializers.CharField(source='assignment.user.username', read_only=True)
    attachment_title = serializers.CharField(source='assignment.attachment.title', read_only=True)
    
    class Meta:
        model = AttachmentDownloadLog
        fields = [
            'id',
            'assignment',
            'user_username',
            'attachment_title',
            'downloaded_at',
            'ip_address',
            'user_agent',
        ]
        read_only_fields = fields


class AttachmentAcknowledgeSerializer(serializers.Serializer):
    """Serializer for acknowledging attachment receipt."""
    
    acknowledged = serializers.BooleanField(default=True)
    notes = serializers.CharField(required=False, allow_blank=True, max_length=500)
