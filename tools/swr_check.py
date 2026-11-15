# SWR check: flrig's SWR next to the radio's own SWR meter, twice a second for 40 s.
# Read-only - changes nothing. flrig open, RigPanel CLOSED.
#   Linux:   python3 ~/Downloads/swr_check.py
#   Windows: open Downloads, type cmd in the address bar, then: py swr_check.py
# While it runs: transmit a carrier at LOW power (10 W) where the SWR is high
# (tuner off / untuned band), then tune, then transmit again.
import time, xmlrpc.client as x

r = x.ServerProxy("http://127.0.0.1:12345/RPC2")

def call(name, *a):
    try:
        return r.__getattr__(name)(*a)
    except Exception:
        return "n/a"

def hexcmd(b):
    return "".join("x%02X" % c for c in b)

def as_text(rep):
    """flrig answers Yaesu in plain text or as hex bytes - show both forms."""
    s = str(rep).strip()
    toks = s.split()
    if toks and all(len(t) <= 2 and all(ch in "0123456789ABCDEFabcdef" for ch in t) for t in toks):
        try:
            return "".join(chr(int(t, 16)) for t in toks)
        except ValueError:
            pass
    return s

ver = call("main.get_version")
rig = str(call("rig.get_xcvr"))
methods = call("system.listMethods")
has_swr = isinstance(methods, list) and "rig.get_SWR" in methods
print("flrig", ver, "| radio", rig, "| flrig has rig.get_SWR:", has_swr)
icom = "7300" in rig
if icom:
    cmd = hexcmd(bytes([0xFE, 0xFE, 0x94, 0xE0, 0x15, 0x12, 0xFD]))
    print("Radio meter = CI-V 15 12 (raw reply shown; 0000 = 1.0, 0048 = 1.5, 0080 = 2.0, 0120 = 3.0)")
else:
    cmd = hexcmd(b"RM6;")
    print("Radio meter = RM6 (RM6000 = 1.0 ... higher = worse, 255 max)")
print()
print(" time  PTT  flrig get_SWR  flrig get_swrmeter  flrig Po    radio's own SWR meter")
t0 = time.time()
while time.time() - t0 < 40:
    ptt = call("rig.get_ptt")
    swr = call("rig.get_SWR") if has_swr else "-"
    mtr = call("rig.get_swrmeter")
    po = call("rig.get_pwrmeter")
    raw = call("rig.cat_string", cmd)
    print("%5.1f  %-3s  %-13s  %-18s  %-9s  %s" % (time.time() - t0, ptt, swr, mtr, po,
                                                     raw if icom else as_text(raw)))
    time.sleep(0.5)
print("\nDone. Copy everything above and paste it back to Claude.")
