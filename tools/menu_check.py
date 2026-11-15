#!/usr/bin/env python3
"""menu_check.py - can the FT-891's 05-12 and 16-15 menus be read/set through flrig?
Radio should be on 16-15 = EXTERNAL (it re-sends that same value once).
Run with flrig connected and RigPanel CLOSED:   python3 menu_check.py"""
import time
import xmlrpc.client


class T(xmlrpc.client.Transport):
    def make_connection(self, host):
        c = super().make_connection(host)
        c.timeout = 20
        return c


p = xmlrpc.client.ServerProxy("http://127.0.0.1:12345/RPC2", transport=T())


def cat(s):
    t0 = time.monotonic()
    try:
        r = repr(p.rig.cat_string(s))
    except Exception as e:
        r = f"ERR {e}"
    return f"{r:24} {time.monotonic() - t0:4.1f}s"


for code in ["0511", "0512", "0513", "1614", "1615", "1616", "0801"]:
    print(f"read EX{code}:", " | ".join(cat(f"EX{code};") for _ in range(3) if not time.sleep(0.3)))
print("read AC (tuner state):", cat("AC;"))
print("write EX16151; (EXTERNAL, same value):", cat("EX16151;"))
time.sleep(0.5)
print("read EX1615 after write:", cat("EX1615;"))
print("read AC after write:", cat("AC;"))
