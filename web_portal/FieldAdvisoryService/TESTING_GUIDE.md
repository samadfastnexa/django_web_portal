# SAP Loading Screen - Testing Guide

## Pre-Testing Checklist

- [ ] Django development server running (`python manage.py runserver`)
- [ ] Test order #32 exists in database
- [ ] Browser with developer tools available (Chrome/Firefox/Edge)
- [ ] Network access to SAP server (fourbtest.vdc.services:50000)

## Test 1: Visual Demo (No SAP Connection Required)

### Objective
Verify loading screen animations work correctly in isolation

### Steps
1. Open file in browser:
   ```
   FieldAdvisoryService/templates/sap_loading_demo.html
   ```

2. Click **"✓ Simulate Success (3s)"**
   - [ ] Loading overlay appears instantly
   - [ ] Spinner rotates smoothly
   - [ ] Progress bar animates
   - [ ] Timer counts: 0s, 1s, 2s, 3s
   - [ ] Success screen shows with green checkmark
   - [ ] Message displays: "Order #32 posted successfully"
   - [ ] DocNum shows: "SO-12345"
   - [ ] Alert appears after 2 seconds

3. Click **"✗ Simulate Error (2s)"**
   - [ ] Loading overlay appears
   - [ ] Timer counts: 0s, 1s, 2s
   - [ ] Error screen shows with red X
   - [ ] Message displays: "Connection timeout..."
   - [ ] Overlay hides after 5 seconds

4. Click **"⏱️ Simulate Timeout (16s)"**
   - [ ] Loading overlay appears
   - [ ] Timer counts up to 15s
   - [ ] Warning appears: "⚠️ This is taking longer than usual..."
   - [ ] Warning pulses (fades in/out)
   - [ ] Timer continues to 16s
   - [ ] Success screen appears
   - [ ] Overlay hides after 2 seconds

5. Click **"🔄 Manual Control"**
   - [ ] Loading overlay appears
   - [ ] Alert shows with console instructions
   - Open browser console (F12)
   - Type: `SAPLoadingScreen.showResult(true, "Test", "SO-999")`
   - [ ] Success screen appears
   - [ ] Shows "Test" message and "SO-999"

### Expected Results
All animations smooth (60 FPS), no console errors, timings accurate

---

## Test 2: Live Admin Interface (Full Integration)

### Objective
Test complete workflow with real Django admin and database

### Steps

#### 2.1 Access Admin Page
1. Navigate to: `http://localhost:8000/admin/`
2. Login with admin credentials
3. Go to: `FieldAdvisoryService > Sales Orders`
4. Click on Order #32 (or any test order)

#### 2.2 Verify Button Display
- [ ] Scroll to "SAP Integration" section
- [ ] If not posted: Blue "Add to SAP" button visible
- [ ] If already posted: Green success box with DocEntry/DocNum

#### 2.3 Inspect Page
- Open browser developer tools (F12)
- Go to **Console** tab
- [ ] No JavaScript errors
- [ ] See: "Sales Order LOV script loaded"
- Go to **Network** tab, clear all entries

#### 2.4 Test Button Click (Mock - Disconnect Network)
1. In browser DevTools, go to **Network** tab
2. Select "Offline" from throttling dropdown
3. Click "Add to SAP" button

**Expected:**
- [ ] Loading overlay appears instantly
- [ ] Spinner rotates smoothly
- [ ] Progress bar animates from 0% to ~90%
- [ ] Timer updates: 0s → 1s → 2s...
- [ ] After ~2-5 seconds, error appears
- [ ] Message: "Unable to connect to server" or "Network error"
- [ ] Red X icon displayed
- [ ] Overlay hides after 5 seconds

4. Set network back to "Online"

#### 2.5 Test Real SAP Posting
**WARNING:** This will create a real sales order in SAP

1. Ensure order is not already posted
2. Verify all required fields filled:
   - [ ] Card Code
   - [ ] Document Date
   - [ ] At least one document line with Item Code
3. Click "Add to SAP" button

