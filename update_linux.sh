#!/bin/bash
# RigPanel - update on Linux from the newest RigPanel_V*.zip in ~/Downloads.
# Fresh copy of the code, build, install (replaces the menu entry and desktop icon).
# Close RigPanel first. Run:  bash ~/Downloads/update_linux.sh
set -e
ZIP=$(ls -t "$HOME"/Downloads/RigPanel_V*.zip 2>/dev/null | head -1)
[ -n "$ZIP" ] || { echo "No RigPanel_V*.zip in ~/Downloads"; exit 1; }
DIR="$HOME/RigPanel-1.4.4"
echo "Using: $ZIP"

pkill -x RigPanel 2>/dev/null && sleep 1 || true            # the installed RigPanel, if still open

# keep the build tools (saves re-downloading them), start the code fresh
[ -d "$DIR/RigPanel/.buildenv" ] && mv "$DIR/RigPanel/.buildenv" "$HOME/.rigpanel_buildenv_keep"
rm -rf "$DIR"
unzip -q "$ZIP" -d "$DIR"
[ -d "$HOME/.rigpanel_buildenv_keep" ] && mv "$HOME/.rigpanel_buildenv_keep" "$DIR/RigPanel/.buildenv"

cd "$DIR/RigPanel"
BUILD=$(grep -o 'APP_BUILD = "[^"]*"' rigpanel/core.py | cut -d'"' -f2)
VER=$(grep -o '^VER=.*' build_linux.sh | cut -d= -f2)
echo "Code: version $VER, build $BUILD"
chmod +x ./*.sh
./build_linux.sh

F="$(ls -t output/*_Linux.tar.gz | head -n 1)"
mkdir -p ~/Applications && tar -xzf "$F" -C ~/Applications
sh ~/Applications/"$(tar -tzf "$F" | head -n 1 | cut -d/ -f1)"/linux_install.sh --yes
echo
echo "Installed build $BUILD - start RigPanel from the menu or the desktop icon."
echo "The status bar (bottom right) should say: build $BUILD"
echo "File to send to others: $DIR/RigPanel/$F"
