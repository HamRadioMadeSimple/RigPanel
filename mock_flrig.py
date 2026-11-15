#!/usr/bin/env python3
"""
mock_flrig.py - a stand-in for flrig so you can try RigPanel with no radio.

    python mock_flrig.py --rig IC-7300          (or --rig FT-891)

Close the real flrig first (both use port 12345), or run this on another
port with --port 12346 and type that port into RigPanel.
"""
import argparse
import random
import re
import time
from xmlrpc.server import SimpleXMLRPCRequestHandler, SimpleXMLRPCServer

XCVR_NAME = ""
ICOM_MODES = ["LSB", "USB", "AM", "CW", "RTTY", "FM", "CW-R", "RTTY-R", "LSB-D", "USB-D", "AM-D", "FM-D"]
YAESU_MODES = ["LSB", "USB", "CW-U", "FM", "AM", "RTTY-L", "CW-L", "DATA-L", "RTTY-U", "DATA-FM",
               "FM-N", "DATA-U", "AM-N"]
SSB_BWS = ["50", "100", "200", "300", "400", "500", "1000", "1500", "1800", "2100", "2400", "2700", "3000", "3600"]
ICOM_CMDS = [(0x16, 0x12), (0x16, 0x47), (0x16, 0x02), (0x16, 0x22), (0x16, 0x40), (0x16, 0x41), (0x16, 0x48),
             (0x1A, 0x07), (0x15, 0x13), (0x11,)]
# IC-7300 macro settings (multi-byte data), starting at the operator's radio values (icom_check.py)
ICOM_DATA = {(0x1A, 0x05, 0x00, 0x59): [0x00], (0x1A, 0x05, 0x00, 0x60): [0x01, 0x28],
             (0x1A, 0x05, 0x00, 0x64): [0x01, 0x28], (0x1A, 0x05, 0x00, 0x65): [0x01, 0x03],
             (0x1A, 0x05, 0x00, 0x66): [0x03], (0x1A, 0x05, 0x00, 0x67): [0x03],
             (0x16, 0x44): [0x00], (0x14, 0x0E): [0x00, 0x11], (0x16, 0x58): [0x00],
             (0x16, 0x45): [0x00], (0x16, 0x46): [0x00], (0x1C, 0x01): [0x00],
             (0x1A, 0x06): [0x01, 0x01], (0x04,): [0x01, 0x01],
             (0x14, 0x06): [0x00, 0x72], (0x14, 0x12): [0x01, 0x28], (0x14, 0x07): [0x01, 0x28],
             (0x21, 0x00): [0x00, 0x00, 0x00], (0x21, 0x01): [0x00]}
# FT-891 menus: digits and the operator's own values (read from his radio 2026-10-25)
EX_DIGITS = {"0101": 4, "0102": 4, "0103": 4, "0201": 2, "0202": 2, "0203": 2, "0204": 2, "0205": 1, "0206": 1,
    "0207": 1, "0301": 3, "0302": 3, "0401": 1, "0402": 1, "0403": 2, "0404": 3, "0405": 1, "0406": 4,
    "0407": 1, "0408": 1, "0409": 1, "0410": 1, "0411": 1, "0501": 1, "0502": 1, "0503": 2, "0504": 3,
    "0505": 1, "0506": 1, "0507": 1, "0508": 1, "0509": 1, "0510": 1, "0511": 1, "0512": 1, "0513": 3,
    "0514": 2, "0515": 1, "0516": 1, "0517": 3, "0518": 1, "0519": 1, "0520": 1, "0601": 2, "0602": 1,
    "0603": 2, "0604": 1, "0605": 1, "0606": 3, "0607": 1, "0701": 2, "0702": 1, "0703": 2, "0704": 1,
    "0705": 3, "0706": 1, "0707": 1, "0708": 1, "0709": 4, "0710": 1, "0711": 1, "0712": 1, "0713": 1,
    "0801": 1, "0802": 1, "0803": 5, "0804": 5, "0805": 2, "0806": 1, "0807": 2, "0808": 1, "0809": 1,
    "0810": 1, "0811": 3, "0812": 1, "0901": 1, "0902": 3, "0903": 1, "0904": 4, "0905": 4, "0906": 1,
    "1001": 2, "1002": 1, "1003": 2, "1004": 1, "1005": 1, "1006": 1, "1007": 1, "1008": 3, "1009": 1,
    "1010": 1, "1011": 1, "1101": 2, "1102": 1, "1103": 2, "1104": 1, "1105": 1, "1106": 3, "1107": 1,
    "1108": 1, "1109": 1, "1201": 1, "1202": 3, "1203": 2, "1204": 1, "1301": 1, "1302": 2, "1401": 1,
    "1402": 1, "1403": 1, "1404": 1, "1405": 1, "1406": 1, "1407": 1, "1501": 2, "1502": 3, "1503": 2,
    "1504": 2, "1505": 3, "1506": 2, "1507": 2, "1508": 3, "1509": 2, "1510": 2, "1511": 3, "1512": 2,
    "1513": 2, "1514": 3, "1515": 2, "1516": 2, "1517": 3, "1518": 2, "1601": 3, "1602": 3, "1603": 3,
    "1604": 3, "1605": 3, "1606": 3, "1607": 3, "1608": 3, "1609": 3, "1610": 3, "1611": 3, "1612": 3,
    "1613": 3, "1614": 3, "1615": 1, "1616": 1, "1617": 3, "1618": 4, "1619": 3, "1620": 3, "1621": 4,
    "1622": 3, "1623": 1, "1801": 4, "1802": 4, "1803": 4}
