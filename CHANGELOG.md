# Changelog

## 1.4.4 - first release on GitHub (build 2026-11-16j)
RigPanel is a one-screen control panel that works through flrig, so your digital apps keep sharing the radio.
- **Tap Ctrl** alone in any program and RigPanel comes forward; tap again and it minimizes (can be turned off in Settings).
- **Default Settings** button under RECEIVE / FILTERS: your last settings stay, also after a restart. One click puts
  your Voice / Data / CW Rig Setting back. When the radio has drifted from it, the button turns amber and a note says
  what changed (for example "Changed from your Voice settings: NB, AGC").
- Full controls for the **Icom IC-7300** and **Yaesu FT-891**; any other radio flrig supports works for frequency,
  mode, bandwidth, VFOs, meters and levels. **Add my radio** (bottom of the Rig list) adds other Icom / Yaesu models,
  and opens by itself for a radio RigPanel doesn't know.
- **Voice | Data | CW** buttons, each with its own width, levels and Rig Setting; **BKIN OFF / SEMI / FULL** on both radios.
- **Rig Settings**: one-click groups of radio settings, including every menu item of both radios. Edit them with one
  **Save**: it's sent at once if that Rig Setting is in use.
- **IC-7300:** a width for each filter (Width FIL1 / FIL2 / FIL3), with every width step the radio offers.
- **Fast:** only the settings the radio doesn't already have are sent.
- 42 **starter frequencies** (160-10 m) on a new install, grouped by band; **Mini Meter** and **Mini Levels**; Dark / Light themes.
- Linux package runs on Mint 21 / Ubuntu 22.04 or newer; an AppImage is included too.
- Guides as PDF in `docs/`; problems go to the GitHub Issues page.

## 1.4.4 - builds 2026-11-16a to 16j (details)
- Fix (Linux): the FT-891 **PROC level menu closed at once** - 0-100 % was taller than the room below, so it opened
  over the mouse pointer and caught the button release. Long level menus now come in columns and open above the
  arrow when they don't fit below. The Default Settings note lists 4 items, then "and n more".
- **Default Settings note sooner after start:** receive controls read three at a time after connecting, the
  Voice / Data / CW Rig Settings' menu items first; known differences show at once, the rest as they're read
  (slow practice radio: 8.2 s -> 5.1 s). Values not read yet never count as "changed".
- **Faster Save / Default Settings / Voice-Data-CW:** only the settings the radio doesn't already have are sent;
  Width FIL1/2/3 only when a different width went to that filter since (on the slow practice radio 6 s -> under 1 s).
- **Default Settings** button under RECEIVE / FILTERS (when the mode in use has a Voice / Data / CW Rig Setting):
  puts that Rig Setting back at any time. Beside it, in amber, what the radio has changed from it ("Changed from
  your Voice settings: NB, NR"). Your last settings stay as they are, also after a restart - RigPanel never puts
  the Rig Setting back on its own.
- Edit Rig Settings: **one Save button** (Save & Apply removed). Saving the Rig Setting in use - Voice / Data / CW
  for the mode you're in, or one whose button is green - sends it to the radio at once; others are used the next
  time you click their button (the status line says which).
- Fix: a Rig Setting's NB / NR / Notch / Auto Notch / IP+ could be undone right after by "Separate settings for
  Voice, Data and CW" (it put back the filters last clicked on the main screen). Applying a Rig Setting now makes
  its values that kind's remembered filters.
- `build_windows.bat` uses `python` first and the `py` launcher only without it (py failed on a locked py.ini).
- **IC-7300 (and added Icom radios): a width for each filter.** Edit Rig Settings has Width FIL1 / FIL2 / FIL3
  instead of one Width. Applying sets each filter's width, then goes to the starting Filter (or back to the filter
  in use). Voice / Data / CW remember a width per filter too, so FIL1 / FIL2 / FIL3 never mix. An older Rig
  Setting's Width shows as the width of its starting filter (FIL1 if none) and works as before until saved.
- Edit Rig Settings: the Width list has the same steps as the main BANDWIDTH list (50 Hz to 500, 100 Hz to 3600)
  plus every width the radio offers in its current mode (was a short fixed list: 2700, 3000, 3200...).

