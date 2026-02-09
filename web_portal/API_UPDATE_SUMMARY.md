# API Update Summary - Product Documents with Swagger

## ✅ Changes Completed

### 1. **Updated Products Catalog API** (`/api/sap/products-catalog/`)

#### New Response Fields Added:
```json
{
  "ItemCode": "FG00292",
  "ItemName": "Gabru-DF 80 WG-2KG",
  "Product_Urdu_Name": "Gabru",
  "Product_Urdu_Ext": "docx",
  
  // EXISTING FIELDS:
  "product_image_url": "/media/product_images/4B-ORANG/Gabru.png",
  "product_description_urdu_url": "/media/product_images/4B-ORANG/Gabru.docx",
  
  // NEW FIELDS:
  "has_document": true,
  "document_detail_url": "/api/sap/products/FG00292/",
  "document_detail_page_url": "http://localhost:8000/api/sap/products/FG00292/?database=4B-ORANG_APP"
}
```

### 2. **Swagger Documentation Updated**

#### New Tag Created: `SAP - Products`
All product-related endpoints are now grouped under this tag in Swagger UI.

#### Updated Endpoints:

**1. GET `/api/sap/products-catalog/`**
- **Tag**: `SAP - Products`
- **Description**: Enhanced with document link information
- **New Features**:
  - Returns clickable document URLs
  - Boolean flag `has_document` for quick filtering
  - Full page URLs for easy navigation
- **Query Parameters**:
  - `database`: Database name (4B-BIO_APP, 4B-ORANG_APP)
  - `search`: Search by ItemCode, ItemName, etc.
  - `item_group`: Filter by category
  - `page`, `page_size`: Pagination

**2. GET `/api/sap/product-document/<item_code>/`** (NEW)
- **Tag**: `SAP - Products`
- **Description**: View formatted product document
- **Features**:
  - Parses Word documents on-the-fly
  - Preserves all formatting (headings, colors, tables, images)
  - RTL support for Urdu text
- **Query Parameters**:
  - `database`: Database name (required)
  - `method`: Parser method (`mammoth` or `custom`)
- **Response**: HTML page with formatted content

### 3. **URL Routes Added**

#### Web Pages:
- `/api/sap/products/` - Product catalog list (browse products)
- `/api/sap/products/<item_code>/` - Document detail page (view formatted doc)

#### API Endpoints (for Swagger):
- `/api/sap/products-catalog/` - Products list API (existing, enhanced)
- `/api/sap/product-document/<item_code>/` - Document detail API (new)

### 4. **Code Changes**

#### File: `sap_integration/views.py`
- ✅ Updated `products_catalog_api()` Swagger documentation
- ✅ Added document link fields to API response
- ✅ Created `product_document_api()` endpoint for Swagger

#### File: `sap_integration/urls.py`
- ✅ Added `product_document_api` import
- ✅ Added route: `product-document/<item_code>/`

## 📊 API Response Behavior

### Products WITH Documents:
```json
{
  "has_document": true,
  "document_detail_url": "/api/sap/products/FG00292/",
  "document_detail_page_url": "http://localhost:8000/api/sap/products/FG00292/?database=4B-ORANG_APP"
}
```
**User Action**: Click on `document_detail_page_url` to view formatted document

### Products WITHOUT Documents:
```json
{
  "has_document": false,
  "document_detail_url": null,
  "document_detail_page_url": null
}
```
**User Action**: No document available, links are null

## 🎯 Use Cases

### For Mobile/Web Apps:
```javascript
// Fetch products
const response = await fetch('/api/sap/products-catalog/?database=4B-ORANG_APP');
const data = await response.json();

// Display products
data.data.forEach(product => {
    if (product.has_document) {
        // Show "View Details" button
        console.log(`View document: ${product.document_detail_page_url}`);
    } else {
        // Show "No document available" message
        console.log('Document not available');
    }
});
```

### For Swagger Testing:
1. Open: `http://localhost:8000/swagger/`
2. Look for: **SAP - Products** section
3. Try: `GET /api/sap/products-catalog/`
4. Click on any `document_detail_page_url` in response
5. View formatted document with all styling

