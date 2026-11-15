"""Small Tk widgets in the RigPanel look: buttons, meters, level bars, frequency display."""
from .core import *  # noqa: F401,F403
from .radios import *  # noqa: F401,F403
from .worker import *  # noqa: F401,F403

# --------------------------------------------------------------------------
# Small widgets
# --------------------------------------------------------------------------
class FlatButton(tk.Canvas):
    """RigPanel's button (1.4.2: raised 3D look). Drawn on a canvas so it looks the same on
    Windows, macOS and Linux: soft top-to-bottom shading, a light top edge and a drop shadow;
    coloured buttons (base=...) stay solid; "on" looks pressed in, in on_color.
    Same use as before: FlatButton(parent, "Text", command=..., font=..., base=..., on_color=...),
    .config(text=, padx=, pady=), .cget("text"), .set_on(True), .command, .on."""
    RADIUS = 5
    _fonts = {}

    def __init__(self, master, text, command=None, width=None, font=None, on_color=None,
                 base=None, base_fg=None, on_fg=None, **kw):
        try:
            parent_bg = master.cget("bg")
        except tk.TclError:
            parent_bg = C["panel"]
        super().__init__(master, highlightthickness=0, bd=0, bg=parent_bg, cursor="hand2", **kw)
        self._text, self._padx, self._pady, self._chars = str(text), 10, 5, width
        self._font = font or (FONT.ui, 10, "bold")
        self.on_fg = on_fg
        self.base, self.base_fg = base, base_fg          # e.g. base=C["tx"] for a red button
        self.command = command
        self.on = False
        self.on_color = on_color or C["on"]
        self._hover = False
        self.bind("<Button-1>", lambda e: self.command and self.command())
        self.bind("<Enter>", lambda e: self._set_hover(True))
        self.bind("<Leave>", lambda e: self._set_hover(False))
        self._fit()
        self._paint()

    # ---- the same options a Label button had ----
    def configure(self, cnf=None, **kw):
        if cnf is None and not kw:
            return super().configure()
        kw = dict(cnf or {}, **kw)
        changed = False
        for key, attr in (("text", "_text"), ("padx", "_padx"), ("pady", "_pady"), ("font", "_font")):
            if key in kw:
                v = kw.pop(key)
                setattr(self, attr, str(v) if key == "text" else v)
                changed = True
        if "width" in kw and not isinstance(kw["width"], str) and kw["width"] is not None and kw["width"] < 60:
            self._chars = kw.pop("width")             # a Label's width was in characters
            changed = True
        for k in ("fg", "foreground"):
            if k in kw:
                self.base_fg = kw.pop(k)
                changed = True
        if kw:
            super().configure(**kw)
        if changed:
            self._fit()
            self._paint()

    config = configure

    def cget(self, key):
        if key == "text":
            return self._text
        if key in ("padx", "pady"):
            return getattr(self, "_" + key)
        return super().cget(key)

    def set_on(self, on, color=None):
        self.on = bool(on)
        if color:
            self.on_color = color
        self._paint()

    # ---- drawing ----
    def _tkfont(self):
        f = self._fonts.get(self._font)
        if f is None:
            f = self._fonts[self._font] = tkfont.Font(font=self._font)
        return f

    def _fit(self):
        f = self._tkfont()
        lines = self._text.split("\n")
        tw = max(f.measure(t) for t in lines) if lines else 0
        if self._chars:
            tw = max(tw, f.measure("0") * self._chars)
        th = f.metrics("linespace") * len(lines)
        self._bw, self._bh = int(tw + 2 * self._padx + 4), int(th + 2 * self._pady + 4)
        super().configure(width=self._bw, height=self._bh)

    @staticmethod
    def _dark():
        bg = C["bg"]
        return sum(int(bg[i:i + 2], 16) for i in (1, 3, 5)) < 3 * 100

    def _set_hover(self, on):
        self._hover = on
        self._paint()

    def _paint(self):
        dark = self._dark()
        neutral_base = "#2a3646" if dark else "#e8eef4"
        on = self.on
        if on:
            col, fg = self.on_color, self.on_fg or "#ffffff"
        else:
            col, fg = self.base or neutral_base, self.base_fg or C["fg"]
        neutral = not on and not self.base
        if self._hover and not on:
            col = hex_mix(col, "#ffffff", 0.12) if not dark or not neutral else hex_mix(col, "#ffffff", 0.10)
        if on:                                    # pressed in: solid, a little darker at the top
            top, bot = hex_mix(col, "#000000", 0.12), col
        elif neutral:
            top, bot = ((hex_mix(col, "#ffffff", 0.18), hex_mix(col, "#000000", 0.25)) if dark
                        else (hex_mix(col, "#ffffff", 0.65), hex_mix(col, "#000000", 0.10)))
        else:                                     # coloured buttons stay solid: a slight sheen only
            top, bot = hex_mix(col, "#ffffff", 0.12), hex_mix(col, "#000000", 0.08)
        self.delete("all")
        w, h, r = self._bw - 2, self._bh - 3, self.RADIUS
        x0, y0 = (1, 2) if on else (0, 0)
        if not on:                                # drop shadow
            self._rrect(1, 2, w, h, r, fill=hex_mix(self.cget("bg"), "#000000", 0.45 if dark else 0.18), outline="")
        for i in range(h):
            d = 0.0
            if i < r:
                d = r - (r * r - (r - i) ** 2) ** 0.5
            elif i > h - r:
                d = r - max(0.0, r * r - (i - (h - r)) ** 2) ** 0.5
            self.create_line(x0 + d, y0 + i, x0 + w - d, y0 + i, fill=hex_mix(top, bot, i / max(1, h - 1)))
        self._rrect(x0, y0, w, h, r, fill="", outline=hex_mix(col, "#000000", 0.35))
        if not on:
            hi = hex_mix(col, "#ffffff", 0.3 if dark else 1.0) if neutral else hex_mix(col, "#ffffff", 0.35)
            self.create_line(x0 + r, y0 + 1, x0 + w - r, y0 + 1, fill=hi)
        self.create_text(x0 + w / 2, y0 + h / 2, text=self._text, fill=fg, font=self._font, justify="center")

    def _rrect(self, x, y, w, h, r, **kw):
        pts = [x + r, y, x + w - r, y, x + w, y, x + w, y + r, x + w, y + h - r, x + w, y + h,
               x + w - r, y + h, x + r, y + h, x, y + h, x, y + h - r, x, y + r, x, y]
        return self.create_polygon(pts, smooth=True, **kw)


