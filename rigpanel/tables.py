"""Radio tables: every FT-891 and IC-7300 menu item RigPanel knows, the starting Rig Settings,
starter frequencies and the US voice band plan. Plain data and small helpers -
no radio commands here (those are in radios.py, which loads this module)."""
from .core import *  # noqa: F401,F403

# --------------------------------------------------------------------------
# FT-891 macros: one click sets a group of radio settings (EX menu + mode/width/filters)
# Menu codes, digit counts and values are from Yaesu's FT-891 CAT reference.
# --------------------------------------------------------------------------
def _cut(first, count, step=50):
    """Audio cut-off menus: 00 = OFF, then 01.. = first, first+step, ... Hz."""
    return {0: "OFF", **{i: f"{first + step * (i - 1)} Hz" for i in range(1, count + 1)}}


def _opts(*names):
    return dict(enumerate(names))


_SLOPE = _opts("6 dB/oct", "18 dB/oct")
_OFFON = _opts("DISABLE", "ENABLE")
_PTT = _opts("DAKY", "RTS", "DTR")
_MICSEL = _opts("MIC", "REAR")
_LCUT, _HCUT = _cut(100, 19), _cut(700, 67)
_EQ1 = {0: "OFF", **{i: f"{100 * i} Hz" for i in range(1, 8)}}
_EQ2 = {0: "OFF", **{i: f"{600 + 100 * i} Hz" for i in range(1, 10)}}
_EQ3 = {0: "OFF", **{i: f"{1400 + 100 * i} Hz" for i in range(1, 19)}}
_FILTERS = lambda g, m: {     # LCUT/HCUT freq + slope, same layout in every mode group
    f"{g}01": (f"{m} LCUT FREQ", 2, _LCUT), f"{g}02": (f"{m} LCUT SLOPE", 1, _SLOPE),
    f"{g}03": (f"{m} HCUT FREQ", 2, _HCUT), f"{g}04": (f"{m} HCUT SLOPE", 1, _SLOPE)}

