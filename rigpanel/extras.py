"""Main-window extras added in 1.4.1: CLAR / RIT, passband SHIFT, MUTE; FT-891 VFO Scan hooks (27f).
App inherits these (class App(Extras)); they use the App's own widgets, worker and helpers
(self._need_link, self._touch, self._recent, self.log, ...), which App defines."""
import sys
import os
import time
import threading
from .core import *  # noqa: F401,F403
from .tables import *  # noqa: F401,F403
from .radios import *  # noqa: F401,F403
from .worker import *  # noqa: F401,F403
from .widgets import *  # noqa: F401,F403
from .waterfall import *  # noqa: F401,F403
from .freqlist import *  # noqa: F401,F403
from .minis import *  # noqa: F401,F403
from .vscan import *  # noqa: F401,F403


class CtrlTap:
    """A quick tap of Ctrl on its own, from any program, brings RigPanel forward (again = back).
    Reads the keyboard state every 30 ms: Windows GetAsyncKeyState, Linux X11 XQueryKeymap (no grab, nothing
    is taken from other programs). Not available on Wayland - then it simply does nothing. (11-09b)"""
    TAP_S = 0.45

    def __init__(self):
        self.ok, self.down, self.alone, self.t0 = False, False, False, 0.0
        try:
            if sys.platform == "win32":
                import ctypes
                self.u32 = ctypes.windll.user32
                self.ctrl = (0x11, 0xA2, 0xA3)
                self.skip = set(self.ctrl) | {0x10, 0x12, 0xA0, 0xA1, 0xA4, 0xA5}   # shift / alt / ctrl codes
                self.ok = True
            elif os.environ.get("DISPLAY") and not os.environ.get("WAYLAND_DISPLAY"):
                import ctypes, ctypes.util
                x = ctypes.cdll.LoadLibrary(ctypes.util.find_library("X11") or "libX11.so.6")
                x.XOpenDisplay.restype = ctypes.c_void_p
                x.XQueryKeymap.argtypes = [ctypes.c_void_p, ctypes.c_char_p]
                x.XKeysymToKeycode.argtypes = [ctypes.c_void_p, ctypes.c_ulong]
                self._xerr = ctypes.CFUNCTYPE(ctypes.c_int, ctypes.c_void_p, ctypes.c_void_p)(lambda d, e: 0)
                x.XSetErrorHandler(self._xerr)        # an X error must never close RigPanel (default handler exits)
                self.dpy = x.XOpenDisplay(None)
                if self.dpy:
                    self.x, self.buf = x, ctypes.create_string_buffer(32)
                    self.ctrl = {x.XKeysymToKeycode(self.dpy, k) for k in (0xFFE3, 0xFFE4)} - {0}
                    self.ok = bool(self.ctrl)
        except Exception as e:                  # never let this stop RigPanel
            debug_log(f"Ctrl tap not available: {e}")
            self.ok = False

    def _keys(self):
        """(ctrl down, any other key down)"""
        if sys.platform == "win32":
            st = lambda vk: self.u32.GetAsyncKeyState(vk) & 0x8000
            ctrl = any(st(k) for k in self.ctrl)
            other = any(st(k) for k in range(0x08, 0xFF) if k not in self.skip)
            return ctrl, other
        self.x.XQueryKeymap(self.dpy, self.buf)
        raw = self.buf.raw
        down = {i * 8 + b for i, byte in enumerate(raw) for b in range(8) if byte >> b & 1}
        return bool(down & self.ctrl), bool(down - self.ctrl)

    def close(self, which="dpy"):
        """Close one X connection (each thread closes its own)."""
        d = getattr(self, which, None)
        if d and sys.platform != "win32":
            try:
                self.x.XCloseDisplay(d)
            except Exception:
                pass
        setattr(self, which, None)

    def is_active(self, root):
        """Is RigPanel's main window the one the desktop has active? (None = can't tell)"""
        try:
            frame = int(root.wm_frame(), 16)
            if sys.platform == "win32":
                return self.u32.GetForegroundWindow() == frame
            import ctypes
            win, rev = ctypes.c_ulong(0), ctypes.c_int(0)
            self.x.XGetInputFocus.argtypes = [ctypes.c_void_p, ctypes.POINTER(ctypes.c_ulong), ctypes.POINTER(ctypes.c_int)]
            if not getattr(self, "dpy2", None):        # own connection: the key watcher thread uses self.dpy
                self.dpy2 = self.x.XOpenDisplay(None)
            dpy = self.dpy2
            self.x.XGetInputFocus(dpy, ctypes.byref(win), ctypes.byref(rev))
            q = self.x.XQueryTree
            q.argtypes = [ctypes.c_void_p, ctypes.c_ulong, ctypes.POINTER(ctypes.c_ulong), ctypes.POINTER(ctypes.c_ulong),
                          ctypes.POINTER(ctypes.c_void_p), ctypes.POINTER(ctypes.c_uint)]

            def chain(w):                              # w and its parents up to (not incl.) the screen's root
                out = []
                for _ in range(12):
                    rt, par, kids, n = ctypes.c_ulong(0), ctypes.c_ulong(0), ctypes.c_void_p(), ctypes.c_uint(0)
                    if not w or not q(dpy, w, ctypes.byref(rt), ctypes.byref(par), ctypes.byref(kids), ctypes.byref(n)):
                        break
                    if kids:
                        self.x.XFree(kids)
                    if w == rt.value:
                        break
                    out.append(w)
                    w = par.value
                return out
            net = self.x11_active_window()             # what the taskbar shows - up to date on Mint
            if net:
                win = ctypes.c_ulong(net)
            if win.value in (0, 1):                    # None / PointerRoot: no window has the keyboard
                return False
            mine = set(chain(root.winfo_id())) | {frame}   # Tk's window, its wrapper, the desktop's frame
            return any(w in mine for w in chain(win.value))
        except Exception:
            return None

    def x11_active_window(self):
        """The window Mint's taskbar shows as active (_NET_ACTIVE_WINDOW on the root window), or None."""
        import ctypes
        x = self.x
        if not getattr(self, "dpy2", None):
            self.dpy2 = x.XOpenDisplay(None)
        dpy = self.dpy2
        x.XInternAtom.restype = ctypes.c_ulong
        x.XInternAtom.argtypes = [ctypes.c_void_p, ctypes.c_char_p, ctypes.c_int]
        x.XDefaultRootWindow.restype = ctypes.c_ulong
        x.XDefaultRootWindow.argtypes = [ctypes.c_void_p]
        x.XGetWindowProperty.argtypes = [ctypes.c_void_p, ctypes.c_ulong, ctypes.c_ulong, ctypes.c_long, ctypes.c_long,
                                         ctypes.c_int, ctypes.c_ulong, ctypes.POINTER(ctypes.c_ulong),
                                         ctypes.POINTER(ctypes.c_int), ctypes.POINTER(ctypes.c_ulong),
                                         ctypes.POINTER(ctypes.c_ulong), ctypes.POINTER(ctypes.c_void_p)]
        typ, fmt, n, after, data = ctypes.c_ulong(), ctypes.c_int(), ctypes.c_ulong(), ctypes.c_ulong(), ctypes.c_void_p()
        ok = x.XGetWindowProperty(dpy, x.XDefaultRootWindow(dpy), x.XInternAtom(dpy, b"_NET_ACTIVE_WINDOW", 0),
                                  0, 1, 0, 33, ctypes.byref(typ), ctypes.byref(fmt), ctypes.byref(n),
                                  ctypes.byref(after), ctypes.byref(data))      # 33 = XA_WINDOW
        if ok != 0 or not data or n.value < 1:
            return None
        w = ctypes.cast(data, ctypes.POINTER(ctypes.c_ulong))[0]
        x.XFree(data)
        return w or None

    def x11_activate(self, root, window=None):
        """Ask the window manager to activate RigPanel the way a taskbar does (_NET_ACTIVE_WINDOW, source 2 =
        pager) - Mint / GNOME honour that even when RigPanel is in the background."""
        import ctypes
        x = self.x
        if not getattr(self, "dpy2", None):
            self.dpy2 = x.XOpenDisplay(None)
        dpy = self.dpy2

        class ClientMessage(ctypes.Structure):
            _fields_ = [("type", ctypes.c_int), ("serial", ctypes.c_ulong), ("send_event", ctypes.c_int),
                        ("display", ctypes.c_void_p), ("window", ctypes.c_ulong), ("message_type", ctypes.c_ulong),
                        ("format", ctypes.c_int), ("data", ctypes.c_long * 5), ("pad", ctypes.c_long * 16)]
        x.XInternAtom.restype = ctypes.c_ulong
        x.XInternAtom.argtypes = [ctypes.c_void_p, ctypes.c_char_p, ctypes.c_int]
        x.XDefaultRootWindow.restype = ctypes.c_ulong
        x.XDefaultRootWindow.argtypes = [ctypes.c_void_p]
        x.XSendEvent.argtypes = [ctypes.c_void_p, ctypes.c_ulong, ctypes.c_int, ctypes.c_long, ctypes.c_void_p]
        rt = ctypes.c_ulong(0); par = ctypes.c_ulong(0); kids = ctypes.c_void_p(); n = ctypes.c_uint(0)
        x.XQueryTree.argtypes = [ctypes.c_void_p, ctypes.c_ulong, ctypes.POINTER(ctypes.c_ulong), ctypes.POINTER(ctypes.c_ulong),
                                 ctypes.POINTER(ctypes.c_void_p), ctypes.POINTER(ctypes.c_uint)]
        x.XQueryTree(dpy, root.winfo_id(), ctypes.byref(rt), ctypes.byref(par), ctypes.byref(kids), ctypes.byref(n))
        if kids:
            x.XFree(kids)
        client = window or par.value or root.winfo_id()   # Tk's wrapper is the window the WM manages
        ev = ClientMessage(type=33, send_event=1, display=dpy, window=client,
                           message_type=x.XInternAtom(dpy, b"_NET_ACTIVE_WINDOW", 0), format=32)
        ev.data[0], ev.data[1] = 2, 0                  # source: pager; timestamp: now
        x.XSendEvent(dpy, x.XDefaultRootWindow(dpy), 0, (1 << 20) | (1 << 19), ctypes.byref(ev))
        x.XFlush(dpy)

    def poll(self):
        """True once when a lone Ctrl tap has just finished."""
        ctrl, other = self._keys()
        now = time.monotonic()
        if ctrl and not self.down:
            self.down, self.alone, self.t0 = True, not other, now
        elif ctrl and other:
            self.alone = False
        elif not ctrl and self.down:
            self.down = False
            return self.alone and not other and now - self.t0 <= self.TAP_S
        return False