EX_RADIO = {"0101": 300, "0102": 700, "0103": 3000, "0201": 10, "0202": 14, "0203": 10, "0204": 7, "0205": 0,
    "0206": 1, "0207": 1, "0301": 50, "0302": 50, "0401": 3, "0402": 0, "0403": 30, "0404": 0, "0405":
    0, "0406": 1, "0407": 0, "0408": 0, "0409": 0, "0410": 0, "0411": 0, "0501": 1, "0502": 1, "0503":
    0, "0504": 10, "0505": 0, "0506": 2, "0507": 2, "0508": 0, "0509": 0, "0510": 0, "0511": 0, "0512":
    0, "0513": 5, "0514": 0, "0515": 1, "0516": 1, "0517": 25, "0518": 0, "0519": 0, "0520": 0, "0601":
    0, "0602": 0, "0603": 0, "0604": 0, "0605": 0, "0606": 50, "0607": 0, "0701": 4, "0702": 1, "0703":
    11, "0704": 1, "0705": 35, "0706": 2, "0707": 2, "0708": 0, "0709": 200, "0710": 2, "0711": 0,
    "0712": 3, "0713": 0, "0801": 1, "0802": 0, "0803": 1500, "0804": 1500, "0805": 0, "0806": 1,
    "0807": 0, "0808": 1, "0809": 1, "0810": 0, "0811": 35, "0812": 0, "0901": 0, "0902": 50, "0903": 0,
    "0904": 100, "0905": 1000, "0906": 0, "1001": 5, "1002": 1, "1003": 47, "1004": 1, "1005": 0,
    "1006": 0, "1007": 0, "1008": 50, "1009": 0, "1010": 1, "1011": 0, "1101": 1, "1102": 0, "1103": 47,
    "1104": 0, "1105": 0, "1106": 85, "1107": 0, "1108": 0, "1109": 3, "1201": 1, "1202": -15, "1203":
    10, "1204": 1, "1301": 0, "1302": 4, "1401": 2, "1402": 2, "1403": 1, "1404": 1, "1405": 0, "1406":
    1, "1407": 0, "1501": 2, "1502": 10, "1503": 8, "1504": 7, "1505": 5, "1506": 8, "1507": 10, "1508":
    7, "1509": 8, "1510": 3, "1511": -3, "1512": 2, "1513": 7, "1514": -3, "1515": 2, "1516": 11,
    "1517": 8, "1518": 2, "1601": 23, "1602": 5, "1603": 23, "1604": 85, "1605": 25, "1606": 40, "1607":
    14, "1608": 51, "1609": 50, "1610": 14, "1611": 50, "1612": 50, "1613": 50, "1614": 50, "1615": 1,
    "1616": 1, "1617": 50, "1618": 500, "1619": 50, "1620": 10, "1621": 100, "1622": 10, "1623": 0,
    "1801": 109, "1802": 204, "1803": 101}
