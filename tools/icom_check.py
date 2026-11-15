"""IC-7300 read-only check for RigPanel macros (reads only, changes nothing).

Run with flrig connected to the IC-7300 and RigPanel closed:
    Windows:  py icom_check.py          (or: python icom_check.py)
    Linux:    python3 icom_check.py
Options: --port 12345  --host 127.0.0.1  --addr 94  (CI-V address, hex)

It reads the settings a Voice/Data macro might change and prints each one with the
raw answer. The output is also saved to icom_check.txt next to this script:
send that file back (or paste the output).
"""
import argparse
import os
import sys
import xmlrpc.client

ap = argparse.ArgumentParser()
ap.add_argument("--host", default="127.0.0.1")
ap.add_argument("--port", type=int, default=12345)
ap.add_argument("--addr", default="94")
a = ap.parse_args()
ADDR = int(a.addr, 16)
rig = xmlrpc.client.ServerProxy(f"http://{a.host}:{a.port}/RPC2")
lines = []


def out(text=""):
    print(text)
    lines.append(text)


def to_bytes(reply):
    s = str(reply)
    h = "".join(ch for ch in s.replace("0x", "").replace("x", "") if ch in "0123456789abcdefABCDEF")
    if h and len(h) % 2 == 0:
        return [int(h[i:i + 2], 16) for i in range(0, len(h), 2)]
    return [ord(c) & 0xFF for c in s]


def answer(reply, cmd):
    """Data bytes after cmd in the radio's answer (our own echo is skipped)."""
    b, frames, i = to_bytes(reply), [], 0
    while i < len(b) - 1:
        if b[i] == 0xFE and b[i + 1] == 0xFE:
            j = i + 2
            while j < len(b) and b[j] == 0xFE:
                j += 1
            k = j
            while k < len(b) and b[k] != 0xFD:
                k += 1
            frames.append(b[j:k])
            i = k + 1
        else:
            i += 1
    for f in reversed(frames):
        if len(f) < 2 or f[0] == ADDR:
            continue
        body = f[2:]
        if body[:1] == [0xFA]:
            return "NG (radio refused)"
        if body[:len(cmd)] == cmd:
            return body[len(cmd):]
    return None


def read(cmd):
    wire = "".join("x%02X" % v for v in [0xFE, 0xFE, ADDR, 0xE0, *cmd, 0xFD])
    try:
        reply = rig.rig.cat_string(wire)
    except Exception as e:
        return None, f"error: {e}"
    return answer(reply, cmd), str(reply)


def bcd(bs):
    return int("".join("%02X" % v for v in bs)) if bs else None


def show(name, cmd, kind="raw"):
    data, raw = read(cmd)
    if isinstance(data, list):
        hx = " ".join("%02X" % v for v in data)
        val = ""
        if kind == "level" and len(data) == 2:
            n = bcd(data)
            val = f"= {n}/255 ({round(n * 100 / 255)}%)"
        elif kind == "onoff" and data:
            val = "= ON" if data[0] else "= OFF"
        out(f"  {name:<34} {hx:<12} {val}")
    else:
        out(f"  {name:<34} no answer   {data or ''}  raw={raw[:60]}")


out("IC-7300 check (read only)")
try:
    out(f"radio: {rig.rig.get_xcvr()}   mode: {rig.rig.get_mode()}")
except Exception as e:
    out(f"Could not reach flrig at {a.host}:{a.port}: {e}")
    sys.exit(1)
try:
    out(f"flrig {rig.main.get_version()}")
except Exception:
    pass

out("\nDirect commands")
show("Mode + filter (04)", [0x04])
show("Data mode on/off + filter (1A 06)", [0x1A, 0x06])
show("RF power (14 0A)", [0x14, 0x0A], "level")
show("Mic gain (14 0B)", [0x14, 0x0B], "level")
show("Comp level (14 0E)", [0x14, 0x0E], "level")
show("Monitor level (14 15)", [0x14, 0x15], "level")
show("NR level (14 06)", [0x14, 0x06], "level")
show("Comp on/off (16 44)", [0x16, 0x44], "onoff")
show("Monitor on/off (16 45)", [0x16, 0x45], "onoff")
show("VOX on/off (16 46)", [0x16, 0x46], "onoff")
show("NR on/off (16 40)", [0x16, 0x40], "onoff")
show("NB on/off (16 22)", [0x16, 0x22], "onoff")
show("AGC (16 12)", [0x16, 0x12])
show("SSB TX bandwidth WIDE/MID/NAR (16 58)", [0x16, 0x58])

# Menu items (1A 05 + 2-byte item number). Labels are my best guess from Icom's CI-V list;
# compare each value with MENU > SET > Connectors on the radio.
GUESS = {59: "ACC/USB Output Select", 60: "ACC/USB AF Output Level", 61: "ACC/USB AF SQL",
         62: "ACC/USB AF Beep/Speech Output", 63: "ACC/USB IF Output Level", 64: "ACC MOD Level",
         65: "USB MOD Level", 66: "DATA OFF MOD", 67: "DATA MOD"}
out("\nMenu items 1A 05 0055-0070 (guessed names; please check against the radio)")
for n in range(55, 71):
    show(f"{n:04d} {GUESS.get(n, '')}", [0x1A, 0x05, 0x00, int(str(n), 16)], "raw")

out("\nDone. Nothing was changed on the radio.")
path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "icom_check.txt")
with open(path, "w", encoding="utf-8") as f:
    f.write("\n".join(lines) + "\n")
print(f"Saved to {path}")
