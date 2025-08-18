from rest_framework import generics, filters, permissions
from django_filters.rest_framework import DjangoFilterBackend
from .models import Meeting
from .serializers import MeetingSerializer
from rest_framework.permissions import IsAuthenticated
from accounts.permissions import HasRolePermission

class MeetingCreateView(generics.CreateAPIView):
    queryset = Meeting.objects.all()
    serializer_class = MeetingSerializer
    # permission_classes = [permissions.IsAuthenticated]
    permission_classes = [IsAuthenticated, HasRolePermission]
    
class MeetingListView(generics.ListAPIView):
    queryset = Meeting.objects.all().order_by('-date')
    serializer_class = MeetingSerializer
    # permission_classes = [permissions.IsAuthenticated]
    permission_classes = [IsAuthenticated, HasRolePermission]
    filter_backends = [
        DjangoFilterBackend,
        filters.OrderingFilter,
        filters.SearchFilter,
    ]

    # ✅ Exact filters
    filterset_fields = [
        'fsm_name', 'region', 'zone', 'territory', 'presence_of_zm_rsm', 'location'
    ]

    # ✅ Fields that can be sorted (ascending/descending)
    ordering_fields = [
        'date', 'fsm_name', 'region', 'zone', 'territory', 'total_attendees'
    ]

    # ✅ Full-text search on string fields
    search_fields = [
        'fsm_name', 'region', 'zone', 'territory', 'location', 'key_topics_discussed'
    ]