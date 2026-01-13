# Sales Order Admin Form - Cascading Dropdowns Setup Complete

## What Was Updated

### 1. **Backend APIs** (Already Working)
- ✅ `/api/sap/customer-policies/` - Get policies for customer
- ✅ `/api/sap/policy-items-lov/` - Get items in policy
- ✅ `/api/sap/item-price/` - Get price for item

### 2. **JavaScript** (`salesorder_policy.js`)
Updated to use new API endpoints and added comprehensive logging:

#### Customer Selection → Policy Loading
When customer is selected, automatically loads their policies:
```javascript
// Calls: /api/sap/customer-policies/?card_code=ORC00001&database=4B-ORANG
// Updates all policy dropdowns in sales order lines
```

#### Policy Selection → Item Loading  
When policy is selected, loads available items:
```javascript
// Extracts DocEntry from selected policy label
// Calls: /api/sap/policy-items-lov/?doc_entry=2&database=4B-ORANG
// Populates item dropdown with 100+ items
```

#### Item Selection → Price Auto-fill
When item is selected, automatically fetches and fills price:
```javascript
// Calls: /api/sap/item-price/?doc_entry=2&item_code=FG00007&database=4B-ORANG
// Auto-fills unit_price field
// Also fills item_description and measure_unit
```

### 3. **Admin.py** (No Changes Needed)
The existing setup already has:
- ✅ `SalesOrderLineInlineForm` with proper field definitions
- ✅ CSS classes: `sap-policy-lov`, `sap-item-lov`
- ✅ JavaScript files included in Media class
- ✅ Readonly fields for auto-filled data

## How It Works (Flow)

```
┌─────────────────────────────────────────────────────────────┐
│  1. SELECT CUSTOMER (top of form)                           │
│     Customer Code: ORC00001 ▼                               │
└────────────────┬────────────────────────────────────────────┘
                 │
                 ▼ (JavaScript triggers)
┌─────────────────────────────────────────────────────────────┐
│  API: /api/sap/customer-policies/?card_code=ORC00001        │
│  Response: [                                                 │
│    {policy_doc_entry: 27, project_name: "Policy A"},        │
│    {policy_doc_entry: 28, project_name: "Policy B"}         │
│  ]                                                           │
└────────────────┬────────────────────────────────────────────┘
                 │
                 ▼ (Updates all policy dropdowns)
┌─────────────────────────────────────────────────────────────┐
│  SALES ORDER LINES                                           │
│  ┌──────────────────────────────────────────────────────┐  │
│  │ Row 1:                                                │  │
│  │ POLICY: Policy A (DocEntry: 27) ▼   ← NOW POPULATED  │  │
│  │ ITEM:   --- Select Item ---      ▼   ← WAITING       │  │
│  └──────────────────────────────────────────────────────┘  │
└────────────────┬────────────────────────────────────────────┘
                 │
                 ▼ (User selects policy)
┌─────────────────────────────────────────────────────────────┐
│  API: /api/sap/policy-items-lov/?doc_entry=27               │
│  Response: [                                                 │
│    {ItemCode: "FG00004", ItemName: "Afsar 60...", ...},     │
│    {ItemCode: "FG00007", ItemName: "Jalwa 32...", ...}      │
│  ]                                                           │
└────────────────┬────────────────────────────────────────────┘
                 │
                 ▼ (Updates item dropdown)
┌─────────────────────────────────────────────────────────────┐
│  │ Row 1:                                                │  │
│  │ POLICY: Policy A (DocEntry: 27) ✓                    │  │
│  │ ITEM:   FG00007 - Jalwa 32.5 Sc ▼   ← NOW POPULATED  │  │
│  └──────────────────────────────────────────────────────┘  │
└────────────────┬────────────────────────────────────────────┘
                 │
                 ▼ (User selects item)
┌─────────────────────────────────────────────────────────────┐
│  API: /api/sap/item-price/?doc_entry=27&item_code=FG00007   │
│  Response: {                                                 │
│    doc_entry: "27",                                          │
│    item_code: "FG00007",                                     │
│    unit_price: -1.0                                          │
│  }                                                           │
└────────────────┬────────────────────────────────────────────┘
                 │
                 ▼ (Auto-fills price field)
┌─────────────────────────────────────────────────────────────┐
│  │ Row 1:                                                │  │
│  │ POLICY: Policy A (DocEntry: 27) ✓                    │  │
│  │ ITEM:   FG00007 - Jalwa 32.5 Sc ✓                    │  │
│  │ DESCRIPTION: Jalwa 32.5 Sc - 200-Mls. (auto-filled)  │  │
│  │ MEASURE UNIT: No (auto-filled)                       │  │
│  │ PRICE: -1 (auto-filled)             ← DONE!          │  │
│  └──────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

## Testing Instructions

### 1. Open Sales Order Form
```
http://localhost:8000/admin/FieldAdvisoryService/salesorder/add/
```

### 2. Open Browser Console (F12)
You'll see detailed logging:
```
[POLICY] Loading policies for customer: ORC00001
[POLICY] Fetching from: /api/sap/customer-policies/?card_code=ORC00001&database=4B-ORANG
[POLICY] Response: {success: true, count: 2, data: [...]}
[POLICY] Found 2 policies
[POLICY] Added option: Policy A (DocEntry: 27)
[POLICY] Added option: Policy B (DocEntry: 28)
[POLICY] Updating all policy dropdowns with 3 options
```

### 3. Select Customer
- Choose a customer from the dropdown (e.g., ORC00001)
- Watch console logs for policy loading
- Check that policy dropdowns in sales order lines are populated

### 4. Select Policy in Line Item
- In "POLICY" column, select a policy
- Console will show: `[POLICY] Loading items from: /api/sap/policy-items-lov/?doc_entry=27`
- Item dropdown should populate with 100+ items

### 5. Select Item
- Choose an item from the dropdown
- Console will show: `[ITEM] Fetching price for DocEntry: 27, ItemCode: FG00007`
- Price field should auto-fill
- Description and measure unit should also auto-fill

## Troubleshooting

### Issue: Policies not loading
**Check:**
1. Open browser console (F12) and look for `[POLICY]` logs
2. Verify customer code is selected
3. Check database selector at top-right (should be 4B-ORANG or 4B-BIO)
4. Test API directly: `http://localhost:8000/api/sap/customer-policies/?card_code=ORC00001&database=4B-ORANG`

