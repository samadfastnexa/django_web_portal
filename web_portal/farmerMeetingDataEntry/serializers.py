from rest_framework import serializers
from .models import Meeting, FarmerAttendance, MeetingAttachment, FieldDay, FieldDayAttendance, FieldDayAttachment, FieldDayAttendanceCrop
from farmers.models import Farmer
import json


# Custom field to handle both list and comma-separated string formats
class FlexibleListField(serializers.ListField):
    """
    A custom field that accepts both:
    1. Proper list format: ['85', '84']
    2. Comma-separated string format: '85,84'
    
    This ensures backward compatibility with different frontend implementations.
    """
    
    def to_internal_value(self, data):
        """
        Convert input data to a list of strings.
        Handles both list and comma-separated string formats.
        Special handling for Swagger UI which may send comma-separated strings as single array items.
        """
        if not data:
            return []
        
        # If data is a string, split it by comma and strip whitespace
        if isinstance(data, str):
            if ',' in data:
                return [item.strip() for item in data.split(',') if item.strip()]
            else:
                return [data.strip()] if data.strip() else []
        
        # If data is a list, process each item
        if isinstance(data, list):
            result = []
            for item in data:
                if isinstance(item, str):
                    # Handle comma-separated strings within list items (common with Swagger UI)
                    if ',' in item:
                        sub_items = [sub_item.strip() for sub_item in item.split(',') if sub_item.strip()]
                        result.extend(sub_items)
                    else:
                        if item.strip():
                            result.append(item.strip())
                else:
                    # Convert non-string items to string
                    result.append(str(item))
            return result
        
        # For any other type, convert to string
        return [str(data)]


# ✅ Attachment Serializer (define this FIRST)
class MeetingAttachmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = MeetingAttachment
        fields = ['id', 'file', 'uploaded_at']

# ✅ Field Day Attachment Serializer
class FieldDayAttachmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = FieldDayAttachment
        fields = ['id', 'file', 'uploaded_at']


