#!/usr/bin/env python3
"""flrig212_check.py - what flrig 2.0.12's newer commands return (read only, changes nothing).
Run with flrig connected to the radio and RigPanel CLOSED:   py flrig212_check.py
Output is also saved to flrig212_check.txt next to this script."""
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
        res = repr(getattr(p, method)(*args))
    except Exception as e:
        res = f"ERROR {type(e).__name__}: {str(e)[:120]}"
    out(f"{time.monotonic() - t0:6.2f}s  {label:30} {res[:150]}")


methods = p.system.listMethods()
ask("flrig version", "main.get_version")
ask("radio", "rig.get_xcvr")
out("\nHelp text for the newer commands:")
for m in ("rig.cmd_string", "rig.get_info", "rig.get_update", "rig.get_nb_label", "rig.get_pre_label",
          "rig.get_att_label", "rig.incr_agc"):
    if m in methods:
        try:
            out(f"        {m:30} {p.system.methodHelp(m)!r}"[:200])
        except Exception as e:
            out(f"        {m:30} help: {e}"[:200])

out("\nState read by flrig's own commands:")
for m in ("get_agc", "get_agc_label", "get_agc_labels", "get_pre_label", "get_pre_labels", "get_att_label",
          "get_att_labels", "get_nb_label", "get_nb_labels", "get_nr_label", "get_nr_labels", "get_an_label",
          "get_an_labels", "get_bk_label", "get_notch", "get_rfgain", "get_info", "get_update"):
    ask(m, "rig." + m)

out("\ncmd_string with read-only Icom commands (mode, ATT, NB), each twice:")
for label, cmd in (("cmd_string 04 hex", "xFE xFE x94 xE0 x04 xFD"), ("cmd_string 11 hex", "xFE xFE x94 xE0 x11 xFD"),
                   ("cmd_string 16 22 hex", "xFE xFE x94 xE0 x16 x22 xFD"),
                   ("cmd_string 04 plain", "FEFE94E004FD")):
    for _ in range(2):
        ask(label, "rig.cmd_string", cmd)

path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "flrig212_check.txt")
with open(path, "w", encoding="utf-8") as f:
    f.write("\n".join(lines) + "\n")
print(f"\nSaved to {path}")
