from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from .models import Meeting
from .serializers import MeetingSerializer
from rest_framework import viewsets, filters, status
from .models import FieldDay
from .serializers import FieldDaySerializer
from FieldAdvisoryService.serializers import CompanySerializer, RegionSerializer, ZoneSerializer, TerritorySerializer,Company,Region,Zone,Territory

class MeetingViewSet(viewsets.ModelViewSet):
    # queryset = Meeting.objects.all()  # Use .filter(is_active=True) after adding the field
    queryset = Meeting.objects.select_related(
        'region_fk', 'zone_fk', 'territory_fk'
    ).all()
    serializer_class = MeetingSerializer
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    # Filters, search, ordering
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ["fsm_name", "region", "zone", "territory", "presence_of_zm_rsm", "location"]
    search_fields = [
        'fsm_name',
        'region_fk__name',
        'zone_fk__name',
        'territory_fk__name',
        'location',
        'key_topics_discussed',
    ]
    ordering_fields = ["date", "fsm_name", "region", "zone", "territory", "total_attendees"]
    
     # ---------------- Global Extra Data ----------------
    def finalize_response(self, request, response, *args, **kwargs):
        response = super().finalize_response(request, response, *args, **kwargs)

        # Add extra dropdown data only on success
        if response.status_code in [200, 201]:
            if isinstance(response.data, dict):
                response.data["companies"] = CompanySerializer(Company.objects.all(), many=True).data
                response.data["regions"] = RegionSerializer(Region.objects.all(), many=True).data
                response.data["zones"] = ZoneSerializer(Zone.objects.all(), many=True).data
                response.data["territories"] = TerritorySerializer(Territory.objects.all(), many=True).data

        return response
    
    # Define common parameters
    common_parameters = [
        openapi.Parameter('fsm_name', openapi.IN_FORM, type=openapi.TYPE_STRING, required=True,
                         description='Field Sales Manager name'),
        openapi.Parameter('territory', openapi.IN_FORM, type=openapi.TYPE_STRING, required=True,
                         description='Territory name'),
        openapi.Parameter('zone', openapi.IN_FORM, type=openapi.TYPE_STRING, required=True,
                         description='Zone name'),
        openapi.Parameter('region', openapi.IN_FORM, type=openapi.TYPE_STRING, required=True,
                         description='Region name'),
        openapi.Parameter('date', openapi.IN_FORM, type=openapi.TYPE_STRING, format='date', required=True,
                         description='Meeting date (YYYY-MM-DD)'),
        openapi.Parameter('location', openapi.IN_FORM, type=openapi.TYPE_STRING, required=True,
                         description='Meeting location'),
        openapi.Parameter('total_attendees', openapi.IN_FORM, type=openapi.TYPE_INTEGER, required=True,
                         description='Total number of attendees'),
        openapi.Parameter('key_topics_discussed', openapi.IN_FORM, type=openapi.TYPE_STRING, required=False,
                         description='Key topics discussed in the meeting'),
        openapi.Parameter('presence_of_zm_rsm', openapi.IN_FORM, type=openapi.TYPE_STRING, required=False,
                         description='Presence of ZM/RSM'),
        openapi.Parameter('feedback_from_attendees', openapi.IN_FORM, type=openapi.TYPE_STRING, required=False,
                         description='Feedback from attendees'),
        openapi.Parameter('suggestions_for_future', openapi.IN_FORM, type=openapi.TYPE_STRING, required=False,
                         description='Suggestions for future meetings'),
        openapi.Parameter('attachments', openapi.IN_FORM, type=openapi.TYPE_FILE, required=False,
                         description='File attachments (can upload multiple)'),
        
        # Multiple fields for attendees
        openapi.Parameter('attendee_name', openapi.IN_FORM, type=openapi.TYPE_ARRAY, 
                         items=openapi.Items(type=openapi.TYPE_STRING), required=False,
                         description='List of farmer names. Example: ["John Doe", "Jane Smith"]'),
        openapi.Parameter('attendee_contact', openapi.IN_FORM, type=openapi.TYPE_ARRAY,
                         items=openapi.Items(type=openapi.TYPE_STRING), required=False,
                         description='List of contact numbers. Example: ["123-456-7890", "098-765-4321"]'),
        openapi.Parameter('attendee_acreage', openapi.IN_FORM, type=openapi.TYPE_ARRAY,
                         items=openapi.Items(type=openapi.TYPE_NUMBER), required=False,
                         description='List of acreage values. Example: [5.5, 3.2]'),
        openapi.Parameter('attendee_crop', openapi.IN_FORM, type=openapi.TYPE_ARRAY,
                         items=openapi.Items(type=openapi.TYPE_STRING), required=False,
                         description='List of crops. Example: ["Wheat", "Corn"]'),
    ]

    # ---------------- List / Retrieve ----------------
    @swagger_auto_schema(
        tags=["Farmer Advisory Meeting"],
        operation_description="List all Farmer Meetings with filters, search, and ordering.",
        responses={200: MeetingSerializer(many=True)},
        manual_parameters=[
            openapi.Parameter('fsm_name', openapi.IN_QUERY, type=openapi.TYPE_STRING, required=False,
                            description='Filter by FSM name'),
            openapi.Parameter('region', openapi.IN_QUERY, type=openapi.TYPE_STRING, required=False,
                            description='Filter by region'),
            openapi.Parameter('zone', openapi.IN_QUERY, type=openapi.TYPE_STRING, required=False,
                            description='Filter by zone'),
            openapi.Parameter('territory', openapi.IN_QUERY, type=openapi.TYPE_STRING, required=False,
                            description='Filter by territory'),
            openapi.Parameter('location', openapi.IN_QUERY, type=openapi.TYPE_STRING, required=False,
                            description='Filter by location'),
            openapi.Parameter('presence_of_zm_rsm', openapi.IN_QUERY, type=openapi.TYPE_STRING, required=False,
                            description='Filter by ZM/RSM presence'),
        ]
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @swagger_auto_schema(
        tags=["Farmer Advisory Meeting"],
        operation_description="Retrieve a specific Farmer Meeting by ID.",
        responses={200: MeetingSerializer},
    )
    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)

    # ---------------- Create ----------------
    @swagger_auto_schema(
        tags=["Farmer Advisory Meeting"],
        operation_description="Create a new Farmer Meeting with attendees and file attachments.",
        manual_parameters=common_parameters,
        responses={201: MeetingSerializer}
    )
    def create(self, request, *args, **kwargs):
        return super().create(request, *args, **kwargs)

    # ---------------- Update ----------------
    @swagger_auto_schema(
        tags=["Farmer Advisory Meeting"],
        operation_description="Update an existing Farmer Meeting (attendees + files supported).",
        manual_parameters=common_parameters,
        responses={200: MeetingSerializer}
    )
    def update(self, request, *args, **kwargs):
        return super().update(request, *args, **kwargs)

    # ---------------- Partial Update ----------------
    @swagger_auto_schema(
        tags=["Farmer Advisory Meeting"],
        operation_description="Partial update of a Farmer Meeting.",
        manual_parameters=common_parameters,
        responses={200: MeetingSerializer}
    )
    def partial_update(self, request, *args, **kwargs):
        kwargs['partial'] = True
        return self.update(request, *args, **kwargs)

    # ---------------- Delete ----------------
    @swagger_auto_schema(
        tags=["Farmer Advisory Meeting"],
        operation_description="Delete a Farmer Meeting.",
        responses={204: "Meeting deleted"}
    )
    def destroy(self, request, *args, **kwargs):
        meeting = self.get_object()
        meeting.delete()
        return Response(
            {"detail": "Meeting deleted."}, 
            status=status.HTTP_204_NO_CONTENT
        )
        
