# 1.4.1 feature tests: python tests/features.py <tmpdir> FT-891|IC-7300 <tag>
# Same set-up as regress.py: mock_flrig.py on port 12401, HOME holding .rigpanel.json
# {"port": 12401, "audio_device": "Demo (test tones)"}, under Xvfb + a window manager.
# Covers what 1.4.1 added: passband SHIFT, CLAR/RIT, MUTE, FT-891 PROC, All Menus.
import os
import sys
import traceback
import xmlrpc.client as x

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import tkinter as tk  # noqa: E402
import rigpanel as rp  # noqa: E402

S, rig, tag = sys.argv[1], sys.argv[2], sys.argv[3]
FT = rig == "FT-891"
radio = x.ServerProxy("http://127.0.0.1:12401")
root = tk.Tk()
rp.pick_fonts(root)
root.geometry("1100x760+0+0")
app = rp.App(root)
errors, res, steps = [], [], []
root.report_callback_exception = lambda e, v, tb: errors.append("".join(traceback.format_exception(e, v, tb))[-400:])


def ok(name, cond, info=""):
    res.append(("PASS" if cond else "FAIL", name, info))


def step(f, wait=1800):
    steps.append((f, wait))


def cat(s):
    """Raw CAT to the practice radio, as RigPanel would send it; answer as text."""
    if FT:
        return rp.hex_reply_text(radio.rig.cat_string("".join(f"x{b:02X}" for b in s.encode())))
    return str(radio.rig.cat_string(s))


def prof():
    return app.profile


def run():
    if not steps:
        for r in res:
            print(f"  {r[0]}  {r[1]} {r[2]}")
        print(f"  {'PASS' if not errors else 'FAIL'}  no Tk callback errors {errors[:2]}")
        print(f"  == {tag} {rig} features: {sum(r[0] == 'PASS' for r in res)}/{len(res)} passed")
        os._exit(0)
    f, w = steps.pop(0)
    try:
        f()
    except Exception:
        errors.append(traceback.format_exc()[-400:])
    root.after(w, run)


step(lambda: ok("connects", app.connected and app.xcvr == rig, app.xcvr), 10)

# --- passband SHIFT (voice only)
step(lambda: app.set_mode("LSB"), 2500)
step(lambda: ok("SHIFT shown in LSB", app.shift_f.winfo_ismapped()), 10)
step(lambda: [app.shift_step(-1) for _ in range(3)], 2500)
step(lambda: ok("SHIFT 3 steps left reaches the radio",
                app.shift_hz == -3 * prof().SHIFT_STEP
                and prof().parse_shift(cat(prof().shift_read_string()), "LSB") == -3 * prof().SHIFT_STEP,
                f"ui={app.shift_hz}"), 10)
step(lambda: app.shift_to(0), 2000)
step(lambda: ok("SHIFT center", prof().parse_shift(cat(prof().shift_read_string()), "LSB") == 0), 10)

# --- CLAR / RIT
step(lambda: [app.clar_step(1) for _ in range(3)], 2500)
step(lambda: ok(f"{prof().CLAR_NAME} +30 Hz switches it on",
                prof().parse_clar([cat(s) for s in prof().clar_read_strings()]) == (True, 30)), 10)
step(lambda: [app.clar_step(-1) for _ in range(8)], 2500)
step(lambda: ok(f"{prof().CLAR_NAME} -50 Hz", prof().parse_clar([cat(s) for s in prof().clar_read_strings()])[1] == -50), 10)
step(lambda: (app.clar_set(0), app.clar_toggle()), 2500)
step(lambda: ok(f"{prof().CLAR_NAME} clear + off", prof().parse_clar([cat(s) for s in prof().clar_read_strings()]) == (False, 0)), 10)
step(lambda: None, 5000)
step(lambda: ok(f"{prof().CLAR_NAME} stays off after background reads", not app.clar_on and app.clar_hz == 0), 10)

# --- MUTE
step(lambda: (app.sliders["volume"].set(30), app.slider_moved("volume", "rig.set_volume", 30)), 2500)
step(lambda: app.do_hotkey("mute"), 2500)
step(lambda: ok("MUTE (Shift+M) sets volume 0", int(radio.rig.get_volume()) == 0 and app.mute_btn.cget("text") == "MUTED"), 10)
step(lambda: app.toggle_mute(), 3000)
step(lambda: ok("unmute puts the level back", int(radio.rig.get_volume()) == 30), 10)
step(lambda: ok("mute doesn't change the saved voice level",
                app.cfg.get("levels_by_kind", {}).get("voice", {}).get("volume") == 30), 10)

# --- FT-891 PROC
if FT:
    ctl = lambda: next(c for c in prof().controls if c.key == "proc")    # noqa: E731
    step(lambda: app.set_control(ctl(), 0), 2500)
    step(lambda: ok("PROC off", "PR00" in cat("PR0;")), 10)
    step(lambda: app.worker.submit(lambda w: w.ctl_level(ctl(), 20)), 2500)
    step(lambda: ok("PROC level 20", "PL020" in cat("PL;")), 10)

    def proc_macro():
        lst = app.macro_list()
        lst.append({"name": "VoiceProc", "group": "Operating", "show": True, "items": {"PROC": "ON", "PROCLV": "35"}})
        app.save_macro_list(lst)
        app.run_macro("VoiceProc")
    step(proc_macro, 5000)
    step(lambda: ok("Rig Setting with PROC ON / level 35", "PR01" in cat("PR0;") and "PL035" in cat("PL;")), 10)

# --- All Menus (Edit Rig Settings)
SEC, CODE, WANT = ("16", "1604", "85") if FT else ("CONN", "0065", "40")
step(lambda: (app.open_macro_editor(), app.macro_win.set_view("all"), app.macro_win.show_section(SEC)), 4500)
step(lambda: ok("All Menus reads a group from the radio", app.macro_win.radio_lbls[CODE].cget("text") == WANT,
                app.macro_win.radio_lbls[CODE].cget("text")), 10)
step(lambda: app.macro_win._copy_radio(CODE), 300)
step(lambda: ok("click a green value copies it", app.macro_win.cells[CODE].get() == WANT), 10)
step(lambda: (app.macro_win.set_view("common"), app.macro_win.close(), app.macro_win.close()), 500)

root.after(3000, run)
root.mainloop()