class Tooltip:
    """Small text box that appears after the mouse rests on a widget for a moment."""
    DELAY_MS = 500

    def __init__(self, widget, text):
        self.widget, self.text, self.job, self.tip = widget, text, None, None
        widget.bind("<Enter>", self._schedule, add="+")
        widget.bind("<Leave>", self._hide, add="+")
        widget.bind("<ButtonPress>", self._hide, add="+")

    def _schedule(self, e=None):
        self._hide()
        self.job = self.widget.after(self.DELAY_MS, self._show)

    def _show(self):
        self.job = None
        if not self.widget.winfo_exists():
            return
        x = self.widget.winfo_rootx() + 8
        y = self.widget.winfo_rooty() + self.widget.winfo_height() + 4
        self.tip = tw = tk.Toplevel(self.widget)
        tw.overrideredirect(True)
        tw.attributes("-topmost", True)
        tk.Label(tw, text=self.text() if callable(self.text) else self.text, bg="#ffffe0", fg="#000000", relief="solid", borderwidth=1,
                 padx=6, pady=2, font=(FONT.ui, 9)).pack()
        tw.geometry(f"+{x}+{y}")

    def _hide(self, e=None):
        if self.job:
            try:
                self.widget.after_cancel(self.job)
            except tk.TclError:
                pass
            self.job = None
        if self.tip is not None:
            try:
                self.tip.destroy()
            except tk.TclError:
                pass
            self.tip = None


