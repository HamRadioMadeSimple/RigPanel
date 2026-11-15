#!/bin/bash
# RigPanel - Linux build: makes output/RigPanel_Ver_<ver>_Linux.tar.gz (build number inside: VERSION + status bar)
# Needs: sudo apt install python3-tk python3-venv libportaudio2
# Run in the RigPanel folder:  ./build_linux.sh    (--appimage also makes output/RigPanel-x86_64.AppImage)
# Build on the OLDEST Linux it should run on (GitHub builds the releases on Ubuntu 22.04).
set -e
cd "$(dirname "$0")"
VER=1.4.3
APPIMAGE=""; [ "$1" = "--appimage" ] && APPIMAGE=1

echo "[1/3] Build tools (in .buildenv, nothing installed system-wide)..."
python3 -c "import tkinter" 2>/dev/null || { echo "Tk missing: sudo apt install python3-tk"; exit 1; }
[ -d .buildenv ] || python3 -m venv .buildenv
.buildenv/bin/pip install --quiet --upgrade pip pyinstaller numpy sounddevice pillow

echo "[2/3] Building RigPanel..."
rm -rf build dist
.buildenv/bin/pyinstaller --noconfirm --clean --windowed --name RigPanel \
  --add-data "icon.png:." --add-data "icon_small.png:." --collect-all sounddevice --hidden-import PIL._tkinter_finder run_rigpanel.py

echo "[3/3] Packaging..."
BUILD=$(grep -o 'APP_BUILD = "[^"]*"' rigpanel/core.py | cut -d'"' -f2)
TOP="RigPanel Ver $VER"
TGZ="RigPanel_Ver_${VER}_Linux.tar.gz"
rm -rf "output/$TOP" output/*_Linux.tar.gz; mkdir -p "output/$TOP"
cp -r dist/RigPanel/. "output/$TOP/"
cp icon.png linux_install.sh "output/$TOP/"
echo "$VER build $BUILD" > "output/$TOP/VERSION"
for f in docs/RigPanel-Linux-Install.pdf docs/RigPanel_Quick_Start.pdf docs/RigPanel_v1.4.3_User_Guide.pdf; do [ -f "$f" ] && cp "$f" "output/$TOP/"; done
tar -C output -czf "output/$TGZ" "$TOP"

if [ -n "$APPIMAGE" ]; then
  echo "[+] AppImage..."
  if [ ! -x .appimagetool ]; then
    URL=https://github.com/AppImage/appimagetool/releases/download/continuous/appimagetool-x86_64.AppImage
    (curl -fsSL -o .appimagetool "$URL" || wget -q -O .appimagetool "$URL") || { echo "Could not download appimagetool"; exit 1; }
    chmod +x .appimagetool
  fi
  rm -rf AppDir; mkdir -p AppDir/usr/bin
  cp -a dist/RigPanel/. AppDir/usr/bin/
  cp icon.png AppDir/rigpanel.png; cp icon.png AppDir/.DirIcon
  printf '[Desktop Entry]\nType=Application\nName=RigPanel\nComment=Radio control panel via flrig\nExec=RigPanel\nIcon=rigpanel\nTerminal=false\nCategories=HamRadio;Utility;\n' > AppDir/rigpanel.desktop
  printf '#!/bin/sh\nHERE="$(dirname "$(readlink -f "$0")")"\nexec "$HERE/usr/bin/RigPanel" "$@"\n' > AppDir/AppRun
  chmod +x AppDir/AppRun
  rm -f output/RigPanel-x86_64.AppImage
  APPIMAGE_EXTRACT_AND_RUN=1 ARCH=x86_64 ./.appimagetool --no-appstream AppDir output/RigPanel-x86_64.AppImage
  rm -rf AppDir
fi

echo
echo "Done: output/$TGZ"
[ -n "$APPIMAGE" ] && echo "      output/RigPanel-x86_64.AppImage"
echo "To install: see RigPanel-Linux-Install.pdf (unpacks into ~/Applications)."
exit 0
