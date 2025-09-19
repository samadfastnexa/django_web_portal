from django.urls import path,include
from .views import (
    AttendanceIndividualView, AttendanceCheckInView, AttendanceUpdateView,
    AttendanceRequestViewSet, AttendanceReportView, 
    LeaveRequestListCreateView, LeaveRequestDetailView, AttendanceByAttendeeView,
    AttendanceStatusView
)
from rest_framework.routers import DefaultRouter
# from .views import AttendanceReportView

router = DefaultRouter()
router.register(r'attendance-requests', AttendanceRequestViewSet, basename='attendance-request')
urlpatterns = [

    path('attendances/<int:pk>/', AttendanceIndividualView.as_view(), name='attendance-individual'),
    path('attendance/check-in/', AttendanceCheckInView.as_view(), name='attendance-check-in'),
    path('attendances/attendee/<int:attendee_id>/', AttendanceByAttendeeView.as_view(), name='attendance-by-attendee'),
    path('attendances/attendee/<int:attendee_id>/update/', AttendanceUpdateView.as_view(), name='attendance-update'),
    path('attendances/status/today/', AttendanceStatusView.as_view(), name='attendance-status-today'),

    path("attendance/report/", AttendanceReportView.as_view(), name="attendance-report"),
    
    # ✅ List + Create (with filtering, ordering, searching in Swagger)
    path("leave-requests/", LeaveRequestListCreateView.as_view(), name="leave-request-list-create"),

    # ✅ Retrieve + Update + Delete (detail view)
    path("leave-requests/<int:pk>/", LeaveRequestDetailView.as_view(), name="leave-request-detail"),
    path('', include(router.urls)),
   
]
