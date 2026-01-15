# Disease Identification & Recommended Products - Implementation Guide

## Overview

This implementation adds a complete disease identification and recommended products management system to your Django web portal. It includes:

1. **Separate Disease Management** - Standalone models for diseases and recommended products
2. **RESTful API Endpoints** - Full CRUD operations via API
3. **Kindwise Integration** - Optional disease recommendations in Kindwise responses
4. **Django Admin Interface** - Easy management of diseases and products

## Database Schema

### DiseaseIdentification Model
Maps to SAP @ODID table structure:
- `doc_entry` - DocEntry from SAP (e.g., '1235')
- `item_code` - U_ItemCode (unique, e.g., 'FG00259')
- `item_name` - U_ItemName
- `description` - U_Description (detailed disease info)
- `disease_name` - U_Disease (disease scientific/common name)
- `is_active` - Boolean for active/inactive status

### RecommendedProduct Model
Links products to diseases:
- `disease` - Foreign key to DiseaseIdentification
- `product_item_code` - SAP Item Code (e.g., 'FG00100')
- `product_name` - Product name
- `dosage` - Recommended dosage
- `application_method` - How to apply
- `timing` - When to apply
- `precautions` - Safety warnings
- `priority` - Recommendation priority (1=highest)
- `effectiveness_rating` - Rating out of 10
- `is_active` - Boolean

## API Endpoints

All endpoints are under `/api/sap/` prefix:

### 1. List All Diseases
```
GET /api/sap/diseases/
```

**Query Parameters:**
- `is_active` (optional): Filter by active status (true/false)
- `search` (optional): Search by disease name or item code

**Example Response:**
```json
{
  "success": true,
  "count": 1,
  "data": [
    {
      "id": 1,
      "item_code": "FG00259",
      "disease_name": "Potato virus Y",
      "is_active": true,
      "recommended_products_count": 3
    }
  ]
}
```

### 2. Get Disease Details
```
GET /api/sap/diseases/<disease_id>/
GET /api/sap/diseases/?item_code=FG00259
```

### 3. Get Recommended Products
```
GET /api/sap/recommended-products/?disease_id=<id>
GET /api/sap/recommended-products/?item_code=FG00259
```

## Kindwise Integration

The Kindwise API automatically includes disease recommendations when `include_recommendations=true`.

**Usage:**
```
POST /api/kindwise/identify/?include_recommendations=true
```

## Quick Start

### 1. Run Migrations (Already Done)
```bash
python manage.py migrate sap_integration
```

### 2. Create Sample Data
```bash
python manage.py create_sample_diseases
```

### 3. Access Admin
Go to `/admin/sap_integration/diseaseidentification/`

## Test the Implementation

Sample data created:
- **Disease**: Potato virus Y (FG00259)
- **Products**: 3 recommended products with priorities 1-3

**Test URLs:**
- List diseases: `http://localhost:8000/api/sap/diseases/`
- Get products: `http://localhost:8000/api/sap/recommended-products/?item_code=FG00259`
- Kindwise with recommendations: `http://localhost:8000/api/kindwise/identify/?include_recommendations=true`

## Next Steps

1. Add more diseases via Django Admin
2. Link products to diseases
3. Test Kindwise integration with real disease images
4. Use the API in your frontend application
