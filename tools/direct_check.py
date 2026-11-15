#!/usr/bin/env python3
"""direct_check.py - talk to the FT-891 directly (NO flrig) to see if it answers menu (EX) commands.
1. Close RigPanel AND flrig (they hold the serial port).
2. python3 direct_check.py              (or: python3 direct_check.py /dev/ttyUSB1)
3. Start flrig again afterwards.
Needs pyserial:  sudo apt install python3-serial"""
import sys
import time

try:
    import serial
except ImportError:
    sys.exit("Needs pyserial:  sudo apt install python3-serial")

port = sys.argv[1] if len(sys.argv) > 1 else "/dev/ttyUSB0"


def ask(s, cmd):
    s.reset_input_buffer()
    s.write(cmd.encode())
    t0, out = time.monotonic(), b""
    while time.monotonic() - t0 < 1.5 and not out.endswith(b";"):
        out += s.read(64)
    return out.decode(errors="replace") or "(no answer)", time.monotonic() - t0


for baud in (4800, 9600, 19200, 38400):
    try:
        s = serial.Serial(port, baud, timeout=0.2, stopbits=2 if baud == 4800 else 1, rtscts=False)
    except serial.SerialException as e:
        sys.exit(f"Can't open {port}: {e}\n(Is flrig still running? Is the radio's CAT port {port}?)")
    s.dtr = s.rts = False                 # never key the radio
    reply, _ = ask(s, "FA;")
    if reply.startswith("FA"):
        print(f"Radio answers on {port} at {baud} baud\n")
        break
    s.close()
else:
    sys.exit(f"No answer on {port} at 4800-38400 baud. Try another port, e.g. /dev/ttyUSB1")

for cmd in ["FA;", "GT0;", "EX0801;", "EX0512;", "EX1615;", "EX1616;", "AC;", "ID;"]:
    reply, dt = ask(s, cmd)
    print(f"{cmd:9} -> {reply:22} {dt:.2f}s")
s.close()
print("\nDone - start flrig again.")