# ✅ Farmer Attendance Serializer (for read operations)
class FarmerAttendanceSerializer(serializers.ModelSerializer):
    # Include farmer information if linked
    farmer_id = serializers.CharField(source='farmer.farmer_id', read_only=True)
    farmer_full_name = serializers.CharField(source='farmer.full_name', read_only=True)
    farmer_primary_phone = serializers.CharField(source='farmer.primary_phone', read_only=True)
    farmer_district = serializers.CharField(source='farmer.district', read_only=True)
    farmer_village = serializers.CharField(source='farmer.village', read_only=True)
    
    class Meta:
        model = FarmerAttendance
        fields = [
            'id', 'farmer', 'farmer_id', 'farmer_full_name', 'farmer_primary_phone', 
            'farmer_district', 'farmer_village', 'farmer_name', 'contact_number', 
            'acreage', 'crop'
        ]
    
    def to_representation(self, instance):
        """Ensure farmer_name and contact_number are populated from linked farmer"""
        representation = super().to_representation(instance)
        
        # If farmer is linked, populate farmer_name and contact_number from farmer data
        if instance.farmer:
            representation['farmer_name'] = instance.farmer.full_name or ''
            representation['contact_number'] = instance.farmer.primary_phone or ''
        
        return representation


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
    location = serializers.CharField(max_length=200, required=False)
    
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
    
    # Farmer linking field
    attendee_farmer_id = FlexibleListField(
        child=serializers.CharField(),
        write_only=True,
        required=False,
        help_text="List of farmer IDs to link existing farmers. When provided, attendee_name and attendee_contact are auto-filled from farmer records. Supports multiple formats: Array [80, 84], Array of strings ['80', '84'], or Comma-separated string '80,84'. Example: [1, 2, 3]"
    )
    
    # Multiple fields for attendee input (more user-friendly)
    attendee_name = serializers.ListField(
        child=serializers.CharField(),
        write_only=True,
        required=False,
        help_text="List of farmer names (used when not linking existing farmers)"
    )
    attendee_contact = serializers.ListField(
        child=serializers.CharField(),
        write_only=True,
        required=False,
        help_text="List of contact numbers (used when not linking existing farmers)"
    )
    attendee_acreage = FlexibleListField(
        child=serializers.DecimalField(max_digits=10, decimal_places=2),
        write_only=True,
        required=False,
        help_text="List of acreage values"
    )
    attendee_crop = FlexibleListField(
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
            'key_topics_discussed', 'products_discussed', 'presence_of_zm', 'presence_of_rsm',
            'feedback_from_attendees', 'suggestions_for_future',
            'attendees', 'attachments',
            # attendee write-only lists (keep as-is)
            'attendee_farmer_id', 'attendee_name', 'attendee_contact', 'attendee_acreage', 'attendee_crop',
        ]

    def get_attendees(self, obj):
        """Return serialized attendees for read operations"""
        attendees = obj.attendees.all()
        return FarmerAttendanceSerializer(attendees, many=True).data

    def create(self, validated_data):
        # Extract attendee data from multiple fields
        farmer_ids = validated_data.pop('attendee_farmer_id', [])
        names = validated_data.pop('attendee_name', [])
        contacts = validated_data.pop('attendee_contact', [])
        acreages = validated_data.pop('attendee_acreage', [])
        crops = validated_data.pop('attendee_crop', [])
        
        request = self.context.get("request")

        # ✅ Create the meeting first
        meeting = Meeting.objects.create(**validated_data)

        # ✅ Handle farmer linking if farmer IDs are provided
        if farmer_ids:
            for i, farmer_id in enumerate(farmer_ids):
                try:
                    # Use pk (primary key/id) instead of farmer_id field
                    farmer = Farmer.objects.get(pk=farmer_id)
                    FarmerAttendance.objects.create(
                        meeting=meeting,
                        farmer=farmer,
                        farmer_name=farmer.name or f"{farmer.first_name} {farmer.last_name}".strip(),
                        contact_number=farmer.primary_phone or '',
                        acreage=acreages[i] if i < len(acreages) else 0.0,
                        crop=crops[i] if i < len(crops) else ''
                    )
                except Farmer.DoesNotExist:
                    # If farmer not found, create attendance without farmer link
                    FarmerAttendance.objects.create(
                        meeting=meeting,
                        farmer_name=names[i] if i < len(names) else f'Unknown Farmer {farmer_id}',
                        contact_number=contacts[i] if i < len(contacts) else '',
                        acreage=acreages[i] if i < len(acreages) else 0.0,
                        crop=crops[i] if i < len(crops) else ''
                    )
        else:
            # ✅ Save attendees from manual input (when no farmer IDs provided)
            for i, name in enumerate(names):
                FarmerAttendance.objects.create(
                    meeting=meeting,
                    farmer_name=name,
                    contact_number=contacts[i] if i < len(contacts) else '',
                    acreage=acreages[i] if i < len(acreages) else 0.0,
                    crop=crops[i] if i < len(crops) else ''
                )

        # ✅ Save uploaded files
        if request and request.FILES:
            for f in request.FILES.getlist("attachments"):
                MeetingAttachment.objects.create(meeting=meeting, file=f)

        return meeting

    def update(self, instance, validated_data):
        # Extract attendee data from multiple fields
        farmer_ids = validated_data.pop('attendee_farmer_id', None)
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
        if farmer_ids is not None or names is not None:
            # Clear existing attendees
            instance.attendees.all().delete()
            
            # Handle farmer linking if farmer IDs are provided
            if farmer_ids:
                for i, farmer_id in enumerate(farmer_ids):
                    try:
                        # Use pk (primary key/id) instead of farmer_id field
                        farmer = Farmer.objects.get(pk=farmer_id)
                        FarmerAttendance.objects.create(
                            meeting=instance,
                            farmer=farmer,
                            farmer_name=farmer.name or f"{farmer.first_name} {farmer.last_name}".strip(),
                            contact_number=farmer.primary_phone or '',
                            acreage=acreages[i] if acreages and i < len(acreages) else 0.0,
                            crop=crops[i] if crops and i < len(crops) else ''
                        )
                    except Farmer.DoesNotExist:
                        # If farmer not found, create attendance without farmer link
                        FarmerAttendance.objects.create(
                            meeting=instance,
                            farmer_name=names[i] if names and i < len(names) else f'Unknown Farmer {farmer_id}',
                            contact_number=contacts[i] if contacts and i < len(contacts) else '',
                            acreage=acreages[i] if acreages and i < len(acreages) else 0.0,
                            crop=crops[i] if crops and i < len(crops) else ''
                        )
            elif names:
                # Add new attendees from manual input
                for i, name in enumerate(names):
                    FarmerAttendance.objects.create(
                        meeting=instance,
                        farmer_name=name,
                        contact_number=contacts[i] if contacts and i < len(contacts) else '',
                        acreage=acreages[i] if acreages and i < len(acreages) else 0.0,
                        crop=crops[i] if crops and i < len(crops) else ''
                    )
        
        # Handle file uploads
        if request and request.FILES:
            for f in request.FILES.getlist("attachments"):
                MeetingAttachment.objects.create(meeting=instance, file=f)
                
        return instance
    
