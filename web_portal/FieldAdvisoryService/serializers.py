from rest_framework import serializers
from .models import Dealer, MeetingSchedule, SalesOrder, SalesOrderAttachment,DealerRequest
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

class MeetingScheduleSerializer(serializers.ModelSerializer):
    class Meta:
        model = MeetingSchedule
        fields = '__all__'

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
        # Remove non-digit characters
        digits_only = re.sub(r'\D', '', value)

        # Ensure 13 digits
        if len(digits_only) != 13:
            raise serializers.ValidationError("CNIC must have exactly 13 digits.")

        # Format to 12345-1234567-1
        formatted = f"{digits_only[:5]}-{digits_only[5:12]}-{digits_only[12]}"
        return formatted


    def validate_minimum_investment(self, value):
        if value < 500000:
            raise serializers.ValidationError("Minimum investment must be at least 5 lakh (500,000).")
        return value

    def validate_cnic_front(self, image):
        return self.validate_image(image, field="CNIC front")

    def validate_cnic_back(self, image):
        return self.validate_image(image, field="CNIC back")

    def validate_image(self, image, field="Image"):
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

