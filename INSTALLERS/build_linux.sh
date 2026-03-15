#!/bin/bash
#
# AMCIS Linux Build Script
# Creates Snap and Flatpak packages for Linux distributions
#

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${GREEN}==========================================${NC}"
echo -e "${GREEN}AMCIS Linux Installer Builder${NC}"
echo -e "${GREEN}==========================================${NC}"
echo ""

# Detect Linux distribution
if [ -f /etc/os-release ]; then
    . /etc/os-release
    DISTRO=$NAME
else
    DISTRO="Unknown"
fi

echo -e "${YELLOW}Detected distribution: $DISTRO${NC}"
echo ""

# Create output directory
mkdir -p dist

# Function to build Snap package
build_snap() {
    echo -e "${YELLOW}Building Snap package...${NC}"
    
    if ! command -v snapcraft &> /dev/null; then
        echo -e "${RED}snapcraft not found. Installing...${NC}"
        sudo snap install snapcraft --classic
    fi
    
    # Build the snap
    snapcraft --use-lxd
    
    # Move to dist
    mv *.snap dist/ 2>/dev/null || true
    
    echo -e "${GREEN}Snap package built successfully${NC}"
}

# Function to build Flatpak
build_flatpak() {
    echo -e "${YELLOW}Building Flatpak package...${NC}"
    
    if ! command -v flatpak-builder &> /dev/null; then
        echo -e "${RED}flatpak-builder not found. Please install flatpak-builder${NC}"
        return 1
    fi
    
    # Install required runtime
    flatpak install --user flathub org.freedesktop.Platform//23.08 org.freedesktop.Sdk//23.08 -y || true
    
    # Build flatpak
    flatpak-builder --force-clean build-dir com.amcis.SecurityPlatform.json
    
    # Create repo
    flatpak-builder --repo=repo --force-clean build-dir com.amcis.SecurityPlatform.json
    
    # Build bundle
    flatpak build-bundle repo dist/amcis-security-platform.flatpak com.amcis.SecurityPlatform
    
    echo -e "${GREEN}Flatpak package built successfully${NC}"
}

# Function to build AppImage
build_appimage() {
    echo -e "${YELLOW}Building AppImage...${NC}"
    
    # Create AppDir structure
    mkdir -p AppDir/usr/bin
    mkdir -p AppDir/usr/share/applications
    mkdir -p AppDir/usr/share/icons/hicolor/256x256/apps
    mkdir -p AppDir/usr/lib/amcis
    
    # Copy AMCIS files
    cp -r ../AMCIS_Q_SEC_CORE/* AppDir/usr/lib/amcis/
    
    # Create launcher
    cat > AppDir/usr/bin/amcis << 'EOF'
#!/bin/bash
HERE="$(dirname "$(readlink -f "$0")")"
export PYTHONPATH="$HERE/../lib/amcis:$PYTHONPATH"
export AMCIS_HOME="$HOME/.amcis"
python3 "$HERE/../lib/amcis/cli/amcis_main.py" "$@"
EOF
    chmod +x AppDir/usr/bin/amcis
    
    # Copy desktop file and icon
    cp com.amcis.SecurityPlatform.desktop AppDir/usr/share/applications/
    cp ../assets/amcis_icon.png AppDir/usr/share/icons/hicolor/256x256/apps/com.amcis.SecurityPlatform.png
    
    # Create AppRun
    cat > AppDir/AppRun << 'EOF'
#!/bin/bash
HERE="$(dirname "$(readlink -f "$0")")"
export PATH="$HERE/usr/bin:$PATH"
exec amcis "$@"
EOF
    chmod +x AppDir/AppRun
    
    # Download appimagetool if not present
    if [ ! -f "appimagetool-x86_64.AppImage" ]; then
        wget -q https://github.com/AppImage/AppImageKit/releases/download/continuous/appimagetool-x86_64.AppImage
        chmod +x appimagetool-x86_64.AppImage
    fi
    
    # Build AppImage
    ARCH=x86_64 ./appimagetool-x86_64.AppImage AppDir dist/AMCIS-Security-Platform-x86_64.AppImage
    
    echo -e "${GREEN}AppImage built successfully${NC}"
}

# Function to build Debian package
build_deb() {
    echo -e "${YELLOW}Building Debian package...${NC}"
    
    VERSION="1.0.0"
    PKGDIR="amcis-security-platform_${VERSION}_amd64"
    
    # Create package structure
    mkdir -p $PKGDIR/DEBIAN
    mkdir -p $PKGDIR/usr/bin
    mkdir -p $PKGDIR/usr/lib/amcis
    mkdir -p $PKGDIR/usr/share/applications
    mkdir -p $PKGDIR/usr/share/doc/amcis
    mkdir -p $PKGDIR/etc/amcis
    mkdir -p $PKGDIR/lib/systemd/system
    
    # Create control file
    cat > $PKGDIR/DEBIAN/control << EOF
Package: amcis-security-platform
Version: $VERSION
Section: utils
Priority: optional
Architecture: amd64
Depends: python3 (>= 3.10), python3-pip, libssl3
Maintainer: AMCIS Team <support@amcis.io>
Description: AMCIS - Autonomous Multidimensional Cyber Intelligence System
 Next-generation security platform with post-quantum cryptography,
 AI-powered threat detection, and federal compliance automation.
EOF
    
    # Copy files
    cp -r ../AMCIS_Q_SEC_CORE/* $PKGDIR/usr/lib/amcis/
    cp ../.env.example $PKGDIR/etc/amcis/
    cp debian/copyright $PKGDIR/usr/share/doc/amcis/
    
    # Create systemd service
    cat > $PKGDIR/lib/systemd/system/amcis.service << 'EOF'
[Unit]
Description=AMCIS Security Platform
After=network.target

[Service]
Type=simple
User=amcis
Group=amcis
ExecStart=/usr/bin/python3 /usr/lib/amcis/cli/amcis_main.py
Restart=always
RestartSec=10
Environment=AMCIS_CONFIG_PATH=/etc/amcis

[Install]
WantedBy=multi-user.target
EOF
    
    # Build package
    dpkg-deb --build $PKGDIR
    mv ${PKGDIR}.deb dist/
    rm -rf $PKGDIR
    
    echo -e "${GREEN}Debian package built successfully${NC}"
}

# Menu
echo "Select build target:"
echo "1) Snap package"
echo "2) Flatpak package"
echo "3) AppImage"
echo "4) Debian package (.deb)"
echo "5) All packages"
echo ""
read -p "Enter choice [1-5]: " choice

case $choice in
    1) build_snap ;;
    2) build_flatpak ;;
    3) build_appimage ;;
    4) build_deb ;;
    5) 
        build_snap
        build_flatpak
        build_appimage
        build_deb
        ;;
    *)
        echo -e "${RED}Invalid choice${NC}"
        exit 1
        ;;
esac

echo ""
echo -e "${GREEN}==========================================${NC}"
echo -e "${GREEN}Build Complete!${NC}"
echo -e "${GREEN}==========================================${NC}"
echo "Output files in dist/:"
ls -lh dist/
