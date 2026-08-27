"""
Admin for HPM (High Profile Meeting) requisitions.

Kept in its own module rather than piled into the already-long admin.py, and
imported from there so autodiscovery still registers it.

The right to decide a requisition is the grantable `approve_hpmrequisition`
permission, not a designation code, so the business can move it between roles
without a code change.
"""
from django.contrib import admin, messages
from django.contrib.admin import widgets as admin_widgets
from django.utils import timezone
from django.utils.html import format_html

from web_portal.admin import admin_site
from web_portal.admin_export import HideGenericExportsMixin
from web_portal.admin_filters import date_range_filter, related_values_filter
from web_portal.form_pdf import form_pdf_action

from .hpm_report import PAGE_MARGIN_MM, requisition_story
from .models import HPMRequisition

APPROVE_HPM_PERM = 'farmerMeetingDataEntry.approve_hpmrequisition'

# Same "Export selected to PDF (form)" action as the other Field Activities
# sheets, but drawing the requisition's own layout - its approval and signature
# block has no equivalent in the generic Field / Description sheet.
export_hpm_to_pdf = form_pdf_action(
    requisition_story, 'Export selected to PDF (form)', 'hpm_requisitions',
    margin=PAGE_MARGIN_MM,
)


def can_approve_hpm(user):
    """True when `user` may approve or reject a requisition.

    Checks Django's own permission machinery *and* the project's role-permission
    table, because most users here carry permissions via `user.role` rather than
    groups.
    """
    if not user or not user.is_authenticated:
        return False
    if user.is_superuser:
        return True
    if user.has_perm(APPROVE_HPM_PERM):
        return True
    role = getattr(user, 'role', None)
    if role is not None:
        return role.permissions.filter(codename='approve_hpmrequisition').exists()
    return False


