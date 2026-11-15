"""IC-7300 passband shift check (read-only, changes nothing).
For 20 seconds it reads PBT1 (14 07), PBT2 (14 08) and the filter (04) twice a second.
While it runs: open the FILTER screen on the radio and move SHIFT left, then right, then back to centre.
Run with flrig connected, RigPanel CLOSED, radio in USB or LSB (voice)."""
import time
import xmlrpc.client


class T(xmlrpc.client.Transport):
    def make_connection(self, host):
        c = super().make_connection(host)
        c.timeout = 20
        return c


p = xmlrpc.client.ServerProxy("http://127.0.0.1:12345/RPC2", transport=T())


def frame(*body):
    return "".join("x%02X" % v for v in (0xFE, 0xFE, 0x94, 0xE0, *body, 0xFD))


def ask(*cmd):
    """Send a CI-V read; return the data bytes after cmd as hex text (FF = hidden by flrig 2.0.12)."""
    r = str(p.rig.cat_string(frame(*cmd)))
    try:
        b = [int(t.lstrip("xX"), 16) for t in r.split()]
    except ValueError:
        return f"? {r[:30]!r}"
    n = len(cmd)
    for i in range(len(b) - n, -1, -1):
        if b[i:i + n] == list(cmd):
            data = []
            for v in b[i + n:]:
                if v in (0xFD,) or (v == 0xFF and data and len(data) >= 2):
                    break
                data.append(v)
            return " ".join("%02X" % v for v in data[:3]) or "-"
    return f"? {r[:30]!r}"


print(f"radio {p.rig.get_xcvr()}  mode {p.rig.get_mode()}  bandwidth {p.rig.get_bw()}")
print("Move SHIFT on the radio's FILTER screen now (left, right, centre)...")
print("  time   PBT1 (14 07)   PBT2 (14 08)   filter (04)")
t0 = time.monotonic()
while time.monotonic() - t0 < 20:
    t = time.monotonic() - t0
    print(f"{t:5.1f}s   {ask(0x14, 0x07):<14} {ask(0x14, 0x08):<14} {ask(0x04)}")
    time.sleep(0.5)
print("done - nothing was changed")
input("Press Enter to close...")
