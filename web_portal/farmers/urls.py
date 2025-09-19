from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    FarmerViewSet, FarmingHistoryViewSet,
    FarmerListCreateView, FarmerDetailView  # Legacy views
)

router = DefaultRouter()
router.register(r'', FarmerViewSet, basename='farmer')  # ⚡ root → /api/farmers/
router.register(r'farming-history', FarmingHistoryViewSet, basename='farming-history')

urlpatterns = [
    path('', include(router.urls)),

    # Legacy URLs under /legacy/ to avoid overlap
    path('legacy/', FarmerListCreateView.as_view(), name='farmer-list-legacy'),
    path('legacy/<int:pk>/', FarmerDetailView.as_view(), name='farmer-detail-legacy'),
]

# The new API endpoints will be:
# GET/POST    /api/farmers/                    - List/Create farmers with search & filtering
# GET/PUT/PATCH/DELETE /api/farmers/{id}/     - Retrieve/Update/Delete specific farmer
# GET         /api/farmers/{id}/farming_history/ - Get farming history for farmer
# GET         /api/farmers/statistics/         - Get farmer statistics
# GET/POST    /api/farming-history/            - List/Create farming history records
# GET/PUT/PATCH/DELETE /api/farming-history/{id}/ - Manage specific farming history record