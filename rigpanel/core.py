"""RigPanel core: app info, paths, settings file, fonts, colours, constants and small helpers."""


import http.client
import json
import os
import platform
import queue
import re
import shutil
import socket
import sys
import threading
import time
import tkinter as tk
import xmlrpc.client
from dataclasses import dataclass, field
from tkinter import filedialog, messagebox
from tkinter import font as tkfont
from tkinter import ttk

try:
    import numpy as np
except ImportError:
    np = None
SD_ERROR = ""
try:
    import sounddevice as sd
except Exception as _e:  # missing module or missing PortAudio library
    sd = None
    SD_ERROR = str(_e)
try:
    from PIL import Image, ImageTk
except ImportError:
    Image = ImageTk = None

# --------------------------------------------------------------------------
# Config / look
# --------------------------------------------------------------------------
APP_NAME = "RigPanel"
APP_VERSION = "1.4.3"
APP_BUILD = "2026-11-14h"     # bump on every release (YYYY-MM-DD + letter)

def _data_dir():
    """Per-user folder for settings and the debug log (always writable, even when the app
    itself is installed in Program Files)."""
    home = os.path.expanduser("~")
    if platform.system() == "Windows":
        return os.path.join(os.environ.get("APPDATA") or home, "RigPanel")
    if platform.system() == "Darwin":
        return os.path.join(home, "Library", "Application Support", "RigPanel")
    return os.path.join(os.environ.get("XDG_CONFIG_HOME") or os.path.join(home, ".config"), "rigpanel")


DATA_DIR = _data_dir()
CONFIG_PATH = os.path.join(DATA_DIR, "settings.json")
OLD_CONFIG_PATH = os.path.join(os.path.expanduser("~"), ".rigpanel.json")   # v1.1 builds before 21n
# Bundled read-only files (icons). A packaged app (PyInstaller) unpacks them to sys._MEIPASS.
RES_DIR = getattr(sys, "_MEIPASS", os.path.dirname(os.path.dirname(os.path.abspath(__file__))))   # icons: repo folder


def ensure_data_dir():
    """Create the data folder and bring settings over from the old ~/.rigpanel.json once
    (the old file is left in place, so going back to an older build still works)."""
    try:
        os.makedirs(DATA_DIR, exist_ok=True)
        if not os.path.exists(CONFIG_PATH) and os.path.exists(OLD_CONFIG_PATH):
            shutil.copy2(OLD_CONFIG_PATH, CONFIG_PATH)
    except OSError:
        pass
DEFAULT_CONFIG = {
    "host": "127.0.0.1",
    "port": 12345,
    "rig": "Auto-detect",
    "civ_addr": "94",          # IC-7300 factory default CI-V address (hex)
    "audio_device": "",
    "memories": [],            # stored frequencies: [{"hz", "mode", "name"}]
    "theme": "Dark",
    "mini_auto": True,         # pop the mini meter up when transmitting
    "mini_always": False,      # keep the mini meter on screen all the time
    "mini_pos": None,          # [x, y] where you last dragged it
    "mini_scale": 1.0,         # mini meter size (drag a corner); 1.0 = normal
    "lv_auto": False,          # mini levels: pop up when receiving
    "lv_always": False,        # mini levels: keep on screen all the time
    "lv_pos": None,            # mini levels: [x, y]
    "lv_scale": 1.0,           # mini levels: size
    "lv_smeter": True,         # mini levels: S-METER row on top (28a)
    "custom_rigs": [],         # "Add my radio": [{name, match, family icom/yaesu/flrig, civ}] (11-14c)
    "ctrl_tap": True,          # tap Ctrl alone (any program): RigPanel forward / back (11-09b)
    "add_radio_asked": [],     # radio names flrig reported that Add my radio was already shown for (11-14g)
    "wf_show": False,          # waterfall panel on the main window (off = smaller window)
    "wf_float_geom": "",       # pop-out waterfall "WxH+X+Y"
    "wf_float_top": True,      # pop-out waterfall stays on top
    "wf_auto": True,           # waterfall auto level
    "wf_floor_db": -110,       # waterfall floor (manual level)
    "wf_contrast_db": 24,      # dB above the floor that reach full brightness
    "wf_speed": "Normal",      # Fast / Normal / Slow
    "band_memory": {},         # last frequency per band and voice/data/cw: {"40:data": 7074000}
    "ft891_macro_list": None,  # FT-891 macros; None = the built-in starting set
    "ic7300_macro_list": None, # IC-7300 macros; None = the built-in starting set
}

