from django.db import models


class LedgerSettings(models.Model):
    """
    Singleton model – only one row (pk=1) should ever exist.
    All values here are used dynamically when generating the General Ledger PDF.
    Manage from Django Admin → General Ledger → Ledger Settings.
    """

    # ── Header ────────────────────────────────────────────────────────────────
    group_name = models.CharField(
        max_length=200,
        default='Four Brothers Group',
        verbose_name='Group Name',
        help_text='Displayed as the top-left bold heading in the PDF header.',
    )
    company_name = models.CharField(
        max_length=300,
        blank=True,
        default='FOUR BROTHERS BIOLOGIC AG PAKISTAN',
        verbose_name='Company Name',
        help_text='Displayed below the group name in the PDF header (bold, larger font). '
                  'Leave blank to use the company name resolved from SAP.',
    )

    # ── Report ────────────────────────────────────────────────────────────────
    report_title = models.CharField(
        max_length=200,
        default='General Ledger',
        verbose_name='Report Title',
        help_text='Title displayed in the PDF header (e.g. "General Ledger").',
    )

    # ── Images ────────────────────────────────────────────────────────────────
    smart_stamp_image = models.ImageField(
        upload_to='ledger_settings/',
        blank=True, null=True,
        verbose_name='Smart Agriculture Stamp Image',
        help_text='Circular stamp shown at top-right of the PDF. '
                  'Recommended size: 150×150 px PNG with transparent background.',
    )
    sap_logo_image = models.ImageField(
        upload_to='ledger_settings/',
        blank=True, null=True,
        verbose_name='SAP Logo Image',
        help_text='Optional: upload a real SAP logo PNG/JPG. '
                  'If left empty the blue SAP badge is drawn automatically. '
                  'Recommended size: ~110×55 px.',
    )

    # ── Table Colors ──────────────────────────────────────────────────────────
    table_header_bg_color = models.CharField(
        max_length=20, default='#ffffff',
        verbose_name='Table Header Background Color',
        help_text='Hex color for the column-header row background (e.g. #ffffff for white).',
    )
    table_header_text_color = models.CharField(
        max_length=20, default='#000000',
        verbose_name='Table Header Text Color',
        help_text='Hex color for the column-header text (e.g. #000000 for black).',
    )
    territory_row_bg_color = models.CharField(
        max_length=20, default='#f1f5f9',
        verbose_name='Territory Row Background Color',
        help_text='Hex color for territory grouping row background.',
    )
    closing_balance_bg_color = models.CharField(
        max_length=20, default='#f1f5f9',
        verbose_name='Closing Balance Row Background Color',
        help_text='Hex color for the per-BP closing balance row.',
    )
    grand_total_bg_color = models.CharField(
        max_length=20, default='#e2e8f0',
        verbose_name='Grand Total Row Background Color',
        help_text='Hex color for the grand total row.',
    )
    grid_color = models.CharField(
        max_length=20, default='#d1d5db',
        verbose_name='Grid / Border Color',
        help_text='Hex color for table grid lines.',
    )

    # ── Font Sizes ──────────────────────────────────────────────────────────
    font_size_group_name = models.PositiveSmallIntegerField(
        default=11,
        verbose_name='Font Size — Group Name',
        help_text='Font size (pt) for the group name in the PDF header (e.g. 11).',
    )
    font_size_company_name = models.PositiveSmallIntegerField(
        default=13,
        verbose_name='Font Size — Company Name',
        help_text='Font size (pt) for the company name in the PDF header (e.g. 13).',
    )
    font_size_report_title = models.PositiveSmallIntegerField(
        default=10,
        verbose_name='Font Size — Report Title',
        help_text='Font size (pt) for the report title line (e.g. 10).',
    )
    font_size_dates = models.PositiveSmallIntegerField(
        default=9,
        verbose_name='Font Size — Date Range',
        help_text='Font size (pt) for the From/To date range line (e.g. 9).',
    )
    font_size_table_header = models.PositiveSmallIntegerField(
        default=8,
        verbose_name='Font Size — Table Header Row',
        help_text='Font size (pt) for the table column-header row (e.g. 8).',
    )
    font_size_table_data = models.PositiveSmallIntegerField(
        default=8,
        verbose_name='Font Size — Table Data Rows',
        help_text='Font size (pt) for table data rows (e.g. 8).',
    )

    # ── Urdu Footer ───────────────────────────────────────────────────────────
    footer_text = models.TextField(
        blank=True,
        default=(
            'معزز بزنس پارٹنر: آپ کے لیجر کی کاپی ارسال کی جا رہی ہے۔ '
            'اسکو اپنے کھاتے کے مطابق چیک کر کے بیلنس کی تصدیق کر دیں۔\n'
            'دستخط اور مہر لازمی ثبت فرمائیں۔ اگر کسی بھی متم کا فرق ہوتو اسی لیجر کے اوپر '
            'نوٹ فرما دیں تا کہ درستگی ہو سکے۔ بصورت دیگر کمپنی کسی کلیم کی ذمہ دارنہ ہوگی\n'
            'مزید برآں !\n'
            'میں کمپنی کے اس لیجر بیلنس کے ساتھ متفق ہوں اور میرا '
            '....................................... کے ساتھ کوئی ذاتی لین دین نہیں ہے'
        ),
        verbose_name='Urdu Footer Text',
        help_text='Each line is printed as a separate paragraph in the PDF footer. Use Enter/Return to start a new paragraph.',
    )

    # ── Meta ──────────────────────────────────────────────────────────────────
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Ledger Settings'
        verbose_name_plural = 'Ledger Settings'

    def __str__(self):
        return 'General Ledger PDF Settings'

    def save(self, *args, **kwargs):
        # Enforce singleton: always save as pk=1
        self.pk = 1
        super().save(*args, **kwargs)

    @classmethod
    def get(cls):
        """Return the singleton settings row, creating it with defaults if missing."""
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj

    def footer_lines(self):
        """Return a list of non-empty footer paragraphs (split by newline)."""
        return [line for line in (self.footer_text or '').splitlines() if line and line.strip()]