@admin.register(HPMRequisition, site=admin_site)
class HPMRequisitionAdmin(HideGenericExportsMixin, admin.ModelAdmin):
    """Raised by a manager, decided by an authorised approver."""

    list_display = (
        'id', 'requisition_date', 'submitted_by', 'region', 'zone',
        'territory', 'meeting_when', 'expected_attendees', 'status_badge',
    )
    list_filter = (
        'status',
        date_range_filter('meeting_date', 'meeting date'),
        related_values_filter('region', 'region'),
        related_values_filter('zone', 'zone'),
        related_values_filter('territory', 'territory'),
        related_values_filter('region_fk__name', 'region (legacy)'),
        related_values_filter('zone_fk__name', 'zone (legacy)'),
        related_values_filter('territory_fk__name', 'territory (legacy)'),
    )
    search_fields = (
        'id', 'meeting_location', 'purpose', 'remarks', 'ceo_remarks',
        'submitted_by__username', 'submitted_by__email',
        'responsible_person__username', 'responsible_person__email',
        'region', 'zone', 'territory', 'employee_code',
    )
    autocomplete_fields = ('submitted_by', 'responsible_person')
    ordering = ['-created_at', '-id']
    list_per_page = 25
    actions = ('approve_selected', 'reject_selected', export_hpm_to_pdf)
    # Only the CSV goes: unlike the other Field Activities sheets this one
    # has no Excel export of its own, so the site-wide one is the Excel.
    hide_generic_exports = ('export_as_csv',)
    change_form_template = 'admin/farmerMeetingDataEntry/hpmrequisition/change_form.html'

    # Mirrors the three boxes on the paper form. Note the GM/BM signature pair
    # belongs in the APPROVAL SECTION box on paper, not with the header - the
    # GM/BM signs as the *author* of the requisition, they do not approve it.
    # The CEO is the only approver, which is what `status` records.
    fieldsets = (
        ('Requisition', {
            'fields': ('id', 'requisition_date'),
        }),
        ('HPM Meeting Details', {
            'fields': (
                'company_fk', 'region_fk', 'zone_fk', 'territory_fk',
                'responsible_person', 'meeting_date', 'meeting_location',
                'expected_attendees', 'purpose', 'remarks',
            ),
        }),
        ('Approval Section', {
            'fields': (
                # GM/BM Signature + Date - stamped on submit, never typed.
                'submitted_by', 'submitted_at',
                # CEO Remarks / Signature + Date - stamped on the decision.
                'ceo_remarks', 'reviewed_by', 'reviewed_at',
                'status',
            ),
            'description': 'GM/BM signature is recorded when the requisition is '
                           'submitted. Only a user with the "Can approve or reject '
                           'HPM requisitions" permission can set the status or add '
                           'CEO remarks.',
        }),
    )

    # ---- display ----------------------------------------------------------
    @admin.display(description='Status', ordering='status')
    def status_badge(self, obj):
        colours = {
            HPMRequisition.STATUS_PENDING: ('#ffedd5', '#9a3412'),
            HPMRequisition.STATUS_APPROVED: ('#dcfce7', '#166534'),
            HPMRequisition.STATUS_REJECTED: ('#fee2e2', '#991b1b'),
        }
        bg, fg = colours.get(obj.status, ('#e5e7eb', '#374151'))
        return format_html(
            '<span style="background:{};color:{};padding:2px 8px;'
            'border-radius:10px;font-weight:600;font-size:12px;">{}</span>',
            bg, fg, obj.get_status_display(),
        )

    @admin.display(description='Meeting date & time', ordering='meeting_date')
    def meeting_when(self, obj):
        if not obj.meeting_date:
            return ''
        return timezone.localtime(obj.meeting_date).strftime('%d %b %Y %H:%M')

    def formfield_for_dbfield(self, db_field, request, **kwargs):
        # Separate date and time inputs, as MeetingAdmin does for Meeting.date.
        if db_field.name == 'meeting_date':
            kwargs['widget'] = admin_widgets.AdminSplitDateTime()
        return super().formfield_for_dbfield(db_field, request, **kwargs)

    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            'submitted_by', 'reviewed_by', 'responsible_person',
            'region_fk', 'zone_fk', 'territory_fk',
        )

    # ---- readonly rules ---------------------------------------------------
    def get_readonly_fields(self, request, obj=None):
        # Identity and both signature stamps are system-set, never typed.
        readonly = ['id', 'submitted_by', 'submitted_at', 'reviewed_by', 'reviewed_at',
                    # Resolved from the responsible person's employee code.
                    'employee_code', 'region', 'zone', 'territory', 'territory_code']
        if not can_approve_hpm(request.user):
            # A requester fills the form but must not decide their own request.
            readonly += ['status', 'ceo_remarks']
        return readonly

    def save_model(self, request, obj, form, change):
        """Stamp the submitter on add, and the approver on the deciding edge."""
        if not change:
            if not obj.submitted_by_id:
                obj.submitted_by = request.user
            if not obj.submitted_at:
                obj.submitted_at = timezone.now()
        else:
            previous = (
                HPMRequisition.objects.filter(pk=obj.pk)
                .values_list('status', flat=True).first()
            )
            # Only on pending -> decided, so re-saving a decided row never
            # rewrites who decided it or when.
            if previous == HPMRequisition.STATUS_PENDING and obj.status != previous:
                obj.reviewed_by = request.user
                obj.reviewed_at = timezone.now()
        super().save_model(request, obj, form, change)

    # ---- bulk actions -----------------------------------------------------
    def _decide(self, request, queryset, status, label):
        if not can_approve_hpm(request.user):
            self.message_user(
                request,
                'You do not have permission to approve or reject HPM requisitions.',
                messages.ERROR,
            )
            return
        # Restricted to pending rows so an existing decision is never overwritten.
        updated = queryset.filter(status=HPMRequisition.STATUS_PENDING).update(
            status=status, reviewed_by=request.user, reviewed_at=timezone.now(),
        )
        skipped = queryset.count() - updated
        msg = f'{updated} requisition(s) {label}.'
        if skipped:
            msg += f' {skipped} skipped (already decided).'
        self.message_user(request, msg, messages.SUCCESS)

    @admin.action(description='Approve selected HPM requisitions')
    def approve_selected(self, request, queryset):
        self._decide(request, queryset, HPMRequisition.STATUS_APPROVED, 'approved')

    @admin.action(description='Reject selected HPM requisitions')
    def reject_selected(self, request, queryset):
        self._decide(request, queryset, HPMRequisition.STATUS_REJECTED, 'rejected')

    # ---- per-object URLs --------------------------------------------------
    def get_urls(self):
        from django.urls import path

        custom = [
            path('<str:pk>/print/', self.admin_site.admin_view(self.print_pdf),
                 name='farmermeetingdataentry_hpmrequisition_print'),
            path('<str:pk>/decide/<str:decision>/',
                 self.admin_site.admin_view(self.decide_view),
                 name='farmermeetingdataentry_hpmrequisition_decide'),
        ]
        return custom + super().get_urls()

    def print_pdf(self, request, pk):
        from django.shortcuts import get_object_or_404

        from .hpm_report import render_requisition_pdf

        obj = get_object_or_404(self.get_queryset(request), pk=pk)
        return render_requisition_pdf(obj)

    def decide_view(self, request, pk, decision):
        """Approve or reject one requisition from its change form."""
        from django.shortcuts import get_object_or_404, redirect
        from django.urls import reverse

        obj = get_object_or_404(HPMRequisition, pk=pk)
        back = redirect(reverse(
            'admin:farmerMeetingDataEntry_hpmrequisition_change', args=[obj.pk]
        ))

        if decision not in (HPMRequisition.STATUS_APPROVED, HPMRequisition.STATUS_REJECTED):
            self.message_user(request, f'Unknown decision {decision!r}.', messages.ERROR)
            return back
        if not can_approve_hpm(request.user):
            self.message_user(
                request,
                'You do not have permission to approve or reject HPM requisitions.',
                messages.ERROR,
            )
            return back
        if obj.status != HPMRequisition.STATUS_PENDING:
            self.message_user(
                request,
                f'{obj.pk} is already {obj.get_status_display().lower()}; left unchanged.',
                messages.WARNING,
            )
            return back

        obj.status = decision
        obj.reviewed_by = request.user
        obj.reviewed_at = timezone.now()
        obj.save(update_fields=['status', 'reviewed_by', 'reviewed_at', 'updated_at'])
        self.message_user(
            request, f'{obj.pk} {obj.get_status_display().lower()}.', messages.SUCCESS,
        )
        return back

    def change_view(self, request, object_id, form_url='', extra_context=None):
        extra_context = extra_context or {}
        obj = HPMRequisition.objects.filter(pk=object_id).only('status').first()
        extra_context['can_approve_hpm'] = can_approve_hpm(request.user)
        extra_context['hpm_is_pending'] = bool(
            obj and obj.status == HPMRequisition.STATUS_PENDING
        )
        return super().change_view(request, object_id, form_url, extra_context)
