from django.urls import path
from .views import UserSettingListCreateView

urlpatterns = [
    path('settings/', UserSettingListCreateView.as_view(), name='user-settings'),
]
# This file is for user preferences and settings related URLs.
# It includes a view for listing and creating user settings.