# Full regression: python tests/regress.py <tmpdir> FT-891|IC-7300 <tag>  (mock_flrig.py on port 12401, HOME with .rigpanel.json port 12401)
# Full feature regression against mock_flrig, any Python/Tk, under a window manager.
import sys, os, subprocess, xmlrpc.client as x, traceback
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import tkinter as tk, rigpanel as rp
S, rig, tag = sys.argv[1], sys.argv[2], sys.argv[3]
radio = x.ServerProxy("http://127.0.0.1:12401")
root = tk.Tk(); rp.pick_fonts(root); root.geometry("1020x700+0+0"); app = rp.App(root)
errors = []
def report_callback_exception(exc, val, tb):
    errors.append("".join(traceback.format_exception(exc, val, tb))[-400:])
root.report_callback_exception = report_callback_exception
res = []
def ok(name, cond, info=""): res.append(("PASS" if cond else "FAIL", name, info))
steps = []
def step(f, wait=1800): steps.append((f, wait))
def run():
    if not steps:
        for r in res: print(f"  {r[0]}  {r[1]} {r[2]}")
        print(f"  {'PASS' if not errors else 'FAIL'}  no Tk callback errors {errors[:2]}")
        print(f"  == {tag} {rig}: {sum(r[0]=='PASS' for r in res)}/{len(res)} passed"); os._exit(0)
    f, w = steps.pop(0)
    try: f()
    except Exception as e: errors.append(f"{f.__name__ if hasattr(f,'__name__') else f}: {e!r}")
    root.after(w, run)
def digits():
    fd = app.freq_disp
    for x0, x1, p in fd.cells:
        if p == 1000:
            fd.event_generate("<ButtonPress-1>", x=int((x0+x1)/2), y=5); fd.event_generate("<ButtonRelease-1>", x=int((x0+x1)/2), y=5)
    fd.event_generate("<Button-4>", x=fd.cells[3][0]+5, y=5)      # Linux wheel up on the 10 kHz digit
step(lambda: ok("connects + detects rig", app.connected and app.xcvr == rig, app.xcvr), 10)
step(digits)
step(lambda: ok("click digit + Linux wheel tune", radio.rig.get_vfo() == "14085000", radio.rig.get_vfo()), 10)
step(lambda: app.pick_band(app.BANDS_40 if hasattr(app, "BANDS_40") else rp.BANDS[3]))
step(lambda: ok("band button", radio.rig.get_vfo().startswith("7"), radio.rig.get_vfo()), 10)
def lvl():
    b = app.sliders["power"]; xx = b.x0 + int((b.x1 - b.x0) * 0.6)
    b.event_generate("<ButtonPress-1>", x=xx, y=10); b.event_generate("<ButtonRelease-1>", x=xx, y=10)
    v = app.sliders["volume"]; v.event_generate("<Button-4>", x=10, y=10)
step(lvl)
step(lambda: ok("level drag + Linux wheel", radio.rig.get_power() == 60 and app.sliders["volume"].get() == 31,
                f"power={radio.rig.get_power()} vol={app.sliders['volume'].get()}"), 10)
def rx():
    ctl = next(c for c in app.profile.controls if c.key == "nb"); app.set_control(ctl, 1)
step(rx)
step(lambda: ok("receive control set + read back", app.ctl_values.get("nb") == 1), 10)
if rig == "FT-891":   # no VFO select over CAT: VFO A / VFO B buttons shown since 27k, done by swapping (SV)
    step(lambda: (app.tune_to(7_076_000)), 1500)
    step(lambda: app.vfo_action("swap"), 1500)
    step(lambda: ok("FT-891 swap (SV)", radio.rig.get_vfoB() == "7076000" and bool(app.vfo_btns["B"].winfo_manager()),
                    f"B={radio.rig.get_vfoB()} other shown={app.other_hz}"), 10)
    step(lambda: app.vfo_action("swap"), 1500)
    step(lambda: (app.vfo_action("copy"), app.vfo_action("split")), 2000)
    step(lambda: ok("FT-891 copy (AB) + split, other VFO read from radio",
                    radio.rig.get_vfoB() == "7076000" and radio.rig.get_split() == 1 and app.other_hz == 7076000,
                    f"B={radio.rig.get_vfoB()} other={app.other_hz}"), 10)
else:
  step(lambda: (app.vfo_action("B"), app.tune_to(7_076_000)), 1500)
  step(lambda: (app.vfo_action("A"), app.vfo_action("split")), 2000)
  step(lambda: ok("VFO B + split", radio.rig.get_vfoB() == "7076000" and radio.rig.get_split() == 1 and radio.rig.get_AB() == "A",
                f"B={radio.rig.get_vfoB()} split={radio.rig.get_split()} AB={radio.rig.get_AB()}"), 10)
step(lambda: (app.vfo_action("split"), app.mini.set_options(auto=True, always=False), app.tune()), 1500)
step(lambda: ok("TUNE -> TX meters + mini pops up", app.ptt and app.mini.visible() and app.m_po.last[1].endswith("W"), app.m_po.last[1]), 10)
def drag():
    m = app.mini; x0, y0 = m.winfo_rootx() + 120, m.winfo_rooty() + 60
    m.cv.event_generate("<ButtonPress-1>", rootx=x0, rooty=y0, x=120, y=60)
    m.cv.event_generate("<B1-Motion>", rootx=x0 - 300, rooty=y0 + 200, x=120, y=60)
    m.cv.event_generate("<ButtonRelease-1>", rootx=x0 - 300, rooty=y0 + 200, x=120, y=60)
