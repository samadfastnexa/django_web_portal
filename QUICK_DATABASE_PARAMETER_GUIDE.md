# Multi-Database Query Parameter Quick Reference

## Summary

All SAP API endpoints now support the `?database=` query parameter to specify which company/HANA schema to query.

## Basic Usage

```bash
# Use database parameter with Company name
curl "http://localhost:8000/api/sap/business-partner/?database=4B-BIO_APP"
curl "http://localhost:8000/api/sap/business-partner/?database=4B-ORANG_APP"

# Without parameter (uses session or first active company)
curl "http://localhost:8000/api/sap/business-partner/"
```

## Valid Database Values

The `?database=` parameter accepts actual Company names from the Company model:

| Company Name | Description |
|---|---|
| `4B-BIO_APP` | BIO company schema |
| `4B-ORANG_APP` | ORANG company schema |
| (any other active company) | Add companies to Company model |

## Updated Endpoints

### Business Partner Endpoints

```bash
# List all business partners
GET /api/sap/business-partner/?database=4B-BIO_APP
GET /api/sap/business-partner/?database=4B-ORANG_APP&top=50

# Get specific business partner
GET /api/sap/business-partner/BIC00001/?database=4B-BIO_APP
```

### Policy Endpoints

```bash
# List policies
GET /api/sap/policies/?database=4B-BIO_APP
GET /api/sap/policies/?database=4B-ORANG_APP&active=true

# Sync policies from SAP
POST /api/sap/policies/sync/?database=4B-BIO_APP
```

### Sales vs Achievement

```bash
# Get sales vs achievement data
GET /api/sap/sales-vs-achievement/?database=4B-BIO_APP&start_date=2024-01-01&end_date=2024-12-31
```

## Implementation Details

### Priority Chain

The endpoint resolves the database in this order:

1. **Query Parameter** → `?database=4B-BIO_APP`
2. **Session Value** → `request.session['selected_db']`
3. **First Active Company** → Auto-selected from Company model
4. **Fallback** → `4B-BIO_APP` (if everything else fails)

### How It Works

1. Client sends: `GET /api/sap/business-partner/?database=4B-ORANG_APP`
2. Endpoint calls: `get_hana_schema_from_request(request)`
3. Helper function:
   - Reads `?database=4B-ORANG_APP` from query
   - Validates it against Company model
   - Returns `4B-ORANG_APP`
4. Endpoint maps to SAPClient: `company_db_key='4B-ORANG'`
5. SAPClient connects to the correct HANA schema

## Code Example

### Python Requests

```python
import requests

# Query specific database
response = requests.get(
    'http://localhost:8000/api/sap/business-partner/',
    params={'database': '4B-ORANG_APP', 'top': 50}
)
print(response.json())
```

### JavaScript Fetch

```javascript
// Query specific database
const response = await fetch('/api/sap/business-partner/?database=4B-BIO_APP');
const data = await response.json();
console.log(data);
```

### cURL

```bash
# Using database parameter
curl "http://localhost:8000/api/sap/business-partner/?database=4B-ORANG_APP"

# With authentication header
curl -H "Authorization: Bearer YOUR_TOKEN" \
     "http://localhost:8000/api/sap/business-partner/?database=4B-BIO_APP"

# With multiple parameters
curl "http://localhost:8000/api/sap/policies/?database=4B-ORANG_APP&active=true&page=1"
```

## Error Handling

### Invalid Company Name

```bash
curl "http://localhost:8000/api/sap/business-partner/?database=INVALID_COMPANY"
```

**Response:** Endpoint falls back to first active company or session value

### Case Insensitivity

```bash
# All these work (case-insensitive matching)
?database=4b-bio_app
?database=4B-BIO_APP
?database=4B-bio_APP
```

## Session vs Query Parameter

### Using Session (Legacy)

```python
# Set in session
request.session['selected_db'] = '4B-BIO'
# Save to session
request.session.save()

# API uses this value
GET /api/sap/business-partner/
```

### Using Query Parameter (Recommended)

```bash
# No session needed - parameter takes priority
GET /api/sap/business-partner/?database=4B-ORANG_APP
```

## Adding New Companies

To support additional databases:

1. Add new Company record in Django admin
2. Set `Company_name` to HANA schema name (e.g., `4B-NEW_APP`)
3. Set `is_active = True`
4. Use in API: `?database=4B-NEW_APP`

No code changes needed!

## Swagger Documentation

All endpoints document the `database` parameter:

```
database (query parameter):
Type: String
Required: False
Description: HANA database/schema to query. Use Company name values 
(e.g., 4B-BIO_APP, 4B-ORANG_APP). If not provided, falls back to 
session or first active company.
```

Visit Swagger UI at: `http://localhost:8000/swagger/`

## Troubleshooting

### Q: I'm getting the wrong company data

**A:** Check:
1. Are you using the correct Company_name value?
2. Is the Company record `is_active = True` in database?
3. Is the database parameter being read? Check logs for "Using HANA schema:" entries

### Q: How do I see valid company names?

**A:** In Django shell:
```python
from FieldAdvisoryService.models import Company
Company.objects.filter(is_active=True).values_list('Company_name', flat=True)
```

### Q: Does the query parameter override session?

**A:** Yes! Priority chain is:
1. Query parameter (highest priority)
2. Session value
3. First active company
4. Hardcoded fallback

### Q: Can I still use the old session-based approach?

**A:** Yes! If you don't pass `?database=` parameter, it falls back to session.

## Performance Notes

- First request to a company: ~2-5 seconds (SAP login + fetch)
- Subsequent requests: ~200-500ms (cached in SAPClient)
- Company lookup: Fast (single database query with index)
- No performance penalty for query parameter processing

## Security

- Company names are public (visible in API responses)
- Database parameter doesn't expose sensitive data
- User must still authenticate to use SAP endpoints
- Session isolation maintained per user
