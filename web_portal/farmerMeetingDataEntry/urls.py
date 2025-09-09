from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import MeetingViewSet, FieldDayViewSet

# Create a router and register the viewset
router = DefaultRouter()
router.register(r'meetings', MeetingViewSet, basename='meeting')
router.register(r'field-days', FieldDayViewSet, basename='field-day')
# Include the router URLs
urlpatterns = [
    path('', include(router.urls)),
]
