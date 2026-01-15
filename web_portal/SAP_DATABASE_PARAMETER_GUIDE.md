# SAP API Database Parameter Guide

## Overview
All SAP integration endpoints support a `database` query parameter to specify which company database to query.

## Database Parameter

### Usage
Add `?database=<company_key>` to any SAP endpoint URL.

### Available Companies
- `4B-BIO` - Bio Company (default)
- `4B-ORANG` - Orang Company

### How It Works

1. **Global DB Selector** (Admin UI)
   - Top-right dropdown in admin interface
   - Updates session: `request.session['selected_db']`
   - Automatically includes database in all API calls via JavaScript

2. **Query Parameter** (API Calls)
   ```
   /sap/policy-customer-balance/ORC00002/?database=4B-ORANG
   /api/customer_details/?card_code=ORC00002&database=4B-ORANG
   /sap/policy-items-lov/?doc_entry=123&database=4B-BIO
   ```

3. **Backend Processing**
   - Reads from query parameter OR session
   - Maps to HANA schema:
     - `4B-BIO` → `4B-BIO_APP` schema
     - `4B-ORANG` → `4B-ORANG_APP` schema
   - Executes `SET SCHEMA "<schema_name>"`

## Endpoints with Database Support

### SAP Integration APIs (`/sap/`)
- `/sap/business-partner/` - List all business partners
- `/sap/business-partner/<card_code>/` - Get specific BP
- `/sap/policy-customer-balance/` - All policy balances
- `/sap/policy-customer-balance/<card_code>/` - Customer policy balance
- `/sap/warehouse-for-item/` - Warehouses for item
- `/sap/customer-lov/` - Customer list of values
- `/sap/item-lov/` - Item master list
- `/sap/item-price/` - Item price by policy
- `/sap/policy-items-lov/` - Items in policy
- `/sap/policy-items/` - Items filtered by customer
- `/sap/policy-project-link/` - Policy project relationships
- `/sap/projects-lov/` - Project list
- `/sap/crop-lov/` - Crop master list
- `/sap/sales-orders/` - Sales orders
- `/sap/contact-persons/` - Contact persons
- `/sap/customer-addresses/` - Customer addresses
- `/sap/project-balance/` - Project balances
- `/sap/territories-full/` - Territory data
- `/sap/cwl-full/` - CWL data
- `/sap/sales-vs-achievement-geo-inv/` - Sales achievement (geo/inv)
- `/sap/sales-vs-achievement-territory/` - Sales achievement (territory)

### Admin Helper APIs (`/api/`)
- `/api/customer_details/` - Customer details (CardName, ContactPerson, etc.)
- `/api/child_customers/` - Child customers (FatherCard hierarchy)
- `/api/warehouse_for_item/` - Warehouses for item code
- `/api/customer_address/` - Customer billing address
- `/api/policy_link/` - Policy link by project
- `/api/discounts/` - Discounts (U_AD, U_EXD)
- `/api/project_balance/` - Project balance

## Implementation Examples

### JavaScript (Admin Forms)
```javascript
function getSelectedDB(){
  var sel = document.querySelector('#db-selector');
  return sel ? sel.value : '';
}

function fetchCustomerDetails(cardCode){
  var db = getSelectedDB();
  var url = '/api/customer_details/?card_code=' + encodeURIComponent(cardCode);
  if(db){ url += '&database=' + encodeURIComponent(db); }
  fetch(url, { credentials: 'same-origin' })
    .then(r => r.json())
    .then(data => console.log(data));
}
```

### Python (Backend)
```python
@require_http_methods(["GET"])
def api_customer_details(request):
    card_code = request.GET.get('card_code')
    
    # Database comes from session or query param
    selected_db = request.session.get('selected_db') if hasattr(request, 'session') else None
    db_param = request.GET.get('database')
    if db_param:
        selected_db = db_param
    
    # Connect to HANA with selected DB
    db = get_hana_connection(request, selected_db_key=selected_db)
    
    # Verify schema
    cursor = db.cursor()
    cursor.execute('SELECT CURRENT_SCHEMA FROM DUMMY')
    current_schema = cursor.fetchone()[0]
    logger.info(f"Connected to schema: {current_schema}")
    
    # Execute queries...
```

## Swagger Documentation

All SAP endpoints include database parameter in Swagger:

```python
@swagger_auto_schema(
    tags=['SAP'], 
    method='get',
    operation_summary="Get Business Partner by CardCode",
    operation_description="Get specific Business Partner by CardCode",
    manual_parameters=[
        openapi.Parameter(
            'database', 
            openapi.IN_QUERY, 
            description="Company database to query", 
            type=openapi.TYPE_STRING, 
            enum=['4B-BIO', '4B-ORANG'], 
            required=False
        )
    ],
    responses={200: openapi.Response(description="OK"), 500: openapi.Response(description="Server Error")}
)
@api_view(['GET'])
def get_business_partner_detail(request, card_code):
    # Implementation...
```

## Admin UI Integration

### Sales Order Form
- **Database Selector Badge** at top shows current company
- **Customer dropdown** loads from selected DB
- **Policy dropdown** loads customer policies from selected DB
- **Item dropdown** loads policy items from selected DB
- **Price auto-fill** fetches from selected DB

### How to Switch Databases
1. Use global DB selector (top-right): Select `4B-ORANG` or `4B-BIO`
2. Page reloads with new database selection
3. All subsequent API calls include the selected database
4. Form LOVs (List of Values) refresh with new database data

## Logging
Backend logs show which schema is being used:
```
Selected DB from session: 4B-ORANG
Connected to HANA schema: 4B-ORANG_APP
Fetching details for ORC00002
```

## Testing
```bash
# Test with BIO database (default)
curl http://localhost:8000/api/customer_details/?card_code=BIC01563

# Test with ORANG database
curl http://localhost:8000/api/customer_details/?card_code=ORC00002&database=4B-ORANG

# Test policy balance
curl http://localhost:8000/sap/policy-customer-balance/ORC00002/?database=4B-ORANG
```

## Summary
✅ **All SAP and Admin APIs support the `database` parameter**
✅ **Admin UI automatically includes database in all requests**
✅ **Backend respects session and query parameter**
✅ **Swagger documents database dropdown for all endpoints**
✅ **Logging confirms which schema is used**
