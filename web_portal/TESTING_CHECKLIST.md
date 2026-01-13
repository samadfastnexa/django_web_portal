# Sales Order Form Testing Checklist

## Prerequisites
1. ✅ Restart Django server (admin.py changes require restart)
2. ✅ Clear browser cache or hard refresh (Ctrl+F5)

## Test Case 1: Customer Selection & Auto-Fill

### Steps:
1. Open Sales Order admin: `/admin/FieldAdvisoryService/salesorder/add/`
2. Select customer: **ORC00004 - New Choudhry Agro Tarders Rohillanwali**
3. Watch browser console for logs

### Expected Console Logs:
```
[CUSTOMER] onCustomerChange called with: ORC00004
[CUSTOMER] About to dispatch customer-selected event with code: ORC00004
[CUSTOMER] ✓ Event dispatched successfully
[CUSTOMER] Removed readonly from: card_name
[CUSTOMER] Removed readonly from: contact_person_code
[CUSTOMER] Removed readonly from: federal_tax_id
[CUSTOMER] Removed readonly from: pay_to_code
[CUSTOMER] Removed readonly from: address
[POLICY] ✓ Received customer-selected event
[POLICY] Extracted cardCode: ORC00004
[POLICY] Found 3 policies
[POLICY] Updating all policy dropdowns with 4 options
```

### Expected UI Changes:
- ✅ Card name: "New Choudhry Agro Tarders Rohillanwali"
- ✅ Contact person code: 669
- ✅ Federal tax ID: "32304-7980549-1"
- ✅ Address: "Rohillanwali Tehsil M Garh"
- ✅ Fields should be editable (no gray background, cursor normal)

---

## Test Case 2: Form Save (Database Persistence)

### Steps:
1. After customer selected and fields auto-filled
2. Click **"Save and continue editing"**
3. Check Django terminal logs

### Expected Terminal Logs:
```
[FORM CLEAN] === Customer Fields ===
[FORM CLEAN] card_code: 'ORC00004' (type: <class 'str'>)
[FORM CLEAN] card_name: 'New Choudhry Agro Tarders Rohillanwali' (type: <class 'str'>)
[FORM CLEAN] contact_person_code: '669'
[FORM CLEAN] federal_tax_id: '32304-7980549-1'
[FORM CLEAN] address: 'Rohillanwali Tehsil M Garh'

[SAVE_MODEL] Saving SalesOrder #123
[SAVE_MODEL] Set obj.card_code = 'ORC00004'
[SAVE_MODEL] Set obj.card_name = 'New Choudhry Agro Tarders Rohillanwali'
[SAVE_MODEL] ✓ After save and refresh - card_code in DB: 'ORC00004'
[SAVE_MODEL] ✓ After save and refresh - card_name in DB: 'New Choudhry Agro Tarders Rohillanwali'
[SAVE_MODEL] ✓ After save and refresh - address in DB: 'Rohillanwali Tehsil M Garh'
```

### Expected UI Changes:
- ✅ Page reloads with success message
- ✅ All fields retain their values (no reset)
- ✅ Customer code still shows ORC00004
- ✅ Card name still shows "New Choudhry Agro Tarders Rohillanwali"

---

## Test Case 3: Policy & Item Selection

### Steps:
1. After customer saved successfully
2. In first line item row, select policy: **"PROJ000000037 (DocEntry: 37) - FARMERS MEETING 2024-25"**
3. Watch console for item loading
4. Select item: **FG00319**
5. Watch for price auto-fill

### Expected Console Logs:
```
[POLICY] Policy changed: PROJ000000037 (DocEntry: 37) - FARMERS MEETING 2024-25
[POLICY] Extracted DocEntry: 37
[POLICY] Loading items for policy DocEntry 37...
[POLICY] Item dropdown updated with 1 valid items
[POLICY] Added item: FG00319 - Some Item Name
[ITEM] Item changed: FG00319
[ITEM] Auto-filled description and measure unit
[ITEM] Fetching price for DocEntry 37, ItemCode FG00319
[ITEM] Price auto-filled: 1500
```

