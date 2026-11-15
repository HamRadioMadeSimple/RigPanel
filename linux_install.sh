#!/bin/sh
# RigPanel installer for Linux - goes into the package as linux_install.sh.
# The program runs from the folder this script is in (normally ~/Applications/RigPanel Ver x.y.z).
#   sh linux_install.sh            install or update: menu entry + desktop icon point to this folder,
#                                  older RigPanel copies (other RigPanel Ver folders, the old ~/.local/share/rigpanel) are offered for removal (y/N)
#   sh linux_install.sh --yes      the same, answering yes to every question
#   sh linux_install.sh --remove   remove the menu entry and desktop icon (program folder and settings kept)
# Settings live in ~/.config/rigpanel and are never touched.
HERE="$(cd "$(dirname "$0")" && pwd)"
MENU="$HOME/.local/share/applications/rigpanel.desktop"
DESK_DIR="$(xdg-user-dir DESKTOP 2>/dev/null || echo "$HOME/Desktop")"
DESK="$DESK_DIR/rigpanel.desktop"
YES=0
[ "$1" = "--yes" ] && YES=1

ask() {   # ask "question" -> 0 for yes
    if [ "$YES" = 1 ]; then echo "$1 [y/N] y"; return 0; fi
    printf '%s [y/N] ' "$1"; read -r a
    case "$a" in y|Y|yes|YES) return 0 ;; *) return 1 ;; esac
}

if [ "$1" = "--remove" ]; then
    rm -f "$MENU" "$DESK"
    update-desktop-database "$(dirname "$MENU")" 2>/dev/null || true
    echo "RigPanel menu entry and desktop icon removed. Settings kept in ~/.config/rigpanel"
    exit 0
fi

if [ ! -f "$HERE/RigPanel" ]; then
    echo "STOP: RigPanel program not found in $HERE - unpack the whole .tar.gz first."; exit 1
fi
if pgrep -x RigPanel >/dev/null 2>&1; then
    echo "STOP: RigPanel is running. Close it, then paste the commands again."; exit 1
fi
chmod +x "$HERE/RigPanel"
VER="$(cat "$HERE/VERSION" 2>/dev/null)"
echo "Installing RigPanel $VER from: $HERE"

# Optional: the waterfall needs the PortAudio sound library
if ! ldconfig -p 2>/dev/null | grep -q libportaudio; then
    echo "The (optional) waterfall needs the sound library libportaudio2."
    if command -v apt-get >/dev/null 2>&1 && ask "Run it now? (installs libportaudio2, asks for your password)"; then
        sudo apt-get install -y libportaudio2 || echo "Not installed - RigPanel works without it (no waterfall)."
    else
        echo "Skipped - RigPanel works without it (no waterfall). Later: sudo apt install libportaudio2"
    fi
fi

# Menu entry and desktop icon
mkdir -p "$(dirname "$MENU")"
cat > "$MENU" <<EOF
[Desktop Entry]
Type=Application
Name=RigPanel
Comment=Radio control panel via flrig
Exec="$HERE/RigPanel"
Path=$HERE
Icon=$HERE/icon.png
Terminal=false
Categories=HamRadio;Utility;
StartupWMClass=Rigpanel
EOF
chmod +x "$MENU"
if [ -d "$DESK_DIR" ]; then
    cp "$MENU" "$DESK"; chmod +x "$DESK"
    gio set "$DESK" metadata::trusted true 2>/dev/null || true
fi
update-desktop-database "$(dirname "$MENU")" 2>/dev/null || true

# Older copies: other ~/Applications/RigPanel Ver * folders (never a newer one), and the old install places
is_rigpanel() { [ -f "$1/RigPanel" ] && [ -d "$1/_internal" ]; }
for d in "$HOME/Applications"/RigPanel\ Ver\ * "$HOME/.local/share/rigpanel"; do
    [ -d "$d" ] || continue
    [ "$(cd "$d" && pwd)" = "$HERE" ] && continue
    is_rigpanel "$d" || continue
    case "$d" in
        "$HOME/Applications/RigPanel Ver "*)
            other="$(cat "$d/VERSION" 2>/dev/null || basename "$d" | sed 's/^RigPanel Ver //')"
            newest="$(printf '%s\n%s\n' "$other" "$VER" | sort -V | tail -n 1)"
            if [ "$other" != "$VER" ] && [ "$newest" = "$other" ]; then
                echo "Kept: $d is newer ($other)."; continue
            fi ;;
    esac
    echo "Found an older RigPanel: $d"
    if ask "Remove it?"; then rm -rf "$d" && echo "Removed. Your settings are kept."; fi
done

echo
echo "RigPanel installed: menu (Ham Radio / Utilities) and desktop icon. Start flrig first, then RigPanel."
