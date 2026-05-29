Bundled Urdu fonts for ReportLab PDF generation
================================================

REQUIRED FONT (this one actually renders correctly with ReportLab):

  NotoNaskhArabic-Regular.ttf   <-- DOWNLOAD AND PLACE THIS HERE

Get it from:
  https://fonts.google.com/noto/specimen/Noto+Naskh+Arabic
or direct:
  wget https://github.com/notofonts/arabic/raw/main/fonts/NotoNaskhArabic/hinted/ttf/NotoNaskhArabic-Regular.ttf

WHY NASKH AND NOT NASTALIQ?
---------------------------
ReportLab cannot perform OpenType GSUB/GPOS shaping. Nastaliq fonts
(NotoNastaliqUrdu, Jameel Noori Nastaleeq) depend on that pipeline — their
glyphs are blank without it. The result is a footer with only punctuation
visible, the Urdu letters disappear.

Naskh-style fonts (NotoNaskhArabic, Amiri) ship precomposed glyphs for
the Arabic Presentation Forms block (U+FE70-FEFF). arabic-reshaper produces
those codepoints, and ReportLab draws them directly. The text is fully
readable Urdu in Naskh style (the same style Tahoma/Arial use on Windows,
which is why local PDFs already looked fine).

You can leave NotoNastaliqUrdu-Regular.ttf in this directory — the code
will skip it and prefer the Naskh font.

After placing the file here, restart Django. The startup log should show:

  [General Ledger] Successfully registered Urdu font: NotoNaskhArabic
  from .../general_ledger/fonts/NotoNaskhArabic-Regular.ttf

OPTIONAL: TRUE NASTALIQ
-----------------------
If you want the calligraphic Nastaliq look, you would need to either:
  (a) switch the PDF library to WeasyPrint (uses HarfBuzz, supports OpenType
      shaping) — major refactor.
  (b) source a "Jameel Noori Nastaleeq" TTF that has precomposed presentation
      forms — distributed by some Pakistani sites, not free, license unclear.

For most cases Naskh is the practical answer.

License
-------
Noto fonts are released under the SIL Open Font License (OFL).
