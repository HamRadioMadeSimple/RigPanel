"""Radio profiles (IC-7300 CI-V, FT-891 CAT) and the macro tables for each radio."""
from .core import *  # noqa: F401,F403
from .tables import *  # noqa: F401,F403

@dataclass
class Control:
    key: str
    label: str
    kind: str                                    # "select" or "toggle"
    options: list = field(default_factory=lambda: [("OFF", 0), ("ON", 1)])
    civ: tuple = ()                              # Icom command (+ sub-command) bytes
    set_fmt: str = ""                            # Yaesu, e.g. "NB0{v};"
    read_cmd: str = ""                           # Yaesu, e.g. "NB0;"
    read_rx: str = ""                            # Yaesu reply regex, one group
    read_map: dict = field(default_factory=dict)
    note: str = ""
    row: str = "rx"                              # "rx" = Receive / Filters panel, "mode" = mode row
    level: tuple = ()                            # adjustable level (the \u25be menu): (lo, hi) + radio details


UNREADABLE = "?"     # the radio answered, but flrig 2.0.12 hid the value (a byte above 0x7F shows as FF)
FLRIG212_REPLY = re.compile(r"(?: [ 0-9A-Fa-f][0-9A-Fa-f])+")


def to_bytes(reply):
    """flrig returns Icom replies as hex text ('xFE xFE ...'); accept raw bytes too.
    flrig 2.0.12 answers ' FF FF E0 ...' style: one ' %2X' per byte, and every byte above
    0x7F (FE, FD, E0, 94 and some data) comes back as FF."""
    if isinstance(reply, (bytes, bytearray)):
        return list(reply)
    s = str(reply)
    if FLRIG212_REPLY.fullmatch(s):
        return [int(s[i:i + 3], 16) for i in range(0, len(s), 3)]
    cleaned = re.sub(r"(?i)0x|x|[\s,;:]", "", s)
    if cleaned and len(cleaned) % 2 == 0 and re.fullmatch(r"[0-9A-Fa-f]+", cleaned):
        return [int(cleaned[i:i + 2], 16) for i in range(0, len(cleaned), 2)]
    return [ord(ch) & 0xFF for ch in s]


def icom_reply_data(reply, addr, cmd):
    """Find the radio's answer frame (skipping our echo) and return the data after cmd."""
    b = to_bytes(reply)
    if 0xFE not in b and 0xFF in b:              # flrig 2.0.12: FE FE E0 94 ... FD all read as FF
        frames, cur = [], []
        for v in b + [0xFF]:
            if v == 0xFF:
                if cur:
                    frames.append(cur)
                cur = []
            else:
                cur.append(v)
        for body in reversed(frames):            # no address bytes left: a frame starts with the command
            if list(body[:len(cmd)]) == list(cmd):
                return body[len(cmd):]           # may be short: a data byte above 0x7F also reads as FF
        return None
    frames, i = [], 0
    while i < len(b) - 1:
        if b[i] == 0xFE and b[i + 1] == 0xFE:
            j = i + 2
            while j < len(b) and b[j] == 0xFE:
                j += 1
            k = j
            while k < len(b) and b[k] != 0xFD:
                k += 1
            frames.append(b[j:k])
            i = k + 1
        else:
            i += 1
    for f in reversed(frames):
        if len(f) < 2 or f[0] == addr:        # f[0] == radio address -> our own echo
            continue
        body = f[2:]
        if list(body[:len(cmd)]) == list(cmd) and len(body) > len(cmd):
            return body[len(cmd):]
    return None


def bcd(b):
    return (b >> 4) * 10 + (b & 0x0F)


