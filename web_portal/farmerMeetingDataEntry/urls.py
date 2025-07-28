from django.urls import path
from .views import MeetingCreateView, MeetingListView

urlpatterns = [
    path('meetings/', MeetingListView.as_view(), name='meeting-list'),
    path('meetings/create/', MeetingCreateView.as_view(), name='meeting-create'),
]
