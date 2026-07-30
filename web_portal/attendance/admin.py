import datetime

from django.contrib import admin
from django.conf import settings
from django.contrib.auth import get_user_model
from django.db.models import Q
from django.utils import timezone
from django.utils.dateparse import parse_date, parse_datetime
from django.utils.html import format_html

from web_portal.admin import admin_site
from .models import Attendance, AttendanceRequest, Holiday, LeaveQuota, LeaveRequest, LeaveType
from .reports import build_rows, render_csv, render_pdf

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


def _scope_label(changelist):
    """The date filter option currently selected in the sidebar, verbatim.

    Reusing the sidebar's own wording ("Any date", "Today", "Past 7 days", ...)
    keeps the summary heading and the filter from contradicting each other.
    """
    for spec in getattr(changelist, 'filter_specs', None) or []:
        title = str(getattr(spec, 'title', '')).lower()
        if 'date' not in title and 'created' not in title:
            continue
        try:
            for choice in spec.choices(changelist):
                if choice.get('selected'):
                    return str(choice['display'])
        except Exception:
            continue
    return 'All dates'


def _tile_links(span, today):
    """Where each summary tile navigates to.

    `span` is the AttendanceMarkedFilter scope token for the page's current
    date filter ('all', a day, or 'start:end'). Passing the page's own scope is
    what keeps the destination count equal to the number on the card.

    Built here rather than in the template so the URLs are reversed (not
    hardcoded) and can be asserted in tests.
    """
    from urllib.parse import quote
    from django.urls import reverse

    users = reverse('admin:accounts_user_changelist')
    leave = reverse('admin:attendance_leaverequest_changelist')
    scope = quote(span, safe='')
    day = today.isoformat()
    return {
        'present': f'{users}?attendance=marked%3A{scope}',
        'off': f'{users}?attendance=not_marked%3A{scope}',
        # 'pool' rather than the plain flags: the tile excludes superusers.
        'total': f'{users}?attendance=pool',
        'leave_pending': f'{leave}?status__exact={LeaveRequest.STATUS_PENDING}',
        'leave_approved': f'{leave}?status__exact={LeaveRequest.STATUS_APPROVED}',
        'leave_rejected': f'{leave}?status__exact={LeaveRequest.STATUS_REJECTED}',
        'leave_today': f'{leave}?on_leave=on%3A{day}',
    }


class OnLeaveTodayFilter(admin.SimpleListFilter):
    """Approved leave covering a given day - the target of the tile link.

    A date range overlap cannot be expressed with the stock date filters, so
    the "On leave today" tile needs its own lookup. The value may carry the day
    ("on:2026-07-28"); a bare "on" means today.
    """
    title = 'on leave'
    parameter_name = 'on_leave'

    def lookups(self, request, model_admin):
        return (('on', 'On leave today'),)

    def queryset(self, request, queryset):
        raw = self.value()
        if not raw:
            return queryset
        mode, _, day = raw.partition(':')
        if mode != 'on':
            return queryset
        date = timezone.localdate()
        if day:
            try:
                date = datetime.date.fromisoformat(day)
            except ValueError:
                pass
        return queryset.filter(
            status=LeaveRequest.STATUS_APPROVED,
            start_date__lte=date,
            end_date__gte=date,
        )


def _leave_stats():
    """Leave-request status breakdown + who's on leave today.

    Shared by the Leave requests and the Attendance changelists - attendance is
    where you notice someone is missing, so the pending/approved queue belongs
    on both. start/end are DateFields, so these plain date comparisons don't hit
    the MySQL CONVERT_TZ issue described in _today_bounds().
    """
    today = timezone.localdate()
    qs = LeaveRequest.objects.all()
    return {
        'total': qs.count(),
        'pending': qs.filter(status=LeaveRequest.STATUS_PENDING).count(),
        'approved': qs.filter(status=LeaveRequest.STATUS_APPROVED).count(),
        'rejected': qs.filter(status=LeaveRequest.STATUS_REJECTED).count(),
        'on_leave_today': qs.filter(
            status=LeaveRequest.STATUS_APPROVED, start_date__lte=today, end_date__gte=today
        ).count(),
    }


