"""
Test script to generate a PDF with Urdu text
This verifies that fonts and text reshaping work correctly
"""
import sys
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.lib.units import inch
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
import arabic_reshaper
from bidi.algorithm import get_display

# Register the Urdu font
if sys.platform.startswith('win'):
    font_path = r'C:\Windows\Fonts\NotoNastaliqUrdu-Regular.ttf'
else:
    font_path = '/usr/share/fonts/truetype/noto/NotoNastaliqUrdu-Regular.ttf'

try:
    pdfmetrics.registerFont(TTFont('NotoNastaliqUrdu', font_path))
    print(f"✓ Font registered: {font_path}")
except Exception as e:
    print(f"✗ Font registration failed: {e}")
    sys.exit(1)

# Create PDF
output_file = 'test_urdu_output.pdf'
c = canvas.Canvas(output_file, pagesize=letter)
width, height = letter

# Test text (the exact footer text from your model)
urdu_text = "معزز بزنس پارٹنر: آپ کے لیجر کی کاپی ارسال کی جا رہی ہے۔"

print(f"\nOriginal text: {urdu_text}")

# Reshape and apply bidi
try:
    reshaped_text = arabic_reshaper.reshape(urdu_text)
    bidi_text = get_display(reshaped_text)
    print(f"After reshaping: {bidi_text}")
except Exception as e:
    print(f"✗ Reshaping failed: {e}")
    bidi_text = urdu_text

# Draw text on PDF
c.setFont('NotoNastaliqUrdu', 14)
c.drawRightString(width - 1*inch, height - 2*inch, bidi_text)

# Also draw a simple test
c.drawRightString(width - 1*inch, height - 3*inch, "پاکستان")  # Pakistan in Urdu

# English for comparison
c.setFont('Helvetica', 12)
c.drawString(1*inch, height - 4*inch, "English text for comparison")

c.save()
print(f"\n✓ PDF created: {output_file}")
print("\nOpen the PDF and check if the Urdu text displays correctly.")
print("If you see proper Urdu characters, the libraries are working!")
