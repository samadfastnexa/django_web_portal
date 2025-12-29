from rest_framework import serializers


class SalesVsAchievementSerializer(serializers.Serializer):
    """Serializer for Sales vs Achievement data"""
    emp_id = serializers.IntegerField(required=False, allow_null=True)
    territory_id = serializers.IntegerField(required=False, allow_null=True)
    territory_name = serializers.CharField(required=False, allow_null=True)
    sales_target = serializers.DecimalField(max_digits=15, decimal_places=2, required=False)
    achievement = serializers.DecimalField(max_digits=15, decimal_places=2, required=False)
    from_date = serializers.DateField(required=False, allow_null=True)
    to_date = serializers.DateField(required=False, allow_null=True)
    percentage = serializers.DecimalField(max_digits=5, decimal_places=2, required=False)


class CollectionVsAchievementSerializer(serializers.Serializer):
    """Serializer for Collection vs Achievement data"""
    region = serializers.CharField(required=False, allow_null=True)
    zone = serializers.CharField(required=False, allow_null=True)
    territory_id = serializers.IntegerField(required=False, allow_null=True)
    territory_name = serializers.CharField(required=False, allow_null=True)
    collection_target = serializers.DecimalField(max_digits=15, decimal_places=2, required=False)
    collection_achievement = serializers.DecimalField(max_digits=15, decimal_places=2, required=False)
    from_date = serializers.DateField(required=False, allow_null=True)
    to_date = serializers.DateField(required=False, allow_null=True)
    percentage = serializers.DecimalField(max_digits=5, decimal_places=2, required=False)


class FarmerStatsSerializer(serializers.Serializer):
    """Serializer for Farmer statistics"""
    total_count = serializers.IntegerField()
    active_count = serializers.IntegerField()
    by_district = serializers.DictField()
    by_education = serializers.DictField()
    by_landholding = serializers.DictField()
    total_land_area = serializers.DecimalField(max_digits=15, decimal_places=2, required=False)
    average_land_per_farmer = serializers.DecimalField(max_digits=10, decimal_places=2, required=False)


class TargetSerializer(serializers.Serializer):
    """Serializer for Target data"""
    target_type = serializers.CharField()
    target_value = serializers.DecimalField(max_digits=15, decimal_places=2)
    achieved_value = serializers.DecimalField(max_digits=15, decimal_places=2)
    achievement_percentage = serializers.DecimalField(max_digits=5, decimal_places=2)
    period_start = serializers.DateField()
    period_end = serializers.DateField()


class DashboardOverviewSerializer(serializers.Serializer):
    """Comprehensive Dashboard Overview Serializer"""
    sales_vs_achievement = SalesVsAchievementSerializer(many=True, required=False)
    collection_vs_achievement = CollectionVsAchievementSerializer(many=True, required=False)
    targets = TargetSerializer(many=True, required=False)
    farmer_stats = FarmerStatsSerializer(required=False)
    visits_today = serializers.IntegerField(required=False)
    pending_sales_orders = serializers.IntegerField(required=False)
    company_options = serializers.ListField(required=False)
    selected_company = serializers.CharField(required=False, allow_blank=True)
    selected_region = serializers.CharField(required=False, allow_blank=True)
    selected_zone = serializers.CharField(required=False, allow_blank=True)
    selected_territory = serializers.CharField(required=False, allow_blank=True)


class PerformanceMetricSerializer(serializers.Serializer):
    """Serializer for Performance Metrics"""
    metric_name = serializers.CharField()
    current_value = serializers.DecimalField(max_digits=15, decimal_places=2)
    previous_value = serializers.DecimalField(max_digits=15, decimal_places=2, required=False)
    target_value = serializers.DecimalField(max_digits=15, decimal_places=2, required=False)
    unit = serializers.CharField(required=False)
    trend = serializers.CharField(required=False)  # 'up', 'down', 'stable'


class CollectionRecordSerializer(serializers.Serializer):
    target = serializers.DecimalField(max_digits=15, decimal_places=2)
    achievement = serializers.DecimalField(max_digits=15, decimal_places=2)
    from_date = serializers.DateField(required=False, allow_null=True)
    to_date = serializers.DateField(required=False, allow_null=True)


class CollectionTerritorySerializer(serializers.Serializer):
    name = serializers.CharField()
    target = serializers.DecimalField(max_digits=15, decimal_places=2)
    achievement = serializers.DecimalField(max_digits=15, decimal_places=2)
    from_date = serializers.DateField(required=False, allow_null=True)
    to_date = serializers.DateField(required=False, allow_null=True)


class CollectionZoneSerializer(serializers.Serializer):
    name = serializers.CharField()
    target = serializers.DecimalField(max_digits=15, decimal_places=2)
    achievement = serializers.DecimalField(max_digits=15, decimal_places=2)
    from_date = serializers.DateField(required=False, allow_null=True)
    to_date = serializers.DateField(required=False, allow_null=True)
    territories = CollectionTerritorySerializer(many=True)


class CollectionRegionSerializer(serializers.Serializer):
    name = serializers.CharField()
    target = serializers.DecimalField(max_digits=15, decimal_places=2)
    achievement = serializers.DecimalField(max_digits=15, decimal_places=2)
    from_date = serializers.DateField(required=False, allow_null=True)
    to_date = serializers.DateField(required=False, allow_null=True)
    zones = CollectionZoneSerializer(many=True)


class CollectionAnalyticsResponseSerializer(serializers.Serializer):
    success = serializers.BooleanField()
    count = serializers.IntegerField()
    data = CollectionRegionSerializer(many=True)
    pagination = serializers.DictField()
    filters = serializers.DictField()
