# Urdu Text Display Fix for General Ledger PDF

## Problem
Urdu text in General Ledger PDF is showing as boxes (■■■) instead of proper Urdu characters.

## Root Cause
Two critical components are missing:
1. **Arabic text processing libraries** (`arabic-reshaper` and `python-bidi`)
2. **Noto Nastaliq Urdu font** (optional but recommended)

## Diagnostic Results
- ✗ `arabic_reshaper` is NOT installed
- ✗ `python-bidi` is NOT installed  
- ✗ Noto Nastaliq Urdu font is missing
- ✓ Fallback fonts (Tahoma, Arial) are available

## Solution

### STEP 1: Install Required Python Libraries

**On Windows Server:**

```powershell
# Option 1: Install from requirements.txt (recommended)
cd "f:\samad\clone tarzan\django_web_portal\web_portal"
python -m pip install -r requirements.txt

# Option 2: Install only the required packages
python -m pip install arabic-reshaper==3.0.1 python-bidi==0.6.7
```

**Verification:**
```powershell
python -c "import arabic_reshaper; from bidi.algorithm import get_display; print('✓ Libraries installed successfully!')"
```

### STEP 2: Install Noto Nastaliq Urdu Font (Optional but Recommended)

This font provides the best Urdu text rendering quality.

**Download:**
1. Visit: https://fonts.google.com/noto/specimen/Noto+Nastaliq+Urdu
2. Click "Download family" button
3. Extract the downloaded ZIP file

**Install on Windows:**
1. Locate `NotoNastaliqUrdu-Regular.ttf` in the extracted folder
2. Right-click the font file → "Install" or "Install for all users"
3. The font will be copied to: `C:\Windows\Fonts\`

**Alternative Direct Download:**
- https://github.com/googlefonts/noto-fonts/raw/main/hinted/ttf/NotoNastaliqUrdu/NotoNastaliqUrdu-Regular.ttf

### STEP 3: Restart Django Server

After installing libraries and fonts, restart the Django development server:

```powershell
# Stop the current server (Ctrl+C in terminal)
# Then start again
python manage.py runserver
```

### STEP 4: Test PDF Generation

1. Go to Django Admin → General Ledger
2. Generate a new PDF
3. Open the PDF and check the footer text
4. Urdu text should now display correctly

## What Happens Without the Fix?

### Without arabic-reshaper & python-bidi:
- Urdu text shows as boxes (■■■) or garbled characters
- Right-to-left (RTL) text direction is broken
- Character joining is incorrect

### Without Noto Nastaliq Urdu font:
- System falls back to Tahoma font
- Basic Urdu characters may display but without proper Nastaliq calligraphy
- Some special characters might not render correctly

## Technical Details

### How the Fix Works:

1. **arabic-reshaper**: Reshapes Arabic/Urdu characters for proper joining
   - Converts characters to their correct positional forms (initial, medial, final, isolated)
   
2. **python-bidi**: Handles bidirectional text (RTL)
   - Reorders text for right-to-left display
   
3. **Font embedding**: Embeds font glyphs in PDF
   - Ensures text displays correctly on any system

### Code Location:
- Main PDF generation: `web_portal/general_ledger/views.py` (line 1472)
- Font registration: `web_portal/general_ledger/views.py` (lines 54-72)
- Footer text processing: `web_portal/general_ledger/views.py` (lines 1955-1962)

## Current Fallback Font Priority

The system tries fonts in this order:
1. **NotoNastaliqUrdu** (Best - proper Urdu/Nastaliq style) ← MISSING
2. **Tahoma** (Good - has Urdu support) ← CURRENTLY USED
3. **Arial** (Limited - basic Unicode)
4. **Calibri** (Limited - basic Unicode)
5. **TimesNewRoman** (Poor - limited Urdu support)
6. **Helvetica** (Worst - no Urdu support)

## Troubleshooting

### Issue: Libraries won't install
```powershell
# Try upgrading pip first
python -m pip install --upgrade pip

# Then install with verbose output
python -m pip install -v arabic-reshaper python-bidi
```

### Issue: Font not showing up after installation
1. Verify font is in: `C:\Windows\Fonts\`
2. Restart ALL Python processes (Django server, Celery, etc.)
3. Clear browser cache
4. Regenerate the PDF

### Issue: Still showing boxes after fix
1. Verify libraries are installed:
   ```powershell
   python -c "import arabic_reshaper, bidi; print('OK')"
   ```

2. Check font registration in Django logs:
   ```
   # Look for: "Connecting to HANA" or font-related messages
   ```

3. Try regenerating with debug mode:
   - Set `DEBUG=True` in settings
   - Check console for errors

### Issue: Slow PDF generation
- Normal with proper font embedding
- First PDF generation might take 2-3 seconds
- Subsequent generations are cached and faster

## Verification Commands

Run these commands to verify everything is working:

```powershell
# Check diagnostic tool
cd "f:\samad\clone tarzan\django_web_portal\web_portal"
python general_ledger\check_urdu_fonts.py

# Verify libraries
python -c "import arabic_reshaper; print('✓ arabic-reshaper')"
python -c "from bidi.algorithm import get_display; print('✓ python-bidi')"

# Check font file
if (Test-Path "C:\Windows\Fonts\NotoNastaliqUrdu-Regular.ttf") { 
    Write-Host "✓ Noto Nastaliq Urdu font installed" 
} else { 
    Write-Host "✗ Font not found" 
}
```

## Quick Fix Script

Save this as `install_urdu_support.ps1` and run in PowerShell:

```powershell
# Navigate to project directory
cd "f:\samad\clone tarzan\django_web_portal\web_portal"

# Install Python libraries
Write-Host "Installing Python libraries..." -ForegroundColor Yellow
python -m pip install arabic-reshaper==3.0.1 python-bidi==0.6.7

# Verify installation
Write-Host "Verifying installation..." -ForegroundColor Yellow
python -c "import arabic_reshaper; from bidi.algorithm import get_display; print('✓ Libraries OK')"

# Check font
if (Test-Path "C:\Windows\Fonts\NotoNastaliqUrdu-Regular.ttf") {
    Write-Host "✓ Font already installed" -ForegroundColor Green
} else {
    Write-Host "⚠ Font not installed. Download from:" -ForegroundColor Yellow
    Write-Host "  https://fonts.google.com/noto/specimen/Noto+Nastaliq+Urdu" -ForegroundColor Cyan
}

Write-Host "`n✓ Installation complete! Restart Django server." -ForegroundColor Green
```

## Support

If issues persist after following this guide:
1. Run the diagnostic tool: `python general_ledger\check_urdu_fonts.py`
2. Check Django error logs
3. Verify server has internet access for pip install
4. Contact system administrator for font installation permissions

## Additional Notes

- **Production servers**: Install fonts system-wide with admin privileges
- **Docker containers**: Add fonts to container image
- **Cloud deployments**: Include fonts in deployment package
- **Multiple servers**: Install on ALL servers serving PDF requests