## 🔍 Testing the Changes

### 1. Start Server:
```bash
python manage.py runserver
```

### 2. Test Products API:
```bash
# Get products with document links
curl "http://localhost:8000/api/sap/products-catalog/?database=4B-ORANG_APP&page_size=5"
```

### 3. Check Swagger:
```
http://localhost:8000/swagger/#/SAP%20-%20Products
```

### 4. Browse Products (Web UI):
```
http://localhost:8000/api/sap/products/?database=4B-ORANG_APP
```

## 📝 Swagger Documentation Details

### Products Catalog API Documentation:
```
GET /api/sap/products-catalog/

Products catalog with images and document links based on database.

Features:
- Product images from media/product_images/{database}/
- Document description links (for products with Word documents)
- Search and filter by category
- Pagination support

Each product includes:
- product_image_url: URL to product image
- product_description_urdu_url: URL to download Word document
- document_detail_url: URL to view formatted document (if available)
- document_detail_page_url: Full URL to document detail page
```

### Product Document API Documentation:
```
GET /api/sap/product-document/{item_code}/

Get detailed product document with formatted Word content.

This endpoint parses Word documents on-the-fly and displays them with full formatting:
- Headings (H1, H2, H3, H4)
- Text colors and fonts
- Tables with cell formatting
- Embedded images
- RTL (Right-to-Left) support for Urdu text

The document is parsed fresh on each request, so changes to the .docx file 
are reflected immediately.

Parser Methods:
- mammoth (default): Automatic conversion with smart formatting
- custom: Detailed control over all formatting elements
```

## ✨ Benefits

1. **Discoverability**: Products with documents are clearly flagged
2. **Direct Links**: One-click access to formatted documents
3. **API-First**: Perfect for mobile/web apps integration
4. **Swagger Ready**: Full API documentation available
5. **User Friendly**: Clear indication of document availability

## 🎉 Summary

✅ **Swagger Documentation**: Fully updated with new "SAP - Products" category  
✅ **API Response**: Enhanced with document link fields  
✅ **Clickable URLs**: Direct links to view formatted documents  
✅ **Boolean Flag**: `has_document` for easy filtering  
✅ **Full Integration**: Works seamlessly with existing catalog API  

**Ready for production use!**

---

# Collection Analytics API Enhancement - User & Employee Tracking + Period Filters

## ✅ Changes Completed (February 3, 2026)

### 1. **Updated Collection Analytics API** (`/api/analytics/collection/`)