### Issue: Items not loading
**Check:**
1. Verify policy is selected
2. Look for DocEntry extraction in console: `[POLICY] Extracted DocEntry: 27`
3. Test API: `http://localhost:8000/api/sap/policy-items-lov/?doc_entry=27&database=4B-ORANG`

### Issue: Price not loading
**Check:**
1. Verify both policy and item are selected
2. Look for: `[ITEM] Fetching price for DocEntry: 27, ItemCode: FG00007`
3. Test API: `http://localhost:8000/api/sap/item-price/?doc_entry=27&item_code=FG00007&database=4B-ORANG`
4. Note: Price `-1` means "use standard price" (not an error)

## Database Switching

The form respects the global database selector at top-right:
- Switch to **4B-BIO** → Shows BIO customers, policies, items
- Switch to **4B-ORANG** → Shows ORANG customers, policies, items

All API calls include `?database=` parameter automatically.

## Files Modified

### Backend
- ✅ `sap_integration/views.py` - Added `customer_policies_api()` endpoint
- ✅ `sap_integration/urls.py` - Added route for customer-policies

### Frontend
- ✅ `static/FieldAdvisoryService/salesorder_policy.js` - Updated all API endpoints, added logging

### Documentation
- ✅ `SALES_ORDER_FORM_API_WORKFLOW.md` - API reference guide
- ✅ `SALES_ORDER_ADMIN_SETUP.md` - This file

## Next Steps

1. **Test the form** with real data
2. **Verify database switching** works correctly
3. **Check mobile compatibility** if needed
4. **Monitor console logs** for any errors

If you see errors, check the browser console (F12) for detailed `[POLICY]` and `[ITEM]` log messages.
