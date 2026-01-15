"""
Quick test to verify the disease products API with images integration
"""

from django.test.client import Client
import json

def test_disease_api():
    """Test disease listing API"""
    client = Client()
    
    print("="*60)
    print("Testing Disease API Endpoints")
    print("="*60)
    
    # Test 1: List all diseases
    print("\n1. GET /api/sap/diseases/")
    response = client.get('/api/sap/diseases/')
    data = response.json()
    print(f"Status: {response.status_code}")
    print(f"Count: {data.get('count')}")
    if data.get('data'):
        print(f"First disease: {data['data'][0]['disease_name']}")
    
    # Test 2: Get disease details
    if data.get('data') and len(data['data']) > 0:
        disease_id = data['data'][0]['id']
        print(f"\n2. GET /api/sap/diseases/{disease_id}/")
        response = client.get(f'/api/sap/diseases/{disease_id}/')
        data = response.json()
        print(f"Status: {response.status_code}")
        if data.get('success'):
            disease_data = data['data']
            print(f"Disease: {disease_data['disease_name']}")
            print(f"Item Code: {disease_data['item_code']}")
            print(f"Recommended Products: {disease_data['recommended_products_count']}")
    
    # Test 3: Get recommended products
    print("\n3. GET /api/sap/recommended-products/?item_code=FG00259")
    response = client.get('/api/sap/recommended-products/?item_code=FG00259')
    data = response.json()
    print(f"Status: {response.status_code}")
    print(f"Success: {data.get('success')}")
    print(f"Disease: {data.get('disease_name')}")
    print(f"Count: {data.get('count')}")
    
    if data.get('data'):
        print(f"\nProduct Details:")
        for idx, product in enumerate(data['data'], 1):
            print(f"\n  Product {idx}:")
            print(f"    Name: {product.get('product_name')}")
            print(f"    Item Code: {product.get('product_item_code')}")
            print(f"    Priority: {product.get('priority')}")
            print(f"    Effectiveness: {product.get('effectiveness_rating')}/10")
            print(f"    Dosage: {product.get('dosage')}")
            
            # Check if HANA catalog data is included
            print(f"    Image URL: {product.get('product_image_url') or 'Not available'}")
            print(f"    Category: {product.get('item_group_name') or 'Not fetched from HANA'}")
            print(f"    Generic Name: {product.get('generic_name') or 'Not available'}")
    
    print("\n" + "="*60)
    print("✅ API Tests Complete!")
    print("="*60)
    
    # Summary
    print("\nAPI Endpoints Available:")
    print("  • GET /api/sap/diseases/")
    print("  • GET /api/sap/diseases/<id>/")
    print("  • GET /api/sap/recommended-products/?item_code=FG00259")
    print("  • POST /api/kindwise/identify/?include_recommendations=true")
    
    print("\nNote: Product images from HANA catalog require:")
    print("  1. HANA database connection configured")
    print("  2. Product images in /media/product_images/ folders")
    print("  3. Database parameter in request (optional)")

if __name__ == '__main__':
    test_disease_api()