# Every FT-891 menu item. Codes, digit counts and values are from Yaesu's FT-891 CAT
# Operation Reference Book (EX command table). code: (name, digits, values) where values is
# {number: name} or (lo, hi) or (lo, hi, step). A negative lo means the value carries a +/- sign,
# counted in the digits (e.g. "+05"). Labels get their "05-03 " prefix added below.
FT891_MENU = {
    # 01 AGC
    "0101": ("AGC FAST DELAY (ms)", 4, (20, 4000, 20)), "0102": ("AGC MID DELAY (ms)", 4, (20, 4000, 20)),
    "0103": ("AGC SLOW DELAY (ms)", 4, (20, 4000, 20)),
    # 02 DISPLAY
    "0201": ("LCD CONTRAST", 2, (1, 15)), "0202": ("DIMMER BACKLIT", 2, (1, 15)), "0203": ("DIMMER LCD", 2, (1, 15)),
    "0204": ("DIMMER TX/BUSY", 2, (1, 15)), "0205": ("PEAK HOLD", 1, _opts("OFF", "0.5 sec", "1.0 sec", "2.0 sec")),
    "0206": ("ZIN LED", 1, _OFFON), "0207": ("POP-UP MENU", 1, _opts("UPPER", "LOWER")),
    # 03 DVS
    "0301": ("DVS RX OUT LVL", 3, (0, 100)), "0302": ("DVS TX OUT LVL", 3, (0, 100)),
    # 04 KEYER
    "0401": ("KEYER TYPE", 1, _opts("OFF", "BUG", "ELEKEY-A", "ELEKEY-B", "ELEKEY-Y", "ACS")),
    "0402": ("KEYER DOT/DASH", 1, _opts("NOR", "REV")), "0403": ("CW WEIGHT (x0.1)", 2, (25, 45)),
    "0404": ("BEACON INTERVAL (s, 0=OFF)", 3, (0, 690)),
    "0405": ("NUMBER STYLE", 1, _opts("1290", "AUNO", "AUNT", "A2NO", "A2NT", "12NO", "12NT")),
    "0406": ("CONTEST NUMBER", 4, (0, 9999)),
    **{f"04{n + 6:02d}": (f"CW MEMORY {n}", 1, _opts("TEXT", "MESSAGE")) for n in range(1, 6)},
    # 05 GENERAL
    "0501": ("NB WIDTH", 1, _opts("1 ms", "3 ms", "10 ms")), "0502": ("NB REJECTION", 1, _opts("10 dB", "30 dB", "50 dB")),
    "0503": ("NB LEVEL", 2, (0, 10)), "0504": ("BEEP LEVEL", 3, (0, 100)), "0505": ("RF/SQL VR", 1, _opts("RF", "SQL")),
    "0506": ("CAT RATE", 1, _opts("4800", "9600", "19200", "38400")),
    "0507": ("CAT TOT", 1, _opts("10 ms", "100 ms", "1000 ms", "3000 ms")), "0508": ("CAT RTS", 1, _OFFON),
    "0509": ("MEM GROUP", 1, _OFFON), "0510": ("FM SETTING", 1, _OFFON), "0511": ("REC SETTING", 1, _OFFON),
    "0512": ("ATAS SETTING", 1, _OFFON), "0513": ("QUICK SPL FREQ (kHz)", 3, (-20, 20)),
    "0514": ("TX TOT (min, 0=OFF)", 2, (0, 30)), "0515": ("MIC SCAN", 1, _OFFON),
    "0516": ("MIC SCAN RESUME", 1, _opts("PAUSE", "TIME")), "0517": ("REF FREQ ADJ", 3, (-25, 25)),
    "0518": ("CLAR SELECT", 1, _opts("RX", "TX", "TRX")),
    "0519": ("APO", 1, _opts("OFF", "1 h", "2 h", "4 h", "6 h", "8 h", "10 h", "12 h")),
    "0520": ("FAN CONTROL", 1, _opts("NORMAL", "CONTEST")),
    # 06 MODE AM
    **_FILTERS("06", "AM"), "0605": ("AM MIC SELECT", 1, _MICSEL), "0606": ("AM OUT LEVEL", 3, (0, 100)),
    "0607": ("AM PTT SELECT", 1, _PTT),
    # 07 MODE CW
    **_FILTERS("07", "CW"), "0705": ("CW OUT LEVEL", 3, (0, 100)), "0706": ("CW AUTO MODE", 1, _opts("OFF", "50M", "ON")),
    "0707": ("CW BFO", 1, _opts("USB", "LSB", "AUTO")), "0708": ("CW BK-IN TYPE", 1, _opts("SEMI", "FULL")),
    "0709": ("CW BK-IN DELAY (ms)", 4, (30, 3000, 10)), "0710": ("CW WAVE SHAPE", 1, {1: "2 ms", 2: "4 ms"}),
    "0711": ("CW FREQ DISPLAY", 1, _opts("FREQ", "PITCH")), "0712": ("PC KEYING", 1, _opts("OFF", "DAKY", "RTS", "DTR")),
    "0713": ("QSK DELAY TIME", 1, _opts("15 ms", "20 ms", "25 ms", "30 ms")),
    # 08 MODE DATA
    "0801": ("DATA MODE", 1, _opts("PSK", "OTHERS")), "0802": ("PSK TONE", 1, _opts("1000 Hz", "1500 Hz", "2000 Hz")),
    "0803": ("OTHER DISP (Hz)", 5, (-3000, 3000, 10)), "0804": ("OTHER SHIFT (Hz)", 5, (-3000, 3000, 10)),
    "0805": ("DATA LCUT FREQ", 2, _LCUT), "0806": ("DATA LCUT SLOPE", 1, _SLOPE),
    "0807": ("DATA HCUT FREQ", 2, _HCUT), "0808": ("DATA HCUT SLOPE", 1, _SLOPE),
    "0809": ("DATA IN SELECT", 1, _MICSEL), "0810": ("DATA PTT SELECT", 1, _PTT),
    "0811": ("DATA OUT LEVEL", 3, (0, 100)), "0812": ("DATA BFO", 1, _opts("USB", "LSB")),
    # 09 MODE FM
    "0901": ("FM MIC SELECT", 1, _MICSEL), "0902": ("FM OUT LEVEL", 3, (0, 100)), "0903": ("PKT PTT SELECT", 1, _PTT),
    "0904": ("RPT SHIFT 28MHz (kHz)", 4, (0, 1000, 10)), "0905": ("RPT SHIFT 50MHz (kHz)", 4, (0, 4000, 10)),
    "0906": ("DCS POLARITY", 1, _opts("Tn-Rn", "Tn-Riv", "Tiv-Rn", "Tiv-Riv")),
    # 10 MODE RTTY
    **_FILTERS("10", "RTTY"), "1005": ("RTTY SHIFT PORT", 1, _opts("SHIFT", "DTR", "RTS")),
    "1006": ("RTTY POLARITY-R", 1, _opts("NOR", "REV")), "1007": ("RTTY POLARITY-T", 1, _opts("NOR", "REV")),
    "1008": ("RTTY OUT LEVEL", 3, (0, 100)), "1009": ("RTTY SHIFT FREQ", 1, _opts("170 Hz", "200 Hz", "425 Hz", "850 Hz")),
    "1010": ("RTTY MARK FREQ", 1, _opts("1275 Hz", "2125 Hz")), "1011": ("RTTY BFO", 1, _opts("USB", "LSB")),
    # 11 MODE SSB
    **_FILTERS("11", "SSB"), "1105": ("SSB MIC SELECT", 1, _MICSEL), "1106": ("SSB OUT LEVEL", 3, (0, 100)),
    "1107": ("SSB BFO", 1, _opts("USB", "LSB", "AUTO")), "1108": ("SSB PTT SELECT", 1, _PTT),
    "1109": ("SSB TX BPF", 1, _opts("100-3000", "100-2900", "200-2800", "300-2700", "400-2600")),
    # 12 RX DSP
    "1201": ("APF WIDTH", 1, _opts("NARROW", "MEDIUM", "WIDE")), "1202": ("CONTOUR LEVEL", 3, (-40, 20)),
    "1203": ("CONTOUR WIDTH", 2, (1, 11)), "1204": ("IF NOTCH WIDTH", 1, _opts("NARROW", "WIDE")),
    # 13 SCOPE
    "1301": ("SCP START CYCLE", 1, _opts("OFF", "3 sec", "5 sec", "10 sec")),
    "1302": ("SCP SPAN FREQ", 2, _opts("37.5 kHz", "75 kHz", "150 kHz", "375 kHz", "750 kHz")),
    # 14 TUNING
    "1401": ("QUICK DIAL", 1, _opts("50 kHz", "100 kHz", "500 kHz")), "1402": ("SSB DIAL STEP", 1, _opts("2 Hz", "5 Hz", "10 Hz")),
    "1403": ("AM DIAL STEP", 1, _opts("10 Hz", "100 Hz")), "1404": ("FM DIAL STEP", 1, _opts("10 Hz", "100 Hz")),
    "1405": ("DIAL STEP", 1, _opts("2 Hz", "5 Hz", "10 Hz")),
    "1406": ("AM CH STEP", 1, _opts("2.5 kHz", "5 kHz", "9 kHz", "10 kHz", "12.5 kHz", "25 kHz")),
    "1407": ("FM CH STEP", 1, _opts("5 kHz", "6.25 kHz", "10 kHz", "12.5 kHz", "15 kHz", "20 kHz", "25 kHz")),
    # 15 TX AUDIO (equalizers: EQ = mic EQ off, P-EQ = processor on)
    **{f"15{3 * i + 1:02d}": (f"{pre}EQ{n} FREQ", 2, fr) for i, (pre, n, fr) in enumerate(
        [("", 1, _EQ1), ("", 2, _EQ2), ("", 3, _EQ3), ("P-", 1, _EQ1), ("P-", 2, _EQ2), ("P-", 3, _EQ3)])},
    **{f"15{3 * i + 2:02d}": (f"{pre}EQ{n} LEVEL", 3, (-20, 10)) for i, (pre, n) in enumerate(
        [("", 1), ("", 2), ("", 3), ("P-", 1), ("P-", 2), ("P-", 3)])},
    **{f"15{3 * i + 3:02d}": (f"{pre}EQ{n} BWTH", 2, (1, 10)) for i, (pre, n) in enumerate(
        [("", 1), ("", 2), ("", 3), ("P-", 1), ("P-", 2), ("P-", 3)])},
    # 16 TX GNRL
    "1601": ("HF SSB PWR (W)", 3, (5, 100)), "1602": ("HF AM PWR (W)", 3, (5, 40)),
    "1603": ("HF PWR (W) - data/CW", 3, (5, 100)), "1604": ("50M SSB PWR (W)", 3, (5, 100)),
    "1605": ("50M AM PWR (W)", 3, (5, 40)), "1606": ("50M PWR (W)", 3, (5, 100)),
    "1607": ("SSB MIC GAIN", 3, (0, 100)), "1608": ("AM MIC GAIN", 3, (0, 100)), "1609": ("FM MIC GAIN", 3, (0, 100)),
    "1610": ("DATA MIC GAIN", 3, (0, 100)), "1611": ("SSB DATA GAIN", 3, (0, 100)), "1612": ("AM DATA GAIN", 3, (0, 100)),
    "1613": ("FM DATA GAIN", 3, (0, 100)), "1614": ("DATA DATA GAIN", 3, (0, 100)),
    "1615": ("TUNER SELECT", 1, _opts("OFF", "EXTERNAL", "ATAS", "LAMP")), "1616": ("VOX SELECT", 1, _opts("MIC", "DATA")),
    "1617": ("VOX GAIN", 3, (0, 100)), "1618": ("VOX DELAY (ms)", 4, (30, 3000, 10)),
    "1619": ("ANTI VOX GAIN", 3, (0, 100)), "1620": ("DATA VOX GAIN", 3, (0, 100)),
    "1621": ("DATA VOX DELAY (ms)", 4, (30, 3000, 10)), "1622": ("ANTI DVOX GAIN", 3, (0, 100)),
    "1623": ("EMERGENCY FREQ TX", 1, _OFFON),
    # 17 RESET is left out on purpose: the radio doesn't answer it over CAT (flrig waits 6 s)
    # and sending it would reset the radio.
    # 18 VERSION - read only
    "1801": ("MAIN VERSION", 4, (0, 9999)), "1802": ("DSP VERSION", 4, (0, 9999)), "1803": ("LCD VERSION", 4, (0, 9999)),
}
FT891_MENU = {code: (f"{code[:2]}-{code[2:]} {name}", digits, vals)
              for code, (name, digits, vals) in sorted(FT891_MENU.items())}
