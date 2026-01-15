# Multi-Database Support Implementation

## Overview

This document describes the implementation of multi-database (HANA schema) support in the SAP integration API. The system allows API clients to specify which company database to query using the `?database=` query parameter, with fallback to session selection or the first active company from the database.

## Problem Statement

Previously, all SAP endpoints only read the database from the session (`request.session['selected_db']`) and completely ignored the `?database=` query parameter. This prevented API clients from querying different company schemas dynamically.

**Error Example:**
```
GET /api/sap/business-partner/?database=4B-ORANG
Response: -5027 error (wrong company context)
Reason: Endpoint ignored ?database parameter and used session value instead
```

## Solution Architecture

### 1. Company Model Integration

The `Company` model in `FieldAdvisoryService/models.py` contains company names that match HANA schema names:

```python
# Company model has Company_name field containing HANA schema names:
# Company 1: Company_name = "4B-BIO_APP"
# Company 2: Company_name = "4B-ORANG_APP"
```

**Key Design Decision:** 
- Do NOT add new fields to the Company model
- Use existing `Company_name` field directly as HANA schema names
- This field already contains the correct values (e.g., "4B-BIO_APP", "4B-ORANG_APP")

### 2. Helper Functions

Two new helper functions were added to `sap_integration/views.py`:

#### `get_hana_schema_from_request(request)`

**Purpose:** Resolve HANA schema name from multiple sources with fallback chain

**Resolution Priority:**
1. Query parameter: `?database=4B-BIO_APP`
2. Session value: `request.session['selected_db']`
3. First active company: `Company.objects.filter(is_active=True).first()`
4. Ultimate fallback: `'4B-BIO_APP'`

**Key Features:**
- Case-insensitive Company name matching
- Returns exact Company_name value (e.g., "4B-BIO_APP")
- Graceful fallback for missing/invalid companies
- Logging for debugging database selection

**Code:**
```python
def get_hana_schema_from_request(request):
    """
    Get HANA schema from database parameter using actual Company names.
    
    Priority:
    1. Query parameter (?database=4B-BIO_APP)
    2. Session value (request.session['selected_db'])
    3. Default from first active company
    
    Returns: HANA schema name (company name - e.g., '4B-BIO_APP', '4B-ORANG_APP')
    """
    # Try query parameter first
    db_param = request.GET.get('database', '').strip()
    if db_param:
        try:
            company = Company.objects.get(Company_name=db_param, is_active=True)
            return company.Company_name
        except Company.DoesNotExist:
            pass
        
        try:
            company = Company.objects.get(Company_name__iexact=db_param, is_active=True)
            return company.Company_name
        except Company.DoesNotExist:
            pass
    
    # Try session next
    session_db = request.session.get('selected_db', '').strip()
    if session_db:
        try:
            company = Company.objects.get(Company_name=session_db, is_active=True)
            return company.Company_name
        except Company.DoesNotExist:
            pass
    
    # Fall back to first active company
    try:
        company = Company.objects.filter(is_active=True).first()
        if company:
            return company.Company_name
    except Exception:
        pass
    
    # Ultimate fallback
    return '4B-BIO_APP'
```

#### `get_valid_company_schemas()`

**Purpose:** Get list of valid HANA schemas for API documentation

**Returns:** List of active company names for Swagger enum values

**Code:**
```python
def get_valid_company_schemas():
    """
    Get list of valid HANA schema names from active companies.
    Used for Swagger documentation enum values.
    
    Returns: List of company names (e.g., ['4B-BIO_APP', '4B-ORANG_APP'])
    """
    try:
        companies = Company.objects.filter(is_active=True).values_list('Company_name', flat=True)
        schemas = list(companies)
        if not schemas:
            schemas = ['4B-BIO_APP', '4B-ORANG_APP']
        return schemas
    except Exception:
        return ['4B-BIO_APP', '4B-ORANG_APP']
```

### 3. SAPClient Mapping

The helper returns Company names (e.g., "4B-BIO_APP"), but SAPClient expects short company_db_key values (e.g., "4B-BIO"). Each endpoint implements mapping logic:

```python
hana_schema = get_hana_schema_from_request(request)  # Returns "4B-BIO_APP"

# Map to SAPClient company_db_key
if 'BIO' in hana_schema.upper():
    company_db_key = '4B-BIO'
elif 'ORANG' in hana_schema.upper():
    company_db_key = '4B-ORANG'
else:
    company_db_key = '4B-BIO'  # Default fallback

sap_client = SAPClient(company_db_key=company_db_key)
```

## Updated Endpoints

The following endpoints now support the `?database=` parameter:

### GET /api/sap/business-partner/ - List All Business Partners

**Changes:**
- Added `database` query parameter to Swagger decorator
- Updated function to use `get_hana_schema_from_request()`
- Maintains backward compatibility with session-based selection

**Usage:**
```bash
# Using database parameter
curl "http://localhost:8000/api/sap/business-partner/?database=4B-ORANG_APP"

# Using session (fallback)
curl "http://localhost:8000/api/sap/business-partner/"

# With additional parameters
curl "http://localhost:8000/api/sap/business-partner/?database=4B-BIO_APP&top=50"
```

