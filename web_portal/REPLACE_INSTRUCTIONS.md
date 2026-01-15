# Instructions to Replace recommended_products_api Function

## Replace in: sap_integration/views.py

Find the function `def recommended_products_api(request):` (around line 6549)

Replace the ENTIRE function body (from `def recommended_products_api(request):` to the end of the function, before the next `def` or EOF) with the code from `new_recommended_products_api.py`

## Key Changes:
1. ✅ NO Django database queries - queries SAP @ODID directly via HANA
2. ✅ Supports multiple products for same disease (e.g., FG00259 and FG00040 both for "Potato virus Y")
3. ✅ Queries OITM table for each product's details
4. ✅ Returns product images (with fallback to ItemCode.jpg if no SAP attachment)
5. ✅ Requires `database` parameter (e.g., 4B-BIO_APP, 4B-ORANG_APP)

## Test:
```bash
# Get all products for "Potato virus Y" (will return FG00259 AND FG00040)
GET /api/sap/recommended-products/?disease_name=Potato virus Y&database=4B-ORANG_APP

# Get product for specific item code
GET /api/sap/recommended-products/?item_code=FG00259&database=4B-ORANG_APP

# Get all products for "Alternaria brown spot"
GET /api/sap/recommended-products/?disease_name=Alternaria brown spot&database=4B-ORANG_APP
```

## Response Format:
```json
{
  "success": true,
  "disease_name": "Potato virus Y",
  "disease_item_code": "FG00259",
  "description": "Disease description from @ODID",
  "database": "4B-ORANG_APP",
  "count": 2,
  "data": [
    {
      "priority": 1,
      "product_item_code": "FG00259",
      "product_name": "Eagle 2 (Fuzzy) - 10-Kgs.",
      "item_group_name": "Cotton Seeds",
      "generic_name": "Eagle-2 Seed Cotton Phutti",
      "brand_name": "Eagle 2 (Fuzzy)",
      "unit_of_measure": "10 KG",
      "product_image_url": "/media/product_images/4B-ORANG/FG00259.jpg",
      "product_description_urdu_url": "/media/product_images/4B-ORANG/FG00259-urdu.jpg",
      "dosage": "As per product label",
      "application_method": "Follow product instructions",
      "timing": "At first symptoms or preventively"
    },
    {
      "priority": 2,
      "product_item_code": "FG00040",
      "product_name": "Map - 25-Kgs.",
      "item_group_name": "Fertilizer",
      ...
    }
  ]
}
```
