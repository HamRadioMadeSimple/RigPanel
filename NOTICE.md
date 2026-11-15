# Notices and credits

RigPanel is Copyright © 2026 KW3KW and is free software under the GNU General Public License v3.0
(see [LICENSE](LICENSE)).

## Programs it works with (not included)

- **flrig** by Dave Freese, W1HKJ, and contributors (GPL), <http://www.w1hkj.com/>. RigPanel talks to
  flrig's XML-RPC server. It is an independent project and is not part of flrig.
- WSJT-X, JS8Call and fldigi are named only as programs that can share the radio through flrig.

## Included in the ready-built programs

The Windows installer, the Linux `.tar.gz` and the AppImage are made with **PyInstaller** and carry their
own copy of:

- **Python** (Python Software Foundation License), <https://www.python.org/>
- **Tcl/Tk** (BSD-style Tcl/Tk license), <https://www.tcl-lang.org/>
- **NumPy** (BSD), **python-sounddevice** (MIT) with **PortAudio** (MIT-style) on Windows, and **Pillow**
  (MIT-CMU), used by code that is still being worked on
- on Linux, the shared libraries Tk needs (X11, fontconfig, FreeType and similar), each under its own
  free license.

The PyInstaller bootloader is GPL with an exception that allows it in programs under any license,
<https://pyinstaller.org/>. The Windows installer is made with **Inno Setup** by Jordan Russell,
<https://jrsoftware.org/isinfo.php>.

## Radio details

Command and menu details for the Icom IC-7300 and Yaesu FT-891 come from the makers' published manuals
and were checked on real radios. Icom and Yaesu names belong to their owners; RigPanel is not made or
endorsed by them.

## Frequencies

The starter frequencies and `examples/KW3KW_settings.json` list publicly known calling frequencies (for
example W1AW, JS8, FT8) and net frequencies. Check the band plan and your license before transmitting.

## Icon and screenshots

The app icon and the screenshots in `docs/images/` were made for this project.
