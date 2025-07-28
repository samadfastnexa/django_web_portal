from rest_framework import serializers
from .models import Complaint

class ComplaintSerializer(serializers.ModelSerializer):
    class Meta:
        model = Complaint
        fields = ['id', 'complaint_id', 'user', 'message', 'image', 'status', 'created_at']
        read_only_fields = ['id', 'complaint_id', 'user', 'status', 'created_at']

    def create(self, validated_data):
        import uuid
        validated_data['complaint_id'] = 'FB' + str(uuid.uuid4().int)[:10]
        validated_data['status'] = 'pending'  # ✅ Always set status to "pending" at creation
        return super().create(validated_data)