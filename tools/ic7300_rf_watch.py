"""IC-7300 RF gain watch (read-only). Runs NEXT TO RigPanel and flrig - close nothing.
Every half second it prints the radio's RF gain (CI-V 14 02), flrig's own RF gain value,
the frequency and AGC, so we can see exactly when RF gain jumps. Runs 3 minutes (Ctrl+C stops it).
Start it, then start Voice Scan in RigPanel as you normally do."""
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


def civ(*cmd):
    r = str(p.rig.cat_string(frame(*cmd)))
    try:
        b = [int(t.lstrip("xX"), 16) for t in r.split()]
    except ValueError:
        return "?"
    n = len(cmd)
    for i in range(len(b) - n, -1, -1):
        if b[i:i + n] == list(cmd):
            d = b[i + n:i + n + 2]
            if len(d) == 2 and 0xFF not in d:
                return f"{round(int(f'{d[0]:02X}{d[1]:02X}') * 100 / 255):3d}%"
            return " 3x%"     # flrig 2.0.12 hid it: 32-39 %
    return "  ?"


def flrig(m):
    try:
        return str(getattr(p.rig, m)())
    except Exception:
        return "-"


print("time      radio RF   flrig RF   frequency    AGC (radio)")
t0, last = time.monotonic(), None
try:
    while time.monotonic() - t0 < 180:
        rf = civ(0x14, 0x02)
        agc = civ(0x16, 0x12)
        line = f"{time.strftime('%H:%M:%S')}   {rf:>6}   {flrig('get_rfgain'):>8}   {flrig('get_vfo'):>10}   {agc}"
        mark = "   <-- RF gain changed" if last is not None and rf != last else ""
        print(line + mark)
        last = rf
        time.sleep(0.5)
except KeyboardInterrupt:
    pass
print("done - nothing was changed")
input("Press Enter to close...")
