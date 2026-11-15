#!/usr/bin/env bash
# RigPanel launcher for Linux (Mint, Ubuntu, Debian, Fedora, Raspberry Pi OS ...).
# First run: makes a private Python environment (.venv) next to this file and installs
# the waterfall packages into it. Later runs just start RigPanel.
#     chmod +x rigpanel.sh   (once)
#     ./rigpanel.sh
cd "$(dirname "$(readlink -f "$0")")" || exit 1

say() { printf '%s\n' "$*"; }

if ! command -v python3 >/dev/null 2>&1; then
    say "Python 3 is not installed.  Mint/Ubuntu/Debian:  sudo apt install python3"
    exit 1
fi
if ! python3 -c 'import sys; sys.exit(sys.version_info < (3, 9))'; then
    say "RigPanel needs Python 3.9 or newer (you have $(python3 -V 2>&1))."
    exit 1
fi
if ! python3 -c 'import tkinter' 2>/dev/null; then
    say "Tk (the window toolkit) is missing."
    say "  Mint/Ubuntu/Debian:  sudo apt install python3-tk"
    say "  Fedora:              sudo dnf install python3-tkinter"
    exit 1
fi

if [ ! -x .venv/bin/python ]; then
    say "First run: setting up RigPanel's Python environment (.venv) ..."
    if ! python3 -m venv --system-site-packages .venv; then
        rm -rf .venv
        say "Could not create the environment."
        say "  Mint/Ubuntu/Debian:  sudo apt install python3-venv"
        exit 1
    fi
    say "Installing waterfall packages (numpy sounddevice pillow) ..."
    if ! .venv/bin/python -m pip install --quiet --upgrade numpy sounddevice pillow; then
        say "Package install failed (no internet?). RigPanel will still run without the waterfall;"
        say "run ./rigpanel.sh again when online to finish the install."
        rm -f .venv/.packages_ok
    else
        touch .venv/.packages_ok
    fi
elif [ ! -f .venv/.packages_ok ]; then
    .venv/bin/python -m pip install --quiet --upgrade numpy sounddevice pillow \
        && touch .venv/.packages_ok
fi

# The waterfall's sound input needs the PortAudio library
if ! .venv/bin/python -c 'import sounddevice' 2>/dev/null; then
    if ldconfig -p 2>/dev/null | grep -q libportaudio; then :; else
        say "Note: for the waterfall install PortAudio:  sudo apt install libportaudio2"
        say "      (Fedora: sudo dnf install portaudio). Everything else works without it."
    fi
fi

say "Starting RigPanel ... (close this window to stop it)"
exec .venv/bin/python run_rigpanel.py "$@"
