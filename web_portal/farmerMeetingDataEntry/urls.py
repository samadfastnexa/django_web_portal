from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import MeetingViewSet, FieldDayViewSet
from .hpm_api import HPMRequisitionViewSet

# Create a router and register the viewset
router = DefaultRouter()
router.register(r'meetings', MeetingViewSet, basename='meeting')
router.register(r'field-days', FieldDayViewSet, basename='field-day')
router.register(r'hpm-requisitions', HPMRequisitionViewSet, basename='hpm-requisition')
# Include the router URLs
urlpatterns = [
    path('', include(router.urls)),
]