FT891_MENU["PROC"] = ("PROC (speech processor)", 1, {0: "OFF", 1: "ON"})     # PR0n; - not an EX menu
FT891_MENU["PROCLV"] = ("PROC level", 3, (0, 100))                           # PLnnn;
# Names kept exactly as before for the menus RigPanel already used (saved files show them)
FT891_MENU["1603"] = ("16-03 HF PWR (W) - data/CW", 3, (5, 100))
# Groups as the radio's own MENU shows them (the All Menus view of Edit Rig Settings)
FT891_SECTIONS = [("01", "AGC"), ("02", "DISPLAY"), ("03", "DVS"), ("04", "KEYER"), ("05", "GENERAL"),
                  ("06", "MODE AM"), ("07", "MODE CW"), ("08", "MODE DAT"), ("09", "MODE FM"),
                  ("10", "MODE RTTY"), ("11", "MODE SSB"), ("12", "RX DSP"), ("13", "SCOPE"),
                  ("14", "TUNING"), ("15", "TX AUDIO"), ("16", "TX GNRL"), ("18", "VERSION")]
# Shown but never changed by RigPanel: changing the CAT link settings would cut flrig off from
# the radio; 18-xx are version numbers. (All 155 items checked on the operator's radio 2026-10-25.)
FT891_LOCKED = {"0506", "0507", "0508", "1801", "1802", "1803"}
MACRO_FILTERS = {"NB": "nb", "DNR": "nr", "DNF": "anf", "NOTCH": "notch"}   # -> YaesuProfile control keys
BKIN_VALUES = ("OFF", "SEMI", "FULL")      # Rig Settings item BKIN -> control "bkin" 0/1/2 (11-09a)
MACRO_ITEMS = ["MODE", "WIDTH", "BKIN", "0503", "0801", "0809", "0810", "0811", "0812", "1105", "1106",
               "1601", "1603", "1616", "PROC", "PROCLV", "NB", "DNR", "DNF", "NOTCH"]
