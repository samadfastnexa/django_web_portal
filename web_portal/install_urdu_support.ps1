# Urdu PDF Support Installation Script
# Run this script in PowerShell to install required libraries for Urdu text in PDFs

Write-Host "======================================================================" -ForegroundColor Cyan
Write-Host "  URDU PDF SUPPORT INSTALLER" -ForegroundColor Cyan
Write-Host "======================================================================" -ForegroundColor Cyan
Write-Host ""

# Change to project directory
$projectDir = "f:\samad\clone tarzan\django_web_portal\web_portal"
Write-Host "Navigating to project directory..." -ForegroundColor Yellow
cd $projectDir

# Step 1: Install Python libraries
Write-Host ""
Write-Host "Step 1: Installing Python libraries..." -ForegroundColor Yellow
Write-Host "  - arabic-reshaper (for character shaping)" -ForegroundColor Gray
Write-Host "  - python-bidi (for right-to-left text)" -ForegroundColor Gray
Write-Host ""

try {
    # Try installing with pip
    python -m pip install arabic-reshaper==3.0.1 python-bidi==0.6.7
    
    # Verify installation
    Write-Host ""
    Write-Host "Verifying installation..." -ForegroundColor Yellow
    python -c "import arabic_reshaper; from bidi.algorithm import get_display; print('SUCCESS')" 2>&1 | Out-Null
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host "  ✓ Libraries installed successfully!" -ForegroundColor Green
    } else {
        Write-Host "  ✗ Library installation failed" -ForegroundColor Red
        Write-Host "    Run manually: python -m pip install arabic-reshaper python-bidi" -ForegroundColor Yellow
    }
} catch {
    Write-Host "  ✗ Error during installation: $_" -ForegroundColor Red
}

# Step 2: Check font installation
Write-Host ""
Write-Host "Step 2: Checking Noto Nastaliq Urdu font..." -ForegroundColor Yellow

$fontPath = "C:\Windows\Fonts\NotoNastaliqUrdu-Regular.ttf"
if (Test-Path $fontPath) {
    Write-Host "  ✓ Noto Nastaliq Urdu font is already installed!" -ForegroundColor Green
} else {
    Write-Host "  ✗ Noto Nastaliq Urdu font is NOT installed" -ForegroundColor Red
    Write-Host ""
    Write-Host "  To install the font:" -ForegroundColor Yellow
    Write-Host "  1. Visit: https://fonts.google.com/noto/specimen/Noto+Nastaliq+Urdu" -ForegroundColor Cyan
    Write-Host "  2. Click 'Download family' button" -ForegroundColor Cyan
    Write-Host "  3. Extract the ZIP file" -ForegroundColor Cyan
    Write-Host "  4. Right-click 'NotoNastaliqUrdu-Regular.ttf' → Install" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "  Alternative: The system will use Tahoma font (acceptable quality)" -ForegroundColor Gray
}

# Step 3: Run diagnostic
Write-Host ""
Write-Host "Step 3: Running diagnostic tool..." -ForegroundColor Yellow
Write-Host ""
python general_ledger\check_urdu_fonts.py

# Final instructions
Write-Host ""
Write-Host "======================================================================" -ForegroundColor Cyan
Write-Host "  NEXT STEPS" -ForegroundColor Cyan
Write-Host "======================================================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "1. If Django server is running, restart it (Ctrl+C then start again)" -ForegroundColor Yellow
Write-Host "2. Generate a new General Ledger PDF from Django Admin" -ForegroundColor Yellow
Write-Host "3. Check that Urdu text in the footer displays correctly" -ForegroundColor Yellow
Write-Host ""
Write-Host "For detailed troubleshooting, see:" -ForegroundColor Gray
Write-Host "  general_ledger\URDU_PDF_FIX_GUIDE.md" -ForegroundColor Cyan
Write-Host ""
