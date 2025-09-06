# AttendanceReportView.py

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.utils.timezone import now
from datetime import timedelta
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

from django.contrib.auth import get_user_model
from .models import Attendance
from .serializers import AttendanceReportSerializer
from accounts.permissions import HasRolePermission
User = get_user_model()

class AttendanceReportView(APIView):
    # permission_classes = [IsAuthenticated]
    permission_classes = [IsAuthenticated, HasRolePermission]
    
    @swagger_auto_schema(
        operation_description="Generate attendance report for users (weekly or monthly)",
        manual_parameters=[
            openapi.Parameter(
                'type',
                openapi.IN_QUERY,
                description='Report type: "weekly" or "monthly"',
                type=openapi.TYPE_STRING,
                default='weekly',
                enum=['weekly', 'monthly']
            )
        ],
        responses={
            200: openapi.Response(
                description='Attendance report data',
                examples={
                    'application/json': {
                        'report_type': 'weekly',
                        'start_date': '2025-01-01',
                        'end_date': '2025-01-07',
                        'users': [
                            {
                                'user_id': 1,
                                'username': 'john_doe',
                                'total_days': 5,
                                'present_days': 4,
                                'absent_days': 1,
                                'attendance_percentage': 80.0
                            }
                        ]
                    }
                }
            )
        },
        tags=['11. Attendance Report']
    )
    def get(self, request):
        report_type = request.query_params.get("type", "weekly")
        today = now().date()

        if report_type == "monthly":
            start_date = today.replace(day=1)
        else:
            start_date = today - timedelta(days=today.weekday())

        end_date = today

        report_data = []
        users = User.objects.all()

        for user in users:
            attendances = Attendance.objects.filter(
                user=user,
                check_in_time__date__gte=start_date,
                check_in_time__date__lte=end_date
            )

            total_seconds = 0
            for att in attendances:
                if att.check_in_time and att.check_out_time:
                    total_seconds += (att.check_out_time - att.check_in_time).total_seconds()

            total_hours = round(total_seconds / 3600, 2)

            report_data.append({
                "user_id": user.id,
                "email": user.email,
                "total_hours": total_hours,
                "report_type": report_type,
                "start_date": start_date,
                "end_date": end_date,
            })

        serializer = AttendanceReportSerializer(report_data, many=True)
        return Response(serializer.data)
