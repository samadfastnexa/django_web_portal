from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('general_ledger', '0002_ledgersettings_company_name'),
    ]

    operations = [
        # Add the new single footer_text field
        migrations.AddField(
            model_name='ledgersettings',
            name='footer_text',
            field=models.TextField(
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
            ),
        ),
        # Remove the old individual line fields
        migrations.RemoveField(model_name='ledgersettings', name='footer_line_1'),
        migrations.RemoveField(model_name='ledgersettings', name='footer_line_2'),
        migrations.RemoveField(model_name='ledgersettings', name='footer_line_3'),
        migrations.RemoveField(model_name='ledgersettings', name='footer_line_4'),
        migrations.RemoveField(model_name='ledgersettings', name='footer_line_5'),
        migrations.RemoveField(model_name='ledgersettings', name='footer_line_6'),
    ]
