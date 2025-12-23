# from django.utils import timezone
# from django.core.exceptions import ValidationError
# from datetime import datetime
# from .models import Attendance, LeaveRequest, Holiday

# def mark_attendance(
#     user,
#     attendee,
#     check_type,
#     timestamp,
#     latitude=None,
#     longitude=None,
#     attachment=None
# ):
#     """
#     Marks attendance safely. Handles check_in/check_out with fallback to created_at.
#     """

#     # -----------------------
#     # 1️⃣ Validate check_type
#     # -----------------------
#     if check_type not in ["check_in", "check_out"]:
#         raise ValidationError("Invalid check_type. Must be 'check_in' or 'check_out'.")

#     # -----------------------
#     # 2️⃣ Validate timestamp
#     # -----------------------
#     if not timestamp:
#         raise ValidationError("Timestamp must be provided to mark attendance.")

#     if timestamp > timezone.now():
#         raise ValidationError("Attendance time cannot be in the future.")

#     # -----------------------
#     # 3️⃣ Safe record_date
#     # -----------------------
#     if isinstance(timestamp, datetime):
#         record_date = timestamp.date()
#     else:
#         # fallback if timestamp is a string (rare)
#         record_date = datetime.strptime(str(timestamp), "%Y-%m-%d %H:%M:%S").date()

#     # -----------------------
#     # 4️⃣ Prevent weekends/holidays for non-staff
#     # -----------------------
#     if not (user.is_staff or user.is_superuser):
#         if record_date.weekday() in [5, 6]:
#             raise ValidationError("Cannot mark attendance on weekends.")
#         if Holiday.objects.filter(date=record_date).exists():
#             raise ValidationError("Cannot mark attendance on holiday.")

#     # -----------------------
#     # 5️⃣ Prevent attendance on approved leave
#     # -----------------------
#     if not (user.is_staff or user.is_superuser):
#         leave_exists = LeaveRequest.objects.filter(
#             user=attendee,
#             status='approved',
#             start_date__lte=record_date,
#             end_date__gte=record_date
#         ).exists()
#         if leave_exists:
#             raise ValidationError("Cannot mark attendance on approved leave day.")

#     # -----------------------
#     # 6️⃣ Find existing attendance
#     # -----------------------
#     attendance = Attendance.objects.filter(
#         attendee=attendee,
#         check_in_time__date=record_date
#     ).first()

#     # -----------------------
#     # 7️⃣ Create or update attendance
#     # -----------------------
#     if not attendance:
#         attendance = Attendance.objects.create(
#             user=user,
#             attendee=attendee,
#             check_in_time=timestamp if check_type=="check_in" else None,
#             check_out_time=timestamp if check_type=="check_out" else None,
#             latitude=latitude,
#             longitude=longitude,
#             attachment=attachment
#         )
#         return attendance

#     # Update existing attendance
#     if check_type == "check_in":
#         if attendance.check_in_time is None or timestamp < attendance.check_in_time:
#             attendance.check_in_time = timestamp
#     else:  # check_out
#         if attendance.check_out_time is None or timestamp > attendance.check_out_time:
#             attendance.check_out_time = timestamp

#     if latitude is not None:
#         attendance.latitude = latitude
#     if longitude is not None:
#         attendance.longitude = longitude
#     if attachment is not None:
#         attendance.attachment = attachment

#     # Calculate gaps
#     if attendance.check_in_time and not attendance.check_in_gap:
#         attendance.check_in_gap = timezone.now() - attendance.check_in_time
#     if attendance.check_in_time and attendance.check_out_time and not attendance.check_out_gap:
#         attendance.check_out_gap = attendance.check_out_time - attendance.check_in_time

#     attendance.save()
#     return attendance

import logging
from datetime import datetime
from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone
from .models import Attendance  # make sure this import does not create circular imports

logger = logging.getLogger(__name__)

def mark_attendance(
    user,
    attendee,
    check_type,
    timestamp=None,
    latitude=None,
    longitude=None,
    check_in_image=None,
    check_out_image=None,
    source="request",  # ✅ mark source as request when called from approved AttendanceRequest
):
    """
    Centralized function to handle attendance marking.

    - Automatically creates or updates Attendance record for the day.
    - Does NOT crash if check-in/check-out already exists.
    - Updates optional fields (latitude, longitude, check_in_image, check_out_image) if provided.
    - source='request' by default to indicate it comes from a request approval.

    Returns:
        Attendance object
    Raises:
        ValidationError for invalid inputs only.
    """

    if check_type not in ["check_in", "check_out"]:
        raise ValidationError("Invalid check_type. Must be 'check_in' or 'check_out'.")

    # Normalize timestamp
    if timestamp:
        if isinstance(timestamp, str):
            try:
                timestamp = datetime.fromisoformat(timestamp)
            except Exception:
                raise ValidationError("Invalid timestamp format. Use ISO format.")
    else:
        timestamp = timezone.now()

    if timezone.is_naive(timestamp):
        timestamp = timezone.make_aware(timestamp)

    attendance_date = timezone.localtime(timestamp).date()

    try:
        with transaction.atomic():
            # Get existing attendance for this user & day or create a new one
            attendance, created = Attendance.objects.get_or_create(
                attendee=attendee,
                check_in_time__date=attendance_date if check_type == "check_in" else None,
                defaults={
                    "user": user,
                    "attendee": attendee,
                    "check_in_time": timestamp if check_type == "check_in" else None,
                    "check_out_time": timestamp if check_type == "check_out" else None,
                    "latitude": latitude,
                    "longitude": longitude,
                    "check_in_image": check_in_image if check_type == "check_in" else None,
                    "check_out_image": check_out_image if check_type == "check_out" else None,
                    "source": source,
                },
            )

            # Update existing record if needed
            if not created:
                if check_type == "check_in" and not attendance.check_in_time:
                    attendance.check_in_time = timestamp
                if check_type == "check_out" and not attendance.check_out_time:
                    # Prevent check-out without check-in
                    if not attendance.check_in_time:
                        raise ValidationError("Cannot check-out without check-in first.")
                    attendance.check_out_time = timestamp

                # Update optional fields if provided
                if latitude:
                    attendance.latitude = latitude
                if longitude:
                    attendance.longitude = longitude
                if attachment:
                    attendance.attachment = attachment

                # Always update source
                attendance.source = source

                attendance.save()

            return attendance

    except ValidationError as ve:
        # Known validation errors
        raise ve

    except Exception as e:
        # Unexpected errors logged for debugging
        logger.exception("mark_attendance failed")
        raise ValidationError(["An unexpected error occurred while marking attendance."])