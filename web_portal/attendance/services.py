# your_app/services.py
from django.core.exceptions import ValidationError
from .models import Attendance

# def mark_attendance(user, attendee, check_type, timestamp):
#     today = timestamp.date()
#     attendance = Attendance.objects.filter(attendee=attendee, check_in_time__date=today).first()

#     if not attendance:
#         if check_type == "check_in":
#             attendance = Attendance.objects.create(user=user, attendee=attendee, check_in_time=timestamp)
#         elif check_type == "check_out":
#             attendance = Attendance.objects.create(user=user, attendee=attendee, check_out_time=timestamp)
#         return attendance

#     if check_type == "check_in":
#         if attendance.check_in_time is None or timestamp < attendance.check_in_time:
#             attendance.check_in_time = timestamp
#             attendance.save()
#     elif check_type == "check_out":
#         if attendance.check_out_time is None or timestamp > attendance.check_out_time:
#             attendance.check_out_time = timestamp
#             # _calculate_gap(attendance)
#             attendance.save()
#     return attendance

from django.core.exceptions import ValidationError
from django.utils import timezone

def mark_attendance(
    user,
    attendee,
    check_type,
    timestamp,
    latitude=None,
    longitude=None,
    attachment=None
):
    """
    Marks attendance for a given attendee on a specific date.

    Args:
        user (User): The user marking the attendance (logged-in user).
        attendee (User): The user whose attendance is being marked.
        check_type (str): Either "check_in" or "check_out".
        timestamp (datetime): The datetime for the check-in/check-out.
        latitude (Decimal, optional): GPS latitude.
        longitude (Decimal, optional): GPS longitude.
        attachment (File, optional): Any file/image attachment.

    Returns:
        Attendance: The updated or newly created Attendance record.

    Raises:
        ValidationError: If parameters are invalid.
    """

    # 1️⃣ Validate check_type
    if check_type not in ["check_in", "check_out"]:
        raise ValidationError("Invalid check_type. Must be 'check_in' or 'check_out'.")

    # 2️⃣ Prevent marking attendance in the future
    if timestamp > timezone.now():
        raise ValidationError("Attendance time cannot be in the future.")

    today = timestamp.date()

    # 3️⃣ Find an existing record for the same date
    attendance = Attendance.objects.filter(
        attendee=attendee,
        check_in_time__date=today
    ).first()

    # 4️⃣ Create a new attendance record if none exists
    if not attendance:
        if check_type == "check_in":
            attendance = Attendance.objects.create(
                user=user,
                attendee=attendee,
                check_in_time=timestamp,
                latitude=latitude,
                longitude=longitude,
                attachment=attachment
            )
        elif check_type == "check_out":
            attendance = Attendance.objects.create(
                user=user,
                attendee=attendee,
                check_out_time=timestamp,
                latitude=latitude,
                longitude=longitude,
                attachment=attachment
            )
        return attendance

    # 5️⃣ Update check-in time if earlier than current
    if check_type == "check_in":
        if attendance.check_in_time is None or timestamp < attendance.check_in_time:
            attendance.check_in_time = timestamp

    # 6️⃣ Update check-out time if later than current
    elif check_type == "check_out":
        if attendance.check_out_time is None or timestamp > attendance.check_out_time:
            attendance.check_out_time = timestamp

    # 7️⃣ Update location and attachment if provided (no overwriting with None)
    if latitude is not None:
        attendance.latitude = latitude
    if longitude is not None:
        attendance.longitude = longitude
    if attachment is not None:
        attendance.attachment = attachment

    # 8️⃣ Automatically calculate gaps if possible
    if attendance.check_in_time and not attendance.check_in_gap:
        attendance.check_in_gap = timezone.now() - attendance.check_in_time
    if attendance.check_in_time and attendance.check_out_time and not attendance.check_out_gap:
        attendance.check_out_gap = attendance.check_out_time - attendance.check_in_time

    # 9️⃣ Save updated record
    attendance.save()

    return attendance