MACRO_LABELS = {"MODE": "Mode", "WIDTH": "Width (Hz)", "NB": "NB (noise blanker)", "DNR": "DNR",
                "DNF": "DNF (auto notch)", "NOTCH": "Notch", "BKIN": "BKIN (CW break-in)"}
SSB_BY_BAND = "LSB/USB (by band)"
SKIP = "\u2014"                     # an em dash = "don't change this one"
# Every setting a macro can include, in the order they're sent. Mode goes first (the
# width table depends on it); 05-12 ATAS goes before 16-15 TUNER SELECT so the ATAS
# supply is off before another tuner is chosen.
COMMON_ITEMS = MACRO_ITEMS + ["0512", "1615"]          # the Common view (the list RigPanel always had)
ALL_ITEMS = (["MODE", "WIDTH", "BKIN"]
             + [c for c in FT891_MENU if c not in FT891_LOCKED and c not in ("0512", "1615")]
             + list(MACRO_FILTERS) + ["0512", "1615"])
GROUPS = ("Operating", "Antenna")
DEFAULT_MACRO_LIST = [      # starting set; examples/KW3KW_settings.json has a full working station
    {"name": "Voice", "group": "Operating", "show": True,
     "items": {"MODE": SSB_BY_BAND, "WIDTH": "2400", "1105": "MIC", "1616": "MIC"}},
    {"name": "Data", "group": "Operating", "show": True,
     "items": {"MODE": "DATA-U", "WIDTH": "3000", "0503": "0", "0801": "OTHERS", "0809": "REAR",
               "0810": "DAKY", "0811": "35", "0812": "USB", "1106": "85",
               "1616": "DATA", "NB": "OFF", "DNR": "OFF", "DNF": "OFF", "NOTCH": "OFF"}},
    {"name": "ATAS", "group": "Antenna", "show": True, "items": {"0512": "ENABLE", "1615": "ATAS"}},
    {"name": "External Tuner", "group": "Antenna", "show": True, "items": {"0512": "DISABLE", "1615": "EXTERNAL"}},
    {"name": "No Tuner", "group": "Antenna", "show": True, "items": {"0512": "DISABLE", "1615": "OFF"}},
]


# --------------------------------------------------------------------------
# IC-7300 macros: same idea, CI-V commands instead of EX menus. Menu item numbers
# (1A 05 00xx) checked on the operator's radio with icom_check.py (2026-10-23).
# --------------------------------------------------------------------------
IC7300_MENU = {         # code: (label, digits, {value: name} or (lo, hi)) - same shape as FT891_MENU
    "0059": ("ACC/USB Output Select", 1, {0: "AF", 1: "IF"}),
    "0060": ("ACC/USB AF Output Level %", 3, (0, 100)),
    "0064": ("ACC MOD Level %", 3, (0, 100)),
    "0065": ("USB MOD Level %", 3, (0, 100)),
    "0066": ("DATA OFF MOD (USB, LSB...)", 1, {0: "MIC", 1: "ACC", 2: "MIC,ACC", 3: "USB"}),
    "0067": ("DATA MOD (USB-D...)", 1, {0: "MIC", 1: "ACC", 2: "MIC,ACC", 3: "USB"}),
    "COMP": ("COMP (speech compressor)", 1, {0: "OFF", 1: "ON"}),
    "COMPLV": ("COMP level", 2, (0, 10)),
    "TBW": ("SSB TX bandwidth", 1, {0: "WIDE", 1: "MID", 2: "NAR"}),
    "MONI": ("Monitor", 1, {0: "OFF", 1: "ON"}),
    "VOX": ("VOX", 1, {0: "OFF", 1: "ON"}),
    "AGC": ("AGC", 1, {1: "FAST", 2: "MID", 3: "SLOW"}),
}
IC7300_MENU["0066"] = ("DATA OFF MOD (USB, LSB...)", 1, {0: "MIC", 1: "ACC", 2: "MIC,ACC", 3: "USB", 4: "MIC,USB"})
IC7300_MENU["0067"] = ("DATA MOD (USB-D...)", 1, {0: "MIC", 1: "ACC", 2: "MIC,ACC", 3: "USB", 4: "MIC,USB"})
# code -> (CI-V command bytes, kind): "byte" = one data byte; "pct" = 0000-0255 shown as 0-100 %;
# "ten" = 0000-0255 shown as 0-10 (the radio's COMP level)
IC7300_CIV = {
    "0059": ((0x1A, 0x05, 0x00, 0x59), "byte"), "0060": ((0x1A, 0x05, 0x00, 0x60), "pct"),
    "0064": ((0x1A, 0x05, 0x00, 0x64), "pct"), "0065": ((0x1A, 0x05, 0x00, 0x65), "pct"),
    "0066": ((0x1A, 0x05, 0x00, 0x66), "byte"), "0067": ((0x1A, 0x05, 0x00, 0x67), "byte"),
    "COMP": ((0x16, 0x44), "byte"), "COMPLV": ((0x14, 0x0E), "ten"), "TBW": ((0x16, 0x58), "byte"),
    "MONI": ((0x16, 0x45), "byte"), "VOX": ((0x16, 0x46), "byte"), "AGC": ((0x16, 0x12), "byte"),
}


