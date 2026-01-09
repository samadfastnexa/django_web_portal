from rest_framework import serializers
from .models import Dealer, MeetingSchedule, MeetingScheduleAttendance, SalesOrder, SalesOrderLine, SalesOrderAttachment,DealerRequest
import re
from .models import Company, Region, Zone, Territory
from rest_framework import viewsets
from django.contrib.auth import get_user_model
from drf_yasg.utils import swagger_serializer_method
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
    farmer_full_name = serializers.CharField(source='farmer.full_name', read_only=True)
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
        ref_name = 'MeetingAttendee'
    
    def create(self, validated_data):
        """Auto-populate farmer_name and contact_number from farmer if farmer is provided"""
        farmer = validated_data.get('farmer')
        if farmer:
            if not validated_data.get('farmer_name'):
                validated_data['farmer_name'] = farmer.name or farmer.full_name
            if not validated_data.get('contact_number'):
                validated_data['contact_number'] = farmer.primary_phone or ''
        return super().create(validated_data)
    
    def update(self, instance, validated_data):
        """Auto-populate farmer_name and contact_number from farmer if farmer is provided"""
        farmer = validated_data.get('farmer')
        if farmer:
            if not validated_data.get('farmer_name'):
                validated_data['farmer_name'] = farmer.name or farmer.full_name
            if not validated_data.get('contact_number'):
                validated_data['contact_number'] = farmer.primary_phone or ''
        return super().update(instance, validated_data)

