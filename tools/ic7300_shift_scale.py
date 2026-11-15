"""IC-7300 SHIFT scale test. Sets PBT1 (14 07) to 4 positions, 8 s each, then back to centre (0128).
Write down what the radio's FILTER screen shows for SHIFT at each step.
Run with flrig connected, RigPanel CLOSED, radio in LSB or USB, filter 2.4k, FILTER screen open."""
import time
import xmlrpc.client


class T(xmlrpc.client.Transport):
    def make_connection(self, host):
        c = super().make_connection(host)
        c.timeout = 20
        return c


p = xmlrpc.client.ServerProxy("http://127.0.0.1:12345/RPC2", transport=T())


def set_pbt1(raw):
    hi, lo = raw // 100, raw % 100
    cmd = "".join("x%02X" % v for v in (0xFE, 0xFE, 0x94, 0xE0, 0x14, 0x07, int(str(hi), 16), int(f"{lo:02d}", 16), 0xFD))
    p.rig.cat_string(cmd)


print(f"radio {p.rig.get_xcvr()}  mode {p.rig.get_mode()}  bandwidth {p.rig.get_bw()}")
try:
    for step, raw in enumerate((103, 78, 153, 178), 1):
        set_pbt1(raw)
        print(f"Step {step}: sent {raw:04d} - what does SHIFT show on the radio?  (8 s)")
        time.sleep(8)
finally:
    set_pbt1(128)
    print("Back to centre (0128) - done")
input("Press Enter to close...")