### GET /api/sap/business-partner/{card_code}/ - Get Business Partner Details

**Changes:**
- Added `database` query parameter to Swagger decorator
- Uses same `get_hana_schema_from_request()` helper

**Usage:**
```bash
curl "http://localhost:8000/api/sap/business-partner/BIC00001/?database=4B-ORANG_APP"
```

### GET /api/sap/policies/ - List Policies

**Changes:**
- Added `database` query parameter to Swagger decorator
- Updated function to use `get_hana_schema_from_request()`
- Maps HANA schema to SAPClient company_db_key

**Usage:**
```bash
curl "http://localhost:8000/api/sap/policies/?database=4B-BIO_APP&active=true"
```

### POST /api/sap/policies/sync/ - Sync Policies from SAP

**Changes:**
- Added `database` query parameter to Swagger decorator
- Updated function to use `get_hana_schema_from_request()`

**Usage:**
```bash
curl -X POST "http://localhost:8000/api/sap/policies/sync/?database=4B-ORANG_APP"
```

### GET /api/sap/sales-vs-achievement/ - Sales vs Achievement Data

**Changes:**
- Updated `database` parameter description
- Removed hardcoded enum values (was: ['4B-BIO-app', '4B-ORANG-app'])
- Now documents to use Company name values

**Usage:**
```bash
curl "http://localhost:8000/api/sap/sales-vs-achievement/?database=4B-BIO_APP&start_date=2024-01-01"
```

## Backward Compatibility

All changes maintain full backward compatibility:

1. **Session-based selection still works:** If no `?database=` parameter, endpoint uses session value
2. **Default fallback:** If neither parameter nor session available, uses first active company
3. **Existing API clients:** No breaking changes to existing code using session selection

## Swagger Documentation

All updated endpoints now document the `database` parameter in Swagger:

```
database (query parameter):
- Type: String
- Required: False
- Description: HANA database/schema to query. Use Company name values 
  (e.g., 4B-BIO_APP, 4B-ORANG_APP). If not provided, falls back to 
  session or first active company.
```

## Error Handling

The implementation includes robust error handling:

1. **Invalid Company Name:** Falls back to session or first active company
2. **Case Sensitivity:** Supports case-insensitive company name matching
3. **Missing Company:** Returns ultimate fallback ("4B-BIO_APP")
4. **Database Errors:** Returns fallback instead of crashing

## Testing

### Test Case 1: Query Parameter Priority
```bash
# Request with database parameter
GET /api/sap/business-partner/?database=4B-ORANG_APP
# Result: Uses 4B-ORANG_APP (from parameter)
```

### Test Case 2: Session Fallback
```bash
# Request without parameter (session has 4B-BIO)
GET /api/sap/business-partner/
# Result: Uses 4B-BIO (from session)
```

### Test Case 3: Company Model Fallback
```bash
# Request without parameter or session (Company model has active companies)
GET /api/sap/business-partner/
# Result: Uses first active company's name
```

### Test Case 4: Case Insensitive Matching
```bash
# Request with lowercase company name
GET /api/sap/business-partner/?database=4b-orang_app
# Result: Matches and uses 4B-ORANG_APP (case-insensitive match)
```

## Database Queries

The implementation executes these database queries:

1. **On each API request with database parameter:**
   ```python
   Company.objects.get(Company_name=db_param, is_active=True)
   ```

2. **Fallback if above fails:**
   ```python
   Company.objects.get(Company_name__iexact=db_param, is_active=True)
   ```

3. **Ultimate fallback:**
   ```python
   Company.objects.filter(is_active=True).first()
   ```

## Configuration

No configuration changes required. The system automatically:

1. Detects active companies from the Company model
2. Uses their names as valid HANA schema values
3. Accepts any active company name via `?database=` parameter

## Future Enhancements

Potential improvements:

1. **Caching:** Cache active company list to reduce database queries
2. **API Endpoint:** Create `/api/companies/` endpoint to list valid values
3. **Validation:** Add schema validation before passing to SAPClient
4. **Metrics:** Add performance tracking for different company schemas
5. **Rate Limiting:** Implement per-company rate limiting

## Migration Path

If you have existing code:

**Before:**
```python
sap_client = SAPClient(company_db_key='4B-BIO')
```

**After (with query parameter support):**
```python
# Clients can now use:
GET /api/sap/business-partner/?database=4B-BIO_APP
# And the endpoint automatically handles the mapping
```

## Troubleshooting

### Issue: "Company not found" error

**Cause:** Invalid company name in database parameter

**Solution:** Check Company model for valid names:
```python
Company.objects.filter(is_active=True).values_list('Company_name', flat=True)
```

### Issue: Wrong company data returned

**Cause:** Query parameter case mismatch or session overriding

**Solution:** 
- Use exact Company name (e.g., "4B-BIO_APP", not "4B-BIO")
- Clear browser session cookies
- Verify Company.is_active = True in database

### Issue: Endpoint returning old company data

**Cause:** Database parameter not recognized

**Solution:** Check logs for "Using HANA schema:" entries to confirm parameter is being read