@admin.register(Attendance, site=admin_site)
class AttendanceAdmin(admin.ModelAdmin):
    list_display = ('attendee_photo', 'attendee', 'user', 'check_in_time', 'check_in_photo',
                    'check_out_time', 'check_out_photo', 'source')
    list_filter = ('source', 'created_at')
    search_fields = ('attendee__username', 'user__username')
    readonly_fields = ('check_in_image_preview', 'check_out_image_preview')

    change_list_template = 'admin/attendance/attendance/change_list.html'

    @admin.display(description='Staff')
    def attendee_photo(self, obj):
        """The attendee's profile photo, so a row is recognisable at a glance."""
        from web_portal.admin_thumbnails import thumb, EMPTY
        return thumb(obj.attendee.profile_image) if obj.attendee_id else EMPTY

    @admin.display(description='In')
    def check_in_photo(self, obj):
        from web_portal.admin_thumbnails import thumb
        return thumb(obj.check_in_image, radius='6px')

    @admin.display(description='Out')
    def check_out_photo(self, obj):
        from web_portal.admin_thumbnails import thumb
        return thumb(obj.check_out_image, radius='6px')

    @admin.display(description='Check-in photo')
    def check_in_image_preview(self, obj):
        from web_portal.admin_thumbnails import preview
        return preview(obj.check_in_image if obj and obj.pk else None)

    @admin.display(description='Check-out photo')
    def check_out_image_preview(self, obj):
        from web_portal.admin_thumbnails import preview
        return preview(obj.check_out_image if obj and obj.pk else None)

    @staticmethod
    def _today_queryset():
        """Attendance rows for today: any check-in OR check-out today.

        The union avoids the contradiction where a late/overnight shift shows a
        check-out today but its check-in fell outside today's window.
        """
        _, start, end = _today_bounds()
        return Attendance.objects.filter(
            Q(check_in_time__gte=start, check_in_time__lt=end)
            | Q(check_out_time__gte=start, check_out_time__lt=end)
        )

    @staticmethod
    def _attendance_stats(queryset, scope):
        """Present/off counts for whatever attendance rows are in scope.

        `queryset` is the changelist's *filtered* queryset, so the tiles always
        describe the same rows the sidebar filter selected - they used to be
        hardcoded to today, which contradicted a filter set to "Any date".
        """
        attended_ids = set(queryset.values_list('attendee_id', flat=True))

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
            'scope': scope,
            'records': queryset.count(),
            'total': total,
            'present': present,
            'off': max(total - present, 0),
        }

    def changelist_view(self, request, extra_context=None):
        extra_context = extra_context or {}
        # Leave status breakdown alongside attendance: part of the "Off"
        # count is approved leave rather than an unexplained absence.
        extra_context['leave_summary'] = _leave_stats()
        extra_context['tile_links'] = _tile_links(self._scope_span(request), timezone.localdate())
        response = super().changelist_view(request, extra_context=extra_context)
        # The ChangeList only exists after super() has built it, and it carries
        # the queryset with the sidebar filters and search already applied.
        changelist = getattr(response, 'context_data', {}).get('cl') if hasattr(response, 'context_data') else None
        if changelist is not None:
            response.context_data['attendance_summary'] = self._attendance_stats(
                changelist.queryset, _scope_label(changelist)
            )
        return response

    # ---- Attendance Report (printed sheet layout) -------------------------
    def get_urls(self):
        from django.urls import path

        custom = [
            path('report/pdf/', self.admin_site.admin_view(self.report_pdf),
                 name='attendance_attendance_report_pdf'),
            path('report/csv/', self.admin_site.admin_view(self.report_csv),
                 name='attendance_attendance_report_csv'),
        ]
        return custom + super().get_urls()

    @classmethod
    def _scope_span(cls, request):
        """The page's date filter as an AttendanceMarkedFilter scope token.

        'all' when no date filter is set, otherwise 'start' or 'start:end'
        (end exclusive), mirroring Django's created_at__gte/__lt params.
        """
        gte = request.GET.get('check_in_time__gte') or request.GET.get('created_at__gte')
        if not gte:
            return 'all'
        start = cls._as_date(gte)
        if not start:
            return 'all'
        lt = request.GET.get('check_in_time__lt') or request.GET.get('created_at__lt')
        end = cls._as_date(lt) if lt else None
        return f'{start.isoformat()}:{end.isoformat()}' if end else start.isoformat()

    @staticmethod
    def _as_date(raw):
        parsed = parse_datetime(raw) or parse_date(raw[:10])
        if isinstance(parsed, datetime.datetime):
            parsed = timezone.localtime(parsed) if timezone.is_aware(parsed) else parsed
            parsed = parsed.date()
        return parsed

    @staticmethod
    def _scope_date(request):
        """The day the current filter points at; today when it names no day.

        Drives both the report banner and the tile links, so a filtered page
        and the pages it links to always talk about the same date.
        """
        gte = request.GET.get('check_in_time__gte') or request.GET.get('created_at__gte')
        if gte:
            parsed = parse_datetime(gte) or parse_date(gte[:10])
            if isinstance(parsed, datetime.datetime):
                parsed = timezone.localtime(parsed) if timezone.is_aware(parsed) else parsed
                parsed = parsed.date()
            if parsed:
                return parsed
        return timezone.localdate()

    def _report_scope(self, request):
        """(attendance queryset, report date, label) for the current filter.

        Reuses the changelist so the report covers exactly the rows the sidebar
        filter selected; falls back to today when the filter is unusable.
        """
        queryset = self.get_queryset(request)
        label = 'All dates'
        try:
            changelist = self.get_changelist_instance(request)
            queryset = changelist.queryset
            label = _scope_label(changelist)
        except Exception:
            pass

        # A single-day filter names the day on the banner, as on the sheet.
        report_date = self._scope_date(request)
        return queryset, report_date, report_date.strftime('%d-%b')

    def report_pdf(self, request):
        queryset, report_date, label = self._report_scope(request)
        rows = build_rows(queryset, report_date)
        return render_pdf(rows, label, f'attendance-report-{report_date}.pdf')

    def report_csv(self, request):
        queryset, report_date, label = self._report_scope(request)
        rows = build_rows(queryset, report_date)
        return render_csv(rows, label, f'attendance-report-{report_date}.csv')

    def get_export_summary(self, request):
        """Summary block prepended to CSV/Excel exports (see admin_export)."""
        stats = self._attendance_stats(self._today_queryset(), 'Today')
        leave = _leave_stats()
        return {
            'title': f'Attendance summary — {timezone.localdate()}',
            'rows': [
                ('Present today', stats['present']),
                ('Off today', stats['off']),
                ('Sales staff', stats['total']),
                ('On leave today (approved)', leave['on_leave_today']),
                ('Leave requests pending', leave['pending']),
                ('Leave requests approved', leave['approved']),
                ('Leave requests rejected', leave['rejected']),
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
        'id', 'user', 'leave_type', 'starts', 'ends',
        'days', 'status_badge', 'created_at',
    )
    list_filter = ('status', 'leave_type', 'created_at', OnLeaveTodayFilter)
    search_fields = (
        'user__username', 'user__email', 'user__first_name', 'user__last_name', 'reason',
    )
    autocomplete_fields = ('user',)
    ordering = ('-created_at',)
    list_per_page = 25
    actions = ('mark_approved', 'mark_rejected')
    change_list_template = 'admin/attendance/leaverequest/change_list.html'

    def changelist_view(self, request, extra_context=None):
        extra_context = extra_context or {}
        extra_context['leave_summary'] = _leave_stats()
        # The shared tile partial links through these; without them the tiles
        # would render as href="" and reload the page.
        extra_context['tile_links'] = _tile_links('all', timezone.localdate())
        return super().changelist_view(request, extra_context=extra_context)

    def get_export_summary(self, request):
        """Summary block prepended to CSV/Excel exports (see admin_export)."""
        s = _leave_stats()
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

    @staticmethod
    def _stamp(date, time):
        """"28 Jul 2026 09:30", or just the date when no time was given."""
        if not date:
            return ''
        text = date.strftime('%d %b %Y')
        return f'{text} {time.strftime("%H:%M")}' if time else text

    @admin.display(description='Starts', ordering='start_date')
    def starts(self, obj):
        return self._stamp(obj.start_date, obj.start_time)

    @admin.display(description='Ends', ordering='end_date')
    def ends(self, obj):
        return self._stamp(obj.end_date, obj.end_time)

    @admin.display(description='Days')
    def days(self, obj):
        try:
            whole = (obj.end_date - obj.start_date).days + 1
        except Exception:
            return ''
        # A single day bounded by both times is a part-day, so report the hours
        # instead of a misleading "1".
        if whole == 1 and obj.start_time and obj.end_time:
            start = datetime.datetime.combine(obj.start_date, obj.start_time)
            end = datetime.datetime.combine(obj.end_date, obj.end_time)
            hours = (end - start).total_seconds() / 3600
            return f'{hours:.2g} hr' if hours > 0 else ''
        return whole

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


@admin.register(LeaveType, site=admin_site)
class LeaveTypeAdmin(admin.ModelAdmin):
    """Manage the kinds of leave staff can request.

    These used to be hardcoded choices on LeaveRequest, so adding a type meant
    a code change. `code` is what the API sends and what quota resolution keys
    off, so renaming one after it is in use will orphan existing requests.
    """
    list_display = ('name', 'code', 'default_quota', 'requests_count', 'is_active', 'sort_order')
    list_editable = ('default_quota', 'is_active', 'sort_order')
    list_filter = ('is_active',)
    search_fields = ('code', 'name', 'description')
    ordering = ('sort_order', 'name')
    list_per_page = 25

    @admin.display(description='Requests')
    def requests_count(self, obj):
        return obj.requests.count()

    def get_readonly_fields(self, request, obj=None):
        # Changing a code in place would silently detach the API and the legacy
        # quota mapping from this type.
        return ('code',) if obj and obj.pk else ()

    def has_delete_permission(self, request, obj=None):
        # leave_type is PROTECTed; refuse up front rather than 500 on delete.
        if obj is not None and obj.requests.exists():
            return False
        return super().has_delete_permission(request, obj)


@admin.register(LeaveQuota, site=admin_site)
class LeaveQuotaAdmin(admin.ModelAdmin):
    list_display = ('profile', 'leave_type', 'days')
    list_editable = ('days',)
    list_filter = ('leave_type',)
    search_fields = ('profile__user__username', 'profile__user__email', 'profile__employee_code')
    autocomplete_fields = ('profile',)
    list_per_page = 25


@admin.register(Holiday, site=admin_site)
class HolidayAdmin(admin.ModelAdmin):
    list_display = ('date', 'name')
    search_fields = ('name',)
    ordering = ('-date',)
    list_per_page = 25