# --------------------------------------------------------------------------
# Every IC-7300 SET menu item RigPanel can show (All Menus view): CI-V 1A 05 0001-0197.
# From Icom's IC-7300 CI-V table; numbers and values checked against the operator's radio
# (ic7300_menu_dump.py, 2026-10-26: e.g. 0091 = his opening message, 0014/15/16 = 100-2900,
# 300-2700, 500-2500). One-byte values are BCD, so the dicts are keyed by the raw byte.
# Left out: HPF/LPF pairs, split offsets, opening text, date/time, colours, scope edges.
# --------------------------------------------------------------------------
def _ic_opts(*names):
    return dict(enumerate(names))


def _ic_bcd(lo, hi, fmt=str):
    return {int(f"{n:02d}", 16): fmt(n) for n in range(lo, hi + 1)}


_IC_OFFON = _ic_opts("OFF", "ON")
_IC_TONE = _ic_bcd(0, 10, lambda n: "0" if n == 5 else f"{n - 5:+d}")
_IC_TBW = {(h << 4) | lo: f"{(100, 200, 300, 500)[lo]}-{(2500, 2700, 2800, 2900)[h]}"
           for lo in range(4) for h in range(4)}             # high nibble = upper edge, low = lower edge
_IC_DELAY = _ic_opts("OFF", "10 ms", "15 ms", "20 ms", "25 ms", "30 ms")
_IC_PTT = _ic_opts("OFF", "DTR", "RTS")
_IC_ITEMS = [   # item, name, kind, values ("pct" -> 0-100 %)
    (2, "SSB RX bass", "byte", _IC_TONE), (3, "SSB RX treble", "byte", _IC_TONE),
    (5, "AM RX bass", "byte", _IC_TONE), (6, "AM RX treble", "byte", _IC_TONE),
    (8, "FM RX bass", "byte", _IC_TONE), (9, "FM RX treble", "byte", _IC_TONE),
    (12, "SSB TX bass", "byte", _IC_TONE), (13, "SSB TX treble", "byte", _IC_TONE),
    (14, "SSB TBW WIDE (Hz)", "byte", _IC_TBW), (15, "SSB TBW MID (Hz)", "byte", _IC_TBW),
    (16, "SSB TBW NAR (Hz)", "byte", _IC_TBW),
    (17, "AM TX bass", "byte", _IC_TONE), (18, "AM TX treble", "byte", _IC_TONE),
    (19, "FM TX bass", "byte", _IC_TONE), (20, "FM TX treble", "byte", _IC_TONE),
    (196, "SSB-D TBW (Hz)", "byte", _IC_TBW),
    (21, "Beep level", "pct", None), (22, "Beep", "byte", _IC_OFFON), (23, "Confirmation beep", "byte", _IC_OFFON),
    (24, "Band edge beep", "byte", _ic_opts("OFF", "ON (default)", "ON (user)", "ON (user) & TX limit")),
    (25, "RF/SQL control", "byte", _ic_opts("AUTO", "SQL", "RF+SQL")),
    (26, "TX delay HF", "byte", _IC_DELAY), (27, "TX delay 50 MHz", "byte", _IC_DELAY),
    (29, "Time-out timer", "byte", _ic_opts("OFF", "3 min", "5 min", "10 min", "20 min", "30 min")),
    (30, "Quick split", "byte", _IC_OFFON), (33, "Split lock", "byte", _IC_OFFON),
    (34, "Tuner switch", "byte", _ic_opts("MANUAL", "AUTO")), (35, "PTT tune", "byte", _IC_OFFON),
    (36, "RTTY mark", "byte", _ic_opts("1275 Hz", "1615 Hz", "2125 Hz")),
    (37, "RTTY shift", "byte", _ic_opts("170 Hz", "200 Hz", "425 Hz")),
    (38, "RTTY keying polarity", "byte", _ic_opts("Normal", "Reverse")),
    (39, "Speech language", "byte", _ic_opts("English", "Japanese")),
    (40, "Speech speed", "byte", _ic_opts("Slow", "Fast")), (41, "S-level speech", "byte", _IC_OFFON),
    (42, "Mode speech", "byte", _IC_OFFON), (43, "Speech level", "pct", None),
    (44, "SPEECH/LOCK switch", "byte", _ic_opts("SPEECH/LOCK", "LOCK/SPEECH")),
    (45, "Lock function", "byte", _ic_opts("MAIN DIAL", "PANEL")),
    (46, "Memo pad numbers", "byte", _ic_opts("5", "10")),
    (47, "MAIN DIAL auto TS", "byte", _ic_opts("OFF", "Low", "High")),
    (48, "MIC up/down speed", "byte", _ic_opts("Slow", "Fast")), (49, "Quick RIT/dTX clear", "byte", _IC_OFFON),
    (50, "Notch (SSB)", "byte", _ic_opts("Auto", "Manual", "Auto/Manual")),
    (51, "Notch (AM)", "byte", _ic_opts("Auto", "Manual", "Auto/Manual")),
    (52, "SSB/CW synchronous tuning", "byte", _IC_OFFON), (53, "CW normal side", "byte", _ic_opts("LSB", "USB")),
    (54, "Screen capture [POWER] switch", "byte", _IC_OFFON),
    (55, "Screen capture file type", "byte", _ic_opts("PNG", "BMP")),
    (56, "Keyboard type", "byte", _ic_opts("Ten-key", "Full keyboard")),
    (57, "Full keyboard layout", "byte", _ic_opts("English", "German", "French")),
    (58, "REF adjust (frequency)", "pct", None),
    (59, None, "byte", None), (60, None, "pct", None),
    (61, "ACC/USB AF SQL", "byte", _ic_opts("OFF (open)", "ON")),
    (62, "ACC/USB AF beep/speech output", "byte", _IC_OFFON),
    (63, "ACC/USB IF output level %", "pct", None), (64, None, "pct", None), (65, None, "pct", None),
    (66, None, "byte", None), (67, None, "byte", None),
    (68, "External keypad VOICE", "byte", _IC_OFFON), (69, "External keypad KEYER", "byte", _IC_OFFON),
    (70, "External keypad RTTY", "byte", _IC_OFFON),
    (71, "CI-V transceive", "byte", _IC_OFFON), (73, "CI-V output (for ANT)", "byte", _IC_OFFON),
    (74, "CI-V USB port", "byte", _ic_opts("Link to REMOTE", "Unlink from REMOTE")),
    (75, "CI-V USB echo back", "byte", _IC_OFFON),
    (76, "USB serial function", "byte", _ic_opts("CI-V", "RTTY decode")),
    (77, "RTTY decode baud rate", "byte", _ic_opts("4800", "9600", "19200", "38400")),
    (78, "USB SEND (PTT)", "byte", _IC_PTT), (79, "USB keying (CW)", "byte", _IC_PTT),
    (80, "USB keying (RTTY)", "byte", _IC_PTT),
    (81, "LCD backlight %", "pct", None), (82, "Display type", "byte", _ic_opts("A", "B")),
    (83, "Display font", "byte", _ic_opts("Basic", "Round")), (84, "Meter peak hold", "byte", _IC_OFFON),
    (85, "Memory name", "byte", _IC_OFFON), (86, "MN-Q popup", "byte", _IC_OFFON),
    (87, "BW popup (PBT)", "byte", _IC_OFFON), (88, "BW popup (FIL)", "byte", _IC_OFFON),
    (89, "Screen saver", "byte", _ic_opts("OFF", "15 min", "30 min", "60 min")),
    (90, "Opening message", "byte", _IC_OFFON), (92, "Power ON check", "byte", _IC_OFFON),
    (93, "Display language", "byte", _ic_opts("English", "Japanese")),
    (97, "Scope during TX", "byte", _IC_OFFON), (98, "Scope max hold", "byte", _ic_opts("OFF", "10 s", "ON")),
    (99, "Scope CENTER type", "byte", _ic_opts("Filter center", "Carrier point center", "Carrier (abs. freq)")),
    (100, "Scope marker position", "byte", _ic_opts("Filter center", "Carrier point")),
    (101, "Scope VBW", "byte", _ic_opts("Narrow", "Wide")),
    (102, "Scope averaging", "byte", _ic_opts("OFF", "2", "3", "4")),
    (103, "Scope waveform type", "byte", _ic_opts("Fill", "Fill+Line")),
    (107, "Waterfall display", "byte", _IC_OFFON), (108, "Waterfall speed", "byte", _ic_opts("Slow", "Mid", "Fast")),
    (109, "Waterfall size (expand)", "byte", _ic_opts("Small", "Mid", "Large")),
    (110, "Waterfall peak color level", "byte", _ic_bcd(0, 7, lambda n: f"Grid {n + 1}")),
    (111, "Waterfall marker auto-hide", "byte", _IC_OFFON),
    (151, "Audio scope waveform type", "byte", _ic_opts("Fill", "Fill+Line")),
    (153, "Audio scope waterfall", "byte", _IC_OFFON),
    (155, "Contest number style", "byte", _ic_opts("Normal", "190->ANO", "190->ANT", "90->NO", "90->NT")),
    (156, "Count-up trigger", "byte", _ic_bcd(1, 8, lambda n: f"M{n}")),
    (158, "CW side tone level %", "pct", None), (159, "Side tone level limit", "byte", _IC_OFFON),
    (160, "Keyer repeat time (s)", "byte", _ic_bcd(1, 60)),
    (161, "Dot/dash ratio", "byte", _ic_bcd(28, 45, lambda n: f"1:1:{n / 10:.1f}")),
    (162, "Rise time", "byte", _ic_opts("2 ms", "4 ms", "6 ms", "8 ms")),
    (163, "Paddle polarity", "byte", _ic_opts("Normal", "Reverse")),
    (164, "Key type", "byte", _ic_opts("Straight", "Bug-key", "Paddle")),
    (165, "MIC up/down keyer", "byte", _IC_OFFON),
    (166, "RTTY FFT averaging", "byte", _ic_opts("OFF", "2", "3", "4")),
    (168, "RTTY decode USOS", "byte", _IC_OFFON), (169, "RTTY new line code", "byte", _ic_opts("CR,LF,CR+LF", "CR+LF")),
    (170, "RTTY TX USOS", "byte", _IC_OFFON), (173, "RTTY log", "byte", _IC_OFFON),
    (174, "RTTY log file type", "byte", _ic_opts("Text", "HTML")), (175, "RTTY time stamp", "byte", _IC_OFFON),
    (176, "RTTY time stamp clock", "byte", _ic_opts("Local", "UTC")), (177, "RTTY frequency stamp", "byte", _IC_OFFON),
    (178, "Scan speed", "byte", _ic_opts("Slow", "Fast")), (179, "Scan resume", "byte", _IC_OFFON),
    (180, "Voice TX auto monitor", "byte", _IC_OFFON), (181, "Voice TX repeat time (s)", "byte", _ic_bcd(1, 15)),
    (182, "QSO recorder mode", "byte", _ic_opts("TX&RX", "RX only")),
    (183, "QSO recorder TX audio", "byte", _ic_opts("MIC", "TX monitor")),
    (184, "QSO recorder squelch", "byte", _ic_opts("Always", "Squelch auto")),
    (185, "QSO record file split", "byte", _IC_OFFON), (186, "PTT auto recording", "byte", _IC_OFFON),
    (187, "PTT auto pre-recording", "byte", _ic_opts("OFF", "5 s", "10 s", "15 s")),
    (188, "QSO play skip time", "byte", _ic_opts("3 s", "5 s", "10 s", "30 s")),
    (189, "NB depth", "byte", _ic_bcd(0, 9, lambda n: str(n + 1))), (190, "NB width %", "pct", None),
    (191, "VOX delay (s)", "byte", _ic_bcd(0, 20, lambda n: f"{n / 10:.1f}")),
    (192, "VOX voice delay", "byte", _ic_opts("OFF", "Short", "Mid", "Long")),
    (193, "MF band ATT", "byte", _IC_OFFON),
    (195, "Voice TX level %", "pct", None), (197, "USB inhibit timer", "byte", _IC_OFFON),
]
for _n, _name, _kind, _vals in _IC_ITEMS:
    _code = f"{_n:04d}"
    _cmd = (0x1A, 0x05, int(f"{_n // 100:02d}", 16), int(f"{_n % 100:02d}", 16))
    if _code not in IC7300_MENU:
        if _kind == "pct":
            IC7300_MENU[_code] = (_name if _name.endswith("%") else f"{_name} %", 3, (0, 100))
        else:
            IC7300_MENU[_code] = (_name, 2, _vals)
    IC7300_CIV.setdefault(_code, (_cmd, _kind))
