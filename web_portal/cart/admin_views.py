"""
Admin-side dashboard for the Shopping Cart & Orders module.

Renders a consistent, orange-themed overview page (matching the SAP
integration admin dashboards) with order/payment/cart statistics and a
recent-orders table. Wired in web_portal/urls.py via admin.site.admin_view.
"""
from django.db.models import Sum, Count, DecimalField
from django.db.models.functions import Coalesce
from django.shortcuts import render
from django.utils import timezone
from datetime import timedelta

from .models import Cart, CartItem, Order, OrderItem, Payment


def _money(value):
    """Normalise a possibly-None aggregate to a Decimal-ish number."""
    return value or 0


def cart_dashboard_admin(request):
    """Overview dashboard for carts, orders and payments."""
    now = timezone.now()
    last_30 = now - timedelta(days=30)

    orders = Order.objects.all()

    # --- Order statistics -------------------------------------------------
    order_agg = orders.aggregate(
        total=Count('id'),
        total_amount=Coalesce(Sum('total_amount'), 0, output_field=DecimalField()),
        paid_amount=Coalesce(Sum('paid_amount'), 0, output_field=DecimalField()),
    )

    status_counts = {row['status']: row['count'] for row in
                     orders.values('status').annotate(count=Count('id'))}
    payment_counts = {row['payment_status']: row['count'] for row in
                      orders.values('payment_status').annotate(count=Count('id'))}

    total_amount = _money(order_agg['total_amount'])
    paid_amount = _money(order_agg['paid_amount'])

    order_stats = {
        'total': order_agg['total'],
        'pending': status_counts.get('pending', 0),
        'inprogress': status_counts.get('inprogress', 0),
        'delivered': status_counts.get('delivered', 0),
        'last_30_days': orders.filter(created_date__gte=last_30).count(),
        'total_amount': total_amount,
        'paid_amount': paid_amount,
        'outstanding': total_amount - paid_amount,
        'unpaid': payment_counts.get('unpaid', 0),
        'partially_paid': payment_counts.get('partially_paid', 0),
        'paid_count': payment_counts.get('paid', 0),
        'synced_to_sap': orders.filter(is_synced_to_sap=True).count(),
    }

    # --- Cart statistics --------------------------------------------------
    active_carts = Cart.objects.filter(is_active=True)
    cart_stats = {
        'active_carts': active_carts.count(),
        'active_items': CartItem.objects.filter(is_active=True, cart__is_active=True).count(),
        'total_carts': Cart.objects.count(),
    }

    # --- Payment statistics -----------------------------------------------
    payments = Payment.objects.all()
    payment_stats = {
        'total': payments.count(),
        'completed': payments.filter(status='completed').count(),
        'pending': payments.filter(status='pending').count(),
        'failed': payments.filter(status='failed').count(),
        'collected': _money(
            payments.filter(status='completed').aggregate(
                s=Coalesce(Sum('amount'), 0, output_field=DecimalField()))['s']
        ),
    }

    # --- Recent orders ----------------------------------------------------
    status_filter = (request.GET.get('status') or '').strip()
    recent_qs = orders.select_related('user').prefetch_related('items')
    if status_filter in dict(Order.STATUS_CHOICES):
        recent_qs = recent_qs.filter(status=status_filter)
    recent_orders = recent_qs.order_by('-created_date')[:25]

    context = {
        'title': 'Shopping Cart & Orders',
        'order_stats': order_stats,
        'cart_stats': cart_stats,
        'payment_stats': payment_stats,
        'recent_orders': recent_orders,
        'status_filter': status_filter,
        'status_choices': Order.STATUS_CHOICES,
    }
    return render(request, 'admin/cart/dashboard.html', context)
