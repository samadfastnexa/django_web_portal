# Swagger Database Parameter Update

## Summary
All SAP integration endpoints in `sap_integration/views.py` have been updated to include the `database` parameter in their Swagger documentation. This enables API consumers to select between different company databases (4B-BIO or 4B-ORANG) directly from the Swagger UI.

## Changes Made

### 1. Standardized Database Parameter Format
- **Parameter Name**: `database`
- **Location**: Query string (`IN_QUERY`)
- **Type**: String
- **Enum Values**: `['4B-BIO', '4B-ORANG']`
- **Required**: False (optional)
- **Description**: "Company database (4B-BIO or 4B-ORANG)"

### 2. Updated Endpoints

All SAP integration endpoints now include the database parameter:

#### Business Partner Endpoints
- `get_business_partners_list` - List all business partners
- `get_business_partner_detail` - Get specific business partner by CardCode

#### Policy Endpoints
- `list_policies` - List all policies from SAP Projects
- `list_db_policies` - List policies stored in database
- `sync_policies` - Sync policies from SAP to database
- `policy_customer_balance_list` - List policy customer balances
- `policy_customer_balance_detail` - Get policy customer balance by CardCode
- `policy_items_api` - Get policy items
- `policy_items_for_customer_api` - Get policy items for specific customer
- `policy_project_link_api` - Policy project linking

#### Sales & Analytics Endpoints
- `sales_vs_achievement_api` - Sales vs achievement data
- `sales_vs_achievement_geo_inv_api` - Sales vs achievement with geo inventory
- `sales_vs_achievement_territory_api` - Sales vs achievement by territory
- `sales_vs_achievement_by_emp_api` - Sales vs achievement by employee
- `territory_summary_api` - Territory summary data
- `sales_orders_api` - List sales orders

#### Catalog & Items Endpoints
- `products_catalog_api` - Products catalog with images
- `item_lov_api` - Item list of values
- `item_price_api` - Item price by policy
- `warehouse_for_item_api` - Warehouse list for item

#### Customer & Contact Endpoints
- `customer_lov_api` - Customer list of values
- `customer_addresses_api` - Customer addresses
- `contact_persons_api` - Contact persons

#### Project & Crop Endpoints
- `projects_lov_api` - Projects list of values
- `project_balance_api` - Project balances
- `crop_lov_api` - Crop list of values

#### Territory & CWL Endpoints
- `territories_full_api` - Full territories list
- `cwl_full_api` - CWL data

#### Health & Diagnostic Endpoints
- `hana_health_api` - HANA health check
- `hana_count_tables_api` - Count HANA tables
- `select_oitm_api` - Sample from OITM table

### 3. Enum Value Standardization
All inconsistent enum values were standardized:
- **Before**: `['4B-BIO-app', '4B-ORANG-app']`
- **After**: `['4B-BIO', '4B-ORANG']`

This ensures consistency across all endpoints and matches the format used in the admin UI and JavaScript code.

### 4. Default Value Update
Default values were also standardized:
- **Before**: `default='4B-BIO-app'`
- **After**: `default='4B-BIO'`

## Swagger UI Experience

When accessing the Swagger documentation (typically at `/swagger/`), users will now see:

1. **Database Parameter Dropdown**: All SAP endpoints will display a dropdown selector for the `database` parameter
2. **Enum Options**: The dropdown will show two options:
   - `4B-BIO` (BioFertilizer Company)
   - `4B-ORANG` (Orange Company)
3. **Try It Out**: Users can select a database before executing API calls

## Example Swagger Decorator

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
            description="Company database (4B-BIO or 4B-ORANG)",
            type=openapi.TYPE_STRING,
            enum=['4B-BIO', '4B-ORANG'],
            required=False
        ),
        # ... other parameters
    ],
    responses={200: openapi.Response(description="OK"), 500: openapi.Response(description="Server Error")}
)
@api_view(['GET'])
def get_business_partner_detail(request, card_code):
    # Implementation...
```

## Testing

To verify the changes:

1. Start the Django development server
2. Navigate to `/swagger/` in your browser
3. Locate any SAP endpoint (tagged with "SAP")
4. Expand the endpoint to view parameters
5. Confirm the `database` parameter appears with a dropdown showing `4B-BIO` and `4B-ORANG`

## Backend Implementation

All endpoints already support the database parameter in their implementation:

```python
# Example: Reading database parameter
db_param = (request.GET.get('database') or '').strip()
if db_param:
    norm = db_param.strip().upper().replace('-APP', '_APP')
    if '4B-BIO' in norm:
        cfg['schema'] = '4B-BIO_APP'
    elif '4B-ORANG' in norm:
        cfg['schema'] = '4B-ORANG_APP'
```

The backend automatically maps:
- `4B-BIO` → `4B-BIO_APP` schema
- `4B-ORANG` → `4B-ORANG_APP` schema

## Related Documentation

- [SAP_DATABASE_PARAMETER_GUIDE.md](SAP_DATABASE_PARAMETER_GUIDE.md) - Comprehensive guide on database parameter usage
- [POLICY_API_QUICK_REFERENCE.md](POLICY_API_QUICK_REFERENCE.md) - Policy API reference
- [SALES_ORDER_API_MOBILE_GUIDE.md](SALES_ORDER_API_MOBILE_GUIDE.md) - Sales order API guide

## Date Updated
January 2025
