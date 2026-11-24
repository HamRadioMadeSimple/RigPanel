# RigPanel and flrig: compatibility notes

*Written 2026-10-23, RigPanel build 2026-10-23a. Found while testing the FT-891 on Linux Mint.*

RigPanel talks to the radio only through flrig (XML-RPC, port 12345). Some of what it does
depends on how a given flrig version behaves. This note records what was found with
**flrig 2.0.09** and the **FT-891**, the workarounds now in RigPanel, and how to re-check
them when a new flrig comes out.

## Test setup

| Item | Value |
|---|---|
| flrig | 2.0.09 (newest release, 2025-10-05) |
| Radio | Yaesu FT-891, `ID0650;`, CAT 19200 baud, `/dev/ttyUSB0` (Digirig) |
| Tuner | FC-50 (16-15 TUNER SELECT = EXTERNAL); ATAS also used |
| OS | Linux Mint |
| Newer flrig seen | 2.0.12.05 alpha (2026-08-14, w1hkj.org/alpha/flrig): Windows installer + source only, no Linux binary |

## What was found (proof in brackets)

1. **flrig garbles Yaesu strings containing an `X`.** `EX` menu commands sent plainly
   through `rig.cat_string` reach the radio as garbage: the radio answers `?;`, which flrig
   shows as hex (`3F 3B`). The same commands sent straight to the radio, with flrig closed,
   all answer correctly in 0.2 s (`EX08011;`, `EX05120;`, `EX16151;`). Commands without an X
   (`GT0;`, `PA0;`, `RG0;`, `NB0;`, `FA;`, `AC;`) are fine. [flrig_check.py, menu_check.py,
   direct_check.py, cat_variants.py]
2. **Sent as hex, `EX` commands work.** Sending the bytes as `x45 x58 x31 x36 x31 x35 x3B`
   gets a hex answer, `45 58 31 36 31 35 31 3B` = `EX16151;`. A hex command sent straight
   after a garbled plain one can fail, so send hex from the start. [cat_variants.py]
3. **A "set" command waits 6 s.** Yaesu set commands get no reply, and flrig waits about
   6.2 s, then returns `No response: FT-891`. This was the cause of the "slow" and
   "takes 7 seconds" reports.
4. **The FT-891 has no VFO select over CAT.** `VS0;` / `VS1;` answer `?;`. flrig's
   `rig.set_AB("B")` really swaps the A and B registers (FA and FB trade values), and the
   radio stays on VFO A. [vfo_check.py, second version]
5. **Mode can't be changed while flrig is on its "VFO B".** `set_mode`, `set_modeB` and
   `set_verify_modeB` all return 1, but the mode never changes. [vfo_check.py, first version]
6. **`rig.tune` works**: the same as flrig's Tune button, and it starts the FC-50. The raw
   `AC001;` / `AC002;` sequence (borrowed from POTA-CAT, which talks to the radio directly)
   was not reliable through flrig.
