"""
Diagnostic script to check Urdu font availability for PDF generation
Works on both Windows and Linux systems
"""
import os
import sys
import platform

def check_fonts():
    """Check which fonts are available for Urdu PDF generation"""
    print("=" * 70)
    print("URDU FONT DIAGNOSTIC TOOL")
    print("=" * 70)
    print()
    print(f"Platform: {platform.system()} ({platform.platform()})")
    print(f"Python: {sys.version}")
    print()
    
    # Project-bundled font dir (preferred — checked first by views.py)
    bundled_dir = os.path.join(os.path.dirname(__file__), 'fonts')
    bundled_candidates = [
        ('NotoNastaliqUrdu', os.path.join(bundled_dir, 'NotoNastaliqUrdu-Regular.ttf')),
        ('NotoNaskhArabic',  os.path.join(bundled_dir, 'NotoNaskhArabic-Regular.ttf')),
    ]

    # List of fonts to check based on platform
    if sys.platform.startswith('win'):
        # Windows font paths
        system_candidates = [
            ('NotoNastaliqUrdu', r'C:\Windows\Fonts\NotoNastaliqUrdu-Regular.ttf'),
            ('JameelNooriNastaleeq', r'C:\Windows\Fonts\Jameel Noori Nastaleeq.ttf'),
            ('Tahoma',          r'C:\Windows\Fonts\tahoma.ttf'),
            ('Arial',           r'C:\Windows\Fonts\arial.ttf'),
            ('Calibri',         r'C:\Windows\Fonts\calibri.ttf'),
            ('TimesNewRoman',   r'C:\Windows\Fonts\times.ttf'),
        ]
    else:
        # Linux/Unix font paths — opentype path added because apt puts it there
        system_candidates = [
            ('NotoNastaliqUrdu', '/usr/share/fonts/opentype/noto/NotoNastaliqUrdu-Regular.ttf'),
            ('NotoNastaliqUrdu', '/usr/share/fonts/truetype/noto/NotoNastaliqUrdu-Regular.ttf'),
            ('NotoNastaliqUrdu', '/usr/share/fonts/noto/NotoNastaliqUrdu-Regular.ttf'),
            ('NotoNaskhArabic',  '/usr/share/fonts/truetype/noto/NotoNaskhArabic-Regular.ttf'),
            ('NotoNaskhArabic',  '/usr/share/fonts/opentype/noto/NotoNaskhArabic-Regular.ttf'),
            ('NotoSans',         '/usr/share/fonts/truetype/noto/NotoSans-Regular.ttf'),
            ('DejaVuSans',       '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'),
            ('LiberationSans',   '/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf'),
            ('FreeSans',         '/usr/share/fonts/truetype/freefont/FreeSans.ttf'),
        ]

    font_candidates = bundled_candidates + system_candidates

    # Recursive scan for NotoNastaliqUrdu under common font roots (Linux)
    if not sys.platform.startswith('win'):
        import glob
        for pat in (
            '/usr/share/fonts/**/NotoNastaliqUrdu*.ttf',
            '/usr/share/fonts/**/NotoNastaliqUrdu*.otf',
            '/usr/local/share/fonts/**/NotoNastaliqUrdu*.ttf',
            '/root/.fonts/**/NotoNastaliqUrdu*.ttf',
        ):
            for match in glob.glob(pat, recursive=True):
                font_candidates.append(('NotoNastaliqUrdu', match))

        # fc-match fallback
        try:
            import subprocess
            out = subprocess.run(
                ['fc-match', '-f', '%{file}', 'Noto Nastaliq Urdu'],
                capture_output=True, text=True, timeout=5,
            )
            fc_path = (out.stdout or '').strip()
            if fc_path and os.path.exists(fc_path):
                print(f"  (fc-match reports: {fc_path})")
                font_candidates.append(('NotoNastaliqUrdu', fc_path))
        except Exception as e:
            print(f"  (fc-match unavailable: {e})")
    
    print("1. Checking font files on disk:")
    print("-" * 70)
    found_fonts = []
    for font_name, font_path in font_candidates:
        exists = os.path.exists(font_path)
        status = "✓ FOUND" if exists else "✗ MISSING"
        print(f"  {status:10} {font_name:20} -> {font_path}")
        if exists:
            found_fonts.append((font_name, font_path))
    print()
    
    # Check reportlab availability
    print("2. Checking reportlab installation:")
    print("-" * 70)
    try:
        from reportlab.pdfbase import pdfmetrics
        from reportlab.pdfbase.ttfonts import TTFont
        print("  ✓ reportlab is installed")
        
        # Try to register fonts
        print()
        print("3. Attempting to register fonts with reportlab:")
        print("-" * 70)
        registered_font = None
        for font_name, font_path in found_fonts:
            try:
                if font_name not in pdfmetrics.getRegisteredFontNames():
                    pdfmetrics.registerFont(TTFont(font_name, font_path))
                print(f"  ✓ Successfully registered: {font_name}")
                if registered_font is None:
                    registered_font = font_name
            except Exception as e:
                print(f"  ✗ Failed to register {font_name}: {str(e)}")
        
        print()
        print("4. Currently registered fonts in reportlab:")
        print("-" * 70)
        all_fonts = pdfmetrics.getRegisteredFontNames()
        for font in sorted(all_fonts):
            marker = "  ← SELECTED" if font == registered_font else ""
            print(f"  - {font}{marker}")
        
    except ImportError:
        print("  ✗ reportlab is NOT installed")
        print("  Install with: pip install reportlab")
    
    # Check arabic reshaper and bidi
    print()
    print("5. Checking Arabic text processing libraries:")
    print("-" * 70)
    try:
        import arabic_reshaper
        print("  ✓ arabic_reshaper is installed")
    except ImportError:
        print("  ✗ arabic_reshaper is NOT installed")
        print("  Install with: pip install arabic-reshaper")
    
    try:
        from bidi.algorithm import get_display
        print("  ✓ python-bidi is installed")
    except ImportError:
        print("  ✗ python-bidi is NOT installed")
        print("  Install with: pip install python-bidi")
    
    print()
    print("=" * 70)
    print("RECOMMENDATIONS:")
    print("=" * 70)
    
    if not any(os.path.exists(path) for _, path in font_candidates):
        print("⚠ NO FONTS FOUND!")
        print()
        if sys.platform.startswith('win'):
            print("Download and install Noto Nastaliq Urdu font:")
            print("1. Visit: https://fonts.google.com/noto/specimen/Noto+Nastaliq+Urdu")
            print("2. Download the font family")
            print("3. Extract and install NotoNastaliqUrdu-Regular.ttf to:")
            print("   C:\\Windows\\Fonts\\")
        else:
            print("Install Noto Nastaliq Urdu font on Linux:")
            print("Option 1 - Package manager (Ubuntu/Debian):")
            print("  sudo apt-get install fonts-noto-nastaliq-urdu")
            print()
            print("Option 2 - Manual download:")
            print("  wget https://github.com/googlefonts/noto-fonts/raw/main/hinted/ttf/NotoNastaliqUrdu/NotoNastaliqUrdu-Regular.ttf")
            print("  sudo mkdir -p /usr/share/fonts/truetype/noto")
            print("  sudo cp NotoNastaliqUrdu-Regular.ttf /usr/share/fonts/truetype/noto/")
            print("  sudo fc-cache -f -v")
        print()
    elif sys.platform.startswith('win') and not os.path.exists(r'C:\Windows\Fonts\NotoNastaliqUrdu-Regular.ttf'):
        print("⚠ Using fallback font (may not display Urdu correctly)")
        print()
        print("For best results, install Noto Nastaliq Urdu font:")
        print("1. Visit: https://fonts.google.com/noto/specimen/Noto+Nastaliq+Urdu")
        print("2. Download the font family")
        print("3. Extract and install NotoNastaliqUrdu-Regular.ttf to:")
        print("   C:\\Windows\\Fonts\\")
        print()
    elif not sys.platform.startswith('win') and not any(os.path.exists(p) for n, p in font_candidates if 'NotoNastaliq' in n):
        print("⚠ Using fallback font (may not display Urdu correctly)")
        print()
        print("For best results, install Noto Nastaliq Urdu font on Linux:")
        print("Run: sudo apt-get install fonts-noto-nastaliq-urdu")
        print("Or see: general_ledger/LINUX_SERVER_FIX.md")
        print()
    else:
        print("✓ Noto Nastaliq Urdu font is installed!")
        print("  This is the best font for Urdu text in PDFs.")
        print()
        print("If you still see boxes (■■■) in PDF:")
        print("1. Make sure reportlab can read the font file")
        print("2. Check that arabic_reshaper and python-bidi are installed")
        print("3. Restart the Django server after installing fonts/libraries")
        print()

if __name__ == '__main__':
    check_fonts()
