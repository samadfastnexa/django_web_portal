from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name='LedgerSettings',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('group_name', models.CharField(default='Four Brothers Group', max_length=200, verbose_name='Group Name')),
                ('company_name', models.CharField(blank=True, default='FOUR BROTHERS BIOLOGIC AG PAKISTAN', max_length=300, verbose_name='Company Name')),
                ('smart_stamp_image', models.ImageField(blank=True, null=True, upload_to='ledger_settings/', verbose_name='Smart Agriculture Stamp Image')),
                ('footer_line_1', models.TextField(blank=True, default='معزز بزنس پارٹنر: آپ کے لیجر کی کاپی ارسال کی جا رہی ہے۔ اسکو اپنے کھاتے کے مطابق چیک کر کے بیلنس کی تصدیق کر دیں۔', verbose_name='Footer Line 1')),
                ('footer_line_2', models.TextField(blank=True, default='دستخط اور مہر لازمی ثبت فرمائیں۔ اگر کسی بھی متم کا فرق ہوتو اسی لیجر کے اوپر نوٹ فرما دیں تا کہ درستگی ہو سکے۔ بصورت دیگر کمپنی کسی کلیم کی ذمہ دارنہ ہوگی', verbose_name='Footer Line 2')),
                ('footer_line_3', models.TextField(blank=True, default='مزید برآں !', verbose_name='Footer Line 3')),
                ('footer_line_4', models.TextField(blank=True, default='میں کمپنی کے اس لیجر بیلنس کے ساتھ متفق ہوں اور میرا ....................................... کے ساتھ کوئی ذاتی لین دین نہیں ہے', verbose_name='Footer Line 4')),
                ('footer_line_5', models.TextField(blank=True, default='', verbose_name='Footer Line 5 (optional)')),
                ('footer_line_6', models.TextField(blank=True, default='', verbose_name='Footer Line 6 (optional)')),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={
                'verbose_name': 'Ledger Settings',
                'verbose_name_plural': 'Ledger Settings',
            },
        ),
    ]