## 1.4.3 - build 2026-11-14h (summary)
RigPanel is a one-screen control panel that works through flrig, so your digital apps keep sharing the radio.
- Full controls for the **Icom IC-7300** and **Yaesu FT-891**; any other radio flrig supports works for frequency,
  mode, bandwidth, VFOs, meters and levels. **Settings ▾ > Add my radio** adds other Icom / Yaesu models.
- **Voice | Data | CW** buttons, each with its own width, levels and Rig Setting; **BKIN OFF / SEMI / FULL** on both radios.
- **Rig Settings**: one-click groups of radio settings, including every menu item of both radios.
- 42 **starter frequencies** (160-10 m) on a new install; **Mini Meter** and **Mini Levels**; Dark / Light themes.
- **Tap Ctrl** in any program to bring RigPanel forward (can be turned off in Settings).
- Guides as PDF in `docs/`; problems go to the GitHub Issues page.

## 1.4.3 - builds 2026-11-14d to 14h
- **Starter frequencies (42, 160-10 m)** for a new install: voice start / end per band (3 kHz inside the edge;
  General and Extra starts both listed where they differ), W1AW CW, JS8 and FT8. Added radios get them too.
  Only when the PC has no stored frequencies yet.
- Stored-frequency drop-down: more than 20 -> this band's frequencies first, then a submenu per band.
- **First connect to a radio RigPanel doesn't know** (Rig on Auto-detect): Add my radio opens by itself, filled in
  from flrig's name - family from IC- / FT-, the model's usual CI-V address. Not forced: Close and it isn't shown
  again for that radio (`add_radio_asked`). Practice radio: `--xcvr IC-705` reports another name.
- Rig drop-down ends with **Add my radio...** (opens the same window as Settings ▾ > Add my radio).
- Edit Rig Settings: a Rig Setting named Voice / Data / CW shows "Runs from the Voice button on the MODE row"
  instead of Row / Show as a button. Tooltips on the mode row's Voice / Data / CW say what a click applies.
- Waterfall left out of the Hot Keys list and the README features (still being worked on; Shift+W / Ctrl+W
  still work). LEVELS tick box reads "Separate settings for Voice, Data and CW".
- **Compact View button removed** (Mini Meter + the Ctrl tap do the same; the pop-out waterfall is still Ctrl+W).

## 1.4.3 - build 2026-11-14c (any radio)
- **Settings ▾ > Add my radio**: name, the name flrig uses, family Icom (CI-V address) / Yaesu / Other. Added radios
  appear in the Rig list and are matched automatically. Icom and Yaesu get the controls most of the brand share
  (AGC, preamp, ATT, NB, NR, notch, BKIN, filter / width) and Rig Settings for mode, width, BKIN and filters;
  Other runs through flrig only. Saved as `custom_rigs` in settings. Tested on the practice radio as IC-705 and FT-710.
- README: "Works with your radio" and the two station types (built-in sound card / external Digirig).
- Practice radio answers Icom BKIN (`16 47`).

## 1.4.3 - build 2026-11-14b
- Unknown radio: the message says what works through flrig and to keep Rig on Auto-detect.

## 1.4.3 - build 2026-11-14a (GitHub preparation)
- **Settings ▾ > Tap Ctrl to bring RigPanel forward** (on / off); turning it off stops the keyboard watcher. Its X
  connections are closed when it stops (were left open on every theme switch).
- README rewritten for 1.4.3 (features, Linux install block, flrig Poll / Restore set-up, what the Ctrl tap reads and
  how to turn it off); **LICENSE** (GPL-3.0) added; `RigPanel.spec` (unused) removed; `linux_install.sh` no longer
  looks in `~/Radio/RigPanel`; PC names removed from the docs; unused imports in tests / tools.

## 1.4.3 - build 2026-11-09h
- Ctrl tap on Linux: back to **minimize** when RigPanel is in front (09g's "back to your program" left it on screen);
  the taskbar's active window (`_NET_ACTIVE_WINDOW`) stays as the test.

## 1.4.3 - build 2026-11-09g
- Ctrl tap on Linux: "active" is taken from the taskbar's `_NET_ACTIVE_WINDOW` (the keyboard focus lagged, so
  the first tap from the other monitor did nothing); going back re-activates the program you came from instead of
  minimizing (Mint often ignored the minimize). Windows unchanged.

## 1.4.3 - build 2026-11-09f
- Ctrl tap on Linux: RigPanel asks the window manager to activate it like a taskbar does (`_NET_ACTIVE_WINDOW`,
  source = pager), so Mint doesn't block it when the tap comes from a program on the other monitor.