class Segmented(tk.Frame):
    def __init__(self, master, options, command, bg=None):
        super().__init__(master, bg=bg or C["panel"])
        self.buttons = {}
        for label, value in options:
            b = FlatButton(self, label, command=lambda v=value: command(v), font=(FONT.ui, 9, "bold"))
            b.config(padx=7)
            b.pack(side="left", padx=(0, 2))
            self.buttons[value] = b

    def set(self, value):
        for v, b in self.buttons.items():
            b.set_on(v == value)


def hex_mix(a, b, t):
    """Colour between a and b ("#rrggbb"), t = 0..1."""
    a = [int(a[i:i + 2], 16) for i in (1, 3, 5)]
    b = [int(b[i:i + 2], 16) for i in (1, 3, 5)]
    return "#%02x%02x%02x" % tuple(int(x + (y - x) * t) for x, y in zip(a, b))


class BarMeter(tk.Canvas):
    """Horizontal bar meter with a number scale underneath (HUD look, same as the mini meter).
    zones = ((up_to_fraction, HUD colour name), ...) colours the bar by level (S-meter)."""
    BAR_Y0, BAR_Y1 = 6, 18

    def __init__(self, master, label, width=290, zone=None, ticks=None, zones=None):
        self.tick_font = tkfont.Font(family=FONT.ui, size=7)
        # canvas sizes are in pixels but fonts follow Windows display scaling, so scale to match
        k = max(1.0, float(master.tk.call("tk", "scaling")) / (96 / 72))
        width = int(width * k)
        height = self.BAR_Y1 + 5 + self.tick_font.metrics("linespace") + 2
        super().__init__(master, width=width, height=height, bg=HUD["panel"], highlightthickness=0)
        self.w = width
        self.x0, self.x1 = int(48 * k), width - int(62 * k)
        self.zones = zones
        ym = (self.BAR_Y0 + self.BAR_Y1) / 2
        self.label = label
        self.create_text(4, ym, text=label, anchor="w", fill=HUD["label"], font=(FONT.ui, 10, "bold"))
        self.create_rectangle(self.x0, self.BAR_Y0, self.x1, self.BAR_Y1, fill=HUD["track"],
                              outline=HUD["track_edge"])
        self.segs = [self.create_rectangle(0, 0, 0, 0, outline="", state="hidden") for _ in range(3)]
        self.shine = self.create_line(0, 0, 0, 0, fill="#ffffff", state="hidden")
        self.zone_line = self.create_line(0, 2, 0, self.BAR_Y1 + 4, fill=HUD["tick"], dash=(2, 2), state="hidden")
        self.txt = self.create_text(width - 4, ym, text="--", anchor="e", fill=HUD["value"], font=(FONT.mono, 11, "bold"))
        self.last = (0, "--", None, False)
        self.set_ticks(ticks or [])
        self.set_zone(zone)

    def set_ticks(self, ticks):
        self.ticks = list(ticks)
        self.delete("tick")
        for frac, label in ticks:
            x = self.x0 + (self.x1 - self.x0) * frac
            self.create_line(x, self.BAR_Y1, x, self.BAR_Y1 + 4, fill=HUD["tick"], tags="tick")
            anchor = "nw" if frac <= 0 else ("ne" if frac >= 1 else "n")
            self.create_text(x, self.BAR_Y1 + 4, text=label, anchor=anchor, fill=HUD["tick_txt"],
                             font=self.tick_font, tags="tick")

    def set_zone(self, frac):
        self.zone = frac
        if frac:
            x = self.x0 + (self.x1 - self.x0) * frac
            self.coords(self.zone_line, x, 2, x, self.BAR_Y1 + 4)
            self.itemconfig(self.zone_line, state="normal")
        else:
            self.itemconfig(self.zone_line, state="hidden")

    def set(self, frac, text, color=None, dim=False):
        self.last = (frac, text, color, dim)
        frac = max(0.0, min(1.0, frac))
        x0, x1, y0, y1 = self.x0 + 1, self.x1 - 1, self.BAR_Y0 + 1, self.BAR_Y1
        end = x0 + (x1 - x0) * frac
        if dim:
            zones = ((1.0, HUD["bar_dim"]),)
        elif self.zones:
            zones = tuple((upto, HUD[c]) for upto, c in self.zones)
        else:
            zones = ((1.0, color or HUD["green"]),)
        start, top_col = x0, None
        for n, seg in enumerate(self.segs):
            if n < len(zones):
                upto, col = zones[n]
                zx = x0 + (x1 - x0) * upto
                a, b = start, min(end, zx)
                start = zx
                if b > a:
                    self.coords(seg, a, y0, b, y1)
                    self.itemconfig(seg, fill=col, state="normal")
                    top_col = col
                    continue
            self.itemconfig(seg, state="hidden")
        if top_col and end > x0 + 1:           # thin bright line on top = "glass" shine
            self.coords(self.shine, x0, y0, end, y0)
            self.itemconfig(self.shine, fill=hex_mix(top_col, "#ffffff", 0.55), state="normal")
        else:
            self.itemconfig(self.shine, state="hidden")
        self.itemconfig(self.txt, text=text, fill=HUD["value_dim"] if dim else HUD["value"])


