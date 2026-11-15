#!/usr/bin/env python3
"""ft891_scan_check.py - can RigPanel start / stop the FT-891's own VFO scan and set squelch
through flrig?  Puts back the squelch level and the frequency at the end.
Radio: VFO mode (not memory), LSB on 40 m.  flrig OPEN, RigPanel CLOSED.
Run:  python3 ~/ft891_scan_check.py      (about 30 seconds)"""
import time
import xmlrpc.client


class T(xmlrpc.client.Transport):
    def make_connection(self, host):
        c = super().make_connection(host)
        c.timeout = 20
        return c


p = xmlrpc.client.ServerProxy("http://127.0.0.1:12345/RPC2", transport=T())


def text(r):
    s = str(r).strip()
    try:
        if s and ";" not in s:
            s = bytes(min(int(h, 16), 0x7F) for h in s.split()).decode("ascii", "replace")
    except ValueError:
        pass
    return s


def cat(s):
    """Send as no-space hex (as RigPanel does); show the answer and the time it took."""
    t0 = time.monotonic()
    try:
        r = text(p.rig.cat_string("".join("x%02X" % b for b in s.encode())))
    except Exception as e:
        r = f"ERR {e}"
    return f"{s:14} -> {r!r:28} {time.monotonic() - t0:4.1f}s"


def ans(line):
    return line.split("->")[1].split("'")[1] if "'" in line else ""


print("== 1. what the radio has now")
fa = cat("FA;")
print(fa)
sq = cat("SQ0;")
print(sq)
for c in ("SC;", "MD0;", "EX0505;", "EX0515;", "EX0516;", "VS;"):
    print(cat(c))
home = ans(fa)[2:-1] if ans(fa).startswith("FA") else None
sq_now = ans(sq)[3:-1] if ans(sq).startswith("SQ0") else None

print("\n== 2. squelch: set it (with its read), then put it back")
test_sq = "030" if sq_now in (None, "000") else sq_now
print(cat(f"SQ0{test_sq};SQ0;"))
print(cat("SQ0;"))

print("\n== 3. VFO scan UP (with its read), watch the frequency for 6 s")
print(cat("SC1;SC;"))
for _ in range(6):
    time.sleep(1.0)
    print("   ", cat("FA;"), "|", cat("SC;"))

print("\n== 4. stop the scan (with its read), check it stays put")
print(cat("SC0;SC;"))
time.sleep(1.5)
print(cat("FA;"))
time.sleep(1.5)
print(cat("FA;"))

print("\n== 5. VFO scan DOWN for 3 s, then stop")
print(cat("SC2;SC;"))
time.sleep(3.0)
print(cat("FA;"))
print(cat("SC0;SC;"))

print("\n== 6. put everything back")
if sq_now is not None:
    print(cat(f"SQ0{sq_now};SQ0;"))
if home:
    print(cat(f"FA{home};FA;"))
print("done - paste all of this back")
