"""
API for HPM (High Profile Meeting) requisitions.

Serializer + ViewSet live together in their own module rather than being added
to the already-large serializers.py / views.py.

Status is never writable through the normal create/update path - it changes only
via the explicit `approve` / `reject` actions, which are gated on the grantable
`approve_hpmrequisition` permission and stamp who decided and when. (The one
pre-existing approve endpoint in this project,
attendance.views.AttendanceRequestViewSet.approve, never records the approver -
that is the mistake this avoids.)
"""
from django.utils import timezone
from rest_framework import filters, serializers, status, viewsets
from rest_framework.decorators import action
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from django_filters.rest_framework import DjangoFilterBackend
from drf_yasg import openapi
from drf_yasg.inspectors import SwaggerAutoSchema
from drf_yasg.utils import no_body, swagger_auto_schema

from .hpm_admin import can_approve_hpm
from .models import HPMRequisition

#: approve/reject take only this one optional field. Declared as IN_FORM (not a
#: request_body) because the ViewSet uses form parsers - mixing the two raises
#: "cannot add form parameters when the request has a request body".
CEO_REMARKS_PARAM = openapi.Parameter(
    'ceo_remarks', openapi.IN_FORM, required=False, type=openapi.TYPE_STRING,
    description="Approver's remarks. On reject, the reason. Optional.",
)

#: Swagger group. The project numbers its tags ("12. Farmer Advisory Meeting"
#: ... "25.") so they sort in the UI; existing tags stop at 25.
HPM_TAG = '26. HPM Requisition'


class _HPMAutoSchema(SwaggerAutoSchema):
    """Force every action onto one tag, including approve/reject.

    Cheaper than decorating each generated CRUD method with
    swagger_auto_schema(tags=...).
    """

    def get_tags(self, operation_keys=None):
        return [HPM_TAG]


class HPMRequisitionSerializer(serializers.ModelSerializer):
    """Writable `*_id` inputs plus read-only `*_name` echoes, as MeetingSerializer does."""

    company_id = serializers.PrimaryKeyRelatedField(
        source='company_fk', queryset=HPMRequisition._meta.get_field('company_fk').related_model.objects.all(),
        required=False, allow_null=True,
    )
    region_id = serializers.PrimaryKeyRelatedField(
        source='region_fk', queryset=HPMRequisition._meta.get_field('region_fk').related_model.objects.all(),
        required=False, allow_null=True,
    )
    zone_id = serializers.PrimaryKeyRelatedField(
        source='zone_fk', queryset=HPMRequisition._meta.get_field('zone_fk').related_model.objects.all(),
        required=False, allow_null=True,
    )
    territory_id = serializers.PrimaryKeyRelatedField(
        source='territory_fk', queryset=HPMRequisition._meta.get_field('territory_fk').related_model.objects.all(),
        required=False, allow_null=True,
    )

    company_name = serializers.CharField(source='company_fk.Company_name', read_only=True)
    region_name = serializers.CharField(source='region_fk.name', read_only=True)
    zone_name = serializers.CharField(source='zone_fk.name', read_only=True)
    territory_name = serializers.CharField(source='territory_fk.name', read_only=True)
    submitted_by_name = serializers.CharField(source='submitted_by.username', read_only=True)
    responsible_person_name = serializers.CharField(
        source='responsible_person.username', read_only=True,
    )
    reviewed_by_name = serializers.CharField(source='reviewed_by.username', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)

    class Meta:
        model = HPMRequisition
        fields = [
            'id',
            'requisition_date',
            'submitted_by', 'submitted_by_name', 'submitted_at',
            'company_id', 'company_name',
            'region_id', 'region_name',
            'zone_id', 'zone_name',
            'territory_id', 'territory_name',
            'responsible_person', 'responsible_person_name',
            'meeting_date', 'meeting_location', 'expected_attendees',
            'purpose', 'remarks',
            'status', 'status_display', 'ceo_remarks',
            'reviewed_by', 'reviewed_by_name', 'reviewed_at',
            'is_active', 'created_at', 'updated_at',
        ]
        # The whole approval block is decided through the approve/reject actions,
        # never by a plain PATCH.
        read_only_fields = [
            'id', 'submitted_by', 'submitted_at', 'status', 'ceo_remarks',
            'reviewed_by', 'reviewed_at', 'created_at', 'updated_at',
        ]