class LevelBar(tk.Canvas):
    """Level bar in the HUD look: name and value above, bar below.
    Click or drag to set, mouse wheel for +/-1.
    Calls command(value) only for changes you make, never for set()."""
    FILL = "#2b8bff"

    def __init__(self, master, command, width=186, unit="", name="", color=None):
        k = max(1.0, float(master.tk.call("tk", "scaling")) / (96 / 72))
        width = int(width * k)
        vfont = tkfont.Font(family=FONT.mono, size=11, weight="bold")
        top = vfont.metrics("linespace")
        self.Y0, self.Y1 = top + 4, top + 15
        super().__init__(master, width=width, height=self.Y1 + 6, bg=HUD["panel"],
                         highlightthickness=0, cursor="hand2")
        self.command, self.unit = command, unit
        self.color = color or self.FILL
        self.x0, self.x1 = 4, width - 5
        self.max, self.value, self.dragging = 100, 0, False
        self.create_text(self.x0, top / 2 + 1, text=name.upper(), anchor="w", fill=HUD["label"],
                         font=(FONT.ui, 8, "bold"))
        self.create_rectangle(self.x0, self.Y0, self.x1, self.Y1, fill=HUD["track"], outline=HUD["track_edge"])
        self.fill = self.create_rectangle(self.x0, self.Y0 + 1, self.x0, self.Y1, fill=self.color, outline="")
        self.shine = self.create_line(self.x0, self.Y0 + 1, self.x0, self.Y0 + 1, fill=hex_mix(self.color, "#ffffff", 0.55))
        self.knob = self.create_rectangle(0, self.Y0 - 3, 0, self.Y1 + 3, fill="#ffffff", outline="")
        self.txt = self.create_text(self.x1, top / 2 + 1, anchor="e", fill=HUD["value"], font=vfont)
        self.bind("<ButtonPress-1>", self._press)
        self.bind("<B1-Motion>", self._press)
        self.bind("<ButtonRelease-1>", lambda e: setattr(self, "dragging", False))
        self.bind("<MouseWheel>", lambda e: self._change(self.value + (1 if e.delta > 0 else -1)))
        self.bind("<Button-4>", lambda e: self._change(self.value + 1))
        self.bind("<Button-5>", lambda e: self._change(self.value - 1))
        self._draw()

    def _draw(self):
        frac = self.value / self.max if self.max else 0
        x = self.x0 + (self.x1 - self.x0) * frac
        self.coords(self.fill, self.x0 + 1, self.Y0 + 1, x, self.Y1)
        self.coords(self.shine, self.x0 + 1, self.Y0 + 1, x, self.Y0 + 1)
        self.coords(self.knob, x - 2, self.Y0 - 3, x + 3, self.Y1 + 3)
        self.itemconfig(self.txt, text=f"{self.value}{self.unit}")

    def _press(self, e):
        self.dragging = True
        frac = (e.x - self.x0) / max(1, self.x1 - self.x0)
        self._change(round(frac * self.max))

    def _change(self, v):
        v = max(0, min(self.max, int(v)))
        if v != self.value:
            self.value = v
            self._draw()
            self.command(v)

    def set(self, v):                      # from the radio; ignored while you're dragging
        if not self.dragging:
            self.value = max(0, min(self.max, int(round(v))))
            self._draw()

    def get(self):
        return self.value

    def set_max(self, m):
        self.max = max(1, int(m))
        self.value = min(self.value, self.max)
        self._draw()


