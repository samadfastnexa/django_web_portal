# ✅ Sales Order - Complete Swagger & Admin Configuration Check

## 📋 Overview
The Sales Order (SO) creation API and admin interface support **multiple line items** based on policies. All fields are properly wired between:
- ✅ Django Admin Form
- ✅ Swagger API Documentation  
- ✅ Serializers
- ✅ Model Inlines

---

## 🎯 Header Fields (Parent/Order Level)

All fields are properly configured in:
- **Admin**: `SalesOrderForm` in `FieldAdvisoryService/admin.py`
- **API**: `SalesOrderSerializer` in `FieldAdvisoryService/serializers.py`
- **Swagger**: Documented in `SalesOrderViewSet.create()` in `FieldAdvisoryService/views.py`

### Core Order Fields
| Field | Type | Admin | Swagger | Serializer | Required |
|-------|------|-------|---------|-----------|----------|
| `staff` | FK(User) | ✅ | ✅ | ✅ | ❌ |
| `dealer` | FK(Dealer) | ✅ | ✅ | ✅ | ❌ |
| `status` | Choice | ✅ | ✅ | ✅ | ❌ |
| `series` | Integer | ✅ Readonly | ✅ | ✅ | ❌ |
| `doc_type` | Choice | ✅ Readonly | ✅ | ✅ | ❌ |
| `doc_date` | Date | ✅ | ✅ | ✅ | ❌ |
| `doc_due_date` | Date | ✅ | ✅ | ✅ | ❌ |
| `tax_date` | Date | ✅ | ✅ | ✅ | ❌ |

### Customer Fields
| Field | Type | Admin | Swagger | Serializer | Notes |
|-------|------|-------|---------|-----------|-------|
| `card_code` | String | ✅ Select LOV | ✅ | ✅ | Auto-populates customer data |
| `card_name` | String | ✅ Auto-filled | ✅ | ✅ | From SAP customer |
| `contact_person_code` | Integer | ✅ Auto-filled | ✅ | ✅ | From SAP |
| `federal_tax_id` | String | ✅ Auto-filled | ✅ | ✅ | NTN from SAP |
| `pay_to_code` | Integer | ✅ Auto-filled | ✅ | ✅ | From SAP |
| `address` | Text | ✅ | ✅ | ✅ | Billing address |

### Child Customer (Optional)
| Field | Type | Admin | Swagger | Serializer | Notes |
|-------|------|-------|---------|-----------|-------|
| `u_s_card_code` | String | ✅ Select LOV | ✅ | ✅ | Parent-dependent dropdown |
| `u_s_card_name` | String | ✅ Auto-filled | ✅ | ✅ | From child customer |

### Additional Fields
| Field | Type | Admin | Swagger | Serializer |
|-------|------|-------|---------|-----------|
| `doc_currency` | String | ✅ | ✅ | ✅ |
| `doc_rate` | Decimal | ✅ | ✅ | ✅ |
| `comments` | Text | ✅ Collapse | ✅ | ✅ |
| `u_sotyp` | String | ✅ | ✅ | ✅ |
| `u_usid` | String | ✅ | ✅ | ✅ |

---

## 📦 Line Item Fields (SalesOrderLine)

All line items are **properly wired** for multiple items support:

### Admin Configuration
- **Inline**: `SalesOrderLineInline` (TabularInline)
- **Form**: `SalesOrderLineInlineForm`
- **Location**: Shows as inline table in SalesOrder admin
- **Multiple Items**: ✅ Extra forms available (extra=1 by default)
- **JavaScript Support**: Yes, for dynamic item selection & pricing

### Swagger/API Configuration
- **Serializer**: `SalesOrderLineSerializer` (nested in SalesOrderSerializer)
- **Support**: `document_lines` array in request body
- **Format**: Form-data with array parameters (item_code[0], item_code[1], etc.)
- **Multiple Items**: ✅ Unlimited line items via arrays