class MeetingScheduleSerializer(serializers.ModelSerializer):
    attendees = MeetingScheduleAttendanceSerializer(many=True, read_only=True, help_text="List of meeting attendees")
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

    def create(self, validated_data):
        import logging
        logger = logging.getLogger(__name__)
        
        # Map FK IDs to actual relations if provided
        region_id = validated_data.pop('region_id', None)
        zone_id = validated_data.pop('zone_id', None)
        territory_id = validated_data.pop('territory_id', None)
        
        # Get nested attendees from initial_data since field is read_only
        logger.warning(f"DEBUG initial_data: {self.initial_data if hasattr(self, 'initial_data') else 'NO initial_data'}")
        attendees_data = self.initial_data.get('attendees', None) if hasattr(self, 'initial_data') else None
        logger.warning(f"DEBUG attendees_data from initial_data: {attendees_data}")
        
        # Handle flat attendee fields
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
        import logging
        logger = logging.getLogger(__name__)
        
        # Handle nested attendees array if provided
        logger.warning(f"DEBUG attendees_data: {attendees_data}")
        if attendees_data:
            for attendee_data in attendees_data:
                # Make a copy to avoid modifying original dict
                attendee_data = dict(attendee_data)
                farmer_id = attendee_data.get('farmer')
                logger.warning(f"DEBUG farmer_id from attendee_data: {farmer_id}, type: {type(farmer_id)}")
                farmer = None
                
                # Look up the Farmer object if farmer ID is provided
                if farmer_id:
                    try:
                        # Convert to int in case it's a string
                        farmer_id_int = int(farmer_id)
                        logger.warning(f"DEBUG looking up Farmer with id={farmer_id_int}")
                        farmer = Farmer.objects.get(id=farmer_id_int)
                        logger.warning(f"DEBUG found farmer: {farmer}")
                        # Set the farmer object for the relationship
                        attendee_data['farmer'] = farmer
                        # Auto-populate farmer_name and contact_number from farmer
                        if not attendee_data.get('farmer_name'):
                            attendee_data['farmer_name'] = farmer.name or farmer.full_name
                        if not attendee_data.get('contact_number'):
                            attendee_data['contact_number'] = farmer.primary_phone or ''
                    except (Farmer.DoesNotExist, ValueError, TypeError):
                        # If farmer not found or invalid ID, set farmer_name to indicate unknown
                        attendee_data['farmer'] = None
                        if not attendee_data.get('farmer_name'):
                            attendee_data['farmer_name'] = f'Unknown Farmer {farmer_id}'
                else:
                    attendee_data['farmer'] = None
                
                MeetingScheduleAttendance.objects.create(
                    schedule=schedule,
                    **attendee_data
                )
        # Handle flat attendee fields if provided
        elif farmer_ids:
            for i, farmer_id in enumerate(farmer_ids):
                farmer = None
                try:
                    # First try to look up by Django id (numeric)
                    farmer_id_int = int(farmer_id)
                    farmer = Farmer.objects.get(id=farmer_id_int)
                except (ValueError, Farmer.DoesNotExist):
                    # Fall back to looking up by farmer_id field (like FM01)
                    try:
                        farmer = Farmer.objects.get(farmer_id=farmer_id)
                    except Farmer.DoesNotExist:
                        farmer = None
                
                if farmer:
                    MeetingScheduleAttendance.objects.create(
                        schedule=schedule,
                        farmer=farmer,
                        farmer_name=farmer.name or farmer.full_name,
                        contact_number=farmer.primary_phone or '',
                        acreage=acreages[i] if i < len(acreages) else 0.0,
                        crop=crops[i] if i < len(crops) else ''
                    )
                else:
                    MeetingScheduleAttendance.objects.create(
                        schedule=schedule,
                        farmer_name=names[i] if names and i < len(names) else f'Unknown Farmer {farmer_id}',
                        contact_number=contacts[i] if contacts and i < len(contacts) else '',
                        acreage=acreages[i] if acreages and i < len(acreages) else 0.0,
                        crop=crops[i] if crops and i < len(crops) else ''
                    )
        elif names:
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
        
        # Get nested attendees from initial_data since field is read_only
        attendees_data = self.initial_data.get('attendees', None) if hasattr(self, 'initial_data') else None
        
        # Handle flat attendee fields
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

        from farmers.models import Farmer
        
        # Handle nested attendees array if provided
        if attendees_data is not None:
            instance.attendees.all().delete()
            for attendee_data in attendees_data:
                # Make a copy to avoid modifying original dict
                attendee_data = dict(attendee_data)
                farmer_id = attendee_data.get('farmer')
                farmer = None
                
                # Look up the Farmer object if farmer ID is provided
                if farmer_id:
                    try:
                        # Convert to int in case it's a string
                        farmer_id_int = int(farmer_id)
                        farmer = Farmer.objects.get(id=farmer_id_int)
                        # Set the farmer object for the relationship
                        attendee_data['farmer'] = farmer
                        # Auto-populate farmer_name and contact_number from farmer
                        if not attendee_data.get('farmer_name'):
                            attendee_data['farmer_name'] = farmer.name or farmer.full_name
                        if not attendee_data.get('contact_number'):
                            attendee_data['contact_number'] = farmer.primary_phone or ''
                    except (Farmer.DoesNotExist, ValueError, TypeError):
                        # If farmer not found or invalid ID, set farmer_name to indicate unknown
                        attendee_data['farmer'] = None
                        if not attendee_data.get('farmer_name'):
                            attendee_data['farmer_name'] = f'Unknown Farmer {farmer_id}'
                else:
                    attendee_data['farmer'] = None
                
                MeetingScheduleAttendance.objects.create(
                    schedule=instance,
                    **attendee_data
                )
        # Handle flat attendee fields if provided
        elif farmer_ids is not None or names is not None:
            instance.attendees.all().delete()
            if farmer_ids:
                for i, farmer_id in enumerate(farmer_ids):
                    farmer = None
                    try:
                        # First try to look up by Django id (numeric)
                        farmer_id_int = int(farmer_id)
                        farmer = Farmer.objects.get(id=farmer_id_int)
                    except (ValueError, Farmer.DoesNotExist):
                        # Fall back to looking up by farmer_id field (like FM01)
                        try:
                            farmer = Farmer.objects.get(farmer_id=farmer_id)
                        except Farmer.DoesNotExist:
                            farmer = None
                    
                    if farmer:
                        MeetingScheduleAttendance.objects.create(
                            schedule=instance,
                            farmer=farmer,
                            farmer_name=farmer.name or farmer.full_name,
                            contact_number=farmer.primary_phone or '',
                            acreage=acreages[i] if acreages and i < len(acreages) else 0.0,
                            crop=crops[i] if crops and i < len(crops) else ''
                        )
                    else:
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


