# Policy Items for Customer API

## Overview
New endpoint to fetch all items in a specific policy, with optional filtering by customer/Business Partner CardCode. This allows you to see what items are available under a policy and their pricing.

## Endpoint Details

**URL:** `/api/sap/policy-items/`  
**Method:** `GET`  
**Authentication:** Required (same as other SAP endpoints)

## Query Parameters

### Required
- `doc_entry` (string): Policy DocEntry number
  - Example: `18`
  - This is the primary key of the policy in @PL1 table

### Optional
- `database` (string): Database/schema to query
  - Options: `4B-BIO-app`, `4B-ORANG-app`
  - Default: `4B-BIO_APP`
  - Example: `4B-ORANG-app`

- `card_code` (string): Business Partner CardCode to filter results
  - When provided, only returns items if the policy is assigned to this customer
  - Example: `C-00001`

- `page` (integer): Page number for pagination
  - Default: `1`
  - Example: `2`

- `page_size` (integer): Number of items per page
  - Default: `50`
  - Example: `20`

## Response Format

### Success Response (200 OK)
```json
{
  "success": true,
  "page": 1,
  "page_size": 50,
  "num_pages": 3,
  "count": 125,
  "data": [
    {
      "policy_doc_entry": "18",
      "policy_name": "Standard Fertilizer Policy 2026",
      "valid_from": "2026-01-01",
      "valid_to": "2026-12-31",
      "bp_code": "C-00001",
      "ItemCode": "FG00316",
      "ItemName": "NPK Fertilizer 20-20-20",
      "unit_price": "1250.00",
      "Currency": "PKR"
    },
    {
      "policy_doc_entry": "18",
      "policy_name": "Standard Fertilizer Policy 2026",
      "valid_from": "2026-01-01",
      "valid_to": "2026-12-31",
      "bp_code": "C-00001",
      "ItemCode": "FG00317",
      "ItemName": "Urea Fertilizer 46-0-0",
      "unit_price": "980.00",
      "Currency": "PKR"
    }
  ]
}
```

### Error Response (400 Bad Request)
```json
{
  "success": false,
  "error": "doc_entry parameter is required"
}
```

### Error Response (500 Internal Server Error)
```json
{
  "success": false,
  "error": "Connection to HANA failed: ..."
}
```

## Use Cases

### 1. Get All Items in a Policy
**Scenario:** Show all available items and their prices in a specific policy

**Request:**
```bash
GET /api/sap/policy-items/?doc_entry=18
```

**Use Case:** Display product catalog with pricing for sales staff

---

### 2. Get Items in Policy for Specific Customer
**Scenario:** Check if a customer has access to specific items under their assigned policy

**Request:**
```bash
GET /api/sap/policy-items/?doc_entry=18&card_code=C-00001
```

**Use Case:** Validate customer eligibility before creating sales order

---

### 3. Query Different Database
**Scenario:** Get policy items from ORANG company database

**Request:**
```bash
GET /api/sap/policy-items/?doc_entry=18&database=4B-ORANG-app
```

**Use Case:** Multi-company support for sales reps handling different territories

---

### 4. Paginated Results
**Scenario:** Load large policy item lists in chunks

**Request:**
```bash
GET /api/sap/policy-items/?doc_entry=18&page=2&page_size=20
```

**Use Case:** Mobile app with infinite scroll or pagination

## Database Schema

### Tables Queried
- **@PL1**: Policy Header table
  - `DocEntry`: Policy ID (primary key)
  - `Dscription`: Policy name/description
  - `U_ValidFrom`: Policy valid from date
  - `U_ValidTo`: Policy valid to date
  - `U_BpCode`: Business Partner CardCode (customer assignment)

- **@PLR4**: Policy Item Lines table
  - `DocEntry`: Links to @PL1
  - `ItemCode`: Item code
  - `ItemName`: Item description
  - `U_frp`: Unit price (farm rate price)
  - `Currency`: Currency code

