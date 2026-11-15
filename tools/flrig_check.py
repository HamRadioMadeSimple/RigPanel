#!/usr/bin/env python3
"""flrig_check.py - times flrig and shows its exact replies (for RigPanel troubleshooting).
Run with flrig connected to the radio:   python3 flrig_check.py
Then copy everything it prints and send it."""
import time
import xmlrpc.client

URL = "http://127.0.0.1:12345/RPC2"


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
        out = repr(r)
    except Exception as e:
        out = f"ERROR {type(e).__name__}: {e}"
    print(f"{time.monotonic() - t0:6.2f}s  {label:22} {out[:90]}")


try:
    methods = p.system.listMethods()
except Exception as e:
    raise SystemExit(f"Can't reach flrig at {URL}: {e}")
ask("flrig version", "main.get_version")
ask("radio", "rig.get_xcvr")
ask("frequency", "rig.get_vfo")
ask("mode", "rig.get_mode")
ask("power", "rig.get_power")
for cmd in ["EX1615;", "EX0512;", "GT0;", "PA0;", "RG0;", "NB0;", "FA;"]:
    ask(f"cat {cmd}", "rig.cat_string", cmd)
print("\nflrig methods:", " ".join(sorted(m[4:] for m in methods if m.startswith("rig."))))
