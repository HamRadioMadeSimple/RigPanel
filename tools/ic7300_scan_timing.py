"""IC-7300 scan test (version 2): steps 20 x 5 kHz, S-meter from flrig and straight from the radio (15 02).
Never transmits; puts the radio back.
Run with flrig connected, RigPanel and JS8Call CLOSED, radio on 20 m USB near 14.200."""
import time
import xmlrpc.client


class T(xmlrpc.client.Transport):
    def make_connection(self, host):
        c = super().make_connection(host)
        c.timeout = 20
        return c


p = xmlrpc.client.ServerProxy("http://127.0.0.1:12345/RPC2", transport=T())
CMD = "xFExFEx94xE0x15x02xFD"


def parse(r):
    """flrig 2.0.12 prints each byte as ' %2X' (so 02 shows as ' 2', bytes >= 0x80 as FF)."""
    try:
        b = [int(t.lstrip("xX"), 16) for t in r.split()]
    except ValueError:
        return None
    for i in range(len(b) - 3, -1, -1):
        if b[i] == 0x15 and b[i + 1] == 0x02:
            if 0xFF in (b[i + 2], b[i + 3]):
                return "FF"
            return int(f"{b[i + 2]:02X}{b[i + 3]:02X}")
    return None


def sm():
    t0 = time.monotonic()
    r = str(p.rig.cat_string(CMD))
    dt = time.monotonic() - t0
    v = parse(r)
    return (v if v is not None else "?"), dt, r


start = int(float(p.rig.get_vfo()))
print(f"start {start} Hz, mode {p.rig.get_mode()}   (flrig's own S-meter: {p.rig.get_smeter()})")
print("raw reply from the radio:", repr(sm()[2]))
try:
    for i in range(1, 21):
        hz = start + i * 5000
        t0 = time.monotonic()
        p.rig.set_vfo(float(hz))
        ts = time.monotonic() - t0
        a, ta, _ = sm()
        time.sleep(0.1)
        b, _, _ = sm()
        time.sleep(0.1)
        c, _, _ = sm()
        time.sleep(0.2)
        d, _, _ = sm()
        print(f"{hz:>9}  set {ts:.2f}s  read {ta:.2f}s   15 02 now={a!s:>5} +0.1={b!s:>5} "
              f"+0.2={c!s:>5} +0.4={d!s:>5}   flrig={p.rig.get_smeter()}")
finally:
    p.rig.set_vfo(float(start))
    print(f"back to {start} Hz - done")
input("Press Enter to close...")
