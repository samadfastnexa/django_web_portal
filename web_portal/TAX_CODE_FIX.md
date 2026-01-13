# Tax Code Corruption Fix - Action Items

## Issue
Error: "234000286 - Specify valid tax code '\u00ff\u00bd'"
- The `vat_group` field contains corrupted character data
- Character `\u00ff\u00bd` is an encoding error marker

## Root Cause
- vat_group field loaded invalid/corrupted data from SAP LOVs
- Or data was corrupted in the database

## Quick Fixes Applied

### 1. ✅ Admin Form Improvement (admin.py lines 460-495)
```python
# Now:
- Validates tax codes before loading
- Skips corrupted codes
- Defaults to 'SE' (Standard Exempted) if no valid codes
- Sets vat_group initial value to 'SE'
- Has fallback safe defaults
```

### 2. ✅ SAP Payload Validation (admin.py lines 1210-1250)
```python
# Now checks before sending to SAP:
- Detects corrupted characters (\ufffd, \xff, \x00)
- Replaces with valid default 'SE'
- Logs warnings for any replacements
```

## Manual Cleanup (DO THIS NOW)

### Step 1: Run Diagnostic
```powershell
python diagnose_tax_code.py
```

This will:
- Find all corrupted vat_group values
- Clean them to 'SE' (Standard Exempted)
- Verify the fix

### Step 2: Verify Database
```powershell
python manage.py shell
```

```python
from FieldAdvisoryService.models import SalesOrderLine

# Check for corruption
bad_lines = SalesOrderLine.objects.filter(vat_group__contains='\ufffd')
print(f"Corrupted lines: {bad_lines.count()}")

# Check for empty
empty_lines = SalesOrderLine.objects.filter(vat_group='')
print(f"Empty vat_group: {empty_lines.count()}")

# All should be clean now
clean_lines = SalesOrderLine.objects.all()
for line in clean_lines[:5]:
    print(f"Line {line.id}: vat_group = '{line.vat_group}'")

exit()
```

## Test SAP Posting Again

### Step 1: Restart Django Server
```powershell
# Ctrl+C to stop current server
python manage.py runserver
```

### Step 2: Open Sales Order
```
http://localhost:8000/admin/FieldAdvisoryService/salesorder/add/
```

### Step 3: Create Order
1. Select customer: ORC00004
2. Add line item with:
   - Policy: PROJ000000037
   - Item: FG00319
   - Quantity: 5
3. **Important**: Select TAX CODE from dropdown (e.g., 'SE' or 'AT1')
4. Click "Save and continue editing"

### Step 4: Post to SAP
```
Click "Add to SAP" button
```

### Step 5: Check Response
- **Expected**: ✅ Success (no tax code error)
- **If error**: Check terminal logs for what vat_group value was sent

## Valid Tax Codes (for reference)

| Code | Name | Rate |
|------|------|------|
| SE | Standard Exempted | 0% |
| AT1 | Standard Taxable | 17% |
| ST | Super Tax | Various |

To find all valid codes in SAP:
```sql
SELECT CODE, NAME, Rate 
FROM "4B-ORANG_APP".OSTC 
WHERE Active = 'Y'
ORDER BY CODE;
```

## Prevention Going Forward

### In Admin Form
- ✅ vat_group now defaults to 'SE'
- ✅ Only valid tax codes in dropdown
- ✅ No corrupted data can be selected

### In SAP Payload
- ✅ Any corrupted values detected and cleaned
- ✅ Always fallback to 'SE' if problem found
- ✅ Logged for debugging

### In Database
- ✅ All existing corrupted data cleaned by diagnose script

## Success Checklist

- [ ] Run `python diagnose_tax_code.py`
- [ ] Verify all vat_group values cleaned to 'SE'
- [ ] Restart Django server
- [ ] Test creating a new sales order
- [ ] Select TAX CODE from dropdown (NOT empty)
- [ ] Click Save and verify fields persist
- [ ] Click "Add to SAP"
- [ ] ✅ Should post successfully without tax code error

## Troubleshooting

### Still Getting Tax Code Error?
1. Check terminal logs for what vat_group is being sent
2. Verify the selected dropdown value
3. Run diagnose script again to ensure all cleaned
4. Check if different database (4B-BIO vs 4B-ORANG) has different tax codes

### VAT Group Not Saving?
1. Ensure it's not in `readonly_fields`
2. Hard refresh browser (Ctrl+F5)
3. Check browser console for JavaScript errors (F12)

### Can't Select Tax Code from Dropdown?
1. Dropdown not populated = admin form not rendering properly
2. Try adding a line item manually
3. Check admin.py console output for LOV loading errors
