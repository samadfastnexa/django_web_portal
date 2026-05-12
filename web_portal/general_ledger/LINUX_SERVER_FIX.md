# Urdu PDF Fix for Linux Server - Quick Guide

## ✅ Status Check
- ✅ Libraries installed: `arabic-reshaper`, `python-bidi`  
- ✅ Server: Ubuntu Linux (`fourb-virtual-machine`)
- ❌ **Font missing**: Noto Nastaliq Urdu font not installed
- ❌ **Code issue**: Only checking Windows font paths

## 🔧 Quick Fix (On Server)

### OPTION 1: Automated Installation (Recommended)

```bash
# Upload the script to your server, then:
cd /home/www/django_web_portal/web_portal
chmod +x install_urdu_support_linux.sh
./install_urdu_support_linux.sh
```

### OPTION 2: Manual Installation

```bash
# 1. Install Noto Nastaliq Urdu font
cd /tmp
wget https://github.com/googlefonts/noto-fonts/raw/main/hinted/ttf/NotoNastaliqUrdu/NotoNastaliqUrdu-Regular.ttf
sudo mkdir -p /usr/share/fonts/truetype/noto
sudo cp NotoNastaliqUrdu-Regular.ttf /usr/share/fonts/truetype/noto/
sudo fc-cache -f -v

# 2. Verify font installation
fc-list | grep -i "noto nastaliq"
# Should output: /usr/share/fonts/truetype/noto/NotoNastaliqUrdu-Regular.ttf: Noto Nastaliq Urdu:style=Regular

# 3. Restart Django server
cd /home/www/django_web_portal/web_portal
# Kill existing server
pkill -f "manage.py runserver"
# Start new server
source /home/www/django_web_portal/venv/bin/activate
nohup python3 manage.py runserver 0.0.0.0:8000 &
```

### OPTION 3: Install from Package Manager

```bash
# Ubuntu/Debian
sudo apt-get update
sudo apt-get install fonts-noto-nastaliq-urdu

# Verify
fc-list | grep -i "noto nastaliq"

# Restart Django
pkill -f "manage.py runserver"
cd /home/www/django_web_portal/web_portal
source /home/www/django_web_portal/venv/bin/activate
nohup python3 manage.py runserver 0.0.0.0:8000 &
```

## 📝 What Was Fixed in the Code

The code now checks for fonts on **both Windows AND Linux**:

**Before (Windows only):**
```python
_URDU_FONT_CANDIDATES = [
    ('NotoNastaliqUrdu', r'C:\Windows\Fonts\NotoNastaliqUrdu-Regular.ttf'),
    # ... other Windows fonts
]
```

**After (Cross-platform):**
```python
if sys.platform.startswith('win'):
    # Windows paths
else:
    # Linux paths: /usr/share/fonts/truetype/noto/...
```

## 🔍 Verification Commands

```bash
# 1. Check if font is installed
fc-list | grep -i "noto nastaliq"

# 2. Test font file exists
ls -la /usr/share/fonts/truetype/noto/NotoNastaliqUrdu-Regular.ttf

# 3. Check Python libraries
python3 -c "import arabic_reshaper; from bidi.algorithm import get_display; print('OK')"

# 4. Check Django logs for font registration
tail -f /home/www/django_web_portal/web_portal/nohup.out | grep -i font

# 5. Test PDF generation (check logs for errors)
tail -f /home/www/django_web_portal/web_portal/nohup.out
```

## 📊 Font Priority on Linux

The system will try fonts in this order:

1. **Noto Nastaliq Urdu** (Best - proper Urdu Nastaliq style) ← **Install this!**
2. **Noto Sans** (Good - has basic Urdu support)
3. **DejaVu Sans** (Acceptable - limited Urdu)
4. **Liberation Sans** (Acceptable - limited Urdu)
5. **Free Sans** (Poor - basic Unicode only)
6. **Helvetica** (Worst - no Urdu support) ← **Currently using**

## 🆘 Troubleshooting

### Issue: Font installed but still showing boxes

```bash
# 1. Rebuild font cache
sudo fc-cache -f -v

# 2. Check Django logs for font registration
tail -n 100 /home/www/django_web_portal/web_portal/nohup.out | grep -i "font"
# Look for: "Successfully registered Urdu font: NotoNastaliqUrdu"

# 3. Restart server completely
pkill -f "manage.py"
pkill -f "celery"
cd /home/www/django_web_portal/web_portal
source /home/www/django_web_portal/venv/bin/activate
nohup python3 manage.py runserver 0.0.0.0:8000 &
```

### Issue: Cannot download font (no internet on server)

```bash
# Download on your local machine, then upload to server:
# Local:
wget https://github.com/googlefonts/noto-fonts/raw/main/hinted/ttf/NotoNastaliqUrdu/NotoNastaliqUrdu-Regular.ttf

# Upload to server using SCP:
scp NotoNastaliqUrdu-Regular.ttf root@fourb-virtual-machine:/tmp/

# On server:
sudo cp /tmp/NotoNastaliqUrdu-Regular.ttf /usr/share/fonts/truetype/noto/
sudo fc-cache -f -v
```

### Issue: Permission denied

```bash
# Make sure you're running as root or with sudo:
sudo mkdir -p /usr/share/fonts/truetype/noto
sudo cp NotoNastaliqUrdu-Regular.ttf /usr/share/fonts/truetype/noto/
sudo chmod 644 /usr/share/fonts/truetype/noto/NotoNastaliqUrdu-Regular.ttf
sudo fc-cache -f -v
```

## 📁 Files Deployed to Server

After pulling from Git, these files are available:

1. **views.py** - Updated with Linux font support
2. **install_urdu_support_linux.sh** - Automated installer script  
3. **check_urdu_fonts.py** - Diagnostic tool

## 🎯 Expected Result

**Before Fix (Current):**
```
■■■■ ■■ ■■■■■ ■■ ■■■■■ ■■ ■■ ■■■ ■■■■■ ■■ ■■■■■ ■■■■ ■■■■
```

**After Fix:**
```
معزز بزنس پارٹنر: آپ کے لیجر کی کاپی ارسال کی جا رہی ہے۔ اسکو اپنے کھاتے کے مطابق چیک کر کے بیلنس کی تصدیق کر دیں۔
```

## ⏱️ Deployment Steps

1. **Push code to Git** (already done - code is fixed)
2. **Pull on server**: `git pull origin main`
3. **Install font** (use one of the 3 options above)
4. **Restart server**
5. **Test PDF generation**

## 🚀 Quick One-Liner Install

```bash
# All-in-one command (as root):
cd /tmp && wget -q https://github.com/googlefonts/noto-fonts/raw/main/hinted/ttf/NotoNastaliqUrdu/NotoNastaliqUrdu-Regular.ttf && sudo mkdir -p /usr/share/fonts/truetype/noto && sudo cp NotoNastaliqUrdu-Regular.ttf /usr/share/fonts/truetype/noto/ && sudo fc-cache -f -v && pkill -f "manage.py runserver" && cd /home/www/django_web_portal/web_portal && source /home/www/django_web_portal/venv/bin/activate && nohup python3 manage.py runserver 0.0.0.0:8000 &
```

## 📞 Support

Check Django logs for detailed error messages:
```bash
tail -f /home/www/django_web_portal/web_portal/nohup.out
```
