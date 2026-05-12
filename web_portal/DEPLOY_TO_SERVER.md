# ⚠️ URGENT: Deploy to Linux Server - Urdu PDF Fix

## 🔍 Problem Confirmed
- ✅ Libraries installed on server: `arabic-reshaper`, `python-bidi`
- ❌ **Font missing**: No Urdu font on Linux server
- ❌ **Code only checks Windows paths**: `/usr/share/fonts/` not checked

## 🚀 Deployment Steps (Do This on Server)

### Step 1: Pull Updated Code

```bash
cd /home/www/django_web_portal
git pull origin main
```

**Files Updated:**
- `web_portal/general_ledger/views.py` - Now supports Linux font paths
- `web_portal/general_ledger/check_urdu_fonts.py` - Cross-platform diagnostic
- `web_portal/install_urdu_support_linux.sh` - Automated installer

### Step 2: Install Noto Nastaliq Urdu Font

**Quick One-Liner (as root):**
```bash
cd /tmp && wget -q https://github.com/googlefonts/noto-fonts/raw/main/hinted/ttf/NotoNastaliqUrdu/NotoNastaliqUrdu-Regular.ttf && sudo mkdir -p /usr/share/fonts/truetype/noto && sudo cp NotoNastaliqUrdu-Regular.ttf /usr/share/fonts/truetype/noto/ && sudo fc-cache -f -v
```

**OR use package manager:**
```bash
sudo apt-get update
sudo apt-get install -y fonts-noto-nastaliq-urdu
```

### Step 3: Verify Font Installation

```bash
# Check font is installed
fc-list | grep -i "noto nastaliq"

# Should output something like:
# /usr/share/fonts/truetype/noto/NotoNastaliqUrdu-Regular.ttf: Noto Nastaliq Urdu:style=Regular
```

### Step 4: Restart Django Server

```bash
# Stop existing server
pkill -f "manage.py runserver"

# Start fresh
cd /home/www/django_web_portal/web_portal
source /home/www/django_web_portal/venv/bin/activate
nohup python3 manage.py runserver 0.0.0.0:8000 &

# Check server started
tail -f nohup.out
# Look for: "Successfully registered Urdu font: NotoNastaliqUrdu"
```

### Step 5: Test PDF Generation

1. Go to Django Admin → General Ledger
2. Generate a new PDF
3. Check footer text shows correct Urdu: **معزز بزنس پارٹنر**

## 📊 What Changed in Code

**Before (Windows only):**
```python
_URDU_FONT_CANDIDATES = [
    ('NotoNastaliqUrdu', r'C:\Windows\Fonts\NotoNastaliqUrdu-Regular.ttf'),
    # ...
]
```

**After (Cross-platform):**
```python
if sys.platform.startswith('win'):
    # Windows font paths
else:
    # Linux font paths
    _URDU_FONT_CANDIDATES = [
        ('NotoNastaliqUrdu', '/usr/share/fonts/truetype/noto/NotoNastaliqUrdu-Regular.ttf'),
        # ... other Linux fonts
    ]
```

## ⏱️ Estimated Time: 5 minutes

1. Git pull: 10 seconds
2. Install font: 2 minutes  
3. Restart server: 30 seconds
4. Test: 1 minute

## 🆘 If It Doesn't Work

```bash
# 1. Check Django logs for errors
tail -f /home/www/django_web_portal/web_portal/nohup.out

# 2. Run diagnostic tool
cd /home/www/django_web_portal/web_portal
source /home/www/django_web_portal/venv/bin/activate
python3 general_ledger/check_urdu_fonts.py

# 3. Verify font file exists
ls -la /usr/share/fonts/truetype/noto/NotoNastaliqUrdu-Regular.ttf

# 4. Rebuild font cache
sudo fc-cache -f -v

# 5. Restart server completely
pkill -f manage.py
pkill -f celery
cd /home/www/django_web_portal/web_portal
source /home/www/django_web_portal/venv/bin/activate
nohup python3 manage.py runserver 0.0.0.0:8000 &
```

## 📁 Documentation Files

- **LINUX_SERVER_FIX.md** - Complete Linux deployment guide
- **install_urdu_support_linux.sh** - Automated installer script
- **URDU_PDF_FIX_GUIDE.md** - Detailed troubleshooting guide

## ✅ Success Criteria

After deployment, the Django logs should show:
```
Successfully registered Urdu font: NotoNastaliqUrdu from /usr/share/fonts/truetype/noto/NotoNastaliqUrdu-Regular.ttf
```

And the PDF footer should display:
```
معزز بزنس پارٹنر: آپ کے لیجر کی کاپی ارسال کی جا رہی ہے۔
```

Instead of:
```
■■■■ ■■ ■■■■■ ■■ ■■■■■ ■■ ■■ ■■■ ■■■■■
```

---

**Ready to deploy? Run the commands above on your server!** 🚀
