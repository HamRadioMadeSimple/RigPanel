#!/bin/bash
# Build a newer flrig NEXT TO the installed one, for testing RigPanel - the installed flrig
# (2.0.09 from the package manager) is not removed or replaced, and its settings aren't touched.
#
#   bash flrig_side_by_side.sh 2.0.12        build it (once)  - check w1hkj.org for the newest number
#   bash flrig_side_by_side.sh 2.0.12 run    start it (close the normal flrig first: one port, one flrig)
#
# Source: https://www.w1hkj.org/files/flrig/  (use .org - w1hkj.com now goes elsewhere)
# Uses FLTK 1.3 (libfltk1.3-dev); newer FLTK doesn't build flrig.
set -e
SELF="$(readlink -f "$0")"          # this script, before any cd (the desktop icon calls it)
VER="${1:?give the flrig version, e.g. 2.0.12}"
TOP="$HOME/flrig-test"
SRC="$TOP/flrig-$VER"
CONF="$HOME/.flrig-test"            # its own settings folder (a copy of yours), so ~/.flrig stays as it is

if [ "$2" = "run" ]; then
  if pgrep -x flrig >/dev/null; then
    echo "Another flrig is running - close it first (both would want the radio's serial port)."
    exit 1
  fi
  BIN="$SRC/src/flrig"
  [ -x "$BIN" ] || { echo "Not built yet: bash $0 $VER"; exit 1; }
  echo "Starting flrig $VER (settings in $CONF). The normal flrig is unchanged."
  exec "$BIN" --config-dir "$CONF/"
fi

echo "[1/4] Build tools (FLTK 1.3)..."
sudo apt install -y build-essential pkg-config libfltk1.3-dev libudev-dev libx11-dev

echo "[2/4] Download flrig $VER..."
mkdir -p "$TOP" && cd "$TOP"
if [ ! -s "flrig-$VER.tar.gz" ]; then
  rm -f "flrig-$VER.tar.gz"
  # w1hkj.org keeps only the newest release; older ones are on SourceForge (fldigi project)
  wget -O "flrig-$VER.tar.gz" "https://www.w1hkj.org/files/flrig/flrig-$VER.tar.gz" \
  || wget -O "flrig-$VER.tar.gz" "https://sourceforge.net/projects/fldigi/files/flrig/flrig-$VER.tar.gz/download" \
  || { rm -f "flrig-$VER.tar.gz"
       echo; echo "flrig $VER not found. Open https://www.w1hkj.org/files/flrig/ in a browser,"
       echo "see which flrig-x.x.xx.tar.gz is listed, and run this again with that number."; exit 1; }
fi
rm -rf "$SRC" && tar xzf "flrig-$VER.tar.gz"

echo "[3/4] Build (no 'make install' - nothing is replaced)..."
cd "$SRC"
./configure
make -j"$(nproc)"

echo "[4/4] Settings: copy yours to $CONF (first time only)..."
if [ ! -d "$CONF" ] && [ -d "$HOME/.flrig" ]; then
  cp -r "$HOME/.flrig" "$CONF"
fi
# a desktop icon for the test flrig (it runs this script's "run", which checks no other flrig is open)
DESK="$(xdg-user-dir DESKTOP 2>/dev/null || echo "$HOME/Desktop")/flrig-$VER-test.desktop"
cat > "$DESK" <<EOF2
[Desktop Entry]
Type=Application
Name=flrig $VER (test)
Exec=bash "$SELF" $VER run
Icon=flrig
Terminal=false
Categories=HamRadio;
EOF2
chmod +x "$DESK"
gio set "$DESK" metadata::trusted true 2>/dev/null || true
echo
"$SRC/src/flrig" --version 2>/dev/null || true
echo "Desktop icon: flrig $VER (test)"
echo "Built: $SRC/src/flrig"
echo "Run it with:  bash $0 $VER run   (close the normal flrig first)"
echo "Your installed flrig: $(command -v flrig || echo 'not found') - unchanged."
