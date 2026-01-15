"""
Test script for Disease Identification and Recommended Products functionality
Run this from the Django shell or as a management command
"""

from sap_integration.models import DiseaseIdentification, RecommendedProduct


def create_sample_data():
    """Create sample disease and recommended products"""
    
    print("Creating sample disease identification...")
    
    # Create the disease from your example
    disease, created = DiseaseIdentification.objects.get_or_create(
        item_code='FG00259',
        defaults={
            'doc_entry': '1235',
            'item_name': 'FG00259',
            'description': (
                'Potato virus Y (PVY) is one of the most serious viral diseases of potato worldwide. '
                'It belongs to the genus Potyvirus and infects potatoes, tobacco, tomato, pepper, '
                'and other plants in the Solanaceae family.'
            ),
            'disease_name': 'Potato virus Y',
            'is_active': True
        }
    )
    
    if created:
        print(f"✓ Created disease: {disease.disease_name}")
    else:
        print(f"✓ Disease already exists: {disease.disease_name}")
    
    # Create some sample recommended products
    products_data = [
        {
            'product_item_code': 'FG00100',
            'product_name': 'Antiviral Spray Pro',
            'dosage': '500ml per acre',
            'application_method': 'Foliar spray - apply evenly on all plant surfaces',
            'timing': 'At first symptoms or preventively every 15 days',
            'precautions': 'Wear protective equipment. Do not apply during rain or strong wind.',
            'priority': 1,
            'effectiveness_rating': 8.5,
            'notes': 'Most effective when applied early'
        },
        {
            'product_item_code': 'FG00101',
            'product_name': 'Viral Defense',
            'dosage': '300ml per acre',
            'application_method': 'Foliar spray with systemic action',
            'timing': 'Apply at 7-day intervals for severe infections',
            'precautions': 'Avoid contact with skin. Store in cool, dry place.',
            'priority': 2,
            'effectiveness_rating': 7.8,
            'notes': 'Good for systemic protection'
        },
        {
            'product_item_code': 'FG00102',
            'product_name': 'Bio-Shield Organic',
            'dosage': '1 liter per acre',
            'application_method': 'Organic foliar spray - mix with water',
            'timing': 'Preventive: every 10-14 days. Curative: every 5-7 days',
            'precautions': 'Safe for organic farming. No waiting period before harvest.',
            'priority': 3,
            'effectiveness_rating': 7.0,
            'notes': 'Organic certified, environmentally friendly'
        }
    ]
    
    for product_data in products_data:
        product, created = RecommendedProduct.objects.get_or_create(
            disease=disease,
            product_item_code=product_data['product_item_code'],
            defaults={
                **product_data,
                'is_active': True
            }
        )
        
        if created:
            print(f"  ✓ Added product: {product.product_name} (Priority: {product.priority})")
        else:
            print(f"  ✓ Product already exists: {product.product_name}")
    
    print(f"\n✅ Setup complete! Disease '{disease.disease_name}' has {disease.recommended_products.count()} recommended products.")
    return disease


def test_api_endpoints():
    """Test that the API endpoints are working"""
    print("\n" + "="*60)
    print("API ENDPOINTS AVAILABLE:")
    print("="*60)
    
    endpoints = [
        ("GET /api/sap/diseases/", "List all diseases"),
        ("GET /api/sap/diseases/?search=potato", "Search diseases"),
        ("GET /api/sap/diseases/<id>/", "Get disease details with products"),
        ("GET /api/sap/diseases/?item_code=FG00259", "Get disease by item code"),
        ("GET /api/sap/recommended-products/?disease_id=<id>", "Get products for disease"),
        ("GET /api/sap/recommended-products/?item_code=FG00259", "Get products by disease code"),
        ("POST /api/sap/diseases/create/", "Create new disease"),
        ("POST /api/sap/recommended-products/create/", "Add recommended product"),
    ]
    
    for endpoint, description in endpoints:
        print(f"  • {endpoint}")
        print(f"    {description}")
        print()
    
    print("="*60)
    print("KINDWISE INTEGRATION:")
    print("="*60)
    print("  Kindwise API now automatically includes disease recommendations!")
    print("  Use: /api/kindwise/identify/?include_recommendations=true")
    print()


def display_disease_info():
    """Display created disease information"""
    try:
        disease = DiseaseIdentification.objects.get(item_code='FG00259')
        
        print("\n" + "="*60)
        print("DISEASE INFORMATION:")
        print("="*60)
        print(f"Disease Name: {disease.disease_name}")
        print(f"Item Code: {disease.item_code}")
        print(f"Doc Entry: {disease.doc_entry}")
        print(f"Description: {disease.description[:100]}...")
        print()
        
        products = disease.recommended_products.filter(is_active=True).order_by('priority')
        print(f"RECOMMENDED PRODUCTS ({products.count()}):")
        print("-"*60)
        
        for product in products:
            print(f"\n  Priority {product.priority}: {product.product_name}")
            print(f"  Item Code: {product.product_item_code}")
            print(f"  Dosage: {product.dosage}")
            print(f"  Effectiveness: {product.effectiveness_rating}/10")
            print(f"  Application: {product.application_method}")
            
    except DiseaseIdentification.DoesNotExist:
        print("Disease not found. Run create_sample_data() first.")


if __name__ == '__main__':
    print("="*60)
    print("DISEASE IDENTIFICATION & RECOMMENDED PRODUCTS")
    print("Testing Implementation")
    print("="*60)
    print()
    
    # Create sample data
    disease = create_sample_data()
    
    # Display information
    display_disease_info()
    
    # Show API endpoints
    test_api_endpoints()
    
    print("\n✅ All tests complete!")
    print("\nNext steps:")
    print("1. Access Django Admin to manage diseases and products")
    print("2. Test API endpoints using Swagger UI or Postman")
    print("3. Try Kindwise integration with include_recommendations=true")
    print("4. Add more diseases and products as needed")
