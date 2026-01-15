"""
Disease Matcher Utility for Kindwise Integration
Matches disease identifications from Kindwise API with local disease database
and provides recommended products with images from HANA catalog.
"""

import logging
import os
from typing import Dict, List, Optional
from django.db.models import Q
from django.conf import settings
from pathlib import Path

logger = logging.getLogger(__name__)


def get_product_catalog_data(product_codes: List[str], database: str = None) -> Dict:
    """
    Fetch product catalog data from HANA for given product codes.
    
    Args:
        product_codes: List of product item codes
        database: Database schema to query
    
    Returns:
        Dictionary mapping ItemCode to product data with images
    """
    if not product_codes:
        return {}
    
    try:
        from sap_integration.hana_connect import (
            _load_env_file as _hana_load_env_file,
            products_catalog
        )
        from hdbcli import dbapi
        
        # Load environment variables
        try:
            _hana_load_env_file(os.path.join(os.path.dirname(os.path.dirname(__file__)), 'sap_integration', '.env'))
            _hana_load_env_file(os.path.join(str(settings.BASE_DIR), '.env'))
            _hana_load_env_file(os.path.join(str(Path(settings.BASE_DIR).parent), '.env'))
        except Exception:
            pass
        
        # Get database schema
        if not database:
            database = os.environ.get('HANA_SCHEMA', '4B-BIO_APP')
        
        cfg = {
            'host': os.environ.get('HANA_HOST', ''),
            'port': os.environ.get('HANA_PORT', ''),
            'user': os.environ.get('HANA_USER', ''),
            'encrypt': os.environ.get('HANA_ENCRYPT', ''),
            'schema': database
        }
        
        pwd = os.environ.get('HANA_PASSWORD', '')
        kwargs = {
            'address': cfg['host'],
            'port': int(cfg['port']),
            'user': cfg['user'],
            'password': pwd
        }
        
        if str(cfg['encrypt']).strip().lower() in ('true', '1', 'yes'):
            kwargs['encrypt'] = True
            kwargs['sslValidateCertificate'] = False  # Skip SSL validation
        
        conn = dbapi.connect(**kwargs)
        
        try:
            # Set schema
            if cfg['schema']:
                cur = conn.cursor()
                cur.execute(f'SET SCHEMA "{cfg["schema"]}"')
                cur.close()
            
            # Fetch all products (we'll filter later)
            catalog_data = products_catalog(conn, cfg['schema'])
            
            # Create lookup dictionary
            product_catalog = {}
            for item in catalog_data:
                item_code = item.get('ItemCode')
                if item_code and item_code in product_codes:
                    product_catalog[item_code] = item
            
            return product_catalog
            
        finally:
            conn.close()
            
    except Exception as e:
        logger.error(f"Error fetching product catalog: {str(e)}")
        return {}


def get_disease_recommendations(disease_name: str, threshold: float = 0.5, include_images: bool = True) -> Optional[Dict]:
    """
    Match a disease name from Kindwise with local disease database
    and return recommended products with images from HANA.
    
    Args:
        disease_name: Disease name from Kindwise API
        threshold: Minimum similarity threshold (not used in basic matching)
        include_images: Whether to fetch product images from HANA catalog
    
    Returns:
        Dictionary with disease info and recommended products, or None if no match
    """
    try:
        from sap_integration.models import DiseaseIdentification
        from sap_integration.serializers import RecommendedProductSerializer
        
        # Try exact match first
        disease = None
        try:
            disease = DiseaseIdentification.objects.get(
                Q(disease_name__iexact=disease_name) |
                Q(item_name__iexact=disease_name),
                is_active=True
            )
        except DiseaseIdentification.DoesNotExist:
            # Try partial match
            disease = DiseaseIdentification.objects.filter(
                Q(disease_name__icontains=disease_name) |
                Q(item_name__icontains=disease_name) |
                Q(description__icontains=disease_name),
                is_active=True
            ).first()
        except DiseaseIdentification.MultipleObjectsReturned:
            # If multiple matches, get the first one
            disease = DiseaseIdentification.objects.filter(
                Q(disease_name__iexact=disease_name) |
                Q(item_name__iexact=disease_name),
                is_active=True
            ).first()
        
        if not disease:
            logger.debug(f"No disease match found for: {disease_name}")
            return None
        
        # Get active recommended products
        recommended_products = disease.recommended_products.filter(is_active=True).order_by('priority', '-effectiveness_rating')
        
        if not recommended_products.exists():
            logger.debug(f"Disease {disease_name} found but has no recommended products")
            return {
                'disease_id': disease.id,
                'disease_item_code': disease.item_code,
                'disease_name': disease.disease_name,
                'description': disease.description,
                'recommended_products': []
            }
        
        # Fetch product catalog data if requested
        product_catalog = {}
        if include_images:
            product_codes = [p.product_item_code for p in recommended_products if p.product_item_code]
            product_catalog = get_product_catalog_data(product_codes)
        
        # Serialize products with product catalog context
        serializer = RecommendedProductSerializer(
            recommended_products, 
            many=True,
            context={'product_catalog': product_catalog}
        )
        
        return {
            'disease_id': disease.id,
            'disease_item_code': disease.item_code,
            'disease_name': disease.disease_name,
            'description': disease.description,
            'recommended_products': serializer.data
        }
        
    except Exception as e:
        logger.error(f"Error matching disease {disease_name}: {str(e)}")
        import traceback
        traceback.print_exc()
        return None


