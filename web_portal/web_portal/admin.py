from django.contrib import admin
from django.contrib.admin import AdminSite
from django.utils import timezone
from django.db.models import Sum, Count, F, ExpressionWrapper, DecimalField
from datetime import timedelta, datetime, time as dtime
from django.conf import settings
import json


class AnalyticsAdminSite(AdminSite):
    """Custom Admin Site with Analytics Dashboard"""
    site_header = settings.ADMIN_SITE_HEADER
    site_title = settings.ADMIN_SITE_TITLE
    index_title = settings.ADMIN_INDEX_TITLE

    def register(self, model_or_iterable, admin_class=None, **options):
        """Give every registered ModelAdmin the detailed form-error summary.

        Mixed in here rather than added to each of the ~60 ModelAdmin classes,
        the same way the export actions are registered site-wide below.
        """
        from django.contrib.admin import ModelAdmin

        from web_portal.admin_form_errors import DetailedFormErrorsMixin

        base = admin_class or ModelAdmin
        if isinstance(base, type) and issubclass(base, ModelAdmin) \
                and not issubclass(base, DetailedFormErrorsMixin):
            admin_class = type(base.__name__, (DetailedFormErrorsMixin, base), {
                '__module__': base.__module__,
                '__doc__': base.__doc__,
            })
        return super().register(model_or_iterable, admin_class, **options)


    def index(self, request, extra_context=None):
        """
        Custom admin index view with analytics data
        """
        extra_context = extra_context or {}
        
        try:
            # Import models here to avoid circular imports
            from farmers.models import Farmer
            from FieldAdvisoryService.models import MeetingSchedule, SalesOrder, SalesOrderLine
            from farmerMeetingDataEntry.models import Meeting, FieldDay
            
            # Period selector: tabs (today / this week / this month) + optional
            # custom date range. Boundaries are aware datetimes compared with
            # >=/< (no __date lookup, which would hit MySQL CONVERT_TZ).
            today = timezone.localdate()
            aging_ref = timezone.make_aware(datetime.combine(today, dtime.min))
            period = (request.GET.get('period') or 'today').strip().lower()
            p_start, p_end, p_label, p_active = self._period_bounds(
                period,
                (request.GET.get('from') or '').strip(),
                (request.GET.get('to') or '').strip(),
                today,
            )
            p_len = p_end - p_start
            prev_start, prev_end = p_start - p_len, p_start

            # Resolve who is looking and what data they may see.
            #   - Superusers, Admin-role users and CEOs (designation) see
            #     ORG-WIDE data; a plain back-office viewer does too.
            #   - Field sales staff see only their own; dealers see only theirs.
            role_label = getattr(getattr(request.user, 'role', None), 'name', None) or 'User'
            is_sales = bool(getattr(request.user, 'is_sales_staff', False))
            is_dealer = bool(hasattr(request.user, 'dealer') and getattr(request.user, 'dealer'))
            profile = getattr(request.user, 'sales_profile', None)
            designation_code = ''
            if profile is not None and getattr(profile, 'designation', None):
                designation_code = (getattr(profile.designation, 'code', '') or '').strip().upper()
            sees_all = (
                bool(getattr(request.user, 'is_superuser', False))
                or role_label.lower() == 'admin'
                or designation_code == 'CEO'
            )

            if sees_all or (not is_sales and not is_dealer):
                scope_user, scope_label = None, 'Overall'
            elif is_dealer:
                scope_user, scope_label = request.user, 'Dealer'
            else:
                scope_user, scope_label = request.user, 'You'

            # Base querysets, scoped to what this user may see.
            if scope_user is None:
                order_qs = SalesOrder.objects.all()
                farmer_qs = Farmer.objects.all()
            elif is_dealer:
                order_qs = SalesOrder.objects.filter(dealer__user=scope_user)
                farmer_qs = Farmer.objects.none()
            else:
                order_qs = SalesOrder.objects.filter(staff=scope_user)
                farmer_qs = Farmer.objects.filter(registered_by=scope_user)
            # None -> all visits; a user filters to their own (dealers -> 0).
            visit_user = scope_user

            # KPI 1: Visits in the period = Farmer Meetings + Field Days + Field
            # Advisory (MeetingSchedule), per-type breakdown and attendees.
            v = self._visits_breakdown(p_start, p_end, user=visit_user)
            visits_period = v['total']
            visits_prev = self._visits_breakdown(prev_start, prev_end, user=visit_user)['total']
            visits_change = self._calculate_percentage_change(visits_period, visits_prev)

            # KPI 2: Farmers - new in the period (cumulative total kept as context).
            total_farmers_current = farmer_qs.count()
            farmers_new_period = farmer_qs.filter(
                registration_date__gte=p_start, registration_date__lt=p_end
            ).count()
            farmers_new_prev = farmer_qs.filter(
                registration_date__gte=prev_start, registration_date__lt=prev_end
            ).count()
            farmers_change = self._calculate_percentage_change(farmers_new_period, farmers_new_prev)
            farmers_active_30d = farmer_qs.filter(
                last_updated__gte=aging_ref - timedelta(days=30)
            ).count()
            top_district_row = farmer_qs.values('district').annotate(c=Count('id')).order_by('-c').first()
            top_district = {
                'name': (top_district_row or {}).get('district') or '—',
                'count': (top_district_row or {}).get('c') or 0
            }

            # KPI 3: Sales orders created in the period + current status health.
            orders_period = order_qs.filter(created_at__gte=p_start, created_at__lt=p_end).count()
            orders_prev = order_qs.filter(created_at__gte=prev_start, created_at__lt=prev_end).count()
            orders_change = self._calculate_percentage_change(orders_period, orders_prev)
            pending_current = order_qs.filter(status='pending').count()
            orders_posted = order_qs.filter(is_posted_to_sap=True).count()
            orders_with_errors = order_qs.filter(sap_error__isnull=False).count()

            # Pending order value and aging buckets (scoped).
            line_total = ExpressionWrapper(
                F('quantity') * F('unit_price') * (1 - F('discount_percent')/100.0),
                output_field=DecimalField(max_digits=18, decimal_places=2)
            )
            pending_value_total = (SalesOrderLine.objects
                                   .filter(sales_order__in=order_qs.filter(status='pending'))
                                   .aggregate(s=Sum(line_total))['s'] or 0)
            aging_0_7 = order_qs.filter(status='pending', created_at__gte=aging_ref - timedelta(days=7)).count()
            aging_8_30 = order_qs.filter(status='pending', created_at__lt=aging_ref - timedelta(days=7), created_at__gte=aging_ref - timedelta(days=30)).count()
            aging_30_plus = order_qs.filter(status='pending', created_at__lt=aging_ref - timedelta(days=30)).count()

            # Sales & Collection achievements (live from SAP). Isolated in its own
            # try/except - a slow or failing HANA call must never break the rest
            # of the dashboard; it just degrades to a "view report" link.
            sales_collection = self._sales_collection_card(p_start, p_end, scope_user, is_dealer, profile)
            
            # Card sparklines: REAL weekly counts for the last 6 weeks, scoped
            # to the same querysets as the KPI numbers. Uses aware >=/< bounds
            # (never __date, which compiles to MySQL CONVERT_TZ and breaks here).
            # All counts are >= 0 - no fabricated/negative trend lines.
            WEEKS = 6
            end_excl = aging_ref + timedelta(days=1)  # include all of today
            chart_labels, chart_activity, chart_farmers, chart_orders = [], [], [], []
            for k in range(WEEKS):
                w_end = end_excl - timedelta(days=7 * (WEEKS - 1 - k))
                w_start = w_end - timedelta(days=7)
                chart_activity.append(self._visits_breakdown(w_start, w_end, user=visit_user)['total'])
                chart_farmers.append(farmer_qs.filter(
                    registration_date__gte=w_start, registration_date__lt=w_end).count())
                chart_orders.append(order_qs.filter(
                    created_at__gte=w_start, created_at__lt=w_end).count())
                chart_labels.append(w_start.strftime('%d %b'))

            # Add analytics data to context
            extra_context.update({
                'user_role': role_label,
                'scope_label': scope_label,
                'period': self._period_context(p_active, p_label, p_start, p_end, request),
                'sales_collection': sales_collection,
                'kpi_visits': {
                    'title': 'Field Activities',
                    'value': visits_period,
                    'change': visits_change,
                    'change_direction': 'up' if visits_change >= 0 else 'down',
                    'period': p_label,
                },
                'kpi_visits_detail': {
                    'advisory': v['advisory'],
                    'meetings': v['meetings'],
                    'field_days': v['field_days'],
                    'attendees': v['attendees'],
                },
                'kpi_farmers': {
                    'title': 'New Farmers',
                    'value': farmers_new_period,
                    'change': farmers_change,
                    'change_direction': 'up' if farmers_change >= 0 else 'down',
                    'period': p_label,
                },
                'kpi_farmers_detail': {
                    'total': total_farmers_current,
                    'active_30d': farmers_active_30d,
                    'top_district': top_district,
                },
                'kpi_orders': {
                    'title': 'Sales Orders',
                    'value': orders_period,
                    'change': orders_change,
                    'change_direction': 'up' if orders_change >= 0 else 'down',
                    'period': p_label,
                },
                'kpi_orders_detail': {
                    'pending': pending_current,
                    'pending_value': pending_value_total,
                    'aging': {
                        'd0_7': aging_0_7,
                        'd8_30': aging_8_30,
                        'd30_plus': aging_30_plus,
                    },
                    'posted': orders_posted,
                    'errors': orders_with_errors,
                },
                'chart_labels': json.dumps(chart_labels),
                'chart_activity': json.dumps(chart_activity),
                'chart_farmers': json.dumps(chart_farmers),
                'chart_orders': json.dumps(chart_orders),
                'date_range': p_label,
                # Consolidated into the KPI cards below; no separate stat row.
                'ops_cards': [],
            })
        except Exception as e:
            # Fallback to default values if analytics fail
            extra_context.update({
                'scope_label': 'Overall',
                'sales_collection': None,
                'period': self._period_context('today', 'Today', None, None, request),
                'kpi_visits': {'title': 'Visits', 'value': 0, 'change': 0, 'change_direction': 'up', 'period': 'Today'},
                'kpi_farmers': {'title': 'New Farmers', 'value': 0, 'change': 0, 'change_direction': 'up', 'period': 'Today'},
                'kpi_orders': {'title': 'Sales Orders', 'value': 0, 'change': 0, 'change_direction': 'up', 'period': 'Today'},
                'chart_labels': json.dumps(['', '', '', '', '', '']),
                'chart_activity': json.dumps([0, 0, 0, 0, 0, 0]),
                'chart_farmers': json.dumps([0, 0, 0, 0, 0, 0]),
                'chart_orders': json.dumps([0, 0, 0, 0, 0, 0]),
                'date_range': 'Dashboard',
                'analytics_error': str(e),
                'ops_cards': [],
            })

        return super().index(request, extra_context)

    # ------------------------------------------------------------------
    # Dashboard period helpers
    # ------------------------------------------------------------------
    def _period_bounds(self, period, from_str, to_str, today):
        """Return (start, end, label, active_key) as aware datetime boundaries.

        A custom from/to range wins; otherwise the tab (today/week/month).
        """
        from django.utils.dateparse import parse_date

        def aware(d):
            stamp = datetime.combine(d, dtime.min)
            if settings.USE_TZ and timezone.is_naive(stamp):
                stamp = timezone.make_aware(stamp)
            return stamp

        if from_str and to_str:
            f, t = parse_date(from_str), parse_date(to_str)
            if f and t and t >= f:
                return aware(f), aware(t + timedelta(days=1)), f'{f} – {t}', 'custom'
        if period == 'week':
            monday = today - timedelta(days=today.weekday())
            return aware(monday), aware(today + timedelta(days=1)), 'This week', 'week'
        if period == 'month':
            return aware(today.replace(day=1)), aware(today + timedelta(days=1)), 'This month', 'month'
        return aware(today), aware(today + timedelta(days=1)), 'Today', 'today'

    def _period_context(self, active, label, start, end, request):
        """Tabs + current range for the dashboard toolbar."""
        base = request.path
        tabs = [
            {'key': 'today', 'label': 'Today', 'active': active == 'today', 'url': f'{base}?period=today'},
            {'key': 'week', 'label': 'This week', 'active': active == 'week', 'url': f'{base}?period=week'},
            {'key': 'month', 'label': 'This month', 'active': active == 'month', 'url': f'{base}?period=month'},
        ]
        return {
            'active': active,
            'label': label,
            'tabs': tabs,
            'from': (request.GET.get('from') or '').strip(),
            'to': (request.GET.get('to') or '').strip(),
            'today': timezone.localdate().isoformat(),
        }

    def _visits_breakdown(self, start, end, user=None):
        """Field Advisory + Farmer Meeting + Field Day counts (and attendees) in
        [start, end). Uses aware >=/< bounds - never the __date lookup, which
        compiles to MySQL CONVERT_TZ() and fails on this server."""
        from FieldAdvisoryService.models import MeetingSchedule
        from farmerMeetingDataEntry.models import Meeting, FieldDay

        ms = MeetingSchedule.objects.filter(date__gte=start, date__lt=end)
        mt = Meeting.objects.filter(date__gte=start, date__lt=end)
        fd = FieldDay.objects.filter(date__gte=start, date__lt=end)
        if user is not None:
            ms = ms.filter(staff=user)
            mt = mt.filter(user_id=user)
            fd = fd.filter(user=user)
        advisory, meetings, field_days = ms.count(), mt.count(), fd.count()
        attendees = (
            (ms.aggregate(s=Sum('confirmed_attendees'))['s'] or 0)
            + (mt.aggregate(s=Sum('total_attendees'))['s'] or 0)
            + (fd.aggregate(s=Sum('total_participants'))['s'] or 0)
        )
        return {
            'advisory': advisory, 'meetings': meetings, 'field_days': field_days,
            'total': advisory + meetings + field_days, 'attendees': attendees,
        }

    def _sales_collection_card(self, p_start, p_end, scope_user, is_dealer, profile):
        """Live sales & collection achievement per company for the period.

        Each active company maps to its own SAP HANA schema. We aggregate every
        company that has a valid schema (invalid/placeholder schemas simply
        return None and are skipped), scoped to the user's per-company employee
        id for sales staff. Returns {'rows': [...]} or None. Fully isolated -
        exceptions here never affect the rest of the dashboard.
        """
        try:
            from FieldAdvisoryService.models import Company
            from sap_integration.hana_connect import sales_collection_totals_scoped

            companies = list(Company.objects.filter(is_active=True))
            if not companies:
                return None

            start_s = p_start.strftime('%Y-%m-%d')
            end_s = (p_end - timedelta(days=1)).strftime('%Y-%m-%d')

            def emp_for(company):
                # Overall (superuser/CEO) and dealers see the whole company.
                if scope_user is None or is_dealer or profile is None:
                    return None
                code = ''
                try:
                    from accounts.models import SalesStaffCompany
                    m = SalesStaffCompany.objects.filter(
                        sales_profile=profile, company=company, is_active=True
                    ).first()
                    if m and m.employee_code:
                        code = m.employee_code
                except Exception:
                    code = ''
                if not code:
                    code = getattr(profile, 'employee_code', '') or ''
                code = str(code).strip()
                return int(code) if code.isdigit() else None

            def pct(ach, target):
                return round(ach / target * 100, 1) if target else 0

            def mn(v):
                return round((v or 0) / 1_000_000.0, 1)

            rows = []
            for company in companies:
                schema = (getattr(company, 'name', '') or '').strip()
                if not schema:
                    continue
                t = sales_collection_totals_scoped(schema, start_s, end_s, emp_id=emp_for(company))
                if not t:
                    continue  # invalid schema or connection failure -> skip
                # Skip companies with nothing (no target and no achievement) this period.
                if not any(t.get(k) for k in ('sales_target', 'sales_ach', 'coll_target', 'coll_ach')):
                    continue
                rows.append({
                    'name': getattr(company, 'Company_name', schema) or schema,
                    'sales_pct': pct(t['sales_ach'], t['sales_target']),
                    'sales_ach_m': mn(t['sales_ach']),
                    'sales_target_m': mn(t['sales_target']),
                    'coll_pct': pct(t['coll_ach'], t['coll_target']),
                    'coll_ach_m': mn(t['coll_ach']),
                    'coll_target_m': mn(t['coll_target']),
                })

            if not rows:
                return None
            return {'rows': rows}
        except Exception:
            return None
    
    def get_urls(self):
        """Add custom organogram + search-suggestion URLs"""
        from django.urls import path
        from accounts.admin import OrganogramAdminView

        urls = super().get_urls()
        custom_urls = [
            path('organogram/', OrganogramAdminView.organogram_view, name='organogram'),
            path(
                'search-suggest/',
                self.admin_view(self.search_suggest),
                name='search_suggest',
            ),
        ]
        return custom_urls + urls

    # Max suggestions returned to the search box.
    SEARCH_SUGGEST_LIMIT = 10

    def search_suggest(self, request):
        """
        Type-ahead suggestions for the changelist search box.

        Reuses the target ModelAdmin's own get_search_results(), so a suggestion
        is always something the search would actually find - never a dead end.
        Permissions are enforced per model, on top of admin_view()'s staff check.
        """
        from django.apps import apps
        from django.http import JsonResponse

        app_label = (request.GET.get('app') or '').strip()
        model_name = (request.GET.get('model') or '').strip()
        term = (request.GET.get('q') or '').strip()
        empty = JsonResponse({'results': []})

        if not (app_label and model_name and term):
            return empty

        try:
            model = apps.get_model(app_label, model_name)
        except (LookupError, ValueError):
            return empty

        model_admin = self._registry.get(model)
        if model_admin is None:
            return empty
        if not model_admin.has_view_permission(request):
            return empty

        # A sidebar filter box asks for one specific field. Only fields a
        # filter on this admin actually declares are allowed, so this can't be
        # used to read arbitrary columns.
        field = (request.GET.get('field') or '').strip()
        if field:
            allowed = {
                getattr(list_filter, 'suggest_field', None)
                for list_filter in model_admin.get_list_filter(request)
            }
            if field not in allowed:
                return empty
            return JsonResponse({'results': self._suggest_field_values(
                request, model_admin, field, term)})

        # Nothing to suggest from if the admin declares no search fields.
        if not model_admin.get_search_fields(request):
            return empty

        try:
            queryset = model_admin.get_queryset(request)
            queryset, _dupes = model_admin.get_search_results(request, queryset, term)
        except Exception:
            return empty

        # Suggest the *matched field value*, not str(obj). A model whose
        # __str__ is a composed sentence (e.g. ActivityLog) would otherwise
        # suggest text that finds nothing when searched.
        search_fields = [
            field.lstrip('^=@~') for field in model_admin.get_search_fields(request)
        ]
        lowered = term.lower()
        rows = list(queryset[: self.SEARCH_SUGGEST_LIMIT * 5])

        results, seen = [], set()
        for obj in rows:
            for field in search_fields:
                value = self._resolve_field(obj, field)
                if value is None:
                    continue
                text = str(value).strip()
                if not text or lowered not in text.lower():
                    continue
                key = text.lower()
                if key not in seen:
                    seen.add(key)
                    results.append(text)
                break  # one suggestion per row keeps the list varied
            if len(results) >= self.SEARCH_SUGGEST_LIMIT:
                break

        # Related-field matches can't always be resolved by attribute walking;
        # fall back to the object label so the box is never needlessly empty.
        if not results:
            for obj in rows:
                try:
                    label = str(obj).strip()
                except Exception:
                    continue
                key = label.lower()
                if label and key not in seen:
                    seen.add(key)
                    results.append(label)
                if len(results) >= self.SEARCH_SUGGEST_LIMIT:
                    break

        return JsonResponse({'results': results})

    def _suggest_field_values(self, request, model_admin, field, term):
        """Distinct values of one field, for a sidebar filter's text box."""
        try:
            queryset = (
                model_admin.get_queryset(request)
                .filter(**{f'{field}__icontains': term})
                .exclude(**{f'{field}__isnull': True})
                .values_list(field, flat=True)
                .distinct()
                .order_by(field)
            )
            rows = list(queryset[: self.SEARCH_SUGGEST_LIMIT * 3])
        except Exception:
            return []

        results, seen = [], set()
        for value in rows:
            text = str(value).strip()
            key = text.lower()
            if text and key not in seen:
                seen.add(key)
                results.append(text)
            if len(results) >= self.SEARCH_SUGGEST_LIMIT:
                break
        return results

    @staticmethod
    def _resolve_field(obj, path):
        """Walk a `a__b__c` search-field path on an instance; None if absent."""
        value = obj
        for part in path.split('__'):
            value = getattr(value, part, None)
            if value is None:
                return None
        return value

    # ------------------------------------------------------------------
    # Sidebar grouping: pull models out of their own apps and present them
    # together under a single heading, so related screens aren't scattered.
    # Each entry is (app_label.lower(), model object_name, label to display);
    # the order within a group follows the order declared here.
    # ------------------------------------------------------------------
    SIDEBAR_GROUPS = [
        ('Field Activities', [
            ('farmermeetingdataentry', 'Meeting', 'Farmer Meeting'),
            ('farmermeetingdataentry', 'FieldDay', 'Field Day'),
            ('fieldadvisoryservice', 'MeetingSchedule', 'Field Advisory'),
            # Listed explicitly rather than relying on SIDEBAR_ABSORB_APPS, which
            # would sweep it in at the bottom with an auto-generated label.
            ('farmermeetingdataentry', 'HPMRequisition', 'HPM Requisition'),
        ]),
        # The old "Field Advisory Service" app split into focused groups.
        ('Organization', [
            ('fieldadvisoryservice', 'Company', 'Companies'),
            ('fieldadvisoryservice', 'Region', 'Regions'),
            ('fieldadvisoryservice', 'Zone', 'Zones'),
            ('fieldadvisoryservice', 'Territory', 'Territories'),
        ]),
        ('Dealers', [
            ('fieldadvisoryservice', 'Dealer', 'Dealers'),
            ('fieldadvisoryservice', 'DealerRequest', 'Dealer Requests'),
        ]),
        ('Sales', [
            ('fieldadvisoryservice', 'SalesOrder', 'Sales Orders'),
        ]),
        ('Monitoring', [
            ('monitoring', 'ActivityLog', 'Activity Logs'),
            ('admin', 'LogEntry', 'Admin Actions'),
        ]),
    ]

    # Extra sidebar rows that point at a pre-filtered changelist rather than a
    # model of their own. Each entry is
    #   (label, admin url name, query string, object_name it depends on)
    # and is only shown when the user can actually see that dependency.
    SIDEBAR_GROUP_EXTRA_LINKS = {
        'Monitoring': [
            ('Error / Crash Logs', 'monitoring_activitylog_changelist',
             '?is_error__exact=1', 'ActivityLog'),
        ],
    }

    # Any leftover model from these apps joins the named group, so the app
    # itself disappears from the sidebar instead of showing as a run-together
    # label like "Farmermeetingdataentry".
    SIDEBAR_ABSORB_APPS = {
        'farmermeetingdataentry': 'Field Activities',
    }

    # Readable names for apps whose auto-generated label is run-together or
    # under-cased. Anything not listed falls back to _prettify_app_name().
    APP_DISPLAY_NAMES = {
        # 'fieldadvisoryservice' no longer appears as an app - all its models
        # are pulled into the Organization / Dealers / Sales groups above.
        'sap_integration': 'SAP Tools',
        'general_ledger': 'General Ledger',
        'kindwise': 'KindWise',
        'crop_manage': 'Crop Management',
        'crop_management': 'Crop R&D',
        'document_management': 'Document Management',
        'preferences': 'Settings',
        'farm': 'Farms',
        'cart': 'Cart & Orders',
    }

    # Sidebar order. Anything not listed keeps its position after these and
    # before the trailing entries.
    SIDEBAR_ORDER_TOP = [
        'Accounts',
        'Field Activities',
        'Organization',
        'Dealers',
        'Sales',
        'Farmers',
        'Farms',
        'Crop Management',
        'Crop R&D',
        'SAP Tools',
        'General Ledger',
        'KindWise',
        'Cart & Orders',
    ]
    SIDEBAR_ORDER_BOTTOM = ['Monitoring', 'Settings']

    @staticmethod
    def _prettify_app_name(name):
        """'General_Ledger' -> 'General Ledger'."""
        cleaned = (name or '').replace('_', ' ').strip()
        return ' '.join(word[:1].upper() + word[1:] for word in cleaned.split())

    def _sidebar_sort_key(self, name):
        if name in self.SIDEBAR_ORDER_TOP:
            return (0, self.SIDEBAR_ORDER_TOP.index(name), '')
        if name in self.SIDEBAR_ORDER_BOTTOM:
            return (2, self.SIDEBAR_ORDER_BOTTOM.index(name), '')
        return (1, 0, name.lower())

    def get_app_list(self, request, app_label=None):
        """Regroup selected models under custom sidebar sections."""
        app_list = super().get_app_list(request, app_label)

        # Only regroup the full index/sidebar listing, not a single-app page.
        if app_label:
            return app_list

        # (app_label, object_name) -> (group name, display label, sort order)
        wanted = {}
        for group_name, entries in self.SIDEBAR_GROUPS:
            for position, (label_app, object_name, display) in enumerate(entries):
                wanted[(label_app, object_name)] = (group_name, display, position)

        collected = {name: [] for name, _ in self.SIDEBAR_GROUPS}
        absorbed = {}
        for app in app_list:
            app_label = app['app_label'].lower()
            absorb_into = self.SIDEBAR_ABSORB_APPS.get(app_label)
            remaining = []
            for model in app['models']:
                key = (app_label, model.get('object_name'))
                match = wanted.get(key)
                if match:
                    group_name, display, position = match
                    collected[group_name].append(
                        (position, model.get('object_name'), {**model, 'name': display})
                    )
                elif absorb_into:
                    absorbed.setdefault(absorb_into, []).append(model)
                else:
                    remaining.append(model)
            app['models'] = remaining

        # Leftovers from an absorbed app trail its group's named entries.
        for group_name, models in absorbed.items():
            if group_name in collected:
                start = len(collected[group_name]) + 1000
                for offset, model in enumerate(models):
                    collected[group_name].append(
                        (start + offset, model.get('object_name'), model)
                    )

        # Drop apps left with no visible models, and give the rest readable names.
        app_list = [app for app in app_list if app['models']]
        for app in app_list:
            app['name'] = (
                self.APP_DISPLAY_NAMES.get(app['app_label'].lower())
                or self._prettify_app_name(app.get('name'))
            )

        # Prepend the custom groups, then order the whole sidebar.
        for group_name, _ in self.SIDEBAR_GROUPS:
            found = sorted(collected[group_name], key=lambda item: item[0])
            if not found:
                continue
            visible = {object_name for _, object_name, _ in found}
            models = [entry for _, _, entry in found]
            models += self._extra_group_links(group_name, visible)
            app_list.append({
                'name': group_name,
                'app_label': group_name.lower().replace(' ', '_').replace('&', 'and'),
                'app_url': models[0].get('admin_url') or '',
                'has_module_perms': True,
                'models': models,
            })

        app_list.sort(key=lambda app: self._sidebar_sort_key(app['name']))
        return app_list

    def _extra_group_links(self, group_name, visible_object_names):
        """Build the synthetic pre-filtered rows for a sidebar group."""
        from django.urls import NoReverseMatch, reverse

        rows = []
        for label, url_name, query, depends_on in self.SIDEBAR_GROUP_EXTRA_LINKS.get(group_name, []):
            if depends_on not in visible_object_names:
                continue
            try:
                url = reverse(f'admin:{url_name}', current_app=self.name)
            except NoReverseMatch:
                continue
            rows.append({
                'name': label,
                'object_name': label.replace(' ', ''),
                'admin_url': f'{url}{query}',
                'add_url': None,
                'view_only': True,
                'perms': {'add': False, 'change': False, 'delete': False, 'view': True},
            })
        return rows


    def _calculate_percentage_change(self, current, previous):
        """Calculate percentage change between two values"""
        if previous == 0:
            return 100 if current > 0 else 0
        return round(((current - previous) / previous) * 100, 1)


# Create custom admin site instance
admin_site = AnalyticsAdminSite(name='admin')

# Site-wide export actions: registering them here makes "Export selected -> CSV
# / Excel" appear on every model changelist without editing each ModelAdmin.
from web_portal.admin_export import export_as_csv, export_as_xlsx  # noqa: E402
admin_site.add_action(export_as_csv, 'export_as_csv')
admin_site.add_action(export_as_xlsx, 'export_as_xlsx')

# Note: All models should be registered with admin_site in their respective admin.py files