SYS = platform.system()


class FONT:
    """Font families in use. pick_fonts() swaps in fonts this computer actually has;
    everything reads FONT.ui / FONT.mono when it builds, so all modules see the choice."""
    ui = "Segoe UI" if SYS == "Windows" else ("Helvetica Neue" if SYS == "Darwin" else "DejaVu Sans")
    mono = "Consolas" if SYS == "Windows" else ("Menlo" if SYS == "Darwin" else "DejaVu Sans Mono")


FONT_CHOICES = {          # first one installed wins (Linux distributions ship different fonts)
    "UI": ["Segoe UI", "Helvetica Neue", "DejaVu Sans", "Noto Sans", "Ubuntu", "Liberation Sans",
           "Cantarell", "FreeSans", "Arial"],
    "MONO": ["Consolas", "Menlo", "DejaVu Sans Mono", "Noto Sans Mono", "Ubuntu Mono", "Liberation Mono",
             "FreeMono", "Courier New"],
}


def pick_fonts(root):
    """Set FONT.ui / FONT.mono to fonts this computer actually has (call once, before building the window)."""
    try:
        have = {f.lower() for f in tkfont.families(root)}
    except tk.TclError:
        return
    for attr, key, named in (("ui", "UI", "TkDefaultFont"), ("mono", "MONO", "TkFixedFont")):
        pick = next((f for f in FONT_CHOICES[key] if f.lower() in have), None)
        if pick is None:          # none of ours installed: use Tk's own default font
            try:
                pick = tkfont.nametofont(named).actual("family")
            except (tk.TclError, RuntimeError):
                continue
        setattr(FONT, attr, pick)

# Shared look with the other station apps (JS8FastChat): dark header band with the app name and monospace
# status values, a toolbar of "Label: [dropdown]" rows, bold gray buttons, red
# for transmit actions, and a status bar along the bottom.
THEMES = {
    "Dark": dict(
        bg="#0d1218", panel="#141b24", panel2="#1e2934", field="#0a1016", border="#26384a",
        fg="#eef3f8", dim="#8fa3b8", btn="#1e2934", hover="#2a3a4c", btn_border="#34485c",
        on="#1f7fff", accent="#2bb3ff", green="#3fb950", amber="#d29922", red="#f85149", tx="#d92b2b",
        freq="#39e75f", freq_dim="#2f6b3c", gold="#e3b341", title="#ff6b6b", profile="#3fe07a",
        po="#ff4d4d", alc="#79c0ff", alc_over="#ff9a1f", voice="#79c0ff", level="#3b82f6",
        go="#2ee06e", go_fg="#000000",
        header="#070b11", header_fg="#ffffff", header_val="#39e75f",
        status_bg="#05080d", status_fg="#eef3f8",
    ),
    "Light": dict(
        bg="#e6ecf2", panel="#f8fafc", panel2="#dfe6ee", field="#ffffff", border="#c2cfdc",
        fg="#111820", dim="#566676", btn="#e2e9f0", hover="#cfdcec", btn_border="#a6b6c6",
        on="#1f7fff", accent="#1f7fff", green="#1a9e3f", amber="#b7791f", red="#d93025", tx="#d92b2b",
        freq="#0b8a36", freq_dim="#93c4a2", gold="#9a6700", title="#8f131a", profile="#0b8a36",
        po="#e02424", alc="#2b8be6", alc_over="#e07800", voice="#1f6fd1", level="#2b7de9",
        go="#2ee06e", go_fg="#000000",
        header="#1c3553", header_fg="#ffffff", header_val="#3dff7a",
        status_bg="#1c3553", status_fg="#ffffff",
    ),
}
C = dict(THEMES["Dark"])      # live palette; App switches it with C.update(THEMES[name])

# Meter "HUD" look (mini meter and the main Meters panel), the same in both themes.
HUD = dict(top="#101a28", bottom="#05080d", panel="#0a1018", edge="#2a4a66", grip="#5b8fbf",
           track="#0a121c", track_edge="#1d3248", tick="#5a7fa3", tick_txt="#dbe5ee", label="#f2c14e",
           value="#39ff7a", value_dim="#2f6b3c", bar_dim="#34465a", hint="#d6e4f0", close="#d6e4f0",
           green="#39ff7a", yellow="#ffd23f", red="#ff4d3a")
S_ZONES = ((0.5, "green"), (0.5 + 20 / 120, "yellow"), (1.0, "red"))   # S-meter colours: to S9, to +20, above

