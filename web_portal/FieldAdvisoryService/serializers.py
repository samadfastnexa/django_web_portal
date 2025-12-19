from rest_framework import serializers
from .models import Dealer, MeetingSchedule, MeetingScheduleAttendance, SalesOrder, SalesOrderAttachment,DealerRequest
import re
from .models import Company, Region, Zone, Territory
from rest_framework import viewsets
from django.contrib.auth import get_user_model
User = get_user_model() 
# class DealerSerializer(serializers.ModelSerializer):
#     class Meta:
#         model = Dealer
#         fields = '__all__'
class DealerSerializer(serializers.ModelSerializer):
    # read-only fields that come from User
    email        = serializers.EmailField(source='user.email', read_only=True)
    first_name   = serializers.CharField(source='user.first_name', read_only=True)
    last_name    = serializers.CharField(source='user.last_name', read_only=True)

    # optional: allow choosing an existing user when creating a dealer
    user         = serializers.PrimaryKeyRelatedField(
                      queryset=User.objects.all(),
                      required=False, allow_null=True)

    class Meta:
        model  = Dealer
        fields = [
            'id','user','email','first_name','last_name','name','cnic_number',
            'contact_number','company','region','zone','territory',
            'address','latitude','longitude','remarks','is_active',
            'cnic_front_image','cnic_back_image'
        ]

class FlexibleListField(serializers.ListField):
    def to_internal_value(self, data):
        if not data:
            return []
        if isinstance(data, str):
            if ',' in data:
                return [item.strip() for item in data.split(',') if item.strip()]
            else:
                return [data.strip()] if data.strip() else []
        if isinstance(data, list):
            result = []
            for item in data:
                if isinstance(item, str):
                    if ',' in item:
                        result.extend([sub.strip() for sub in item.split(',') if sub.strip()])
                    else:
                        if item.strip():
                            result.append(item.strip())
                else:
                    result.append(str(item))
            return result
        return [str(data)]

class MeetingScheduleAttendanceSerializer(serializers.ModelSerializer):
    farmer_id = serializers.CharField(source='farmer.farmer_id', read_only=True)
    farmer_full_name = serializers.CharField(source='farmer.get_full_name', read_only=True)
    farmer_primary_phone = serializers.CharField(source='farmer.primary_phone', read_only=True)
    farmer_district = serializers.CharField(source='farmer.district', read_only=True)
    farmer_village = serializers.CharField(source='farmer.village', read_only=True)

    class Meta:
        model = MeetingScheduleAttendance
        fields = [
            'id', 'farmer', 'farmer_id', 'farmer_full_name', 'farmer_primary_phone',
            'farmer_district', 'farmer_village', 'farmer_name', 'contact_number',
            'acreage', 'crop'
        ]

