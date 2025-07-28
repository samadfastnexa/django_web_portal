from django.urls import path
from .views import UserSettingListCreateView,WeatherTestView
from .views import (
    UserSettingListCreateView,
    GlobalSettingListCreateView,
    UserSpecificSettingView,
    SettingsView
)

urlpatterns = [
   
    path('settings/', UserSettingListCreateView.as_view(), name='user-global-settings'),
    path('settings/global/', GlobalSettingListCreateView.as_view(), name='global-settings'),
    path('settings/user/', UserSpecificSettingView.as_view(), name='user-settings'),
    path('settings/all/', SettingsView.as_view(), name='unified-settings'),
    path('weather/', WeatherTestView.as_view(), name='weather-test'),
]
# This file is for user preferences and settings related URLs.
# It includes a view for listing and creating user settings.