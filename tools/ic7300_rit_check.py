"""IC-7300 RIT check (read-only, changes nothing).
For 20 seconds it reads RIT offset (21 00), RIT on/off (21 01) and dTX on/off (21 02) twice a second.
While it runs: turn RIT on, turn the RIT/dTX knob up and down, then turn RIT off.
Run with flrig connected and RigPanel CLOSED."""
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
    r = str(p.rig.cat_string(frame(*cmd)))
    try:
        b = [int(t.lstrip("xX"), 16) for t in r.split()]
    except ValueError:
        return f"? {r[:30]!r}"
    n = len(cmd)
    for i in range(len(b) - n, -1, -1):
        if b[i:i + n] == list(cmd):
            data = b[i + n:]
            if data and data[-1] == 0xFD:
                data = data[:-1]
            return " ".join("%02X" % v for v in data) or "-"
    return f"? {r[:30]!r}"


print(f"radio {p.rig.get_xcvr()}  mode {p.rig.get_mode()}")
print("Turn RIT on, turn the RIT knob up and down, then turn RIT off...")
print("  time   offset (21 00)     RIT (21 01)   dTX (21 02)")
t0 = time.monotonic()
while time.monotonic() - t0 < 20:
    print(f"{time.monotonic() - t0:5.1f}s   {ask(0x21, 0x00):<18} {ask(0x21, 0x01):<13} {ask(0x21, 0x02)}")
    time.sleep(0.5)
print("done - nothing was changed")
input("Press Enter to close...")