### Line Item Fields
| Field | Type | Admin | Swagger | Serializer | Notes |
|-------|------|-------|---------|-----------|-------|
| `line_num` | Integer | Hidden | ✅ | ✅ | Auto-assigned by index |
| `item_code` | String | ✅ Select LOV | ✅ Array | ✅ | SAP item selection |
| `item_description` | String | ✅ Readonly | ✅ Array | ✅ | Auto-filled from item |
| `quantity` | Decimal | ✅ | ✅ Array | ✅ | Required per line |
| `unit_price` | Decimal | ✅ | ✅ Array | ✅ | From policy/item |
| `discount_percent` | Decimal | ✅ | ✅ Array | ✅ | % discount |
| `warehouse_code` | String | ✅ Select LOV | ✅ Array | ✅ | SAP warehouse |
| `vat_group` | String | ✅ Select LOV | ✅ Array | ✅ | SAP tax code |
| `tax_percentage_per_row` | Decimal | Hidden | ✅ Array | ✅ | Tax % per line |
| `measure_unit` | String | ✅ Readonly | ✅ Array | ✅ | UoM name |
| `uom_code` | String | ✅ Readonly | ✅ Array | ✅ | UoM code |
| `units_of_measurment` | Decimal | Hidden | ✅ Array | ✅ | UoM conversion |
| `uom_entry` | Integer | Hidden | ✅ Array | ✅ | UoM ID |
| `project_code` | String | ✅ Select LOV | ✅ Array | ✅ | SAP project |
| `u_crop` | String | ✅ Select LOV | ✅ Array | ✅ | Crop selection |
| `u_policy` | String | ✅ Select LOV | ✅ Array | ✅ | Policy code |
| `u_pl` | Integer | ✅ | ✅ Array | ✅ | Policy link ID |
| `u_bp` | Decimal | Hidden | ✅ Array | ✅ | Project balance |
| `u_sd` | Decimal | Hidden | ✅ Array | ✅ | Special discount % |
| `u_ad` | Decimal | Hidden | ✅ Array | ✅ | Additional discount % |
| `u_exd` | Decimal | Hidden | ✅ Array | ✅ | Extra discount % |
| `u_zerop` | Decimal | Hidden | ✅ Array | ✅ | Phase discount % |
| `u_focitem` | String | Hidden | ✅ Array | ✅ | FOC item flag |

---

## 🔄 Multiple Items Example

### Admin Form
When adding a Sales Order in admin:
1. Create main order with customer details
2. Scroll to **Sales Order Lines** inline section
3. Click "Add another Sales Order Line"
4. Fill in item details (item code, quantity, warehouse, etc.)
5. Repeat for each line item
6. Save order

### Swagger API Request
```bash
curl -X POST http://localhost:8000/api/sales-orders/ \
  -F "staff=1" \
  -F "dealer=1" \
  -F "card_code=C20000" \
  -F "status=pending" \
  -F "item_code[0]=SEED-001" \
  -F "item_code[1]=FERT-001" \
  -F "quantity[0]=10" \
  -F "quantity[1]=5" \
  -F "unit_price[0]=2500" \
  -F "unit_price[1]=1500" \
  -F "warehouse_code[0]=WH01" \
  -F "warehouse_code[1]=WH01" \
  -F "vat_group[0]=SE" \
  -F "vat_group[1]=AT1" \
  -F "u_crop[0]=CORN" \
  -F "u_crop[1]=WHEAT" \
  -F "u_policy[0]=POL-001" \
  -F "u_policy[1]=POL-002"
```

### Response (Nested document_lines)
```json
{
  "id": 1,
  "staff": 1,
  "dealer": 1,
  "card_code": "C20000",
  "card_name": "ABC Traders",
  "status": "pending",
  "document_lines": [
    {
      "id": 1,
      "line_num": 1,
      "item_code": "SEED-001",
      "item_description": "Corn Seed",
      "quantity": 10,
      "unit_price": 2500,
      "warehouse_code": "WH01",
      "vat_group": "SE",
      "u_crop": "CORN",
      "u_policy": "POL-001"
    },
    {
      "id": 2,
      "line_num": 2,
      "item_code": "FERT-001",
      "item_description": "Fertilizer",
      "quantity": 5,
      "unit_price": 1500,
      "warehouse_code": "WH01",
      "vat_group": "AT1",
      "u_crop": "WHEAT",
      "u_policy": "POL-002"
    }
  ]
}
```

