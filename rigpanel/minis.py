"""Floating mini meter and Mini Levels windows."""
from .core import *  # noqa: F401,F403
from .radios import *  # noqa: F401,F403
from .worker import *  # noqa: F401,F403
from .widgets import *  # noqa: F401,F403
from .waterfall import *  # noqa: F401,F403
from .freqlist import *  # noqa: F401,F403

# --------------------------------------------------------------------------
# Mini meter: small always-on-top Po / SWR / ALC window
# --------------------------------------------------------------------------
class _Cmd:
    """Tiny stand-in with a .command, so older code can still call mini.full_btn.command()."""
    def __init__(self, command):
        self.command = command


class MiniMeter(tk.Toplevel):
    """Floating, always-on-top meter in the HUD look, drawn on one canvas.
    Drag anywhere to move it; drag a corner to make it bigger or smaller.
    Size (mini_scale) and place (mini_pos) are remembered."""
    HIDE_AFTER_TX_MS = 4000      # auto-shown meter stays this long after TX so you can read SWR
    BASE_W, BASE_H = 340, 250    # pixels at size 1.0 (before display scaling)
    SCALE_MIN, SCALE_MAX = 0.8, 3.0
    GRIP = 16                    # corner grab area, pixels
    # The mini meter keeps this dark HUD look in both themes (it floats over other programs).
    HUD = HUD
    NAMES = ("S-METER", "POWER", "SWR", "ALC")
    CURSORS = {"nw": "top_left_corner", "ne": "top_right_corner",
               "sw": "bottom_left_corner", "se": "bottom_right_corner"}
    KEYS = dict(auto="mini_auto", always="mini_always", pos="mini_pos", scale="mini_scale")
    APP_VARS = ("mini_auto_var", "mini_always_var")      # the main window's tick boxes
    BUTTONS = ("mini_btn", "mini_btn2")                  # main window buttons that light up when shown
    HOTKEY = "Shift+Z"
    AUTO_TEXT = "Pop up when transmitting"
    AUTO_DEFAULT = True
    HAS_FULL = True                                      # Full Panel button in Compact View
    DEFAULT_DY = 20                                      # first-time place: below the top of the main window

    def __init__(self, app):
        super().__init__(app.root)
        self.app = app
        self.withdraw()
        self.overrideredirect(True)            # no title bar; drag it anywhere
        self.attributes("-topmost", True)      # stays above your other programs
        self.manual = False                    # opened with Shift+Z / button (stays until closed)
        self.hide_job = None
        self.drag = None
        self.compact = False
        self._cursor = None
        self._xy = None
        self.dpi = max(1.0, float(self.tk.call("tk", "scaling")) / (96 / 72))
        try:
            s = float(app.cfg.get(self.KEYS["scale"]) or 1.0)
        except (TypeError, ValueError):
            s = 1.0
        self.scale = max(self.SCALE_MIN, min(self.SCALE_MAX, s))
        self.cv = tk.Canvas(self, highlightthickness=0, bd=0, bg=self.HUD["bottom"])
        self.cv.pack(fill="both", expand=True)
        self.tx_lbl = self.cv                  # older name, kept for the tests
        self.full_btn = _Cmd(app.exit_compact)
        self.mains = self._sources()
        self.rows = []
        self._layout()

        self.auto_var = tk.BooleanVar(value=app.cfg.get(self.KEYS["auto"], self.AUTO_DEFAULT))
        self.always_var = tk.BooleanVar(value=app.cfg.get(self.KEYS["always"], False))
        self.menu = app._menu(self)
        self.menu.add_checkbutton(label=self.AUTO_TEXT, variable=self.auto_var,
                                  command=self._menu_changed)
        self.menu.add_checkbutton(label="Always on screen", variable=self.always_var,
                                  command=self._menu_changed)
        self.menu.add_command(label="Normal size", command=self.normal_size)
        self.menu.add_separator()
        self.menu.add_command(label=f"Hide  ({self.HOTKEY})", command=self.hide)

        self.cv.bind("<ButtonPress-1>", self._press)
        self.cv.bind("<B1-Motion>", self._drag_move)
        self.cv.bind("<ButtonRelease-1>", self._drag_end)
        self.cv.bind("<Motion>", self._hover)
        self.cv.bind("<Button-3>", self._popup_menu)
        # the Shift hot keys are bound app-wide in App (bind_all), which already covers this window

    def _sources(self):
        return (self.app.m_s, self.app.m_po, self.app.m_swr, self.app.m_alc)

    # ---- drawing ----
    def _k(self):
        return self.scale * self.dpi

    def _size(self):
        k = self._k()
        return int(self.BASE_W * k), int(self.BASE_H * k)

    def _layout(self):
        """Draw the whole meter at the current size (pixel-sized fonts, so it scales cleanly)."""
        k, H, cv = self._k(), self.HUD, self.cv
        w, h = self._size()

        def px(v):
            return max(1, int(round(v * k)))

        def font(family, size, bold=True):
            return (family, -px(size), "bold" if bold else "normal")

        cv.config(width=w, height=h)
        cv.delete("all")
        for y in range(0, h, 2):               # dark blue gradient, top to bottom
            cv.create_rectangle(0, y, w, y + 2, fill=hex_mix(H["top"], H["bottom"], y / h), outline="")
        cv.create_rectangle(0, 0, w - 1, h - 1, outline=H["edge"])
        g = px(10)                             # corner marks = where to grab to resize
        for x, y, dx, dy in ((1, 1, 1, 1), (w - 2, 1, -1, 1), (1, h - 2, 1, -1), (w - 2, h - 2, -1, -1)):
            cv.create_line(x, y, x + dx * g, y, fill=H["grip"], width=2)
            cv.create_line(x, y, x, y + dy * g, fill=H["grip"], width=2)

        hy = px(19)                            # header: RX/TX, frequency, hot key, close
        self.pill = cv.create_rectangle(px(12), px(8), px(48), px(30), fill=C["go"], outline="")
        self.pill_txt = cv.create_text(px(30), hy, text="RX", fill=C["go_fg"], font=font(FONT.ui, 13))
        self.freq_item = cv.create_text(px(58), hy, text="", anchor="w", fill=H["value"], font=font(FONT.mono, 20))
        cv.create_text(w - px(16), hy, text="✕", fill=H["close"], font=font(FONT.ui, 15, False), tags=("close",))
        self.ctrlz = cv.create_text(w - px(36), hy, text=self.HOTKEY, anchor="e", fill=H["hint"],
                                    font=font(FONT.ui, 12))
        fx1 = w - px(34)
        fx0 = fx1 - px(80)
        self.full_items = (
            cv.create_rectangle(fx0, px(8), fx1, px(30), fill=C["tx"], outline="", tags=("full",)),
            cv.create_text((fx0 + fx1) / 2, hy, text="Full Panel", fill="#ffffff", font=font(FONT.ui, 11), tags=("full",)))
        cv.create_line(px(12), px(38), w - px(12), px(38), fill=H["edge"])
        if not self.HAS_FULL:
            for item in self.full_items:
                cv.delete(item)
            self.full_items = ()
        self._draw_rows(px, font, w, h)
        self.set_compact(self.compact)
        self.mirror(force=True)

    def _draw_rows(self, px, font, w, h):
        x0, x1 = px(12), w - px(12)
        rowh = (h - px(46)) / 4
        self.rows = []
        for i, main in enumerate(self.mains):
            self.rows.append(self._meter_row(px, font, main, self.NAMES[i], px(44) + i * rowh, x0, x1))

    def _meter_row(self, px, font, main, name, t, x0, x1):
        """One meter row (name, value, coloured bar, scale) with its top at t; returns its parts."""
        H, cv = self.HUD, self.cv
        cv.create_text(x0, t + px(9), text=name, anchor="w", fill=H["label"], font=font(FONT.ui, 12))
        val = cv.create_text(x1, t + px(9), text="--", anchor="e", fill=H["value"], font=font(FONT.mono, 18))
        by0, by1 = t + px(20), t + px(30)
        cv.create_rectangle(x0, by0, x1, by1, fill=H["track"], outline=H["track_edge"])
        segs = [cv.create_rectangle(x0, by0, x0, by1, outline="", state="hidden") for _ in range(3)]
        shine = cv.create_line(x0, by0 + 1, x0, by0 + 1, fill="#ffffff", state="hidden")
        zone = cv.create_line(0, 0, 0, 0, fill=H["tick"], dash=(2, 2), state="hidden")
        for frac, txt in main.ticks:
            tx = x0 + 1 + (x1 - x0 - 2) * frac
            cv.create_line(tx, by1, tx, by1 + px(4), fill=H["tick"])
            anchor = "nw" if frac <= 0 else ("ne" if frac >= 1 else "n")
            cv.create_text(tx, by1 + px(4), text=txt, anchor=anchor, fill=H["tick_txt"], font=font(FONT.ui, 11))
        return dict(val=val, segs=segs, shine=shine, zone=zone, x0=x0 + 1, x1=x1 - 1,
                    y0=by0 + 1, y1=by1, ticks=list(main.ticks), zf=None, last=None)

    # ---- visibility ----
    def visible(self):
        return self.state() == "normal"

    def set_compact(self, on):
        """Compact View: show a Full Panel button so there's always a way back."""
        self.compact = bool(on)
        for item in self.full_items:
            self.cv.itemconfig(item, state="normal" if on else "hidden")
        self.cv.itemconfig(self.ctrlz, state="hidden" if on and self.HAS_FULL else "normal")

    def show(self, manual):
        self.manual = self.manual or manual
        if self.hide_job:
            self.after_cancel(self.hide_job)
            self.hide_job = None
        if not self.visible():
            self.mirror()
            self.update_idletasks()
            w, h = self._size()
            self.geometry("%dx%d+%d+%d" % ((w, h) + self._position()))
            self.deiconify()
        self.lift()
        self.attributes("-topmost", True)
        self.sync_buttons()
        if SYS != "Windows" and not getattr(self, "_keep_job", None):
            self._keep_job = self.after(2000, self._keep_on_top)

    def _keep_on_top(self):
        """Some X11 window managers don't keep a borderless window above others, so re-raise
        it every 2 s while it's showing (cheap, and harmless where -topmost already works)."""
        self._keep_job = None
        try:
            if self.winfo_exists() and self.visible():
                self.lift()
                self._keep_job = self.after(2000, self._keep_on_top)
        except tk.TclError:
            pass

    def sync_buttons(self):
        on = self.visible()
        fw = getattr(self.app, "float_wf", None)
        extra = (fw.mini_btn if fw is not None and fw.winfo_exists() else None,) if self.HAS_FULL else ()
        for b in tuple(getattr(self.app, n, None) for n in self.BUTTONS) + extra:
            if b is not None and b.winfo_exists():
                b.set_on(on)

    def hide(self):
        if self.app.compact and self.HAS_FULL:  # hiding the last window in Compact View: come back instead
            self.app.exit_compact()
            if not self.visible():
                return
        self.cancel_jobs()
        self.manual = False
        self.withdraw()
        self.sync_buttons()
        if self.always_var.get():              # hiding it on purpose turns "Always on screen" off
            self.set_options(always=False)

    def cancel_jobs(self):
        if getattr(self, "_keep_job", None):
            try:
                self.after_cancel(self._keep_job)
            except tk.TclError:
                pass
            self._keep_job = None
        if self.hide_job:
            try:
                self.after_cancel(self.hide_job)
            except tk.TclError:
                pass
            self.hide_job = None

    def toggle(self):
        if self.visible():
            self.hide()
        else:
            self.show(manual=True)

    def on_ptt(self, ptt):
        if ptt:
            if self.auto_var.get():
                self.show(manual=False)
        elif self.visible() and not self.manual and not self.always_var.get() and not self.hide_job:
            self.hide_job = self.after(self.HIDE_AFTER_TX_MS, self._auto_hide)

    def _auto_hide(self):
        self.hide_job = None
        if not self.manual and not self.always_var.get() and not self.app.ptt:
            self.withdraw()
            self.sync_buttons()

    def set_options(self, auto=None, always=None):
        """One place for both options; keeps the right-click menu, the main
        window's checkboxes and the saved settings in step."""
        if auto is not None:
            self.auto_var.set(auto)
            getattr(self.app, self.APP_VARS[0]).set(auto)
            self.app.cfg[self.KEYS["auto"]] = auto
        if always is not None:
            self.always_var.set(always)
            getattr(self.app, self.APP_VARS[1]).set(always)
            self.app.cfg[self.KEYS["always"]] = always
            if always:
                self.show(manual=True)
        save_config(self.app.cfg)

    def _menu_changed(self):
        self.set_options(auto=bool(self.auto_var.get()), always=bool(self.always_var.get()))

    # ---- contents ----
    def mirror(self, force=False):
        """Copy the main window's meters (values, scales, ALC limit) and RX/TX + frequency."""
        if self._mirror_rows(force):
            self._mirror_head()

    def _mirror_head(self):
        cv = self.cv
        ptt = bool(getattr(self.app, "ptt", False))
        cv.itemconfig(self.pill, fill=C["tx"] if ptt else C["go"])
        cv.itemconfig(self.pill_txt, text="TX" if ptt else "RX", fill="#ffffff" if ptt else C["go_fg"])
        freq = getattr(self.app, "freq", None)
        cv.itemconfig(self.freq_item, text=fmt_freq(freq) if freq else "")

    def _mirror_rows(self, force):
        """Meter rows; returns False when it had to redraw everything (which mirrors anyway)."""
        if any(row["ticks"] != main.ticks for main, row in zip(self.mains, self.rows)):
            self._layout()                     # a scale changed (e.g. Po full scale): redraw, which mirrors
            return False
        for main, row in zip(self.mains, self.rows):
            self._paint_meter(main, row, force)
        return True

    def _paint_meter(self, main, row, force):
        H, cv = self.HUD, self.cv
        zf = getattr(main, "zone", None)
        if zf != row["zf"]:
            row["zf"] = zf
            if zf:
                zx = row["x0"] + (row["x1"] - row["x0"]) * zf
                cv.coords(row["zone"], zx, row["y0"] - 3, zx, row["y1"] + 3)
                cv.itemconfig(row["zone"], state="normal")
            else:
                cv.itemconfig(row["zone"], state="hidden")
        if not force and row["last"] == main.last:
            return
        row["last"] = main.last
        frac, text, color, dim = main.last
        f = max(0.0, min(1.0, frac))
        x0, x1, y0, y1 = row["x0"], row["x1"], row["y0"], row["y1"]
        end = x0 + (x1 - x0) * f
        if dim:
            zones = ((1.0, H["bar_dim"]),)
        elif main is self.app.m_s:
            zones = tuple((upto, H[c]) for upto, c in S_ZONES)
        else:
            zones = ((1.0, color or H["green"]),)
        start, top_col = x0, None
        for n, seg in enumerate(row["segs"]):
            if n < len(zones):
                upto, col = zones[n]
                zx = x0 + (x1 - x0) * upto
                a, b = start, min(end, zx)
                start = zx
                if b > a:
                    cv.coords(seg, a, y0, b, y1)
                    cv.itemconfig(seg, fill=col, state="normal")
                    top_col = col
                    continue
            cv.itemconfig(seg, state="hidden")
        if top_col and end > x0 + 1:       # thin bright line on top = "glass" shine
            cv.coords(row["shine"], x0, y0, end, y0)
            cv.itemconfig(row["shine"], fill=hex_mix(top_col, "#ffffff", 0.55), state="normal")
        else:
            cv.itemconfig(row["shine"], state="hidden")
        cv.itemconfig(row["val"], text=text, fill=H["value_dim"] if dim else H["value"])

    # ---- position and size ----
    def _position(self):
        w, h = self._size()
        pos = self.app.cfg.get(self.KEYS["pos"])
        if pos:
            x, y = pos
        else:                                  # first time: top-right of the main window
            r = self.app.root
            x, y = r.winfo_rootx() + r.winfo_width() - w - 20, r.winfo_rooty() + self.DEFAULT_DY
        left, top, right, bottom = screen_bounds(self)
        x = max(left, min(x, right - w))       # keep it on screen if a monitor went away
        y = max(top, min(y, bottom - h))
        return x, y

    def _corner(self, x, y):
        w, h = self.cv.winfo_width(), self.cv.winfo_height()
        g = int(self.GRIP * self.dpi)
        ns = "n" if y < g else ("s" if y >= h - g else "")
        ew = "w" if x < g else ("e" if x >= w - g else "")
        return ns + ew if ns and ew else None

    def _tag_at(self, x, y):
        for item in self.cv.find_overlapping(x - 1, y - 1, x + 1, y + 1):
            if self.cv.itemcget(item, "state") != "hidden":
                tags = self.cv.gettags(item)
                if "close" in tags:
                    return "close"
                if "full" in tags:
                    return "full"
                if "mute" in tags:
                    return "mute"
        return None

    def _hover(self, e):
        if self.drag:
            return
        cur = self.CURSORS.get(self._corner(e.x, e.y)) or \
            ("hand2" if self._tag_at(e.x, e.y) or self._row_at(e.x, e.y) else "")
        if cur != self._cursor:
            self._cursor = cur
            self.cv.config(cursor=cur)

    def _press(self, e):
        if self._press_row(e):
            return
        tag = self._tag_at(e.x, e.y)
        if tag == "close":
            self.hide()
            return
        if tag == "full":
            self.app.exit_compact()
            return
        if tag == "mute":
            self.app.toggle_mute()
            return
        corner = self._corner(e.x, e.y)
        if corner:
            self.drag = ("size", corner, self.winfo_x(), self.winfo_y(), self.winfo_width(), self.winfo_height(),
                         e.x_root, e.y_root)
        else:
            self.drag = ("move", e.x_root - self.winfo_x(), e.y_root - self.winfo_y())

    def _drag_move(self, e):
        d = self.drag
        if not d:
            return
        if d[0] == "level":
            self._level_at(d[1], e.x)
            return
        if d[0] == "move":
            self.geometry("+%d+%d" % (e.x_root - d[1], e.y_root - d[2]))
            return
        _, corner, x, y, w, h, rx, ry = d
        dx = (e.x_root - rx) * (1 if "e" in corner else -1)
        dy = (e.y_root - ry) * (1 if "s" in corner else -1)
        ratio = self.BASE_W / self.BASE_H
        new_w = w + dx if abs(dx) >= abs(dy) * ratio else (h + dy) * ratio   # follow the bigger move
        k = max(self.SCALE_MIN, min(self.SCALE_MAX, new_w / (self.BASE_W * self.dpi)))
        if abs(k - self.scale) < 0.01:
            return
        self.scale = k
        nw, nh = self._size()
        nx = x + w - nw if "w" in corner else x          # the opposite corner stays put
        ny = y + h - nh if "n" in corner else y
        self._layout()
        self.geometry("%dx%d+%d+%d" % (nw, nh, nx, ny))
        self._xy = (nx, ny)

    def _drag_end(self, e):
        d, self.drag = self.drag, None
        if not d or d[0] == "level":
            return
        if d[0] == "move":
            x, y = e.x_root - d[1], e.y_root - d[2]   # where it was dropped
            self.geometry("+%d+%d" % (x, y))
        else:
            x, y = self._xy or (d[2], d[3])
            self.app.cfg[self.KEYS["scale"]] = round(self.scale, 3)
        self.app.cfg[self.KEYS["pos"]] = [x, y]
        save_config(self.app.cfg)

    def normal_size(self):
        self.scale = 1.0
        x, y = self.winfo_x(), self.winfo_y()
        self._layout()
        w, h = self._size()
        self.geometry("%dx%d+%d+%d" % (w, h, x, y))
        self.app.cfg[self.KEYS["scale"]] = 1.0
        save_config(self.app.cfg)

    def _press_row(self, e):
        return False                           # meters can't be clicked (MiniLevels overrides)

    def _row_at(self, x, y):
        return None

    def _popup_menu(self, e):
        popup_menu(self.menu, e.x_root, e.y_root)