**Expected:**
- [ ] Loading overlay appears instantly
- [ ] Spinner rotates continuously
- [ ] Progress bar animates
- [ ] Timer updates every ~100ms
- [ ] Wait 10-20 seconds (typical SAP response time)
- [ ] If >15s: Warning appears with pulse animation
- [ ] On success:
   - [ ] Progress bar completes (100%)
   - [ ] Spinner stops
   - [ ] Success screen appears (green)
   - [ ] Shows: "Order #X posted successfully to SAP"
   - [ ] Shows SAP DocNum
   - [ ] Page reloads after 2 seconds
   - [ ] After reload, see green success box instead of button

**On Success, Verify Database:**
```sql
SELECT id, is_posted_to_sap, sap_doc_entry, sap_doc_num, posted_at, sap_error
FROM FieldAdvisoryService_salesorder
WHERE id = 32;
```
- [ ] `is_posted_to_sap` = 1
- [ ] `sap_doc_entry` = [number]
- [ ] `sap_doc_num` = [string]
- [ ] `posted_at` = [timestamp]
- [ ] `sap_error` = NULL
- [ ] `sap_response_json` = [full JSON response]

---

## Test 3: Error Scenarios

### 3.1 Already Posted Error
1. Navigate to order that is already posted (is_posted_to_sap = True)
2. [ ] Verify green success box displayed, no button
3. In database, temporarily set `is_posted_to_sap = 0`
4. Refresh admin page
5. [ ] Blue "Add to SAP" button appears
6. Click button

**Expected:**
- [ ] Loading overlay appears
- [ ] Quick response (< 1 second)
- [ ] Error screen: "Order already posted"
- [ ] Overlay hides after 5 seconds

### 3.2 SAP Connection Error
**Setup:** Temporarily break SAP connection
- Option A: Change SAP_SERVICE_LAYER_URL in .env to wrong URL
- Option B: Stop SAP Service Layer (if you have access)
- Option C: Add firewall rule blocking port 50000

**Steps:**
1. Click "Add to SAP" on valid order
2. Wait for response

**Expected:**
- [ ] Loading overlay appears
- [ ] Spinner and progress bar animate
- [ ] Timer counts up
- [ ] After 30-60 seconds (timeout)
- [ ] Error screen appears
- [ ] Message: Connection error or timeout
- [ ] Overlay hides after 5 seconds

**Restore SAP connection after test**

### 3.3 Validation Error
**Setup:** Create order with missing required field
1. Create new order without Card Code
2. Add document line
3. Click "Add to SAP"

**Expected:**
- [ ] Loading overlay appears
- [ ] Quick response (< 1 second)
- [ ] Error screen with validation message
- [ ] Overlay hides after 5 seconds

---

## Test 4: Performance & UI

### 4.1 Loading Screen Appearance Speed
1. Click "Add to SAP"
2. Use browser DevTools Performance profiler
3. Record timing from click to overlay visible

**Expected:** < 50ms

### 4.2 Animation Smoothness
1. Click "Add to SAP"
2. Open DevTools > More Tools > Rendering
3. Enable "FPS Meter"

**Expected:** 
- [ ] 55-60 FPS during animations
- [ ] No dropped frames
- [ ] Smooth spinner rotation
- [ ] Smooth progress bar animation

### 4.3 Timer Accuracy
1. Click "Add to SAP"
2. Use stopwatch on phone/watch
3. Compare real time vs displayed time after 10 seconds

**Expected:** Within ±0.5 seconds

### 4.4 Warning Timing
1. Click "Add to SAP" (with slow SAP response)
2. Watch timer closely
3. Note exact second warning appears

**Expected:** Warning appears between 15.0s and 15.1s

### 4.5 Responsive Design
Test on different screen sizes:
1. Desktop (1920x1080)
   - [ ] Overlay covers full screen
   - [ ] Modal centered
2. Laptop (1366x768)
   - [ ] Modal fully visible
   - [ ] No scrolling needed
3. Tablet (768x1024)
   - [ ] Modal scales appropriately
   - [ ] Text readable
4. Mobile (375x667)
   - [ ] Modal fits screen
   - [ ] Touch targets adequate

---

## Test 5: Browser Compatibility

### 5.1 Chrome/Edge (Chromium)
- [ ] All animations work
- [ ] No console errors
- [ ] AJAX request succeeds
- [ ] Auto-reload works

### 5.2 Firefox
- [ ] All animations work
- [ ] No console errors
- [ ] AJAX request succeeds
- [ ] Auto-reload works

