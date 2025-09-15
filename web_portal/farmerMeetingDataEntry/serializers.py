from rest_framework import serializers
from .models import Meeting, FarmerAttendance, MeetingAttachment, FieldDay, FieldDayAttendance
import json

# ✅ Attachment Serializer (define this FIRST)
class MeetingAttachmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = MeetingAttachment
        fields = ['id', 'file', 'uploaded_at']


# ✅ Farmer Attendance Serializer (for read operations)
class FarmerAttendanceSerializer(serializers.ModelSerializer):
    class Meta:
        model = FarmerAttendance
        fields = ['farmer_name', 'contact_number', 'acreage', 'crop']


# ✅ Farmer Attendance Input Serializer (for form input)
class FarmerAttendanceInputSerializer(serializers.Serializer):
    farmer_name = serializers.CharField(max_length=100)
    contact_number = serializers.CharField(max_length=20, required=False, allow_blank=True)
    acreage = serializers.DecimalField(max_digits=10, decimal_places=2, required=False, allow_null=True)
    crop = serializers.CharField(max_length=100, required=False, allow_blank=True)


# ✅ Meeting Serializer
class MeetingSerializer(serializers.ModelSerializer):
    attendees = serializers.SerializerMethodField(read_only=True)
    attachments = MeetingAttachmentSerializer(many=True, read_only=True)
    
     # IDs (writable on create/update)
    company_id   = serializers.IntegerField(source='company_fk_id',   required=False, allow_null=True)
    region_id   = serializers.IntegerField(source='region_fk_id',   required=False, allow_null=True)
    zone_id     = serializers.IntegerField(source='zone_fk_id',     required=False, allow_null=True)
    territory_id = serializers.IntegerField(source='territory_fk_id', required=False, allow_null=True)

    # Human-readable names
    company_name = serializers.CharField(source='company_fk.Company_name', read_only=True)
    region_name  = serializers.CharField(source='region_fk.name',   read_only=True)
    zone_name    = serializers.CharField(source='zone_fk.name',     read_only=True)
    territory_name = serializers.CharField(source='territory_fk.name', read_only=True)
    
    # Multiple fields for attendee input (more user-friendly)
    attendee_name = serializers.ListField(
        child=serializers.CharField(),
        write_only=True,
        required=False,
        help_text="List of farmer names"
    )
    attendee_contact = serializers.ListField(
        child=serializers.CharField(),
        write_only=True,
        required=False,
        help_text="List of contact numbers"
    )
    attendee_acreage = serializers.ListField(
        child=serializers.DecimalField(max_digits=10, decimal_places=2),
        write_only=True,
        required=False,
        help_text="List of acreage values"
    )
    attendee_crop = serializers.ListField(
        child=serializers.CharField(),
        write_only=True,
        required=False,
        help_text="List of crops"
    )

    class Meta:
        model = Meeting
        fields = [
            'id', 'user_id', 'fsm_name',
            'company_id', 'company_name',
            'region_id', 'region_name',
            'zone_id', 'zone_name',
            'territory_id', 'territory_name',
            'date', 'location', 'total_attendees',
            'key_topics_discussed', 'presence_of_zm_rsm',
            'feedback_from_attendees', 'suggestions_for_future',
            'attendees', 'attachments',
            # attendee write-only lists (keep as-is)
            'attendee_name', 'attendee_contact', 'attendee_acreage', 'attendee_crop',
        ]

    def get_attendees(self, obj):
        """Return serialized attendees for read operations"""
        attendees = obj.attendees.all()
        return FarmerAttendanceSerializer(attendees, many=True).data

    def create(self, validated_data):
        # Extract attendee data from multiple fields
        names = validated_data.pop('attendee_name', [])
        contacts = validated_data.pop('attendee_contact', [])
        acreages = validated_data.pop('attendee_acreage', [])
        crops = validated_data.pop('attendee_crop', [])
        
        request = self.context.get("request")

        # ✅ Create the meeting first
        meeting = Meeting.objects.create(**validated_data)

        # ✅ Save attendees from multiple fields
        for i, name in enumerate(names):
            FarmerAttendance.objects.create(
                meeting=meeting,
                farmer_name=name,
                contact_number=contacts[i] if i < len(contacts) else '',
                acreage=acreages[i] if i < len(acreages) else None,
                crop=crops[i] if i < len(crops) else ''
            )

        # ✅ Save uploaded files
        if request and request.FILES:
            for f in request.FILES.getlist("attachments"):
                MeetingAttachment.objects.create(meeting=meeting, file=f)

        return meeting

    def update(self, instance, validated_data):
        # Extract attendee data from multiple fields
        names = validated_data.pop('attendee_name', None)
        contacts = validated_data.pop('attendee_contact', None)
        acreages = validated_data.pop('attendee_acreage', None)
        crops = validated_data.pop('attendee_crop', None)
        
        request = self.context.get("request")
        
        # Update other fields
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        
        # Process attendees if provided
        if names is not None:
            # Clear existing attendees
            instance.attendees.all().delete()
            
            # Add new attendees
            for i, name in enumerate(names):
                FarmerAttendance.objects.create(
                    meeting=instance,
                    farmer_name=name,
                    contact_number=contacts[i] if contacts and i < len(contacts) else '',
                    acreage=acreages[i] if acreages and i < len(acreages) else None,
                    crop=crops[i] if crops and i < len(crops) else ''
                )
        
        # Handle file uploads
        if request and request.FILES:
            for f in request.FILES.getlist("attachments"):
                MeetingAttachment.objects.create(meeting=instance, file=f)
                
        return instance
    