class FreqDisplay(tk.Canvas):
    """Frequency readout where each digit is a button: click the top half to
    raise that digit by one, the bottom half to lower it. Holding repeats, and
    the mouse wheel over a digit steps it too."""
    PLACES = [10_000_000, 1_000_000, 100_000, 10_000, 1_000, 100, 10, 1]
    PATTERN = "DD.DDD.DDD"

    def __init__(self, master, on_change, size=34):
        self.font = tkfont.Font(family=FONT.mono, size=size, weight="bold")
        self.cw = self.font.measure("0")
        self.h = self.font.metrics("linespace") + 6
        super().__init__(master, width=self.cw * len(self.PATTERN) + 8, height=self.h,
                         bg=HUD["panel"], highlightthickness=0, cursor="hand2")
        self.on_change = on_change
        self.hz = None
        self.hover = None          # (cell index, +1/-1)
        self.repeat_job = None
        self.hl = self.create_rectangle(0, 0, 0, 0, fill=HUD["track_edge"], outline="", state="hidden")
        self.arrow = self.create_text(0, 0, text="", fill=HUD["hint"], font=(FONT.ui, 8), state="hidden")
        self.cells, self.digit_items = [], []
        x, idx = 4, 0
        for ch in self.PATTERN:
            cx = x + self.cw / 2
            if ch == "D":
                self.cells.append((x, x + self.cw, self.PLACES[idx]))
                self.digit_items.append(self.create_text(cx, self.h / 2, text="-", font=self.font, fill=HUD["value"]))
                idx += 1
            else:
                self.create_text(cx, self.h / 2, text=".", font=self.font, fill=HUD["value"])
            x += self.cw
        self.bind("<Motion>", self._motion)
        self.bind("<Leave>", lambda e: self._set_hover(None))
        self.bind("<ButtonPress-1>", self._press)
        self.bind("<ButtonRelease-1>", lambda e: self._stop_repeat())
        self.bind("<MouseWheel>", lambda e: self._wheel(e, 1 if e.delta > 0 else -1))
        self.bind("<Button-4>", lambda e: self._wheel(e, 1))
        self.bind("<Button-5>", lambda e: self._wheel(e, -1))

    def set(self, hz):
        self.hz = None if hz is None else int(round(hz))
        if self.hz is None:
            for item in self.digit_items:
                self.itemconfig(item, text="-")
            return
        s = f"{max(0, min(self.hz, 99_999_999)):08d}"
        for i, (item, ch) in enumerate(zip(self.digit_items, s)):
            blank = i == 0 and ch == "0"          # no leading zero below 10 MHz
            self.itemconfig(item, text=" " if blank else ch)

    def _hit(self, e):
        for i, (x0, x1, _) in enumerate(self.cells):
            if x0 <= e.x < x1:
                return i, (1 if e.y < self.h / 2 else -1)
        return None

    def _set_hover(self, hit):
        self.hover = hit
        if not hit:
            self.itemconfig(self.hl, state="hidden")
            self.itemconfig(self.arrow, state="hidden")
            return
        x0, x1, _ = self.cells[hit[0]]
        y0, y1 = (0, self.h / 2) if hit[1] > 0 else (self.h / 2, self.h)
        self.coords(self.hl, x0, y0, x1, y1)
        self.itemconfig(self.hl, state="normal")
        self.tag_lower(self.hl)
        self.coords(self.arrow, (x0 + x1) / 2, 6 if hit[1] > 0 else self.h - 6)
        self.itemconfig(self.arrow, text="▲" if hit[1] > 0 else "▼", state="normal")

    def _motion(self, e):
        hit = self._hit(e)
        if hit != self.hover:
            self._set_hover(hit)

    def _step(self, hit):
        if self.hz is None or not hit:
            return
        self.on_change(self.hz + hit[1] * self.cells[hit[0]][2])

    def _press(self, e):
        hit = self._hit(e)
        self._step(hit)
        self._stop_repeat()
        if hit:
            self.repeat_job = self.after(FREQ_REPEAT_DELAY_MS, lambda: self._repeat(hit))

    def _repeat(self, hit):
        self._step(hit)
        self.repeat_job = self.after(FREQ_REPEAT_MS, lambda: self._repeat(hit))

    def _stop_repeat(self):
        if self.repeat_job:
            self.after_cancel(self.repeat_job)
            self.repeat_job = None

    def _wheel(self, e, direction):
        hit = self._hit(e)
        if hit:
            self._step((hit[0], direction))