class MiniLevels(MiniMeter):
    """Floating levels (RF Power, Mic Gain, RF Gain, AF Volume) in the same HUD look as the
    mini meter. Click, drag or wheel on a bar to change it; drag elsewhere to move;
    drag a corner to resize. Shift+L shows / hides it. "Pop up when receiving" shows it
    on receive and hides it while transmitting."""
    KEYS = dict(auto="lv_auto", always="lv_always", pos="lv_pos", scale="lv_scale")
    APP_VARS = ("lv_auto_var", "lv_always_var")
    BUTTONS = ("lv_btn",)
    HOTKEY = "Shift+L"
    AUTO_TEXT = "Pop up when receiving"
    AUTO_DEFAULT = False
    HAS_FULL = False
    DEFAULT_DY = 300
    ROWS = (("power", "RF POWER"), ("micgain", "MIC GAIN"), ("rfgain", "RF GAIN"), ("volume", "AF VOLUME"))
    S_ROW_H = 58                               # extra height for the S-METER row (at size 1.0)

    def __init__(self, app):
        self.smeter_var = None
        self.show_s = bool(app.cfg.get("lv_smeter", True))     # S-METER row on top (28a)
        self.BASE_H = MiniMeter.BASE_H + (self.S_ROW_H if self.show_s else 0)
        super().__init__(app)
        self.smeter_var = tk.BooleanVar(value=self.show_s)
        self.menu.insert_checkbutton(2, label="Show S-meter", variable=self.smeter_var,
                                     command=self._smeter_changed)
        self.cv.bind("<MouseWheel>", lambda e: self._wheel(e, 1 if e.delta > 0 else -1))
        self.cv.bind("<Button-4>", lambda e: self._wheel(e, 1))
        self.cv.bind("<Button-5>", lambda e: self._wheel(e, -1))

    def _sources(self):
        return tuple(self.app.sliders[key] for key, _ in self.ROWS)

    def _smeter_changed(self):
        """Right-click "Show S-meter": add / remove the S-METER row; the top-left corner stays put."""
        self.show_s = bool(self.smeter_var.get())
        self.app.cfg["lv_smeter"] = self.show_s
        save_config(self.app.cfg)
        self.BASE_H = MiniMeter.BASE_H + (self.S_ROW_H if self.show_s else 0)
        x, y = self.winfo_x(), self.winfo_y()
        self._layout()
        if self.visible():
            w, h = self._size()
            self.geometry("%dx%d+%d+%d" % (w, h, x, y))

    def _draw_rows(self, px, font, w, h):
        H, cv = self.HUD, self.cv
        x0, x1 = px(12), w - px(12)
        top = px(44)
        self.s_row = None
        if self.show_s:                        # S-METER: same row as the Mini Meter's, then a line
            self.s_row = self._meter_row(px, font, self.app.m_s, "S-METER", top, x0, x1)
            top += px(self.S_ROW_H)
            cv.create_line(x0, top - px(6), x1, top - px(6), fill=H["edge"])
        rowh = (h - px(46) - (px(self.S_ROW_H) if self.show_s else 0)) / 4
        self.rows = []
        for i, (bar, (key, name)) in enumerate(zip(self.mains, self.ROWS)):
            t = top + i * rowh
            cv.create_text(x0, t + px(12), text=name, anchor="w", fill=H["label"], font=font(FONT.ui, 12))
            val = cv.create_text(x1, t + px(12), text="--", anchor="e", fill=H["value"], font=font(FONT.mono, 18))
            by0, by1 = t + px(26), t + px(38)
            cv.create_rectangle(x0, by0, x1, by1, fill=H["track"], outline=H["track_edge"])
            fill = cv.create_rectangle(x0, by0, x0, by1, fill=bar.color, outline="")
            shine = cv.create_line(x0, by0 + 1, x0, by0 + 1, fill=hex_mix(bar.color, "#ffffff", 0.55))
            knob = cv.create_rectangle(0, 0, 0, 0, fill="#ffffff", outline="")
            self.rows.append(dict(bar=bar, val=val, fill=fill, shine=shine, knob=knob, x0=x0 + 1, x1=x1 - 1,
                                  y0=by0 + 1, y1=by1, ky=(by0 - px(4), by1 + px(4)), kw=px(3),
                                  hit=(by0 - px(10), by1 + px(8)), last=None))
            if key == "volume":                # MUTE beside the AF VOLUME name (same as the main window)
                mx = x0 + px(104)
                self.mute_items = (
                    cv.create_rectangle(mx, t + px(3), mx + px(62), t + px(21), outline=H["edge"], tags=("mute",)),
                    cv.create_text(mx + px(31), t + px(12), text="MUTE", font=font(FONT.ui, 11), tags=("mute",)))
                self.show_mute()

    def _mirror_rows(self, force):
        cv = self.cv
        if getattr(self, "s_row", None):
            self._paint_meter(self.app.m_s, self.s_row, force)
        for row in self.rows:
            bar = row["bar"]
            state = (bar.value, bar.max)
            if not force and row["last"] == state:
                continue
            row["last"] = state
            f = bar.value / bar.max if bar.max else 0
            x = row["x0"] + (row["x1"] - row["x0"]) * f
            cv.coords(row["fill"], row["x0"], row["y0"], x, row["y1"])
            cv.coords(row["shine"], row["x0"], row["y0"], x, row["y0"])
            cv.coords(row["knob"], x - row["kw"], row["ky"][0], x + row["kw"], row["ky"][1])
            cv.itemconfig(row["val"], text=f"{bar.value}{bar.unit}")
        return True

    def show_mute(self):
        """MUTE pill: red "MUTED" while the AF Volume is muted (App.toggle_mute)."""
        items = getattr(self, "mute_items", None)
        if not items:
            return
        on = getattr(self.app, "muted_vol", None) is not None
        self.cv.itemconfig(items[0], fill=C["tx"] if on else self.HUD["track"])
        self.cv.itemconfig(items[1], text="MUTED" if on else "MUTE", fill="#ffffff" if on else self.HUD["hint"])

    def _row_at(self, x, y):
        for row in self.rows:
            if row["hit"][0] <= y <= row["hit"][1] and row["x0"] - 6 <= x <= row["x1"] + 6:
                return row
        return None

    def _press_row(self, e):
        if self._corner(e.x, e.y):
            return False
        row = self._row_at(e.x, e.y)
        if not row:
            return False
        self.drag = ("level", row)
        self._level_at(row, e.x)
        return True

    def _level_at(self, row, x):
        bar = row["bar"]
        f = (x - row["x0"]) / max(1, row["x1"] - row["x0"])
        bar._change(round(f * bar.max))       # same as using the main window's bar
        self._mirror_rows(False)

    def _wheel(self, e, step):
        row = self._row_at(e.x, e.y)
        if row:
            row["bar"]._change(row["bar"].value + step)
            self._mirror_rows(False)

    def on_ptt(self, ptt):
        if ptt:                                # transmitting: step aside unless kept on screen
            if self.visible() and not self.manual and not self.always_var.get():
                self.withdraw()
                self.sync_buttons()
        elif self.auto_var.get():
            self.show(manual=False)
