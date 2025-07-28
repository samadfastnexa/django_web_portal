from rest_framework import serializers
from .models import Meeting, FarmerAttendance, MeetingAttachment

# ✅ Attachment Serializer
class MeetingAttachmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = MeetingAttachment
        fields = ['id', 'file', 'uploaded_at']

# ✅ Farmer Attendance Serializer
class FarmerAttendanceSerializer(serializers.ModelSerializer):
    class Meta:
        model = FarmerAttendance
        fields = ['farmer_name', 'contact_number', 'acreage', 'crop']

# ✅ Meeting Serializer
class MeetingSerializer(serializers.ModelSerializer):
    attendees = FarmerAttendanceSerializer(many=True, write_only=True)  # used for POSTing attendees
    attachments = MeetingAttachmentSerializer(many=True, read_only=True)  # shows uploaded files (GET only)

    class Meta:
        model = Meeting
        fields = [
            'id',
            'user_id',    
            'fsm_name', 'territory', 'zone', 'region',
            'date', 'location', 'total_attendees',
            'key_topics_discussed', 'presence_of_zm_rsm',
            'feedback_from_attendees', 'suggestions_for_future',
            'attendees',      # used in POST
            'attachments'     # shown in GET
        ]

    def create(self, validated_data):
        attendees_data = validated_data.pop('attendees', [])
        meeting = Meeting.objects.create(**validated_data)
        for farmer_data in attendees_data:
            FarmerAttendance.objects.create(meeting=meeting, **farmer_data)
        return meeting