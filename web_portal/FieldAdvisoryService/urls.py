# from rest_framework.routers import DefaultRouter
# from django.urls import path, include
# from .views import DealerViewSet, MeetingScheduleViewSet, SalesOrderViewSet
# from .views import DealerRequestListCreateView, DealerRequestDetailView
# from .views import CompanyViewSet, RegionViewSet, ZoneViewSet, TerritoryViewSet
# router = DefaultRouter()
# router.register(r'dealers', DealerViewSet)
# router.register(r'schedule', MeetingScheduleViewSet)
# router.register(r'sales-orders', SalesOrderViewSet)

# router.register(r'companies', CompanyViewSet)
# router.register(r'regions', RegionViewSet)
# router.register(r'zones', ZoneViewSet)
# router.register(r'territories', TerritoryViewSet)
# urlpatterns = [
#     path('', include(router.urls)),
#      path('dealer-requests/', DealerRequestListCreateView.as_view(), name='dealer-request-list-create'),
#     path('dealer-requests/<int:pk>/', DealerRequestDetailView.as_view(), name='dealer-request-detail'),
# ]

# router = DefaultRouter()
# router.register(r'dealers', DealerViewSet)
# router.register(r'schedule', MeetingScheduleViewSet)
# router.register(r'sales-orders', SalesOrderViewSet)
# router.register(r'companies', CompanyViewSet)
# router.register(r'regions', RegionViewSet)
# router.register(r'zones', ZoneViewSet)
# router.register(r'territories', TerritoryViewSet)


# urlpatterns = [
#     path('', include(router.urls)),
#     path('dealer-requests/', include([
#     path('', DealerRequestListCreateView.as_view(), name='dealer-request-list-create'),
#     path('<int:pk>/', DealerRequestDetailView.as_view(), name='dealer-request-detail'),
    
#     ])),
# ]
# Separate router for dealer requests (clean grouping in Swagger)



from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import (
    DealerViewSet, MeetingScheduleViewSet, SalesOrderViewSet,
    CompanyViewSet, RegionViewSet, ZoneViewSet, TerritoryViewSet,
    DealerRequestViewSet, CompanyNestedViewSet  # 👈 Don't forget this import!
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

# 📦 Dealer Request Router (optional Swagger grouping)
dealer_router = DefaultRouter()
dealer_router.register(r'requests', DealerRequestViewSet, basename='dealer-requests')

# ✅ Combined URL Patterns
urlpatterns = [
    path('', include(core_router.urls)),
    path('dealer-requests/', include(dealer_router.urls)),
]