# ------------------------------------------------
# Field Day ViewSet (similar structure to MeetingViewSet)
# ------------------------------------------------
class FieldDayViewSet(viewsets.ModelViewSet):
    queryset = FieldDay.objects.all()
    serializer_class = FieldDaySerializer
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    # Filters, search, ordering
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ["region", "zone", "territory", "location", "status"]
    search_fields = ["title", "region", "zone", "territory", "location", "objectives"]
    ordering_fields = ["date", "title", "region", "zone", "territory"]

    # ---------------- Common Parameters ----------------
    common_parameters = [
        openapi.Parameter('title', openapi.IN_FORM, type=openapi.TYPE_STRING, required=True,
                          description='Title of the Field Day'),
        openapi.Parameter('region', openapi.IN_FORM, type=openapi.TYPE_STRING, required=True,
                          description='Region name'),
        openapi.Parameter('zone', openapi.IN_FORM, type=openapi.TYPE_STRING, required=True,
                          description='Zone name'),
        openapi.Parameter('territory', openapi.IN_FORM, type=openapi.TYPE_STRING, required=True,
                          description='Territory name'),
        openapi.Parameter('date', openapi.IN_FORM, type=openapi.TYPE_STRING, format='date', required=True,
                          description='Field Day date (YYYY-MM-DD)'),
        openapi.Parameter('location', openapi.IN_FORM, type=openapi.TYPE_STRING, required=True,
                          description='Field Day location'),
        openapi.Parameter('objectives', openapi.IN_FORM, type=openapi.TYPE_STRING, required=False,
                          description='Objectives of the Field Day'),
        openapi.Parameter('remarks', openapi.IN_FORM, type=openapi.TYPE_STRING, required=False,
                          description='Remarks about the Field Day'),
        openapi.Parameter('status', openapi.IN_FORM, type=openapi.TYPE_STRING, required=False,
                          description='Status of the Field Day (draft, scheduled, completed)'),

        # Multiple attendees
        openapi.Parameter('attendee_name', openapi.IN_FORM, type=openapi.TYPE_ARRAY,
                          items=openapi.Items(type=openapi.TYPE_STRING), required=False,
                          description='List of farmer names. Example: ["Ali", "Ahmed"]'),
        openapi.Parameter('attendee_contact', openapi.IN_FORM, type=openapi.TYPE_ARRAY,
                          items=openapi.Items(type=openapi.TYPE_STRING), required=False,
                          description='List of contact numbers.'),
        openapi.Parameter('attendee_acreage', openapi.IN_FORM, type=openapi.TYPE_ARRAY,
                          items=openapi.Items(type=openapi.TYPE_NUMBER), required=False,
                          description='List of acreage values.'),
        openapi.Parameter('attendee_crop', openapi.IN_FORM, type=openapi.TYPE_ARRAY,
                          items=openapi.Items(type=openapi.TYPE_STRING), required=False,
                          description='List of crops.'),
    ]

    # ---------------- List ----------------
    @swagger_auto_schema(
        tags=["Field Day"],
        operation_description="List all Field Days with filters, search, and ordering.",
        responses={200: FieldDaySerializer(many=True)},
        manual_parameters=[
            openapi.Parameter('region', openapi.IN_QUERY, type=openapi.TYPE_STRING, required=False,
                              description='Filter by region'),
            openapi.Parameter('zone', openapi.IN_QUERY, type=openapi.TYPE_STRING, required=False,
                              description='Filter by zone'),
            openapi.Parameter('territory', openapi.IN_QUERY, type=openapi.TYPE_STRING, required=False,
                              description='Filter by territory'),
            openapi.Parameter('location', openapi.IN_QUERY, type=openapi.TYPE_STRING, required=False,
                              description='Filter by location'),
            openapi.Parameter('status', openapi.IN_QUERY, type=openapi.TYPE_STRING, required=False,
                              description='Filter by status'),
        ]
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    # ---------------- Retrieve ----------------
    @swagger_auto_schema(
        tags=["Field Day"],
        operation_description="Retrieve details of a specific Field Day by ID.",
        responses={200: FieldDaySerializer},
    )
    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)

    # ---------------- Create ----------------
    @swagger_auto_schema(
        tags=["Field Day"],
        operation_description="Create a new Field Day with attendees.",
        manual_parameters=common_parameters,
        responses={201: FieldDaySerializer}
    )
    def create(self, request, *args, **kwargs):
        return super().create(request, *args, **kwargs)

    # ---------------- Update ----------------
    @swagger_auto_schema(
        tags=["Field Day"],
        operation_description="Update a Field Day with attendees.",
        manual_parameters=common_parameters,
        responses={200: FieldDaySerializer}
    )
    def update(self, request, *args, **kwargs):
        return super().update(request, *args, **kwargs)

    # ---------------- Partial Update ----------------
    @swagger_auto_schema(
        tags=["Field Day"],
        operation_description="Partially update a Field Day.",
        manual_parameters=common_parameters,
        responses={200: FieldDaySerializer}
    )
    def partial_update(self, request, *args, **kwargs):
        kwargs['partial'] = True
        return self.update(request, *args, **kwargs)

    # ---------------- Delete ----------------
    @swagger_auto_schema(
        tags=["Field Day"],
        operation_description="Delete a Field Day.",
        responses={204: "Field Day deleted"}
    )
    def destroy(self, request, *args, **kwargs):
        field_day = self.get_object()
        field_day.delete()
        return Response({"detail": "Field Day deleted."}, status=status.HTTP_204_NO_CONTENT)