## 1.4.3 - build 2026-11-09e
- Ctrl tap on Windows: no Alt key any more (a lone Alt put the window in menu mode - it came up blank). RigPanel
  joins the front program's input for a moment (AttachThreadInput), takes the front, lets go.

## 1.4.3 - build 2026-11-09d
- Ctrl tap on Windows: a background program isn't allowed to the front, so RigPanel restores itself and asks
  with a brief Alt press first (the usual way). One log line per tap (`Ctrl tap: state ..., active ...`).

## 1.4.3 - build 2026-11-09c
- Ctrl tap: **minimize / restore** (was lower / raise); "is RigPanel active" asked from the desktop (Windows
  GetForegroundWindow, X11 XGetInputFocus + parent chain, own connection); X errors can't close RigPanel.

## 1.4.3 - build 2026-11-09b
- **Tap Ctrl (on its own) from any program: RigPanel comes forward; tap again: it steps back.** Only a lone Ctrl
  press-and-release under ~0.45 s counts - Ctrl+C / Ctrl+V and a held Ctrl don't. Windows (GetAsyncKeyState) and
  Linux X11 (XQueryKeymap), read on its own thread, nothing is taken from other programs; does nothing on Wayland.
  Setting `ctrl_tap` (default on). Listed under Hot Keys.

## 1.4.3 - build 2026-11-09a
- **BKIN OFF / SEMI / FULL on the FT-891 too** (break-in `BI0;`/`BI1;` + menu 07-08 BK-IN TYPE), like the IC-7300.
- **BKIN as a Rig Settings item** on both radios (Common and All Menus, next to Mode / Width): OFF / SEMI / FULL,
  applied, read back, captured by Read from radio and used for the green "matches" check.

## 1.4.3 - build 2026-11-06l
- Clean-up, no change in behaviour: unused leftovers removed (`minis.py`), architecture doc renamed
  `RIGPANEL_ARCHITECTURE_Version_1_4_3.md` and brought up to date (Voice / Data / CW, BKIN, IC-7300 A⇄B and volume,
  FT-891 notes), stale handoff copy removed from the project folder.

## 1.4.3 - build 2026-11-06k
- **Fix: Voice stayed in CW on the IC-7300.** The Voice Rig Setting had Mode = CW (saved by Read from radio while in
  CW). Voice / Data / CW now ignore a saved Mode of the wrong kind and pick the right mode themselves.

## 1.4.3 - build 2026-11-06j
- **Quicker Voice / Data / CW:** menu items RigPanel read or set on the radio in the last 10 minutes (background
  checks keep them fresh) are not re-read when switching - only the ones that differ are touched. Rig Settings
  buttons and Save & Apply still check everything. On the slow practice radio: Data 5.4 s -> 2.5 s.

## 1.4.3 - build 2026-11-06i
- **Power is the operator's:** Voice / Data / CW skip the FT-891 power menus (16-01..16-04) even if their Rig Setting
  has them, so the RF Power slider (and its per-mode memory) always decides. Power removed from the built-in
  Voice / Data starting settings.

## 1.4.3 - build 2026-11-06h
- **Fix: Voice / Data / CW flipped back and forth.** A late reading of the old mode right after the switch was taken
  as a mode change and put the old kind's settings back; for ~5 s after a click such readings are now ignored, and
  the new width shows at once.

## 1.4.3 - build 2026-11-06g
- Voice / Data / CW switch the mode (and width) **at once**, then apply the rest of the Rig Setting in the
  background - the full Rig Setting took 17-20 s on the FT-891 before the mode changed.

## 1.4.3 - build 2026-11-06f
- FT-891: the CW button picks **CW-L** (was CW-U) when there is no CW Rig Setting; a CW Rig Setting's Mode decides otherwise.

## 1.4.3 - build 2026-11-06e
- Edit Rig Settings: the Width list now has CW widths (300-1400) as well as 1800-3200.

## 1.4.3 - build 2026-11-06d
- **Version 1.4.3** (the CW work, BKIN, MUTE / A⇄B fixes, width-memory fix and merged Voice / Data / CW buttons
  of builds 2026-11-05a .. 11-06c). Packages: RigPanel_Setup_1.4.3.exe, RigPanel_Ver_1.4.3_Linux.tar.gz.