# Shown, but RigPanel never changes them: the CI-V / USB link (changing them would cut flrig off
# from the radio or key the transmitter), the frequency reference, and a read-only item.
IC7300_LOCKED = {"0058", "0071", "0073", "0074", "0075", "0076", "0077", "0078", "0079", "0080"}
IC7300_READONLY = {"0074"}
# Groups as the radio's own MENU > SET shows them
IC7300_SECTIONS = [("TONE", "Tone Control / TBW"), ("FUNC", "Function"), ("CONN", "Connectors"),
                   ("DISP", "Display"), ("SCOPE", "Scope"), ("KEYER", "Keyer / Contest"), ("RTTY", "RTTY"),
                   ("REC", "Scan / Voice / Recorder"), ("MORE", "NB / VOX / More")]


def ic7300_section(code):
    if not code.isdigit():
        return None
    n = int(code)
    for top, sec in ((20, "TONE"), (58, "FUNC"), (80, "CONN"), (93, "DISP"), (154, "SCOPE"), (165, "KEYER"),
                     (177, "RTTY"), (188, "REC"), (199, "MORE")):
        if n <= top:
            return "TONE" if n == 196 else sec
    return None


IC7300_FILTERS = {"NB": "nb", "NR": "nr", "NOTCH": "notch", "AUTO NOTCH": "anf", "IP+": "ipplus"}
IC7300_ITEMS = ["MODE", "FILTER", "WIDTH", "BKIN", "0066", "0067", "0065", "0064", "0060", "0059", "COMP", "COMPLV", "TBW",
                "MONI", "VOX", "AGC", "NB", "NR", "NOTCH", "AUTO NOTCH", "IP+"]
