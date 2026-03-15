#!/bin/bash
#
# AMCIS macOS DMG Build Script
# Creates standalone macOS application bundle and DMG installer
#

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}==========================================${NC}"
echo -e "${GREEN}AMCIS macOS DMG Installer Builder${NC}"
echo -e "${GREEN}==========================================${NC}"
echo ""

# Check for macOS
if [[ "$OSTYPE" != "darwin"* ]]; then
    echo -e "${RED}ERROR: This script must be run on macOS${NC}"
    exit 1
fi

# Check for required tools
command -v python3 >/dev/null 2>&1 || { echo -e "${RED}ERROR: Python 3 is required${NC}"; exit 1; }
command -v pip3 >/dev/null 2>&1 || { echo -e "${RED}ERROR: pip3 is required${NC}"; exit 1; }

# Install dependencies
echo -e "${YELLOW}Installing dependencies...${NC}"
pip3 install pyinstaller
pip3 install create-dmg || echo "Warning: create-dmg not installed, will use fallback method"
pip3 install -r ../AMCIS_Q_SEC_CORE/requirements.txt

# Create build directories
mkdir -p build dist

# Build the application
echo ""
echo -e "${YELLOW}Building AMCIS macOS application...${NC}"
echo "This may take several minutes..."
echo ""

pyinstaller \
    --name="AMCIS-Security-Platform" \
    --windowed \
    --onedir \
    --icon=../assets/amcis_icon.icns \
    --osx-bundle-identifier="com.amcis.security" \
    --osx-entitlements-file="amcis.entitlements" \
    --hidden-import=core.amcis_kernel \
    --hidden-import=crypto.amcis_encrypt \
    --hidden-import=compliance.compliance_engine \
    --hidden-import=edr.amcis_file_integrity \
    --hidden-import=network.amcis_microsegmentation \
    --hidden-import=ai_security.amcis_prompt_firewall \
    --hidden-import=threat_intel.ioc_matcher \
    --hidden-import=dashboard.amcis_dashboard_server \
    --add-data="../AMCIS_Q_SEC_CORE/compliance/*.json:compliance" \
    --add-data="../AMCIS_Q_SEC_CORE/dashboard/*.html:dashboard" \
    --add-data="../.env.example:." \
    --clean \
    --noconfirm \
    ../AMCIS_Q_SEC_CORE/cli/amcis_main.py

# Sign the application (optional, requires Apple Developer ID)
if [ -n "$APPLE_DEVELOPER_ID" ]; then
    echo -e "${YELLOW}Signing application...${NC}"
    codesign --deep --force --verify --verbose --sign "$APPLE_DEVELOPER_ID" \
        "dist/AMCIS-Security-Platform.app"
fi

# Create DMG
echo ""
echo -e "${YELLOW}Creating DMG installer...${NC}"

DMG_NAME="AMCIS-Security-Platform-macOS.dmg"
VOLUME_NAME="AMCIS Security Platform"

if command -v create-dmg &> /dev/null; then
    create-dmg \
        --volname "$VOLUME_NAME" \
        --volicon "../assets/amcis_icon.icns" \
        --background "../assets/dmg_background.png" \
        --window-pos 200 120 \
        --window-size 800 400 \
        --icon-size 100 \
        --icon "AMCIS-Security-Platform.app" 200 190 \
        --hide-extension "AMCIS-Security-Platform.app" \
        --app-drop-link 600 185 \
        "$DMG_NAME" \
        "dist/AMCIS-Security-Platform.app"
else
    # Fallback: create simple DMG using hdiutil
    TEMP_DMG="temp.dmg"
    MOUNT_POINT="/Volumes/$VOLUME_NAME"
    
    # Create temporary DMG
    hdiutil create -srcfolder "dist/AMCIS-Security-Platform.app" \
        -volname "$VOLUME_NAME" -fs HFS+ \
        -format UDRW -o "$TEMP_DMG"
    
    # Convert to compressed read-only DMG
    hdiutil convert "$TEMP_DMG" -format UDZO -o "$DMG_NAME"
    rm -f "$TEMP_DMG"
fi

# Move to dist folder
mv "$DMG_NAME" dist/

echo ""
echo -e "${GREEN}==========================================${NC}"
echo -e "${GREEN}Build Complete!${NC}"
echo -e "${GREEN}==========================================${NC}"
echo "Output: dist/$DMG_NAME"
echo ""