class SalesOrderLineSerializer(serializers.ModelSerializer):
    class Meta:
        model = SalesOrderLine
        exclude = ('sales_order',)


class SalesOrderLineInputSerializer(serializers.Serializer):
    """Serializer for individual sales order line items in form-data"""
    line_num = serializers.IntegerField(required=False)
    item_code = serializers.CharField(required=False, allow_blank=True)
    item_description = serializers.CharField(required=False, allow_blank=True)
    quantity = serializers.DecimalField(max_digits=10, decimal_places=2, required=False, default=0)
    unit_price = serializers.DecimalField(max_digits=10, decimal_places=2, required=False, default=0)
    discount_percent = serializers.DecimalField(max_digits=5, decimal_places=2, required=False, default=0)
    warehouse_code = serializers.CharField(required=False, allow_blank=True)
    vat_group = serializers.CharField(required=False, allow_blank=True)
    tax_percentage_per_row = serializers.DecimalField(max_digits=5, decimal_places=2, required=False, default=0)
    units_of_measurment = serializers.IntegerField(required=False, default=1)
    uom_entry = serializers.IntegerField(required=False, default=0)
    measure_unit = serializers.CharField(required=False, allow_blank=True)
    uom_code = serializers.CharField(required=False, allow_blank=True)
    project_code = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    u_sd = serializers.DecimalField(max_digits=10, decimal_places=2, required=False, default=0)
    u_ad = serializers.DecimalField(max_digits=10, decimal_places=2, required=False, default=0)
    u_exd = serializers.DecimalField(max_digits=10, decimal_places=2, required=False, default=0)
    u_zerop = serializers.DecimalField(max_digits=10, decimal_places=2, required=False, default=0)
    u_pl = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    u_bp = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    u_policy = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    u_focitem = serializers.CharField(required=False, allow_blank=True, default='No')
    u_crop = serializers.CharField(required=False, allow_blank=True, allow_null=True)