def enrich_kindwise_response(kindwise_result: Dict, include_recommendations: bool = True) -> Dict:
    """
    Enrich Kindwise API response with local disease recommendations.
    
    Args:
        kindwise_result: Original response from Kindwise API
        include_recommendations: Whether to include product recommendations
    
    Returns:
        Enhanced response with disease recommendations
    """
    if not include_recommendations:
        return kindwise_result
    
    try:
        # Extract disease suggestions from Kindwise result
        result_data = kindwise_result.get('result', {})
        disease_data = result_data.get('disease', {})
        disease_suggestions = disease_data.get('suggestions', [])
        
        if not disease_suggestions:
            logger.debug("No disease suggestions in Kindwise result")
            return kindwise_result
        
        # Match each disease and add recommendations
        enriched_suggestions = []
        for suggestion in disease_suggestions:
            disease_name = suggestion.get('name', '')
            probability = suggestion.get('probability', 0)
            
            # Create enriched suggestion with original data
            enriched = {**suggestion}  # Copy all original fields
            
            # Only add recommendations for high-confidence matches
            if probability >= 0.3:  # 30% confidence threshold
                recommendations = get_disease_recommendations(disease_name)
                if recommendations:
                    enriched['local_disease_match'] = recommendations
                    logger.info(f"Matched disease {disease_name} with {len(recommendations.get('recommended_products', []))} products")
            
            enriched_suggestions.append(enriched)
        
        # Update the result with enriched suggestions
        kindwise_result_copy = {**kindwise_result}
        if 'result' in kindwise_result_copy:
            if 'disease' in kindwise_result_copy['result']:
                kindwise_result_copy['result']['disease']['suggestions'] = enriched_suggestions
        
        return kindwise_result_copy
        
    except Exception as e:
        logger.error(f"Error enriching Kindwise response: {str(e)}")
        # Return original result on error
        return kindwise_result


def get_recommendations_for_kindwise_record(record_id: int) -> List[Dict]:
    """
    Get all disease recommendations for a Kindwise identification record.
    
    Args:
        record_id: KindwiseIdentification record ID
    
    Returns:
        List of disease recommendations with products
    """
    try:
        from kindwise.models import KindwiseIdentification
        
        record = KindwiseIdentification.objects.get(pk=record_id)
        response_payload = record.response_payload
        
        if not response_payload:
            return []
        
        result_data = response_payload.get('result', {})
        disease_data = result_data.get('disease', {})
        disease_suggestions = disease_data.get('suggestions', [])
        
        recommendations = []
        for suggestion in disease_suggestions:
            disease_name = suggestion.get('name', '')
            probability = suggestion.get('probability', 0)
            
            disease_recs = get_disease_recommendations(disease_name)
            if disease_recs:
                recommendations.append({
                    'disease_name': disease_name,
                    'kindwise_probability': probability,
                    **disease_recs
                })
        
        return recommendations
        
    except Exception as e:
        logger.error(f"Error getting recommendations for record {record_id}: {str(e)}")
        return []