---

## ✅ Verification Checklist

### Admin Side
- [x] `SalesOrderForm` - All header fields present
- [x] `SalesOrderLineInlineForm` - All line item fields present
- [x] `SalesOrderLineInline` - Properly configured for multiple items
- [x] LOV dropdowns - item_code, warehouse_code, vat_group, project_code, u_crop, u_policy
- [x] Auto-fill fields - card_name, contact_person, federal_tax_id, address
- [x] Child customer dropdown - Dependent on parent card_code
- [x] Readonly fields - item_description, measure_unit
- [x] JavaScript support - For dynamic pricing & child customers

### Swagger/API Side
- [x] `SalesOrderSerializer` - All fields documented
- [x] `SalesOrderLineSerializer` - Nested in main serializer
- [x] `SalesOrderViewSet.create()` - Comprehensive swagger_auto_schema
- [x] Header parameters - All documented
- [x] Line item array parameters - All documented with examples
- [x] Multiple items support - Via array format (param[0], param[1], etc.)
- [x] Response example - Shows nested document_lines

### Model & Database
- [x] `SalesOrder` model - All fields properly defined
- [x] `SalesOrderLine` model - Proper FK relationship to SalesOrder
- [x] Serializer `_create_lines()` - Handles bulk line creation
- [x] Serializer `to_internal_value()` - Handles JSON string conversion

---

## 🚀 How to Create Sales Order with Multiple Items

### Method 1: Django Admin
1. Go to **Admin → Sales Orders**
2. Click **Add Sales Order**
3. Fill header fields (staff, dealer, customer)
4. Scroll to **Sales Order Lines** section
5. Add multiple line items:
   - Line 1: Item A, Qty 10, Price 2500, Warehouse WH01, Policy POL-001
   - Line 2: Item B, Qty 5, Price 1500, Warehouse WH01, Policy POL-002
6. Save

### Method 2: Swagger API
1. Go to **Swagger UI** (`/api/docs/`)
2. Navigate to **POST /api/sales-orders/**
3. Fill in form-data:
   - Header fields
   - Item arrays (item_code[0], item_code[1], etc.)
   - Line item arrays for all fields
4. Click **Execute**

### Method 3: cURL/Postman
```bash
curl -X POST \
  http://localhost:8000/api/sales-orders/ \
  -H 'Authorization: Bearer YOUR_TOKEN' \
  -F 'staff=1' \
  -F 'dealer=1' \
  -F 'item_code[0]=SEED-001' \
  -F 'item_code[1]=FERT-001' \
  -F 'quantity[0]=10' \
  -F 'quantity[1]=5'
```

---

## 📍 File Locations

| Component | File | Location |
|-----------|------|----------|
| Model | SalesOrder, SalesOrderLine | `FieldAdvisoryService/models.py` |
| Serializer | SalesOrderSerializer | `FieldAdvisoryService/serializers.py` |
| Admin Form | SalesOrderForm, SalesOrderLineInlineForm | `FieldAdvisoryService/admin.py` |
| Admin Register | SalesOrderAdmin, SalesOrderLineInline | `FieldAdvisoryService/admin.py` |
| ViewSet | SalesOrderViewSet | `FieldAdvisoryService/views.py` |
| URLs | sales-orders endpoint | `FieldAdvisoryService/urls.py` |

---

## 🎉 Summary

✅ **All Fields Are Properly Wired:**
- Admin and Swagger support **identical fields**
- **Multiple line items** supported via inline forms (admin) and arrays (API)
- **Policy-based items** with proper LOV dropdowns
- **Auto-fill functionality** for customer & item data
- **Full JavaScript integration** for dynamic pricing & dependencies

**Everything is ready for production use!**