## 1.4.2 - build 2026-11-06c
- **Voice / Data / CW buttons merged:** the mode row's Voice, Data and CW now run the Rig Setting of the same name
  (mode, width, menus...) when there is one, and those three no longer get their own button on the Rig Settings
  row (ANTENNA and other Rig Settings stay). The Rig Setting's width becomes that kind's width. Shift+V / Shift+D
  do the same. Without a Rig Setting of that name the mode row works as before.

## 1.4.2 - build 2026-11-06b
- **Fix: width memory mixed up between Voice / Data / CW.** On a mode change the width was put back before RigPanel
  had taken the new mode, so it was saved into the old kind's memory (CW 500 into Data, Data 3000 into CW) and
  checked against the old width list. The new mode is now taken first.

## 1.4.2 - build 2026-11-06a
- FT-891 **BKIN** OFF / ON (`BI0;` / `BI1;`, checked on the operator's radio with `ft891_bkin_check.py`), shown only
  in CW like the IC-7300's; set paired with its read (`BI;`).

## 1.4.2 - build 2026-11-05e
- Stored frequencies: **CW / RTTY in red** (drop-down and Edit frequency list), with "Red = CW" in the key.

## 1.4.2 - build 2026-11-05d
- IC-7300 **AF Volume / MUTE** by the radio's own command (CI-V `14 01`, read back), like RF gain: flrig's
  `rig.set_volume` didn't reach the radio in voice / CW on the operator's IC-7300 (MUTE showed MUTED, volume stayed).

## 1.4.2 - build 2026-11-05c
- IC-7300 **A⇄B** now exchanges the two VFOs (CI-V `07 B0`); flrig's `rig.swap` only selected VFO B.

## 1.4.2 - build 2026-11-05b
- Mode row **Voice | Data | CW**: CW lights in CW/RTTY; clicking it picks CW (IC-7300) / CW-U (FT-891) and
  puts back the CW memory.
- IC-7300 **BKIN** OFF / SEMI / FULL (CI-V `16 47`) in Receive / Filters, shown only in CW. FT-891: after a test.

## 1.4.2 - build 2026-11-05a
- **CW / RTTY get their own memory** (`memory_kind`): picking CW no longer lights Voice or puts back the Voice
  width and levels. Width (starts at 500 Hz), levels, receive filters and the per-band frequency are remembered
  for CW separately; a band click in CW stays in CW (first time: band edge + 25 kHz). Voice / Data unchanged.

## 1.4.2 - build 2026-11-03a
- Linux package renamed `RigPanel_Ver_1.4.2_Linux.tar.gz` (no build number in the file name; the build is in
  `VERSION` and the status bar). Install docs updated. flrig Poll / Restore screenshots in the install docs.

## 1.4.2 - build 2026-11-02a
- **Linux install, standard layout (same as JS8FastChat):** the package is now
  `RigPanel_Ver_<ver>_build_<build>_Linux.tar.gz` with top folder `RigPanel Ver <ver>`; it is unpacked into
  `~/Applications` and runs from there. `linux_install.sh` (in the package) makes the menu entry and desktop icon,
  offers libportaudio2 (waterfall), offers to remove older copies (other `RigPanel Ver *`, the old
  `~/.local/share/rigpanel` and `~/Radio/RigPanel`; never a newer version), `--remove`, `--yes`. The package
  carries `VERSION`, RigPanel-Linux-Install.docx and RigPanel_Quick_Start.docx. `update_linux.sh` installs the
  same way. Docs: RigPanel-Linux-Install.docx (replaces the one-page Quick Install), Building_RigPanel.docx and
  the user guide updated. No change to the program itself; Windows unchanged.

## 1.4.2 - build 2026-11-01a
- **Fix: switching theme froze RigPanel** (open since 27b as "Tk error after the theme switch"). The rebuild
  updated the MUTE pill of the old, already destroyed Mini Levels window; the error stopped the switch halfway
  (no new mini windows, radio panels not rebuilt, header "--", theme not saved) and every poll then failed on
  the old Mini Meter, so the window froze and wouldn't close. `apply_theme` now drops the old mini windows first.
- Docs: Building_RigPanel.docx, RigPanel_Quick_Start.docx, RigPanel-1.4.2-Linux-Quick-Install.docx; user guide
  section "Building RigPanel and sharing it".

## 1.4.2 - build 2026-10-30a
- **FT-891: Data width no longer left at 500 after flrig restarts.** Closing flrig always runs its
  `restore_xcvr_vals` (flrig source `support.cxx closeRig`, `restore_rig.cxx`): it selects VFO B, then A - on the
  FT-891 that is two swaps, and the firmware forces the DATA width to 500 on every swap. The width is only put
  back if flrig's Restore > Bandwidth is ticked, and then to the width flrig saw at start-up (often 500 again).
  RigPanel now puts the Data width back within 10 s of connecting, the same way it does after A/B.

## 1.4.2 - build 2026-10-29a
- `.gitattributes`: `.sh` / `.py` always LF, `.bat` / `.iss` always CRLF, images and archives binary
  (keeps the Linux scripts working when the repo is checked out on Windows). No code change.
- IC-7300 SWR checked (`swr_check.py`): at 1.5:1 flrig `get_SWR`, the radio's own meter (`15 12` = 0048)
  and RigPanel agree. A high-SWR reading is still to be compared.

## 1.4.2 - build 2026-10-28a
- **Mini Levels: S-METER row on top** (same bar and scale as the Mini Meter, follows the radio, dims on TX).
  Right-click > Show S-meter turns it off (window shrinks back); remembered in `lv_smeter` (default on).

## 1.4.2 - build 2026-10-27q
- VFO Scan: HEARD back to the exact stop frequency (0.1 kHz, as 27o) - the operator found whole-kHz
  rounding (27p) worked less well. The click-a-digit frequency display (27p) stays.

## 1.4.2 - build 2026-10-27p
- **VFO Scan:** HEARD lists whole kHz (the radio stops where its squelch opens - measured on 40 m: +4.2,
  +0.4, -1.7, -0.4 kHz from the voice, no fixed offset to correct), and the frequency in the window is
  now a click-a-digit display like the main one: click / scroll a digit to fine-tune; it stops the scan.

## 1.4.2 - build 2026-10-27o
- **FT-891 on flrig 2.0.12 (first real test, side-by-side build on the Mint PC):** every click took ~2 s.
  Measured (`ft891_212_timing.py`): reads take 0.07 s, but 2.0.12 sometimes hands back another answer
  (flrig's own poll's `MD0C;`, or the previous request's), and its `readResponse` loop then runs 1.2 s.
  Now, when flrig is 2.0.12 or newer: FT-891 **sets go with `rig.cmd_string`** (writes, waits for nothing -
  sets never answer), then the read-back on its own; **every FT-891 read checks the answer starts like the
  question** (`NB0;` -> `NB0...`) and asks again (up to 3 tries) if not. flrig 2.0.09 path unchanged.
  Practice radio `--flrig212` FT-891: mixes up 25 % of answers, knows `rig.cmd_string` and `main.get_version`.
- Fix (Linux, installed app): clicking the build text / "Open settings folder" didn't open the folder -
  the PyInstaller library path was passed on to the file manager.
- `tools/flrig_side_by_side.sh`: builds a newer flrig next to the installed one (own settings, desktop
  icon, no `make install`); tries w1hkj.org, then SourceForge.

## 1.4.2 - build 2026-10-27n
- **IC-7300 Rig Settings: Filter (FIL1/2/3)** - new item (Common view and the top of All Menus, between
  Mode and Width). Applying the Rig Setting picks that filter first, then sets the width (each filter
  keeps its own width). It's only the starting filter: a Rig Setting that has one stays green when you
  switch FIL1/2/3 for strong / weak signals (filter and width are then left out of the green check).
  Read all settings reads the filter too. Built-in defaults unchanged (Filter = leave it alone).

## 1.4.2 - build 2026-10-27m
- **Edit Rig Settings can be resized:** drag a corner - the All Menus table gets taller (and the window
  wider); it never shrinks below its opening size. Size and place are remembered (`rs_geom`, a PC key).
- Tooltips on every button and box of Edit Rig Settings (New, Clone, Delete, ▲▼, Name, Row, Show as a
  button, Read from radio, Read all / this group, Clear all, Save as new, Common, All Menus, Save,
  Save & Apply, Defaults, Close).

## 1.4.2 - build 2026-10-27l
- **Edit Rig Settings - Save & Apply** (green, next to Save): saves, then sends this Rig Setting to the
  radio at once (same as its button in the main window); "applied and confirmed ✓" (or what failed)
  shows in the editor as well as the status bar. Plain Save still only saves.

## 1.4.2 - build 2026-10-27k
- **FT-891 VFO row looks like the IC-7300's:** VFO A / VFO B buttons (lit = the one in use), A⇄B, A=B,
  Split. The FT-891 can't select a VFO over CAT, so VFO B / VFO A swap the registers (`SV;`) and RigPanel
  remembers which side you're on (`ft891_vfo_side`, kept across restarts); A⇄B swaps the contents and
  stays on the same side, like the IC-7300. Shift+A / Shift+B now pick A / B on both radios. Pressing the
  radio's own A/B key isn't seen over CAT - press VFO A or B once in RigPanel to line it up again.

## 1.4.2 - build 2026-10-27j
- Fix (Linux): drop-down and right-click menus (Settings ▾, Hot Keys, stored frequencies, level ▾,
  Mini Meter / Mini Levels) stayed open until you picked something. On X11 `tk_popup` returns at once and
  the following `grab_release` took away the menu's grab, so a click outside couldn't close it. One helper
  `popup_menu` (widgets.py) now keeps the grab on Linux (Windows unchanged); Escape also closes.

## 1.4.2 - build 2026-10-27i
- Fix: VFO Scan's segment limit never took hold on the real radio - the window cleared it while waiting
  for the radio to report "scanning" (a fraction of a second through flrig), so the scan ran out of 40 m
  and stops outside were listed. The limit now stays until a real stop. Practice radio: FT-891 scan runs
  out of the band like the real one; tested with `--cat-delay 0.15`.

## 1.4.2 - build 2026-10-27h
- **VFO Scan stays inside your voice segment:** LICENSE General / Extra (US band plan, `scan_class`) and
  AT THE END Go round / Stop (`vscan_end`). The FT-891's own scan runs right out of the band (it went
  from 20 m to 15.2 MHz), so RigPanel watches the frequency: past the segment end it starts again at the
  other end (or stops inside the segment). Overshoot is a few kHz (one poll); stops out there aren't
  listed. ▲/▼ refuse outside a voice segment (and 60 m); "From here" outside your segment begins at its
  edge. The segment is shown under the frequency.

## 1.4.2 - build 2026-10-27g
- **VFO Scan - HEARD list:** every station the radio stops on is listed (the frequency holds still for 1 s
  while the scan runs); stops within 2 kHz count as one station (x2, x3...). Low to high, scrolls (8 rows
  shown), "now" / "n min", ▲/▼ = which way the scan was going. Click = stop the scan and go there;
  right-click = remove; Clear. Kept while RigPanel runs. "START" row renamed **BEGIN AT**.
- `update_linux.sh`: one-step Linux update from the newest RigPanel_V*.zip in Downloads (the old
  instructions unpacked the stale 1.4 package - the build makes RigPanel-1.4.2-linux.tar.gz).
- Practice radio FT-891 really scans on SC1/SC2 (~22 kHz/s, 5 s on its pretend stations).

## 1.4.2 - build 2026-10-27f
- **FT-891 VFO Scan** (gold **Scan** button in the header, FT-891 only): a floating HUD window that runs
  the radio's own scan - ▼ Down / ■ Stop / ▲ Up (`SC2;` / `SC0;` / `SC1;`), **Squelch** 0-100 (`SQ0nnn;`,
  handy since the knob is RF gain with 05-05 = RF), **On a signal** Wait 5 s / Stay until it ends (menu
  05-16), **Start** from here or at the band edge (bottom of the voice segment for ▲, top for ▼). Shows
  SCANNING / STOPPED and the frequency as the radio moves. EXIT stops the scan. New settings `vscan_pos`,
  `vscan_start`. Practice radio knows `SC` and `SQ0`.
