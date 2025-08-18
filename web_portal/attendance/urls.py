from django.urls import path,include
from .views import AttendanceListCreateView, AttendanceDetailView
from rest_framework.routers import DefaultRouter
from .views import AttendanceRequestViewSet
# from .views import AttendanceReportView

router = DefaultRouter()
router.register(r'attendance-requests', AttendanceRequestViewSet, basename='attendance-request')
urlpatterns = [
    path('attendances/', AttendanceListCreateView.as_view(), name='attendance-list-create'),
    path('attendances/<int:pk>/', AttendanceDetailView.as_view(), name='attendance-detail'),
    # path('attendance/report/', AttendanceReportView.as_view(), name='attendance-report'),
    # path('report/', AttendanceReportView.as_view(), name='attendance-report'),
    path('', include(router.urls)),
   
]