### 5.3 Safari (if available)
- [ ] All animations work
- [ ] No console errors
- [ ] AJAX request succeeds
- [ ] Auto-reload works

---

## Test 6: Console Testing

### 6.1 Manual Control
Open browser console on admin page and test:

```javascript
// Test 1: Show loading
SAPLoadingScreen.show();
// Verify: Overlay visible, spinner rotating, timer counting

// Test 2: Hide loading
SAPLoadingScreen.hide();
// Verify: Overlay hidden, timer stopped

// Test 3: Success result
SAPLoadingScreen.show();
setTimeout(() => {
    SAPLoadingScreen.showResult(true, "Test success message", "SO-99999");
}, 3000);
// Verify: Shows success after 3s, auto-reloads after 2s

// Test 4: Error result
SAPLoadingScreen.show();
setTimeout(() => {
    SAPLoadingScreen.showResult(false, "Test error message");
}, 2000);
// Verify: Shows error after 2s, auto-hides after 5s

// Test 5: Long wait with warning
SAPLoadingScreen.show();
// Wait and observe: Warning appears at 15s, keeps counting
setTimeout(() => {
    SAPLoadingScreen.hide();
}, 20000);
```

### 6.2 Check Object State
```javascript
// Inspect loading screen object
console.log(SAPLoadingScreen);

// Check properties
console.log(SAPLoadingScreen.overlay);        // jQuery object
console.log(SAPLoadingScreen.startTime);      // null or timestamp
console.log(SAPLoadingScreen.elapsedTimer);   // null or interval ID
console.log(SAPLoadingScreen.timeoutWarningShown); // boolean
```

---

## Test 7: Network Analysis

### 7.1 AJAX Request Inspection
1. Open DevTools > Network tab
2. Click "Add to SAP"
3. Find POST request to `post-to-sap/`

**Verify Request:**
- [ ] Method: POST
- [ ] Headers include: X-CSRFToken
- [ ] Headers include: X-Requested-With: XMLHttpRequest
- [ ] Content-Type: application/x-www-form-urlencoded

**Verify Response (Success):**
- [ ] Status: 200 OK
- [ ] Content-Type: application/json
- [ ] Body:
```json
{
  "success": true,
  "message": "Order #32 posted successfully to SAP",
  "doc_entry": 12345,
  "doc_num": "SO-12345"
}
```

**Verify Response (Error):**
- [ ] Status: 400 or 500
- [ ] Content-Type: application/json
- [ ] Body:
```json
{
  "success": false,
  "error": "Error message here"
}
```

### 7.2 Timing Breakdown
In Network tab, check timing for successful request:
- [ ] Queuing: < 10ms
- [ ] DNS Lookup: < 50ms (or cached)
- [ ] Initial Connection: < 100ms
- [ ] Waiting (TTFB): 10-20 seconds (SAP processing)
- [ ] Content Download: < 50ms

---

## Test 8: Edge Cases

### 8.1 Rapid Clicks
1. Click "Add to SAP" button
2. Immediately click it again (while loading)

**Expected:**
- [ ] Second click has no effect (button inside overlay, not clickable)
- [ ] Only one AJAX request sent

### 8.2 Page Navigation During Loading
1. Click "Add to SAP"
2. While loading, click browser back button

**Expected:**
- [ ] Request continues in background
- [ ] Previous page loads
- [ ] No errors in console

### 8.3 Browser Tab Switch
1. Click "Add to SAP"
2. Switch to different browser tab
3. Wait 20 seconds
4. Switch back

**Expected:**
- [ ] Loading screen still visible
- [ ] Timer showing correct elapsed time
- [ ] Result displayed when ready

### 8.4 Slow Network
1. Open DevTools > Network tab
2. Set throttling to "Slow 3G"
3. Click "Add to SAP"

**Expected:**
- [ ] Loading screen appears immediately (not affected by throttling)
- [ ] Request takes much longer
- [ ] Warning appears at 15s
- [ ] Eventually completes or times out
- [ ] Result displayed correctly

---

## Troubleshooting

### Issue: Loading screen doesn't appear
**Check:**
1. Browser console for JavaScript errors
2. jQuery loaded: Type `typeof jQuery` in console (should return "function")
3. SAPLoadingScreen object exists: Type `SAPLoadingScreen` in console
4. CSS loaded correctly (check DevTools > Elements > Styles)