class HPMRequisitionViewSet(viewsets.ModelViewSet):
    """Requisitions the caller is allowed to see, plus approve/reject actions."""

    serializer_class = HPMRequisitionSerializer
    permission_classes = [IsAuthenticated]
    swagger_schema = _HPMAutoSchema
    # Form data, matching MeetingViewSet / FieldDayViewSet. JSONParser is
    # deliberately omitted: with a JSON parser in the list drf-yasg renders the
    # body as one JSON blob instead of individual form fields, and mixing the two
    # raises "cannot add form parameters when the request has a request body".
    parser_classes = [MultiPartParser, FormParser]
    queryset = HPMRequisition.objects.select_related(
        'submitted_by', 'reviewed_by', 'responsible_person',
        'company_fk', 'region_fk', 'zone_fk', 'territory_fk',
    )
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['status', 'region_fk', 'zone_fk', 'territory_fk', 'submitted_by']
    search_fields = ['id', 'meeting_location', 'purpose', 'remarks']
    ordering_fields = ['requisition_date', 'meeting_date', 'id']
    ordering = ['-id']

    def get_queryset(self):
        """Own requisitions plus those of anyone below the caller in the chain.

        Mirrors the reporting-chain rule used for farmers: a manager sees their
        subordinates' requisitions. Fails closed - a user with no sales profile
        sees only their own.
        """
        qs = super().get_queryset()
        user = self.request.user
        if user.is_superuser or user.is_staff:
            return qs

        allowed = {user.pk}
        profile = getattr(user, 'sales_profile', None)
        if profile is not None:
            try:
                for sub in profile.get_all_subordinates(include_self=False):
                    if sub.user_id:
                        allowed.add(sub.user_id)
            except Exception:
                # Never widen the queryset because the hierarchy walk failed.
                pass
        return qs.filter(submitted_by_id__in=allowed)

    def perform_create(self, serializer):
        serializer.save(
            submitted_by=self.request.user,
            submitted_at=timezone.now(),
            status=HPMRequisition.STATUS_PENDING,
        )

    def _decide(self, request, decision):
        obj = self.get_object()
        if not can_approve_hpm(request.user):
            return Response(
                {'detail': 'You do not have permission to approve or reject '
                           'HPM requisitions.'},
                status=status.HTTP_403_FORBIDDEN,
            )
        if obj.status != HPMRequisition.STATUS_PENDING:
            return Response(
                {'detail': f'Already {obj.get_status_display().lower()}.',
                 'status': obj.status},
                status=status.HTTP_409_CONFLICT,
            )

        remarks = (request.data.get('ceo_remarks') or '').strip()
        obj.status = decision
        obj.reviewed_by = request.user
        obj.reviewed_at = timezone.now()
        if remarks:
            obj.ceo_remarks = remarks
        obj.save(update_fields=[
            'status', 'ceo_remarks', 'reviewed_by', 'reviewed_at', 'updated_at',
        ])
        return Response(self.get_serializer(obj).data, status=status.HTTP_200_OK)

    @swagger_auto_schema(
        operation_summary='Approve a pending HPM requisition',
        operation_description=(
            'Requires the "Can approve or reject HPM requisitions" permission '
            '(`approve_hpmrequisition`). Stamps the approver and the timestamp. '
            'Returns 409 if the requisition has already been decided.'
        ),
        # no_body stops drf-yasg inferring the whole HPMRequisition serializer as
        # form fields here; these actions take nothing but ceo_remarks.
        request_body=no_body,
        manual_parameters=[CEO_REMARKS_PARAM],
        responses={200: HPMRequisitionSerializer, 403: 'No approval permission',
                   409: 'Already decided'},
    )
    @action(detail=True, methods=['post'])
    def approve(self, request, pk=None):
        return self._decide(request, HPMRequisition.STATUS_APPROVED)

    @swagger_auto_schema(
        operation_summary='Reject a pending HPM requisition',
        operation_description=(
            'Requires the "Can approve or reject HPM requisitions" permission '
            '(`approve_hpmrequisition`). Send ceo_remarks to record the reason.'
        ),
        # no_body stops drf-yasg inferring the whole HPMRequisition serializer as
        # form fields here; these actions take nothing but ceo_remarks.
        request_body=no_body,
        manual_parameters=[CEO_REMARKS_PARAM],
        responses={200: HPMRequisitionSerializer, 403: 'No approval permission',
                   409: 'Already decided'},
    )
    @action(detail=True, methods=['post'])
    def reject(self, request, pk=None):
        return self._decide(request, HPMRequisition.STATUS_REJECTED)
