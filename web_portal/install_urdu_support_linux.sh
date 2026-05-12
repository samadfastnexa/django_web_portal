#!/bin/bash
# ==============================================================================
# Urdu PDF Support Installer for Linux Server
# ==============================================================================

echo "======================================================================"
echo "  URDU PDF SUPPORT INSTALLER (Linux)"
echo "======================================================================"
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Step 1: Check if libraries are installed
echo -e "${YELLOW}Step 1: Checking Python libraries...${NC}"
python3 -c "import arabic_reshaper; from bidi.algorithm import get_display" 2>/dev/null
if [ $? -eq 0 ]; then
    echo -e "${GREEN}  ✓ arabic-reshaper and python-bidi are installed${NC}"
else
    echo -e "${RED}  ✗ Libraries not installed${NC}"
    echo -e "${YELLOW}  Installing now...${NC}"
    pip install arabic-reshaper==3.0.1 python-bidi==0.6.7
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}  ✓ Libraries installed successfully${NC}"
    else
        echo -e "${RED}  ✗ Failed to install libraries${NC}"
        exit 1
    fi
fi

# Step 2: Install Noto Nastaliq Urdu font
echo ""
echo -e "${YELLOW}Step 2: Installing Noto Nastaliq Urdu font...${NC}"

# Check if font is already installed
if fc-list | grep -qi "Noto Nastaliq Urdu"; then
    echo -e "${GREEN}  ✓ Noto Nastaliq Urdu font is already installed${NC}"
else
    echo -e "${YELLOW}  Downloading and installing font...${NC}"
    
    # Create temporary directory
    TEMP_DIR=$(mktemp -d)
    cd "$TEMP_DIR"
    
    # Download font
    echo -e "${CYAN}  Downloading font from Google Fonts...${NC}"
    wget -q "https://github.com/googlefonts/noto-fonts/raw/main/hinted/ttf/NotoNastaliqUrdu/NotoNastaliqUrdu-Regular.ttf" -O NotoNastaliqUrdu-Regular.ttf
    
    if [ $? -eq 0 ]; then
        # Install font system-wide
        sudo mkdir -p /usr/share/fonts/truetype/noto
        sudo cp NotoNastaliqUrdu-Regular.ttf /usr/share/fonts/truetype/noto/
        sudo fc-cache -f -v > /dev/null 2>&1
        
        # Verify installation
        if fc-list | grep -qi "Noto Nastaliq Urdu"; then
            echo -e "${GREEN}  ✓ Font installed successfully to /usr/share/fonts/truetype/noto/${NC}"
        else
            echo -e "${RED}  ✗ Font installation verification failed${NC}"
        fi
    else
        echo -e "${RED}  ✗ Failed to download font${NC}"
        echo -e "${YELLOW}  Trying alternative method...${NC}"
        
        # Alternative: Install from package manager
        if command -v apt-get &> /dev/null; then
            echo -e "${CYAN}  Installing from apt package manager...${NC}"
            sudo apt-get update > /dev/null 2>&1
            sudo apt-get install -y fonts-noto-nastaliq-urdu > /dev/null 2>&1
            if [ $? -eq 0 ]; then
                echo -e "${GREEN}  ✓ Font installed from package manager${NC}"
            else
                echo -e "${RED}  ✗ Package installation failed${NC}"
            fi
        fi
    fi
    
    # Cleanup
    cd - > /dev/null
    rm -rf "$TEMP_DIR"
fi

# Step 3: Check available fonts
echo ""
echo -e "${YELLOW}Step 3: Available fonts for Urdu rendering:${NC}"
echo -e "${CYAN}  Checking font files...${NC}"

FONTS_FOUND=0

# Check for Noto Nastaliq Urdu
if [ -f "/usr/share/fonts/truetype/noto/NotoNastaliqUrdu-Regular.ttf" ]; then
    echo -e "${GREEN}  ✓ Noto Nastaliq Urdu (Best quality)${NC}"
    FONTS_FOUND=$((FONTS_FOUND + 1))
elif [ -f "/usr/share/fonts/noto/NotoNastaliqUrdu-Regular.ttf" ]; then
    echo -e "${GREEN}  ✓ Noto Nastaliq Urdu (Best quality)${NC}"
    FONTS_FOUND=$((FONTS_FOUND + 1))
fi

# Check for other Unicode fonts
if [ -f "/usr/share/fonts/truetype/noto/NotoSans-Regular.ttf" ]; then
    echo -e "${GREEN}  ✓ Noto Sans (Good quality)${NC}"
    FONTS_FOUND=$((FONTS_FOUND + 1))
fi

if [ -f "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf" ]; then
    echo -e "${GREEN}  ✓ DejaVu Sans (Acceptable)${NC}"
    FONTS_FOUND=$((FONTS_FOUND + 1))
fi

if [ -f "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf" ]; then
    echo -e "${GREEN}  ✓ Liberation Sans (Acceptable)${NC}"
    FONTS_FOUND=$((FONTS_FOUND + 1))
fi

if [ $FONTS_FOUND -eq 0 ]; then
    echo -e "${RED}  ✗ No suitable fonts found!${NC}"
    echo -e "${YELLOW}  Installing DejaVu fonts as fallback...${NC}"
    if command -v apt-get &> /dev/null; then
        sudo apt-get install -y fonts-dejavu-core > /dev/null 2>&1
    fi
fi

# Step 4: Restart Django server
echo ""
echo -e "${YELLOW}Step 4: Restarting Django server...${NC}"

# Find Django runserver process
DJANGO_PID=$(ps aux | grep "manage.py runserver" | grep -v grep | awk '{print $2}')

if [ ! -z "$DJANGO_PID" ]; then
    echo -e "${CYAN}  Stopping Django server (PID: $DJANGO_PID)...${NC}"
    kill $DJANGO_PID
    sleep 2
    
    # Start server in background
    echo -e "${CYAN}  Starting Django server...${NC}"
    cd /home/www/django_web_portal/web_portal
    source /home/www/django_web_portal/venv/bin/activate
    nohup python3 manage.py runserver 0.0.0.0:8000 > /dev/null 2>&1 &
    
    sleep 3
    
    # Verify server is running
    if ps aux | grep "manage.py runserver" | grep -v grep > /dev/null; then
        echo -e "${GREEN}  ✓ Django server restarted successfully${NC}"
    else
        echo -e "${RED}  ✗ Failed to restart Django server${NC}"
    fi
else
    echo -e "${YELLOW}  No running Django server found. Please start manually:${NC}"
    echo -e "${CYAN}    cd /home/www/django_web_portal/web_portal${NC}"
    echo -e "${CYAN}    source /home/www/django_web_portal/venv/bin/activate${NC}"
    echo -e "${CYAN}    nohup python3 manage.py runserver 0.0.0.0:8000 &${NC}"
fi

# Final summary
echo ""
echo "======================================================================"
echo -e "${GREEN}  INSTALLATION COMPLETE${NC}"
echo "======================================================================"
echo ""
echo -e "${YELLOW}Next steps:${NC}"
echo -e "  1. Wait a few seconds for server to fully start"
echo -e "  2. Go to Django Admin → General Ledger"
echo -e "  3. Generate a new PDF"
echo -e "  4. Check that Urdu text displays correctly in the footer"
echo ""
echo -e "${CYAN}To verify font installation:${NC}"
echo -e "  fc-list | grep -i 'noto nastaliq'"
echo ""
echo -e "${CYAN}To check Django logs:${NC}"
echo -e "  tail -f /home/www/django_web_portal/web_portal/nohup.out"
echo ""