POLL_S = 0.25          # flrig poll interval
TOUCH_HOLD_S = 1.2     # after you change something, ignore stale poll values this long

FREQ_MIN, FREQ_MAX = 30_000, 74_800_000   # widest range either radio tunes
FREQ_REPEAT_DELAY_MS, FREQ_REPEAT_MS = 400, 90   # hold a digit to keep stepping

# Meter scales: (fraction of bar, label)
S_TICKS = [(n / 9 * 0.5, str(n)) for n in (1, 3, 5, 7, 9)] + [(0.5 + d / 120, f"+{d}") for d in (20, 40, 60)]
SWR_TICKS = [((s - 1) / 2, t) for s, t in ((1, "1"), (1.5, "1.5"), (2, "2"), (2.5, "2.5"), (3, "3+"))]
ALC_TICKS = [(f, str(int(f * 100))) for f in (0, 0.25, 0.5, 0.75, 1)]


def po_ticks(pmax):
    return [(f, str(round(pmax * f))) for f in (0, 0.25, 0.5, 0.75, 1)]

# (band, low Hz, high Hz, default voice dial, default data dial)  - US band plan
BANDS = [
    ("160", 1_800_000, 2_000_000, 1_900_000, 1_840_000),
    ("80", 3_500_000, 4_000_000, 3_850_000, 3_573_000),
    ("60", 5_330_000, 5_410_000, 5_371_500, 5_357_000),
    ("40", 7_000_000, 7_300_000, 7_200_000, 7_074_000),
    ("30", 10_100_000, 10_150_000, None, 10_136_000),
    ("20", 14_000_000, 14_350_000, 14_250_000, 14_074_000),
    ("17", 18_068_000, 18_168_000, 18_140_000, 18_100_000),
    ("15", 21_000_000, 21_450_000, 21_300_000, 21_074_000),
    ("12", 24_890_000, 24_990_000, 24_950_000, 24_915_000),
    ("10", 28_000_000, 29_700_000, 28_400_000, 28_074_000),
    ("6", 50_000_000, 54_000_000, 50_125_000, 50_313_000),
]

DATA_UPPER = ["USB-D", "DATA-U", "D-U", "PKT-U", "USB-D1", "DATA-USB", "USER-U"]
DATA_LOWER = ["LSB-D", "DATA-L", "D-L", "PKT-L", "LSB-D1", "DATA-LSB", "USER-L"]


DEBUG_LOG = os.path.join(DATA_DIR, "rigpanel_debug.log")


def debug_log(text):
    """Small trace of raw CAT traffic for troubleshooting (kept under ~200 KB)."""
    try:
        os.makedirs(DATA_DIR, exist_ok=True)
        if os.path.exists(DEBUG_LOG) and os.path.getsize(DEBUG_LOG) > 200_000:
            os.replace(DEBUG_LOG, DEBUG_LOG + ".old")
        with open(DEBUG_LOG, "a", encoding="utf-8") as f:
            f.write(time.strftime("%Y-%m-%d %H:%M:%S  ") + text + "\n")
    except OSError:
        pass


def open_data_folder(log=None):
    """Show the settings / debug-log folder in Explorer, Files, or Finder."""
    ensure_data_dir()
    try:
        if platform.system() == "Windows":
            os.startfile(DATA_DIR)
        else:
            import subprocess
            env = dict(os.environ)
            if getattr(sys, "frozen", False):
                # the installed (PyInstaller) app points LD_LIBRARY_PATH at its own libraries; the file
                # manager then fails to start (seen on Mint 2026-10-27). Give it the system's back.
                orig = env.pop("LD_LIBRARY_PATH_ORIG", None)
                if orig:
                    env["LD_LIBRARY_PATH"] = orig
                else:
                    env.pop("LD_LIBRARY_PATH", None)
            subprocess.Popen(["open" if platform.system() == "Darwin" else "xdg-open", DATA_DIR],
                             stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, env=env)
        if log:
            log(f"Settings and debug log: {DATA_DIR}")
    except Exception:
        if log:
            log(f"Settings and debug log are in {DATA_DIR}")


def load_config():
    ensure_data_dir()
    cfg = json.loads(json.dumps(DEFAULT_CONFIG))
    try:
        with open(CONFIG_PATH) as f:
            cfg.update(json.load(f))
    except Exception:
        pass
    return cfg


