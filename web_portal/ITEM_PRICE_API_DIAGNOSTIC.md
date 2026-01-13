# Item Price API - Diagnostic Report & Test Guide

## Status: ✅ API is WORKING CORRECTLY

The `/sap/item-price/` endpoint is functioning properly. The issue is **DATA**, not code.

---

## The Problem

### ORANGE Database
- **All prices are set to -1** (invalid sentinel value)
- Out of 6,830 item rows: **6,028 have -1 prices**, 802 have 0 prices, **0 have positive prices**
- This is a **DATA PROBLEM** in the SAP system

### BIO Database ✅
- **Prices range from 189 to 237,000**
- Out of 7,209 item rows: **1,081 have positive prices**
- API works correctly here

---

## What The API Expects

**Endpoint:** `/sap/item-price/`

**Required Parameters:**
| Parameter | Type | Example | Notes |
|-----------|------|---------|-------|
| `database` | string | `4B-ORANG` or `4B-BIO` | Case-insensitive, with/without `-APP` suffix |
| `doc_entry` | integer | `111`, `271`, `19` | Actual policy DocEntry from @PL1 table |
| `item_code` | string | `FG00107`, `FG00516` | Actual item code from catalog |

---

## Quick Test Examples

### ✅ BIO Database (Works - Has Prices)

```bash
curl "http://localhost:8000/sap/item-price/?database=4B-BIO&doc_entry=271&item_code=FG00516"
```

**Expected Response:**
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

### ❌ ORANGE Database (Doesn't Work - All Prices are -1)

```bash
curl "http://localhost:8000/sap/item-price/?database=4B-ORANG&doc_entry=111&item_code=FG00107"
```

**Response (Price is 0 - no positive prices available):**
```json
{
  "success": true,
  "data": {
    "doc_entry": "111",
    "item_code": "FG00107",
    "unit_price": 0.0
  }
}
```

---

## Valid Sample Data

### BIO Database Valid Combinations:
```
DocEntry    ItemCode    Price
------  -----------  ----------
271     FG00516      237,000
281     FG00516      237,000
266     FG00516      237,000
281     FG00343      210,000
266     FG00343      197,000
281     FG00399      107,000
281     FG00274       90,000
266     FG00274       84,000
```

### ORANGE Database Valid Combinations:
```
DocEntry    ItemCode    Price
------  -----------  ----------
111     FG00107          0
111     FG00229          0
111     FG00371          0
192     FG00050          0
166     FG00346          0
26      FG00177          0
```

---

## Root Cause Analysis

| Aspect | ORANGE | BIO |
|--------|--------|-----|
| Total Items | 6,830 | 7,209 |
| Items with Positive Prices | **0** ❌ | 1,081 ✅ |
| Items with -1 Prices | 6,028 (88%) | 4,784 (66%) |
| Items with 0 Prices | 802 (12%) | 1,315 (18%) |
| API Status | Working but no data | Working + data available |

---

## Diagnostic Scripts Provided

Three scripts created for testing:

1. **`test_item_price.py`** - Basic connectivity test
2. **`test_item_price_real_data.py`** - Real data from database
3. **`item_price_diagnostic.py`** - Complete diagnostic report (THIS FILE'S SOURCE)

Run any with:
```bash
python item_price_diagnostic.py
```

---

## Recommended Actions

### For ORANGE Database:
1. **Contact SAP team** - Investigate why all policy prices are -1
2. **Check SAP B1** - Verify policy pricing is correctly configured
3. **Update Data** - Populate `@PLR4.U_frp` with actual prices
4. **Verify in HANA** - Confirm prices sync correctly
5. **Test API** - Re-run diagnostic after data fix

### For BIO Database:
- ✅ No action needed - API works perfectly
- Prices are properly populated and accessible

---

## Technical Details

**Query Used:**
```sql
SELECT T1."U_frp" 
FROM "@PL1" T0 
INNER JOIN "@PLR4" T1 ON T0."DocEntry" = T1."DocEntry" 
WHERE T0."DocEntry" = ? 
AND T1."U_itc" = ?
```

**API Response Format:**
```json
{
  "success": true,
  "data": {
    "doc_entry": "<string>",
    "item_code": "<string>",
    "unit_price": <float or null>
  }
}
```

---

## Conclusion

✅ **The API is working correctly and returning prices as expected.**

❌ **The ORANGE database does not have valid pricing data (-1 is a sentinel value indicating "not set").**

**To resolve: Update the policy pricing in ORANGE database in SAP B1.**