**Fix:**
- Clear browser cache and reload
- Verify template extends base correctly
- Check {% load static %} present

### Issue: Spinner not rotating
**Check:**
1. DevTools > Elements > find `.sap-spinner`
2. Check computed styles for `animation` property
3. Browser supports CSS animations

**Fix:**
- Try different browser
- Check CSS syntax in template
- Verify no conflicting styles

### Issue: Timer not updating
**Check:**
1. Console for JavaScript errors
2. `SAPLoadingScreen.elapsedTimer` is set (not null)
3. `setInterval` working in browser

**Fix:**
- Reload page
- Check `startElapsedTimer()` being called
- Verify no exceptions in timer function

### Issue: AJAX request fails
**Check:**
1. Network tab shows request
2. Status code and response
3. CSRF token present in headers
4. Django server logs

**Fix:**
- Verify CSRF token: `$('[name=csrfmiddlewaretoken]').val()`
- Check Django middleware includes CSRF
- Verify URL is correct

### Issue: No auto-reload after success
**Check:**
1. Console for errors
2. `response.success` is true
3. `window.location.reload()` being called

**Fix:**
- Test manually: `window.location.reload()`
- Check browser blocks reload (popup blocker?)
- Verify success handler logic

---

## Performance Benchmarks

Expected performance metrics:

| Metric | Target | Acceptable | Poor |
|--------|--------|------------|------|
| Load time | < 50ms | < 100ms | > 100ms |
| FPS | 60 | 55-59 | < 55 |
| Timer accuracy | ±0.1s | ±0.5s | > ±0.5s |
| Warning trigger | 15.0-15.1s | 15.0-15.5s | > 15.5s |
| CSS size | < 3KB | < 5KB | > 5KB |
| JS size | < 4KB | < 6KB | > 6KB |

---

## Automated Testing (Optional)

### Selenium Test Script (Python)
```python
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time

# Setup
driver = webdriver.Chrome()
driver.get('http://localhost:8000/admin/FieldAdvisoryService/salesorder/32/change/')

# Login (if needed)
# driver.find_element(By.NAME, 'username').send_keys('admin')
# driver.find_element(By.NAME, 'password').send_keys('password')
# driver.find_element(By.CSS_SELECTOR, 'input[type="submit"]').click()

# Test 1: Button click shows overlay
button = driver.find_element(By.CSS_SELECTOR, 'a[href*="post-to-sap"]')
button.click()

overlay = WebDriverWait(driver, 1).until(
    EC.presence_of_element_located((By.ID, 'sapLoadingOverlay'))
)
assert 'active' in overlay.get_attribute('class'), "Overlay not active"
print("✓ Overlay appears")

# Test 2: Spinner visible
spinner = driver.find_element(By.CLASS_NAME, 'sap-spinner')
assert spinner.is_displayed(), "Spinner not visible"
print("✓ Spinner visible")

# Test 3: Timer counting
time.sleep(2)
timer = driver.find_element(By.ID, 'sapElapsedTime')
elapsed = timer.text
assert elapsed in ['1s', '2s', '3s'], f"Timer not counting: {elapsed}"
print(f"✓ Timer counting: {elapsed}")

# Test 4: Wait for result (success or error)
result = WebDriverWait(driver, 30).until(
    EC.presence_of_element_located((By.ID, 'sapResult'))
)
assert 'show' in result.get_attribute('class'), "Result not shown"
print("✓ Result displayed")

# Cleanup
driver.quit()
```

---

## Sign-Off Checklist

Before marking testing complete:

- [ ] Test 1: Visual Demo completed
- [ ] Test 2: Live Admin Interface completed
- [ ] Test 3: Error Scenarios completed
- [ ] Test 4: Performance & UI completed
- [ ] Test 5: Browser Compatibility completed
- [ ] Test 6: Console Testing completed
- [ ] Test 7: Network Analysis completed
- [ ] Test 8: Edge Cases completed
- [ ] All issues documented
- [ ] No critical bugs found
- [ ] Performance meets targets
- [ ] Ready for production

---

**Testing Status:** ⬜ Not Started | 🟨 In Progress | ✅ Complete  
**Tested By:** _______________  
**Date:** _______________  
**Sign-Off:** _______________