# Settings that belong to one PC (its sound card, flrig address, radio, screen): kept when
# settings are loaded from another PC's file or from "my default".
PC_KEYS = ("host", "port", "rig", "civ_addr", "audio_device", "mini_pos", "lv_pos", "mini_scale",
           "lv_scale", "wf_float_geom", "rs_geom")
MY_DEFAULT_PATH = os.path.join(DATA_DIR, "my_default.json")
BACKUP_PATH = os.path.join(DATA_DIR, "settings_before_load.json")


def write_json(path, data):
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    os.replace(tmp, path)


def save_config(cfg):
    try:
        os.makedirs(DATA_DIR, exist_ok=True)
        tmp = CONFIG_PATH + ".tmp"            # write then rename: a crash can't leave half a file
        with open(tmp, "w") as f:
            json.dump(cfg, f, indent=2)
        os.replace(tmp, CONFIG_PATH)
    except Exception:
        pass


def fmt_freq(hz):
    hz = int(round(hz))
    return f"{hz // 1_000_000}.{(hz // 1000) % 1000:03d}.{hz % 1000:03d}"


def band_of(hz):
    for b in BANDS:
        if b[1] <= hz <= b[2]:
            return b
    return None


def is_data_mode(mode):
    m = mode.upper()
    return "-D" in m or "DATA" in m or "PKT" in m or m.startswith("D-")


VOICE_BASES = ("USB", "LSB", "AM", "FM", "SSB", "NFM", "WFM")
CW_BASES = ("CW", "RTTY")


def memory_kind(mode):
    """Which Voice/Data memory a mode uses: 'data', 'cw' (CW / RTTY, own memory since 11-05a) or 'voice'."""
    m = (mode or "").upper()
    if is_data_mode(m):
        return "data"
    return "cw" if m.split("-")[0] in CW_BASES else "voice"


def mode_kind(mode):
    """'voice' for USB/LSB/AM/FM, 'cw' for CW/RTTY (red in the lists, 11-05e), 'data' for data modes."""
    m = (mode or "").upper()
    if not m or is_data_mode(m):
        return "data"
    base = m.split("-")[0]
    return "voice" if base in VOICE_BASES else ("cw" if base in CW_BASES else "data")


def kind_color(mode):
    return {"voice": C["voice"], "cw": C["red"]}.get(mode_kind(mode), C["freq"])


def parse_hz(text):
    """'2400' -> 2400, '2.4k' -> 2400, '500 Hz' -> 500. None if no number."""
    m = re.search(r"(\d+(?:\.\d+)?)\s*(k)?", str(text), re.I)
    if not m:
        return None
    v = float(m.group(1))
    return int(v * 1000) if m.group(2) else int(v)


def parse_freq_input(text):
    """What an operator types -> Hz.  '7.074' or '7.074 MHz' -> MHz, '7074' -> kHz,
    '7.074.000' or '7074000' -> Hz.  None if it isn't a frequency."""
    t = str(text).strip().lower().replace(",", "").replace(" ", "")
    unit = None
    for suffix, u in (("mhz", "m"), ("khz", "k"), ("hz", "h")):
        if t.endswith(suffix):
            t, unit = t[: -len(suffix)], u
            break
    if t.count(".") >= 2:                     # 7.074.000 style
        t, unit = t.replace(".", ""), unit or "h"
    try:
        v = float(t)
    except ValueError:
        return None
    if unit is None:
        unit = "m" if v < 100 else ("k" if v < 100_000 else "h")
    hz = int(round(v * {"m": 1_000_000, "k": 1_000, "h": 1}[unit]))
    return hz if FREQ_MIN <= hz <= FREQ_MAX else None


def interp(x, pts):
    if x <= pts[0][0]:
        return pts[0][1]
    for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
        if x <= x1:
            return y0 + (y1 - y0) * (x - x0) / (x1 - x0)
    return pts[-1][1]


def swr_from_deflection(d):
    """flrig's older rig.get_swrmeter returns 0-100 needle deflection. Approximate SWR."""
    return interp(d, [(0, 1.0), (12.5, 1.5), (25, 2.0), (37.5, 2.5), (50, 3.0), (75, 5.0), (100, 10.0)])


def s_text(v):
    """flrig S-meter is 0-100 with S9 at 50."""
    if v <= 50:
        return f"S{max(0, round(v / 50 * 9))}"
    return f"S9+{round((v - 50) * 60 / 50)}"


# --------------------------------------------------------------------------
# Rig profiles: the rig-specific controls, sent as raw CAT via rig.cat_string
# --------------------------------------------------------------------------
