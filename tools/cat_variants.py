#!/usr/bin/env python3
"""cat_variants.py - find a way to get FT-891 menu (EX) and tuner (AC) commands through flrig.
flrig running, RigPanel CLOSED:   python3 cat_variants.py   (only reads, plus re-sends 16-15 = EXTERNAL)"""
import time
import xmlrpc.client


class T(xmlrpc.client.Transport):
    def make_connection(self, host):
        c = super().make_connection(host)
        c.timeout = 20
        return c


p = xmlrpc.client.ServerProxy("http://127.0.0.1:12345/RPC2", transport=T())


def hexed(cmd):          # "EX0801;" -> "x45 x58 x30 x38 x30 x31 x3B"
    return " ".join(f"x{b:02X}" for b in cmd.encode())


def run(label, method, arg):
    t0 = time.monotonic()
    try:
        r = repr(getattr(p.rig, method)(arg))
    except Exception as e:
        r = f"ERR {e}"
    print(f"{label:34} {r[:60]:62} {time.monotonic() - t0:4.1f}s")


for cmd in ["EX0801;", "EX1615;", "AC;"]:
    run(f"plain    {cmd}", "cat_string", cmd)
    run(f"hex      {cmd}", "cat_string", hexed(cmd))
    run(f"lower    {cmd.lower()}", "cat_string", cmd.lower())
    run(f"rig.cmd  {cmd}", "cmd", cmd)
    print()
run("hex write EX16151; (same value)", "cat_string", hexed("EX16151;"))
run("hex read  EX1615; after", "cat_string", hexed("EX1615;"))