## SQL Query (Internal)
```sql
SELECT 
    h."DocEntry" AS policy_doc_entry,
    h."Dscription" AS policy_name,
    h."U_ValidFrom" AS valid_from,
    h."U_ValidTo" AS valid_to,
    h."U_BpCode" AS bp_code,
    l."ItemCode",
    l."ItemName",
    l."U_frp" AS unit_price,
    l."Currency"
FROM "@PL1" h
INNER JOIN "@PLR4" l ON h."DocEntry" = l."DocEntry"
WHERE h."DocEntry" = ?
  AND (h."U_BpCode" = ? OR ? IS NULL)
ORDER BY l."ItemCode"
```

## Integration Examples

### Python (requests)
```python
import requests

url = "http://localhost:8000/api/sap/policy-items/"
headers = {"Authorization": "Token your-auth-token"}
params = {
    "doc_entry": "18",
    "card_code": "C-00001",
    "database": "4B-BIO-app",
    "page_size": 50
}

response = requests.get(url, params=params, headers=headers)
data = response.json()

if data['success']:
    for item in data['data']:
        print(f"{item['ItemCode']}: {item['ItemName']} - {item['unit_price']}")
```

### JavaScript (fetch)
```javascript
const url = new URL('http://localhost:8000/api/sap/policy-items/');
url.searchParams.append('doc_entry', '18');
url.searchParams.append('card_code', 'C-00001');
url.searchParams.append('database', '4B-BIO-app');

fetch(url, {
    headers: {
        'Authorization': 'Token your-auth-token'
    }
})
.then(response => response.json())
.then(data => {
    if (data.success) {
        data.data.forEach(item => {
            console.log(`${item.ItemCode}: ${item.ItemName} - ${item.unit_price}`);
        });
    }
});
```

### cURL
```bash
curl -X GET "http://localhost:8000/api/sap/policy-items/?doc_entry=18&card_code=C-00001&database=4B-BIO-app" \
     -H "Authorization: Token your-auth-token"
```

## Mobile App Integration

### Flutter/Dart Example
```dart
Future<List<PolicyItem>> fetchPolicyItems(String docEntry, {String? cardCode}) async {
  final queryParams = {
    'doc_entry': docEntry,
    if (cardCode != null) 'card_code': cardCode,
    'database': '4B-BIO-app',
    'page_size': '50',
  };
  
  final uri = Uri.parse('$baseUrl/api/sap/policy-items/').replace(
    queryParameters: queryParams,
  );
  
  final response = await http.get(
    uri,
    headers: {'Authorization': 'Token $authToken'},
  );
  
  if (response.statusCode == 200) {
    final data = json.decode(response.body);
    if (data['success']) {
      return (data['data'] as List)
          .map((item) => PolicyItem.fromJson(item))
          .toList();
    }
  }
  throw Exception('Failed to load policy items');
}
```

## Swagger Documentation

Visit `/swagger/` in your Django application to see interactive API documentation with:
- Parameter descriptions
- Request/response examples
- "Try it out" functionality
- Schema definitions

## Testing

Run the test script:
```bash
cd web_portal
python test_policy_items_api.py
```

## Related Endpoints

1. **Policy Customer Balance** (`/api/sap/policy-customer-balance/`)
   - Get balance/outstanding amounts per policy

2. **Item Price** (`/api/sap/item-price/`)
   - Get price for a single item in a policy

3. **Item LOV** (`/api/sap/item-lov/`)
   - Get list of all items (master data)

## Notes

- Results are ordered by `ItemCode` alphabetically
- Dates are returned in ISO format (YYYY-MM-DD)
- Currency codes follow SAP standard (PKR, USD, etc.)
- Policy DocEntry must exist in @PL1 table
- If CardCode is provided but doesn't match policy's U_BpCode, no results will be returned
- Database parameter allows querying different company schemas (BIO vs ORANG)

## Changelog

**2026-01-02**: Initial implementation
- Added endpoint for policy items with customer filtering
- Support for database parameter (multi-schema)
- Pagination support
- Swagger documentation
