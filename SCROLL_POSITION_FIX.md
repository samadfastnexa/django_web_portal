# Scroll Position Persistence - HANA Connect Admin

## Problem
When users change filters (period, region, zone, territory, etc.) in the HANA Connect admin, the page reloads and scrolls back to the top, causing frustration when viewing long data tables.

## Solution
Implemented a ScrollManager using `sessionStorage` that:
- ✅ Saves scroll position before filter form submission
- ✅ Restores scroll position after page reload
- ✅ Validates URL and timestamp to prevent stale restoration
- ✅ Works across all filter forms in HANA Connect

## How It Works

### 1. Save Scroll Position
When a filter form is submitted or dropdown changes:
```javascript
ScrollManager.save();
// Saves: { x, y, url, timestamp } to sessionStorage
```

### 2. Restore Scroll Position
On page load, attempts restoration at multiple intervals:
- Immediately on script load
- 0ms, 50ms, 100ms, 200ms, 400ms, 800ms after load
- After DOMContentLoaded event
- After window.load event (+ 100ms)

### 3. Validation
Only restores if:
- URL matches exactly (prevents cross-page restoration)
- Timestamp is recent (within 5 seconds)
- Not already restored (prevents duplicates)

### 4. Cleanup
After successful restoration, the stored position is cleared from sessionStorage.

## Features

### Smart Binding
Automatically binds to:
- All forms with `id*="filter-form"`
- All forms with `action*="hana-connect"`
- Specific dropdowns: `period`, `company_db`, `region`, `zone`, `territory`

### Console Logging
Debug messages show:
```
[ScrollManager] Saved scroll position: 842px
[ScrollManager] Bound 3 filter forms
[ScrollManager] Bound 5 filter dropdowns
[ScrollManager] Restored scroll to: 842px
```

### Multiple Restoration Attempts
Tries to restore at different times to handle:
- Fast page loads (0ms)
- Images loading (50-100ms)
- Tables rendering (200-400ms)
- Lazy-loaded content (800ms)

## Testing

### Test Procedure
1. Open browser Developer Console (F12)
2. Navigate to any HANA Connect report:
   ```
   http://localhost:8000/admin/hana-connect/?action=collection_vs_achievement&company_db=4B-AGRI_LIVE
   ```
3. Scroll down to any position (e.g., 500px down)
4. Change any filter:
   - Period: today → monthly
   - Region: Select a region
   - Zone: Select a zone
   - Territory: Select a territory
5. **Expected:** Page reloads and returns to the same scroll position
6. **Console should show:**
   ```
   [ScrollManager] Saved scroll position: 500px
   [ScrollManager] Restored scroll to: 500px
   ```

### Test Cases

#### ✅ Case 1: Period Filter Change
- Scroll to 500px
- Change period from "today" to "monthly"
- Page reloads
- **Expected:** Scroll restored to 500px

#### ✅ Case 2: Region/Zone/Territory Filter
- Scroll to 1000px
- Select a region
- Page reloads
- **Expected:** Scroll restored to 1000px

#### ✅ Case 3: Date Range Change
- Scroll to 300px
- Change start/end date
- Submit form
- **Expected:** Scroll restored to 300px

#### ✅ Case 4: Database Change
- Scroll to 700px
- Change company_db dropdown
- Page reloads
- **Expected:** Scroll restored to 700px

#### ❌ Case 5: Navigate to Different Action
- Scroll to 500px on `collection_vs_achievement`
- Click to navigate to `sales_vs_achievement_territory`
- Page loads
- **Expected:** Scroll NOT restored (different URL)

#### ❌ Case 6: Stale Data
- Save scroll position
- Wait 10 seconds
- Reload page
- **Expected:** Scroll NOT restored (timestamp > 5 seconds)

## Browser Compatibility

Works on:
- ✅ Chrome/Edge (Chromium)
- ✅ Firefox
- ✅ Safari
- ✅ Opera

Uses standard Web APIs:
- `sessionStorage` (supported by all modern browsers)
- `window.pageXOffset` / `window.pageYOffset`
- `document.documentElement.scrollLeft` / `scrollTop`
- `window.scrollTo(x, y)`

## Code Location

**File:** `web_portal/sap_integration/templates/admin/sap_integration/hana_connect.html`

**Lines:** ~2722-2810 (ScrollManager object and initialization)

## Debugging

### Enable Console Logging
Console logs are already included. Open Developer Console (F12) to see:
- When scroll is saved
- How many forms/dropdowns are bound
- When scroll is restored
- Why restoration was skipped (URL mismatch, stale data, etc.)

### Check sessionStorage
In Developer Console, run:
```javascript
JSON.parse(sessionStorage.getItem('hana_connect_scroll_position'))
```

Output example:
```json
{
  "x": 0,
  "y": 842,
  "url": "http://localhost:8000/admin/hana-connect/?action=collection_vs_achievement&company_db=4B-AGRI_LIVE&period=monthly",
  "timestamp": 1712476989234
}
```

### Manual Test
```javascript
// Save current scroll
ScrollManager.save();

// Check saved data
console.log(sessionStorage.getItem('hana_connect_scroll_position'));

// Restore scroll
ScrollManager.restore();
```

## Troubleshooting

### Issue: Scroll not being saved
**Cause:** Form not bound to ScrollManager
**Fix:** Check console for "Bound X filter forms" message
**Solution:** Ensure form has `id` containing "filter-form" or `action` containing "hana-connect"

### Issue: Scroll not being restored
**Possible causes:**
1. URL changed (different query parameters)
2. More than 5 seconds passed since save
3. sessionStorage was cleared
4. Page loaded too slowly (try increasing restoration attempts)

**Fix:** Check console for skip reason

### Issue: Scroll restores to wrong position
**Cause:** Content loaded after restoration
**Fix:** Increase final restoration delay from 100ms to 200ms:
```javascript
window.addEventListener('load', function() {
  setTimeout(function() {
    ScrollManager.restore();
  }, 200); // Increase this
});
```

## Performance Impact

**Minimal:**
- sessionStorage write: ~1ms
- sessionStorage read: <1ms
- Scroll restoration: <5ms
- Total overhead: <10ms per page load

**Storage:**
- ~150 bytes per saved position
- Automatically cleared after use
- Maximum 1 position stored at a time

## Future Enhancements

Possible improvements:
1. **Per-action storage keys** - Save different scroll positions for different actions
2. **Scroll anchoring** - Restore to specific table row instead of pixel position
3. **Smooth scrolling** - Animate scroll restoration
4. **User preference** - Allow users to enable/disable via settings

## Related Files

- `web_portal/sap_integration/templates/admin/sap_integration/hana_connect.html` - Template with ScrollManager
- `web_portal/sap_integration/views.py` - Backend views handling filter submissions

## Deployment

After updating the template:
```bash
# 1. Commit changes
git add web_portal/sap_integration/templates/admin/sap_integration/hana_connect.html
git commit -m "Add scroll position persistence for HANA Connect filters"

# 2. Push to server
git push origin master:server-branch

# 3. On server
git pull origin server-branch
sudo systemctl restart gunicorn

# 4. Clear browser cache (Ctrl+Shift+R)
```

## Notes

- No external libraries required (pure vanilla JavaScript)
- Works with existing filter infrastructure
- Does not interfere with other page functionality
- Gracefully degrades if sessionStorage unavailable
