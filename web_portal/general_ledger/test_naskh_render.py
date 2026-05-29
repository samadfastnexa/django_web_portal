"""
One-off render test: prove Noto Naskh Arabic renders the actual Urdu
footer text correctly via the same pipeline views.py uses.
Run from the web_portal directory:
    python general_ledger/test_naskh_render.py
Writes test_naskh_output.pdf in the cwd.
"""
import os
import sys

from reportlab.lib.pagesizes import landscape, letter
from reportlab.lib import colors
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas
from reportlab.lib.utils import simpleSplit

import arabic_reshaper
from bidi.algorithm import get_display

FONT_PATH = os.path.join(os.path.dirname(__file__), 'fonts', 'NotoNaskhArabic-Regular.ttf')
FONT_NAME = 'NotoNaskhArabic'
OUT_PATH = os.path.abspath('test_naskh_output.pdf')

URDU_LINES = [
    'معزز بزنس پارٹنر: آپ کے لیجر کی کاپی ارسال کی جا رہی ہے۔ '
    'اسکو اپنے کھاتے کے مطابق چیک کر کے بیلنس کی تصدیق کر دیں۔',
    'دستخط اور مہر لازمی ثبت فرمائیں۔ اگر کسی بھی متم کا فرق ہوتو اسی لیجر کے اوپر '
    'نوٹ فرما دیں تا کہ درستگی ہو سکے۔ بصورت دیگر کمپنی کسی کلیم کی ذمہ دارنہ ہوگی',
    'مزید برآں !',
    'میں کمپنی کے اس لیجر بیلنس کے ساتھ متفق ہوں اور میرا '
    '....................................... کے ساتھ کوئی ذاتی لین دین نہیں ہے',
]

pdfmetrics.registerFont(TTFont(FONT_NAME, FONT_PATH))

reshaper = arabic_reshaper.ArabicReshaper(configuration={
    'language': 'Urdu',
    'support_ligatures': True,
    'delete_harakat': False,
})

shaped = []
for line in URDU_LINES:
    reshaped = reshaper.reshape(line)
    shaped.append(get_display(reshaped))

c = canvas.Canvas(OUT_PATH, pagesize=landscape(letter))
W, H = landscape(letter)
margin = 30
font_size = 12
line_gap = 6
y = H - margin - font_size

c.setFont('Helvetica-Bold', 14)
c.drawString(margin, y, 'Sample render: Noto Naskh Arabic + Urdu footer text')
y -= 30

c.setFillColor(colors.HexColor('#f8f9ff'))
c.rect(margin, margin, W - 2 * margin, y - margin, fill=1, stroke=0)

c.setFillColor(colors.HexColor('#1e293b'))
c.setFont(FONT_NAME, font_size)

text_x = margin + 10
max_w = W - 2 * margin - 20

for s in shaped:
    wrapped = simpleSplit(s, FONT_NAME, font_size, max_w)
    for sub in wrapped:
        c.drawString(text_x, y, sub)
        y -= font_size * 1.5
    y -= line_gap

c.showPage()
c.save()
print(f'wrote {OUT_PATH}')