def panel(master, **kw):
    """Plain bordered panel (rows without a title)."""
    return tk.Frame(master, bg=C["panel"], highlightthickness=1, highlightbackground=C["border"],
                    highlightcolor=C["border"], **kw)


def label(master, text, bold=True, size=10, **kw):
    """FastChat-style field label: 'Rig:' in bold."""
    kw.setdefault("bg", master.cget("bg"))
    kw.setdefault("fg", C["fg"])
    return tk.Label(master, text=text, font=(FONT.ui, size, "bold" if bold else "normal"), **kw)


def checkbox(master, text, var, command=None):
    return tk.Checkbutton(master, text=text, variable=var, command=command, bg=master.cget("bg"), fg=C["fg"],
                          selectcolor=C["field"], activebackground=master.cget("bg"), activeforeground=C["fg"],
                          highlightthickness=0, font=(FONT.ui, 9, "bold"))


def section(master, title):
    f = tk.Frame(master, bg=C["panel"], padx=10, pady=8)
    f.config(highlightthickness=1, highlightbackground=C["border"], highlightcolor=C["border"])
    head = tk.Frame(f, bg=C["panel"])
    head.pack(fill="x", pady=(0, 6))
    tk.Frame(head, bg=C["accent"], width=3).pack(side="left", fill="y", padx=(0, 8))
    tk.Label(head, text=title.upper(), bg=C["panel"], fg=C["title"], font=(FONT.ui, 13, "bold")).pack(side="left")
    return f


def small_label(master, text, bg=None, fg=None):
    """Bold capitals in the title red in front of a row of buttons ("BAND", "MODE")."""
    return tk.Label(master, text=text.upper(), bg=bg or master.cget("bg"), fg=fg or C["title"], font=(FONT.ui, 10, "bold"))


def popup_menu(menu, x, y):
    """Open a drop-down / right-click menu at x, y (screen pixels).
    Windows: tk_popup waits until the menu closes, then the grab is released (the usual recipe).
    Linux / X11: tk_popup returns at once - releasing the grab there meant a click outside could
    no longer close the menu (it stayed open until you picked something). Leave Tk's grab alone."""
    menu.bind("<Escape>", lambda e: menu.unpost())
    if SYS == "Windows":
        try:
            menu.tk_popup(x, y)
        finally:
            menu.grab_release()
    else:
        menu.tk_popup(x, y)


def screen_bounds(widget):
    """(left, top, right, bottom) of the whole desktop, all monitors on Windows."""
    if SYS == "Windows":
        try:
            import ctypes
            gm = ctypes.windll.user32.GetSystemMetrics
            x, y = gm(76), gm(77)                  # SM_XVIRTUALSCREEN, SM_YVIRTUALSCREEN
            return x, y, x + gm(78), y + gm(79)    # SM_CXVIRTUALSCREEN, SM_CYVIRTUALSCREEN
        except Exception:
            pass
    return 0, 0, widget.winfo_screenwidth(), widget.winfo_screenheight()
