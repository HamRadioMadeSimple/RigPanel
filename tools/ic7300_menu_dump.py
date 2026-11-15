"""IC-7300 SET menu dump (read-only, changes nothing).
Asks the radio for every SET menu item (CI-V 1A 05 0001 ... 0220) through flrig and prints the answer.
Run with flrig connected and RigPanel CLOSED. Saves the result to ic7300_menus.txt next to this file."""
import os
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


def to_bytes(r):
    try:
        return [int(t.lstrip("xX"), 16) for t in str(r).split()]
    except ValueError:
        return None


def ask(item):
    hi, lo = int(f"{item // 100:02d}", 16), int(f"{item % 100:02d}", 16)
    cmd = [0x1A, 0x05, hi, lo]
    t0 = time.monotonic()
    r = str(p.rig.cat_string(frame(*cmd)))
    dt = time.monotonic() - t0
    b = to_bytes(r)
    if b is None:
        return f"? {r[:40]!r}", dt
    for i in range(len(b) - len(cmd), -1, -1):
        if len(b[i:i + len(cmd)]) == len(cmd) and all(
                x == y or (y >= 0x80 and x == 0xFF) for x, y in zip(b[i:i + len(cmd)], cmd)):
            data = b[i + len(cmd):]
            if data and data[-1] == 0xFD:
                data = data[:-1]
            return " ".join("%02X" % v for v in data) or "(empty)", dt
    return f"no answer {r[:40]!r}", dt


print(f"radio {p.rig.get_xcvr()}")
out = []
for item in range(1, 221):
    try:
        v, dt = ask(item)
    except Exception as e:
        v, dt = f"ERR {e}", 0.0
    line = f"{item:04d}  {v:<30} {dt:.2f}s"
    print(line)
    out.append(line)
path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ic7300_menus.txt")
with open(path, "w") as f:
    f.write("\n".join(out) + "\n")
print(f"\nDone - saved to {path}. Nothing was changed.")
input("Press Enter to close...")