class SalesOrderFormSerializer(serializers.ModelSerializer):
    """Form-data serializer with separate array fields for line items"""
    
    # Make all fields optional
    staff = serializers.PrimaryKeyRelatedField(queryset=User.objects.all(), required=False, allow_null=True)
    schedule = serializers.PrimaryKeyRelatedField(queryset=MeetingSchedule.objects.all(), required=False, allow_null=True)
    dealer = serializers.PrimaryKeyRelatedField(queryset=Dealer.objects.all(), required=False, allow_null=True)
    status = serializers.CharField(required=False, allow_blank=True)
    
    # SAP fields - all optional
    series = serializers.IntegerField(required=False, allow_null=True)
    doc_type = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    doc_date = serializers.DateField(required=False, allow_null=True)
    doc_due_date = serializers.DateField(required=False, allow_null=True)
    tax_date = serializers.DateField(required=False, allow_null=True)
    
    card_code = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    card_name = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    contact_person_code = serializers.IntegerField(required=False, allow_null=True)
    federal_tax_id = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    address = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    
    doc_currency = serializers.CharField(required=False, allow_blank=True)
    doc_rate = serializers.DecimalField(max_digits=10, decimal_places=4, required=False, allow_null=True)
    
    comments = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    
    # UDF fields
    u_sotyp = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    u_usid = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    u_s_card_code = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    u_s_card_name = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    
    # Line item array fields - add multiple items by providing arrays
    item_code = FlexibleListField(child=serializers.CharField(), write_only=True, required=False, help_text='Array of item codes')
    item_description = FlexibleListField(child=serializers.CharField(), write_only=True, required=False, help_text='Array of item descriptions')
    quantity = FlexibleListField(child=serializers.DecimalField(max_digits=10, decimal_places=2), write_only=True, required=False, help_text='Array of quantities')
    unit_price = FlexibleListField(child=serializers.DecimalField(max_digits=10, decimal_places=2), write_only=True, required=False, help_text='Array of unit prices')
    discount_percent = FlexibleListField(child=serializers.DecimalField(max_digits=5, decimal_places=2), write_only=True, required=False, help_text='Array of discount percentages')
    warehouse_code = FlexibleListField(child=serializers.CharField(), write_only=True, required=False, help_text='Array of warehouse codes')
    vat_group = FlexibleListField(child=serializers.CharField(), write_only=True, required=False, help_text='Array of VAT groups')
    u_crop = FlexibleListField(child=serializers.CharField(), write_only=True, required=False, help_text='Array of crop codes')

    class Meta:
        model = SalesOrder
        fields = ['id', 'staff', 'schedule', 'dealer', 'status', 'series', 'doc_type', 
                  'doc_date', 'doc_due_date', 'tax_date', 'card_code', 'card_name',
                  'contact_person_code', 'federal_tax_id', 'address', 'doc_currency',
                  'doc_rate', 'comments', 'u_sotyp', 'u_usid', 'u_s_card_code',
                  'u_s_card_name', 'created_at',
                  'item_code', 'item_description', 'quantity', 'unit_price', 
                  'discount_percent', 'warehouse_code', 'vat_group', 'u_crop']
        read_only_fields = ['id', 'created_at']
    
    def create(self, validated_data):
        from .models import SalesOrderLine
        
        # Extract line item arrays
        item_codes = validated_data.pop('item_code', [])
        item_descriptions = validated_data.pop('item_description', [])
        quantities = validated_data.pop('quantity', [])
        unit_prices = validated_data.pop('unit_price', [])
        discount_percents = validated_data.pop('discount_percent', [])
        warehouse_codes = validated_data.pop('warehouse_code', [])
        vat_groups = validated_data.pop('vat_group', [])
        u_crops = validated_data.pop('u_crop', [])
        
        # Create sales order
        order = SalesOrder.objects.create(**validated_data)
        
        # Get the maximum length of arrays to handle all items
        max_length = max(
            len(item_codes), len(item_descriptions), len(quantities), 
            len(unit_prices), len(discount_percents), len(warehouse_codes),
            len(vat_groups), len(u_crops)
        ) if any([item_codes, item_descriptions, quantities, unit_prices, discount_percents, warehouse_codes, vat_groups, u_crops]) else 0
        
        # Create line items by zipping arrays together
        for idx in range(max_length):
            SalesOrderLine.objects.create(
                sales_order=order,
                line_num=idx,
                item_code=item_codes[idx] if idx < len(item_codes) else '',
                item_description=item_descriptions[idx] if idx < len(item_descriptions) else '',
                quantity=quantities[idx] if idx < len(quantities) else 0,
                unit_price=unit_prices[idx] if idx < len(unit_prices) else 0,
                discount_percent=discount_percents[idx] if idx < len(discount_percents) else 0,
                warehouse_code=warehouse_codes[idx] if idx < len(warehouse_codes) else '',
                vat_group=vat_groups[idx] if idx < len(vat_groups) else '',
                u_crop=u_crops[idx] if idx < len(u_crops) else None,
                tax_percentage_per_row=0,
                units_of_measurment=1,
                uom_entry=0,
                u_focitem='No'
            )
        
        return order


