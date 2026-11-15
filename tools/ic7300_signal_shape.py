"""IC-7300 signal shape check (read-only apart from the frequency, which is put back).

How strong does one voice station read as the dial moves across it?
1. Open flrig. CLOSE RigPanel (it would move the frequency too).
2. On the radio, tune a steady voice station (a net or a long QSO) EXACTLY right by ear.
   Use your normal voice settings (LSB/USB, 2400 filter).
3. Run:  py ic7300_signal_shape.py
It steps the dial from 3.5 kHz below to 3.5 kHz above your spot in 100 Hz steps, 3 times
(up, down, up - voice comes and goes), keeps the strongest reading at each spot, then
puts your frequency back. About 2 minutes. Paste back what it prints (also saved to
ic7300_signal_shape.txt next to this script).
"""
import os
import re
import sys
import time
import xmlrpc.client

HOST, PORT = "127.0.0.1", 12345
CIV = 0x94
SPAN, STEP, SWEEPS = 3500, 100, 3
SETTLE, READS, GAP = 0.15, 3, 0.06          # same as RigPanel's Voice Scan
for a in sys.argv[1:]:                       # optional: span=1000 step=200 sweeps=1 port=12345
    k, _, v = a.partition("=")
    if k == "span": SPAN = int(v)
    if k == "step": STEP = int(v)
    if k == "sweeps": SWEEPS = int(v)
    if k == "port": PORT = int(v)

FLRIG212 = re.compile(r"(?: [ 0-9A-Fa-f][0-9A-Fa-f])+")
OUT = []


def say(s=""):
    print(s)
    OUT.append(s)


def frame(body):
    return "".join("x%02X" % v for v in [0xFE, 0xFE, CIV, 0xE0, *body, 0xFD])


def to_bytes(r):
    s = str(r)
    if FLRIG212.fullmatch(s):
        return [int(s[i:i + 3], 16) for i in range(0, len(s), 3)]
    c = re.sub(r"(?i)0x|x|[\s,;:]", "", s)
    if c and len(c) % 2 == 0 and re.fullmatch(r"[0-9A-Fa-f]+", c):
        return [int(c[i:i + 2], 16) for i in range(0, len(c), 2)]
    return [ord(ch) & 0xFF for ch in s]


def bcd(b):
    return (b >> 4) * 10 + (b & 0x0F)


def s_meter(reply):
    """15 02 answer -> 0-255 (S9 = 120). flrig 2.0.12 hides xx80-xx99: estimated xx89."""
    b, cmd = to_bytes(reply), [0x15, 0x02]
    if 0xFE not in b and 0xFF in b:          # flrig 2.0.12 style
        frames, cur = [], []
        for v in b + [0xFF]:
            if v == 0xFF:
                if cur:
                    frames.append(cur)
                cur = []
            else:
                cur.append(v)
        for f in reversed(frames):
            if f[:2] == cmd:
                d = f[2:]
                if len(d) >= 2:
                    return bcd(d[0]) * 100 + bcd(d[1])
                if len(d) == 1:
                    return bcd(d[0]) * 100 + 89
        return None
    i = 0
    while i < len(b) - 1:                    # older flrig: FE FE E0 94 15 02 hh ll FD
        if b[i] == 0xFE and b[i + 1] == 0xFE:
            j = i + 2
            while j < len(b) and b[j] == 0xFE:
                j += 1
            k = j
            while k < len(b) and b[k] != 0xFD:
                k += 1
            f = b[j:k]
            if len(f) >= 6 and f[0] != CIV and f[2:4] == cmd:
                return bcd(f[4]) * 100 + bcd(f[5])
            i = k + 1
        else:
            i += 1
    return None


def s_text(raw):
    if raw is None:
        return "  -  "
    if raw <= 120:
        return "S%d" % round(9 * raw / 120)
    return "S9+%d" % round(60 * (raw - 120) / 135)


def main():
    rig = xmlrpc.client.ServerProxy(f"http://{HOST}:{PORT}/RPC2")
    try:
        home = int(float(rig.rig.get_vfo()))
        mode, bw = rig.rig.get_mode(), rig.rig.get_bw()
        bw = bw[0] if isinstance(bw, (list, tuple)) and bw else bw
    except Exception as e:
        print(f"Can't reach flrig at {HOST}:{PORT} - is flrig open? ({e})")
        return
    say(f"IC-7300 signal shape - {time.strftime('%Y-%m-%d %H:%M')}")
    say(f"Your spot {home / 1000:.3f} kHz, mode {mode}, width {bw}")
    offs = list(range(-SPAN, SPAN + 1, STEP))
    best = {o: None for o in offs}
    t0 = time.monotonic()
    try:
        for n in range(SWEEPS):
            order = offs if n % 2 == 0 else offs[::-1]
            say(f"sweep {n + 1} of {SWEEPS} ...")
            for o in order:
                rig.rig.set_frequency(float(home + o))
                time.sleep(SETTLE)
                for r in range(READS):
                    if r:
                        time.sleep(GAP)
                    v = s_meter(rig.rig.cat_string(frame([0x15, 0x02])))
                    if v is not None and (best[o] is None or v > best[o]):
                        best[o] = v
    except KeyboardInterrupt:
        say("stopped early")
    finally:
        rig.rig.set_frequency(float(home))
        say(f"frequency put back to {home / 1000:.3f} kHz  ({time.monotonic() - t0:.0f} s)")

    say()
    say("offset Hz   raw   S       (each # = 5 raw)")
    for o in offs:
        v = best[o]
        mark = "  <== your spot" if o == 0 else ""
        say(f"{o:+6d}   {('%3d' % v) if v is not None else '  -'}   {s_text(v):6s}  {'#' * ((v or 0) // 5)}{mark}")
    got = [(o, v) for o, v in best.items() if v is not None]
    if got:
        top = max(v for _, v in got)
        near = [o for o, v in got if v >= top - 12]          # within ~1 S of the strongest
        say()
        say(f"strongest {top} ({s_text(top)}); within 1 S of it from {min(near):+d} to {max(near):+d} Hz")
        # Where is the signal heard at all? Its two edges sit the same distance either side of the
        # right spot, so the middle between them = the estimate (a one-step dropout is ignored).
        floor = min(v for _, v in got)
        thr = floor + max(8, (top - floor) // 4)
        heard = [best[o] is not None and best[o] >= thr for o in offs]
        for i in range(1, len(offs) - 1):
            if not heard[i] and heard[i - 1] and heard[i + 1]:
                heard[i] = True
        runs, start = [], None
        for i, h in enumerate(heard + [False]):
            if h and start is None:
                start = i
            if not h and start is not None:
                runs.append((start, i - 1))
                start = None
        if runs:
            a, b = max(runs, key=lambda r: r[1] - r[0])
            mid = (offs[a] + offs[b]) / 2
            say(f"heard (above {thr}) from {offs[a]:+d} to {offs[b]:+d} Hz -> middle {mid:+.0f} Hz "
                f"= {(home + mid) / 1000:.3f} kHz  (your spot {home / 1000:.3f})")
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ic7300_signal_shape.txt")
    try:
        with open(path, "w", encoding="utf-8") as f:
            f.write("\n".join(OUT) + "\n")
        print(f"\nsaved to {path}")
    except OSError:
        pass


if __name__ == "__main__":
    main()
    if os.name == "nt":
        input("\nPress Enter to close")