#### New Query Parameters Added:
- **`user_id`**: Portal User ID (automatically fetches employee_code from user's sales_profile)
- **`period`**: Quick date filter - `today`, `monthly`, or `yearly` (auto-calculates date ranges)

#### New Response Fields:
```json
{
  "success": true,
  "user_id": 123,              // NEW: Portal user ID
  "employee_id": "EMP001",     // NEW: Employee code from sales_profile
  "count": 10,
  "data": [...],
  "pagination": {...},
  "filters": {...},
  "totals": {...}
}
```

### 2. **Period Filter Feature** ⭐ NEW

Quick date filters that automatically calculate date ranges based on current date (February 3, 2026):

#### Available Period Options:
1. **`period=today`** - Current day only
   - Calculates: `start_date=2026-02-03`, `end_date=2026-02-03`
   
2. **`period=monthly`** - Current month to date
   - Calculates: `start_date=2026-02-01`, `end_date=2026-02-03`
   
3. **`period=yearly`** - Current year to date
   - Calculates: `start_date=2026-01-01`, `end_date=2026-02-03`

#### Priority Logic:
- `period` parameter **overrides** `start_date` and `end_date` if provided
- If no `period`, uses custom `start_date` and `end_date`
- If neither provided, uses default date range

### 3. **Parameter Priority Logic**

**Employee Filter Priority:**
1. **`emp_id`** (SAP Employee ID) - Direct SAP employee ID (highest priority)
2. **`user_id`** (Portal User ID) - Fetches employee_code from user's sales_profile
3. **Neither provided** - Returns data for authenticated user or all employees

**Date Filter Priority:**
1. **`period`** - Quick filter (highest priority, overrides custom dates)
2. **`start_date` & `end_date`** - Custom date range
3. **Neither provided** - Uses default date range

### 4. **Usage Examples**

#### Quick Period Filters:
```bash
# Today's collection data
GET /api/analytics/collection/?database=4B-BIO&period=today

# This month's data (Feb 1 - Feb 3, 2026)
GET /api/analytics/collection/?database=4B-BIO&period=monthly

# Year-to-date (Jan 1 - Feb 3, 2026)
GET /api/analytics/collection/?database=4B-BIO&period=yearly
```

#### User + Period Combinations:
```bash
# User 123's monthly performance
GET /api/analytics/collection/?database=4B-BIO&user_id=123&period=monthly

# Employee 456's today data
GET /api/analytics/collection/?database=4B-BIO&emp_id=456&period=today

# User's yearly data in millions
GET /api/analytics/collection/?database=4B-BIO&user_id=789&period=yearly&in_millions=true
```

#### Regional Filters with Period:
```bash
# North region's monthly data
GET /api/analytics/collection/?database=4B-BIO&region=North&period=monthly

# Zone 1's today performance
GET /api/analytics/collection/?database=4B-BIO&zone=Zone1&period=today

# Territory filtered yearly data
GET /api/analytics/collection/?database=4B-BIO&territory=Territory1&period=yearly
```

#### Custom Date Range (Still Works):
```bash
# Specific date range
GET /api/analytics/collection/?database=4B-BIO&start_date=2026-01-01&end_date=2026-01-31
```

### 5. **How It Works**

#### Scenario 1: Using `period=today`
```bash
GET /api/analytics/collection/?database=4B-BIO&user_id=123&period=today
```
**Process:**
1. System calculates: `start_date=2026-02-03`, `end_date=2026-02-03` (today)
2. Finds portal user with ID `123`
3. Retrieves `employee_code` from `user.sales_profile.employee_code`
4. Fetches today's collection data from SAP for that employee
5. Returns data with `user_id: 123` and `employee_id: "EMP001"`

#### Scenario 2: Using `period=monthly`
```bash
GET /api/analytics/collection/?database=4B-BIO&period=monthly
```
**Process:**
1. System calculates: `start_date=2026-02-01`, `end_date=2026-02-03` (current month to date)
2. Uses authenticated user's employee_code
3. Fetches current month's collection data from SAP
4. Returns month-to-date performance

#### Scenario 3: Using `period=yearly`
```bash
GET /api/analytics/collection/?database=4B-BIO&emp_id=456&period=yearly
```
**Process:**
1. System calculates: `start_date=2026-01-01`, `end_date=2026-02-03` (year to date)
2. Uses SAP employee ID `456` directly
3. Fetches year-to-date collection data from SAP
4. Returns current year's performance

#### Scenario 4: Period Overrides Custom Dates
```bash
GET /api/analytics/collection/?database=4B-BIO&start_date=2026-01-01&end_date=2026-01-31&period=today
```
**Process:**
1. `period=today` **overrides** the custom `start_date` and `end_date`
2. Uses today's date: `start_date=2026-02-03`, `end_date=2026-02-03`
3. Custom dates are ignored

### 6. **Swagger Documentation Updated**

#### New Parameters in Swagger:
```yaml
- name: user_id
  in: query
  description: Portal User ID (fetches employee_code automatically)
  type: integer
  required: false

- name: emp_id
  in: query
  description: Employee ID (SAP employee ID, overrides user_id if provided)
  type: integer
  required: false

- name: period
  in: query
  description: Quick date filter - 'today', 'monthly', 'yearly' (overrides start_date/end_date)
  type: string
  enum: [today, monthly, yearly]
  required: false

- name: start_date
  in: query
  description: Custom start date (YYYY-MM-DD). Ignored if 'period' is provided
  type: string
  required: false

- name: end_date
  in: query
  description: Custom end date (YYYY-MM-DD). Ignored if 'period' is provided
  type: string
  required: false
```

#### Enhanced Operation Description:
```
Get detailed collection vs achievement analytics with hierarchical data.

Date Filtering Options:
- Quick Period Filters: period=today|monthly|yearly
- Custom Date Range: start_date & end_date

Parameter Priority:
1. Employee: emp_id → user_id → authenticated user
2. Date: period → start_date/end_date → default range

Examples:
- Today: ?database=4B-BIO&period=today
- This month: ?database=4B-BIO&user_id=123&period=monthly
- Year-to-date: ?database=4B-BIO&period=yearly&in_millions=true
```

#### Updated Response Example:
```json
{
  "success": true,
  "user_id": 123,
  "employee_id": "EMP001",
  "count": 10,
  "data": [
    {
      "name": "Region A",
      "target": 1500000.00,
      "achievement": 1200000.00,
      "from_date": "2026-02-01",
      "to_date": "2026-02-03",
      "zones": [...]
    }
  ],
  "pagination": {
    "page": 1,
    "num_pages": 2,
    "has_next": true,
    "page_size": 10
  },
  "filters": {
    "company": "4B-BIO",
    "region": "",
    "zone": "",
    "territory": ""
  },
  "totals": {
    "target": 1500000.00,
    "achievement": 1200000.00
  }
}
```

### 7. **Code Changes**

#### File: `analytics/serializers.py`
- ✅ Added `user_id` field to `CollectionAnalyticsResponseSerializer`
- ✅ Added `employee_id` field to `CollectionAnalyticsResponseSerializer`

#### File: `analytics/views.py` - `CollectionAnalyticsView`
- ✅ Added `user_id` parameter to Swagger documentation
- ✅ Added `period` parameter to Swagger documentation (enum: today, monthly, yearly)
- ✅ Implemented period calculation logic using Python datetime
- ✅ Enhanced operation description with period examples
- ✅ Implemented user lookup logic to fetch employee_code
- ✅ Added response fields: `user_id` and `employee_id`
- ✅ Enhanced operation description with usage details

## 📊 API Response Behavior

### With user_id Parameter:
```json
{
  "user_id": 123,
  "employee_id": "EMP001"  // Automatically fetched from sales_profile
}
```

### Without user_id (uses authenticated user):
```json
{
  "user_id": 456,
  "employee_id": "EMP002"  // From authenticated request.user
}
```

### User Without sales_profile:
```json
{
  "user_id": 789,
  "employee_id": null  // No sales_profile linked
}
```

## 🎯 Use Cases

### For Mobile/Web Apps - Quick Dashboard Views:
```javascript
// Get today's performance
const todayResponse = await fetch(
  `/api/analytics/collection/?database=4B-BIO&period=today`
);
const todayData = await todayResponse.json();
console.log(`Today's Achievement: ${todayData.totals.achievement}`);

// Get current month performance
const monthResponse = await fetch(
  `/api/analytics/collection/?database=4B-BIO&period=monthly`
);
const monthData = await monthResponse.json();
console.log(`This Month: ${monthData.totals.target} / ${monthData.totals.achievement}`);

// Get year-to-date in millions
const yearResponse = await fetch(
  `/api/analytics/collection/?database=4B-BIO&period=yearly&in_millions=true`
);
const yearData = await yearResponse.json();
console.log(`YTD (M): ${yearData.totals.achievement}M`);
```

### For User-Specific Performance Tracking:
```javascript
// Check specific user's monthly performance
const userId = 123;
const response = await fetch(
  `/api/analytics/collection/?database=4B-BIO&user_id=${userId}&period=monthly`
);
const data = await response.json();

console.log(`User ID: ${data.user_id}`);
console.log(`Employee Code: ${data.employee_id}`);
console.log(`Monthly Target: ${data.totals.target}`);
console.log(`Monthly Achievement: ${data.totals.achievement}`);
console.log(`Date Range: ${data.data[0].from_date} to ${data.data[0].to_date}`);
```

### For Admin Dashboard - Team Overview:
```javascript
// Get today's performance for entire team
const teamToday = await fetch(
  `/api/analytics/collection/?database=4B-BIO&period=today&ignore_emp_filter=true`
);

// Get specific region's monthly data
const regionMonthly = await fetch(
  `/api/analytics/collection/?database=4B-BIO&region=North&period=monthly`
);

// Compare user performance month-to-date
const user1 = await fetch(`/api/analytics/collection/?user_id=123&period=monthly`);
const user2 = await fetch(`/api/analytics/collection/?user_id=456&period=monthly`);
```

### For Reports - Date Range Comparisons:
```javascript
// Current month vs last month
const currentMonth = await fetch(
  `/api/analytics/collection/?database=4B-BIO&period=monthly`
);

const lastMonth = await fetch(
  `/api/analytics/collection/?database=4B-BIO&start_date=2026-01-01&end_date=2026-01-31`
);

// Year-to-date comparison
const ytd2026 = await fetch(
  `/api/analytics/collection/?database=4B-BIO&period=yearly`
);

const ytd2025 = await fetch(
  `/api/analytics/collection/?database=4B-BIO&start_date=2025-01-01&end_date=2025-02-03`
);
```

## 🔍 Testing the Changes

### 1. Test Period Filters:
```bash
# Today's data
curl "http://localhost:8000/api/analytics/collection/?database=4B-BIO&period=today"

# This month (Feb 1 - Feb 3, 2026)
curl "http://localhost:8000/api/analytics/collection/?database=4B-BIO&period=monthly"

# Year to date (Jan 1 - Feb 3, 2026)
curl "http://localhost:8000/api/analytics/collection/?database=4B-BIO&period=yearly"
```

### 2. Test with user_id + period:
```bash
# User 123's monthly data
curl "http://localhost:8000/api/analytics/collection/?database=4B-BIO&user_id=123&period=monthly"

# User 456's today
curl "http://localhost:8000/api/analytics/collection/?database=4B-BIO&user_id=456&period=today"
```

### 3. Test period override:
```bash
# Period overrides custom dates
curl "http://localhost:8000/api/analytics/collection/?database=4B-BIO&start_date=2026-01-01&end_date=2026-01-31&period=today"
# Result: Uses today's date, ignores Jan 1-31 range
```

### 4. Test with regional filters:
```bash
# North region's monthly data
curl "http://localhost:8000/api/analytics/collection/?database=4B-BIO&region=North&period=monthly"
```

### 5. Check Swagger:
```
http://localhost:8000/swagger/#/SAP/api_analytics_collection_list
```
- Try the `period` dropdown with options: today, monthly, yearly
- See auto-calculated date ranges in results

## ✨ Benefits

1. **Quick Filters**: No need to calculate dates client-side
2. **User Tracking**: Always know which user's data is being viewed
3. **Automatic Mapping**: Portal user_id → employee_code mapping is automatic
4. **Flexible Querying**: Support both portal user IDs and SAP employee IDs
5. **Mobile Friendly**: Perfect for dashboards - single parameter for common views
6. **Admin Capability**: Admins can check any user's performance for any period
7. **Time Zones**: Server-side date calculation ensures consistency
8. **Swagger Ready**: Full API documentation with dropdown selections

## 🔐 Security Notes

- Requires authentication (`IsAuthenticated` permission)
- Returns authenticated user's info by default
- `user_id` parameter allows checking other users (useful for admins/managers)
- Employee data filtered based on SAP permissions and hierarchy
- Period calculations use server time (Asia/Karachi timezone)

## 📅 Period Calculation Examples

Based on current date: **February 3, 2026**

| Period Parameter | Start Date | End Date | Description |
|-----------------|------------|----------|-------------|
| `period=today` | 2026-02-03 | 2026-02-03 | Current day only |
| `period=monthly` | 2026-02-01 | 2026-02-03 | Month to date |
| `period=yearly` | 2026-01-01 | 2026-02-03 | Year to date |
| *(no period)* | Custom or default | Custom or default | Uses start_date/end_date |

## 🎉 Summary

✅ **New Parameter**: `period` with 3 options (today, monthly, yearly)  
✅ **Auto Date Calculation**: Server-side date range calculation  
✅ **User Tracking**: `user_id` and `employee_id` in all responses  
✅ **Response Fields**: `user_id` and `employee_id` in all responses  
✅ **Auto Mapping**: Portal user → SAP employee automatic  
✅ **Swagger Updated**: Dropdown selection for period parameter  
✅ **Full Documentation**: Comprehensive examples and use cases  
✅ **Backward Compatible**: Existing calls still work  
✅ **Multiple Endpoints**: Collection Analytics + Sales vs Achievement Territory APIs enhanced

**Ready for production use!**

---

# Sales vs Achievement Territory API Enhancement

## ✅ Changes Completed (February 3, 2026)

### 1. **Updated Sales vs Achievement Territory API** (`/api/sap/sales-vs-achievement-territory/`)

Same enhancements as Collection Analytics API:

#### New Query Parameters:
- **`user_id`**: Portal User ID (auto-fetches employee_code)
- **`emp_id`**: SAP Employee ID (overrides user_id)
- **`period`**: Quick date filter (today, monthly, yearly)

#### New Response Fields:
```json
{
  "success": true,
  "user_id": 123,
  "employee_id": "EMP001",
  "count": 5,
  "data": [...],
  "pagination": {...},
  "totals": {
    "sales": 5000000.00,
    "achievement": 4200000.00
  }
}
```

### 2. **All Features from Collection Analytics**

The Sales vs Achievement Territory API now supports:
- ✅ Period filters (today, monthly, yearly)
- ✅ User ID tracking and employee code mapping
- ✅ Parameter priority (emp_id → user_id → authenticated user)
- ✅ Date filter priority (period → custom dates)
- ✅ Regional/zone/territory filtering
- ✅ Conversion to millions
- ✅ Pagination

### 3. **Usage Examples**

Same usage pattern as Collection Analytics:

```bash
# Today's sales data
GET /api/sap/sales-vs-achievement-territory/?database=4B-BIO&period=today

# User's monthly performance
GET /api/sap/sales-vs-achievement-territory/?database=4B-BIO&user_id=123&period=monthly

# Region filter with period
GET /api/sap/sales-vs-achievement-territory/?database=4B-BIO&region=North&period=yearly&in_millions=true

# Employee's data
GET /api/sap/sales-vs-achievement-territory/?database=4B-BIO&emp_id=456&period=monthly
```

### 4. **Response Structure**

```json
{
  "success": true,
  "user_id": 123,
  "employee_id": "EMP001",
  "count": 3,
  "data": [
    {
      "name": "North Region",
      "sales": 2500000.00,
      "achievement": 2100000.00,
      "zones": [
        {
          "name": "Zone 1",
          "sales": 1500000.00,
          "achievement": 1250000.00,
          "territories": [
            {
              "name": "Territory A",
              "sales": 750000.00,
              "achievement": 625000.00
            }
          ]
        }
      ]
    }
  ],
  "pagination": {
    "page": 1,
    "num_pages": 1,
    "has_next": false,
    "has_prev": false,
    "count": 3,
    "page_size": 10
  },
  "totals": {
    "sales": 2500000.00,
    "achievement": 2100000.00
  }
}
```

### 5. **Swagger Documentation**

Full swagger documentation with:
- Period parameter dropdown (today, monthly, yearly)
- User_id and emp_id parameters
- Enhanced operation description
- Usage examples
- Parameter priority explanations

---

**Last Updated**: February 3, 2026  
**Files Modified**: 7 (views.py, urls.py, analytics/views.py, analytics/serializers.py, sap_integration/views.py, API_UPDATE_SUMMARY.md)  
**New Features**: Period filters (today, monthly, yearly), User tracking (user_id, employee_id)  
**New Endpoints**: 1 (product-document API)  
**Enhanced Endpoints**: 2 (collection analytics API, sales-vs-achievement-territory API)  
**Swagger Tags**: 1 (SAP - Products)