### Expected UI Changes:
- ✅ Policy dropdown shows 3 policies (DocEntry 27, 28, 37)
- ✅ After selecting policy 37, item dropdown shows FG00319
- ✅ After selecting FG00319:
  - Item description auto-filled
  - Measure unit auto-filled
  - Unit price auto-filled (e.g., 1500)
  - Warehouse dropdown populates

---

## Test Case 4: Complete Order Save

### Steps:
1. After policy, item, and price filled
2. Enter quantity: **10**
3. Click **"Save and continue editing"** again
4. Verify all line items saved

### Expected:
- ✅ Order header saved with customer info
- ✅ Line items saved with policy, item, quantity, price
- ✅ No fields reset after save

---

## Test Case 5: Post to SAP

### Steps:
1. After order completely saved
2. Scroll down to "SAP Integration" section
3. Click **"Add to SAP"** button
4. Wait for response (10-20 seconds)

### Expected Terminal Logs:
```
[ORDER DATA] Order #123 from database (refreshed):
  CardCode: 'ORC00004'
  CardName: 'New Choudhry Agro Tarders Rohillanwali'
  U_SCardCode: ''
  DocumentLines: 1

[SAP PAYLOAD] Order #123 payload:
{
  "CardCode": "ORC00004",
  "CardName": "New Choudhry Agro Tarders Rohillanwali",
  "ContactPersonCode": 669,
  "FederalTaxID": "32304-7980549-1",
  "Address": "Rohillanwali Tehsil M Garh",
  "DocumentLines": [
    {
      "ItemCode": "FG00319",
      "Quantity": 10.0,
      "UnitPrice": 1500.0,
      "U_policy": "PROJ000000037"
    }
  ]
}

[SAP PAYLOAD] Using company DB: 4B-ORANG
```

### Expected UI Response:
- ✅ Success message: "Order #123 posted successfully to SAP"
- ✅ SAP Doc Entry filled (e.g., 12345)
- ✅ SAP Doc Num filled (e.g., 67890)
- ✅ "Is posted to SAP" checkbox checked
- ✅ NO ERROR about CardCode or CardName being empty

---

## Common Issues & Solutions

### Issue 1: Fields Reset After Save
**Solution**: JavaScript is removing readonly attributes correctly

### Issue 2: "CardCode is required but is empty"
**Root Cause**: Fields not persisting to database
**Solutions Applied**:
1. ✅ Removed card_name, contact_person_code, etc. from `readonly_fields`
2. ✅ Changed HTML `readonly=True` to CSS styling
3. ✅ JavaScript explicitly removes readonly/disabled attributes
4. ✅ save_model() explicitly sets all fields from form.cleaned_data

### Issue 3: Policies Not Showing
**Solution**: Event-based cascade implemented, API working

### Issue 4: Items Not Loading for Policy 27/28
**Solution**: These policies have no items (ITEMCODE is null) - correct behavior

---

## Key Files Modified

1. **admin.py** (Lines 320-360, 1020-1065, 560):
   - Removed HTML readonly attributes
   - Removed card_name, etc. from readonly_fields
   - Enhanced clean() method with logging
   - Enhanced save_model() with explicit field setting

2. **salesorder_customer.js** (Lines 50-66):
   - Added explicit removal of readonly/disabled attributes after auto-fill
   - Comprehensive logging for debugging

3. **salesorder_policy.js** (Lines 157-169):
   - Broadened selectors to find policy dropdowns
   - Event-based policy loading

---

## Success Criteria

✅ **All fields persist after save**
✅ **No CardCode/CardName errors when posting to SAP**
✅ **Cascading dropdowns work correctly**
✅ **Form is fully functional end-to-end**
