# ✅ Disease Sync from SAP @ODID Table

## What Changed

### 1. Removed POST/Create Endpoints ❌
- `/api/sap/diseases/create/` - **REMOVED**
- `/api/sap/recommended-products/create/` - **REMOVED**

Diseases are now synced from SAP `@ODID` table, not created manually.

### 2. Added SAP Sync Function ✅
- **File**: `sap_integration/sap_client.py`
- **Method**: `get_diseases()` - Fetches all diseases from SAP `@ODID` user-defined table

### 3. Added Admin Sync Action ✅
- **Location**: Django Admin → SAP Integration → Disease identifications
- **Button**: "Sync from SAP @ODID" (top right of list page)
- **Action**: Select diseases → Actions → "Sync diseases from SAP @ODID table"

## How to Sync Diseases from SAP

### Option 1: Using Admin Button (Recommended)
1. Go to: `http://localhost:8000/admin/sap_integration/diseaseidentification/`
2. Click **"Sync from SAP @ODID"** button (top right)
3. All diseases from SAP `@ODID` table will be imported/updated

### Option 2: Using Admin Action
1. Go to: `http://localhost:8000/admin/sap_integration/diseaseidentification/`
2. Select any disease records (or none)
3. Choose action: **"Sync diseases from SAP @ODID table"**
4. Click "Go"

## SAP @ODID Table Structure

The sync function reads from SAP user-defined table `@ODID`:

```sql
SELECT 
    "DocEntry",      -- Maps to doc_entry
    "U_ItemCode",    -- Maps to item_code (unique)
    "U_ItemName",    -- Maps to item_name
    "U_Description", -- Maps to description
    "U_Disease"      -- Maps to disease_name
FROM "@ODID"
```

### Example Data:
```sql
INSERT INTO "@ODID"(
    "DocEntry", 
    "U_ItemCode", 
    "U_ItemName", 
    "U_Description",
    "U_Disease"
) VALUES (
    '1235',
    'FG00259',
    'FG00259',
    'Potato virus Y (PVY) is one of the most serious viral diseases...',
    'Potato virus Y'
);

INSERT INTO "@ODID"(
    "DocEntry", 
    "U_ItemCode", 
    "U_ItemName", 
    "U_Description",
    "U_Disease"
) VALUES (
    '1236',
    'FG00040',
    'FG00040',
    'Late blight disease description...',
    'Late Blight'
);
```

## API Usage After Sync

### Get Recommended Products
```bash
# Query by item code (from @ODID)
GET /api/sap/recommended-products/?item_code=FG00040&database=4B-ORANG_APP

# Query by disease ID
GET /api/sap/recommended-products/?disease_id=1&database=4B-BIO_APP
```

### Expected Flow:
1. **Add disease to SAP**: Insert into `@ODID` table in SAP
2. **Sync to Django**: Click "Sync from SAP @ODID" in admin
3. **Add product recommendations**: In Django admin, edit disease and add recommended products inline
4. **API returns products**: GET endpoint returns products with images from HANA catalog

## Workflow Example

### Step 1: Add Disease in SAP
```sql
-- In SAP HANA or B1 Service Layer
INSERT INTO "@ODID"(
    "DocEntry", 
    "U_ItemCode", 
    "U_ItemName", 
    "U_Description",
    "U_Disease"
) VALUES (
    '1237',
    'FG00040',
    'Late Blight Disease',
    'Late blight is caused by Phytophthora infestans...',
    'Late Blight'
);
```

### Step 2: Sync in Django Admin
1. Go to admin: `/admin/sap_integration/diseaseidentification/`
2. Click **"Sync from SAP @ODID"**
3. Result: Disease `FG00040` now in Django

### Step 3: Add Product Recommendations
1. In admin, click on disease `FG00040`
2. Scroll to **Recommended Products** section
3. Add products inline:
   - Product Item Code: `FG00100`
   - Product Name: `Fungicide X`
   - Dosage: `2L per acre`
   - Priority: `1`
   - Effectiveness Rating: `8.5`
4. Save

### Step 4: API Returns Products
```bash
curl "http://localhost:8000/api/sap/recommended-products/?item_code=FG00040&database=4B-ORANG_APP"
```

**Response:**
```json
{
  "success": true,
  "disease_name": "Late Blight",
  "disease_item_code": "FG00040",
  "database": "4B-ORANG_APP",
  "count": 1,
  "data": [
    {
      "id": 4,
      "product_item_code": "FG00100",
      "product_name": "Fungicide X",
      "dosage": "2L per acre",
      "priority": 1,
      "effectiveness_rating": 8.5,
      "product_image_url": "/media/product_images/4B-ORANG/FG00100.jpg",
      "item_group_name": "Fungicides",
      "generic_name": "Mancozeb 80%",
      "brand_name": "Fungicide X Pro"
    }
  ]
}
```

## Database Schema Selection

The sync respects the selected database in admin session:
- Session variable: `selected_db`
- Default: `4B-BIO`
- Alternatives: `4B-ORANG`, etc.

Each database can have different diseases in their `@ODID` table.

## Files Modified

1. **sap_integration/sap_client.py** - Added `get_diseases()` method
2. **sap_integration/admin.py** - Added sync action and button
3. **sap_integration/urls.py** - Removed create endpoints
4. **sap_integration/views.py** - Removed create API functions
5. **templates/admin/.../change_list.html** - Added sync button template

## Benefits

✅ **Single Source of Truth** - Diseases managed in SAP `@ODID` table  
✅ **No Manual Entry** - Auto-sync from SAP with one click  
✅ **Multi-Database Support** - Sync different diseases per company  
✅ **Product Recommendations** - Add in Django admin with inline editing  
✅ **HANA Integration** - Product images fetched automatically  

---

**Next Steps:**
1. Add your diseases to SAP `@ODID` table
2. Click "Sync from SAP @ODID" in admin
3. Add product recommendations for each disease
4. Test API with `item_code` parameter
