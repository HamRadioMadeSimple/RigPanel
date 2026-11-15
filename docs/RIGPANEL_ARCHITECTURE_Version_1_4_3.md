# RigPanel: Architecture (Ver 1.4.3, build 2026-11-14h)

> This describes RigPanel **as actually built** at build 2026-11-03a.
> The source code is authoritative: if this document and the code disagree, the code wins -
> update this document from the code.
>
> **Read §6 (IC-7300) and §7 (FT-891) before touching anything that talks to a radio.**
> Every fact there was proven on the operator's own radios with test scripts (`tools/`).
> Guessing about radio behaviour cost many rounds in earlier sessions; the scripts found every
> real cause.
>
> Companion docs: `RigPanel_Session_Handoff.md` (start of a session), `FLRIG_COMPATIBILITY.md`
> (flrig findings + how to re-test), `RigPanel_v1.4.3_User_Guide.pdf`, `RigPanel-Linux-Install.pdf`, `RigPanel_Quick_Start.pdf` (Word masters kept by the author).

---

## 1. What RigPanel is

A one-screen desktop control panel for the **Icom IC-7300** and the **Yaesu FT-891**. It is a
client of **flrig's XML-RPC server** (default `127.0.0.1:12345`) and **never opens the radio's
COM port**, so WSJT-X, JS8Call, fldigi and loggers keep sharing the radio through flrig. Where flrig
has no method for something, RigPanel sends the radio's own CAT command **through** flrig with
`rig.cat_string`.

