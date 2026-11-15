"""IC-7300 RIT write test: RIT on, +150 Hz, -150 Hz, clear, RIT off. 5 s per step, then puts it back.
Watch the RIT offset on the radio's display at each step.
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


def offset(hz):
    a = abs(hz)
    return frame(0x21, 0x00, int(f"{a % 100:02d}", 16), int(f"{a // 100 % 100:02d}", 16), 1 if hz < 0 else 0)


def read(*cmd):
    return str(p.rig.cat_string(frame(*cmd))).strip()


print(f"radio {p.rig.get_xcvr()}  mode {p.rig.get_mode()}")
steps = (("RIT on", frame(0x21, 0x01, 0x01)), ("offset +150 Hz", offset(150)),
         ("offset -150 Hz", offset(-150)), ("offset 0 (clear)", offset(0)), ("RIT off", frame(0x21, 0x01, 0x00)))
try:
    for n, (what, cmd) in enumerate(steps, 1):
        p.rig.cat_string(cmd)
        time.sleep(0.3)
        print(f"Step {n}: {what:<17} radio now: offset {read(0x21, 0x00)} | RIT {read(0x21, 0x01)}  - look at the radio (5 s)")
        time.sleep(5)
finally:
    p.rig.cat_string(offset(0))
    p.rig.cat_string(frame(0x21, 0x01, 0x00))
    print("put back: RIT off, offset 0 - done")
input("Press Enter to close...")