class SalesOrderSerializer(serializers.ModelSerializer):
    attachments = SalesOrderAttachmentSerializer(many=True, read_only=True)
    document_lines = SalesOrderLineSerializer(many=True, required=False)
    
    # Make all fields optional for easier mobile API usage
    staff = serializers.PrimaryKeyRelatedField(queryset=User.objects.all(), required=False, allow_null=True)
    schedule = serializers.PrimaryKeyRelatedField(queryset=MeetingSchedule.objects.all(), required=False, allow_null=True)
    dealer = serializers.PrimaryKeyRelatedField(queryset=Dealer.objects.all(), required=False, allow_null=True)
    status = serializers.CharField(required=False, allow_blank=True)
    
    # SAP fields - all optional
    series = serializers.IntegerField(required=False, allow_null=True)
    doc_type = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    doc_date = serializers.DateField(required=False, allow_null=True)
    doc_due_date = serializers.DateField(required=False, allow_null=True)
    tax_date = serializers.DateField(required=False, allow_null=True)
    
    card_code = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    card_name = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    contact_person_code = serializers.IntegerField(required=False, allow_null=True)
    federal_tax_id = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    pay_to_code = serializers.IntegerField(required=False, allow_null=True)
    address = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    
    doc_currency = serializers.CharField(required=False, allow_blank=True)
    doc_rate = serializers.DecimalField(max_digits=10, decimal_places=4, required=False, allow_null=True)
    
    comments = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    summery_type = serializers.CharField(required=False, allow_blank=True)
    doc_object_code = serializers.CharField(required=False, allow_blank=True)
    
    # UDF fields - all optional
    u_sotyp = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    u_usid = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    u_swje = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    u_secje = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    u_crje = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    u_s_card_code = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    u_s_card_name = serializers.CharField(required=False, allow_blank=True, allow_null=True)

    class Meta:
        model = SalesOrder
        fields = '__all__'
    
    def to_internal_value(self, data):
        # Handle document_lines when it comes as JSON string from form data
        import json
        if 'document_lines' in data and isinstance(data['document_lines'], str):
            try:
                data = data.copy() if hasattr(data, 'copy') else dict(data)
                data['document_lines'] = json.loads(data['document_lines'])
            except (json.JSONDecodeError, ValueError):
                pass
        return super().to_internal_value(data)

    def create(self, validated_data):
        lines_data = validated_data.pop('document_lines', [])
        order = super().create(validated_data)
        self._create_lines(order, lines_data)
        return order

    def update(self, instance, validated_data):
        lines_data = validated_data.pop('document_lines', None)
        order = super().update(instance, validated_data)
        if lines_data is not None:
            order.document_lines.all().delete()
            self._create_lines(order, lines_data)
        return order

    def _create_lines(self, order, lines_data):
        for idx, line in enumerate(lines_data or []):
            SalesOrderLine.objects.create(
                sales_order=order,
                line_num=line.get('line_num', idx),
                item_code=line.get('item_code', ''),
                item_description=line.get('item_description', ''),
                quantity=line.get('quantity', 0),
                unit_price=line.get('unit_price', 0),
                discount_percent=line.get('discount_percent', 0),
                warehouse_code=line.get('warehouse_code', ''),
                vat_group=line.get('vat_group', ''),
                tax_percentage_per_row=line.get('tax_percentage_per_row', 0),
                units_of_measurment=line.get('units_of_measurment', 1),
                uom_entry=line.get('uom_entry', 0),
                measure_unit=line.get('measure_unit', ''),
                uom_code=line.get('uom_code', ''),
                project_code=line.get('project_code'),
                u_sd=line.get('u_sd', 0),
                u_ad=line.get('u_ad', 0),
                u_exd=line.get('u_exd', 0),
                u_zerop=line.get('u_zerop', 0),
                u_pl=line.get('u_pl'),
                u_bp=line.get('u_bp'),
                u_policy=line.get('u_policy'),
                u_focitem=line.get('u_focitem', 'No'),
                u_crop=line.get('u_crop'),
            )


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
    region_name = serializers.CharField(source='zone.region.name', read_only=True)

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