class Extras:
    # ---------------- Ctrl tap: bring RigPanel forward / send it back (11-09b) ----------------
    def start_ctrl_tap(self):
        if not self.cfg.get("ctrl_tap", True) or getattr(self, "ctrl_tap_running", False):
            return
        self.ctrl_tap = CtrlTap()
        if not self.ctrl_tap.ok:
            return
        self.ctrl_tap_hit = False
        tap = self.ctrl_tap

        def watch():                                   # own thread: a quick tap is ~0.1 s, the UI can be busier
            try:
                while not getattr(self, "dead", False) and self.cfg.get("ctrl_tap", True):
                    if tap.poll():
                        self.ctrl_tap_hit = True
                    time.sleep(0.015)
            except Exception as e:
                debug_log(f"Ctrl tap stopped: {e}")
            finally:
                tap.close("dpy")                       # this thread's own X connection
        self.ctrl_tap_running = True
        threading.Thread(target=watch, daemon=True, name="ctrl-tap").start()
        self._ctrl_tap_tick()

    def _ctrl_tap_tick(self):
        if getattr(self, "dead", False) or not self.cfg.get("ctrl_tap", True):
            self.ctrl_tap_running = False
            self.ctrl_tap.close("dpy2")                # the UI thread's X connection
            return
        if self.ctrl_tap_hit:
            self.ctrl_tap_hit = False
            self.toggle_front()
        self.root.after(50, self._ctrl_tap_tick)

    # ---------------- Add my radio (11-14c) ----------------
    ADD_RIG = "Add my radio..."

    def rig_choices(self):
        return RIG_CHOICES + [r["name"] for r in self.cfg.get("custom_rigs", []) if r.get("name")]

    def rig_combo_values(self):
        """The Rig drop-down: the radios, then "Add my radio..." (opens the same window as Settings)."""
        return self.rig_choices() + [self.ADD_RIG]

    def offer_add_radio(self):
        """First connect to a radio RigPanel doesn't know: open Add my radio, filled in. Once per radio name,
        never forced - Close and it isn't asked again (11-14g)."""
        x = (self.xcvr or "").strip()
        if (self.profile is not None or not x or x.upper() == "NONE" or self.rig_var.get() != "Auto-detect"
                or find_custom(self.cfg.get("custom_rigs"), xcvr=x)):
            return
        asked = self.cfg.setdefault("add_radio_asked", [])
        if x in asked:
            return
        asked.append(x)
        save_config(self.cfg)
        self.root.after(600, self.open_add_radio)

    def open_add_radio(self):
        """Settings > Add my radio...: name, what flrig calls it, family (Icom / Yaesu / other), CI-V address."""
        w = getattr(self, "add_radio_win", None)
        if w is not None and w.winfo_exists():
            w.lift()
            return
        w = self.add_radio_win = tk.Toplevel(self.root)
        w.title("Add my radio")
        w.configure(bg=C["panel"])
        w.transient(self.root)
        pad = dict(padx=14, pady=4)
        lab = lambda t, **k: tk.Label(w, text=t, bg=C["panel"], fg=C["fg"], font=(FONT.ui, 10, "bold"), **k)
        dim = lambda t: tk.Label(w, text=t, bg=C["panel"], fg=C["dim"], font=(FONT.ui, 9), justify="left")
        tk.Label(w, text="ADD MY RADIO", bg=C["panel"], fg=C["title"], font=(FONT.ui, 13, "bold")).grid(
            row=0, column=0, columnspan=2, sticky="w", padx=14, pady=(12, 2))
        dim("Any radio flrig supports works with RigPanel. Adding it here gives it a name in the Rig list\n"
            "and, for Icom and Yaesu, the receive controls most of their radios share.").grid(
            row=1, column=0, columnspan=2, sticky="w", padx=14, pady=(0, 8))
        cur = self.xcvr if self.xcvr and not self.profile else ""
        name_v, match_v, civ_v = tk.StringVar(value=cur), tk.StringVar(value=cur), tk.StringVar(value=civ_guess(cur))
        fam_v = tk.StringVar(value="icom" if cur.upper().startswith("IC") else ("yaesu" if cur.upper().startswith("FT") else "flrig"))
        lab("Name").grid(row=2, column=0, sticky="w", **pad)
        tk.Entry(w, textvariable=name_v, width=22, bg=C["field"], fg=C["fg"], insertbackground=C["fg"]).grid(
            row=2, column=1, sticky="w", **pad)
        lab("flrig calls it").grid(row=3, column=0, sticky="w", **pad)
        tk.Entry(w, textvariable=match_v, width=22, bg=C["field"], fg=C["fg"], insertbackground=C["fg"]).grid(
            row=3, column=1, sticky="w", **pad)
        dim("(the RIG name in RigPanel's header when flrig is running - picked automatically)").grid(
            row=4, column=0, columnspan=2, sticky="w", padx=14)
        lab("Family").grid(row=5, column=0, sticky="nw", **pad)
        ff = tk.Frame(w, bg=C["panel"])
        ff.grid(row=5, column=1, sticky="w", **pad)
        civ_row = []
        for key, text in RIG_FAMILIES.items():
            tk.Radiobutton(ff, text=text, value=key, variable=fam_v, bg=C["panel"], fg=C["fg"],
                           selectcolor=C["field"], activebackground=C["panel"], activeforeground=C["fg"],
                           command=lambda: [c.grid() if fam_v.get() == "icom" else c.grid_remove() for c in civ_row]
                           ).pack(anchor="w")
        civ_row.append(lab("CI-V address"))
        civ_row[-1].grid(row=6, column=0, sticky="w", **pad)
        civ_row.append(tk.Entry(w, textvariable=civ_v, width=6, bg=C["field"], fg=C["fg"], insertbackground=C["fg"]))
        civ_row[-1].grid(row=6, column=1, sticky="w", **pad)
        civ_row.append(dim("Hex, as on the radio's CI-V menu: " + CIV_HINTS))
        civ_row[-1].grid(row=7, column=0, columnspan=2, sticky="w", padx=14)
        if fam_v.get() != "icom":
            for c in civ_row:
                c.grid_remove()
        msg = dim("")
        msg.grid(row=9, column=0, columnspan=2, sticky="w", padx=14)
        lst = tk.Frame(w, bg=C["panel"])
        lst.grid(row=10, column=0, columnspan=2, sticky="we", padx=14, pady=(6, 12))

        def show_list():
            for c in lst.winfo_children():
                c.destroy()
            rigs = self.cfg.get("custom_rigs", [])
            if rigs:
                tk.Label(lst, text="YOUR RADIOS", bg=C["panel"], fg=C["title"], font=(FONT.ui, 10, "bold")).pack(anchor="w")
            for r in rigs:
                row = tk.Frame(lst, bg=C["panel"])
                row.pack(fill="x", pady=1)
                civ = f", CI-V {r.get('civ')}" if r.get("family") == "icom" else ""
                tk.Label(row, text=f"{r['name']}  -  {RIG_FAMILIES.get(r.get('family'), '?')}{civ}", bg=C["panel"],
                         fg=C["fg"], font=(FONT.ui, 9)).pack(side="left")
                FlatButton(row, "Remove", command=lambda n=r["name"]: remove(n), font=(FONT.ui, 8, "bold")).pack(side="right")

        def changed():
            self.rig_combo["values"] = self.rig_combo_values()
            if self.rig_var.get() not in self.rig_choices():
                self.rig_var.set("Auto-detect")
                self.cfg["rig"] = "Auto-detect"
            save_config(self.cfg)
            self._apply_profile()
            show_list()

        def remove(n):
            self.cfg["custom_rigs"] = [r for r in self.cfg.get("custom_rigs", []) if r.get("name") != n]
            changed()
            msg.config(text=f"{n} removed.")

        def save():
            n, m, fam = name_v.get().strip(), match_v.get().strip(), fam_v.get()
            civ = civ_v.get().strip().upper().removeprefix("0X")
            if not n:
                msg.config(text="Give the radio a name.", fg=C["red"])
                return
            if n in RIG_CHOICES:
                msg.config(text=f"{n} is built in already.", fg=C["red"])
                return
            if fam == "icom":
                try:
                    if not 0 < int(civ, 16) < 0xE0:
                        raise ValueError
                except ValueError:
                    msg.config(text="CI-V address: two hex digits, e.g. A4.", fg=C["red"])
                    return
            rigs = [r for r in self.cfg.get("custom_rigs", []) if r.get("name") != n]
            rigs.append({"name": n, "match": m or n, "family": fam, "civ": civ if fam == "icom" else ""})
            self.cfg["custom_rigs"] = rigs
            changed()
            msg.config(text=f"{n} saved - it's in the Rig list and picked automatically when flrig reports '{m or n}'.",
                       fg=C["dim"])
            self.log(f"Added radio {n} ({RIG_FAMILIES[fam]})")

        bf = tk.Frame(w, bg=C["panel"])
        bf.grid(row=8, column=0, columnspan=2, sticky="w", padx=14, pady=(8, 2))
        FlatButton(bf, "Save", command=save, font=(FONT.ui, 10, "bold"), base=C["go"], base_fg=C["go_fg"]).pack(side="left")
        FlatButton(bf, "Close", command=w.destroy, font=(FONT.ui, 10, "bold")).pack(side="left", padx=(8, 0))
        show_list()

    def set_ctrl_tap(self, on):
        """Settings menu: Tap Ctrl to bring RigPanel forward - on / off."""
        self.cfg["ctrl_tap"] = bool(on)
        save_config(self.cfg)
        if on:
            self.root.after(200, self.start_ctrl_tap)  # after the old watcher (if any) has stopped
        self.log("Ctrl tap " + ("on: tap Ctrl alone to bring RigPanel forward" if on else "off"))

    def toggle_front(self):
        """Ctrl tap: in front and active -> minimize; minimized or behind other windows -> restore to the front."""
        r = self.root
        active = self.ctrl_tap.is_active(r)
        if active is None:
            active = r.focus_get() is not None
        debug_log(f"Ctrl tap: state {r.state()}, active {active}, Tk focus {r.focus_get() is not None}")
        if r.state() == "normal" and active:
            r.iconify()                                # in front and active: minimize
            return
        if r.state() == "iconic":
            r.deiconify()                              # restores on its own monitor
        if sys.platform == "win32":                    # Windows refuses a background program the front:
            try:                                       # join the front program's input for a moment, then take it
                import ctypes
                u32, k32, hwnd = self.ctrl_tap.u32, ctypes.windll.kernel32, int(r.wm_frame(), 16)
                fg = u32.GetForegroundWindow()
                fg_tid = u32.GetWindowThreadProcessId(fg, None)
                me = k32.GetCurrentThreadId()
                joined = fg_tid and fg_tid != me and u32.AttachThreadInput(me, fg_tid, True)
                u32.BringWindowToTop(hwnd)
                u32.SetForegroundWindow(hwnd)
                if joined:
                    u32.AttachThreadInput(me, fg_tid, False)
            except Exception as e:
                debug_log(f"Ctrl tap: Windows front request failed: {e}")
            r.after(50, r.focus_force)
        else:
            try:
                self.ctrl_tap.x11_activate(r)
            except Exception as e:
                debug_log(f"Ctrl tap: activate request failed: {e}")
            r.lift()
            r.attributes("-topmost", True)             # some window managers won't raise it otherwise
            r.after(200, lambda: r.attributes("-topmost", False))
            r.after(50, r.focus_force)
        r.after(600, lambda: debug_log(f"Ctrl tap: restored -> state {r.state()}, active {self.ctrl_tap.is_active(r)}"))

    # ---------------- building the controls (called from App._build) ----------------
    def _build_clar(self, fr, go):
        """CLAR / RIT block in the frequency panel, between VFO B and the kHz box."""
        # CLAR (FT-891) / RIT (IC-7300): receive offset, transmit stays put
        clar = tk.Frame(fr, bg=HUD["panel"])
        clar.pack(side="right", padx=(16, 4))      # the space the kHz box used to take
        ctop = tk.Frame(clar, bg=HUD["panel"])
        ctop.pack(anchor="w")
        self.clar_name = tk.Label(ctop, text="CLAR", bg=HUD["panel"], fg=THEMES["Dark"]["gold"], font=(FONT.ui, 12, "bold"))
        self.clar_name.pack(side="left")
        self.clar_lbl = tk.Label(ctop, text="0 Hz", width=10, anchor="w", bg=HUD["panel"], fg=HUD["value_dim"],
                                 font=(FONT.mono, 14, "bold"), cursor="hand2")
        self.clar_lbl.pack(side="left", padx=(6, 0))
        for ev, d in (("<Button-4>", 1), ("<Button-5>", -1)):
            self.clar_lbl.bind(ev, lambda e, d=d: self.clar_step(d))
        self.clar_lbl.bind("<MouseWheel>", lambda e: self.clar_step(1 if e.delta > 0 else -1))
        Tooltip(self.clar_lbl, "Receive offset - your transmit frequency doesn't move. Mouse wheel = 10 Hz")
        cb = tk.Frame(clar, bg=HUD["panel"])
        cb.pack(anchor="w", pady=(3, 0))
        self.clar_btn = FlatButton(cb, "ON", command=self.clar_toggle, **go)
        self.clar_btn.config(padx=7, pady=2)
        self.clar_btn.pack(side="left", padx=(0, 3))
        for text, d in (("\u25c0", -1), ("\u25b6", 1)):
            b = FlatButton(cb, text, command=lambda d=d: self.clar_step(d), font=(FONT.ui, 9, "bold"))
            b.config(padx=7, pady=2)
            b.pack(side="left", padx=(0, 3))
        b = FlatButton(cb, "CLEAR", command=lambda: self.clar_set(0), font=(FONT.ui, 9, "bold"))
        b.config(padx=7, pady=2)
        b.pack(side="left")
        self.clar_on, self.clar_hz = False, 0

    def _build_shift(self, mf):
        """Passband SHIFT in the MODE row (shown only in USB / LSB)."""
        # passband SHIFT (voice only: USB / LSB)
        self.shift_f = tk.Frame(mf, bg=C["panel"])
        small_label(self.shift_f, "Shift").pack(side="left", padx=(14, 4))
        sb = dict(font=(FONT.ui, 9, "bold"))
        b = FlatButton(self.shift_f, "\u25c0", command=lambda: self.shift_step(-1), **sb)
        b.config(padx=7)
        b.pack(side="left")
        self.shift_lbl = tk.Label(self.shift_f, text="0 Hz", width=8, bg=HUD["panel"], fg=HUD["value_dim"],
                                  font=(FONT.mono, 10, "bold"), cursor="hand2")
        self.shift_lbl.pack(side="left", padx=2, ipady=3)
        b = FlatButton(self.shift_f, "\u25b6", command=lambda: self.shift_step(1), **sb)
        b.config(padx=7)
        b.pack(side="left")
        self.shift_c = FlatButton(self.shift_f, "Center", command=lambda: self.shift_to(0), **sb)
        self.shift_c.config(padx=7)
        self.shift_c.pack(side="left", padx=(3, 0))
        for w in (self.shift_lbl,):
            w.bind("<MouseWheel>", lambda e: self.shift_step(1 if e.delta > 0 else -1))
            w.bind("<Button-4>", lambda e: self.shift_step(1))
            w.bind("<Button-5>", lambda e: self.shift_step(-1))
        Tooltip(self.shift_lbl, "Passband shift (voice): \u25c0 \u25b6 or the mouse wheel; Center puts it back")
        self.shift_hz = 0

    def _build_mute(self, holder):
        """MUTE button beside the AF Volume bar."""
        self.mute_btn = FlatButton(holder, "MUTE", command=self.toggle_mute, font=(FONT.ui, 8, "bold"),
                                   on_color=C["tx"], on_fg="#ffffff")
        self.mute_btn.config(padx=6)
        self.mute_btn.pack(side="left", padx=(4, 0), anchor="s", pady=(0, 2))
        Tooltip(self.mute_btn, "Mute the radio's audio (Shift+M); click again for the level you had")

    # ---------------- CLAR (FT-891) / RIT (IC-7300) ----------------
    def _clar_ok(self):
        return self.connected and hasattr(self.profile, "clar_read_strings")

    def _show_clar(self):
        name = getattr(self.profile, "CLAR_NAME", "CLAR")
        self.clar_name.config(text=name)
        hz = self.clar_hz
        if getattr(self.profile, "CLAR_KHZ", False):      # IC-7300 shows RIT in kHz: 20 Hz = 0.02
            text = f"{hz / 1000:+.2f} kHz" if hz else "0.00 kHz"
        else:
            text = f"{hz:+d} Hz" if hz else "0 Hz"
        self.clar_lbl.config(text=text,
                             fg=HUD["value"] if self.clar_on else HUD["value_dim"])
        self.clar_btn.set_on(self.clar_on)

    def clar_toggle(self):
        if not self._need_link() or not self._clar_ok():
            return
        on = not self.clar_on
        self.clar_on = on
        self._touch("clar")
        self._show_clar()
        self.worker.submit(lambda w: w.clar(on=on))

    def clar_step(self, d):
        if self._clar_ok():
            self.clar_set(self.clar_hz + d * self.profile.CLAR_STEP)

    def clar_set(self, hz):
        if not self._need_link() or not self._clar_ok():
            return
        hz = max(-self.profile.CLAR_MAX, min(self.profile.CLAR_MAX, int(hz)))
        turn_on = None if self.clar_on or hz == 0 else True      # moving the offset switches it on
        self.clar_hz = hz
        if turn_on:
            self.clar_on = True
        self._touch("clar")
        self._show_clar()
        self.worker.submit(lambda w: w.clar(on=turn_on, hz=hz))

    def _on_clar(self, data):
        (on, hz), sent_on, sent_hz = data
        if not self._recent("clar"):
            if on is not None:
                self.clar_on = on
            if hz is not None:
                self.clar_hz = hz
        self._show_clar()

    # ---------------- passband SHIFT (voice: USB / LSB) ----------------
    def _shift_ok(self):
        return hasattr(self.profile, "shift_read_string") and str(self.mode or "").upper() in ("USB", "LSB")

    def _show_shift_row(self):
        want = self._shift_ok()
        if want != bool(self.shift_f.winfo_ismapped()):
            if want:
                self.shift_f.pack(side="left", before=self.mode_ctl)
            else:
                self.shift_f.pack_forget()

    def _show_shift(self):
        hz = self.shift_hz
        self.shift_lbl.config(text=f"{hz:+d} Hz" if hz else "0 Hz", fg=HUD["value"] if hz else HUD["value_dim"])
        self.shift_c.set_on(False)

    def shift_step(self, d):
        prof = self.profile
        if not self._shift_ok():
            return
        self.shift_to(self.shift_hz + d * prof.SHIFT_STEP)

    def shift_to(self, hz):
        if not self._need_link() or not self._shift_ok():
            return
        prof = self.profile
        hz = max(-prof.SHIFT_MAX, min(prof.SHIFT_MAX, int(hz)))
        self.shift_hz = hz
        self._touch("shift")
        self._show_shift()
        self.worker.submit(lambda w: w.shift(hz))

    def _on_shift(self, data):
        v, sent = data
        if v is not None and not self._recent("shift"):
            self.shift_hz = v
        elif v is None and sent is not None:
            self.shift_hz = sent                 # flrig 2.0.12 can hide some values: keep what was sent
        self._show_shift()

    # ---------------- MUTE (AF Volume) ----------------
    def toggle_mute(self):
        """AF Volume to 0, and back to the level you had (not stored as your voice/data level)."""
        if not self._need_link():
            return
        bar = self.sliders["volume"]
        if self.muted_vol is None:
            if bar.get() <= 0:
                self.log("AF Volume is already at 0.")
                return
            self.muted_vol, target = bar.get(), 0
            self.log(f"Muted (AF Volume was {self.muted_vol}) - MUTE or Shift+M again to bring it back")
        else:
            target, self.muted_vol = self.muted_vol, None
            self.log(f"Unmuted - AF Volume {target}")
        bar.set(target)
        self.slider_moved("volume", "rig.set_volume", target, remember=False)
        self._show_mute()

    def _show_mute(self):
        on = self.muted_vol is not None
        self.mute_btn.config(text="MUTED" if on else "MUTE")
        self.mute_btn.set_on(on)
        if getattr(self, "mini_lv", None) is not None:
            self.mini_lv.show_mute()               # the Mini Levels window has one too

    # ---------------- FT-891 VFO Scan (the radio's own scan) ----------------
    def has_vfo_scan(self):
        return bool(getattr(self.profile, "HAS_VFO_SCAN", False))

    def toggle_vscan(self):
        if self.vscan_win is not None and self.vscan_win.winfo_exists():
            self.vscan_win.close()
            return
        if not self._need_link() or not self.has_vfo_scan():
            return
        self.vscan_win = VfoScan(self)
        self.vscan_win.open()
        self.sync_vscan_button()

    def sync_vscan_button(self):
        try:
            self.scan_btn.set_on(self.vscan_win is not None and self.vscan_win.winfo_exists())
        except tk.TclError:
            pass

    def close_vscan(self):
        if getattr(self, "vscan_win", None) is not None and self.vscan_win.winfo_exists():
            self.vscan_win.close()

    def show_scan_button(self):
        """The gold Scan button is there only for a radio with its own scan over CAT (the FT-891)."""
        try:
            if self.has_vfo_scan():
                if not self.scan_btn.winfo_manager():
                    self.scan_btn.pack(side="right", padx=(0, 6), after=self.mini_btn)
            else:
                self.scan_btn.pack_forget()
        except (tk.TclError, AttributeError):
            pass
