from django.urls import path
from .views import (
    DashboardOverviewView,
    SalesAnalyticsView,
    CollectionAnalyticsView,
    FarmerAnalyticsView,
    PerformanceMetricsView
)

urlpatterns = [
    # Main dashboard overview - aggregates all data
    path('dashboard/overview/', DashboardOverviewView.as_view(), name='analytics-dashboard-overview'),
    
    # Detailed analytics endpoints
    path('sales/', SalesAnalyticsView.as_view(), name='analytics-sales'),
    path('collection/', CollectionAnalyticsView.as_view(), name='analytics-collection'),
    path('farmers/', FarmerAnalyticsView.as_view(), name='analytics-farmers'),
    path('performance/', PerformanceMetricsView.as_view(), name='analytics-performance'),
]