# ✅ Field Day Attendance Crop Serializer
class FieldDayAttendanceCropSerializer(serializers.ModelSerializer):
    class Meta:
        model = FieldDayAttendanceCrop
        fields = ['id', 'crop_name', 'acreage']


# ✅ Field Day Attendance Serializer (for read operations)
class FieldDayAttendanceSerializer(serializers.ModelSerializer):
    # ✅ Farmer information fields (read-only, auto-populated)
    farmer_id = serializers.CharField(source='farmer.farmer_id', read_only=True)
    farmer_full_name = serializers.CharField(source='farmer.full_name', read_only=True)
    farmer_primary_phone = serializers.CharField(source='farmer.primary_phone', read_only=True)
    farmer_district = serializers.CharField(source='farmer.district', read_only=True)
    farmer_village = serializers.CharField(source='farmer.village', read_only=True)
    
    # ✅ New crops relationship
    crops = FieldDayAttendanceCropSerializer(many=True, read_only=True)
    
    class Meta:
        model = FieldDayAttendance
        fields = [
            'id', 'farmer', 'farmer_id', 'farmer_full_name', 'farmer_primary_phone', 
            'farmer_district', 'farmer_village', 'farmer_name', 'contact_number', 
            'acreage', 'crops'
        ]
    
    def to_representation(self, instance):
        """Ensure farmer_name and contact_number are populated from linked farmer"""
        representation = super().to_representation(instance)
        
        # If farmer is linked, populate farmer_name and contact_number from farmer data
        if instance.farmer:
            representation['farmer_name'] = instance.farmer.full_name or ''
            representation['contact_number'] = instance.farmer.primary_phone or ''
        
        return representation
        
    def create(self, validated_data):
        # ✅ Auto-populate farmer information if farmer is linked
        attendance = super().create(validated_data)
        if attendance.farmer:
            attendance.farmer_name = attendance.farmer.full_name
            attendance.contact_number = attendance.farmer.primary_phone
            attendance.save()
            
        return attendance
        
    def update(self, instance, validated_data):
        # ✅ Auto-populate farmer information if farmer is changed
        attendance = super().update(instance, validated_data)
        if attendance.farmer:
            attendance.farmer_name = attendance.farmer.full_name
            attendance.contact_number = attendance.farmer.primary_phone
            attendance.save()
            
        return attendance