def resize():
    m = app.mini; w0 = m.winfo_width(); x0, y0 = m.winfo_rootx() + w0 - 3, m.winfo_rooty() + m.winfo_height() - 3
    m.cv.event_generate("<ButtonPress-1>", rootx=x0, rooty=y0, x=w0 - 3, y=m.winfo_height() - 3)
    m.cv.event_generate("<B1-Motion>", rootx=x0 + 170, rooty=y0 + 10, x=w0 - 3, y=m.winfo_height() - 3)
    m.cv.event_generate("<ButtonRelease-1>", rootx=x0 + 170, rooty=y0 + 10, x=w0 - 3, y=m.winfo_height() - 3)
step(resize, 800)
step(lambda: ok("mini meter corner resize saves size", app.cfg.get("mini_scale", 1) > 1.3 and app.mini.winfo_width() > 450,
                f"scale={app.cfg.get('mini_scale')} w={app.mini.winfo_width()}"), 10)
step(drag, 800)
step(lambda: ok("mini meter drag saves position", bool(app.cfg.get("mini_pos")), str(app.cfg.get("mini_pos"))), 7000)
step(lambda: ok("mini meter auto-hides after TX", not app.mini.visible()), 10)
step(lambda: root.event_generate("<Shift-Z>"), 600)
step(lambda: ok("Shift+Z opens mini meter", app.mini.visible()), 10)
if app.wf.ok:   # waterfall (unfinished) only when its optional packages load
    step(lambda: (setattr(app, "h_before_wf", root.winfo_height()), root.event_generate("<Shift-Z>"), app.toggle_waterfall()), 1500)
    step(lambda: ok("waterfall on (demo audio)", app.wf_shown and app.wf.running and root.winfo_height() > 750, f"h={root.winfo_height()}"), 10)
    step(lambda: (app.toggle_float()), 1200)
    step(lambda: ok("pop-out waterfall", app._float_visible() and app.float_wf.W > 300), 10)
    step(lambda: (app.toggle_float(), app.toggle_waterfall()), 1200)
    step(lambda: ok("waterfall off closes audio + shrinks", not app.wf.running and root.winfo_height() <= app.h_before_wf + 4, f"h={root.winfo_height()} before={app.h_before_wf}"), 10)
else:
    step(lambda: root.event_generate("<Shift-Z>"), 600)   # close the mini meter as the waterfall steps did
step(lambda: app.enter_compact(), 1500)
step(lambda: ok("Compact View minimises", root.state() == "iconic" and app.mini.visible(), root.state()), 10)
step(lambda: app.mini.full_btn.command(), 1500)
step(lambda: ok("Full Panel restores", root.state() == "normal"), 10)
step(lambda: app.apply_theme("Light"), 1500)
step(lambda: ok("theme switch keeps state", app.theme == "Light" and app.ctl_values.get("nb") == 1 and app.freq_disp.hz is not None), 10)
step(lambda: app.apply_theme("Dark"), 1200)
def flist_open():
    app.mem_start = {m["hz"] for m in app._memories()}     # starting list (built-in for this radio)
    app.open_freq_list(); root.update()
def flist():                                                # window is on screen now (slow screens need the wait)
    w = app.freq_win; w.freq_e.focus_force(); root.update()
    for f in ("7071", "3.575"):
        w.freq_e.insert(0, f); w.add(); root.update()      # = Return (GitHub's virtual screen drops generated keys)
step(flist_open, 1500)
step(flist, 1500)
step(lambda: (ok("frequency list add", {m["hz"] for m in app._memories()} - app.mem_start == {7071000, 3575000},
                 str(sorted({m["hz"] for m in app._memories()} - app.mem_start))), app.freq_win.destroy()), 10)
if rig == "FT-891":
    step(lambda: app.run_macro("Data"), 3500)
    step(lambda: ok("FT-891 Data macro confirmed", "confirmed" in app.log_lbl.cget("text"), app.log_lbl.cget("text")[10:]), 10)   # Data has no Rig Settings button since 11-06c
    step(lambda: app.run_macro("No Tuner"), 2000)
    def notune():
        app.tune(); ok("TUNE blocked on No Tuner", "TUNER SELECT is OFF" in app.log_lbl.cget("text"))
    step(notune, 10)
    def builder():
        app.open_macro_editor(); w = app.macro_win; w.clone(); w.name_var.set("Voice - DX"); w.save(); w.destroy()
    step(builder, 800)
    step(lambda: ok("macro builder clone + save", "Voice - DX" in app.macro_btns or "Digital copy" in app.macro_btns, str(list(app.macro_btns))), 10)
def shot():
    root.update(); subprocess.run(["import", "-window", "root", f"{S}/linux_{tag}_{rig}.png"])
step(shot, 10)
root.after(3500, run); root.mainloop()
