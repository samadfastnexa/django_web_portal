from django.urls import path,include
from .views import AttendanceListCreateView, AttendanceDetailView
from rest_framework.routers import DefaultRouter
from .views import AttendanceRequestViewSet

router = DefaultRouter()
router.register(r'attendance-requests', AttendanceRequestViewSet, basename='attendance-request')
urlpatterns = [
    path('attendances/', AttendanceListCreateView.as_view(), name='attendance-list-create'),
    path('attendances/<int:pk>/', AttendanceDetailView.as_view(), name='attendance-detail'),
    path('', include(router.urls)),
]
