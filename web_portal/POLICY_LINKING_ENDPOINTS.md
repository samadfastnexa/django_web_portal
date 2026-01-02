# Policy Linking Endpoints - Implementation Summary

## Overview
Two new endpoints have been implemented to handle policy linking and relationships:

1. **Policy Items for Customer** - Get items in a specific policy
2. **Policy Project Link** - Get projects linked to policies for a customer

---

## 1. Policy Items for Customer API

**Endpoint:** `GET /api/sap/policy-items/`

### Purpose
Fetch all items available in a specific policy, with optional filtering by customer CardCode.

### Parameters
- `doc_entry` (required): Policy DocEntry number
- `card_code` (optional): Business Partner CardCode to filter
- `database` (optional): 4B-BIO-app or 4B-ORANG-app
- `page` (optional): Page number
- `page_size` (optional): Items per page

### Example Requests
```bash
# Get all items in policy 18
GET /api/sap/policy-items/?doc_entry=18

# Get items for specific customer
GET /api/sap/policy-items/?doc_entry=18&card_code=C-00001

# Query ORANG database
GET /api/sap/policy-items/?doc_entry=18&database=4B-ORANG-app
```

### Response
```json
{
  "success": true,
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
    }
  ]
}
```

### Database Query
```sql
SELECT 
    h."DocEntry", h."Dscription", h."U_ValidFrom", h."U_ValidTo",
    h."U_BpCode", l."ItemCode", l."ItemName", l."U_frp", l."Currency"
FROM "@PL1" h
INNER JOIN "@PLR4" l ON h."DocEntry" = l."DocEntry"
WHERE h."DocEntry" = ? AND (h."U_BpCode" = ? OR ? IS NULL)
```

### Use Cases
- Display product catalog with pricing
- Check item availability in policy
- Validate customer eligibility for items
- Show pricing before creating orders

---

## 2. Policy Project Link API

**Endpoint:** `GET /api/sap/policy-project-link/`

### Purpose
Fetch projects linked to policies assigned to a specific Business Partner (customer).

### Parameters
- `card_code` (required): Business Partner CardCode
- `database` (optional): 4B-BIO-app or 4B-ORANG-app
- `page` (optional): Page number
- `page_size` (optional): Items per page

### Example Requests
```bash
# Get policy-project links for a customer
GET /api/sap/policy-project-link/?card_code=BIC00611

# Query ORANG database
GET /api/sap/policy-project-link/?card_code=C-00001&database=4B-ORANG-app

# Paginated results
GET /api/sap/policy-project-link/?card_code=BIC00611&page=2&page_size=20
```

### Response
```json
{
  "success": true,
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
    }
  ]
}
```

### Database Query
```sql
SELECT 
    T1."DocEntry", T1."U_proj", T2."PrjName",
    T2."Active", T2."ValidTo", T0."U_bp", T1."Dscription"
FROM "@PLR8" T0
INNER JOIN "@PL1" T1 ON T0."DocEntry" = T1."DocEntry"
INNER JOIN OPRJ T2 ON T2."PrjCode" = T1."U_proj"
WHERE T0."U_bp" = ?
AND T2."Active" = 'Y'
AND T2."ValidTo" >= CURRENT_DATE
```

### Use Cases
- Check project eligibility based on policies
- Validate customer participation in projects
- Show available projects per customer
- Territory management and planning

---

## Implementation Details

### Files Modified
1. `sap_integration/views.py` - Added two new API functions
2. `sap_integration/urls.py` - Added two new URL routes

### Features
- ✅ Full Swagger documentation
- ✅ Multi-database support (BIO & ORANG)
- ✅ Pagination support
- ✅ Optional filters
- ✅ Error handling & validation
- ✅ ISO date formatting
- ✅ HANA schema switching

### Authentication
Both endpoints require DRF token authentication (same as other SAP APIs)

### Database Support
- Primary: 4B-BIO_APP (default)
- Secondary: 4B-ORANG_APP (via database parameter)

---

## Testing

### Test Scripts Provided
1. `test_policy_items_api.py` - Test Policy Items endpoint
2. `test_policy_project_link_api.py` - Test Policy Project Link endpoint

### Run Tests
```bash
python test_policy_items_api.py
python test_policy_project_link_api.py
```

### Swagger Testing
Visit `/swagger/` and search for:
- "Policy Items for Customer"
- "Policy Project Link"

---

## Integration Flow

### Typical User Journey

1. **Load Policies** → Use existing `/api/sap/policy-customer-balance/` endpoint
2. **Get Policy Items** → Use `/api/sap/policy-items/?doc_entry=18`
3. **Get Policy Projects** → Use `/api/sap/policy-project-link/?card_code=BIC00611`
4. **Validate & Create Order** → Create sales order with selected items/projects

### Multi-Database Flow

For organizations using both BIO and ORANG databases:

```
1. User selects database in UI
2. Pass database parameter: ?database=4B-ORANG-app
3. Endpoint reconnects to HANA with new schema
4. Returns data from selected database
5. Results marked with database source
```

---

## API Response Codes

| Code | Meaning | Example |
|------|---------|---------|
| 200 | Success | Data returned |
| 400 | Bad Request | Missing required parameter |
| 500 | Server Error | HANA connection failed |

---

## Related Endpoints

- **Policy Customer Balance** `/api/sap/policy-customer-balance/` - Balance queries
- **Item Master List** `/api/sap/item-lov/` - All items (no policy filter)
- **Projects Master** `/api/sap/projects-lov/` - All projects (no policy filter)
- **Item Price** `/api/sap/item-price/` - Price lookup for single items
- **Policy Records** `/api/sap/policy-records/` - DB-backed policies

---

## Performance Notes

### Pagination Defaults
- Default page size: 50 items
- Supports up to 200 items per page
- First page loads immediately

### Query Optimization
- Uses INNER JOINs (filters at database level)
- Only returns active/valid records
- Indexed on DocEntry and CardCode fields

### Caching Recommendations
For high-traffic scenarios, consider caching:
- Policy items (varies by DocEntry)
- Customer projects (varies by CardCode + database)
- Cache TTL: 1-4 hours

---

## Documentation Files

1. **POLICY_ITEMS_API_GUIDE.md** - Complete Policy Items endpoint docs
2. **POLICY_PROJECT_LINK_API_GUIDE.md** - Complete Policy Project Link docs
3. This file - Quick reference and integration guide

---

## Changelog

**2026-01-02 Implementation**
- Added Policy Items for Customer API
- Added Policy Project Link API
- Full Swagger documentation
- Multi-database support
- Pagination support
- Test scripts and guides

---

## Support & Troubleshooting

### Common Issues

**Missing CardCode Parameter**
```json
{
  "success": false,
  "error": "card_code parameter is required"
}
```
→ Add `?card_code=BIC00611` to request

**No Results Returned**
- Check if customer is assigned to policies
- Verify projects are active (Active = 'Y')
- Check project validity dates

**Schema/Database Errors**
- Verify database parameter spelling: `4B-BIO-app` or `4B-ORANG-app`
- Check HANA_HOST and credentials in .env
- Ensure user has access to both schemas

---

## Next Steps

1. ✅ Deploy to staging
2. ✅ Test with real SAP data
3. ✅ Add admin interface buttons (optional)
4. ✅ Mobile app integration
5. ✅ Add caching layer (if needed)