Features: click-a-digit tuning, bands with per-band voice/data memory, VFO A/B / swap / copy /
split, **CLAR / RIT**, stored frequencies, S/Po/SWR/ALC meters, RF Power / Mic Gain / RF Gain / AF Volume
+ **MUTE**, receive filters, **passband SHIFT** (voice), FT-891 **PROC**, **Rig Settings** (one-click groups
of radio settings, both radios) with an editor (**Common | All Menus** - every menu item of both radios),
IC-7300 FIL1/2/3 (also as a Rig Settings item), Tuner in/out (both radios), DNR/NR/NB/PROC level menus,
**VFO Scan** (FT-891 only: runs the radio's own scan, lists where it stops), **Mini Meter** and **Mini
Levels** (floating, resizable), optional
audio waterfall + pop-out + Compact View, Shift hot keys, Dark/Light themes, settings files.

```
   IC-7300 / FT-891
        │ USB: CAT (virtual COM)                      USB audio codec / Digirig
        ▼                                                        │
   flrig (owns the COM port)  ◄──── WSJT-X / JS8Call / fldigi    │
        │ XML-RPC http://127.0.0.1:12345/RPC2                    │
        ▼                                                        ▼
   ┌───────────────────────────────────────────────────────────────────┐
   │ RigPanel (package rigpanel/)                                       │
   │   FlrigWorker thread ──► out_q ──► App._pump (Tk main thread)      │
   │        ▲  jobs queue ◄─────────────────┘                           │
   │   Waterfall ◄── sounddevice callback (audio thread)                │
   │   Toplevels: MiniMeter · MiniLevels · FloatWaterfall · VfoScan ·   │
   │              FreqListWindow · MacroBuilder ("Edit Rig Settings")   │
   └───────────────────────────────────────────────────────────────────┘
     DATA_DIR/settings.json · my_default.json · settings_before_load.json · rigpanel_debug.log
```

---

## 2. Status at a glance

| Item | State |
|---|---|
| Version | `APP_VERSION = "1.4.3"`, `APP_BUILD = "2026-11-14c"` (`rigpanel/core.py`; shown in title, header, status bar). 1.4.1 = the features of 2026-10-25/26, 1.4.2 = the tidy-up |
| IC-7300 | Windows 11, **flrig 2.0.12** (current release) - proven 2026-10-24 after the hex-format fix (§5): receive controls change the radio, VFO switch fast, Rig Settings confirm. Earlier also on 2.0.10. Filter item + Save & Apply + resizable editor used by the operator 2026-10-27 (Windows PC was on 27n) |
| FT-891 | Linux Mint (the operator's go-box PC), **flrig 2.0.09**, Digirig `/dev/ttyUSB0` 19200 baud, FC-50 + ATAS - proven 2026-10-22..24 incl. V1.4 Linux package, Tuner, DNR level, Po meter. **Proven on real flrig 2.0.12 2026-10-27** (side-by-side build on the Mint PC, build 27o: fast after the `cmd_string` + checked-read fix, FLRIG_COMPATIBILITY.md) |
| Packaging | Windows: `build_windows.bat` (PyInstaller + Inno Setup 6, `VER=1.4.3`) → `output\RigPanel_Setup_1.4.3.exe`, installs to `C:\Program Files (x86)\RigPanel` (admin), desktop icon. Linux (11-02a, standard layout shared with the operator's other apps): `build_linux.sh` (`--appimage`: also the AppImage; GitHub builds releases on Ubuntu 22.04 via `.github/workflows/release.yml`) → `output/RigPanel_Ver_1.4.3_Linux.tar.gz` (top folder `RigPanel Ver 1.4.3`, + `VERSION`, `linux_install.sh`, install + quick-start docs); users unpack it into `~/Applications` and run `sh linux_install.sh` there (menu entry + trusted desktop icon, offers to remove older copies incl. the old `~/.local/share/rigpanel`). Install doc: `docs/RigPanel-Linux-Install.docx`. **One-step update: `bash ~/Downloads/update_linux.sh`** (newest RigPanel_V*.zip in Downloads → fresh folder → build → install; keeps `.buildenv`). Linux package proven on the Mint PC; Windows installer built and run by the operator (1.3) |
| Tests | `bash tests/run_all.sh /usr/bin/python3.12`: `names_check.py`, then `regress.py` and `features.py` against `mock_flrig.py` (FT-891 `--real891`, IC-7300 `--flrig212`). Result of the 27q run: §10. Voice Scan checks removed from `features.py` with the feature |
| Python | 3.9+, standard library + Tk; `numpy`, `sounddevice`, `pillow` only for the waterfall |
| Repo | Ready for GitHub (README, CHANGELOG, requirements.txt, .gitignore, .gitattributes (line endings), GPL-3.0 planned). Handoff file is git-ignored |

---

## 3. Code layout (package `rigpanel/`, split from one file in 1.3)

Modules load in this order; each does `from .earlier import *`. **A module may only use names
from modules before it** - the 1.3 split once left `screen_bounds` (used by the pop-out waterfall)
in a later module, which broke Compact View until build 24h. Check with the AST script in the
1.4 session notes (or simply: grep the definition's module vs the user's module).

| Module | Lines | Owns |
|---|---|---|
| `core.py` | ~355 | `APP_*`, `DATA_DIR`/`CONFIG_PATH`/`RES_DIR`, `DEFAULT_CONFIG`, `load_config`/`save_config`/`write_json`, `PC_KEYS`, `MY_DEFAULT_PATH`/`BACKUP_PATH`, `FONT` (ui/mono) + `pick_fonts`, `THEMES`, live palette `C`, `HUD` palette, `S_ZONES`, meter ticks, `BANDS`, helpers (`fmt_freq`, `is_data_mode`, `parse_hz`, `interp`, `debug_log`, …) |
| `tables.py` | ~450 | Plain data: `FT891_MENU` (every EX menu + PROC/PROCLV), `FT891_SECTIONS`/`FT891_LOCKED`, Common list (`MACRO_ITEMS`, `COMMON_ITEMS`, `ALL_ITEMS`), `DEFAULT_MACRO_LIST`; `IC7300_MENU`/`IC7300_CIV` (every SET item 0001-0197 that is a simple value), `IC7300_SECTIONS`/`LOCKED`/`READONLY`, `ic7300_section`, `IC7300_ITEMS`/`ALL_ITEMS` (incl. `FILTER`, 27n), defaults; `RADIO_DEFAULTS`, `DATA_MODE_SAME`; US voice band plan `VOICE_BANDS`, `CH60`, `LICENSE_CLASSES`, `voice_range`, `voice_sideband`, `voice_band_of` (used by VFO Scan) |
| `radios.py` | ~570 | `Control`, `to_bytes`/`icom_reply_data`/`bcd`, `IcomProfile`, `YaesuProfile` (all radio commands: controls, levels, menus, SHIFT, CLAR/RIT, Po/ALC, FT-891 VFO Scan `SC`/`SQ0` + `HAS_VFO_SCAN`), `MacroSpec`, `FT891_SPEC`/`IC7300_SPEC`, `MACROS` (spec of the radio in use, switched by `make_profile`), `section_codes`, `sec_title`, `menu_encode`/`menu_decode`, `yaesu_readback`, `hex_reply_text`, `UNREADABLE`, `FLRIG212_REPLY`, `make_profile` |
| `worker.py` | ~840 | `TimeoutTransport`, `FlrigWorker` - **the only code that talks to flrig** (incl. `vscan_*`, `shift`, `clar`, `EXTRA_READS`, flrig 2.0.12 FT-891 handling in `cat`/`cat_read`) |
| `widgets.py` | ~520 | `FlatButton`, `Tooltip`, `Segmented`, `hex_mix`, `BarMeter`, `LevelBar`, `FreqDisplay`, `panel`/`label`/`checkbox`/`section`/`small_label`, `popup_menu` (every drop-down / right-click menu, 27j), `screen_bounds` |
| `waterfall.py` | ~430 | `Waterfall`, `FloatWaterfall`, `DEMO_DEVICE` |
| `freqlist.py` | ~190 | `FreqListWindow` |
| `minis.py` | ~540 | `MiniMeter` (base: canvas HUD, move, corner resize, size/place memory) and `MiniLevels(MiniMeter)` |
| `vscan.py` | ~460 | `VfoScan` window (FT-891): ▼ ■ ▲, squelch, On a signal (05-16), Begin at, License, At the end, HEARD list, click-a-digit frequency (27f-27q). `scan.py` (S-meter Voice Scan) was **removed** in 27f |
| `extras.py` | ~400 | `CtrlTap` (system-wide Ctrl tap, 11-09) and `Extras` - mixed into `App`: CLAR/RIT, SHIFT, MUTE, VFO Scan hooks, `start_ctrl_tap` / `toggle_front` |
| `builder.py` | ~570 | `MacroBuilder` (shown to users as **Edit Rig Settings**): Common / All Menus views, Radio now column, Save as new, **Save & Apply** (27l), resizable + `rs_geom` (27m), tooltips |
| `app.py` | ~1600 | `App(Extras)` - main window, poll handling, actions, voice/data memory, Rig Settings, hot keys, settings files |
| `main.py` | ~40 | `set_app_icon`, `main()` |

Load order: core → tables → radios → worker → widgets → waterfall → freqlist → minis → vscan → extras →
builder → app → main. `tests/names_check.py` enforces the two rules (no name in two modules; no use of a
later module's name) - run it after moving code.

Entry points: `python -m rigpanel`, `run_rigpanel.py` (also the PyInstaller entry), `RigPanel.bat`,
`rigpanel.sh`.

Other files: `mock_flrig.py` (practice radio), `tests/regress.py`, `tools/` (radio diagnostic
scripts), `examples/KW3KW_settings.json` (the operator's full station), `docs/`, build/install
scripts, icons.

### 3.1 Threads (the load-bearing rule)

| Thread | Does | Never does |
|---|---|---|
| Tk main (`App`) | All widgets; drains `out_q` every 50 ms (`_pump`); queues jobs with `worker.submit(lambda w: …)` | Network calls; changing worker attributes directly |
| `FlrigWorker` (daemon) | Every XML-RPC call; posts results (`post(kind, data)`) | Touches Tk |
| sounddevice callback | Copies audio into `Waterfall.buf` under a lock | Touches Tk |

Since 1.3 the window changes worker state **only through the job queue** (`set_profile`,
`macro_codes`, …). Each profile carries its own macro tables (`profile.macro_spec`); the worker uses
those, never the `MACROS` global.

Messages on `out_q`: `poll`, `ctl`, `ctl_level`, `tables`, `connected`, `down`, `log`,
`macro_state`, `macro_done`, `macro_capture` (tag = Rig Setting index, or `("radio", group)` for the
Radio now column), `ex_unsupported`, `shift`, `clar`, `vscan` (VFO Scan: `scan` state up/down/stop,
`sql`, `resume`).

Closing: `App.close` saves settings, sets `worker.alive = False`, hides the window, **joins the
worker (≤3 s)** so a request in progress finishes, the worker closes its HTTP connection
("closed the connection to flrig" in the log), then the window is destroyed (24c).

Settings load / Return to my default rebuild **in the same Tk root** (`_restart_with`): the old App
gets `dead = True` (its `_clock`, `_pump`, waterfall `_tick` stop themselves), widgets destroyed,
new settings saved, `App(root)` again. A second `tk.Tk()` in one process was tried and is
unreliable (stray timers fire into the new interpreter) - don't.

---

## 4. The flrig link (`FlrigWorker`)

- `RPC_TIMEOUT_S` = 10 s per call (longer than flrig's own wait). Reads that time out are retried
  once on a fresh connection; commands never. flrig is "lost" only after 3 timeouts in a row.
  Replies slower than 1 s are logged as `slow flrig reply: …` - **the first thing to read** when
  anything is slow.
- Poll every `POLL_S` = 0.25 s: freq, mode, bw, PTT every poll; VFO state every 2nd; S-meter on RX;
  Po / SWR / ALC on TX; levels every 8th (RF gain by CAT every 5 s). Background CAT reads at most
  **one per poll**, paced by `pace()` (1-8×, from the running average CAT reply time).
- `TOUCH_HOLD_S` = 1.2 s: values the user just changed are not overwritten by stale polls.
- `rig.tune` for TUNE on both radios.
- Background CAT reads per poll (at most one): controls after connect, Rig Settings menu items,
  then `EXTRA_READS` (SHIFT in USB/LSB, CLAR/RIT) every 4.5 s, then one receive control every 1.5 s.
- **VFO Scan** (`vscan_*`, FT-891, 27f): the **radio scans**; RigPanel only sends `SC1;`/`SC2;`/`SC0;`
  (`vscan_cmd`, optional start frequency first), reads `SC;` every 0.5 s and `SQ0;` / `EX0516;` on opening
  (`vscan_read`), sets squelch (`vscan_squelch`) and 05-16 (`vscan_resume`), `vscan_goto` = stop + tune.
  Everything else (stop detection, band limits) is in the window (§8.3).
- **flrig 2.0.12+ and the FT-891** (27o, `yaesu_cmd_string`, set in `_connect` from `main.get_version`):
  sets go with **`rig.cmd_string`** (writes, no wait), then the read-back alone; **every Yaesu read checks
  the answer starts like the question** (`NB0;` → `NB0…`) and asks again, `YAESU_READ_TRIES` = 3. 2.0.09
  keeps set+read in one `cat_string` (§7.2). Details §7.5.

### 4.1 Raw CAT through flrig - format (1.4)

**Every** raw command is sent as hex, **exactly 3 characters per byte, no spaces**:
IC-7300 `xFExFEx94xE0x16x22xFD`, FT-891 `x4Ex42x30x3B` (= `NB0;`).

- flrig **2.0.12** reads every `cat_string` as `x%2X` chunks of 3 characters; a space breaks the
  parse and the radio receives garbage (nothing happens, flrig waits its timeout, then returns
  whatever is in its buffer - often its own poll's answer). Plain text (Yaesu) is mis-read too.
- flrig **2.0.09 / 2.0.10** accept the same no-space hex (and garbled plain Yaesu strings containing
  an `X` - another reason to always send hex).

Replies (`radios.to_bytes`, `icom_reply_data`, `hex_reply_text`) understand:
- old: `xFE xFE xE0 x94 … xFD` (Icom) or `45 58 31 …` (Yaesu hex) or plain `EX16151;`;
- **2.0.12**: `" %2X"` per byte of a *signed* char → every byte ≥ 0x80 prints as `FF`, single digits
  get a leading space (`"  1"`), no echo. Icom frames are found by splitting on `FF` (FE FE E0 94 and
  FD all read FF); a frame that starts with the command is the answer. A data byte ≥ 0x80 is
  **lost** (e.g. BCD `00 89`): `menu_parse` then returns `UNREADABLE` ("?") - Rig Settings send it
  and count it as sent, `_macro_matches` ignores it. ALC/level reads that come back short fall back
  to flrig's getter.

---

## 5. flrig behaviour that matters (proven)

| flrig | Fact | RigPanel |
|---|---|---|
| 2.0.12 | `cat_string` strict hex, `FF` replies (§4.1). Source: 2.0.12.05 `xml_server.cxx` `recv_hex`/`send_hex` | No-space hex everywhere, 2.0.12 reply decoding |
| 2.0.12 | `cmd_string` only writes (returns `''`), no wait; `cat_priority` is listed but "unknown method name"; `rig.cmd` presses flrig's own command buttons; `get_*_label(s)`, `get_info`, `get_update`, `incr_agc`, `shutdown` exist | `cmd_string` for FT-891 sets (27o) |
| 2.0.12 | `cat_string` = write (no flush) + `waitResponse` → `readResponse(";", "\xFD")`: up to 100 × 10 ms (≈1.2 s). FT-891: a read is 0.07 s, but **now and then the answer is someone else's** (flrig's own poll `MD0C;`, or the previous request's) - measured 2026-10-27 (`ft891_212_timing.py`, source `support/rig_io.cxx`) | Checked reads + retry (§4, §7.5) |
| 2.0.12 | `waitResponse` waits 10 ms, then the **full serial timeout** if the radio is silent (1.2-2.2 s per bad command = the old 3-5 s VFO delay) | Fixed by correct format |
| 2.0.09 | FT-891 "set" commands get no reply → flrig waits ~6.2 s | Every Yaesu set is sent together with its read (§7.2) |
| all | Meters only update if **flrig > Config > Setup > Poll: S-mtr, Pwr out, SWR, ALC** are ticked | Install guide; FT-891 Po now read directly (§7.6) |
| all | At start-up flrig restores its saved freq / mode / bandwidth / levels (incl. VFO B) to the radio, overriding it (and RigPanel). **Config > Setup > Restore: untick Freq, Mode, Bandwidth, Volume/gain; tick Use xcvr data** (operator, 2026-10-27 - still being tested; it fixed VFO B coming back wrong on the FT-891) | Install guide; FLRIG_COMPATIBILITY.md |
| all | flrig keeps its settings per PC (`~/.flrig`); a source-built flrig can run beside the installed one with `--config-dir` (`tools/flrig_side_by_side.sh`) | Testing other flrig versions |
| all | `rig.set_rfgain` was ignored for the IC-7300 (2.0.10) | RF gain by CAT `14 02` |

Digital apps through flrig (FT-891): **JS8Call / WSJT-X → Settings → Radio: Poll Interval 3 s,
PTT CAT, Mode None, Split Operation None.** With Mode = Data/Pkt and Split = Fake It they send
FT-891 sets on every frequency change and transmission; flrig waits each out and TUNE / frequency
changes lagged 5-10 s (2026-10-24). RigPanel's own requests were all < 1 s in the log.

---

## 6. IC-7300 (CI-V through `cat_string`) - what we know

CI-V address `0x94` (setting `civ_addr`), controller `0xE0`. Operator's radio settings (from his
guides): CI-V USB Echo Back ON, Transceive ON, USB baud matching flrig.

### 6.1 Receive controls (`IcomProfile.controls`)

| Control | CI-V | Values | Notes |
|---|---|---|---|
| AGC | `16 12` | FAST 1 · MID 2 · SLOW 3 | |
| P.AMP | `16 02` | OFF 0 · P.AMP1 1 · P.AMP2 2 | |
| ATT | `11` | OFF 00 · 20 dB 0x20 | |
| IP+ | `1A 07` | toggle | |
| NB / NR / Notch / Auto Notch | `16 22` / `16 40` / `16 48` / `16 41` | toggle | Manual **Notch** cuts ~1500 Hz of the *audio* (WIDE): shows as a dark band in RigPanel's waterfall and is heard by digital apps, but the radio's scope (pre-DSP) doesn't show it |
| **NR level** (▾) | `14 06` | 0-15 ↔ 0000-0255 BCD (n×255/15) | 1.4 |
| **Filter FIL1/2/3** (mode row) | read `04` → (mode, filter); set: data mode on → `1A 06 01 ff`, else `06 mm ff` | 1-3 | Never changes the mode (USB-D stays USB-D). After a change, `get_bws` is re-read |
| **Tuner** (mode row) | `1C 01` | 00 off · 01 on (02 = tune - not used) | In/out only; TUNE uses `rig.tune` |
| RF gain | `14 02` | 0000-0255 BCD ↔ 0-100 % | flrig's setter ignored on this radio |
| ALC meter | `15 13` | 0000-0255, ALC zone 120/255 | |
| Po | flrig `get_pwrmeter` (× `get_pwrmeter_scale`) | | **Matches the radio's own Po meter** (operator: both read ~12 W under the power setting on his antenna) - leave it |

### 6.1a Added in 1.4.1 (checked on the operator's radio 2026-10-25/26)

| Function | CI-V | Facts |
|---|---|---|
| S-meter `15 02` (was used by Voice Scan, removed 27f) | `15 02` | 0000-0255, S9 = 0120, S9+60 = 0241; quiet band reads 0 with P.AMP off. **With AGC FAST it drops to 0 between words** (stations read only on voice peaks); AGC SLOW holds it up (band reads 2026-10-27, `ic7300_band_read.py`) |
| **SHIFT** (FILTER screen) | `14 07` (PBT1 only) | 0128 = centre, **5 Hz per unit**, radio steps 25 Hz, ±625 Hz. **USB: Hz = (raw−128)×5; LSB: sign flips** (0103 → USB −125 / LSB +125) |
| **RIT** | `21 01` on/off, `21 00` offset | offset = 2 BCD bytes (10/1 Hz, 1000/100 Hz) + sign byte (00 +, 01 −), to ±9.999 kHz. `21 02` = ΔTX (not used) |
| Menu read retry | `1A 05` | flrig 2.0.12 sometimes returns its own poll's answer; `ex_read` tries twice on the IC-7300 |

- **P.AMP and ATT are remembered per band by the radio itself** (RF gain is not). On the operator's
  station 20 m had P.AMP1 and 40 m ATT 20 dB; **P.AMP on or ATT off turns the scope yellow/orange** -
  not RigPanel. Hence the Scan Settings Default: P.AMP OFF, ATT OFF.
- flrig 2.0.12 hides RF gain read-backs of 32-39 % (BCD xx80-xx99) - treated as success, not failure.

- **Why the S-meter scan was dropped (27f):** stepping the dial through flrig sees only ~0.5 s
  snapshots per step, so stations were missed; and the right SSB dial spot can't be found from S-meter
  readings - a station reads across ±2.5 kHz of the dial (`ic7300_signal_shape.py`), and "middle of the
  edges" lock-in was ±2 kHz off on a busy band. The IC-7300's own scope shows stations better.
- **Filter as a Rig Settings item (27n):** `FILTER` (FIL1/2/3) sits between MODE and WIDTH; applied first
  (`set_filter`), then the width (each filter keeps its own width). A Rig Setting with a FILTER leaves
  FILTER and WIDTH out of `_macro_matches`, so switching filters for strong / weak signals keeps it green.

### 6.2 Rig Settings items (`IC7300_MENU` / `IC7300_CIV`)

Menu items are `1A 05 00 xx`; numbers **verified on the operator's radio** with `tools/icom_check.py`
(2026-10-23), values matching his guides:

| Code | Item | Kind | Operator's values |
|---|---|---|---|
| 0059 | ACC/USB Output Select | byte: 0 AF · 1 IF | AF |
| 0060 | ACC/USB AF Output Level | % (0000-0255) | 50 % (raw 0128) |
| 0063 | ACC/USB IF Output Level | % | 50 % (not in the table) |
| 0064 | ACC MOD Level | % | 50 % |
| 0065 | USB MOD Level | % | 40 % (raw 0103) |
| 0066 | **DATA OFF MOD** (audio source in USB/LSB) | byte: 0 MIC · 1 ACC · 2 MIC,ACC · 3 USB | **3 = USB confirmed**; MIC = 0 is the best reading of Icom's list - operator to confirm on the radio |
| 0067 | DATA MOD (audio source in USB-D) | same | USB |
| COMP | `16 44` on/off · COMPLV `14 0E` 0-10 (0000-0255) | | |
| TBW | `16 58` WIDE 0 · MID 1 · NAR 2 | | |
| MONI / VOX | `16 45` / `16 46` | | |
| AGC | `16 12` | | |

**All Menus (1.4.1):** every SET item 0001-0197 that is a simple value - 141 items in 9 groups
(Tone Control/TBW, Function, Connectors, Display, Scope, Keyer/Contest, RTTY, Scan/Voice/Recorder,
NB/VOX/More; `ic7300_section`). Numbering checked with `ic7300_menu_dump.py` (0091 = opening message
"KW3KW", 0094 = date). One-byte values are BCD, so value dicts are keyed by the raw byte. TBW byte:
high nibble = upper edge (2500/2700/2800/2900), low nibble = lower edge (100/200/300/500): WIDE 0x30 =
100-2900, MID 0x12 = 300-2700, NAR 0x03 = 500-2500. Left out: HPF/LPF pairs, split offsets, text,
date/time, colours, scope edges. Locked: 0058 REF adjust, 0071-0080 CI-V/USB link (0074 read-only).
Items above 0197 answer on current firmware but aren't documented - not shown.

**Key fact:** with DATA OFF MOD = USB the microphone is silent in plain USB/LSB (audio comes from the
computer). The Voice button sets MIC, the Data button USB. The IC-7300 keeps DATA OFF MOD and DATA
MOD separately, so USB ↔ USB-D already switches the source when they differ.

What does **not** work for voice/data switching: loading an SD-card settings file (front panel
only, no CI-V; the radio restarts) and memory channels (frequency/mode/filter only).

Built-in starting buttons (`IC7300_DEFAULT_MACROS`): Voice (LSB/USB by band, 2400, DATA OFF MOD MIC,
COMP ON 3, TBW WIDE, MONI/VOX OFF, AGC MID) and Data (USB-D, 3000, DATA OFF/DATA MOD USB, USB MOD 40,
AF out 50, AF, COMP OFF, MONI/VOX OFF, AGC FAST, NB/NR OFF). Operator's own Voice adds NB, NR, Notch,
IP+ ON (in `examples/`).

### 6.3 Flrig 2.0.12 specifics for the IC-7300

Every CI-V frame contains bytes ≥ 0x80 (FE FE 94 E0 … FD) - so with spaces in the hex **nothing
worked** on 2.0.12 (verified: NB/ATT/P.AMP/AGC didn't change on the radio; flrig's labels didn't
change either). With no-space hex all worked at once (`tools/flrig212_write_check.py`, 2026-10-24).
Levels whose BCD bytes are 0x80-0x99 can't be read back on 2.0.12 (§4.1).

---

### 6.4 Added in 1.4.3 (operator's IC-7300, Windows, flrig 2.0.12, 2026-11-05)

| Function | CI-V | Why |
|---|---|---|
| **A⇄B** (exchange VFOs) | `07 B0` | flrig's `rig.swap` only selected VFO B |
| **AF Volume / MUTE** | `14 01` (0000-0255, read back) | flrig's `rig.set_volume` didn't reach the radio in voice / CW; now like RF gain (`LEVEL_SUB`) |
| **BKIN** OFF / SEMI / FULL | `16 47` 00/01/02 | CW only (`CW_ONLY`, `_show_cw_rows`) |

## 7. FT-891 (Yaesu ASCII CAT through `cat_string`) - what we know

Operator's station: FT-891, Digirig on `/dev/ttyUSB0`, 19200 baud, FC-50 (16-15 TUNER SELECT =
EXTERNAL) and ATAS, Linux Mint, flrig 2.0.09.

### 7.1 Receive controls (`YaesuProfile.controls`)

| Control | Set / read | Values | Notes |
|---|---|---|---|
| AGC | `GT0n;` / `GT0;` | OFF 0 · FAST 1 · MID 2 · SLOW 3 · AUTO 4 (5/6 read as AUTO) | per VFO |
| IPO / AMP | `PA0n;` / `PA0;` | IPO 0 · AMP 1 | per VFO; IPO = preamp off |
| ATT | `RA0n;` / `RA0;` | OFF 0 · ON 1 | per VFO |
| NB | `NB0n;` / `NB0;` | toggle | per VFO |
| DNR | `NR0n;` / `NR0;` | toggle | radio-wide |
| **DNR level** (▾) | `RL0nn;` / `RL0;` | **01-15** | 1.4; radio-wide |
| DNF | `BC0n;` / `BC0;` | toggle | radio-wide |
| Notch (manual) | `BP00nnn;` / `BP00;` | toggle | radio-wide |
| **Tuner** (mode row) | `AC00n;` / `AC;` → `AC00n;` | 0 off · 1 on (`AC002;` = start tune - not used, TUNE uses `rig.tune`) | Acts on the tuner chosen in 16-15 (FC-50 or ATAS). 1.4 |
| RF gain | `RG0nnn;` / `RG0;` | **0-30** (`RG_MAX`) ↔ 0-100 % | |
| ALC | `RM4;` → `RM4nnn;` | 0-255, zone 0.5 | |
| **Po** | `RM5;` → `RM5nnn;` | 0-255, **not linear** | §7.6 |
| Mode (VFO B path) | `MD0x;` | `MD_CODES` (DATA-U = C) | only if flrig is on its "B" |

### 7.1a Added in 1.4.1 (checked on the operator's radio 2026-10-25/26)

| Function | Set / read | Facts |
|---|---|---|
| S-meter | `SM0;` → `SM0nnn;` | 000-255 (S9 ≈ 128 = flrig's 50); quiet band ~8-15 with RF gain max. **With RF gain turned down the meter sits at a raised floor** (read 53 everywhere). Not used since 27f |
| **SHIFT** | `IS01±nnnn;` / `IS0;` → `IS0P±nnnn;` | P = 1 while the knob is on SHIFT, 0 on WIDTH; 20 Hz steps, ±1200 |
| **CLAR** | `CF0n0;` / `CF0;`; `RU`/`RD` `nnnn;` up/down by Hz, `RC;` clear (no answers → paired with `IF;`) | state from `IF;`: chars 15-19 = ±offset, 20 = CLAR on. `RT0;`/`XT0;` answer `?;` |
| **PROC** | `PR0n;` / `PR0;`; level `PLnnn;` / `PL;` (0-100) | `PR1` = mic EQ (not used) |
| Menu 13-02 | `EX1302nn;` | **2 digits** on the radio (the CAT book says 1) |
| Menu 17-01 RESET | - | no answer (flrig waits 6 s) - left out on purpose |

### 7.2 Set + read pairing (the 6-second rule)

The FT-891 **does not answer set commands**; flrig 2.0.09 then waits ~6.2 s and returns
`No response: FT-891`. `yaesu_readback()` appends the matching read to every set, so the radio
answers at once **and** confirms: `NB01;NB0;`, `EX16151;EX1615;`, `SV;FA;`, `AB;FB;`, `RL007;RL0;`,
`AC001;AC;`, `IS01+0100;IS0;`, `CF010;CF0;`, `RC;RU0120;IF;`, `PR01;PR0;`, `PL035;PL;`, `SQ0030;SQ0;`, `SC1;SC;`.
On flrig **2.0.12+** the set goes alone with `rig.cmd_string` and the read follows (§7.5).
The prefix list is in `yaesu_readback` - **any new FT-891 set command must be added
there**, or each use costs ~6 s (the DNR level and Tuner nearly shipped without it).

### 7.3 VFOs

- **No VFO select over CAT** (`VS0;`/`VS1;` → `?;`). flrig's "VFO B" really swaps the registers.
  **27k: the FT-891 shows the same VFO A / VFO B buttons as the IC-7300** - VFO B / VFO A = `SV;` and
  RigPanel remembers the side (`ft891_vfo_side`, kept across restarts); **A⇄B = `SV;`** too but stays
  on the same side (contents swap); **A=B = `AB;`**; VFO B read with `FB;`; split works. Shift+A /
  Shift+B pick A / B. The radio's own A/B key isn't seen over CAT - pressing VFO A or B once lines it up.
  If flrig is found on its "B", RigPanel puts it back to A once.
- Mode can't be set while flrig is on its "B" → `MD0x;` path (`MD_CODES`).
- **Per VFO:** frequency, mode, AGC, IPO/AMP, ATT, NB. **Radio-wide:** RF power, mic gain, RF gain,
  AF volume, DNR (+ level), Notch, DNF. Voice/Data memory (App §8.3) puts the radio-wide ones back.
- **Firmware bug:** every A/B swap forces the DATA-U/L bandwidth to **500 Hz**; RigPanel puts the
  data width back within 4 s of A⇄B (`swap_check`).
  **Closing flrig does two swaps too** (flrig `closeRig` → `restore_xcvr_vals`: selects B, then A), so the radio is
  left at 500 after every flrig close; RigPanel also arms `swap_check` for 10 s on connect (30a).

### 7.4 Menu items (Rig Settings) - `EX` + 4-digit menu

**All Menus (1.4.1):** all 155 EX menus 01-01 … 18-03 (`FT891_MENU`, groups `FT891_SECTIONS` as on the
radio), digits and values from the CAT book, every code checked with `ft891_menu_dump.py`. Signed values
(05-13, 05-17, 08-03/04, 12-02, 15-x2 levels) carry the sign as a digit (`EX1502+10;`). Locked: 05-06 CAT
RATE, 05-07 CAT TOT, 05-08 CAT RTS (would cut flrig off), 18-xx versions (read only). PROC / PROCLV ride
along as menu-like items (`YaesuProfile.NON_EX`). The Common view is the list below plus PROC.


Sent as hex (they contain an X). **Read first, write only if different** (re-writing 16-15 can
disturb the tuner). A code is treated as unavailable only after **3** bad answers in a row
(`ex_unsupported`).

| Menu | Setting | Values |
|---|---|---|
| 05-03 | NB LEVEL | 0-10 |
| 05-12 | ATAS SETTING | DISABLE / ENABLE |
| 08-01 | DATA MODE | PSK / OTHERS |
| 08-09 | DATA IN SELECT | MIC / REAR |
| 08-10 | DATA PTT SELECT | DAKY / RTS / DTR |
| 08-11 | DATA OUT LEVEL | 0-100 (RX audio to the data jack, not power) |
| 08-12 | DATA BFO | USB / LSB |
| 11-05 | SSB MIC SELECT | MIC / REAR |
| 11-06 | SSB OUT LEVEL | 0-100 |
| 16-01 | HF SSB PWR | 5-100 W - **used in SSB (voice)** |
| 16-03 | HF PWR (data/CW) | 5-100 W - **used in DATA-U** |
| 16-15 | TUNER SELECT | OFF / EXTERNAL / ATAS / LAMP - TUNE is blocked when OFF |
| 16-16 | VOX SELECT | MIC / DATA |

Order (`ALL_ITEMS`): mode first, width, menus, filters, then **05-12 before 16-15** (ATAS supply off
before another tuner is selected). FC-50 buttons must set **05-12 DISABLE + 16-15 EXTERNAL**, ATAS
buttons **ENABLE + ATAS** (the operator's own FC-50 buttons lacked 05-12; fixed in the example file).

**Power:** RigPanel's RF Power bar (flrig `set_power` → `PC`) sets the menu of the **current mode**:
in DATA-U it changed 16-03 (40 W set → 16-03 = 40), in voice 16-01 (93). Verified 2026-10-24.

### 7.5 flrig 2.0.12 and the FT-891 (proven 2026-10-27, build 27o)

2.0.12 reads plain text as hex too, so all FT-891 commands go as no-space hex. First real test (2.0.12
built beside 2.0.09 on the Mint PC): everything worked but **every click took ~2 s**. Log: single
reads (`NB0;`, `FB;`, `RG0;`, `PA0;`, `EX0512;`, `IF;`) 1.2 s each. `ft891_212_timing.py`: a read is
0.07 s, but answers get mixed up (`FA;` → `MD0C;`, three reads → the previous `FA…`). Fix (27o): sets via
`rig.cmd_string`, reads checked and repeated (§4). Operator: **"Fast and works great!"** The 2.0.09 path
is unchanged; RigPanel picks by `main.get_version` at every connect, so switching flrig versions needs
nothing.

### 7.7 VFO Scan - the radio's own scan (27f-27q)

`SC1;` up / `SC2;` down / `SC0;` stop / `SC;` → `SCn;`; about **22 kHz a second**; it runs **right out of
the band** (went from 20 m to 15.2 MHz) - RigPanel keeps it inside the segment. Squelch `SQ0nnn;`
000-100 (the knob is RF gain while **05-05 = RF**, so CAT is the easy way). **05-16 MIC SCAN RESUME**:
0 PAUSE (stay until the signal ends), 1 TIME (5 s) - not 05-17 (REF FREQ ADJ). 05-15 MIC SCAN = ON on
the operator's radio. Checked with `tools/ft891_scan_check.py` (2026-10-27, flrig 2.0.09, all 0.1-0.2 s).
The radio stops where its **squelch opens**, i.e. at the edge of an SSB signal: measured on 40 m
+4.2, +0.4, −1.7, −0.4 kHz from the voice - **no fixed offset to correct**. Squelch 30 ran past
stations; ~10 worked; at 0 it stops on noise. AGC / bandwidth trade-offs (catch more vs stop closer)
are being tested by the operator.

### 7.8 Added in 1.4.3 (operator's FT-891, Linux, flrig 2.0.09, 2026-11-06)

- **BKIN** OFF / ON: `BI0;` / `BI1;`, read `BI;` (checked with a read-only paste script); in `yaesu_readback`.
- CW is **CW-L** for the operator: the CW button picks CW-L first (a CW Rig Setting's Mode decides otherwise).
- Closing flrig leaves the DATA width at 500 (its `restore_xcvr_vals` swaps twice) - RigPanel puts it back on connect
  (30a, `swap_check`); FLRIG_COMPATIBILITY.md.

### 7.6 Power meter (`RM5`) - measured curve

flrig's FT-891 conversion is a straight line (raw × ~0.39) and read **~12 W high** at low power
(10 W set → 22 W, 20 W → 33 W) while the radio's own display showed the setting. Measured on the
operator's FT-891 with JS8Call Tune (`tools/ft891_po_check.py`, 2026-10-24):

| Set (W) | 10 | 20 | 40 | 60 | 80 | 100 |
|---|---|---|---|---|---|---|
| RM5 raw | 56 | 82 | 125 | 156 | 168 | 180 |
| flrig Po | 22 | 33 | 49 | 61 | 66 | 71 |

`YaesuProfile.PO_TABLE = [(0,0),(56,10),(82,20),(125,40),(156,60),(168,80),(180,100)]`, interpolated
(`parse_po`), extrapolated past 180. The worker uses `profile.po_string()/parse_po()` when the
profile has them, else flrig's `get_pwrmeter`. The curve assumes output = setting (confirmed on the
display at 20 W). Built-in meters are ±10-20 %; neither radio's meter sees cable loss.

---

## 8. Main window behaviour (App)

### 8.1 Look

Header (icon, name, version, FLRIG / RIG / UTC labels above green values, gold **Scan** (FT-891 only -
opens VFO Scan; same bright gold in both themes), Mini Meter, Connect, red TUNE), blue accent line, toolbar (Rig, flrig Host, Port, Theme, **Settings ▾**, **Hot Keys**,
(Compact View button removed 11-14d; `enter_compact` still there) - the Waterfall button was removed in 1.4, Shift+W instead). Dark **HUD** display
panels (`HUD` palette, same in both themes) for frequency, meters, levels and both mini windows.
Section titles in capitals with an accent bar. Green = on / matches the radio; blue = choice in use;
red = transmit / go back. Level colours: RF Power red `#ff4d4d`, Mic Gain magenta `#e040fb`, RF Gain
blue, AF Volume green `#2ee06e`. S-meter green → yellow past S9 → red past +20. RX badge green, TX red.

**1.4.2 look:** `FlatButton` is now a canvas-drawn raised key (gradient, top highlight, drop shadow,
rounded; coloured `base` buttons stay solid; `on` = pressed in, in `on_color`) - same API as before
(`config(text/padx/pady)`, `cget("text")`, `set_on`, `.command`). Theme key `title` (Light #8f131a, Dark
#ff6b6b) colours all section titles and row labels (`section`, `small_label`, RIG SETTINGS / ANTENNA / THEME);
`profile` colours the Profile line. VFO B and RIT/CLAR labels use the Dark gold in both themes.

### 8.2 Rows

Frequency (+ VFO B block, **CLAR/RIT** block on the right; the kHz box is gone - **Shift+G** opens a
"Go to kHz" box, `goto_box`) · BAND (+ **Tuner On / Off** far right, `band_tail`) · MODE (groups spread evenly) (Voice/Data, mode, bandwidth,
**Shift** in USB/LSB, IC-7300 FIL1/2/3, Tuner) · **Rig Settings**
("Rig Settings:" gold, buttons with tooltip "Apply <name> Settings", Antenna group, blue
"Edit Rig Settings") · METERS | LEVELS | RECEIVE / FILTERS · waterfall (optional) · status bar.
Fits about 1080 (FT-891) - 1120 (IC-7300) px wide depending on fonts. The mouse wheel never changes
the Rig or Theme box (blocked - it once switched an IC-7300 to the FT-891 profile).

### 8.3 Behaviour

- **Voice/Data memory** (`levels_per_kind`, default on): levels (`levels_by_kind`), clicked receive
  controls (`ctl_by_kind`) and bandwidth (`bw_by_kind`; 2400 voice / 3000 data) are remembered per
  kind and put back when the mode kind changes (A⇄B, Voice/Data, Rig Settings, radio knob). On the
  IC-7300 an A↔B switch can put back ~11 settings - each is a CAT command, which is why slow CAT
  (old 2.0.12 format) showed up as a 3-5 s VFO delay.
- **Rig Settings** (`run_macro`): refuses during TX; reads each item, writes only if different,
  reads back, posts `macro_done` (try/finally; 90 s watchdog). Status "all N settings applied and
  confirmed ✓" or the failed names. A button is green while the radio matches (`_macro_matches`,
  ignoring `ex_unsupported` and `UNREADABLE` items). Lists per radio: `ft891_macro_list`,
  `ic7300_macro_list`.
- **Hot keys** (`App.HOTKEYS`, `bind_all <Shift-X>`, ignored while typing in Entry/Combobox/Text):
  V Voice, D Data (exact name, else first name starting with it), E Edit Rig Settings, A/B VFO
  (FT-891 by swapping, 27k), Z Mini Meter, L Mini Levels, W Waterfall, M Mute, G Go to kHz; Ctrl+W
  pop-out. (S/H/R/X went with Voice Scan.)
- **VFO Scan window** (`vscan.py`, FT-891, `show_scan_button` hides the gold Scan button on the IC-7300):
  HUD floating window (mock-up A). Status SCANNING ▲/▼ / STOPPED; **click-a-digit `FreqDisplay`** (27p:
  tuning a digit stops the scan, `app.tune_to`); segment line ("40 m voice, Extra: 7,125 - 7,300 kHz");
  ▼ Down / ■ Stop / ▲ Up; SQUELCH bar (click / ◀ ▶ ±5 / wheel ±1); ON A SIGNAL Wait 5 s / Stay (05-16);
  BEGIN AT From here / At the band edge (`vscan_start`; ▲ from the bottom, ▼ from the top); LICENSE
  General / Extra (`scan_class`); AT THE END Go round / Stop (`vscan_end`). **Range limit** (`_check_edge`,
  every 0.25 s): past the segment end → go round (start at the other end) or stop inside; overshoot a few
  kHz; ▲/▼ refuse outside a voice segment and on 60 m. `limits` are cleared **only by a real stop**
  (27i fix: clearing on the radio's late "stop" state let the scan run out of 40 m). **HEARD list**
  (`_watch_stop`): scanning and the frequency hasn't moved for 1 s = a stop → listed (exact Hz, 0.1 kHz
  shown; 27p rounded to whole kHz, operator preferred exact, 27q); within 2 kHz = same station (x2…),
  low to high, ▲/▼, "now"/"n min", scrolls (8 rows), click = stop + go there, right-click = remove, Clear;
  kept in `app.vscan_heard` while RigPanel runs; stops outside the segment aren't listed. EXIT stops the
  radio's scan. Stop detection and edge checks run on the UI timers - the worker only sends commands.
- **RF gain per band** (1.4.2, `app.py`, LEVELS tick box `rf_band_var`, default on): `rf_by_band` keyed
  `"rig:band"`; `pick_band` / band change from the radio's knob (only when the frequency wasn't just set
  by RigPanel, `_recent("freq")`) saves the old band's value and puts back the new one's;
  `_restore_levels` then leaves RF gain alone.
- **SHIFT / CLAR / MUTE** (`extras.py`): read back after every change and followed in the background;
  MUTE keeps the volume it replaced and doesn't touch `levels_by_kind`.
- **Edit Rig Settings** (both radios): VIEW Common | All Menus (`rs_view`), MENU GROUP dropdown with
  "(n)" = items used, blue names = in this Rig Setting, Radio now column (read on group change / Read
  this group; click to copy), Read from radio also refreshes the group on screen, Save as new.
  **Save** only stores the Rig Setting; **Save & Apply** (27l) saves and runs it, the result shows in the
  editor (`_macro_done` → `macro_win.say`). **Resizable** (27m; never below its opening size; the All
  Menus table grows; size/place in `rs_geom`, a PC key). Tooltips on every button. IC-7300 **Filter**
  item (27n, §6.1a). The Hot Keys button lists the hot keys (`hotkey_menu`).
- **Mini windows** (`minis.py`): borderless, topmost (re-lifted every 2 s on X11), drag to move,
  drag a corner to resize (fixed aspect, scale 0.8-3.0, pixel fonts), right-click menu (options,
  Normal size, Hide). Mini Meter: Pop up when transmitting / Always; Full Panel button in Compact
  View. Mini Levels: Pop up when receiving / Always; bars clickable (calls the main `LevelBar._change`);
  **S-METER row on top** (28a, `MiniMeter._meter_row` / `_paint_meter` shared with the Mini Meter; right-click
  Show S-meter, `lv_smeter`, adds 58 px at size 1.0).
- **Level menus** (`level_menu`): ▾ next to a control with `Control.level`; worker `ctl_level()`
  sets and reads back, posts `ctl_level`.
- **Settings ▾**: Save settings to a file / Load from a file / Save as my default / Return to my
  default (asks) / Open settings folder. Files hold **everything**, Rig Settings included. Loading keeps
  `PC_KEYS` (host, port, rig, civ_addr, audio_device, mini/lv pos+scale, wf_float_geom, rs_geom) and backs
  up to `settings_before_load.json` first. Settings live in DATA_DIR, so program updates never touch them.
- **Menus** (`popup_menu`, 27j): Windows - `tk_popup` then `grab_release` (the usual recipe); Linux/X11 -
  `tk_popup` returns at once, and releasing the grab meant a click outside couldn't close the menu, so
  the grab is left to Tk. Escape closes. **Open settings folder** from the frozen Linux app restores the
  system `LD_LIBRARY_PATH` for `xdg-open` (27o; the file manager didn't start).
- **Starter frequencies** (`RADIO_DEFAULTS` = `_starters`, `_seed_radio_defaults`; 14h: voice start/end per band incl.
  General/Extra, W1AW CW, JS8, FT8 - 42, added radios too; drop-down by band past `MEM_FLAT_MAX` 20):
  given once per radio (`seeded`) only when the PC has no stored frequencies. A stored frequency
  made on the other radio is translated (`DATA_MODE_SAME`: USB-D ↔ DATA-U).
- Theme switch rebuilds the window and restores state (`apply_theme` / `_restore_view`).

---

### 8.4 Voice / Data / CW (1.4.3)

- **Three memory kinds** (`memory_kind`: data / cw / voice; CW and RTTY = cw). Each has its own width (`DEFAULT_BW`
  2400 / 3000 / 500), levels, clicked receive controls and per-band frequency (`band_memory` "band:kind"). Picking a
  mode of another kind puts that kind back; a BAND click in CW stays in CW (first time: band edge + 25 kHz).
- **Mode row Voice | Data | CW** = the Rig Setting of the same name, if any (`_kind_macro`). Those three no longer
  get a Rig Settings button (the row keeps ANTENNA and others). A click switches mode and width **at once**
  (`set_voice_data`), holds them ~5 s against late readings of the old mode (`touched` in the future), then runs the
  Rig Setting in the background with `quick=True`: menu items read or set in the last 10 min (`menu_known`,
  `MENU_TRUST_S`) are not re-read. A saved Mode of the wrong kind is ignored; **power menus (16-01..16-04) are skipped**
  (`POWER_ITEMS`) - the RF Power slider and its per-kind memory decide.
- Order on a mode change (`_on_poll`): take the new mode **first**, then `_restore_levels` (else the width was saved
  into the old kind's memory - fixed 06b). The worker posts the new width list before the poll, so `_restore_bw`
  can run at once; it always sends the width.
- Stored frequencies: CW / RTTY red (`mode_kind` returns cw, `kind_color`), "Red = CW" in the key.
- Mini Levels has an **S-METER** row (28a, `lv_smeter`). Theme switch drops the old mini windows first (11-01a fix
  for the freeze / "--" header).

### 8.5 BKIN and the Ctrl tap (1.4.3, 2026-11-09)

**BKIN OFF / SEMI / FULL, both radios, shown only in CW** (`CW_ONLY`, `_show_cw_rows`):
- IC-7300: CI-V `16 47` 00/01/02 (plain select control).
- FT-891: no 3-way break-in command - **OFF = `BI0;`; SEMI / FULL = menu 07-08 BK-IN TYPE (0 SEMI, 1 FULL) + `BI1;`**
  (`worker.set_bkin` / `read_bkin`; the panel click goes there, `read_control` too). `BI` checked on the operator's
  radio with a read-only paste script (`BI0;`/`BI1;`), `BI` is in `yaesu_readback`.
- **Rig Settings item `BKIN`** (both radios, `BKIN_VALUES` OFF/SEMI/FULL, `macro_choices`): in the Common list and in
  All Menus next to Mode / Filter / Width; applied with `set_bkin` and read back, captured by Read from radio, used by
  `_macro_matches` (`ctl_values["bkin"]`). Not a menu code - never in the background menu reads.
- Edit Rig Settings Width list now has CW widths 300-1400 as well as 1800-3200.

**Ctrl tap - RigPanel forward / back from any program** (`CtrlTap` in `extras.py`, setting `ctrl_tap`, default on):
- Only a **lone Ctrl press-and-release under 0.45 s** counts; Ctrl+C / Ctrl+V and a held Ctrl don't. The operator
  rejected every key that types (Shift+Z, Shift alone) and F9 (mic mute on many keyboards); his mini keyboard has no
  Pause / Scroll Lock; Fn never reaches the OS.
- Keyboard state is **polled, nothing is grabbed**: Windows `GetAsyncKeyState`, X11 `XQueryKeymap`, on **its own
  thread every 15 ms** (the UI timer missed ~0.1 s taps). The thread sets a flag; `_ctrl_tap_tick` (UI, 50 ms) acts.
  Does nothing on Wayland.
- `toggle_front`: RigPanel in front and **active** -> **minimize**; otherwise **restore + bring to the front** on its
  own monitor (never moved). "Active": Windows `GetForegroundWindow` == `wm_frame`; X11 the taskbar's
  `_NET_ACTIVE_WINDOW` (XGetInputFocus lagged after clicking another program -> two taps needed), compared with
  RigPanel's window **and its parents** (the focus is on Tk's wrapper, not `winfo_id`).
- Coming to the front: **Windows** refuses a background program -> `AttachThreadInput` to the front program's thread,
  `BringWindowToTop` + `SetForegroundWindow`, detach. (A lone Alt "keybd_event" trick put the window in **menu mode** -
  it came up blank: don't.) **Linux/Mint** ignores a raise from the background -> send `_NET_ACTIVE_WINDOW` with
  source 2 (pager) like a taskbar. Going back = minimize (re-activating the previous program left RigPanel on screen).
- X11 safety: own `XOpenDisplay` per thread (sharing one jammed the watcher); an **X error handler** that returns 0
  (Xlib's default exits the program - a `XQueryTree` on window 1 killed it); window 0/1 = no focus.
- First taps can be slow (loading / the WM's animation), then quick (operator, 11-09). One debug line per tap
  ("Ctrl tap: state ..., active ...").
- Proven by the operator 2026-11-09: Windows 11 (09e) and Mint with two monitors (09h), main and other monitor.

### 8.6 Add my radio (1.4.3, build 14c)
- Settings ▾ > Add my radio (`extras.open_add_radio`): Name, "flrig calls it" (upper-case match, exact or substring of
  flrig's `rig.get_xcvr`), family `icom` / `yaesu` / `flrig`, CI-V hex (Icom). Stored in `custom_rigs`
  `[{name, match, family, civ}]`; `rig_choices()` = built-in + added names.
- `radios.make_profile(choice, xcvr, civ, custom)` checks `find_custom` first: `icom` → `GenericIcomProfile(name, civ)`,
  `yaesu` → `GenericYaesuProfile`, `flrig` → no profile (flrig only). The wrong-radio warning is skipped for a match.
- Generic profiles use `generic_spec()` (MODE/FILTER/WIDTH/BKIN + filters, no menus). Yaesu-only features
  (`MD_CODES`, `po_string`, `tune_cmds`, CLAR/SHIFT reads, VFO scan, BKIN menu) are `_Absent` so `hasattr` is False and
  the app falls back to flrig. BKIN on generic Yaesu is OFF/ON (`BI`), RF gain through flrig.
- 14d: last line of the Rig drop-down = "Add my radio...". 14g: `offer_add_radio` on connect - unknown radio + Auto-detect
  opens the window once per flrig name (`add_radio_asked`), pre-filled; `civ_guess` / `CIV_DEFAULTS` (radios.py).

## 9. Settings file (`DATA_DIR/settings.json`)

`%APPDATA%\RigPanel` (Windows), `~/.config/rigpanel` (Linux). A missing key gets its default - never
change what an existing key means.

| Keys | Meaning |
|---|---|
| `host`, `port`, `rig`, `civ_addr`, `theme` | connection, look |
| `memories`, `band_memory`, `seeded` | stored frequencies, last freq per band+kind, radios already given starters |
| `mini_auto`, `mini_always`, `mini_pos`, `mini_scale` | Mini Meter |
| `lv_auto`, `lv_always`, `lv_pos`, `lv_scale`, `lv_smeter` (28a, default on) | Mini Levels |
| `ctrl_tap` (default on) | Ctrl tap brings RigPanel forward / back (11-09); **Settings ▾ switch** (11-14), off stops the watcher thread |
| `wf_*`, `audio_device` | waterfall |
| `ft891_macro_list`, `ic7300_macro_list` | Rig Settings per radio (`{name, group, show, items}`) |
| `levels_per_kind`, `levels_by_kind`, `ctl_by_kind`, `bw_by_kind` | Voice / Data / CW memory (keys voice, data, cw) |
| `rs_view`, `rs_section_FT-891`, `rs_section_IC-7300` | Edit Rig Settings view and last group |
| `vscan_pos`, `vscan_start` (here / edge), `vscan_end` (round / stop), `scan_class` (General / Extra) | VFO Scan window |
| `ft891_vfo_side` (A / B) | FT-891 VFO A / VFO B shown (the radio only swaps) |
| `rs_geom` (PC key) | Edit Rig Settings size and place |
| `scan_band`, `scan_pos`, `scan_presets`, `scan_preset`, `scan_step`, `scan_hold_s`, `scan_weak`, `scan_strong` | **unused** (old Voice Scan) - left in existing files, harmless |
| `rf_per_band`, `rf_by_band` (`{"rig:band": %}`) | RF gain per band |

Also in DATA_DIR: `my_default.json`, `settings_before_load.json`, `rigpanel_debug.log` (200 KB cap).

---

## 10. Testing

- **Practice radio** `mock_flrig.py --rig FT-891|IC-7300 --port N` with `--real891` (flrig 2.0.09 +
  FT-891: X garbling, silent sets with 6 s wait, no VFO select, per-VFO swap, 500 Hz reset),
  `--flrig212` (strict no-space hex in, `" %2X"`/FF out, no echo), `--ignore-rfgain`, `--slow-*`,
  `--cat-delay`. Knows FT-891 RM5 (operator's curve), AC, RL0; IC-7300 menu items, COMP/TBW/MONI/VOX,
  `04`/`06`/`1A 06` filter, `1C 01` tuner, `14 06` NR level. 27f-27o: FT-891 **really scans** on SC1/SC2
  (~22 kHz/s, runs out of the band like the real one, 5 s on its pretend stations when SQ0 < 40), knows
  `SQ0`, `SC`, `rig.cmd_string`, `main.get_version` (2.0.12 with `--flrig212`, else 2.0.09); with
  `--flrig212` the FT-891 **mixes up 25 % of answers** like real 2.0.12. Use `--cat-delay 0.15` to catch
  timing bugs the instant mock hides (the 27h edge-limit bug passed without it).
- **All tests**: `bash tests/run_all.sh python3.12` (needs Xvfb + openbox; the sandbox may need
  `apt install python3-tk openbox` and `pip install numpy pillow sounddevice` for the waterfall tests).
- **Names check** `tests/names_check.py` - no radio needed; run after moving code between modules.
- **Features** `tests/features.py <tmp> FT-891|IC-7300 <tag>` - SHIFT, CLAR/RIT, MUTE,
  PROC, All Menus (Voice Scan checks removed 27f). Practice radio knows SM0/15 02 with pretend stations, IS0, CF/RU/RD/RC/IF, PR0/PL,
  14 07, 21 00/01, all FT-891 menus and the IC-7300 SET menu with the operator's own values.
- **Regression** `tests/regress.py <tmp> FT-891|IC-7300 <tag>` under Xvfb + openbox, `HOME` with
  `.rigpanel.json` `{"port": 12401, "audio_device": "Demo (test tones)"}`. Expected **FT-891 22/22,
  IC-7300 18/18**. **27q run:** IC-7300 `--flrig212` 18/18; FT-891 `--real891` 19/22 - "FT-891 swap (SV)"
  still expected hidden VFO A/B buttons (test fixed after the run, 27k shows them), "Data macro
  confirmed" + "TUNE blocked on No Tuner" open since 27b; Tk callback error after the theme switch
  (`.!minilevels.!canvas`, `minis.py visible()`) open since 26k-27b. Features 27q: FT-891 16/16, IC-7300 13/13.
- **Radio scripts** (`tools/`, operator runs with RigPanel closed) - 1.4.1 added `ft891_menu_dump.py`,
  `ic7300_menu_dump.py`, `ic7300_scan_timing.py`, `ic7300_shift_check.py`/`_scale.py`,
  `ic7300_rit_check.py`/`_set.py`, 1.4.2 `ic7300_rf_watch.py` (prints RF gain / AGC every 0.5 s, read-only) (the FT-891 SHIFT / CLAR / PROC checks were paste blocks): `icom_check.py` (IC-7300 settings
  read-only), `icom_flrig_check.py`, `flrig212_check.py`, `flrig212_write_check.py` (toggles and puts
  back), `ft891_po_check.py`, plus the FT-891 set from 1.1 (`flrig_check`, `cat_variants`,
  `vfo_check`, `menu_check`, `direct_check`). **27c-27o:** `ic7300_signal_shape.py` (S-meter across one
  station, 100 Hz steps), `ic7300_band_read.py` (S-meter across a band, 1 kHz steps), `ft891_scan_check.py`
  (radio's own scan + squelch), `flrig_side_by_side.sh` (build another flrig beside the installed one),
  `ft891_212_timing.py` was a paste block (cat_string / cmd_string timings on 2.0.12). When a script must
  reach the operator's Linux PC, a `cat > ~/file.py <<'EOF'` paste block is the reliable route.
- **Linux package**: built and installed on the operator's Mint PC. PyInstaller needs
  `--hidden-import PIL._tkinter_finder` (the waterfall crashed the frozen app without it).

---

## 11. Open items

- **VFO Scan (FT-891) on air**: operator testing AGC (SLOW = catches more, may stop past; FAST = closer,
  misses more) and bandwidth (wide catches more, narrow stops closer); then maybe a "scan settings"
  switch (AGC + width set at ▲, put back at ■). If the radio keeps passing talking stations, a slower
  RigPanel-stepped scan using the radio's busy/squelch state (`BY;`, untested) is the next idea.
- **Radio power on/off** (operator's to-do, 2026-10-27): FT-891 `PS0;` / dummy + `PS1;`; IC-7300 `18 00`
  (on over USB unlikely); flrig's reaction when the radio goes off is the unknown; flrig 2.0.12 `rig.shutdown`.
- Backlog (not requested yet): IC-7300 radio's own scan (CI-V `0E` + squelch `14 03`); day/night RF gain
  per band.
- IC-7300 HPF/LPF and other two-part SET items are not in All Menus yet.

- ~~FT-891 on real flrig 2.0.12~~ - done 2026-10-27 (build 27o).
- **Pre-release test plan (before the GitHub release - after 1.4.2 is finished, added 2026-10-27):**
  1. **Older / newer flrig.** Distro packages are older than anything tested: Ubuntu 22.04 / Mint 21 =
     flrig **1.4.4**, Ubuntu 24.04 / Mint 22 = **2.0.04**, Ubuntu 26.04 / Mint 23 = **2.0.05** (tested so far:
     2.0.09, 2.0.10, 2.0.12). Raw CAT (`rig.cat_string`, no-space hex, §4.1) must be checked on them with the
     `tools/` scripts (`flrig212_check.py`, `ft891_scan_check.py`, `icom_flrig_check.py`) and the practice
     radio taught any new reply format. Also build the **newest** flrig to stay ahead of the next change.
     **Side-by-side build on the Mint PC** (keeps the installed 2.0.09): `tools/flrig_side_by_side.sh <ver>`
     builds from w1hkj.org (.org - .com redirects elsewhere) with FLTK 1.3 in `~/flrig-test`, **no
     `make install`**, own settings copy in `~/.flrig-test` (`--config-dir`); `... <ver> run` starts it
     (only one flrig at a time - one serial port). Based on the operator's "Flrig Linux Build Instructions"
     (which, for a full upgrade, removes the package first and does `sudo make install` to /usr/local/bin).
     Users are never asked to build flrig - this is for testing only.
  2. **Wayland.** Ubuntu 26.04 dropped the GNOME X11 session (Wayland only; X11 apps run in Xwayland);
     Fedora likewise; Mint 23 (≈ Christmas 2026, Ubuntu 26.04 base) is working on Wayland. Test the
     borderless always-on-top windows (Mini Meter, Mini Levels, VFO Scan: `overrideredirect`, `-topmost`,
     placement) on an Ubuntu 26.04 live USB; fall back to normal windows on Wayland if needed.
  3. **Linux packaging.** A PyInstaller build only runs on glibc as new as the build machine's, and is
     x86 only (many hams use a Raspberry Pi). Build the release on the oldest supported Ubuntu (GitHub
     Actions) and document the source route (`python3 -m rigpanel`, needs `python3-tk`), which runs anywhere.
  4. README: list the flrig versions RigPanel is tested with, and the flrig set-up (Poll boxes; Restore
     settings once confirmed - FLRIG_COMPATIBILITY.md).
- IC-7300: confirm DATA OFF MOD = MIC after the Voice button.
- GitHub: repository, LICENSE (GPL-3.0 via GitHub), Actions to build the installers, small unit tests
  (parsers, `menu_encode`, settings merge).
- Windows install sheet for 1.4 (the user guide covers installing).
- Ideas: IC-7300 Po from its own meter if a radio ever disagrees; per-band power memory.