class MeetingScheduleSerializer(serializers.ModelSerializer):
    attendees = serializers.SerializerMethodField(read_only=True)
    fsm_name = serializers.CharField(required=False)
    region_id = serializers.IntegerField(required=False, allow_null=True, write_only=True)
    zone_id = serializers.IntegerField(required=False, allow_null=True, write_only=True)
    territory_id = serializers.IntegerField(required=False, allow_null=True, write_only=True)

    attendee_farmer_id = FlexibleListField(child=serializers.CharField(), write_only=True, required=False)
    attendee_name = serializers.ListField(child=serializers.CharField(), write_only=True, required=False)
    attendee_contact = serializers.ListField(child=serializers.CharField(), write_only=True, required=False)
    attendee_acreage = FlexibleListField(child=serializers.DecimalField(max_digits=10, decimal_places=2), write_only=True, required=False)
    attendee_crop = FlexibleListField(child=serializers.CharField(), write_only=True, required=False)

    class Meta:
        model = MeetingSchedule
        fields = [
            'id', 'staff', 'fsm_name',
            'region_id', 'zone_id', 'territory_id',
            'date', 'location', 'total_attendees',
            'key_topics_discussed', 'presence_of_zm', 'presence_of_rsm',
            'feedback_from_attendees', 'suggestions_for_future',
            'attendees',
            'attendee_farmer_id', 'attendee_name', 'attendee_contact', 'attendee_acreage', 'attendee_crop',
        ]
        read_only_fields = ['staff']

    def get_attendees(self, obj):
        attendees = obj.attendees.all()
        return MeetingScheduleAttendanceSerializer(attendees, many=True).data

    def create(self, validated_data):
        # Map FK IDs to actual relations if provided
        region_id = validated_data.pop('region_id', None)
        zone_id = validated_data.pop('zone_id', None)
        territory_id = validated_data.pop('territory_id', None)
        farmer_ids = validated_data.pop('attendee_farmer_id', [])
        names = validated_data.pop('attendee_name', [])
        contacts = validated_data.pop('attendee_contact', [])
        acreages = validated_data.pop('attendee_acreage', [])
        crops = validated_data.pop('attendee_crop', [])

        schedule = MeetingSchedule.objects.create(**validated_data)
        if region_id is not None:
            schedule.region_id = region_id
        if zone_id is not None:
            schedule.zone_id = zone_id
        if territory_id is not None:
            schedule.territory_id = territory_id
        schedule.save()

        from farmers.models import Farmer
        if farmer_ids:
            for i, farmer_id in enumerate(farmer_ids):
                try:
                    farmer = Farmer.objects.get(farmer_id=farmer_id)
                    MeetingScheduleAttendance.objects.create(
                        schedule=schedule,
                        farmer=farmer,
                        farmer_name=farmer.get_full_name(),
                        contact_number=farmer.primary_phone or '',
                        acreage=acreages[i] if i < len(acreages) else 0.0,
                        crop=crops[i] if i < len(crops) else ''
                    )
                except Farmer.DoesNotExist:
                    MeetingScheduleAttendance.objects.create(
                        schedule=schedule,
                        farmer_name=names[i] if i < len(names) else f'Unknown Farmer {farmer_id}',
                        contact_number=contacts[i] if i < len(contacts) else '',
                        acreage=acreages[i] if i < len(acreages) else 0.0,
                        crop=crops[i] if i < len(crops) else ''
                    )
        else:
            for i, name in enumerate(names):
                MeetingScheduleAttendance.objects.create(
                    schedule=schedule,
                    farmer_name=name,
                    contact_number=contacts[i] if i < len(contacts) else '',
                    acreage=acreages[i] if i < len(acreages) else 0.0,
                    crop=crops[i] if i < len(crops) else ''
                )

        return schedule

    def update(self, instance, validated_data):
        region_id = validated_data.pop('region_id', None)
        zone_id = validated_data.pop('zone_id', None)
        territory_id = validated_data.pop('territory_id', None)
        farmer_ids = validated_data.pop('attendee_farmer_id', None)
        names = validated_data.pop('attendee_name', None)
        contacts = validated_data.pop('attendee_contact', None)
        acreages = validated_data.pop('attendee_acreage', None)
        crops = validated_data.pop('attendee_crop', None)

        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        if region_id is not None:
            instance.region_id = region_id
        if zone_id is not None:
            instance.zone_id = zone_id
        if territory_id is not None:
            instance.territory_id = territory_id
        instance.save()

        if farmer_ids is not None or names is not None:
            instance.attendees.all().delete()
            from farmers.models import Farmer
            if farmer_ids:
                for i, farmer_id in enumerate(farmer_ids):
                    try:
                        farmer = Farmer.objects.get(farmer_id=farmer_id)
                        MeetingScheduleAttendance.objects.create(
                            schedule=instance,
                            farmer=farmer,
                            farmer_name=farmer.get_full_name(),
                            contact_number=farmer.primary_phone or '',
                            acreage=acreages[i] if acreages and i < len(acreages) else 0.0,
                            crop=crops[i] if crops and i < len(crops) else ''
                        )
                    except Farmer.DoesNotExist:
                        MeetingScheduleAttendance.objects.create(
                            schedule=instance,
                            farmer_name=names[i] if names and i < len(names) else f'Unknown Farmer {farmer_id}',
                            contact_number=contacts[i] if contacts and i < len(contacts) else '',
                            acreage=acreages[i] if acreages and i < len(acreages) else 0.0,
                            crop=crops[i] if crops and i < len(crops) else ''
                        )
            elif names:
                for i, name in enumerate(names):
                    MeetingScheduleAttendance.objects.create(
                        schedule=instance,
                        farmer_name=name,
                        contact_number=contacts[i] if contacts and i < len(contacts) else '',
                        acreage=acreages[i] if acreages and i < len(acreages) else 0.0,
                        crop=crops[i] if crops and i < len(crops) else ''
                    )

        return instance

class SalesOrderAttachmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = SalesOrderAttachment
        fields = '__all__'

class SalesOrderSerializer(serializers.ModelSerializer):
    attachments = SalesOrderAttachmentSerializer(many=True, read_only=True)

    class Meta:
        model = SalesOrder
        fields = '__all__'


