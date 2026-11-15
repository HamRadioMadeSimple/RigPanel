#!/usr/bin/env bash
# Adds RigPanel to your Linux applications menu (Mint, Ubuntu, etc.).
#     ./install_linux_launcher.sh            add the menu entry
#     ./install_linux_launcher.sh --remove   take it away again
HERE="$(cd "$(dirname "$(readlink -f "$0")")" && pwd)"
APPS="${XDG_DATA_HOME:-$HOME/.local/share}/applications"
ENTRY="$APPS/rigpanel.desktop"

if [ "$1" = "--remove" ]; then
    rm -f "$ENTRY"
    echo "Removed RigPanel from the applications menu."
    exit 0
fi

chmod +x "$HERE/rigpanel.sh"
mkdir -p "$APPS"
cat > "$ENTRY" <<EOF
[Desktop Entry]
Type=Application
Name=RigPanel
Comment=IC-7300 / FT-891 control panel (through flrig)
Exec="$HERE/rigpanel.sh"
Path=$HERE
Icon=$HERE/icon.png
StartupWMClass=Rigpanel
Terminal=false
Categories=HamRadio;Utility;
EOF
chmod +x "$ENTRY"
command -v update-desktop-database >/dev/null && update-desktop-database "$APPS" >/dev/null 2>&1
echo "RigPanel added to the applications menu (under Accessories, or search 'RigPanel')."
echo "Run ./rigpanel.sh once from a terminal first so the setup messages are visible."
