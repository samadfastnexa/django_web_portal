# from django.urls import path
# from .views import UserSettingListCreateView,WeatherTestView
# from .views import (
#     UserSettingListCreateView,
#     GlobalSettingListCreateView,
#     UserSpecificSettingView,
#     SettingsView
# )

# urlpatterns = [
   
#     path('settings/', UserSettingListCreateView.as_view(), name='user-global-settings'),
#     path('settings/global/', GlobalSettingListCreateView.as_view(), name='global-settings'),
#     path('settings/user/', UserSpecificSettingView.as_view(), name='user-settings'),
#     path('settings/all/', SettingsView.as_view(), name='unified-settings'),

#     path('weather/', WeatherTestView.as_view(), name='weather-test'),
# ]
# # This file is for user preferences and settings related URLs.
# # It includes a view for listing and creating user settings.

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import SettingViewSet
from .views import WeatherTestView,AvailableLocationsView,UserAnalyticsView
from FieldAdvisoryService.views import ZoneNestedViewSet, TerritoryNestedViewSet  # Import from FAS

router = DefaultRouter()
router.register('settings', SettingViewSet)

urlpatterns = [
    path('', include(router.urls)),
    path('weather/',WeatherTestView.as_view(), name='weather-search'),
    path('available-locations/',AvailableLocationsView.as_view(), name='available-locations'),
    path('analytics/overview/', UserAnalyticsView.as_view(), name='user-analytics-overview'),
    # For ViewSets, you need to specify the action
   # Correct ViewSet usage - specify actions explicitly
    path('zones/',ZoneNestedViewSet.as_view({'get': 'list'}), name='zone-list'),
    path('zones/<int:pk>/territories/',TerritoryNestedViewSet.as_view({'get': 'list'}), 
         name='territory-list-by-zone'),
]
