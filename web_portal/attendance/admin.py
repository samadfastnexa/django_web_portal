import datetime

from django.contrib import admin
from django.conf import settings
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.utils.html import format_html

from web_portal.admin import admin_site
from .models import Attendance, AttendanceRequest, LeaveRequest

User = get_user_model()


def _today_bounds():
    """Start (inclusive) and end (exclusive) of today as aware datetimes.

    Built in Python on purpose: a `__date` lookup would compile to MySQL
    CONVERT_TZ(), which fails on this server (no timezone tables loaded).
    """
    today = timezone.localdate()
    start = datetime.datetime.combine(today, datetime.time.min)
    end = start + datetime.timedelta(days=1)
    if settings.USE_TZ:
        start = timezone.make_aware(start)
        end = timezone.make_aware(end)
    return today, start, end


@admin.register(Attendance, site=admin_site)
class AttendanceAdmin(admin.ModelAdmin):
    list_display = ('attendee', 'user', 'check_in_time', 'check_out_time', 'source')
    list_filter = ('source', 'created_at')
    search_fields = ('attendee__username', 'user__username')

    change_list_template = 'admin/attendance/attendance/change_list.html'

    def _attendance_stats(self):
        """Today's present/off counts for the sales-staff pool."""
        today, start, end = _today_bounds()

        # Present = attended today, i.e. any check-in OR check-out today. Using
        # the union avoids the contradiction where a late/overnight shift shows
        # a check-out today but its check-in fell outside today's window.
        attended_ids = set(
            Attendance.objects.filter(check_in_time__gte=start, check_in_time__lt=end)
            .values_list('attendee_id', flat=True)
        ) | set(
            Attendance.objects.filter(check_out_time__gte=start, check_out_time__lt=end)
            .values_list('attendee_id', flat=True)
        )

        # Only sales staff mark attendance (via the mobile attendance API), so
        # the expected pool is active sales staff. Superusers are excluded (an
        # admin account is not a field salesperson), and this already excludes
        # the ~1700 farmer/dealer accounts that would otherwise count as "Off".
        pool_ids = set(
            User.objects.filter(is_active=True, is_sales_staff=True, is_superuser=False)
            .values_list('pk', flat=True)
        )
        total = len(pool_ids)
        present = len(pool_ids & attended_ids)
        return {
            'date': today,
            'total': total,
            'present': present,
            'off': max(total - present, 0),
        }

    def changelist_view(self, request, extra_context=None):
        extra_context = extra_context or {}
        extra_context['attendance_summary'] = self._attendance_stats()
        return super().changelist_view(request, extra_context=extra_context)

    def get_export_summary(self, request):
        """Summary block prepended to CSV/Excel exports (see admin_export)."""
        stats = self._attendance_stats()
        return {
            'title': f'Attendance summary — {stats["date"]}',
            'rows': [
                ('Present today', stats['present']),
                ('Off today', stats['off']),
                ('Sales staff', stats['total']),
            ],
        }




@admin.register(AttendanceRequest, site=admin_site)
class AttendanceRequestAdmin(admin.ModelAdmin):
    list_display = ['user', 'check_type', 'attendance', 'created_at']
    fields = ['user', 'check_type', 'check_in_time', 'check_out_time', 'reason', 'attendance']

    def save_model(self, request, obj, form, change):
        # Custom logic to auto-create/update Attendance
        user = obj.user
        check_type = obj.check_type
        check_in_time = obj.check_in_time
        check_out_time = obj.check_out_time

        # Use check_in_time or check_out_time to detect date
        target_date = check_in_time.date() if check_type == 'check_in' and check_in_time else \
                      check_out_time.date() if check_out_time else None

        if target_date:
            attendance = Attendance.objects.filter(
                attendee=user,
                check_in_time__date=target_date
            ).first()

            if attendance:
                if check_type == 'check_in':
                    attendance.check_in_time = check_in_time
                elif check_type == 'check_out':
                    attendance.check_out_time = check_out_time
                attendance.source = 'request'
                attendance.save()
            else:
                attendance = Attendance.objects.create(
                    user=user,
                    attendee=user,
                    check_in_time=check_in_time if check_type == 'check_in' else None,
                    check_out_time=check_out_time if check_type == 'check_out' else None,
                    source='request'
                )

            obj.attendance = attendance

        super().save_model(request, obj, form, change)

@admin.register(LeaveRequest, site=admin_site)
class LeaveRequestAdmin(admin.ModelAdmin):
    list_display = (
        'id', 'user', 'leave_type', 'start_date', 'end_date',
        'days', 'status_badge', 'created_at',
    )
    list_filter = ('status', 'leave_type', 'created_at')
    search_fields = (
        'user__username', 'user__email', 'user__first_name', 'user__last_name', 'reason',
    )
    autocomplete_fields = ('user',)
    ordering = ('-created_at',)
    list_per_page = 25
    actions = ('mark_approved', 'mark_rejected')
    change_list_template = 'admin/attendance/leaverequest/change_list.html'

    def _leave_stats(self):
        """Status breakdown + who's on leave today. start/end are DateFields,
        so these plain date comparisons don't hit the MySQL CONVERT_TZ issue."""
        today = timezone.localdate()
        qs = LeaveRequest.objects.all()
        return {
            'total': qs.count(),
            'pending': qs.filter(status='pending').count(),
            'approved': qs.filter(status='approved').count(),
            'rejected': qs.filter(status='rejected').count(),
            'on_leave_today': qs.filter(
                status='approved', start_date__lte=today, end_date__gte=today
            ).count(),
        }

    def changelist_view(self, request, extra_context=None):
        extra_context = extra_context or {}
        extra_context['leave_summary'] = self._leave_stats()
        return super().changelist_view(request, extra_context=extra_context)

    def get_export_summary(self, request):
        """Summary block prepended to CSV/Excel exports (see admin_export)."""
        s = self._leave_stats()
        return {
            'title': 'Leave requests summary',
            'rows': [
                ('Pending', s['pending']),
                ('Approved', s['approved']),
                ('Rejected', s['rejected']),
                ('On leave today', s['on_leave_today']),
                ('Total', s['total']),
            ],
        }

    @admin.display(description='Days')
    def days(self, obj):
        try:
            return (obj.end_date - obj.start_date).days + 1
        except Exception:
            return ''

    @admin.display(description='Status', ordering='status')
    def status_badge(self, obj):
        colours = {
            'pending': ('#ffedd5', '#9a3412'),
            'approved': ('#dcfce7', '#166534'),
            'rejected': ('#fee2e2', '#991b1b'),
        }
        bg, fg = colours.get(obj.status, ('#e5e7eb', '#374151'))
        return format_html(
            '<span style="background:{};color:{};padding:2px 8px;'
            'border-radius:10px;font-weight:600;font-size:12px;">{}</span>',
            bg, fg, obj.get_status_display(),
        )

    # .update() bypasses the model's quota clean() on purpose: an approval/
    # rejection is a status change, not a new leave that should re-check quota.
    @admin.action(description='Approve selected leave requests')
    def mark_approved(self, request, queryset):
        updated = queryset.update(status='approved')
        self.message_user(request, f'{updated} leave request(s) approved.')

    @admin.action(description='Reject selected leave requests')
    def mark_rejected(self, request, queryset):
        updated = queryset.update(status='rejected')
        self.message_user(request, f'{updated} leave request(s) rejected.')
