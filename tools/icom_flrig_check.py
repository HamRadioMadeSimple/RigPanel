#!/usr/bin/env python3
"""icom_flrig_check.py - IC-7300 + flrig: speed and exact replies (read only, changes nothing).
Run with flrig connected to the IC-7300 and RigPanel CLOSED:
    py icom_flrig_check.py        (Linux: python3 icom_flrig_check.py)
Output is also saved to icom_flrig_check.txt next to this script - send that file."""
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


def ask(label, method, *args):
    t0 = time.monotonic()
    try:
        r = getattr(p, method)(*args)
        res = repr(r)
    except Exception as e:
        res = f"ERROR {type(e).__name__}: {e}"
    out(f"{time.monotonic() - t0:6.2f}s  {label:26} {res[:110]}")


try:
    methods = p.system.listMethods()
except Exception as e:
    raise SystemExit(f"Can't reach flrig at {URL}: {e}")
ask("flrig version", "main.get_version")
ask("radio", "rig.get_xcvr")

out("\nCAT through flrig (rig.cat_string), each asked twice:")
for label, cmd in (("mode+filter 04", "xFE xFE x94 xE0 x04 xFD"), ("ATT 11", "xFE xFE x94 xE0 x11 xFD"),
                   ("AGC 16 12", "xFE xFE x94 xE0 x16 x12 xFD"), ("NB 16 22", "xFE xFE x94 xE0 x16 x22 xFD"),
                   ("RF power 14 0A", "xFE xFE x94 xE0 x14 x0A xFD"), ("RF gain 14 02", "xFE xFE x94 xE0 x14 x02 xFD")):
    for _ in range(2):
        ask(label, "rig.cat_string", cmd)

out("\nflrig's own commands (no CAT):")
for m in ("rig.get_agc", "rig.get_preamp", "rig.get_attenuator", "rig.get_noise", "rig.get_nb",
          "rig.get_noise_reduction", "rig.get_nr", "rig.get_notch", "rig.get_auto_notch", "rig.get_rfgain",
          "rig.get_power", "rig.get_AB", "rig.get_vfoA", "rig.get_vfoB", "rig.get_bw", "rig.get_mode"):
    if m in methods:
        ask(m[4:], m)
    else:
        out(f"{'':8}{m[4:]:26} (flrig has no such command)")

out("\nflrig methods: " + " ".join(sorted(m[4:] for m in methods if m.startswith("rig."))))
path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "icom_flrig_check.txt")
with open(path, "w", encoding="utf-8") as f:
    f.write("\n".join(lines) + "\n")
print(f"\nSaved to {path}")
