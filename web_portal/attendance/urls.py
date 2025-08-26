from django.urls import path,include
from .views import AttendanceListCreateView, AttendanceDetailView
from .views import AttendanceRequestViewSet,AttendanceReportView
from .views import LeaveRequestListCreateView, LeaveRequestDetailView
from rest_framework.routers import DefaultRouter
# from .views import AttendanceReportView

router = DefaultRouter()
router.register(r'attendance-requests', AttendanceRequestViewSet, basename='attendance-request')
urlpatterns = [
    path('attendances/', AttendanceListCreateView.as_view(), name='attendance-list-create'),
    path('attendances/<int:pk>/', AttendanceDetailView.as_view(), name='attendance-detail'),
    path("attendance/report/", AttendanceReportView.as_view(), name="attendance-report"),
    
    # ✅ List + Create (with filtering, ordering, searching in Swagger)
    path("leave-requests/", LeaveRequestListCreateView.as_view(), name="leave-request-list-create"),

    # ✅ Retrieve + Update + Delete (detail view)
    path("leave-requests/<int:pk>/", LeaveRequestDetailView.as_view(), name="leave-request-detail"),
    path('', include(router.urls)),
   
]
