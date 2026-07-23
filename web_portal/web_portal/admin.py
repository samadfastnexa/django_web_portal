from django.contrib import admin
from django.contrib.admin import AdminSite
from django.utils import timezone
from django.db.models import Sum, Count, F, ExpressionWrapper, DecimalField
from datetime import timedelta
from django.conf import settings
import json


class AnalyticsAdminSite(AdminSite):
    """Custom Admin Site with Analytics Dashboard"""
    site_header = settings.ADMIN_SITE_HEADER
    site_title = settings.ADMIN_SITE_TITLE
    index_title = settings.ADMIN_INDEX_TITLE
    
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
            
            # Calculate date ranges
            today = timezone.localdate()
            last_month_day = today - timedelta(days=30)
            week_start = today - timedelta(days=6)

            # Resolve user role context
            role_label = getattr(getattr(request.user, 'role', None), 'name', None) or 'User'
            is_admin = bool(getattr(request.user, 'is_superuser', False)) or role_label.lower() == 'admin'
            is_sales = bool(getattr(request.user, 'is_sales_staff', False))
            is_dealer = bool(hasattr(request.user, 'dealer') and getattr(request.user, 'dealer'))
            
            # KPI 1: Today's Visits (global)
            visits_today = (
                MeetingSchedule.objects.filter(date=today).count() +
                Meeting.objects.filter(date__date=today).count() +
                FieldDay.objects.filter(date__date=today).count()
            )
            visits_scheduled_today = MeetingSchedule.objects.filter(date=today).count()
            meetings_held_today = Meeting.objects.filter(date__date=today).count()
            fielddays_held_today = FieldDay.objects.filter(date__date=today).count()
            attendees_today = (
                (MeetingSchedule.objects.filter(date=today).aggregate(s=Sum('confirmed_attendees'))['s'] or 0) +
                (Meeting.objects.filter(date__date=today).aggregate(s=Sum('total_attendees'))['s'] or 0) +
                (FieldDay.objects.filter(date__date=today).aggregate(s=Sum('total_participants'))['s'] or 0)
            )
            visits_last_month = (
                MeetingSchedule.objects.filter(date=last_month_day).count() +
                Meeting.objects.filter(date__date=last_month_day).count() +
                FieldDay.objects.filter(date__date=last_month_day).count()
            )
            visits_change = self._calculate_percentage_change(visits_today, visits_last_month)

            # Weekly and forward-looking signals (global)
            visits_week = (
                MeetingSchedule.objects.filter(date__gte=week_start, date__lte=today).count() +
                Meeting.objects.filter(date__date__gte=week_start, date__date__lte=today).count() +
                FieldDay.objects.filter(date__date__gte=week_start, date__date__lte=today).count()
            )
            upcoming_meetings = MeetingSchedule.objects.filter(date__gte=today, date__lte=today + timedelta(days=7)).count()
            
            # KPI 2: Total Farmers
            total_farmers_current = Farmer.objects.count()
            total_farmers_last_month = Farmer.objects.filter(
                registration_date__date__lte=last_month_day
            ).count()
            farmers_change = self._calculate_percentage_change(total_farmers_current, total_farmers_last_month)
            
            # KPI 3: Pending Sales Orders (global)
            pending_current = SalesOrder.objects.filter(status='pending').count()
            pending_last_month = SalesOrder.objects.filter(
                status='pending', created_at__date=last_month_day
            ).count()
            pending_change = self._calculate_percentage_change(pending_current, pending_last_month)

            # Order health (global)
            orders_posted = SalesOrder.objects.filter(is_posted_to_sap=True).count()
            orders_with_errors = SalesOrder.objects.filter(sap_error__isnull=False).count()

            # Farmer freshness (global)
            farmers_new_7d = Farmer.objects.filter(registration_date__date__gte=week_start).count()
            farmers_active_30d = Farmer.objects.filter(last_updated__date__gte=today - timedelta(days=30)).count()
            top_district_row = Farmer.objects.values('district').annotate(c=Count('id')).order_by('-c').first()
            top_district = {
                'name': (top_district_row or {}).get('district') or '—',
                'count': (top_district_row or {}).get('c') or 0
            }

            # Role-scoped metrics
            my_visits_today = (
                MeetingSchedule.objects.filter(staff=request.user, date=today).count() +
                Meeting.objects.filter(user_id=request.user, date__date=today).count() +
                FieldDay.objects.filter(user=request.user, date__date=today).count()
            ) if is_sales else None
            my_visits_week = (
                MeetingSchedule.objects.filter(staff=request.user, date__gte=week_start, date__lte=today).count() +
                Meeting.objects.filter(user_id=request.user, date__date__gte=week_start, date__date__lte=today).count() +
                FieldDay.objects.filter(user=request.user, date__date__gte=week_start, date__date__lte=today).count()
            ) if is_sales else None
            my_orders_pending = SalesOrder.objects.filter(staff=request.user, status='pending').count() if is_sales else None
            my_orders_posted = SalesOrder.objects.filter(staff=request.user, is_posted_to_sap=True).count() if is_sales else None

            dealer_orders_pending = SalesOrder.objects.filter(dealer__user=request.user, status='pending').count() if is_dealer else None
            dealer_orders_total = SalesOrder.objects.filter(dealer__user=request.user).count() if is_dealer else None

            # Pending order value and aging buckets (global)
            line_total = ExpressionWrapper(
                F('quantity') * F('unit_price') * (1 - F('discount_percent')/100.0),
                output_field=DecimalField(max_digits=18, decimal_places=2)
            )
            pending_value_total = (SalesOrderLine.objects
                                   .filter(sales_order__status='pending')
                                   .aggregate(s=Sum(line_total))['s'] or 0)
            aging_0_7 = SalesOrder.objects.filter(status='pending', created_at__date__gte=today - timedelta(days=7)).count()
            aging_8_30 = SalesOrder.objects.filter(status='pending', created_at__date__lt=today - timedelta(days=7), created_at__date__gte=today - timedelta(days=30)).count()
            aging_30_plus = SalesOrder.objects.filter(status='pending', created_at__date__lt=today - timedelta(days=30)).count()
            
            # KPI 4: This Month's Activities (for chart)
            days_in_month = 30
            activity_data = []
            activity_labels = []
            
            for i in range(0, days_in_month, 7):  # Weekly data points
                week_start = today - timedelta(days=days_in_month - i)
                week_end = week_start + timedelta(days=6)
                
                week_count = (
                    MeetingSchedule.objects.filter(date__gte=week_start, date__lte=week_end).count() +
                    Meeting.objects.filter(date__date__gte=week_start, date__date__lte=week_end).count() +
                    FieldDay.objects.filter(date__date__gte=week_start, date__date__lte=week_end).count()
                )
                
                activity_data.append(week_count)
                activity_labels.append(f"W{i//7 + 1}")
            
            # Add analytics data to context
            extra_context.update({
                'user_role': role_label,
                'kpi_visits': {
                    'title': 'Today\'s Visits',
                    'value': visits_today,
                    'change': visits_change,
                    'change_direction': 'up' if visits_change >= 0 else 'down',
                },
                'kpi_visits_detail': {
                    'scheduled': visits_scheduled_today,
                    'meetings': meetings_held_today,
                    'field_days': fielddays_held_today,
                    'attendees': attendees_today,
                },
                'kpi_farmers': {
                    'title': 'Total Farmers',
                    'value': total_farmers_current,
                    'change': farmers_change,
                    'change_direction': 'up' if farmers_change >= 0 else 'down',
                },
                'kpi_farmers_detail': {
                    'new_7d': farmers_new_7d,
                    'active_30d': farmers_active_30d,
                    'top_district': top_district,
                },
                'kpi_orders': {
                    'title': 'Pending Sales Orders',
                    'value': pending_current,
                    'change': pending_change,
                    'change_direction': 'up' if pending_change >= 0 else 'down',
                },
                'kpi_orders_detail': {
                    'pending_value': pending_value_total,
                    'aging': {
                        'd0_7': aging_0_7,
                        'd8_30': aging_8_30,
                        'd30_plus': aging_30_plus,
                    },
                    'posted': orders_posted,
                    'errors': orders_with_errors,
                },
                'activity_labels': json.dumps(activity_labels),
                'activity_data': json.dumps(activity_data),
                'date_range': f"{(today - timedelta(days=30)).strftime('%B %d')} — {today.strftime('%B %d, %Y')}",
                'ops_cards': [
                    {'title': "Visits this week", 'value': visits_week, 'chip': 'last 7 days'},
                    {'title': "Upcoming meetings", 'value': upcoming_meetings, 'chip': 'next 7 days'},
                    {'title': "Orders posted to SAP", 'value': orders_posted, 'chip': 'lifetime'},
                    {'title': "Orders with SAP errors", 'value': orders_with_errors, 'chip': 'needs attention', 'variant': 'alert'},
                    {'title': "New farmers", 'value': farmers_new_7d, 'chip': 'last 7 days'},
                ] + ([
                    {'title': "My visits today", 'value': my_visits_today, 'chip': 'you'}
                ] if is_sales else []) + ([
                    {'title': "My visits (7d)", 'value': my_visits_week, 'chip': 'you'},
                    {'title': "My pending orders", 'value': my_orders_pending, 'chip': 'you'},
                    {'title': "My orders posted", 'value': my_orders_posted, 'chip': 'you'},
                ] if is_sales else []) + ([
                    {'title': "Dealer pending orders", 'value': dealer_orders_pending, 'chip': 'dealer'},
                    {'title': "Dealer total orders", 'value': dealer_orders_total, 'chip': 'dealer'},
                ] if is_dealer else [])
            })
        except Exception as e:
            # Fallback to default values if analytics fail
            extra_context.update({
                'kpi_visits': {'title': 'Today\'s Visits', 'value': 0, 'change': 0, 'change_direction': 'up'},
                'kpi_farmers': {'title': 'Total Farmers', 'value': 0, 'change': 0, 'change_direction': 'up'},
                'kpi_orders': {'title': 'Pending Sales Orders', 'value': 0, 'change': 0, 'change_direction': 'up'},
                'activity_labels': json.dumps(['W1', 'W2', 'W3', 'W4']),
                'activity_data': json.dumps([0, 0, 0, 0]),
                'date_range': 'Dashboard',
                'analytics_error': str(e),
                'ops_cards': [
                    {'title': "Visits this week", 'value': 0, 'chip': 'last 7 days'},
                    {'title': "Upcoming meetings", 'value': 0, 'chip': 'next 7 days'},
                    {'title': "Orders posted to SAP", 'value': 0, 'chip': 'lifetime'},
                    {'title': "Orders with SAP errors", 'value': 0, 'chip': 'needs attention', 'variant': 'alert'},
                    {'title': "New farmers", 'value': 0, 'chip': 'last 7 days'},
                ],
            })
        
        return super().index(request, extra_context)
    
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
