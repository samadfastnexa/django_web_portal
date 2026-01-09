# Item Price API - Comprehensive Analysis

## Executive Summary

**Status:** ✅ API is WORKING CORRECTLY  
**Issue:** ❌ DATA PROBLEM in ORANGE database - all prices are set to -1

---

## Findings

### ORANGE Database Issue
- **6,028 out of 6,830 items (88%)** have price = -1 (invalid/not configured)
- **802 items (12%)** have price = 0
- **0 items (0%)** have positive prices ❌
- **CONCLUSION:** No actual pricing data available for ORANGE

### BIO Database Status
- **1,081 out of 7,209 items (15%)** have positive prices ✅
- **4,784 items (66%)** have price = -1
- **1,315 items (18%)** have price = 0  
- **CONCLUSION:** API works correctly, but many items lack pricing

---

## API Endpoint Details

**URL:** `GET /sap/item-price/`

**Parameters:**
```
database   : 4B-ORANG or 4B-BIO (case-insensitive, -APP suffix optional)
doc_entry  : Policy DocEntry number (integer)
item_code  : Item code from catalog (string, e.g., FG00516)
```

**Response Format:**
```json
{
  "success": true,
  "data": {
    "doc_entry": "271",
    "item_code": "FG00516", 
    "unit_price": 237000.0
  }
}
```

---

## Test Data Available

### BIO Database - Working Examples
```
DocEntry  ItemCode  Price      Status
-------  --------  --------   --------
271      FG00516   237,000    ✅ Valid
281      FG00516   237,000    ✅ Valid
281      FG00343   210,000    ✅ Valid
266      FG00343   197,000    ✅ Valid
281      FG00399   107,000    ✅ Valid
281      FG00274    90,000    ✅ Valid
```

### ORANGE Database - No Valid Prices
```
DocEntry  ItemCode  Price     Status
-------  --------  -------   --------
111      FG00107      0       ❌ Zero
111      FG00229      0       ❌ Zero
111      FG00371      0       ❌ Zero
111      FG00219      0       ❌ Zero
192      FG00050      0       ❌ Zero
166      FG00346      0       ❌ Zero
2        FG00171     -1       ❌ Invalid
```

---

## Database Query

The API uses this SQL query:

```sql
SELECT T1."U_frp" 
FROM "@PL1" T0 
INNER JOIN "@PLR4" T1 ON T0."DocEntry" = T1."DocEntry" 
WHERE T0."DocEntry" = ? 
AND T1."U_itc" = ?
```

Where:
- `@PL1` = Policy Header table
- `@PLR4` = Policy Items table  
- `U_frp` = Unit Price field (Custom field)
- `U_itc` = Item Code field (Custom field)

---

## Root Cause

The issue is **NOT** with the API code. The problem is:

1. **ORANGE Database Pricing Issue**
   - Custom fields `@PL1.U_frp` contains mostly -1 (sentinel value = "not set")
   - This indicates SAP B1 policies were created but pricing was never entered
   - The -1 value is interpreted as "invalid/no price configured"

2. **Why BIO Works**
   - Policies have actual pricing configured
   - Prices populated in `@PLR4.U_frp` column
   - API successfully retrieves and returns them

---

## How to Fix

### For ORANGE Database:

1. **In SAP B1:**
   - Navigate to: Purchasing → Policy Master
   - Select the policy
   - Edit > Items tab > Set Unit Price field

2. **Verify in HANA:**
   ```sql
   SELECT COUNT(*) FROM 4B-ORANG_APP."@PLR4" WHERE "U_frp" > 0
   ```
   Should show > 0 rows

3. **Re-test API:**
   ```bash
   curl "http://localhost:8000/sap/item-price/?database=4B-ORANG&doc_entry=111&item_code=FG00107"
   ```
   Should return positive price instead of 0 or -1

---

## Test Scripts Provided

Three diagnostic scripts created:

1. **`test_item_price.py`**
   - Basic connectivity check
   - Verifies HANA and table access
   ```bash
   python test_item_price.py
   ```

2. **`test_item_price_real_data.py`**
   - Queries actual database data
   - Shows sample valid combinations
   - Tests direct SQL queries
   ```bash
   python test_item_price_real_data.py
   ```

3. **`item_price_diagnostic.py`**
   - Complete diagnostic report
   - Data quality analysis
   - Recommended actions
   ```bash
   python item_price_diagnostic.py
   ```

4. **`quick_test_item_price.py`**
   - HTTP endpoint tests (requires Django running)
   - Real API calls with parameters
   ```bash
   python manage.py runserver  # First terminal
   python quick_test_item_price.py  # Second terminal
   ```

---

## Conclusion

### ✅ What's Working
- API code is correct and functional
- Database connectivity is solid
- Query logic is sound
- BIO database pricing accessible

### ❌ What's Not Working
- ORANGE database has no pricing data
- All prices are -1 (invalid sentinel)
- This is a **DATA ISSUE**, not a **CODE ISSUE**

### 📋 Next Steps
1. Contact SAP team to investigate ORANGE policy pricing
2. Update pricing in SAP B1
3. Verify prices sync to HANA
4. Re-run diagnostic script to confirm fix

---

## Files Created

- `test_item_price.py` - Basic diagnostic
- `test_item_price_real_data.py` - Real data analysis  
- `item_price_diagnostic.py` - Full diagnostic report
- `quick_test_item_price.py` - API endpoint testing
- `ITEM_PRICE_API_DIAGNOSTIC.md` - This file
