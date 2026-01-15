# Sales Order Form API Workflow

Complete API workflow for the sales order form with customer → policy → item → price cascade.

## API Endpoints (in order of usage)

### 1. **Get Customer Policies** (NEW!)
**When:** Customer is selected in sales order form  
**Purpose:** Populate policy dropdown

```http
GET /api/sap/customer-policies/?database=4B-ORANG&card_code=ORC00001
```

**Response:**
```json
{
  "success": true,
  "page": 1,
  "page_size": 10,
  "count": 2,
  "data": [
    {
      "policy_doc_entry": 27,
      "project_code": null,
      "project_name": null,
      "customer_code": "ORC00001"
    },
    {
      "policy_doc_entry": 28,
      "project_code": "0323040",
      "project_name": "Orange Protection Policy Rate Diff & Policy Incentives",
      "customer_code": "ORC00001"
    }
  ]
}
```

**Parameters:**
- `database` - Company database (e.g., `4B-ORANG`, `4B-ORANG_APP`, `4B-BIO`)
- `card_code` - Customer CardCode (required, e.g., `ORC00001`)
- `page` - Page number (optional, default: 1)
- `page_size` - Items per page (optional, default: 50)

---

### 2. **Get Policy Items**
**When:** Policy is selected in sales order form  
**Purpose:** Populate item dropdown

```http
GET /api/sap/policy-items-lov/?database=4B-ORANG&doc_entry=2&page_size=10
```

**Alternate URL:** `/api/sap/policy-items/` (same endpoint, different alias)

**Response:**
```json
{
  "success": true,
  "page": 1,
  "page_size": 10,
  "count": 168,
  "data": [
    {
      "policy_doc_entry": 2,
      "ItemCode": "FG00004",
      "ItemName": "Afsar 60 Wdg - 120-Gms.",
      "unit_price": -1.0,
      "unit_of_measure": "No"
    },
    {
      "policy_doc_entry": 2,
      "ItemCode": "FG00007",
      "ItemName": "Jalwa 32.5 Sc - 200-Mls.",
      "unit_price": -1.0,
      "unit_of_measure": "No"
    }
  ]
}
```

**Parameters:**
- `database` - Company database (e.g., `4B-ORANG`, `4B-ORANG_APP`, `4B-BIO`)
- `doc_entry` - Policy DocEntry (required, e.g., `2`)
- `card_code` - Customer CardCode (optional filter)
- `page` - Page number (optional, default: 1)
- `page_size` - Items per page (optional, default: 50)

---

### 3. **Get Item Price**
**When:** Item is selected in sales order form  
**Purpose:** Populate price field automatically

```http
GET /api/sap/item-price/?database=4B-ORANG&doc_entry=2&item_code=FG00007
```

**Response:**
```json
{
  "success": true,
  "data": {
    "doc_entry": "2",
    "item_code": "FG00007",
    "unit_price": -1.0
  }
}
```

**Parameters:**
- `database` - Company database (e.g., `4B-ORANG`, `4B-ORANG_APP`, `4B-BIO`)
- `doc_entry` - Policy DocEntry (required, e.g., `2`)
- `item_code` - Item code (required, e.g., `FG00007`)

**Note:** Price `-1` means "use item's standard price" (negotiable/market rate)

---

## Complete Workflow Example

### Step 1: User selects customer "ORC00001" → Get their policies
```javascript
// Frontend code example
const customer = 'ORC00001';
const database = '4B-ORANG';

fetch(`/api/sap/customer-policies/?database=${database}&card_code=${customer}`)
  .then(res => res.json())
  .then(data => {
    // Populate policy dropdown with data.data
    data.data.forEach(policy => {
      console.log(`Policy ${policy.policy_doc_entry}: ${policy.project_name}`);
    });
  });
```

### Step 2: User selects policy "2" → Get available items
```javascript
const policyDocEntry = 2;

fetch(`/api/sap/policy-items-lov/?database=${database}&doc_entry=${policyDocEntry}`)
  .then(res => res.json())
  .then(data => {
    // Populate item dropdown with data.data
    data.data.forEach(item => {
      console.log(`${item.ItemCode}: ${item.ItemName} (${item.unit_of_measure})`);
    });
  });
```

### Step 3: User selects item "FG00007" → Get price automatically
```javascript
const itemCode = 'FG00007';

fetch(`/api/sap/item-price/?database=${database}&doc_entry=${policyDocEntry}&item_code=${itemCode}`)
  .then(res => res.json())
  .then(data => {
    // Auto-fill price field
    const price = data.data.unit_price;
    document.getElementById('price').value = price;
  });
```

---

## Database Parameter Variants

All endpoints accept multiple database parameter formats:
- `4B-ORANG` → resolved to `4B-ORANG_APP`
- `4B-ORANG_APP` → used as-is
- `4B-ORANG-app` → normalized to `4B-ORANG_APP`
- `4B-BIO` → resolved to `4B-BIO_APP`

If omitted, falls back to:
1. Session value (`request.session['selected_db']`)
2. First active company from database
3. Default: `4B-BIO_APP`

---

## API Documentation (Swagger)

All three endpoints are grouped under **"SAP Sales Order Form"** tag in Swagger UI:

```
http://localhost:8000/api/swagger/
```

Look for the "SAP Sales Order Form" section to see interactive documentation with "Try it out" buttons.

---

## Database Tables

These APIs query SAP HANA custom tables:
- `@PL1` - Policy header table (DocEntry, U_proj)
- `@PLR8` - Policy-customer link table (U_bp = CardCode)
- `@PLR4` - Policy items/lines table (U_itc = ItemCode, U_frp = unit price)
- `OITM` - Item master table (ItemName, SalUnitMsr)
- `OPRJ` - Project master table (PrjName)

---

## Error Handling

All endpoints return consistent error format:

```json
{
  "success": false,
  "error": "card_code parameter is required"
}
```

Common HTTP status codes:
- `200` - Success
- `400` - Bad Request (missing required parameters)
- `500` - Server Error (database connection issues, etc.)

---

## Testing with curl

```bash
# Test customer policies
curl "http://localhost:8000/api/sap/customer-policies/?database=4B-ORANG&card_code=ORC00001"

# Test policy items
curl "http://localhost:8000/api/sap/policy-items-lov/?database=4B-ORANG&doc_entry=2"

# Test item price
curl "http://localhost:8000/api/sap/item-price/?database=4B-ORANG&doc_entry=2&item_code=FG00007"
```

---

## Notes

1. **Price value `-1`**: Indicates the item uses standard/negotiable pricing (not a fixed policy price)
2. **Pagination**: All list endpoints support pagination for large result sets
3. **Database consistency**: Use the same `database` parameter across all three API calls in a workflow
4. **Logging**: All endpoints log to console with `[CUSTOMER_POLICIES]`, `[POLICY_ITEMS]`, `[ITEM_PRICE]` prefixes for debugging