# ✅ Field Day Serializer (similar to MeetingSerializer)
class FieldDaySerializer(serializers.ModelSerializer):
    attendees = serializers.SerializerMethodField(read_only=True)
    attachments = FieldDayAttachmentSerializer(many=True, read_only=True)
    
    # Field mapping for API parameter name
    fsm_name = serializers.CharField(source='title', max_length=200, help_text="Name of FSM", required=False)
    location = serializers.CharField(max_length=200, required=False)

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
    # Option 1: Link existing farmers by farmer_id
    attendee_farmer_id = FlexibleListField(
        child=serializers.CharField(),
        write_only=True,
        required=False,
        help_text="List of farmer IDs to link existing farmers. When provided, attendee_name, attendee_contact, and attendee_acreage are auto-filled from farmer records. Supports multiple formats: Array [80, 84], Array of strings ['80', '84'], or Comma-separated string '80,84'. Example: [1, 2, 3]"
    )
    
    # Option 2: Manual entry (for backward compatibility)
    attendee_name = serializers.ListField(
        child=serializers.CharField(),
        write_only=True,
        required=False,
        help_text="List of farmer names (used when not linking existing farmers)"
    )
    attendee_contact = serializers.ListField(
        child=serializers.CharField(),
        write_only=True,
        required=False,
        help_text="List of contact numbers (used when not linking existing farmers)"
    )
    
    # Common fields for both options
    attendee_acreage = FlexibleListField(
        child=serializers.DecimalField(max_digits=10, decimal_places=2),
        write_only=True,
        required=False,
        help_text="List of acreage values for this field day"
    )
    attendee_crop = FlexibleListField(
        child=serializers.CharField(),
        write_only=True,
        required=False,
        help_text="List of crops for farmer attendees. Supports multiple formats: 1) Individual crops ['rice', 'wheat'] with repeated farmer IDs for precise acreage control, 2) Comma-separated crops ['rice,wheat'] for equal acreage distribution, 3) Mixed formats ['rice,wheat', 'cotton']. When using comma-separated crops with single farmer ID, acreage is automatically distributed equally among crops. Example: attendee_farmer_id=['68'], attendee_crop=['rice,wheat'], attendee_acreage=[6.0] creates rice (3.0 acres) and wheat (3.0 acres) for farmer 68."
    )

    class Meta:
        model = FieldDay
        fields = [
            "id", "fsm_name",
            "company_id", "company_name",
            "region_id", "region_name",
            "zone_id", "zone_name",
            "territory_id", "territory_name",
            "date", "location", "total_participants", "demonstrations_conducted", "feedback",
            "attendees", "attachments",
            "attendee_farmer_id", "attendee_name", "attendee_contact", "attendee_acreage", "attendee_crop",
            "user", "is_active"
        ]
        read_only_fields = ["user", "is_active"]

    def get_attendees(self, obj):
        """Return serialized attendees for read operations, consolidating multiple crops per farmer"""
        from collections import defaultdict
        
        attendees = obj.attendees.prefetch_related('crops', 'farmer').all()
        
        # Group attendees by farmer
        farmer_groups = defaultdict(list)
        for attendee in attendees:
            farmer_key = attendee.farmer.id if attendee.farmer else f"manual_{attendee.farmer_name}_{attendee.contact_number}"
            farmer_groups[farmer_key].append(attendee)
        
        consolidated_attendees = []
        
        for farmer_key, farmer_attendees in farmer_groups.items():
            # Use the first attendee as the base record
            primary_attendee = farmer_attendees[0]
            
            # Collect all crops from all attendee records for this farmer
            all_crops = []
            total_acreage = 0
            
            for attendee in farmer_attendees:
                # Add crops from the crops relationship
                for crop in attendee.crops.all():
                    all_crops.append({
                        'id': crop.id,
                        'crop_name': crop.crop_name,
                        'acreage': float(crop.acreage)
                    })
                    total_acreage += float(crop.acreage)
                
                # If no crops in relationship but has primary crop, add it
                if not attendee.crops.exists() and attendee.crop:
                    all_crops.append({
                        'id': None,  # No separate crop record
                        'crop_name': attendee.crop,
                        'acreage': float(attendee.acreage) if attendee.acreage else 0.0
                    })
                    total_acreage += float(attendee.acreage) if attendee.acreage else 0.0
            
            # Create consolidated attendee data
            attendee_data = {
                'id': primary_attendee.id,
                'farmer': primary_attendee.farmer.id if primary_attendee.farmer else None,
                'farmer_id': primary_attendee.farmer.farmer_id if primary_attendee.farmer else '',
                'farmer_primary_phone': primary_attendee.farmer.primary_phone if primary_attendee.farmer else '',
                'farmer_district': primary_attendee.farmer.district if primary_attendee.farmer else '',
                'farmer_village': primary_attendee.farmer.village if primary_attendee.farmer else '',
                'farmer_name': primary_attendee.farmer.full_name if primary_attendee.farmer else (primary_attendee.farmer_name or ''),
                'contact_number': primary_attendee.farmer.primary_phone if primary_attendee.farmer else (primary_attendee.contact_number or ''),
                'acreage': total_acreage,
                'crop': all_crops[0]['crop_name'] if all_crops else primary_attendee.crop,  # Primary crop
                'crops': all_crops
            }
            
            consolidated_attendees.append(attendee_data)
        
        return consolidated_attendees

    def create(self, validated_data):
        from farmers.models import Farmer
        
        # Extract attendee data from multiple fields
        farmer_ids = validated_data.pop('attendee_farmer_id', [])
        names = validated_data.pop('attendee_name', [])
        contacts = validated_data.pop('attendee_contact', [])
        acreages = validated_data.pop('attendee_acreage', [])
        crops = validated_data.pop('attendee_crop', [])
        
        request = self.context.get("request")

        # ✅ Create the field day first
        user = request.user if request and request.user.is_authenticated else None
        field_day = FieldDay.objects.create(**validated_data, user=user, is_active=True)

        # ✅ Handle farmer linking (Option 1: Link existing farmers)
        if farmer_ids:
            # Debug logging to help identify crop distribution issues
            print(f"DEBUG: farmer_ids = {farmer_ids}")
            print(f"DEBUG: crops = {crops}")
            print(f"DEBUG: acreages = {acreages}")
            
            # Handle case where crops array is longer than farmer_ids due to comma-separated expansion
            if len(crops) > len(farmer_ids):
                # Expand farmer_ids and acreages to match crops length
                # This handles the case where FlexibleListField expanded "rice,wheat" into ['rice', 'wheat']
                # but we only have one farmer_id
                expanded_farmer_ids = []
                expanded_acreages = []
                
                original_crop_data = self.initial_data.get('attendee_crop', [])
                
                # Handle both array and string formats
                if isinstance(original_crop_data, list):
                    # Array format: ['wheat', 'potato,rice']
                    # Each array element corresponds to a farmer
                    for i, farmer_id in enumerate(farmer_ids):
                        original_crop_string = original_crop_data[i] if i < len(original_crop_data) else ''
                        
                        # Count how many crops this farmer should have
                        if original_crop_string and ',' in str(original_crop_string):
                            crop_count = len([c.strip() for c in str(original_crop_string).split(',') if c.strip()])
                        else:
                            crop_count = 1
                        
                        # Get the acreage for this farmer (to be distributed among crops)
                        farmer_acreage = float(acreages[i]) if i < len(acreages) else 0.0
                        acreage_per_crop = farmer_acreage / crop_count if crop_count > 0 else 0.0
                        
                        # Add entries for each crop
                        for _ in range(crop_count):
                            expanded_farmer_ids.append(farmer_id)
                            expanded_acreages.append(acreage_per_crop)
                
                elif isinstance(original_crop_data, str):
                    # String format: 'wheat,potato,rice'
                    # Need to distribute crops among farmers based on acreage ratios
                    
                    # Calculate total acreage to determine distribution
                    total_acreage = sum(float(a) for a in acreages)
                    
                    if total_acreage > 0:
                        # Distribute crops proportionally based on acreage
                        for i, farmer_id in enumerate(farmer_ids):
                            farmer_acreage = float(acreages[i]) if i < len(acreages) else 0.0
                            acreage_ratio = farmer_acreage / total_acreage
                            
                            # Calculate how many crops this farmer should get
                            crops_for_farmer = max(1, round(len(crops) * acreage_ratio))
                            
                            # Ensure we don't exceed available crops
                            remaining_crops = len(crops) - len(expanded_farmer_ids)
                            crops_for_farmer = min(crops_for_farmer, remaining_crops)
                            
                            # If this is the last farmer, give them all remaining crops
                            if i == len(farmer_ids) - 1:
                                crops_for_farmer = remaining_crops
                            
                            # Calculate acreage per crop for this farmer
                            acreage_per_crop = farmer_acreage / crops_for_farmer if crops_for_farmer > 0 else 0.0
                            
                            # Add entries for each crop
                            for _ in range(crops_for_farmer):
                                expanded_farmer_ids.append(farmer_id)
                                expanded_acreages.append(acreage_per_crop)
                    else:
                        # If no acreage specified, distribute evenly
                        crops_per_farmer = len(crops) // len(farmer_ids)
                        remaining_crops = len(crops) % len(farmer_ids)
                        
                        for i, farmer_id in enumerate(farmer_ids):
                            # Give each farmer the base number of crops
                            farmer_crop_count = crops_per_farmer
                            
                            # Give remaining crops to the last farmers
                            if i >= len(farmer_ids) - remaining_crops:
                                farmer_crop_count += 1
                            
                            # Add entries for each crop
                            for _ in range(farmer_crop_count):
                                expanded_farmer_ids.append(farmer_id)
                                expanded_acreages.append(0.0)
                
                # Use the expanded arrays
                farmer_ids = expanded_farmer_ids
                acreages = expanded_acreages
                
                print(f"DEBUG: Expanded farmer_ids = {farmer_ids}")
                print(f"DEBUG: Expanded acreages = {acreages}")
            
            # Group crops by farmer to create consolidated attendance records
            from collections import defaultdict
            farmer_crop_data = defaultdict(list)
            
            # Group all crop data by farmer
            for i, farmer_id in enumerate(farmer_ids):
                attendee_crop = crops[i] if i < len(crops) else ''
                attendee_acreage = acreages[i] if i < len(acreages) else 0.0
                
                farmer_crop_data[farmer_id].append({
                    'crop': attendee_crop,
                    'acreage': attendee_acreage
                })
                
                print(f"DEBUG: Attendee {i} (farmer_id={farmer_id}) -> crop='{attendee_crop}', acreage={attendee_acreage}")
            
            # Create one attendance record per farmer with all their crops
            for farmer_id, crop_list in farmer_crop_data.items():
                # Calculate total acreage for this farmer
                total_acreage = sum(crop_data['acreage'] for crop_data in crop_list)
                
                # Use the first crop as the primary crop
                primary_crop = crop_list[0]['crop'] if crop_list else ''
                
                print(f"DEBUG: Creating consolidated attendance for farmer {farmer_id} with {len(crop_list)} crops, total acreage: {total_acreage}")
                
                try:
                    # Try to get farmer by database ID first (if it's a number)
                    try:
                        farmer_db_id = int(farmer_id)
                        farmer = Farmer.objects.get(id=farmer_db_id)
                    except (ValueError, TypeError):
                        # If not a number, try by farmer_id field
                        farmer = Farmer.objects.get(farmer_id=farmer_id)
                    
                    # Create one attendance record for this farmer
                    attendance = FieldDayAttendance.objects.create(
                        field_day=field_day,
                        farmer=farmer,
                        acreage=total_acreage,
                        crop=primary_crop
                    )
                    
                    # Create individual crop records for all crops
                    for crop_data in crop_list:
                        FieldDayAttendanceCrop.objects.create(
                            attendance=attendance,
                            crop_name=crop_data['crop'],
                            acreage=crop_data['acreage']
                        )
                        
                except Farmer.DoesNotExist:
                    # If farmer doesn't exist, create attendance without farmer link
                    attendance = FieldDayAttendance.objects.create(
                        field_day=field_day,
                        farmer_name=f"Unknown Farmer ({farmer_id})",
                        contact_number='',
                        acreage=total_acreage,
                        crop=primary_crop
                    )
                    
                    # Create individual crop records for all crops
                    for crop_data in crop_list:
                        FieldDayAttendanceCrop.objects.create(
                            attendance=attendance,
                            crop_name=crop_data['crop'],
                            acreage=crop_data['acreage']
                        )
        
        # ✅ Handle manual entry (Option 2: For backward compatibility)
        elif names:
            # Debug logging for manual entry
            print(f"DEBUG: names = {names}")
            print(f"DEBUG: contacts = {contacts}")
            print(f"DEBUG: crops = {crops}")
            print(f"DEBUG: acreages = {acreages}")
            
            for i, name in enumerate(names):
                # Get the data for this specific attendee
                attendee_contact = contacts[i] if i < len(contacts) else ''
                attendee_acreage = acreages[i] if i < len(acreages) else 0.0
                attendee_crop = crops[i] if i < len(crops) else ''
                
                print(f"DEBUG: Attendee {i} (name={name}) -> crop='{attendee_crop}', contact='{attendee_contact}', acreage={attendee_acreage}")
                
                attendance = FieldDayAttendance.objects.create(
                    field_day=field_day,
                    farmer_name=name,
                    contact_number=attendee_contact,
                    acreage=attendee_acreage,
                    crop=attendee_crop
                )
                # Create individual crop records from the old crop field
                self._create_crops_from_old_format(attendance, attendee_crop)

        # ✅ Save uploaded files
        if request and request.FILES:
            for f in request.FILES.getlist("attachments"):
                FieldDayAttachment.objects.create(field_day=field_day, file=f)

        return field_day

    def update(self, instance, validated_data):
        from farmers.models import Farmer
        
        # Extract attendee data from multiple fields
        farmer_ids = validated_data.pop('attendee_farmer_id', None)
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
        if farmer_ids is not None or names is not None:
            # Clear existing attendees
            instance.attendees.all().delete()
            
            # ✅ Handle farmer linking (Option 1: Link existing farmers)
            if farmer_ids:
                for i, farmer_id in enumerate(farmer_ids):
                    try:
                        # Try to get farmer by database ID first (if it's a number)
                        try:
                            farmer_db_id = int(farmer_id)
                            farmer = Farmer.objects.get(id=farmer_db_id)
                        except (ValueError, TypeError):
                            # If not a number, try by farmer_id field
                            farmer = Farmer.objects.get(farmer_id=farmer_id)
                        
                        attendance = FieldDayAttendance.objects.create(
                            field_day=instance,
                            farmer=farmer,
                            acreage=acreages[i] if acreages and i < len(acreages) else 0.0,
                            crop=crops[i] if crops and i < len(crops) else ''
                        )
                        # Create individual crop records from the old crop field
                        self._create_crops_from_old_format(attendance, crops[i] if crops and i < len(crops) else '')
                    except Farmer.DoesNotExist:
                        # If farmer doesn't exist, create attendance without farmer link
                        attendance = FieldDayAttendance.objects.create(
                            field_day=instance,
                            farmer_name=f"Unknown Farmer ({farmer_id})",
                            contact_number='',
                            acreage=acreages[i] if acreages and i < len(acreages) else 0.0,
                            crop=crops[i] if crops and i < len(crops) else ''
                        )
                        # Create individual crop records from the old crop field
                        self._create_crops_from_old_format(attendance, crops[i] if crops and i < len(crops) else '')
            
            # ✅ Handle manual entry (Option 2: For backward compatibility)
            elif names:
                for i, name in enumerate(names):
                    attendance = FieldDayAttendance.objects.create(
                        field_day=instance,
                        farmer_name=name,
                        contact_number=contacts[i] if contacts and i < len(contacts) else '',
                        acreage=acreages[i] if acreages and i < len(acreages) else 0.0,
                        crop=crops[i] if crops and i < len(crops) else ''
                    )
                    # Create individual crop records from the old crop field
                    self._create_crops_from_old_format(attendance, crops[i] if crops and i < len(crops) else '')

        # Handle file uploads
        if request and request.FILES:
            for f in request.FILES.getlist("attachments"):
                FieldDayAttachment.objects.create(field_day=instance, file=f)

        return instance

    def _create_crops_from_old_format(self, attendance, crop_string):
        """
        Parse the old comma-separated crop format and create individual FieldDayAttendanceCrop records.
        Distribute the total acreage equally among all crops.
        """
        if not crop_string or not crop_string.strip():
            return
        
        # Split by comma and clean up each crop name
        crop_names = [crop.strip() for crop in crop_string.split(',') if crop.strip()]
        
        if not crop_names:
            return
            
        # Calculate acreage per crop (distribute total acreage equally)
        total_acreage = float(attendance.acreage) if attendance.acreage else 0.0
        acreage_per_crop = total_acreage / len(crop_names) if len(crop_names) > 0 else 0.0
        
        for crop_name in crop_names:
            if crop_name:  # Only create if crop name is not empty
                FieldDayAttendanceCrop.objects.create(
                    attendance=attendance,
                    crop_name=crop_name,
                    acreage=acreage_per_crop
                )