- **Voice Scan removed** (both radios): the Scan button, the Voice Scan window (`scan.py`), the worker's
  scan engine, the Shift+S/H/R/X hot keys and the S-meter reads that only the scan used. Tested on the
  IC-7300 2026-10-27: stepping through flrig sees only short S-meter snapshots, so stations were missed
  (AGC SLOW helped), and finding the right SSB dial spot from S-meter edges was off by up to 2 kHz on a
  busy band. The radio's own scan is used instead (below). Old `scan_*`
  settings are left in settings.json, unused. The US voice band plan stays in `tables.py`.
- Diagnostic tools kept: `ic7300_signal_shape.py`, `ic7300_band_read.py` (S-meter across a station /
  a band), `ft891_scan_check.py` (FT-891 own scan `SC`, squelch `SQ0`).

## 1.4.2 - build 2026-10-27e
- **Voice Scan Default preset: AGC SLOW** (was FAST) and **weak from S2** (was S3); S1 and S2 added to the
  weak choices. Band reads on the IC-7300 (`tools/ic7300_band_read.py`): with AGC FAST the S-meter
  dropped to 0 between words, so stations showed only as single spikes and the scan walked past them;
  with SLOW every station read as a smooth hump on nearly every look. Stations seen on the scope read
  S0-S2, below the old S3 limit.

