from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

app_name = "crop_manage"

# Create a router and register ViewSets
router = DefaultRouter()
router.register(r'crops', views.CropViewSet, basename='crop')
router.register(r'crop-stages', views.CropStageViewSet, basename='crop-stage')

urlpatterns = [
    # API endpoints (registered with router)
    path('', include(router.urls)),
    
    # Report views
    path("reports/", views.reports_index, name="reports_index"),
    path("reports/weed-efficacy/", views.weed_efficacy_report, name="weed_efficacy_report"),
]
