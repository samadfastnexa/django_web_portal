# Policy Project Link API

## Overview
New endpoint to fetch policy-project relationships for a specific Business Partner (customer). Shows which projects are linked to policies assigned to that customer, including project details and validity information.

## Endpoint Details

**URL:** `/api/sap/policy-project-link/`  
**Method:** `GET`  
**Authentication:** Required (same as other SAP endpoints)

## Query Parameters

### Required
- `card_code` (string): Business Partner CardCode
  - Example: `BIC00611`
  - This identifies the customer/vendor in SAP

### Optional
- `database` (string): Database/schema to query
  - Options: `4B-BIO-app`, `4B-ORANG-app`
  - Default: `4B-BIO_APP`
  - Example: `4B-ORANG-app`

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
  "num_pages": 1,
  "count": 2,
  "data": [
    {
      "policy_doc_entry": "18",
      "project_code": "PROJ001",
      "project_name": "Sugarcane Production 2026",
      "project_active": "Y",
      "project_valid_to": "2026-12-31",
      "bp_code": "BIC00611",
      "policy_name": "Standard Fertilizer Policy 2026"
    },
    {
      "policy_doc_entry": "18",
      "project_code": "PROJ002",
      "project_name": "Cotton Cultivation 2026",
      "project_active": "Y",
      "project_valid_to": "2026-12-31",
      "bp_code": "BIC00611",
      "policy_name": "Standard Fertilizer Policy 2026"
    }
  ]
}
```

### Error Response (400 Bad Request)
```json
{
  "success": false,
  "error": "card_code parameter is required"
}
```

### Error Response (500 Internal Server Error)
```json
{
  "success": false,
  "error": "Connection to HANA failed: ..."
}
```

## Database Schema

### Tables Queried
- **@PLR8**: Policy Line Items (customer assignment)
  - `DocEntry`: Links to @PL1
  - `U_bp`: Business Partner CardCode

- **@PL1**: Policy Header
  - `DocEntry`: Policy ID (primary key)
  - `U_proj`: Project Code
  - `Dscription`: Policy description

- **OPRJ**: Projects Master
  - `PrjCode`: Project code
  - `PrjName`: Project name
  - `Active`: Is project active (Y/N)
  - `ValidTo`: Project validity end date

### SQL Query
```sql
SELECT 
    T1."DocEntry" AS policy_doc_entry,
    T1."U_proj" AS project_code,
    T2."PrjName" AS project_name,
    T2."Active" AS project_active,
    T2."ValidTo" AS project_valid_to,
    T0."U_bp" AS bp_code,
    T1."Dscription" AS policy_name
FROM "@PLR8" T0
INNER JOIN "@PL1" T1 ON T0."DocEntry" = T1."DocEntry"
INNER JOIN OPRJ T2 ON T2."PrjCode" = T1."U_proj"
WHERE T0."U_bp" = ?
  AND T2."Active" = 'Y'
  AND T2."ValidTo" >= CURRENT_DATE
ORDER BY T1."DocEntry", T2."PrjCode"
```

## Use Cases

### 1. Customer Project Eligibility Check
**Scenario:** Determine which projects a customer is eligible for based on assigned policies

**Request:**
```bash
GET /api/sap/policy-project-link/?card_code=BIC00611
```

**Response:** Lists all active projects linked to policies for customer BIC00611

**Use Case:** Show customer which projects they can participate in

---

### 2. Policy-Project Mapping for Territory
**Scenario:** Show all project assignments through policies for a territory's customers

**Request:**
```bash
GET /api/sap/policy-project-link/?card_code=C-00001&database=4B-ORANG-app
```

**Use Case:** Territory management and project planning

---

### 3. Validate Project Participation
**Scenario:** Verify customer can participate in a project before creating records

**Request:**
```bash
GET /api/sap/policy-project-link/?card_code=BIC00611&page_size=100
```

**Response:** Get all valid projects and cross-check required project

**Use Case:** Form validation in mobile/web apps

---

### 4. List Active Projects per Customer
**Scenario:** Fetch paginated results of projects with validity dates

**Request:**
```bash
GET /api/sap/policy-project-link/?card_code=BIC00611&page=1&page_size=20
```

**Response:** Paginated projects with validity info

**Use Case:** UI display with pagination

## Integration Examples

### Python (requests)
```python
import requests

url = "http://localhost:8000/api/sap/policy-project-link/"
headers = {"Authorization": "Token your-auth-token"}
params = {
    "card_code": "BIC00611",
    "database": "4B-BIO-app",
    "page_size": 50
}

response = requests.get(url, params=params, headers=headers)
data = response.json()

if data['success']:
    for link in data['data']:
        print(f"Policy {link['policy_doc_entry']}: {link['project_name']}")
```

### JavaScript (fetch)
```javascript
const url = new URL('http://localhost:8000/api/sap/policy-project-link/');
url.searchParams.append('card_code', 'BIC00611');
url.searchParams.append('database', '4B-BIO-app');

fetch(url, {
    headers: {
        'Authorization': 'Token your-auth-token'
    }
})
.then(response => response.json())
.then(data => {
    if (data.success) {
        data.data.forEach(link => {
            console.log(`${link.policy_doc_entry}: ${link.project_name}`);
        });
    }
});
```

### cURL
```bash
curl -X GET "http://localhost:8000/api/sap/policy-project-link/?card_code=BIC00611&database=4B-BIO-app" \
     -H "Authorization: Token your-auth-token"
```

## Mobile App Integration

### Flutter/Dart Example
```dart
Future<List<PolicyProject>> fetchPolicyProjects(String cardCode, {String? database}) async {
  final queryParams = {
    'card_code': cardCode,
    if (database != null) 'database': database,
    'page_size': '50',
  };
  
  final uri = Uri.parse('$baseUrl/api/sap/policy-project-link/').replace(
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
          .map((item) => PolicyProject.fromJson(item))
          .toList();
    }
  }
  throw Exception('Failed to load policy projects');
}

// Usage
List<PolicyProject> projects = await fetchPolicyProjects('BIC00611');
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
python test_policy_project_link_api.py
```

## Related Endpoints

1. **Policy Customer Balance** (`/api/sap/policy-customer-balance/`)
   - Get balance/outstanding amounts per policy

2. **Policy Items** (`/api/sap/policy-items/`)
   - Get items in a specific policy

3. **Projects LOV** (`/api/sap/projects-lov/`)
   - List of all available projects (master data)

## Notes

- Only returns **active projects** (Active = 'Y')
- Only returns projects with **future validity** (ValidTo >= CURRENT_DATE)
- Results are ordered by Policy DocEntry then Project Code
- Multiple projects can be linked to the same policy
- All dates are returned in ISO format (YYYY-MM-DD)
- CardCode must exist in @PLR8 with active, valid projects
- Database parameter allows querying different company schemas

## Changelog

**2026-01-02**: Initial implementation
- Added endpoint for policy-project links
- Support for database parameter (multi-schema)
- Pagination support
- Swagger documentation
