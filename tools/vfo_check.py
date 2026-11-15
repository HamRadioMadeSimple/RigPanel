#!/usr/bin/env python3
"""vfo_check.py (2) - does flrig really switch the FT-891 between VFO A and B?
Run with flrig connected and RigPanel CLOSED:   python3 vfo_check.py
Takes ~25 s and ends back on VFO A."""
import time
import xmlrpc.client

p = xmlrpc.client.ServerProxy("http://127.0.0.1:12345/RPC2", allow_none=True)


def cat(s):
    try:
        return str(p.rig.cat_string(s))
    except Exception as e:
        return f"ERR {e}"


def show(step):
    time.sleep(3)
    print(f"{step:26} radio says {cat('VS;'):8} flrig AB={p.rig.get_AB()!s:2} "
          f"flrig freq={p.rig.get_vfo()!s:9} FA={cat('FA;')} FB={cat('FB;')}")


show("start")
p.rig.set_AB("A");  show("flrig set_AB(A)")
p.rig.set_AB("B");  show("flrig set_AB(B)")
cat("VS1;");        show("radio VS1; (VFO B)")
cat("VS0;");        show("radio VS0; (VFO A)")
p.rig.set_AB("A");  show("end (VFO A)")