EX_SIGNED = {"0513", "0517", "0803", "0804", "1202", "1502", "1505", "1508", "1511", "1514", "1517"}
EX_START = {"0503": 5, "0512": 0, "0801": 0, "0809": 0, "0810": 1, "0811": 50, "0812": 0, "1105": 1,
            "1106": 50, "1601": 100, "1603": 100, "1615": 1, "1616": 0}
# IC-7300 SET menu (1A 05 0001-0197): the operator's own values (ic7300_menu_dump.py, 2026-10-26)
IC_MENU = {1: [0, 37], 2: [9], 3: [9], 4: [0, 37], 5: [5], 6: [5], 7: [0, 37], 8: [5], 9: [5], 10: [0, 37],
    11: [0, 37], 12: [7], 13: [9], 14: [48], 15: [18], 16: [3], 17: [5], 18: [5], 19: [5], 20: [5], 21: [1,
    40], 22: [1], 23: [1], 24: [1], 25: [2], 26: [0], 27: [0], 29: [0], 30: [1], 31: [0, 16, 0, 1], 32: [0,
    80, 0, 1], 33: [0], 34: [1], 35: [0], 36: [2], 37: [0], 38: [0], 39: [0], 40: [1], 41: [1], 42: [0], 43:
    [1, 40], 44: [0], 45: [0], 46: [0], 47: [2], 48: [1], 49: [0], 50: [2], 51: [2], 52: [0], 53: [0], 54:
    [0], 55: [0], 56: [1], 57: [0], 58: [0, 89], 59: [0], 60: [1, 40], 61: [0], 62: [0], 63: [1, 40], 64: [1,
    40], 65: [1, 3], 66: [2], 67: [3], 68: [0], 69: [0], 70: [0], 71: [1], 72: [0, 0], 73: [0], 74: [1], 75:
    [1], 76: [0], 77: [1], 78: [2], 79: [1], 80: [0], 81: [1, 85], 82: [0], 83: [1], 84: [1], 85: [1], 86:
    [1], 87: [1], 88: [1], 89: [3], 90: [1], 91: [75, 87, 51, 75, 87, 32, 32, 32, 32, 32], 92: [1], 93: [0],
    94: [32, 38, 16, 38], 95: [17, 68], 96: [4, 0, 1], 97: [1], 98: [1], 99: [1], 100: [1], 103: [1], 104: [0,
    0, 0, 0, 0, 0], 105: [2, 85, 2, 85, 0, 0], 106: [2, 85, 0, 121, 0, 0], 107: [1], 109: [1], 110: [1], 114:
    [0, 80, 0, 0, 80, 1], 118: [0, 80, 3, 0, 0, 4], 122: [0, 0, 7, 0, 3, 7], 123: [0, 3, 7, 0, 32, 7], 125:
    [0, 16, 16, 0, 19, 16], 128: [0, 0, 20, 0, 16, 20], 129: [0, 16, 20, 0, 53, 20], 146: [0, 0, 80, 0, 16,
    80], 147: [0, 16, 80, 0, 48, 80], 150: [0, 37, 112, 0, 80, 112], 151: [1], 157: [0, 1], 158: [1, 40], 162:
    [1], 165: [0], 167: [0, 81, 1, 83, 2, 85], 168: [1], 171: [1, 40, 2, 85, 1, 40], 172: [2, 85, 1, 6, 1, 6],
    175: [1], 176: [0], 178: [1], 184: [1], 185: [1], 186: [0], 193: [1], 194: [0], 196: [50], 197: [1], 199:
    [0], 200: [0], 208: [0, 16, 16, 0, 21, 16], 209: [0, 0, 20, 0, 5, 20], 211: [0, 0, 33, 0, 5, 33], 217:
    [1]}


# Voice Scan practice: pretend SSB stations (dial Hz, the radio's own S-meter 0-255 at the peak)
STATIONS = [(14195000, 150), (14240000, 60), (14285000, 175), (14300000, 120), (14313000, 48),
            (14335000, 90), (7185000, 135), (7230000, 55), (7268000, 100), (3850000, 150), (3925000, 52),
            (3990000, 95), (21300000, 105), (21380000, 50), (28400000, 85), (5357000, 70), (18130000, 66)]


