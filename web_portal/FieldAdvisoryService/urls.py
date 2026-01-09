# django_wed_panel/web_portal/FieldAdvisoryService/urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import (
    DealerViewSet, MeetingScheduleViewSet, SalesOrderViewSet,
    CompanyViewSet, RegionViewSet, ZoneViewSet, TerritoryViewSet,
    DealerRequestViewSet, CompanyNestedViewSet ,RegionNestedViewSet, ZoneNestedViewSet,TerritoryNestedViewSet,
    HierarchyLevelViewSet, UserHierarchyViewSet,
    api_warehouse_for_item, api_customer_address, api_policy_link, api_discounts, api_project_balance, api_customer_details, api_child_customers
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

# 📦 Hierarchy Router
hierarchy_router = DefaultRouter()
hierarchy_router.register(r'hierarchy-levels', HierarchyLevelViewSet, basename='hierarchy-level')
hierarchy_router.register(r'user-hierarchies', UserHierarchyViewSet, basename='user-hierarchy')

# 📦 Dealer Request Router (optional Swagger grouping)
dealer_router = DefaultRouter()
dealer_router.register(r'requests',DealerRequestViewSet, basename='dealer-requests')

# ✅ Combined URL Patterns
urlpatterns = [
    path('',include(core_router.urls)),
    path('',include(hierarchy_router.urls)),
    path('dealer-requests/',include(dealer_router.urls)),
    
    # SAP LOV API endpoints for admin forms
    path('api/warehouse_for_item/', api_warehouse_for_item, name='api_warehouse_for_item'),
    path('api/customer_address/', api_customer_address, name='api_customer_address'),
    path('api/customer_details/', api_customer_details, name='api_customer_details'),
    path('api/child_customers/', api_child_customers, name='api_child_customers'),
    path('api/policy_link/', api_policy_link, name='api_policy_link'),
    path('api/discounts/', api_discounts, name='api_discounts'),
    path('api/project_balance/', api_project_balance, name='api_project_balance'),
]