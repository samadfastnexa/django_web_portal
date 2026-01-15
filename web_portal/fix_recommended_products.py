"""
Fix recommended products to use actual products from @ODID table
Run: python manage.py shell < fix_recommended_products.py
"""

import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'web_portal.settings')
django.setup()

from sap_integration.models import DiseaseIdentification, RecommendedProduct

print("\n=== Fixing Recommended Products ===\n")

# Get Potato virus Y disease
try:
    disease = DiseaseIdentification.objects.get(item_code='FG00259')
    print(f"Found disease: {disease.disease_name} ({disease.item_code})")
    
    # Delete old recommendations
    old_count = disease.recommended_products.all().delete()[0]
    print(f"Deleted {old_count} old recommendations")
    
    # Add correct products from @ODID table
    products = [
        {
            'product_item_code': 'FG00259',
            'product_name': 'Eagle 2 (Fuzzy) - 10-Kgs.',
            'dosage': '10 kg per acre',
            'application_method': 'Soil application',
            'timing': 'At planting time',
            'precautions': 'Follow safety guidelines',
            'priority': 1,
            'effectiveness_rating': 9.0,
            'notes': 'Main recommended product for Potato virus Y'
        },
        {
            'product_item_code': 'FG00040',
            'product_name': 'Map - 25-Kgs.',
            'dosage': '25 kg per acre',
            'application_method': 'Soil application or fertigation',
            'timing': 'Apply at early growth stages',
            'precautions': 'Avoid over-application',
            'priority': 2,
            'effectiveness_rating': 8.5,
            'notes': 'Alternative product for Potato virus Y'
        },
    ]
    
    created_count = 0
    for product_data in products:
        product = RecommendedProduct.objects.create(
            disease=disease,
            **product_data
        )
        print(f"✓ Created: {product.product_item_code} - {product.product_name}")
        created_count += 1
    
    print(f"\n✓ Created {created_count} new recommendations")
    print(f"✓ Disease '{disease.disease_name}' now has {disease.recommended_products.count()} products")
    
except DiseaseIdentification.DoesNotExist:
    print("✗ Disease 'Potato virus Y' (FG00259) not found. Please sync from SAP first.")
except Exception as e:
    print(f"✗ Error: {str(e)}")
    import traceback
    traceback.print_exc()

print("\n=== Fix Complete ===\n")
