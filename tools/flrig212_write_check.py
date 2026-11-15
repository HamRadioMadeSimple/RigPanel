#!/usr/bin/env python3
"""flrig212_write_check.py - IC-7300 + flrig 2.0.12: do commands sent through flrig work, and do
flrig's labels follow? Changes NB, ATT, preamp and AGC one at a time and PUTS EACH ONE BACK.
Run with flrig connected to the IC-7300, on receive, RigPanel CLOSED:   py flrig212_write_check.py
Output is also saved to flrig212_write_check.txt next to this script."""
import os
import time
import xmlrpc.client

URL = "http://127.0.0.1:12345/RPC2"
lines = []


def out(s=""):
    print(s)
    lines.append(s)


class T(xmlrpc.client.Transport):
    def make_connection(self, host):
        c = super().make_connection(host)
        c.timeout = 20
        return c


p = xmlrpc.client.ServerProxy(URL, transport=T(), allow_none=True)


def civ(*body):
    # flrig 2.0.12 reads exactly 3 characters per byte ("xFE"), so NO spaces between bytes
    return "".join("x%02X" % v for v in (0xFE, 0xFE, 0x94, 0xE0, *body, 0xFD))


def send(body):
    t0 = time.monotonic()
    try:
        r = p.rig.cat_string(civ(*body))
    except Exception as e:
        r = f"ERROR {e}"
    return time.monotonic() - t0, str(r)[:60]


def wait_label(getter, want, limit=4.0):
    """Read the label until it shows `want` (or time runs out). Returns (seconds, last label)."""
    t0 = time.monotonic()
    lab = None
    while time.monotonic() - t0 < limit:
        lab = getattr(p.rig, getter)()
        if lab == want:
            break
        time.sleep(0.1)
    return time.monotonic() - t0, lab


# name, CI-V command bytes, label getter, labels getter, {label: value byte}
TESTS = [
    ("NB", (0x16, 0x22), "get_nb_label", {"NB": 0x00, "NB on": 0x01}),
    ("ATT", (0x11,), "get_att_label", {"ATT": 0x00, "20 dB": 0x20}),
    ("Preamp", (0x16, 0x02), "get_pre_label", {"PRE": 0x00, "Amp 1": 0x01, "Amp 2": 0x02}),
    ("AGC", (0x16, 0x12), "get_agc_label", {"FST": 0x01, "MED": 0x02, "SLO": 0x03}),
]

out(f"flrig {p.main.get_version()}   radio {p.rig.get_xcvr()}   mode {p.rig.get_mode()}   ptt {p.rig.get_ptt()}")
if int(p.rig.get_ptt() or 0):
    raise SystemExit("The radio is transmitting - run this on receive.")
for name, cmd, getter, table in TESTS:
    start = getattr(p.rig, getter)()
    if start not in table:
        out(f"\n{name}: label now {start!r} - not one I know, skipped")
        continue
    other = next(lab for lab in table if lab != start)
    out(f"\n{name}: now {start!r} -> {other!r} -> back")
    sec, reply = send((*cmd, table[other]))
    out(f"   send {other!r:9} cat_string took {sec:4.2f}s  reply {reply!r}")
    sec, lab = wait_label(getter, other)
    out(f"   label shows {lab!r:9} after {sec:4.2f}s   {'OK' if lab == other else 'DID NOT FOLLOW'}")
    sec, reply = send((*cmd, table[start]))
    out(f"   send {start!r:9} cat_string took {sec:4.2f}s  reply {reply!r}")
    sec, lab = wait_label(getter, start)
    out(f"   label shows {lab!r:9} after {sec:4.2f}s   {'OK - put back' if lab == start else 'NOT BACK - check the radio'}")

path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "flrig212_write_check.txt")
with open(path, "w", encoding="utf-8") as f:
    f.write("\n".join(lines) + "\n")
print(f"\nSaved to {path}")
