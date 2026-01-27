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
        """Add custom organogram URL"""
        from django.urls import path
        from accounts.admin import OrganogramAdminView
        
        urls = super().get_urls()
        custom_urls = [
            path('organogram/', OrganogramAdminView.organogram_view, name='organogram'),
        ]
        return custom_urls + urls
    
    def _calculate_percentage_change(self, current, previous):
        """Calculate percentage change between two values"""
        if previous == 0:
            return 100 if current > 0 else 0
        return round(((current - previous) / previous) * 100, 1)


# Create custom admin site instance
admin_site = AnalyticsAdminSite(name='admin')

# Note: All models should be registered with admin_site in their respective admin.py files