def band_reading(hz):
    """What an S-meter would read here: band noise plus any station within its 2.4 kHz."""
    v = random.uniform(5, 15)
    for f, peak in STATIONS:
        d = abs(hz - f)
        if d <= 2400:
            v = max(v, peak * (1 - d / 3600) * random.uniform(0.55, 1.0))    # voice comes and goes
    return int(min(255, v))


YAESU_CMDS = {"BI": 1, "SQ0": 3, "SC": 1, "PR0": 1, "PL": 3, "BP00": 3, "RM4": 3, "GT0": 1, "PA0": 1, "RA0": 1, "NB0": 1, "NR0": 1, "BC0": 1, "RG0": 3, "RL0": 2, "RM5": 3}


class Quiet(SimpleXMLRPCRequestHandler):
    rpc_paths = ("/RPC2", "/")

    def log_message(self, *a):
        pass


class MockRig:
    def __init__(self, rig, ignore_rfgain=False, real891=False, flrig212=False):
        self.real891 = real891
        self.flrig212 = flrig212
        self.ignore_rfgain = ignore_rfgain    # imitate an flrig that ignores rig.set_rfgain
        self.rf_raw, self.rf_cache = (143 if rig == "IC-7300" else 16), None
        self.cat_log = []
        self.calls = {}                       # method -> count (for load tests)
        self.ex = {**EX_RADIO, **EX_START}
        self.tune_calls = 0
        self.rig = rig
        self.icom = rig == "IC-7300"
        self.vfos = {"A": 14_074_000.0, "B": 7_000_000.0}
        self.ab = "A"
        self.split = 0
        self.modes = {"A": "USB-D" if self.icom else "DATA-U", "B": "USB-D" if self.icom else "DATA-U"}
        self.bw = "3000"
        self.power, self.volume, self.rfgain, self.micgain = 50, 30, 100, 50
        self.tx_until = 0.0
        self.s = 30.0
        self.state = {}
        if self.icom:
            self.state.update({(0x16, 0x12): 2, (0x16, 0x02): 1, (0x11,): 0})
        else:
            self.state.update({"GT0": 3, "PA0": 1})

    def tx(self):
        return time.time() < self.tx_until

    @property
    def freq(self):                      # the VFO in use
        return self.vfos[self.ab]

    @freq.setter
    def freq(self, v):
        self.vfos[self.ab] = float(v)

    # --- flrig-ish API ---
    def get_xcvr(self): return XCVR_NAME or self.rig
    def get_vfo(self): return str(int(self.freq))
    def set_frequency(self, f): self.freq = float(f); return f
    def set_vfo(self, f): self.freq = float(f); return f
    # VFO A / B, swap, split (flrig's generic VFO methods)
    def get_AB(self): return self.ab
    def set_AB(self, ab): self.ab = "B" if str(ab).upper().startswith("B") else "A"; return 0
    def get_vfoA(self): return str(int(self.vfos["A"]))
    def get_vfoB(self): return str(int(self.vfos["B"]))
    def set_vfoA(self, f): self.vfos["A"] = float(f); return f
    def set_vfoB(self, f): self.vfos["B"] = float(f); return f
    def swap(self): self.vfos["A"], self.vfos["B"] = self.vfos["B"], self.vfos["A"]; return 0
    def get_split(self): return self.split
    def set_split(self, v): self.split = 1 if int(v) else 0; return 0
    @property
    def mode(self): return self.modes[self.ab]
    def get_mode(self): return self.modes[self.ab]
    # like the FT-891 seen through flrig: plain set_mode lands on VFO A even while B is in use
    def set_mode(self, m):
        if not (self.real891 and self.ab == "B"):
            self.modes["A"] = m
        return 1
    def get_modeA(self): return self.modes["A"]
    def get_modeB(self): return self.modes["B"]
    def set_modeA(self, m): self.modes["A"] = m; return 0
    def set_modeB(self, m):
        if not self.real891:
            self.modes["B"] = m
        return 1
    def get_modes(self): return ICOM_MODES if self.icom else YAESU_MODES
    def get_bws(self): return [["Bandwidth"] + SSB_BWS]
    def get_bw(self): return [self.bw, ""]
    def set_bandwidth(self, hz):
        self.bw = min(SSB_BWS, key=lambda b: abs(int(b) - int(hz))); return int(self.bw)
    def get_ptt(self): return 1 if self.tx() else 0
    def get_pwrmax(self): return "100"
    def get_smeter(self):
        self.s = max(5, min(80, self.s + random.uniform(-6, 6))); return str(int(self.s))
    def get_pwrmeter(self): return str(int(self.power * random.uniform(0.9, 1.0))) if self.tx() else "0"
    def get_SWR(self): return f"{random.uniform(1.25, 1.4):.2f}" if self.tx() else "1.0"
    def get_power(self): return self.power
    def set_power(self, v): self.power = int(v); return 0
    def get_volume(self): return self.volume
    def set_volume(self, v): self.volume = int(v); return 0
    # RF gain: the radio's real value is rf_raw (0-255). With --ignore-rfgain this acts like
    # the flrig seen on the IC-7300: it echoes the new value for a moment but never changes
    # the radio, then reports the radio's value again (so a slider "pops back").
    def get_rfgain(self):
        if self.rf_cache and time.time() - self.rf_cache[1] < 1.5:
            return self.rf_cache[0]
        return round(self.rf_raw * 100 / 255)
    def set_rfgain(self, v):
        if self.ignore_rfgain:
            self.rf_cache = (int(v), time.time())
        else:
            self.rf_raw = round(int(v) * 255 / 100)
        return 0
    def get_micgain(self): return self.micgain
    def set_micgain(self, v): self.micgain = int(v); return 0
    def tune(self): self.tune_calls += 1; self.tx_until = time.time() + 4; return 0
    def get_test_info(self): return {"cat_log": self.cat_log[-30:], "tune_calls": self.tune_calls, "ex": self.ex,
                                     "calls": dict(self.calls)}

    def cmd_string(self, s):
        """flrig's rig.cmd_string: writes the command, waits for nothing, returns ''."""
        if self.flrig212:
            self._cat_212(s, quiet=True)
        else:
            self.cat_string(s)
        return ""

    def cat_string(self, s):
        if self.flrig212:
            return self._cat_212(s)
        if self.icom:
            return self._icom(s)
        # like flrig 2.0.09 + FT-891 (operator's results): a plain string with an X is
        # garbled (radio: "?;", shown as hex); a hex string goes through and is answered in
        # hex; several commands in one string all run; no answer at all = 'No response' after 6 s
        if s.startswith("x"):
            text = bytes(int(t, 16) for t in re.findall(r"x([0-9A-Fa-f]{2})", s)).decode()
            as_hex = True
        elif "X" in s.upper() and self.real891:
            return "3F 3B"
        else:
            text, as_hex = s, False
        replies = "".join(self._yaesu(c + ";") or "" for c in text.split(";") if c)
        if not replies and not self.real891:
            return ""
        if not replies:
            time.sleep(1.0)                     # (6 s in real flrig - shortened for tests)
            return f"No response: {self.rig}"
        return " ".join(f"{b:02X}" for b in replies.encode()) if as_hex else replies

    def _cat_212(self, s, quiet=False):
        """Like flrig 2.0.12: every command is read as hex, exactly 3 characters per byte ("xFE",
        no spaces - a space breaks it); the reply comes back as " %2X" per byte with every byte
        above 0x7F shown as FF, and without the echo of the command."""
        data, c = [], 0
        for n in range(0, len(s), 3):
            chunk = s[n:n + 3]
            if re.fullmatch(r"x[0-9A-Fa-f]{2}", chunk):
                c = int(chunk[1:], 16)
            data.append(c & 0xFF)                # a bad chunk repeats the last byte, like sscanf failing
        if self.icom:
            if len(data) < 6 or data[:2] != [0xFE, 0xFE] or data[-1] != 0xFD:
                time.sleep(0.5)
                return " FF FF FF FF 15  2  0  0 FF"          # garbage in: flrig hands back its own poll
            rep = self._icom(" ".join("x%02X" % v for v in data))
            b = [int(t, 16) for t in re.findall(r"x([0-9A-Fa-f]{2})", rep)][len(data):]   # drop the echo
        else:
            text = bytes(data).decode("latin-1")
            b = list("".join(self._yaesu(c + ";") or "" for c in text.split(";") if c).encode("latin-1"))
            if quiet:
                return ""
            # real flrig 2.0.12 + FT-891 (measured 2026-10-27): now and then the answer is another one -
            # flrig's own poll's (MD0..;) or the previous request's
            if b and random.random() < 0.25:
                b, self.last_891 = (list(getattr(self, "last_891", None) or list(b"MD0C;")), b)
            elif b:
                self.last_891 = b
            if not b:
                time.sleep(0.5)
                return f"No response: {self.rig}"
        return "".join(" FF" if v >= 0x80 else " %2X" % v for v in b)

    def _icom(self, s):
        b = [int(t, 16) for t in re.findall(r"x([0-9A-Fa-f]{2})", s)]
        body = b[4:-1]
        echo = " ".join("x%02X" % v for v in b)
        if tuple(body[:2]) == (0x14, 0x02):       # RF gain, 2-byte BCD 0000-0255
            bcd = lambda x: (x >> 4) * 10 + (x & 15)
            if len(body) > 2:
                self.rf_raw = bcd(body[2]) * 100 + bcd(body[3])
                return echo + " xFE xFE xE0 x94 xFB xFD"
            raw = self.rf_raw
            reply = [0x14, 0x02, int(str(raw // 100), 16), int(f"{raw % 100:02d}", 16)]
            return echo + " " + " ".join("x%02X" % v for v in [0xFE, 0xFE, 0xE0, 0x94, *reply, 0xFD])
        store = self.__dict__.setdefault("icom_data", {k: list(v) for k, v in ICOM_DATA.items()})
        if body[:1] == [0x06] and len(body) >= 3:          # mode + filter
            store[(0x04,)] = [body[1], body[2]]
            store[(0x1A, 0x06)] = [0x00, body[2]]
            return echo + " xFE xFE xE0 x94 xFB xFD"
        if body[:2] == [0x1A, 0x06] and len(body) >= 4:    # data mode + filter
            store[(0x1A, 0x06)] = [body[2], body[3]]
            store[(0x04,)][1] = body[3]
            return echo + " xFE xFE xE0 x94 xFB xFD"
        for cmd in ICOM_DATA:
            if tuple(body[:len(cmd)]) == cmd:
                data = body[len(cmd):]
                store = self.__dict__.setdefault("icom_data", {k: list(v) for k, v in ICOM_DATA.items()})
                if data:
                    store[cmd] = list(data)
                    reply = [0xFB]
                else:
                    reply = [*cmd, *store[cmd]]
                return echo + " " + " ".join("x%02X" % v for v in [0xFE, 0xFE, 0xE0, 0x94, *reply, 0xFD])
        if body[:2] == [0x1A, 0x05] and len(body) >= 4 and (0x1A, 0x05, body[2], body[3]) not in ICOM_DATA:
            n = int(f"{body[2]:02X}{body[3]:02X}")
            if not 1 <= n <= 197:
                return echo + " xFE xFE xE0 x94 xFA xFD"
            menu = self.__dict__.setdefault("ic_menu", {k: list(v) for k, v in IC_MENU.items()})
            if len(body) > 4:
                menu[n] = list(body[4:])
                return echo + " xFE xFE xE0 x94 xFB xFD"
            reply = [0x1A, 0x05, body[2], body[3], *menu.get(n, [0x00])]
            return echo + " " + " ".join("x%02X" % v for v in [0xFE, 0xFE, 0xE0, 0x94, *reply, 0xFD])
        if body == [0x15, 0x02]:                  # S-meter, 0000-0255 BCD (S9 = 0120)
            v = band_reading(self.vfos[self.ab]) if not self.tx() else 0
            reply = [0x15, 0x02, int(str(v // 100), 16), int(f"{v % 100:02d}", 16)]
            return echo + " " + " ".join("x%02X" % v for v in [0xFE, 0xFE, 0xE0, 0x94, *reply, 0xFD])
        for cmd in sorted(ICOM_CMDS, key=len, reverse=True):
            if tuple(body[:len(cmd)]) == cmd:
                data = body[len(cmd):]
                if data:
                    self.state[cmd] = data[0]
                    reply = [0xFB]
                elif cmd == (0x15, 0x13):
                    v = random.randint(20, 90) if self.tx() else 0
                    reply = [*cmd, v // 100, ((v // 10 % 10) << 4) | (v % 10)]
                else:
                    reply = [*cmd, self.state.get(cmd, 0)]
                return echo + " " + " ".join("x%02X" % v for v in [0xFE, 0xFE, 0xE0, 0x94, *reply, 0xFD])
        return echo + " xFE xFE xE0 x94 xFA xFD"

    def _yaesu(self, s):
        if s.startswith("EX") and len(s) >= 7:  # menu items: EX + 4-digit menu + value
            code, arg = s[2:6], s[6:].rstrip(";")
            if code not in EX_DIGITS:
                return "?;"                     # no such menu (the real radio answers "?;")
            digits = EX_DIGITS[code]
            if arg:
                self.ex[code] = int(arg)
                self.cat_log.append(s)
                return ""
            if code in EX_SIGNED:
                return f"EX{code}{self.ex.get(code, 0):+0{digits}d};"
            return f"EX{code}{self.ex.get(code, 0):0{digits}d};"
        # FT-891 VFO commands: no VFO select (VS answers "?;"), swap (SV), copy A->B (AB), read B (FB)
        if s.startswith("VS"):
            return "?;"
        if s == "SV;":     # the FT-891 swaps frequency, mode AND receive settings (kept per VFO)
            self.vfos["A"], self.vfos["B"] = self.vfos["B"], self.vfos["A"]
            self.modes["A"], self.modes["B"] = self.modes["B"], self.modes["A"]
            if self.real891:     # per VFO: AGC, IPO/AMP, ATT, NB. Radio-wide: DNR, notch, DNF
                per_vfo = ("GT0", "PA0", "RA0", "NB0")
                if not hasattr(self, "state_b"):
                    self.state_b = {k: self.state.get(k, 0) for k in per_vfo}
                    self.state_b.update(GT0=4, NB0=1)
                mine = {k: self.state.get(k, 0) for k in per_vfo}
                self.state.update(self.state_b)
                self.state_b = mine
                if self.modes["A"].startswith("DATA"):
                    self.bw = "500"          # FT-891 firmware bug: data bandwidth -> 500 on A/B
            self.cat_log.append(s); return ""
        if s == "AB;":
            self.vfos["B"] = self.vfos["A"]; self.cat_log.append(s); return ""
        if s == "FB;":
            return f"FB{int(self.vfos['B']):09d};"
        md = {"1": "LSB", "2": "USB", "C": "DATA-U", "8": "DATA-L"}
        if s.startswith("MD0"):
            if len(s) > 4:
                self.modes[self.ab] = md.get(s[3], self.modes[self.ab]); return ""
            return "MD0" + {v: k for k, v in md.items()}.get(self.modes[self.ab], "C") + ";"
        if s == "AC;":                          # tuner state: AC000 off, AC001 on
            return f"AC00{getattr(self, 'tuner_on', 0)};"
        if s.startswith("AC0"):                 # AC000 off, AC001 tuner on, AC002 start tuning
            self.cat_log.append(s)
            if s.startswith("AC002"):
                self.tx_until = time.time() + 4
                self.tuner_on = 1
            else:
                self.tuner_on = int(s[4]) if s[4:5].isdigit() else 0
            return ""
        if s.startswith("CF0"):                    # CLAR on/off
            if len(s) > 4:
                self.clar_on = int(s[3]); self.cat_log.append(s); return ""
            return f"CF0{getattr(self, 'clar_on', 0)}0;"
        if s == "RC;" or s[:2] in ("RU", "RD"):   # CLAR clear / up / down (no answer)
            off = 0 if s == "RC;" else getattr(self, "clar_off", 0) + (1 if s[:2] == "RU" else -1) * int(s[2:6])
            self.clar_off = max(-9999, min(9999, off)); self.cat_log.append(s); return ""
        if s == "IF;":                            # FT-891 IF answer (frequency, CLAR offset and on/off)
            off = getattr(self, "clar_off", 0)
            return f"IF001{int(self.vfos[self.ab]):09d}{off:+05d}{getattr(self, 'clar_on', 0)}0200000;"
        if s.startswith("IS0"):                    # IF SHIFT: IS0 + on/off + sign + 4 digits Hz
            if len(s) > 4:
                self.if_shift = int(s[4:9])
                self.cat_log.append(s)
                return ""
            return f"IS01{getattr(self, 'if_shift', 0):+05d};"
        if s == "SM0;":                           # S-meter 000-255
            return f"SM0{band_reading(self.vfos[self.ab]) if not self.tx() else 0:03d};"
        for pre in sorted(YAESU_CMDS, key=len, reverse=True):
            if s.startswith(pre):
                arg = s[len(pre):].rstrip(";")
                if pre == "RM4":
                    v = random.randint(20, 120) if self.tx() else 0
                    return f"RM4{v:03d};"
                if pre == "RM5":                 # PO meter, the operator's FT-891 curve
                    pts = [(0, 0), (10, 56), (20, 82), (40, 125), (60, 156), (80, 168), (100, 180)]
                    w = self.power if self.tx() else 0
                    v = next((r0 + (r1 - r0) * (w - w0) / (w1 - w0) for (w0, r0), (w1, r1) in zip(pts, pts[1:]) if w <= w1), 180)
                    return f"RM5{round(v):03d};"
                if pre == "RG0":
                    if arg:
                        self.rf_raw = int(arg)
                        return ""
                    return f"RG0{self.rf_raw:03d};"
                if arg:
                    self.state[pre] = int(arg)
                    return ""
                return f"{pre}{self.state.get(pre, 0):0{YAESU_CMDS[pre]}d};"
        return "?;"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--rig", default="IC-7300", choices=["IC-7300", "FT-891"])
    ap.add_argument("--port", type=int, default=12345)
    ap.add_argument("--xcvr", default="", help="radio name flrig reports (e.g. IC-705) - behaves like --rig")
    ap.add_argument("--ignore-rfgain", action="store_true", help="act like an flrig that ignores rig.set_rfgain")
    ap.add_argument("--slow-every", type=int, default=0, metavar="N",
                    help="make every Nth call slow, like a busy flrig waiting on the radio")
    ap.add_argument("--slow-s", type=float, default=3.0, metavar="S", help="how long a slow call takes (s)")
    ap.add_argument("--real891", action="store_true",
                    help="menu 05-12 gives 'No response' and 16-15 gives '?;', as on the operator's FT-891")
    ap.add_argument("--cat-delay", type=float, default=0.0, metavar="S",
                    help="every raw CAT command takes this long (a slow serial link, e.g. 0.4)")
    ap.add_argument("--flrig212", action="store_true",
                    help="raw CAT like flrig 2.0.12: strict no-space hex in, ' HH' hex out with bytes > 0x7F as FF")
    a = ap.parse_args()
    global XCVR_NAME
    XCVR_NAME = a.xcvr
    rig = MockRig(a.rig, a.ignore_rfgain, a.real891, a.flrig212)
    if a.rig == "FT-891":                    # the radio's own VFO scan (SC1 / SC2): ~22 kHz/s, 5 s on a station
        import threading

        def scanner():
            paused_on = None
            while True:
                time.sleep(0.1)
                d = {1: 1, 2: -1}.get(rig.state.get("SC", 0))
                if not d:
                    paused_on = None
                    continue
                f = rig.vfos[rig.ab]
                near = next((st for st, _ in STATIONS if abs(f - st) <= 1500), None)
                if near is not None and near != paused_on and rig.state.get("SQ0", 0) < 40:
                    paused_on = near
                    time.sleep(5.0)
                    continue
                f += d * 2200                    # like the real FT-891: runs right out of the band
                rig.vfos[rig.ab] = float(min(56_000_000, max(30_000, f)))
        threading.Thread(target=scanner, daemon=True).start()
    srv = SimpleXMLRPCServer(("127.0.0.1", a.port), requestHandler=Quiet, allow_none=True, logRequests=False)
    srv.register_introspection_functions()
    calls = [0]

    def slow(f):
        def wrapped(*args):
            calls[0] += 1
            rig.calls[f.__name__] = rig.calls.get(f.__name__, 0) + 1
            if f.__name__ == "cat_string" and a.cat_delay:
                time.sleep(a.cat_delay)
            if a.slow_every and calls[0] % a.slow_every == 0:
                time.sleep(a.slow_s)
            return f(*args)
        return wrapped
    for name in dir(rig):
        if not name.startswith("_") and callable(getattr(rig, name)) and name != "tx":
            srv.register_function(slow(getattr(rig, name)), "rig." + name)
    srv.register_function(lambda: "2.0.12" if a.flrig212 else "2.0.09", "main.get_version")
    print(f"Mock flrig ({a.rig}) on 127.0.0.1:{a.port} - Ctrl+C to stop")
    srv.serve_forever()


if __name__ == "__main__":
    main()
