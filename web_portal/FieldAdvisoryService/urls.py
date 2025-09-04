# django_wed_panel/web_portal/FieldAdvisoryService/urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import (
    DealerViewSet, MeetingScheduleViewSet, SalesOrderViewSet,
    CompanyViewSet, RegionViewSet, ZoneViewSet, TerritoryViewSet,
    DealerRequestViewSet, CompanyNestedViewSet ,RegionNestedViewSet, ZoneNestedViewSet,TerritoryNestedViewSet
)

# 📦 Core API Router
core_router = DefaultRouter()
core_router.register(r'dealers', DealerViewSet)
core_router.register(r'schedule', MeetingScheduleViewSet)
core_router.register(r'sales-orders', SalesOrderViewSet)
core_router.register(r'companies', CompanyViewSet)
core_router.register(r'regions', RegionViewSet)
core_router.register(r'zones', ZoneViewSet)
core_router.register(r'territories', TerritoryViewSet)
core_router.register(r'companies-nested', CompanyNestedViewSet, basename='company-nested')  # ✅ Correct router
core_router.register(r'regions-nested', RegionNestedViewSet, basename='region-nested')
core_router.register(r'zones-nested', ZoneNestedViewSet, basename='zone-nested')
core_router.register(r'territories-nested', TerritoryNestedViewSet, basename='territory-nested')

# 📦 Dealer Request Router (optional Swagger grouping)
dealer_router = DefaultRouter()
dealer_router.register(r'requests',DealerRequestViewSet, basename='dealer-requests')

# ✅ Combined URL Patterns
urlpatterns = [
    path('',include(core_router.urls)),
    path('dealer-requests/',include(dealer_router.urls)),
]