7. **RF gain is 0-30 on the FT-891** (`RG0016;`, the same as flrig's slider), not 0-255.
8. **Levels are radio-wide, not per VFO.** RF power, mic gain, RF gain and AF volume don't
   swap with A⇄B; frequency, mode and receive filters (AGC, NB, ...) do.
9. **FT-891 firmware bug** (named in the flrig 2.0.12 notes): every A/B select or swap
   forces the DATA-U/L bandwidth to 500. flrig 2.0.12 compensates. RigPanel does not yet:
   its A⇄B uses the radio's `SV;`, so flrig's fix doesn't apply.

## Workarounds now in RigPanel (FT-891 = `YaesuProfile`)

| # | Workaround | Where in rigpanel.py |
|---|---|---|
| 1, 2 | Any Yaesu string containing X is sent as hex; hex answers are decoded | `FlrigWorker._yaesu_send`, `hex_reply_text` |
| 3 | Every set is sent together with its read (`NB01;NB0;`, `EX16151;EX1615;`, `SV;FA;`), so the radio answers at once | `FlrigWorker.cat`, `yaesu_readback` |
| 4 | No VFO A/B select buttons on the FT-891. A⇄B = `SV;`, A=B = `AB;`, VFO B frequency read with `FB;`. If flrig is found on its "VFO B", it is put back to A once | `VFO_BY_SWAP`, `_swap_only`, `_poll` |
| 5 | Mode on VFO B by `MD0x;` (only if flrig's "B" is ever in use) | `MD_CODES`, `set_mode` / `get_mode` |
| 6 | TUNE uses `rig.tune` first; raw `AC` only if flrig has no `rig.tune` | `FlrigWorker.tune` |
| 7 | `RG_MAX = 30` | `YaesuProfile` |
| 8 | "Separate levels for Voice and Data": levels are remembered per mode kind and put back on a voice/data change | `App._restore_levels` |
| — | A menu item is treated as unavailable only after 3 bad answers in a row (one bad answer can be a hiccup) | `ex_read` |
| — | Timeouts: 10 s per call (longer than flrig's own 6 s), one retry for reads on a fresh connection, "lost" only after 3 in a row | `RPC_TIMEOUT_S`, `rpc`, `_guard` |
| — | Background CAT reads are paced (one per poll, slower when CAT is slow) | `_poll`, `pace` |

## When a new flrig comes out

1. Install it and keep RigPanel closed.
2. Run the test scripts in the RigPanel folder with flrig connected:
   - `python3 flrig_check.py`: speeds, plain menu reads, method list
   - `python3 cat_variants.py`: plain vs hex menu commands
   - `python3 vfo_check.py`: what flrig's VFO B and swap really do
3. Compare with the findings above. What to look for:
   - **Plain `EX` reads answer correctly** (`EX08011;`): flrig fixed the X problem. The hex
     path should keep working anyway; keep it, since older flrig versions still need it.
   - **Set commands return at once** without `No response`: the paired read is harmless
     and can stay.
   - **Mode changes stick on flrig's VFO B**: the `MD0` path is no longer needed, but it
     does no harm.
   - **New methods in the list** (for example native AGC, NB or menu access for the
     FT-891): consider using them instead of raw CAT.
   - **Bandwidth after A⇄B**: if flrig's fix only covers its own swap, add the
     "put data bandwidth back" fix to RigPanel's `SV;` swap.
4. Run RigPanel's own tests (`mock_flrig.py --rig FT-891 --real891` reproduces 2.0.09).

## Still open

- Data bandwidth reset to 500 after A⇄B (firmware bug, item 9): offered, not built.
- Building flrig 2.0.12 from source on Linux: not tried. No instructions written yet.
- IC-7300: not re-checked against these findings. It uses CI-V hex already, so items 1-3
  don't apply.

---

## flrig 2.0.12 (added 2026-10-24, RigPanel 1.4)

*Found on the operator's IC-7300 (Windows, flrig 2.0.12) and confirmed in the 2.0.12.05 source
(`src/server/xml_server.cxx`, `recv_hex` / `send_hex`).*

| # | Fact | What RigPanel 1.4 does |
|---|---|---|
| 10 | `rig.cat_string` now reads **every** string as hex, exactly 3 characters per byte (`"x%2X"` chunks). `xFE xFE x94 ...` **with spaces is misread** - the radio gets garbage and ignores it (nothing changed on the IC-7300's screen). Plain-text Yaesu strings are misread the same way | Every raw command is sent as `xFExFEx94xE0...xFD` / `x46x41x3B` - no spaces. Older flrig (2.0.09, 2.0.10) accepts this too |
| 11 | The reply is `" %2X"` per byte of a signed char: every byte above 0x7F prints as `FF` (FE, FD, E0, 94 and some data), small values have a leading space (`"  1"`), and the echo is not included | `to_bytes` / `icom_reply_data` decode this format and split frames on FF. A value hidden by FF (e.g. USB MOD 35 % = `00 89`) is treated as **sent**, not failed (`UNREADABLE`) |
| 12 | A command the radio doesn't answer makes flrig wait its full serial timeout and then return whatever was left in its buffer (often its own poll answer) | Fixed by #10 - correctly formed commands are answered at once |
| 13 | `rig.cmd_string` only writes (returns ''); `rig.cmd` presses flrig's user command buttons. New read-only getters: `get_agc`, `get_*_label(s)` (NB, PRE, ATT, AN...), `get_info`, `get_update` | Not used |

Test scripts (in `tools/`): `icom_flrig_check.py` (timing + raw replies), `flrig212_check.py`
(newer methods), `flrig212_write_check.py` (changes NB / ATT / preamp / AGC and puts each back).
Practice radio: `mock_flrig.py --flrig212`.

## flrig and digital-app settings (FT-891)

- **flrig → Config → Setup → Poll:** tick S-mtr, Pwr out, SWR and ALC, or RigPanel's TX meters
  show stale values.
- **JS8Call / WSJT-X → Settings → Radio:** Poll Interval **3 s**, PTT **CAT**, Mode **None**,
  Split Operation **None**. With Mode = Data/Pkt and Split = Fake It, JS8Call sends FT-891 "set"
  commands on every frequency change and transmission; the radio doesn't answer sets, so flrig waits
  each one out and TUNE / frequency changes lagged **5-10 s**. With the settings above: about 1 s.
- **Po meter (FT-891 through flrig 2.0.09):** reads about **12 W above** the power setting at every
  level (10 W set -> 22 W, 40 W -> ~50 W); flrig's own meter agrees. It is flrig's conversion of the
  FT-891 meter, not real extra output - the power setting (menu 16-01 / 16-03) is the reliable number.

## flrig Restore settings - let the radio win at start-up (added 2026-10-27, operator's finding - CONFIRMED 2026-11-02)

By default flrig, when it starts, puts back the frequency, mode, bandwidth and levels it saved last
time and sends them to the radio. That overrode the radio's own state - and with it what RigPanel set
(Voice/Data memory, levels, Rig Settings) - so RigPanel didn't open the way it was left. The operator
fixed it on his station with:

**flrig > Config > Setup > Restore:**

| Item | Setting |
|---|---|
| Freq | unticked |
| Mode | unticked |
| Bandwidth | unticked |
| Volume / gain items | unticked |
| **Use xcvr data** | **ticked** - flrig reads the radio at start-up instead of writing to it |

First results: RigPanel's settings opened correctly after this. **Not confirmed yet** - the operator is
testing more. Once confirmed, put it in the install guide next to the Poll boxes (S-mtr, Pwr out, SWR, ALC).

## FT-891 on flrig 2.0.12 (tested 2026-10-27, side-by-side build on the Mint PC)

Source (2.0.12 `xml_server.cxx`, `support/rig_io.cxx`): `rig.cat_string` writes the bytes (no flush),
then `waitResponse(serial_timeout)` -> `readResponse(";", "\xFD")`, a loop of up to 100 x 10 ms that stops
when the answer holds `;` or `FD`. `rig.cmd_string` only writes (no wait). `rig.cat_priority` is listed
but not implemented ("unknown method name").

Measured (`ft891_212_timing.py`): a read is 0.07 s, but now and then the answer is someone else's -
flrig's own poll (`MD0C;`) or the previous request's - and the call can take 1.2 s. RigPanel (27o): FT-891
sets via `rig.cmd_string`, reads checked against the question and repeated if they don't match.

**Result on the radio (27o):** operator 2026-10-27 - "Fast and works great".

## Closing flrig leaves the FT-891 data width at 500 (found 2026-10-30, RigPanel 30a)

Source (2.0.12 `support/support.cxx` `closeRig`, `support/restore_rig.cxx` `restore_xcvr_vals`): on close flrig
**always** writes its start-up values back - it selects VFO B, restores B, selects A, restores A. On the FT-891
each select is a swap, and the firmware sets the DATA-U/L width to **500** on every swap (item 9). The width is
written back only if **Restore > Bandwidth** is ticked, and then to the width flrig read at start-up - so once it
is 500 it stays 500. Seen on 2.0.09 (Linux); the operator found 2.0.12 better here, but 2.0.12 had TX stuck in
JS8Call on the FT-891, so the Mint PC is back on 2.0.09.

RigPanel 30a: on connect, if the FT-891 is in Data at 500, the remembered Data width is put back (same fix as
after A/B, `swap_check`). flrig Poll > BW only *reads* the width; it never writes it.

## flrig set-up confirmed for the install guides (2026-11-02)

On a third PC (Linux Mint, IC-7300, flrig 2.0.09) the IC-7300 FIL1/2/3 buttons switched the radio but
RigPanel's BANDWIDTH stayed at the old width: flrig's **Poll > BW** was unticked, so `rig.get_bw` kept returning
flrig's stale value. Ticking BW fixed it at once. Now in RigPanel-Linux-Install.pdf, RigPanel_Quick_Start.pdf
and the user guide: **Poll** - S-mtr, Pwr out, SWR, ALC, Freq, Mode, BW; **Restore** - everything unticked except
**Use xcvr data**.