# ✅ Field Day Attendance Serializer (for read operations)
class FieldDayAttendanceSerializer(serializers.ModelSerializer):
    class Meta:
        model = FieldDayAttendance
        fields = ['id', 'farmer_name', 'contact_number', 'acreage', 'crop']


# ✅ Field Day Serializer (similar to MeetingSerializer)
class FieldDaySerializer(serializers.ModelSerializer):
    attendees = serializers.SerializerMethodField(read_only=True)

      # IDs (writable on create/update)
    company_id   = serializers.IntegerField(source='company_fk_id',   required=False, allow_null=True)
    region_id   = serializers.IntegerField(source='region_fk_id',   required=False, allow_null=True)
    zone_id     = serializers.IntegerField(source='zone_fk_id',     required=False, allow_null=True)
    territory_id = serializers.IntegerField(source='territory_fk_id', required=False, allow_null=True)

    # Human-readable names
    company_name = serializers.CharField(source='company_fk.Company_name', read_only=True)
    region_name  = serializers.CharField(source='region_fk.name',   read_only=True)
    zone_name    = serializers.CharField(source='zone_fk.name',     read_only=True)
    territory_name = serializers.CharField(source='territory_fk.name', read_only=True)
    
    # Multiple fields for attendee input (like MeetingSerializer)
    attendee_name = serializers.ListField(
        child=serializers.CharField(),
        write_only=True,
        required=False,
        help_text="List of farmer names"
    )
    attendee_contact = serializers.ListField(
        child=serializers.CharField(),
        write_only=True,
        required=False,
        help_text="List of contact numbers"
    )
    attendee_acreage = serializers.ListField(
        child=serializers.DecimalField(max_digits=10, decimal_places=2),
        write_only=True,
        required=False,
        help_text="List of acreage values"
    )
    attendee_crop = serializers.ListField(
        child=serializers.CharField(),
        write_only=True,
        required=False,
        help_text="List of crops"
    )

    class Meta:
        model = FieldDay
        fields = [
            "id", "title",
            "company_id", "company_name",
            "region_id", "region_name",
            "zone_id", "zone_name",
            "territory_id", "territory_name",
            "date", "location", "objectives", "remarks",
            "status", "attendees",
            "attendee_name", "attendee_contact", "attendee_acreage", "attendee_crop",
            "user", "is_active"
        ]
        read_only_fields = ["user"]

    def get_attendees(self, obj):
        """Return serialized attendees for read operations"""
        attendees = obj.attendees.all()
        return FieldDayAttendanceSerializer(attendees, many=True).data

    def create(self, validated_data):
        # Extract attendee data
        names = validated_data.pop('attendee_name', [])
        contacts = validated_data.pop('attendee_contact', [])
        acreages = validated_data.pop('attendee_acreage', [])
        crops = validated_data.pop('attendee_crop', [])

        # ✅ Create the field day
        field_day = FieldDay.objects.create(**validated_data, user=self.context["request"].user)

        # ✅ Save attendees
        for i, name in enumerate(names):
            FieldDayAttendance.objects.create(
                field_day=field_day,
                farmer_name=name,
                contact_number=contacts[i] if i < len(contacts) else '',
                acreage=acreages[i] if i < len(acreages) else None,
                crop=crops[i] if i < len(crops) else ''
            )

        return field_day

    def update(self, instance, validated_data):
        # Extract attendee data
        names = validated_data.pop('attendee_name', None)
        contacts = validated_data.pop('attendee_contact', None)
        acreages = validated_data.pop('attendee_acreage', None)
        crops = validated_data.pop('attendee_crop', None)

        # Update other fields
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        # If attendee data is provided, replace old ones
        if names is not None:
            instance.attendees.all().delete()
            for i, name in enumerate(names):
                FieldDayAttendance.objects.create(
                    field_day=instance,
                    farmer_name=name,
                    contact_number=contacts[i] if contacts and i < len(contacts) else '',
                    acreage=acreages[i] if acreages and i < len(acreages) else None,
                    crop=crops[i] if crops and i < len(crops) else ''
                )

        return instance
