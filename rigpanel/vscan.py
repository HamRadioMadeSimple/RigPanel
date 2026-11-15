"""FT-891 VFO Scan window: starts / stops the radio's own scan and sets its squelch (1.4.2, 27f)."""
from .core import *  # noqa: F401,F403
from .tables import *  # noqa: F401,F403
from .radios import *  # noqa: F401,F403
from .worker import *  # noqa: F401,F403
from .widgets import *  # noqa: F401,F403
from .waterfall import *  # noqa: F401,F403
from .freqlist import *  # noqa: F401,F403
from .minis import *  # noqa: F401,F403

VSCAN_GOLD = "#f2c14e"
VSCAN_KEY = dict(base="#1b2a3a", base_fg="#dbe5ee")


class VfoScan(tk.Toplevel):
    """Floating, always-on-top window in the HUD look (FT-891 only). The radio does the scanning;
    this window sends SC / SQ0 / EX0516 through the worker and shows what the radio reports."""
    TICK_MS = 250                 # frequency on screen
    STATE_MS = 500                # scan state read from the radio
    STILL_S = 1.0                 # scanning, but the frequency hasn't moved this long = the radio stopped on a station
    SAME_HZ = 2000                # stops this close together are the same station
    ROWS = 8                      # HEARD rows on screen (the list scrolls)

    def __init__(self, app):
        super().__init__(app.root)
        self.app = app
        self.withdraw()
        self.overrideredirect(True)
        self.attributes("-topmost", True)
        self.state_ = None            # "up" / "down" / "stop" as the radio reports it
        self.sql = None
        self.resume = None            # 0 PAUSE (stay), 1 TIME (5 s)
        self.drag = None
        self._jobs = {}
        self.start = app.cfg.get("vscan_start", "edge")
        self.cls = app.cfg.get("scan_class") if app.cfg.get("scan_class") in LICENSE_CLASSES else "Extra"
        self.end = app.cfg.get("vscan_end", "round")
        self.limits = None            # (band, lo, hi) Hz of the segment being scanned
        self.edge_busy = False        # turning round / stopping at the edge: wait for the radio
        if not hasattr(app, "vscan_heard"):
            app.vscan_heard = {}      # hz -> dict(hz, t, n, dir): kept while RigPanel runs
        self.heard = app.vscan_heard
        self.still = (None, 0.0, False)   # (frequency, since, already listed)
        self.rows = []

        self.config(bg=HUD["edge"])
        body = tk.Frame(self, bg=HUD["bottom"])
        body.pack(fill="both", expand=True, padx=2, pady=2)
        top = tk.Frame(body, bg=HUD["top"])
        top.pack(fill="x")
        self._lab(top, "VFO SCAN", VSCAN_GOLD, 13, bg=HUD["top"]).pack(side="left", padx=12, pady=6)
        self._lab(top, getattr(app.profile, "name", ""), HUD["hint"], 9, bg=HUD["top"]).pack(side="left")
        FlatButton(top, "EXIT", command=self.close, base="#3a1414", base_fg="#ff8a80",
                   font=(FONT.ui, 9, "bold")).pack(side="right", padx=8, pady=4)

        mid = tk.Frame(body, bg=HUD["bottom"])
        mid.pack(fill="x", padx=14, pady=(8, 0))
        self.status = self._lab(mid, "STOPPED", HUD["hint"], 10)
        self.status.grid(row=0, column=0, sticky="w")
        # click or scroll a digit to fine-tune (stops the scan) - SSB scan stops are only close (27p)
        self.fd = FreqDisplay(mid, self._dial, size=24)
        self.fd.config(bg=HUD["bottom"])
        self.fd.grid(row=1, column=0, sticky="w")
        Tooltip(self.fd, "Click the top / bottom of a digit (or scroll it) to tune up / down - stops the scan")
        self.mode_lbl = self._lab(mid, "", HUD["hint"], 10)
        self.mode_lbl.grid(row=1, column=1, sticky="e", padx=(30, 0))
        self.range_lbl = self._lab(mid, "", HUD["tick"], 9)
        self.range_lbl.grid(row=2, column=0, columnspan=2, sticky="w")
        mid.columnconfigure(0, weight=1)

        row = tk.Frame(body, bg=HUD["bottom"])
        row.pack(fill="x", padx=14, pady=10)
        self.btn = {}
        for key, text in (("down", "▼  Down"), ("stop", "■  Stop"), ("up", "▲  Up")):
            b = FlatButton(row, text, command=lambda k=key: self.cmd(k), font=(FONT.ui, 11, "bold"),
                           on_color="#2ee06e", on_fg="#04110a", **VSCAN_KEY)
            b.config(padx=18, pady=8)
            b.pack(side="left", padx=(0, 8))
            self.btn[key] = b

        sq = tk.Frame(body, bg=HUD["bottom"])
        sq.pack(fill="x", padx=14, pady=(4, 0))
        self._lab(sq, "SQUELCH", HUD["label"], 9).pack(side="left")
        FlatButton(sq, "◀", command=lambda: self.set_sql((self.sql or 0) - 5), **VSCAN_KEY).pack(side="left", padx=(10, 4))
        self.sql_cv = tk.Canvas(sq, width=170, height=14, bg=HUD["track"], highlightthickness=1,
                                highlightbackground=HUD["track_edge"], cursor="hand2")
        self.sql_cv.pack(side="left")
        self.sql_cv.bind("<Button-1>", self._sql_click)
        self.sql_cv.bind("<B1-Motion>", self._sql_click)
        self.sql_cv.bind("<ButtonRelease-1>", self._sql_release)
        for w in (self.sql_cv, self):
            w.bind("<MouseWheel>", lambda e: self.set_sql((self.sql or 0) + (1 if e.delta > 0 else -1)))
        FlatButton(sq, "▶", command=lambda: self.set_sql((self.sql or 0) + 5), **VSCAN_KEY).pack(side="left", padx=4)
        self.sql_lbl = self._lab(sq, "--", HUD["value"], 12, mono=True)
        self.sql_lbl.pack(side="left", padx=6)

        rs = tk.Frame(body, bg=HUD["bottom"])
        rs.pack(fill="x", padx=14, pady=(10, 0))
        self._lab(rs, "ON A SIGNAL", HUD["label"], 9).pack(side="left")
        self.res_btn = {}
        for v, text in ((1, "Wait 5 s, go on"), (0, "Stay until it ends")):
            b = FlatButton(rs, text, command=lambda v=v: self.set_resume(v), font=(FONT.ui, 9, "bold"),
                           on_color="#4da3ff", **VSCAN_KEY)
            b.pack(side="left", padx=(8, 0))
            self.res_btn[v] = b

        st = tk.Frame(body, bg=HUD["bottom"])
        st.pack(fill="x", padx=14, pady=(10, 0))
        self._lab(st, "BEGIN AT", HUD["label"], 9).pack(side="left")
        self.start_btn = {}
        for v, text in (("here", "From here"), ("edge", "At the band edge")):
            b = FlatButton(st, text, command=lambda v=v: self.set_start(v), font=(FONT.ui, 9, "bold"),
                           on_color="#4da3ff", **VSCAN_KEY)
            b.pack(side="left", padx=(8, 0))
            self.start_btn[v] = b
        Tooltip(self.start_btn["edge"], "▲ starts at the bottom of the band's voice segment, ▼ at the top")

        # the scan stays inside the voice segment your license allows (US band plan, tables.VOICE_BANDS)
        lc = tk.Frame(body, bg=HUD["bottom"])
        lc.pack(fill="x", padx=14, pady=(10, 0))
        self._lab(lc, "LICENSE", HUD["label"], 9).pack(side="left")
        self.cls_btn = {}
        for v in LICENSE_CLASSES:
            b = FlatButton(lc, v, command=lambda v=v: self.set_class(v), font=(FONT.ui, 9, "bold"),
                           on_color="#4da3ff", **VSCAN_KEY)
            b.pack(side="left", padx=(8, 0))
            self.cls_btn[v] = b
        self._lab(lc, "AT THE END", HUD["label"], 9).pack(side="left", padx=(16, 0))
        self.end_btn = {}
        for v, text in (("round", "Go round"), ("stop", "Stop")):
            b = FlatButton(lc, text, command=lambda v=v: self.set_end(v), font=(FONT.ui, 9, "bold"),
                           on_color="#4da3ff", **VSCAN_KEY)
            b.pack(side="left", padx=(8, 0))
            self.end_btn[v] = b
        Tooltip(self.end_btn["round"], "At the end of the voice segment: start again at the other end")

        hd = tk.Frame(body, bg=HUD["bottom"])
        hd.pack(fill="x", padx=14, pady=(12, 2))
        self.heard_lbl = self._lab(hd, "HEARD", VSCAN_GOLD, 10)
        self.heard_lbl.pack(side="left")
        self._lab(hd, "click = go there", HUD["tick"], 8, bold=False).pack(side="left", padx=8)
        FlatButton(hd, "Clear", command=self.clear_heard, font=(FONT.ui, 8, "bold"), **VSCAN_KEY).pack(side="right")
        lf = tk.Frame(body, bg=HUD["edge"])
        lf.pack(fill="x", padx=14)
        self.lst = tk.Listbox(lf, height=self.ROWS, bg=HUD["panel"], fg=HUD["value"], font=(FONT.mono, 12, "bold"),
                              selectbackground="#1d3a5c", selectforeground="#ffffff", activestyle="none",
                              highlightthickness=0, bd=0, relief="flat", exportselection=False, cursor="hand2")
        sb = tk.Scrollbar(lf, orient="vertical", command=self.lst.yview, bg=HUD["top"], troughcolor=HUD["track"],
                          activebackground=HUD["grip"], highlightthickness=0, bd=0, width=14)
        self.lst.config(yscrollcommand=sb.set)
        self.lst.pack(side="left", fill="both", expand=True, padx=(1, 0), pady=1)
        sb.pack(side="right", fill="y", pady=1)
        self.lst.bind("<ButtonRelease-1>", self._row_click)
        self.lst.bind("<Button-3>", self._row_forget)

        self._lab(body, "Raise squelch until the noise just goes quiet, then press ▲ or ▼.\n"
                        "Each station the radio stops on is listed. Right-click a row to remove it.",
                  HUD["tick"], 8, bold=False).pack(anchor="w", padx=14, pady=(8, 10))

        for w in (top, mid, self.status, self.mode_lbl, body):
            w.bind("<ButtonPress-1>", self._press)
            w.bind("<B1-Motion>", self._drag_move)
        self._show()

    def _lab(self, parent, text, fg, size, mono=False, bold=True, bg=None):
        return tk.Label(parent, text=text, fg=fg, bg=bg or HUD["bottom"], justify="left",
                        font=((FONT.mono if mono else FONT.ui), size, "bold" if bold else "normal"))

    # ---------------- opening / closing ----------------
    def open(self):
        self.update_idletasks()
        self.geometry("+%d+%d" % self._position())
        self.deiconify()
        self.lift()
        self.app.worker.submit(lambda w: w.vscan_read(all_=True))
        self._fill()
        self._after("tick", self.TICK_MS, self._tick)
        self._after("state", self.STATE_MS, self._state_tick)
        if SYS != "Windows":
            self._after("top", 2000, self._keep_on_top)

    def _after(self, name, ms, fn):
        try:
            self._jobs[name] = self.after(ms, fn)
        except tk.TclError:
            pass

    def close(self):
        """EXIT: stop the radio's scan, remember the place, close."""
        if self.state_ in ("up", "down"):
            self.app.worker.submit(lambda w: w.vscan_cmd("stop"))
        for job in self._jobs.values():
            try:
                self.after_cancel(job)
            except tk.TclError:
                pass
        self._jobs = {}
        try:
            self.app.cfg["vscan_pos"] = [self.winfo_x(), self.winfo_y()]
            save_config(self.app.cfg)
        except tk.TclError:
            pass
        self.app.vscan_win = None
        try:
            self.destroy()
        except tk.TclError:
            pass
        self.app.sync_vscan_button()

    def _position(self):
        pos = self.app.cfg.get("vscan_pos")
        w, h = self.winfo_reqwidth(), self.winfo_reqheight()
        if pos:
            x, y = pos
        else:
            r = self.app.root
            x, y = r.winfo_rootx() + 40, r.winfo_rooty() + 80
        left, top, right, bottom = screen_bounds(self)
        return max(left, min(x, right - w)), max(top, min(y, bottom - h))

    def _keep_on_top(self):
        if self.winfo_exists():
            self.lift()
            self._after("top", 2000, self._keep_on_top)

    def _press(self, e):
        self.drag = (e.x_root - self.winfo_x(), e.y_root - self.winfo_y())

    def _drag_move(self, e):
        if self.drag:
            self.geometry(f"+{e.x_root - self.drag[0]}+{e.y_root - self.drag[1]}")

    # ---------------- timers ----------------
    def _tick(self):
        """Frequency and mode from the normal poll (it follows the radio while it scans)."""
        if self.app.freq and not self.fd.repeat_job:
            self.fd.set(int(self.app.freq))
        self.mode_lbl.config(text=str(getattr(self.app, "mode", "") or ""))
        self._check_edge()
        self._watch_stop()
        if self.limits is None:
            self._show_range()                    # stopped: the range follows the dial
        self._after("tick", self.TICK_MS, self._tick)

    def _watch_stop(self):
        """While the radio scans, a frequency that stays put for STILL_S = it stopped on a station."""
        f, now = int(self.app.freq or 0), time.monotonic()
        if self.state_ not in ("up", "down") or not f:
            self.still = (None, now, False)
            return
        last, since, listed = self.still
        if f != last:
            self.still = (f, now, False)
        elif not listed and now - since >= self.STILL_S:
            self.still = (f, since, True)
            self._add_heard(f)

    def _dial(self, hz):
        """A digit clicked or scrolled: stop the scan (if it runs) and tune there."""
        if self.state_ in ("up", "down"):
            self.state_ = "stop"
            self.limits = None
            self._show()
            self.app.worker.submit(lambda w: w.vscan_cmd("stop"))
        self.app.tune_to(int(hz))

    def _add_heard(self, hz):
        raw = hz                                  # exact stop (27p rounded to whole kHz - operator preferred exact, 27q)
        if self.limits and not self.limits[1] <= hz <= self.limits[2]:
            return                                # outside your segment: not listed
        near = next((k for k in self.heard if abs(k - hz) <= self.SAME_HZ), None)
        e = self.heard.pop(near) if near is not None else {"n": 0}
        e.update(hz=hz, t=time.time(), n=e["n"] + 1, dir=self.state_)
        self.heard[hz] = e
        debug_log(f"VFO Scan: stopped on {raw} -> listed {hz} ({self.state_})")
        self._fill()

    def _fill(self):
        """The HEARD list, low to high; keeps where you've scrolled to."""
        top = self.lst.yview()[0]
        self.rows = sorted(self.heard)
        now = time.time()
        self.lst.delete(0, "end")
        for hz in self.rows:
            e = self.heard[hz]
            age = now - e["t"]
            ago = "now" if age < 60 else f"{int(age // 60)} min"
            arrow = "▲" if e.get("dir") == "up" else "▼"
            times = f"x{e['n']}" if e["n"] > 1 else ""
            self.lst.insert("end", f" {hz / 1000:9.1f} kHz  {arrow} {times:>3}  {ago:>6}")
        self.lst.yview_moveto(top)
        self.heard_lbl.config(text=f"HEARD ({len(self.rows)})" if self.rows else "HEARD")

    def _row_click(self, e):
        i = self.lst.nearest(e.y)
        if 0 <= i < len(self.rows):
            hz = self.rows[i]
            self.state_ = "stop"                  # no new HEARD entry while we go there
            self.limits = None
            self._show()
            self.app.worker.submit(lambda w: w.vscan_goto(hz))
            self.app.log(f"VFO Scan: stopped - went to {hz / 1000:.1f} kHz (fine-tune with the digits above)")

    def _row_forget(self, e):
        i = self.lst.nearest(e.y)
        if 0 <= i < len(self.rows):
            self.heard.pop(self.rows[i], None)
            self._fill()

    def clear_heard(self):
        self.heard.clear()
        self._fill()

    def _state_tick(self):
        self.app.worker.submit(lambda w: w.vscan_read())
        if int(time.time()) % 30 == 0:
            self._fill()                          # "now" -> "1 min"
        self._after("state", self.STATE_MS, self._state_tick)

    # ---------------- actions ----------------
    def cmd(self, c):
        if c == "stop":
            self.state_ = "stop"                  # at once: a stopped radio is not a station
            self.limits = None
            self._show()
            self.app.worker.submit(lambda w: w.vscan_cmd("stop"))
            return
        f = int(self.app.freq or 0)
        lim = self._segment(f)
        if lim is None:
            self.app.log("VFO Scan: tune into a band's voice segment first (160-10 m, not 60 m).")
            return
        self.limits, self.limits_dir = lim, c
        _, lo, hi = lim
        start = None
        if self.start == "edge" or not lo <= f <= hi:     # outside your segment: begin at its edge
            start = lo if c == "up" else hi
        self.edge_busy = False
        self._show()
        self.app.worker.submit(lambda w: w.vscan_cmd(c, start))

    def _segment(self, hz):
        """(band, lo, hi) of the voice segment for your license that the frequency is in or near."""
        band = voice_band_of(hz)
        if band is None or band == "60 m":
            return None
        lo, hi = voice_range(band, self.cls)
        return band, lo, hi

    def _check_edge(self):
        """The radio's scan doesn't know the band plan: at the segment's end, go round or stop."""
        f = int(self.app.freq or 0)
        if not self.limits or not f:
            self.edge_busy = False
            return
        _, lo, hi = self.limits
        if lo <= f <= hi:
            self.edge_busy = False
            return
        if self.edge_busy:
            return
        self.edge_busy = True
        d = self.state_ if self.state_ in ("up", "down") else self.limits_dir
        if self.end == "round":
            start = lo if d == "up" else hi
            self.app.worker.submit(lambda w: w.vscan_cmd(d, start))
            debug_log(f"VFO Scan: end of the segment at {f} - round to {start}")
        else:
            self.state_ = "stop"
            self.limits = None
            self._show()
            back = hi if f > hi else lo
            self.app.worker.submit(lambda w: (w.vscan_cmd("stop"), w.set_freq(back)))
            self.app.log("VFO Scan: end of the voice segment - stopped.")

    def set_class(self, v):
        self.cls = v
        self.app.cfg["scan_class"] = v
        save_config(self.app.cfg)
        if self.limits:
            self.limits = self._segment(int(self.app.freq or 0)) or self.limits
        self._show()

    def set_end(self, v):
        self.end = v
        self.app.cfg["vscan_end"] = v
        save_config(self.app.cfg)
        self._show()

    def set_sql(self, n):
        n = max(0, min(100, int(n)))
        self.sql = n
        self._show()
        self.app.worker.submit(lambda w: w.vscan_squelch(n))

    def _sql_click(self, e):
        w = max(1, self.sql_cv.winfo_width() - 2)
        self.sql = max(0, min(100, round(e.x * 100 / w)))
        self._show()

    def _sql_release(self, e):
        self.set_sql(self.sql or 0)

    def set_resume(self, v):
        self.resume = v
        self._show()
        self.app.worker.submit(lambda w: w.vscan_resume(v))

    def set_start(self, v):
        self.start = v
        self.app.cfg["vscan_start"] = v
        save_config(self.app.cfg)
        self._show()

    # ---------------- from the worker ----------------
    def on_vscan(self, d):
        if "scan" in d and d["scan"] is not None:
            if self.state_ in ("up", "down") and d["scan"] == "stop":
                self.limits = None                # the radio stopped (PTT, the dial, a click)
            self.state_ = d["scan"]
        if d.get("sql") is not None:
            self.sql = d["sql"]
        if d.get("resume") is not None:
            self.resume = d["resume"]
        self._show()

    def _show_range(self):
        seg = self.limits or self._segment(int(self.app.freq or 0))
        self.range_lbl.config(text=f"{seg[0]} voice, {self.cls}: {seg[1] / 1000:,.0f} - {seg[2] / 1000:,.0f} kHz"
                              if seg else "not in a voice segment - tune into one to scan")

    def _show(self):
        try:
            run = self.state_ in ("up", "down")
            arrow = {"up": "▲  up", "down": "▼  down"}.get(self.state_, "")
            self.status.config(text=f"SCANNING  {arrow}" if run else "STOPPED",
                               fg=VSCAN_GOLD if run else HUD["hint"])
            for k, b in self.btn.items():
                b.set_on(k == self.state_ and run)
            for v, b in self.res_btn.items():
                b.set_on(v == self.resume)
            for v, b in self.cls_btn.items():
                b.set_on(v == self.cls)
            for v, b in self.end_btn.items():
                b.set_on(v == self.end)
            self._show_range()
            for v, b in self.start_btn.items():
                b.set_on(v == self.start)
            self.sql_lbl.config(text="--" if self.sql is None else f"{self.sql:3d}")
            c = self.sql_cv
            c.delete("all")
            w = int(c.cget("width"))
            if self.sql:
                c.create_rectangle(0, 0, round(w * self.sql / 100), 16, fill=VSCAN_GOLD, width=0)
        except tk.TclError:
            pass