class DealerRequestSerializer(serializers.ModelSerializer):
    requested_by = serializers.PrimaryKeyRelatedField(read_only=True)

    def validate_cnic_number(self, value):
        # Skip validation if value is None or empty
        if not value:
            return value
            
        # Remove non-digit characters
        digits_only = re.sub(r'\D', '', value)

        # Ensure 13 digits
        if len(digits_only) != 13:
            raise serializers.ValidationError("CNIC must have exactly 13 digits.")

        # Format to 12345-1234567-1
        formatted = f"{digits_only[:5]}-{digits_only[5:12]}-{digits_only[12]}"
        return formatted


    def validate_minimum_investment(self, value):
        # Skip validation if value is None
        if value is None:
            return value
            
        if value < 500000:
            raise serializers.ValidationError("Minimum investment must be at least 5 lakh (500,000).")
        return value

    def validate_cnic_front(self, image):
        if not image:
            return image
        return self.validate_image(image, field="CNIC front")

    def validate_cnic_back(self, image):
        if not image:
            return image
        return self.validate_image(image, field="CNIC back")

    def validate_image(self, image, field="Image"):
        # Skip validation if no image provided
        if not image:
            return image
            
        max_size_mb = 2  # Max 2 MB
        valid_mime_types = ['image/jpeg', 'image/png']
        
        # Check MIME type
        if hasattr(image, 'content_type'):
            if image.content_type not in valid_mime_types:
                raise serializers.ValidationError(
                    f"{field} must be JPEG or PNG."
                )

        # Check file size
        if image.size > max_size_mb * 1024 * 1024:
            raise serializers.ValidationError(
                f"{field} size must not exceed {max_size_mb} MB."
            )

        return image

    def create(self, validated_data):
        validated_data['requested_by'] = self.context['request'].user
        return super().create(validated_data)

    class Meta:
        model = DealerRequest
        fields = '__all__'
        extra_kwargs = {
            # Basic Info
            'owner_name': {'required': False},
            'business_name': {'required': False},
            'contact_number': {'required': False},
            'mobile_phone': {'required': False},
            'email': {'required': False},
            'address': {'required': False},
            'city': {'required': False},
            'state': {'required': False},
            'country': {'required': False},
            
            # Tax & Legal
            'cnic_number': {'required': False},
            'federal_tax_id': {'required': False},
            'additional_id': {'required': False},
            'unified_federal_tax_id': {'required': False},
            'filer_status': {'required': False},
            
            # License
            'govt_license_number': {'required': False},
            'license_expiry': {'required': False},
            'u_leg': {'required': False},
            
            # Documents
            'cnic_front': {'required': False},
            'cnic_back': {'required': False},
            
            # Territory
            'company': {'required': False},
            'region': {'required': False},
            'zone': {'required': False},
            'territory': {'required': False},
            
            # SAP Configuration
            'sap_series': {'required': False},
            'card_type': {'required': False},
            'group_code': {'required': False},
            'debitor_account': {'required': False},
            'vat_group': {'required': False},
            'vat_liable': {'required': False},
            'whatsapp_messages': {'required': False},
            
            # Financial
            'minimum_investment': {'required': False},
            'reason': {'required': False},
            
            # SAP Integration (read-only)
            'is_posted_to_sap': {'read_only': True},
            'sap_card_code': {'read_only': True},
            'sap_doc_entry': {'read_only': True},
            'sap_error': {'read_only': True},
            'sap_response_json': {'read_only': True},
            'posted_at': {'read_only': True},
        }


class CompanySerializer(serializers.ModelSerializer):
    class Meta:
        model = Company
        fields = '__all__'

class RegionSerializer(serializers.ModelSerializer):
    company_name = serializers.CharField(source='company.Company_name', read_only=True)

    class Meta:
        model = Region
        fields = '__all__'

class ZoneSerializer(serializers.ModelSerializer):
    company_name = serializers.CharField(source='company.Company_name', read_only=True)
    region_name = serializers.CharField(source='region.name', read_only=True)

    class Meta:
        model = Zone
        fields = ['id', 'name', 'company', 'company_name', 'region', 'region_name', 'created_by']

class TerritorySerializer(serializers.ModelSerializer):
    zone_name = serializers.CharField(source='zone.name', read_only=True)

    class Meta:
        model = Territory
        fields = '__all__'
        
        # nested serializers for hierarchical representation

class TerritoryNestedSerializer(serializers.ModelSerializer):
    company = serializers.PrimaryKeyRelatedField(read_only=True)
    company_name = serializers.CharField(source='company.Company_name', read_only=True)
    zone = ZoneSerializer(read_only=True)  # 👈 re-use your ZoneSerializer (already has company_name, region_name)

    class Meta:
        model = Territory
        fields = [
            'id',
            'name',
            'latitude',
            'longitude',
            'company',
            'company_name',
            'zone',
            'created_by'
        ]
        
class ZoneNestedSerializer(serializers.ModelSerializer):
    company = serializers.PrimaryKeyRelatedField(read_only=True)   # company id
    company_name = serializers.CharField(source='company.Company_name', read_only=True)
    territories = TerritorySerializer(many=True, read_only=True)

    class Meta:
        model = Zone
        fields = ['id', 'name', 'company', 'company_name', 'territories']
        
class RegionNestedSerializer(serializers.ModelSerializer):
    zones = ZoneNestedSerializer(many=True, read_only=True)
    company = serializers.PrimaryKeyRelatedField(read_only=True)   # returns company id
    company_name = serializers.CharField(source='company.Company_name', read_only=True)

    class Meta:
        model = Region
        fields = ['id', 'name', 'company', 'company_name', 'zones']

class CompanyNestedSerializer(serializers.ModelSerializer):
    regions = RegionNestedSerializer(many=True, read_only=True)

    class Meta:
        model = Company
        fields = ['id', 'name', 'regions']