IC7300_ALL_ITEMS = (IC7300_ITEMS[:IC7300_ITEMS.index("NB")]
                    + [c for c in sorted(IC7300_MENU) if c.isdigit() and c not in IC7300_ITEMS]
                    + IC7300_ITEMS[IC7300_ITEMS.index("NB"):])
IC7300_LABELS = {"BKIN": "BKIN (CW break-in)", "MODE": "Mode", "FILTER": "Filter (FIL1/2/3)", "WIDTH": "Width (Hz)", "NB": "NB (noise blanker)", "NR": "NR (noise reduction)",
                 "NOTCH": "Notch", "AUTO NOTCH": "Auto Notch", "IP+": "IP+"}
IC7300_DEFAULT_MACROS = [   # a typical voice / data pair (based on KW3KW's setup guides)
    {"name": "Voice", "group": "Operating", "show": True,
     "items": {"MODE": SSB_BY_BAND, "WIDTH": "2400", "0066": "MIC", "COMP": "ON", "COMPLV": "3",
               "TBW": "WIDE", "MONI": "OFF", "VOX": "OFF", "AGC": "MID"}},
    {"name": "Data", "group": "Operating", "show": True,
     "items": {"MODE": "USB-D", "WIDTH": "3000", "0066": "USB", "0067": "USB", "0065": "40", "0060": "50",
               "0059": "AF", "COMP": "OFF", "MONI": "OFF", "VOX": "OFF", "AGC": "FAST", "NB": "OFF", "NR": "OFF"}},
]


