"""IC-7300 band read (read-only apart from the frequency, which is put back).

What does the radio's S-meter read across a whole voice segment, step by step?
1. Open flrig. CLOSE RigPanel (it would move the frequency too).
2. Radio as you scan: LSB, your filter, P.AMP / ATT / AGC / RF gain as you like them.
3. Run:  py ic7300_band_read.py            (40 m, 7125-7300 kHz)
   or    py ic7300_band_read.py 14150 14350
It reads every 1 kHz (5 readings each, keeps the strongest), about 2 minutes, then puts your
frequency back. WHILE IT RUNS, watch the radio's scope and write down 3-4 frequencies where you
can see or hear a station. Paste back the output (also saved to ic7300_band_read.txt) and your notes.
"""
import os
import re
import sys
import time
import xmlrpc.client

HOST, PORT = "127.0.0.1", 12345
CIV = 0x94
SETTLE, READS, GAP = 0.15, 5, 0.06          # RigPanel's Voice Scan: 0.15 s, 3 reads
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


LO, HI = (int(sys.argv[1]), int(sys.argv[2])) if len(sys.argv) > 2 else (7125, 7300)
if len(sys.argv) > 3:
    PORT = int(sys.argv[3])


def main():
    rig = xmlrpc.client.ServerProxy(f"http://{HOST}:{PORT}/RPC2")
    try:
        home = int(float(rig.rig.get_vfo()))
        mode, bw = rig.rig.get_mode(), rig.rig.get_bw()
        bw = bw[0] if isinstance(bw, (list, tuple)) and bw else bw
    except Exception as e:
        print(f"Can't reach flrig at {HOST}:{PORT} - is flrig open? ({e})")
        return
    say(f"IC-7300 band read - {time.strftime('%Y-%m-%d %H:%M')}  {LO}-{HI} kHz, mode {mode}, width {bw}")
    rows, t0 = [], time.monotonic()
    try:
        for khz in range(LO, HI + 1):
            rig.rig.set_frequency(float(khz * 1000))
            time.sleep(SETTLE)
            vals = []
            for r in range(READS):
                if r:
                    time.sleep(GAP)
                vals.append(s_meter(rig.rig.cat_string(frame([0x15, 0x02]))))
            got = [v for v in vals if v is not None]
            first3 = [v for v in vals[:3] if v is not None]
            rows.append((khz, max(got) if got else None, max(first3) if first3 else None))
            print(f"\r{khz} kHz ...", end="", flush=True)
    except KeyboardInterrupt:
        say("\nstopped early")
    finally:
        rig.rig.set_frequency(float(home))
        print()
        say(f"frequency put back to {home / 1000:.3f} kHz  ({time.monotonic() - t0:.0f} s)")
    say()
    say("kHz     best5  first3  S      (each # = 5 raw; first3 = what Voice Scan's 3 reads saw)")
    for khz, b5, b3 in rows:
        say(f"{khz}   {('%3d' % b5) if b5 is not None else '  -'}    {('%3d' % b3) if b3 is not None else '  -'}   "
            f"{s_text(b5):6s} {'#' * ((b5 or 0) // 5)}")
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ic7300_band_read.txt")
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