class IcomProfile:
    name = "IC-7300"
    alc_zone = 120 / 255          # IC-7300 ALC zone upper limit on its 0-255 scale
    has_macros = True

    def __init__(self, civ_addr=0x94):
        self.addr = civ_addr
        self.controls = [
            Control("agc", "AGC", "select", [("FAST", 1), ("MID", 2), ("SLOW", 3)], civ=(0x16, 0x12)),
            Control("preamp", "P.AMP", "select", [("OFF", 0), ("P.AMP1", 1), ("P.AMP2", 2)], civ=(0x16, 0x02)),
            Control("att", "ATT", "select", [("OFF", 0), ("20 dB", 0x20)], civ=(0x11,)),
            Control("bkin", "BKIN", "select", [("OFF", 0), ("SEMI", 1), ("FULL", 2)], civ=(0x16, 0x47)),   # CW only (11-05b)
            Control("ipplus", "IP+", "toggle", civ=(0x1A, 0x07)),
            Control("nb", "NB", "toggle", civ=(0x16, 0x22), level=(0, 100, (0x14, 0x12), 10)),   # NB level %
            Control("nr", "NR", "toggle", civ=(0x16, 0x40), level=(0, 15, (0x14, 0x06))),   # NR level 0-15
            Control("notch", "Notch", "toggle", civ=(0x16, 0x48)),
            Control("anf", "Auto Notch", "toggle", civ=(0x16, 0x41)),
            # mode row: the radio's filter presets and the internal tuner in/out (not a tune)
            Control("filter", "Filter", "select", [("FIL1", 1), ("FIL2", 2), ("FIL3", 3)], civ=(0x04,),
                    row="mode"),
            Control("tuner", "Tuner", "toggle", civ=(0x1C, 0x01), row="mode"),
        ]

    def _frame(self, body):
        # "xFExFEx94..." - exactly 3 characters per byte, no spaces: flrig 2.0.12 reads it that
        # way (a space breaks the command), and older flrig versions accept it too
        return "".join("x%02X" % v for v in [0xFE, 0xFE, self.addr, 0xE0, *body, 0xFD])

    def set_string(self, ctl, value):
        return self._frame([*ctl.civ, value])

    def read_string(self, ctl):
        return self._frame(list(ctl.civ))

    def parse_read(self, ctl, reply):
        data = icom_reply_data(reply, self.addr, ctl.civ)
        if ctl.key == "filter":                  # 04 answers mode, filter
            return data[1] if data and len(data) > 1 and data[1] in (1, 2, 3) else None
        return data[0] if data else None

    def ctl_level_set(self, ctl, n):
        lo, hi, civ = ctl.level[:3]
        raw = round(max(lo, min(hi, n)) * 255 / hi)
        return self._frame([*civ, int(str(raw // 100), 16), int(f"{raw % 100:02d}", 16)])

    def ctl_level_read(self, ctl):
        return self._frame(list(ctl.level[2]))

    def ctl_level_parse(self, ctl, reply):
        lo, hi, civ = ctl.level[:3]
        data = icom_reply_data(reply, self.addr, civ)
        if not data or len(data) < 2:
            return None
        return round((bcd(data[0]) * 100 + bcd(data[1])) * hi / 255)

    def filter_strings(self, data_reply, mode_reply, fil):
        """CI-V to pick filter preset fil without changing the mode: 1A 06 keeps data mode on,
        06 sets mode + filter for a plain mode."""
        d = icom_reply_data(data_reply, self.addr, (0x1A, 0x06))
        if d and d[0]:
            return self._frame([0x1A, 0x06, d[0], fil])
        m = icom_reply_data(mode_reply, self.addr, (0x04,))
        return self._frame([0x06, m[0], fil]) if m else None

    # RF gain and AF volume straight to the radio (flrig's rig.set_rfgain was ignored; set_volume didn't
    # reach the radio in voice / CW on the operator's IC-7300, 11-05c)
    LEVEL_SUB = {"rfgain": 0x02, "volume": 0x01}

    def level_set_string(self, key, pct):
        if key not in self.LEVEL_SUB:
            return None
        v = round(max(0, min(100, pct)) * 255 / 100)
        return self._frame([0x14, self.LEVEL_SUB[key], int(str(v // 100), 16), int(f"{v % 100:02d}", 16)])

    def level_read_string(self, key):
        return self._frame([0x14, self.LEVEL_SUB[key]]) if key in self.LEVEL_SUB else None

    def level_hidden(self, key, reply):
        """flrig 2.0.12 answered, but hid the value (xx80-xx99 show as FF): the set did arrive."""
        data = icom_reply_data(reply, self.addr, (0x14, self.LEVEL_SUB.get(key, 0x02)))
        return data is not None and len(data) < 2 and bool(FLRIG212_REPLY.fullmatch(str(reply)))

    def parse_level(self, key, reply):
        data = icom_reply_data(reply, self.addr, (0x14, self.LEVEL_SUB.get(key, 0x02)))
        if not data or len(data) < 2:
            return None
        return round((bcd(data[0]) * 100 + bcd(data[1])) * 100 / 255)

    def alc_string(self):
        return self._frame([0x15, 0x13])

    # macro settings (IC7300_CIV)
    def menu_read_string(self, code):
        return self._frame(list(IC7300_CIV[code][0]))

    def menu_parse(self, code, reply):
        cmd, kind = IC7300_CIV[code]
        data = icom_reply_data(reply, self.addr, cmd)
        if data is None:
            return None
        need = 1 if kind == "byte" else 2
        if len(data) < need:                     # answered, value hidden by flrig 2.0.12
            return UNREADABLE if FLRIG212_REPLY.fullmatch(str(reply)) else None
        if kind == "byte":
            return data[0]
        raw = bcd(data[0]) * 100 + bcd(data[1])
        return round(raw * (100 if kind == "pct" else 10) / 255)

    def menu_write_string(self, code, num):
        cmd, kind = IC7300_CIV[code]
        if kind == "byte":
            return self._frame([*cmd, num])
        raw = round(num * 255 / (100 if kind == "pct" else 10))
        return self._frame([*cmd, int(str(raw // 100), 16), int(f"{raw % 100:02d}", 16)])

    # Passband SHIFT (the FILTER screen's SHIFT) = PBT1, 14 07: 0128 = centre, 5 Hz per unit,
    # the radio moves it in 25 Hz steps. In LSB the sign is the other way round.
    # Checked on the operator's radio 2026-10-26: 0103 -> USB -125 / LSB +125.
    SHIFT_STEP, SHIFT_MAX = 25, 625

    def _shift_sign(self, mode):
        return -1 if str(mode).upper().startswith("LSB") else 1

    def shift_set_string(self, hz, mode):
        raw = max(0, min(255, 128 + self._shift_sign(mode) * round(hz / 5)))
        return self._frame([0x14, 0x07, int(str(raw // 100), 16), int(f"{raw % 100:02d}", 16)])

    def shift_read_string(self):
        return self._frame([0x14, 0x07])

    # RIT (the IC-7300's clarifier): 21 01 on/off; 21 00 offset = 2 BCD bytes (10/1 Hz, 1000/100 Hz)
    # + sign byte (00 +, 01 -), up to 9.999 kHz. From Icom's CI-V table - to be checked on the radio.
    CLAR_NAME, CLAR_STEP, CLAR_MAX = "RIT", 10, 9990
    CLAR_KHZ = True        # shown like the radio's own display: +0.02 kHz (operator's request 2026-10-26)

    def clar_on_string(self, on):
        return self._frame([0x21, 0x01, 1 if on else 0])

    def clar_offset_strings(self, hz):
        a = abs(int(hz))
        return [self._frame([0x21, 0x00, int(f"{a % 100:02d}", 16), int(f"{a // 100 % 100:02d}", 16),
                             1 if hz < 0 else 0])]

    def clar_read_strings(self):
        return [self._frame([0x21, 0x01]), self._frame([0x21, 0x00])]

    def parse_clar(self, replies):
        on = icom_reply_data(replies[0], self.addr, (0x21, 0x01))
        off = icom_reply_data(replies[1], self.addr, (0x21, 0x00))
        on = bool(on[0]) if on else None
        hz = None
        if off and len(off) >= 3 and 0xFF not in off[:3]:
            hz = (bcd(off[1]) * 100 + bcd(off[0])) * (-1 if off[2] else 1)
        return on, hz

    def parse_shift(self, reply, mode):
        data = icom_reply_data(reply, self.addr, (0x14, 0x07))
        if not data or len(data) < 2:
            return None                              # flrig 2.0.12 hides xx80-xx99 (FF)
        hz = (bcd(data[0]) * 100 + bcd(data[1]) - 128) * 5 * self._shift_sign(mode)
        return int(round(hz / self.SHIFT_STEP) * self.SHIFT_STEP)

    def parse_alc(self, reply):
        data = icom_reply_data(reply, self.addr, (0x15, 0x13))
        if not data or len(data) < 2:
            return None
        return min(1.0, (bcd(data[0]) * 100 + bcd(data[1])) / 255)


class YaesuProfile:
    name = "FT-891"
    alc_zone = 0.5
    # ATU/FC-50 tune: AC001 = tuner on, AC002 = start tuning. Sending both works whether
    # the tuner was off or on (same sequence POTA-CAT uses for the FT-891).
    tune_cmds = ("AC001;", "AC002;")
    has_macros = True

    def __init__(self):
        self.controls = [
            Control("agc", "AGC", "select", [("OFF", 0), ("FAST", 1), ("MID", 2), ("SLOW", 3), ("AUTO", 4)],
                    set_fmt="GT0{v};", read_cmd="GT0;", read_rx=r"GT0(\d)", read_map={5: 4, 6: 4}),
            Control("preamp", "IPO / AMP", "select", [("IPO", 0), ("AMP", 1)],
                    set_fmt="PA0{v};", read_cmd="PA0;", read_rx=r"PA0(\d)",
                    note="IPO = preamp off (the FT-891's IP+)"),
            Control("att", "ATT", "select", [("OFF", 0), ("ON", 1)],
                    set_fmt="RA0{v};", read_cmd="RA0;", read_rx=r"RA0(\d)"),
            Control("bkin", "BKIN", "select", [("OFF", 0), ("SEMI", 1), ("FULL", 2)],   # CW only: BI0;/BI1; +
                    set_fmt="BI{v};", read_cmd="BI;", read_rx=r"BI(\d)"),           # menu 07-08 SEMI/FULL (11-09a)
            Control("nb", "NB", "toggle", set_fmt="NB0{v};", read_cmd="NB0;", read_rx=r"NB0(\d)",
                    level=(0, 10, ("EX0503{v:02d};", "EX0503;", r"EX0503(\d{2})"))),   # menu 05-03 NB LEVEL
            Control("nr", "DNR", "toggle", set_fmt="NR0{v};", read_cmd="NR0;", read_rx=r"NR0(\d)",
                    level=(1, 15, ("RL0{v:02d};", "RL0;", r"RL0(\d{2})"))),     # DNR level 1-15
            Control("notch", "Notch", "toggle", set_fmt="BP00{v:03d};", read_cmd="BP00;", read_rx=r"BP00(\d{3})"),
            Control("anf", "DNF", "toggle", set_fmt="BC0{v};", read_cmd="BC0;", read_rx=r"BC0(\d)"),
            # speech processor (transmit) and its level 0-100 - checked on the operator's radio 2026-10-26
            Control("proc", "PROC", "toggle", set_fmt="PR0{v};", read_cmd="PR0;", read_rx=r"PR0(\d)",
                    level=(0, 100, ("PL{v:03d};", "PL;", r"PL(\d{3})"), 5)),
            # mode row: tuner (FC-50 / ATAS, per 16-15 TUNER SELECT) in or out - not a tune
            Control("tuner", "Tuner", "toggle", set_fmt="AC00{v};", read_cmd="AC;", read_rx=r"AC00(\d)",
                    row="mode"),
        ]

    def set_string(self, ctl, value):
        return ctl.set_fmt.format(v=value)

    def ctl_level_set(self, ctl, n):
        lo, hi, (fmt, _, _) = ctl.level[:3]
        return fmt.format(v=max(lo, min(hi, n)))

    def ctl_level_read(self, ctl):
        return ctl.level[2][1]

    def ctl_level_parse(self, ctl, reply):
        m = re.search(ctl.level[2][2], str(reply))
        return int(m.group(1)) if m else None

    def read_string(self, ctl):
        return ctl.read_cmd

    def parse_read(self, ctl, reply):
        m = re.search(ctl.read_rx, str(reply))
        if not m:
            return None
        v = int(m.group(1))
        return ctl.read_map.get(v, v)

    RG_MAX = 30          # FT-891 RF gain runs 0-30 over CAT (same as flrig's slider)
    # The FT-891 can't be put on VFO B over CAT ("VS1;" answers "?;"); flrig's "VFO B" is
    # really a swap of the two frequency registers. So RigPanel offers what the radio does:
    # swap (SV), copy A to B (AB) and split, and always works on the VFO the radio is on.
    VFO_BY_SWAP = True
    # FT-891 "MD0x;" mode codes. flrig 2.0.09 can't change the mode while VFO B is in use
    # (set_mode / set_modeB answer 1 but nothing changes), so on VFO B RigPanel uses these.
    MD_CODES = {"LSB": "1", "USB": "2", "CW-U": "3", "FM": "4", "AM": "5", "RTTY-L": "6",
                "CW-L": "7", "DATA-L": "8", "RTTY-U": "9", "DATA-FM": "A", "FM-N": "B",
                "DATA-U": "C", "AM-N": "D"}

    def level_set_string(self, key, pct):
        if key != "rfgain":
            return None
        return f"RG0{round(max(0, min(100, pct)) * self.RG_MAX / 100):03d};"

    def level_read_string(self, key):
        return "RG0;" if key == "rfgain" else None

    def parse_level(self, key, reply):
        m = re.search(r"RG0(\d{3})", str(reply))
        return round(min(int(m.group(1)), self.RG_MAX) * 100 / self.RG_MAX) if m else None

    def alc_string(self):
        return "RM4;"

    # Power out from the radio's own meter (RM5 = PO, 0-255). Not linear: measured on the operator's
    # FT-891 against its power setting / front-panel display (2026-10-24); flrig's straight-line
    # conversion read 12 W high at low power. RigPanel interpolates these points instead.
    PO_TABLE = [(0, 0), (56, 10), (82, 20), (125, 40), (156, 60), (168, 80), (180, 100)]

    def po_string(self):
        return "RM5;"

    def parse_po(self, reply):
        m = re.search(r"RM5(\d{3})", str(reply))
        if not m:
            return None
        raw = int(m.group(1))
        if raw > self.PO_TABLE[-1][0]:            # past 100 W: carry on at the last slope
            (x0, y0), (x1, y1) = self.PO_TABLE[-2:]
            return y1 + (raw - x1) * (y1 - y0) / (x1 - x0)
        return interp(raw, self.PO_TABLE)

    # IF SHIFT: IS0 + 1 (shift on) + sign + 4 digits Hz, 20 Hz steps, -1200..+1200.
    # Checked on the operator's radio 2026-10-26 (reads IS01-0180; ... IS01+0180;).
    SHIFT_STEP, SHIFT_MAX = 20, 1200

    def shift_set_string(self, hz, mode):
        return f"IS01{int(hz):+05d};"

    def shift_read_string(self):
        return "IS0;"

    # CLAR (RX clarifier): CF0n0; on/off; RU/RD nnnn; = up/down by Hz, RC; = clear (no answers -
    # paired with IF;); state and offset read from IF;. Checked on the operator's radio 2026-10-26.
    CLAR_NAME, CLAR_STEP, CLAR_MAX = "CLAR", 10, 9990

    def clar_on_string(self, on):
        return f"CF0{1 if on else 0}0;"

    def clar_offset_strings(self, hz):
        hz = int(hz)
        return ["RC;" + (f"{'RU' if hz > 0 else 'RD'}{abs(hz):04d};" if hz else "")]

    def clar_read_strings(self):
        return ["IF;"]

    def parse_clar(self, replies):
        m = re.search(r"IF\d{3}\d{9}([+-]\d{4})(\d)", str(replies[0]))
        return (m.group(2) == "1", int(m.group(1))) if m else (None, None)

    def parse_shift(self, reply, mode):
        m = re.search(r"IS0[01]([+-]\d{4});", str(reply))
        return int(m.group(1)) if m else None

    # VFO Scan: the radio's own scan (checked on the operator's FT-891 + flrig 2.0.09, 2026-10-27,
    # tools/ft891_scan_check.py): SC1; up, SC2; down, SC0; stop, SC; reads it back (SCn;); about
    # 22 kHz a second. Squelch SQ0nnn; 000-100 (the knob is RF gain while 05-05 = RF). The radio
    # stops a scan on PTT or the dial. 05-16 MIC SCAN RESUME: 0 PAUSE (stay until the signal ends), 1 TIME.
    HAS_VFO_SCAN = True
    SCAN_CODES = {"stop": 0, "up": 1, "down": 2}
    SCAN_RESUME_MENU = "0516"

    def scan_string(self, cmd):
        return f"SC{self.SCAN_CODES[cmd]};"

    def parse_scan(self, reply):
        m = re.search(r"SC(\d)", str(reply))
        return {v: k for k, v in self.SCAN_CODES.items()}.get(int(m.group(1))) if m else None

    def squelch_string(self, n):
        return f"SQ0{max(0, min(100, int(n))):03d};"

    def parse_squelch(self, reply):
        m = re.search(r"SQ0(\d{3})", str(reply))
        return int(m.group(1)) if m else None

    # macro settings (EX menu items)
    # PROC / PROC level ride along with the EX menus in Rig Settings
    NON_EX = {"PROC": ("PR0{n};", "PR0;", r"PR0(\d)"), "PROCLV": ("PL{n:03d};", "PL;", r"PL(\d{3})")}

    def menu_read_string(self, code):
        if code in self.NON_EX:
            return self.NON_EX[code][1]
        return f"EX{code};"

    def menu_parse(self, code, reply):
        rx = self.NON_EX[code][2] if code in self.NON_EX else rf"EX{code}([+-]?\d+)"
        m = re.search(rx, str(reply))
        return int(m.group(1)) if m else None

    def menu_write_string(self, code, num):
        if code in self.NON_EX:
            return self.NON_EX[code][0].format(n=num)
        label, digits, vals = FT891_MENU[code]
        signed = isinstance(vals, tuple) and vals[0] < 0       # e.g. "+05": the sign counts as a digit
        return f"EX{code}{num:+0{digits}d};" if signed else f"EX{code}{num:0{digits}d};"

    def parse_alc(self, reply):
        m = re.search(r"RM4(\d{3})", str(reply))
        return min(1.0, int(m.group(1)) / 255) if m else None


class MacroSpec:
    """Everything the macro code needs to know about one radio's settings."""
    def __init__(self, **kw):
        self.__dict__.update(kw)


FT891_SPEC = MacroSpec(rig="FT-891", menu=FT891_MENU, filters=MACRO_FILTERS, items=MACRO_ITEMS,
                       all_items=ALL_ITEMS, common=COMMON_ITEMS, sections=FT891_SECTIONS, locked=FT891_LOCKED,
                       readonly={"1801", "1802", "1803"}, section_of=lambda c: c[:2] if c.isdigit() else None,
                       labels=MACRO_LABELS, defaults=DEFAULT_MACRO_LIST, groups=GROUPS,
                       cfg_key="ft891_macro_list", always_read=("0512", "1615"))
IC7300_SPEC = MacroSpec(rig="IC-7300", menu=IC7300_MENU, filters=IC7300_FILTERS, items=IC7300_ITEMS,
                        all_items=IC7300_ALL_ITEMS, common=IC7300_ITEMS, sections=IC7300_SECTIONS,
                        locked=IC7300_LOCKED, readonly=IC7300_READONLY, section_of=ic7300_section,
                        labels=IC7300_LABELS, defaults=IC7300_DEFAULT_MACROS,
                        groups=("Operating", "Antenna"), cfg_key="ic7300_macro_list", always_read=())
IcomProfile.macro_spec = IC7300_SPEC
YaesuProfile.macro_spec = FT891_SPEC
MACROS = MacroSpec(**FT891_SPEC.__dict__)     # the radio in use now (switched by make_profile)


def use_macros(spec):
    MACROS.__dict__.update(spec.__dict__)


def section_codes(num, spec=None):
    """The menu items in one All Menus group, in menu order."""
    spec = spec or MACROS
    return [c for c in sorted(spec.menu) if spec.section_of(c) == num]


def sec_title(num, name):
    return f"{num} {name}" if num.isdigit() else name


def item_label(key, spec=None):
    spec = spec or MACROS
    return spec.menu[key][0] if key in spec.menu else spec.labels.get(key, key)


def menu_encode(code, text):
    """Display value -> number for the EX command. Raises ValueError if it doesn't fit."""
    label, digits, spec = MACROS.menu[code]
    t = str(text).strip().upper()
    if isinstance(spec, dict):
        for num, name in spec.items():
            if name.upper() == t:
                return num
        if t.isdigit() and len(t) <= digits:     # a raw value read from the radio (e.g. an option
            return int(t)                        # this list doesn't name)
        raise ValueError(f"{label}: choose one of {', '.join(spec.values())}")
    m = re.match(r"([+-]?\d+)", t)
    if not m:
        raise ValueError(f"{label}: enter a number {spec[0]}-{spec[1]}")
    v = int(m.group(1))
    if not spec[0] <= v <= spec[1]:
        raise ValueError(f"{label}: {v} is outside {spec[0]}-{spec[1]}")
    if len(spec) > 2 and (v - spec[0]) % spec[2]:
        raise ValueError(f"{label}: use steps of {spec[2]} (e.g. {v - (v - spec[0]) % spec[2]})")
    return v


def menu_decode(code, num):
    if num == UNREADABLE:
        return None
    spec = MACROS.menu[code][2]
    if isinstance(spec, dict):
        return spec.get(num, str(num))
    return f"{num:+d}" if spec[0] < 0 else str(num)


def macro_choices(key, app=None):
    if key == "MODE":
        modes = [m for m in (app.modes if app else []) if m]
        return [SKIP, SSB_BY_BAND] + (modes or ["LSB", "USB", "DATA-U", "DATA-L", "CW-U", "AM", "FM"])
    if key == "WIDTH":
        return [SKIP] + ["300", "400", "500", "600", "800", "1200", "1400",           # CW (11-06e)
                         "1800", "2100", "2400", "2700", "3000", "3200"]
    if key == "FILTER":                      # IC-7300 FIL1/2/3 (27n)
        return [SKIP, "FIL1", "FIL2", "FIL3"]
    if key == "BKIN":                        # CW break-in, both radios (11-09a)
        return [SKIP] + list(BKIN_VALUES)
    if key in MACROS.filters:
        return [SKIP, "OFF", "ON"]
    spec = MACROS.menu[key][2]
    if isinstance(spec, dict):
        return [SKIP] + list(spec.values())
    lo, hi = spec[:2]
    step = spec[2] if len(spec) > 2 else 1
    while (hi - lo) // step > 60:            # keep the dropdown short; any value can be typed
        step *= 5 if str(step)[0] in "12" else 2
    if step == 1 and hi - lo > 20:
        step = 5
    vals = list(range(lo, hi + 1, step))
    if lo < 0 < hi and 0 not in vals:
        vals = sorted(vals + [0])
    return [SKIP] + [f"{v:+d}" if lo < 0 else str(v) for v in vals]


RIG_CHOICES = ["Auto-detect", "IC-7300", "FT-891"]


def yaesu_readback(cmd):
    """The read that goes with a Yaesu set command (None if there isn't one)."""
    m = re.fullmatch(r"EX(\d{4})\d+;", cmd)
    if m:
        return f"EX{m.group(1)};"
    if cmd == "SV;":
        return "FA;"
    if cmd.startswith(("RC;", "RU", "RD")):     # clarifier offset: confirmed by IF;
        return "IF;"
    if cmd == "AB;":
        return "FB;"
    for pre in ("BP00", "RG0", "GT0", "PA0", "RA0", "NB0", "NR0", "BC0", "MD0", "RL0", "AC", "IS0", "PR0", "PL", "CF0",
                "SQ0", "SC", "BI"):
        if cmd.startswith(pre) and len(cmd) > len(pre) + 1:
            return pre + ";"
    return None


def hex_reply_text(reply):
    """'45 58 31 36 31 35 31 3B' -> 'EX16151;' (flrig answers a hex command in hex)."""
    s = str(reply)
    if FLRIG212_REPLY.fullmatch(s) and ";" not in s:          # flrig 2.0.12 style
        return bytes(min(v, 0x7F) for v in to_bytes(s)).decode("ascii", "replace")
    t = s.strip()
    if t and ";" not in t and re.fullmatch(r"(?:[0-9A-Fa-f]{2}\s*)+", t):
        try:
            return bytes.fromhex(t).decode("ascii", "replace")
        except ValueError:
            pass
    return reply


# ---------------- other radios: "Add my radio" (11-14c) ----------------
# Most Icom (CI-V) and newer Yaesu radios share the basic receive commands of the IC-7300 / FT-891, but not
# their menu numbers. An added radio gets those common controls and Rig Settings for mode / width / filters /
# BKIN - never menu items (a wrong menu number changes the wrong setting). "Other" = through flrig only.
RIG_FAMILIES = {"icom": "Icom (CI-V)", "yaesu": "Yaesu (newer CAT)", "flrig": "Other - through flrig only"}
CIV_HINTS = "IC-7300 94 · IC-705 A4 · IC-7100 88 · IC-7610 98 · IC-9700 A2"
# usual factory CI-V address by model number (Add my radio fills it in; the user can change it)
CIV_DEFAULTS = {"7300": "94", "705": "A4", "7100": "88", "7610": "98", "9700": "A2", "7000": "70",
                "7200": "76", "7410": "80", "9100": "7C", "7600": "7A", "7851": "8E", "905": "AC"}


def civ_guess(xcvr):
    """'IC-705' -> 'A4'; '' when the model isn't known."""
    digits = "".join(ch for ch in (xcvr or "") if ch.isdigit())
    return CIV_DEFAULTS.get(digits, "")


class _Absent:
    """A feature the generic radios don't have: hasattr() answers False."""
    def __get__(self, obj, cls):
        raise AttributeError("not on this radio")


def generic_spec(family, name):
    filters = ({"NB": "nb", "NR": "nr", "NOTCH": "notch", "AUTO NOTCH": "anf"} if family == "icom"
               else dict(MACRO_FILTERS))
    items = (["MODE", "FILTER", "WIDTH", "BKIN"] if family == "icom" else ["MODE", "WIDTH", "BKIN"]) + list(filters)
    labels = dict(IC7300_LABELS if family == "icom" else MACRO_LABELS)
    labels.update({"NR": "NR", "AUTO NOTCH": "Auto Notch", "BKIN": "BKIN (CW break-in)"})
    slug = re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_") or "radio"
    return MacroSpec(rig=name, menu={}, filters=filters, items=items, all_items=items, common=items,
                     sections={}, locked=set(), readonly=set(), section_of=lambda c: None, labels=labels,
                     defaults=[], groups=("Operating",), cfg_key=f"rig_{slug}_macro_list", always_read=())


class GenericIcomProfile(IcomProfile):
    """Any CI-V radio: the IC-7300's common controls at its own CI-V address (no IP+, no tuner, no menus)."""
    KEEP = ("agc", "preamp", "att", "bkin", "nb", "nr", "notch", "anf", "filter")

    def __init__(self, name, civ_addr):
        super().__init__(civ_addr)
        self.name = name
        self.controls = [c for c in self.controls if c.key in self.KEEP]
        self.macro_spec = generic_spec("icom", name)


class GenericYaesuProfile(YaesuProfile):
    """Newer Yaesu CAT radios: the FT-891's common controls. RF gain, Po and VFOs through flrig (their ranges
    and VFO commands differ), BKIN on / off only (break-in type is a menu), no menus, no scan, no CLAR/SHIFT."""
    KEEP = ("agc", "preamp", "att", "bkin", "nb", "nr", "notch", "anf")
    VFO_BY_SWAP = False
    HAS_VFO_SCAN = False
    BKIN_MENU = None
    MD_CODES = _Absent()
    po_string = _Absent()
    parse_po = _Absent()
    shift_read_string = _Absent()
    clar_read_strings = _Absent()
    tune_cmds = _Absent()

    def __init__(self, name):
        super().__init__()
        self.name = name
        ctls = []
        for c in self.controls:
            if c.key not in self.KEEP:
                continue
            if c.key == "bkin":
                c.options = [("OFF", 0), ("ON", 1)]
            if c.key in ("nb", "nr"):
                c.level = ()                      # level menus differ per radio
            ctls.append(c)
        self.controls = ctls
        self.macro_spec = generic_spec("yaesu", name)

    def level_set_string(self, key, pct):
        return None                               # RF gain range differs per radio: flrig's own setter

    def level_read_string(self, key):
        return None


def find_custom(custom, choice=None, xcvr=None):
    """The added radio picked in Rig (choice), or the one flrig is driving (xcvr)."""
    for r in custom or ():
        if choice and r.get("name") == choice:
            return r
    x = (xcvr or "").strip().upper()
    for r in custom or ():
        m = (r.get("match") or r.get("name") or "").strip().upper()
        if x and m and (x == m or m in x):
            return r
    return None


def make_profile(choice, xcvr, civ_hex, custom=()):
    name = choice
    c = find_custom(custom, choice=None if choice == "Auto-detect" else choice,
                    xcvr=xcvr if choice == "Auto-detect" else None)
    if c is not None:
        if c.get("family") == "icom":
            try:
                addr = int(str(c.get("civ") or "94"), 16)
            except ValueError:
                addr = 0x94
            prof = GenericIcomProfile(c["name"], addr)
        elif c.get("family") == "yaesu":
            prof = GenericYaesuProfile(c["name"])
        else:
            return None                           # through flrig only
        use_macros(prof.macro_spec)
        return prof
    if choice == "Auto-detect":
        x = (xcvr or "").upper()
        name = "IC-7300" if "7300" in x else ("FT-891" if "891" in x else None)
    if name == "IC-7300":
        try:
            addr = int(civ_hex, 16)
        except ValueError:
            addr = 0x94
        use_macros(IC7300_SPEC)
        return IcomProfile(addr)
    if name == "FT-891":
        use_macros(FT891_SPEC)
        return YaesuProfile()
    return None
