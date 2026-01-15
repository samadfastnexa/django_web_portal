from rest_framework import serializers
from .models import Policy, DiseaseIdentification, RecommendedProduct


class PolicySerializer(serializers.ModelSerializer):
    class Meta:
        model = Policy
        fields = (
            'id', 'code', 'name', 'policy', 'valid_from', 'valid_to', 'active',
            'created_at', 'updated_at'
        )


class RecommendedProductSerializer(serializers.ModelSerializer):
    """Serializer for recommended products"""
    disease_name = serializers.CharField(source='disease.disease_name', read_only=True)
    
    # Fields populated from HANA product catalog
    product_image_url = serializers.SerializerMethodField()
    product_description_urdu_url = serializers.SerializerMethodField()
    item_group_name = serializers.SerializerMethodField()
    generic_name = serializers.SerializerMethodField()
    brand_name = serializers.SerializerMethodField()
    unit_of_measure = serializers.SerializerMethodField()
    
    class Meta:
        model = RecommendedProduct
        fields = (
            'id', 'disease', 'disease_name', 'product_item_code', 'product_name',
            'dosage', 'application_method', 'timing', 'precautions',
            'priority', 'effectiveness_rating', 'is_active', 'notes',
            # HANA product catalog fields
            'product_image_url', 'product_description_urdu_url',
            'item_group_name', 'generic_name', 'brand_name', 'unit_of_measure',
            'created_at', 'updated_at'
        )
        read_only_fields = ('created_at', 'updated_at')
    
    def get_product_image_url(self, obj):
        """Get product image URL from context if available"""
        product_catalog = self.context.get('product_catalog', {})
        product = product_catalog.get(obj.product_item_code, {})
        return product.get('product_image_url')
    
    def get_product_description_urdu_url(self, obj):
        """Get Urdu description image URL from context if available"""
        product_catalog = self.context.get('product_catalog', {})
        product = product_catalog.get(obj.product_item_code, {})
        return product.get('product_description_urdu_url')
    
    def get_item_group_name(self, obj):
        """Get item group name from product catalog"""
        product_catalog = self.context.get('product_catalog', {})
        product = product_catalog.get(obj.product_item_code, {})
        return product.get('ItmsGrpNam')
    
    def get_generic_name(self, obj):
        """Get generic name from product catalog"""
        product_catalog = self.context.get('product_catalog', {})
        product = product_catalog.get(obj.product_item_code, {})
        return product.get('U_GenericName')
    
    def get_brand_name(self, obj):
        """Get brand name from product catalog"""
        product_catalog = self.context.get('product_catalog', {})
        product = product_catalog.get(obj.product_item_code, {})
        return product.get('U_BrandName')
    
    def get_unit_of_measure(self, obj):
        """Get unit of measure from product catalog"""
        product_catalog = self.context.get('product_catalog', {})
        product = product_catalog.get(obj.product_item_code, {})
        return product.get('SalPackMsr') or product.get('InvntryUom')


class DiseaseIdentificationSerializer(serializers.ModelSerializer):
    """Serializer for disease identification with optional recommended products"""
    recommended_products = RecommendedProductSerializer(many=True, read_only=True)
    recommended_products_count = serializers.SerializerMethodField()
    
    class Meta:
        model = DiseaseIdentification
        fields = (
            'id', 'doc_entry', 'item_code', 'item_name', 'description',
            'disease_name', 'is_active', 'created_at', 'updated_at',
            'recommended_products', 'recommended_products_count'
        )
        read_only_fields = ('created_at', 'updated_at')
    
    def get_recommended_products_count(self, obj):
        """Get count of active recommended products"""
        return obj.recommended_products.filter(is_active=True).count()


class DiseaseIdentificationListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for disease list (without nested products)"""
    recommended_products_count = serializers.SerializerMethodField()
    
    class Meta:
        model = DiseaseIdentification
        fields = (
            'id', 'item_code', 'item_name', 'disease_name', 
            'is_active', 'recommended_products_count'
        )
    
    def get_recommended_products_count(self, obj):
        """Get count of active recommended products"""
        return obj.recommended_products.filter(is_active=True).count()
