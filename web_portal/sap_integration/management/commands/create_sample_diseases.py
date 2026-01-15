"""
Django management command to create sample disease identification data
"""

from django.core.management.base import BaseCommand
from sap_integration.models import DiseaseIdentification, RecommendedProduct


class Command(BaseCommand):
    help = 'Create sample disease identification and recommended products data'

    def handle(self, *args, **options):
        self.stdout.write("="*60)
        self.stdout.write("Creating sample disease identification...")
        self.stdout.write("="*60)
        
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
            self.stdout.write(self.style.SUCCESS(f"✓ Created disease: {disease.disease_name}"))
        else:
            self.stdout.write(self.style.WARNING(f"✓ Disease already exists: {disease.disease_name}"))
        
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
                self.stdout.write(self.style.SUCCESS(f"  ✓ Added product: {product.product_name} (Priority: {product.priority})"))
            else:
                self.stdout.write(self.style.WARNING(f"  ✓ Product already exists: {product.product_name}"))
        
        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS(f"✅ Setup complete! Disease '{disease.disease_name}' has {disease.recommended_products.count()} recommended products."))
        
        # Display information
        self.stdout.write("")
        self.stdout.write("="*60)
        self.stdout.write("DISEASE INFORMATION:")
        self.stdout.write("="*60)
        self.stdout.write(f"Disease Name: {disease.disease_name}")
        self.stdout.write(f"Item Code: {disease.item_code}")
        self.stdout.write(f"Doc Entry: {disease.doc_entry}")
        self.stdout.write(f"Description: {disease.description[:100]}...")
        self.stdout.write("")
        
        products = disease.recommended_products.filter(is_active=True).order_by('priority')
        self.stdout.write(f"RECOMMENDED PRODUCTS ({products.count()}):")
        self.stdout.write("-"*60)
        
        for product in products:
            self.stdout.write(f"\n  Priority {product.priority}: {product.product_name}")
            self.stdout.write(f"  Item Code: {product.product_item_code}")
            self.stdout.write(f"  Dosage: {product.dosage}")
            self.stdout.write(f"  Effectiveness: {product.effectiveness_rating}/10")
        
        # Show API endpoints
        self.stdout.write("")
        self.stdout.write("="*60)
        self.stdout.write("API ENDPOINTS AVAILABLE:")
        self.stdout.write("="*60)
        
        endpoints = [
            ("GET /api/sap/diseases/", "List all diseases"),
            ("GET /api/sap/diseases/?search=potato", "Search diseases"),
            ("GET /api/sap/diseases/<id>/", "Get disease details with products"),
            ("GET /api/sap/recommended-products/?item_code=FG00259", "Get products by disease code"),
            ("POST /api/sap/diseases/create/", "Create new disease"),
            ("POST /api/sap/recommended-products/create/", "Add recommended product"),
        ]
        
        for endpoint, description in endpoints:
            self.stdout.write(f"  • {endpoint}")
            self.stdout.write(f"    {description}")
        
        self.stdout.write("")
        self.stdout.write("="*60)
        self.stdout.write("KINDWISE INTEGRATION:")
        self.stdout.write("="*60)
        self.stdout.write("  Kindwise API now automatically includes disease recommendations!")
        self.stdout.write("  Use: /api/kindwise/identify/?include_recommendations=true")
        self.stdout.write("")
        
        self.stdout.write(self.style.SUCCESS("\n✅ All tests complete!"))
        self.stdout.write("\nNext steps:")
        self.stdout.write("1. Access Django Admin to manage diseases and products")
        self.stdout.write("2. Test API endpoints using Swagger UI or Postman")
        self.stdout.write("3. Try Kindwise integration with include_recommendations=true")
        self.stdout.write("4. Add more diseases and products as needed")