## 1.4.2 - build 2026-10-27d
- **Voice Scan - Lock in:** clicking a FOUND signal (list or band map), and every hold on a strong
  signal, now finds the right dial spot: the dial walks out both ways (500 Hz, then 100 Hz steps) until
  the station is gone, and goes to the middle between the two edges (an SSB station is heard about one
  filter width either side of its right spot - measured on the IC-7300). About 5-6 s; the FOUND entry
  moves to the locked frequency. Pressing anything meanwhile stops it.

## 1.4.2 - build 2026-10-27c
- **Voice Scan - One pass** (now the Default preset's band-edge choice; Bounce and Wrap still there):
  ▶ / Shift+S start at the **beginning of the band** - LSB scans up from the bottom, USB down from the
  top - and stop at the other end. Press ▶ again for another pass; on a 2.5 kHz grid the next pass lands
  half a step between the earlier steps. Shift+R resumes from where you stopped; ⏮ ⏭ scan from here.
- Tool: `tools/ic7300_signal_shape.py` - S-meter across one station in 100 Hz steps (for lock-in).

## 1.4.2 - 2026-10-26/27 (builds 2026-10-26g to 2026-10-27b)
- **Voice Scan - Scan Settings presets:** built-in **Default** (P.AMP/IPO off, ATT off, AGC FAST, RF gain
  as is, 2.5 kHz, hold 5 s, S3/S7, Bounce) and **Current settings** (changes nothing); save your own,
  pick one from the gold ⚙ menu. **Copy from radio** fills a preset from the radio now. Applied at ▶,
  everything put back at stop; anything you change by hand during a scan is kept.
- **Bounce at band edge:** the scan turns round at the edge instead of jumping back; the return pass
  visits the half-steps (e.g. 1.25 kHz between 2.5 kHz steps). Wrap still available.
- **RF gain per band** (LEVELS tick box, on by default): each band keeps the RF gain you last used there;
  changing band (BAND buttons, Voice Scan, the radio's knob) saves the old band's and puts back the new band's.
- Voice Scan leaves RF gain alone (option: "RF gain to max while scanning"); a change during a scan is kept.
- MUTE in the Mini Levels window. flrig 2.0.12 hiding an RF gain read-back (32-39 %) no longer counts as failed.
- **New look:** every button is a raised 3D key (solid colours, pressed in when on). Titles BAND / MODE /
  BANDWIDTH / FILTER / SHIFT / RIG SETTINGS / ANTENNA / THEME / METERS / LEVELS / RECEIVE / FILTERS in bold
  capitals, dark red (bright red in the Dark theme). VFO B and RIT/CLAR in gold, larger. Profile larger, green.
  FLRIG shows Connected / Waiting / Offline. Menus in bold. Stored-frequency legend: Green = Digital, Blue = Voice.
- **Layout:** Tuner On / Tuner Off on the BAND row (far right); MODE row spread out; kHz box removed -
  **Shift+G** opens a Go to kHz box; RIT/CLAR moved to the right; Settings - THEME - Hot Keys evenly spaced,
  Settings and Hot Keys blue.
- Edit Rig Settings: one-click Delete; red hint, bold status line. IC-7300 RIT shown in kHz like the radio.
- Fix: after a theme change the FT-891 showed VFO A / VFO B buttons.
- Code tidy-up, no change in behaviour: radio tables (both menus, defaults, band plan) moved to
  `rigpanel/tables.py`; CLAR/RIT, SHIFT, MUTE and the Voice Scan hooks moved from `app.py` to
  `rigpanel/extras.py`; the worker's background reads of SHIFT / CLAR share one table.
- New tests: `tests/names_check.py` (no name defined in two modules, no module using a later one's name),
  `tests/features.py` (Voice Scan, SHIFT, CLAR/RIT, MUTE, PROC, All Menus on both radios),
  `tests/run_all.sh` (everything, both radios).

## 1.4.1 - 2026-10-25 / 26 (builds 2026-10-25b to 2026-10-26f)
- **Voice Scan** (gold Scan button, Shift+S/H/R/X), both radios: steps through the US voice segment of a
  band (General or Extra), reads the radio's own S-meter, lists signals strongest first (weak magenta,
  strong green), band map, hold on signal, skip, click to tune, TUNE. RF gain max and AGC FAST while
  scanning, put back after; stops at once if anything transmits.
- **Edit Rig Settings: Common | All Menus** for both radios - every FT-891 menu (155) and IC-7300 SET menu
  item (141) by group, "Radio now" column read from the radio, click to copy. Save as new.
- **Passband SHIFT** (voice): FT-891 IF SHIFT (20 Hz steps, +-1200), IC-7300 FILTER SHIFT (25 Hz, +-625).
- **CLAR** (FT-891) / **RIT** (IC-7300): on/off, 10 Hz steps, clear.
- **FT-891 PROC** (speech processor) with level menu; PROC and PROC level in Rig Settings.
- **MUTE** beside AF Volume (Shift+M) - doesn't change your saved voice/data volume.
- Fixes: mouse wheel no longer changes the Rig or Theme box; main S-meter text (showed S9+110);
  "Read from radio" also refreshes the group on screen.

## 1.4 - 2026-10-24 (build 2026-10-24d)
- **Works with flrig 2.0.12** (and older). flrig 2.0.12 reads raw CAT strings as hex with exactly
  3 characters per byte, so every raw command is now sent as `xFExFEx94...` (no spaces) - IC-7300
  CI-V and FT-891 text commands alike. Its replies (`' FF FF 16 22  1 FF'`, bytes above 0x7F shown as FF)
  are decoded; a value flrig hides that way is sent and logged as "sent", not reported as failed.
- Rig Settings row (was Macros), "Edit Rig Settings", tooltips "Apply ... Settings"; FT-891 "Data" (was Digital).
- Hot Keys button (replaces the Waterfall button): Shift+V/D/E/A/B/Z/L/W. Mini Levels is now Shift+L.
- Closing RigPanel finishes the current flrig request and closes the connection cleanly.
- Practice radio: `mock_flrig.py --flrig212` behaves like flrig 2.0.12's raw CAT.
- New radio checks in `tools/`: `icom_flrig_check.py`, `flrig212_check.py`, `flrig212_write_check.py`.

## 1.3 - 2026-10-23 (build 2026-10-23m)
- Code split from one file into the `rigpanel` package (no change in behaviour). Start with
  `python -m rigpanel`, `run_rigpanel.py`, `RigPanel.bat` or `rigpanel.sh`.
- The flrig worker now owns all of its state (profile and macro list changes go through its job queue);
  each radio profile carries its own macro tables.
- Neutral built-in defaults; a full working station is in `examples/KW3KW_settings.json`.
- Windows installer (`build_windows.bat` + Inno Setup) and Linux package (`build_linux.sh`).
- Folders: `docs/` guides, `tools/` radio diagnostic scripts, `examples/` settings.

## 1.1 - builds 2026-10-23c to 2026-10-23l
- New look: dark display panels for frequency, meters and levels; app icon in the header.
- Mini meter: new style, corner resize, remembers size; hot key Shift+Z.
- Mini Levels window (Shift+A) with "Pop up when receiving".
- Coloured level bars; green RX badge; S-meter yellow past S9, red past +20.
- IC-7300 macros (CI-V `1A 05` menu items, COMP, TBW, AGC...) in the same Macro Builder.
- IC-7300 FIL1/2/3 and Tuner on/off buttons.
- Settings menu: save/load settings files (keeps each PC's sound card, flrig address and window places),
  "Save as my default" / "Return to my default".
- Starting stored frequencies per radio; stored frequencies work across radios (USB-D <-> DATA-U).

## 1.1 - up to build 2026-10-23b
- IC-7300 and FT-891 through flrig; FT-891 macros; voice/data memory; waterfall; Linux support.
