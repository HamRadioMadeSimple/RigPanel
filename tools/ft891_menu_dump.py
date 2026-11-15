#!/usr/bin/env python3
"""Read-only: asks the FT-891 for every EX menu through flrig and prints the answer (changes nothing).
Run with flrig connected and RigPanel CLOSED:  python3 ft891_menu_dump.py   (saves ft891_menus.txt here)"""
import os, re, time, xmlrpc.client
class T(xmlrpc.client.Transport):
    def make_connection(self, host):
        c = super().make_connection(host); c.timeout = 20; return c
p = xmlrpc.client.ServerProxy("http://127.0.0.1:12345/RPC2", transport=T())
def hx(s): return "".join(f"x{b:02X}" for b in s.encode())
def text(r):
    r = str(r)
    if "EX" in r or "?" in r: return r.strip()
    return "".join(chr(int(t, 16)) for t in re.findall(r"[0-9A-Fa-f]{2}", r))
out = []
for sec in range(1, 19):
    misses = 0
    for item in range(1, 31):
        if (sec, item) == (17, 1):
            continue                                  # 17-01 RESET: no answer (flrig waits 6 s)
        code = f"{sec:02d}{item:02d}"
        t0 = time.monotonic()
        try: r = text(p.rig.cat_string(hx(f"EX{code};")))
        except Exception as e: r = f"ERR {e}"
        dt = time.monotonic() - t0
        m = re.search(rf"EX{code}([^;]*);", r)
        if m:
            misses = 0
            line = f"{code[:2]}-{code[2:]}  value={m.group(1):<10} digits={len(m.group(1))}  {dt:.1f}s"
        else:
            misses += 1
            line = f"{code[:2]}-{code[2:]}  no ({r!r})  {dt:.1f}s"
        print(line); out.append(line)
        if misses >= 2: break
path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ft891_menus.txt")
open(path, "w").write("\n".join(out) + "\n")
print(f"\nDone - saved to {path}. Nothing was changed.")
