# from django.urls import path
# from .views import MeetingCreateView, MeetingListView

# urlpatterns = [
#     path('meetings/', MeetingListView.as_view(), name='meeting-list'),
#     path('meetings/create/', MeetingCreateView.as_view(), name='meeting-create'),
# ]

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
