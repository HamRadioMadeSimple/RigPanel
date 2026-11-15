#!/usr/bin/env python3
"""ft891_po_check.py - records the FT-891's raw power meter (RM5) against the power setting,
so RigPanel can show watts that match the radio's own display. Reads only.

1. Close RigPanel. flrig running with the FT-891.
2. Start a steady transmission into your antenna (JS8Call: Tune), on a clear frequency.
3. Run:  python3 ft891_po_check.py
4. While it runs (90 s), change the power in flrig to 10, 20, 40, 60, 80 and 100 W,
   about 10 seconds at each. Stop transmitting when it says Done.
Output is also saved to ft891_po_check.txt next to this script."""
import os
import re
import time
import xmlrpc.client

p = xmlrpc.client.ServerProxy("http://127.0.0.1:12345/RPC2")
hexs = lambda s: "".join(f"x{b:02X}" for b in s.encode())       # works on flrig 2.0.09 and 2.0.12
lines = []


def out(s):
    print(s)
    lines.append(s)


def rm5():
    r = str(p.rig.cat_string(hexs("RM5;")))
    if re.fullmatch(r"(?: [ 0-9A-Fa-f][0-9A-Fa-f])+", r) or re.fullmatch(r"(?:[0-9A-Fa-f]{2}\s*)+", r.strip()):
        r = bytes(int(t, 16) for t in r.split()).decode("ascii", "replace")
    m = re.search(r"RM5(\d{3})", r)
    return int(m.group(1)) if m else None


out(f"flrig {p.main.get_version()}  radio {p.rig.get_xcvr()}")
out(" time  ptt  setting(W)  RM5 raw  flrig Po(W)")
t0 = time.monotonic()
while time.monotonic() - t0 < 90:
    try:
        ptt = int(p.rig.get_ptt() or 0)
        setting = p.rig.get_power()
        raw = rm5()
        po = p.rig.get_pwrmeter()
        out(f"{time.monotonic() - t0:5.0f}  {ptt:3}  {str(setting):>10}  {str(raw):>7}  {str(po):>10}")
    except Exception as e:
        out(f"error: {e}")
    time.sleep(1.5)
out("Done - stop transmitting.")
path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ft891_po_check.txt")
with open(path, "w", encoding="utf-8") as f:
    f.write("\n".join(lines) + "\n")
print(f"Saved to {path}")