# Starting stored frequencies, given to a PC the first time each radio connects - only if
# that PC has none of its own (App._seed_radio_defaults). FT8 and JS8 calling frequencies.
def _mems(rows):
    return [{"hz": hz, "mode": mode, "name": name} for hz, mode, name in rows]


# Starter frequencies (given once per radio on a PC with no stored frequencies). US band plan.
# Voice starts / ends sit 3 kHz inside the edge so the whole LSB / USB signal is in the segment;
# where General and Extra differ, both are listed and labeled.
_DIGITAL = [(1842000, "JS8 160M"), (3573000, "FT8 80M"), (3578000, "JS8 80M"), (7074000, "FT8 40M"),
            (7078000, "JS8 40M"), (10130000, "JS8 30M"), (10136000, "FT8 30M"), (14074000, "FT8 20M"),
            (14078000, "JS8 20M"), (18104000, "JS8 17M"), (21074000, "FT8 15M"), (21078000, "JS8 15M"),
            (24922000, "JS8 12M"), (28074000, "FT8 10M"), (28078000, "JS8 10M")]
_CW = [(1802500, "W1AW CW 160M"), (3581500, "W1AW CW 80M"), (7047500, "W1AW CW 40M"), (14047500, "W1AW CW 20M"),
       (18097500, "W1AW CW 17M"), (21067500, "W1AW CW 15M"), (28067500, "W1AW CW 10M")]
_VOICE = [(1803000, "Voice 160M Start"), (1997000, "Voice 160M End"),
          (3603000, "Voice 80M Start Extra"), (3803000, "Voice 80M Start General"), (3997000, "Voice 80M End"),
          (7128000, "Voice 40M Start Extra"), (7178000, "Voice 40M Start General"), (7297000, "Voice 40M End"),
          (14150000, "Voice 20M Start Extra"), (14225000, "Voice 20M Start General"), (14347000, "Voice 20M End"),
          (18110000, "Voice 17M Start"), (18165000, "Voice 17M End"),
          (21200000, "Voice 15M Start Extra"), (21275000, "Voice 15M Start General"), (21447000, "Voice 15M End"),
          (24930000, "Voice 12M Start"), (24987000, "Voice 12M End"),
          (28300000, "Voice 10M Start"), (29697000, "Voice 10M End")]


def _starters(data, cw):
    rows = [(hz, data, n) for hz, n in _DIGITAL] + [(hz, cw, n) for hz, n in _CW]
    rows += [(hz, "LSB" if hz < 10_000_000 else "USB", n) for hz, n in _VOICE]
    return _mems(sorted(rows))


RADIO_DEFAULTS = {
    "IC-7300": {"memories": _starters("USB-D", "CW")},
    "FT-891": {"memories": _starters("DATA-U", "CW-L")},
}
DATA_MODE_SAME = {"USB-D": "DATA-U", "LSB-D": "DATA-L", "DATA-U": "USB-D", "DATA-L": "LSB-D"}   # IC-7300 <-> FT-891


# --------------------------------------------------------------------------
# US phone (voice) segments, kHz (FCC 97.305 as listed by the ARRL, checked 2026-10-25).
# 30 m has no voice. 60 m is channels (USB dial frequencies) plus the 5351.5-5366.5 segment.
# --------------------------------------------------------------------------
VOICE_BANDS = [   # name, General (lo, hi), Extra (lo, hi)
    ("160 m", (1800, 2000), (1800, 2000)),
    ("80/75 m", (3800, 4000), (3600, 4000)),
    ("60 m", None, None),
    ("40 m", (7175, 7300), (7125, 7300)),
    ("20 m", (14225, 14350), (14150, 14350)),
    ("17 m", (18110, 18168), (18110, 18168)),
    ("15 m", (21275, 21450), (21200, 21450)),
    ("12 m", (24930, 24990), (24930, 24990)),
    ("10 m", (28300, 29700), (28300, 29700)),
]
CH60 = [5330.5, 5346.5, 5351.5, 5354.0, 5356.5, 5359.0, 5361.5, 5364.0, 5366.5, 5371.5, 5403.5]
LICENSE_CLASSES = ("General", "Extra")


def voice_band(name):
    return next((b for b in VOICE_BANDS if b[0] == name), VOICE_BANDS[4])


def voice_range(name, cls):
    """(lo, hi) in Hz of the voice segment for this band and license class."""
    b = voice_band(name)
    if b[1] is None:
        return int(CH60[0] * 1000), int(CH60[-1] * 1000)
    lo, hi = b[2] if cls == "Extra" else b[1]
    return lo * 1000, hi * 1000


def voice_sideband(name):
    lo = voice_range(name, "Extra")[0]
    return "USB" if lo > 10_000_000 or name == "60 m" else "LSB"


def voice_band_of(hz):
    """Band name whose voice range (Extra) holds hz, or None."""
    for b in VOICE_BANDS:
        lo, hi = voice_range(b[0], "Extra")
        if lo - 5000 <= hz <= hi + 5000:
            return b[0]
    return None
