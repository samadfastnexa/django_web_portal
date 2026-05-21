Bundled Urdu fonts for ReportLab PDF generation
================================================

Drop the following TTF file(s) into this directory to guarantee Urdu rendering
on ANY server, regardless of system fonts:

  - NotoNastaliqUrdu-Regular.ttf   (preferred — Nastaliq style)
  - NotoNaskhArabic-Regular.ttf    (optional fallback — Naskh style)

Why bundle?
-----------
The Linux apt package `fonts-noto-nastaliq-urdu` installs the font at
/usr/share/fonts/opentype/noto/ on some distros, /usr/share/fonts/truetype/noto/
on others, and somewhere else entirely on a few. Bundling the TTF here removes
that ambiguity.

Where to get it
---------------
Official Google Fonts release:
  https://fonts.google.com/noto/specimen/Noto+Nastaliq+Urdu

Direct download (single file):
  wget https://github.com/googlefonts/noto-fonts/raw/main/hinted/ttf/NotoNastaliqUrdu/NotoNastaliqUrdu-Regular.ttf

After placing the file here, restart the Django server. The startup log should
show:
  [General Ledger] Successfully registered Urdu font: NotoNastaliqUrdu from .../general_ledger/fonts/NotoNastaliqUrdu-Regular.ttf

License
-------
Noto fonts are released under the SIL Open Font License (OFL).
