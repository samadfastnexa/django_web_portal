from rest_framework import serializers
from .models import Dealer, MeetingSchedule, SalesOrder, SalesOrderAttachment,DealerRequest

class DealerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Dealer
        fields = '__all__'

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
    requested_by = serializers.StringRelatedField(read_only=True)
    reviewed_by = serializers.StringRelatedField(read_only=True)
    status = serializers.CharField(read_only=True)  # Optional: if you want status to be admin-only

    class Meta:
        model = DealerRequest
        fields = [
            'id',
            'name',
            'contact_number',
            'address',
            'status',
            'requested_by',
            'reviewed_by',
            'reviewed_at',
            'created_at',
        ]
        read_only_fields = ['requested_by', 'reviewed_by', 'reviewed_at', 'created_at']