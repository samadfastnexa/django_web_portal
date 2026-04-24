import django_filters
from django.db.models import Q
from .models import Attachment, AttachmentAssignment


class AttachmentFilter(django_filters.FilterSet):
    """
    Filter class for Attachment model.
    Supports filtering by status, creator, date ranges, and tags.
    """
    
    # Status filter
    status = django_filters.ChoiceFilter(
        choices=Attachment.STATUS_CHOICES,
        help_text='Filter by attachment status'
    )
    
    # Creator filter
    created_by = django_filters.NumberFilter(
        field_name='created_by__id',
        help_text='Filter by creator user ID'
    )
    
    # Boolean filters
    is_mandatory = django_filters.BooleanFilter(
        help_text='Filter mandatory attachments'
    )
    
    is_expired = django_filters.BooleanFilter(
        method='filter_expired',
        help_text='Filter expired attachments'
    )
    
    # Date filters
    created_after = django_filters.DateTimeFilter(
        field_name='created_at',
        lookup_expr='gte',
        help_text='Filter attachments created after this date'
    )
    
    created_before = django_filters.DateTimeFilter(
        field_name='created_at',
        lookup_expr='lte',
        help_text='Filter attachments created before this date'
    )
    
    expires_after = django_filters.DateTimeFilter(
        field_name='expiry_date',
        lookup_expr='gte',
        help_text='Filter attachments expiring after this date'
    )
    
    expires_before = django_filters.DateTimeFilter(
        field_name='expiry_date',
        lookup_expr='lte',
        help_text='Filter attachments expiring before this date'
    )
    
    # Tag filter (exact or contains)
    tags = django_filters.CharFilter(
        method='filter_tags',
        help_text='Filter by tags (comma-separated or single tag)'
    )
    
    # File type filter
    file_type = django_filters.CharFilter(
        help_text='Filter by file type (pdf, doc, docx, jpg, png)'
    )
    
    # Text search
    search = django_filters.CharFilter(
        method='filter_search',
        help_text='Search in title, description, and tags'
    )
    
    class Meta:
        model = Attachment
        fields = [
            'status',
            'created_by',
            'is_mandatory',
            'file_type',
        ]
    
    def filter_expired(self, queryset, name, value):
        """Filter expired or non-expired attachments."""
        from django.utils import timezone
        now = timezone.now()
        
        if value:
            # Show expired attachments
            return queryset.filter(
                Q(expiry_date__isnull=False) &
                Q(expiry_date__lt=now)
            )
        else:
            # Show non-expired attachments
            return queryset.filter(
                Q(expiry_date__isnull=True) |
                Q(expiry_date__gte=now)
            )
    
    def filter_tags(self, queryset, name, value):
        """Filter by tags (supports comma-separated values)."""
        if not value:
            return queryset
        
        # Split by comma and search for any matching tag
        tags = [tag.strip() for tag in value.split(',')]
        
        query = Q()
        for tag in tags:
            query |= Q(tags__icontains=tag)
        
        return queryset.filter(query)
    
    def filter_search(self, queryset, name, value):
        """Search across multiple fields."""
        if not value:
            return queryset
        
        return queryset.filter(
            Q(title__icontains=value) |
            Q(description__icontains=value) |
            Q(tags__icontains=value)
        )


class AttachmentAssignmentFilter(django_filters.FilterSet):
    """
    Filter class for AttachmentAssignment model.
    """
    
    viewed = django_filters.BooleanFilter(
        help_text='Filter by viewed status'
    )
    
    acknowledged = django_filters.BooleanFilter(
        help_text='Filter by acknowledged status'
    )
    
    attachment = django_filters.NumberFilter(
        field_name='attachment__id',
        help_text='Filter by attachment ID'
    )
    
    user = django_filters.NumberFilter(
        field_name='user__id',
        help_text='Filter by user ID'
    )
    
    assigned_after = django_filters.DateTimeFilter(
        field_name='assigned_at',
        lookup_expr='gte',
        help_text='Filter assignments created after this date'
    )
    
    assigned_before = django_filters.DateTimeFilter(
        field_name='assigned_at',
        lookup_expr='lte',
        help_text='Filter assignments created before this date'
    )
    
    has_downloads = django_filters.BooleanFilter(
        method='filter_has_downloads',
        help_text='Filter assignments with downloads'
    )
    
    class Meta:
        model = AttachmentAssignment
        fields = ['viewed', 'acknowledged', 'attachment', 'user']
    
    def filter_has_downloads(self, queryset, name, value):
        """Filter assignments that have been downloaded."""
        if value:
            return queryset.filter(download_count__gt=0)
        else:
            return queryset.filter(download_count=0)
