from rest_framework import serializers
from .models import Crop, CropStage, Trial, TrialTreatment, TrialImage, Product


class CropStageSerializer(serializers.ModelSerializer):
    class Meta:
        model = CropStage
        fields = [
            "id", "stage_name", "days_after_sowing", "brand",
            "active_ingredient", "dose_per_acre", "purpose", "remarks"
        ]


class CropSerializer(serializers.ModelSerializer):
    stages = CropStageSerializer(many=True, read_only=True)

    class Meta:
        model = Crop
        fields = ["id", "name", "variety", "season", "remarks", "stages"]

    def create(self, validated_data):
        # Handle form data for stages
        request = self.context.get('request')
        crop = Crop.objects.create(**validated_data)
        
        if request and hasattr(request, 'data'):
            # Extract stage data from form data
            stage_index = 0
            while f'stages[{stage_index}][stage_name]' in request.data:
                stage_data = {
                    'stage_name': request.data.get(f'stages[{stage_index}][stage_name]'),
                    'days_after_sowing': request.data.get(f'stages[{stage_index}][days_after_sowing]'),
                    'brand': request.data.get(f'stages[{stage_index}][brand]', ''),
                    'active_ingredient': request.data.get(f'stages[{stage_index}][active_ingredient]', ''),
                    'dose_per_acre': request.data.get(f'stages[{stage_index}][dose_per_acre]', ''),
                    'purpose': request.data.get(f'stages[{stage_index}][purpose]', '')
                }
                if stage_data['stage_name'] and stage_data['days_after_sowing']:
                    CropStage.objects.create(crop=crop, **stage_data)
                stage_index += 1
        
        return crop

    def update(self, instance, validated_data):
        instance.name = validated_data.get("name", instance.name)
        instance.variety = validated_data.get("variety", instance.variety)
        instance.season = validated_data.get("season", instance.season)
        instance.remarks = validated_data.get("remarks", instance.remarks)
        instance.save()
        
        # Handle form data for stages update
        request = self.context.get('request')
        if request and hasattr(request, 'data'):
            # Clear existing stages and create new ones
            instance.stages.all().delete()
            stage_index = 0
            while f'stages[{stage_index}][stage_name]' in request.data:
                stage_data = {
                    'stage_name': request.data.get(f'stages[{stage_index}][stage_name]'),
                    'days_after_sowing': request.data.get(f'stages[{stage_index}][days_after_sowing]'),
                    'brand': request.data.get(f'stages[{stage_index}][brand]', ''),
                    'active_ingredient': request.data.get(f'stages[{stage_index}][active_ingredient]', ''),
                    'dose_per_acre': request.data.get(f'stages[{stage_index}][dose_per_acre]', ''),
                    'purpose': request.data.get(f'stages[{stage_index}][purpose]', '')
                }
                if stage_data['stage_name'] and stage_data['days_after_sowing']:
                    CropStage.objects.create(crop=instance, **stage_data)
                stage_index += 1

        return instance


class TrialImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = TrialImage
        fields = ['id', 'image', 'image_type', 'caption', 'taken_at', 'uploaded_at']


class TrialTreatmentSerializer(serializers.ModelSerializer):
    images = TrialImageSerializer(many=True, read_only=True)
    product_name = serializers.CharField(source='product.name', read_only=True)
    
    class Meta:
        model = TrialTreatment
        fields = [
            'id', 'label', 'product', 'product_name', 'crop_stage_soil',
            'pest_stage_start', 'crop_safety_stress_rating', 'details',
            'growth_improvement_type', 'best_dose', 'others', 'images'
        ]


class TrialSerializer(serializers.ModelSerializer):
    treatments = TrialTreatmentSerializer(many=True, read_only=True)
    
    class Meta:
        model = Trial
        fields = [
            'id', 'station', 'trial_name', 'location_area', 'crop_variety',
            'application_date', 'design_replicates', 'water_volume_used',
            'previous_sprays', 'temp_min_c', 'temp_max_c', 'humidity_min_percent',
            'humidity_max_percent', 'wind_velocity_kmh', 'rainfall', 'created_at',
            'treatments'
        ]


class ProductSerializer(serializers.ModelSerializer):
    class Meta:
        model = Product
        fields = ['id', 'name', 'brand', 'active_ingredient', 'formulation', 'remarks', 'created_at']
