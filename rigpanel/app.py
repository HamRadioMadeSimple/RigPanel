"""The main window (App): layout, actions, voice/data memory, macros, settings files."""
from .core import *  # noqa: F401,F403
from .tables import *  # noqa: F401,F403
from .radios import *  # noqa: F401,F403
from .worker import *  # noqa: F401,F403
from .widgets import *  # noqa: F401,F403
from .waterfall import *  # noqa: F401,F403
from .freqlist import *  # noqa: F401,F403
from .minis import *  # noqa: F401,F403
from .extras import *  # noqa: F401,F403
from .builder import *  # noqa: F401,F403

# --------------------------------------------------------------------------
# Main window
# --------------------------------------------------------------------------
class App(Extras):
    def __init__(self, root):
        self.root = root
        self.cfg = load_config()
        self.out_q = queue.Queue()
        self.worker = FlrigWorker(self.out_q)
        self.worker.start()

        self.profile = None
        self.xcvr = ""
        self.connected = False
        self.modes, self.bws = [], []
        self.freq = None
        self.mode = ""
        self.ptt = False
        self.pmax = 100.0
        self.touched = {}
        self.ctl_widgets = {}
        self.ctl_values = {}
        self.ctl_levels = {}          # e.g. {"nr": 7}: levels set from the \u25be menus
        self.pending_freq = None
        self.freq_job_queued = False
        self.slider_jobs = {}
        self.slider_prog = {}
        self.freq_win = None
        self.float_wf = None          # pop-out waterfall window (made on first use)
        self.wf_shown = bool(self.cfg.get("wf_show", False))
        self.macro_state = {}         # FT-891 menu values read from the radio
        self.ex_unsupported = set()   # menu items this radio won't do over CAT
        self.ab, self.other_hz, self.split = "A", None, False
        self.macro_busy = None
        self.macro_win = None
        self.vscan_win = None           # FT-891 VFO Scan window (gold Scan button)
        self.muted_vol = None           # AF Volume before MUTE (None = not muted)
        self.compact = False          # Compact View: main panel minimised, mini meter + waterfall only
        self.mini_before_compact = False
        self.last_swr = None
        self.levels = {}                       # last power/mic/rf/volume values (restored after a rebuild)
        self.last_status = ("wait", "Not connected")
        self.last_log = ""
        self.theme = self.cfg.get("theme", "Dark") if self.cfg.get("theme") in THEMES else "Dark"
        C.update(THEMES[self.theme])

        root.title(f"{APP_NAME} v{APP_VERSION} - IC-7300 / FT-891 via flrig")
        root.configure(bg=C["bg"])
        root.minsize(900, 300)
        self._style()
        self._build()
        self.mini = MiniMeter(self)
        self.mini_lv = MiniLevels(self)
        for key, action in self.HOTKEYS:
            root.bind_all(f"<Shift-{key}>", lambda e, a=action: self._hotkey(e, a))
        root.bind_all("<Control-w>", lambda e: self.toggle_float())
        root.bind_all("<Control-W>", lambda e: self.toggle_float())
        root.bind("<Map>", self._on_main_restored)
        root.protocol("WM_DELETE_WINDOW", self.close)
        root.after(50, self._pump)
        self._clock()
        self.start_ctrl_tap()                   # tap Ctrl alone: RigPanel forward / back (11-09b)
        if self.cfg.get("mini_always"):
            root.after(600, lambda: self.mini.show(manual=True))
        if self.cfg.get("lv_always") or self.cfg.get("lv_auto"):
            root.after(700, lambda: self.mini_lv.show(manual=bool(self.cfg.get("lv_always"))))
        self._update_audio()
        self.connect()

    def _clock(self):
        if getattr(self, "dead", False):
            return
        try:
            self.utc_val.config(text=time.strftime("%H:%M:%S", time.gmtime()))
        except tk.TclError:
            pass
        self.root.after(1000, self._clock)

    # ---------------- theme ----------------
    def apply_theme(self, name):
        """Switch Dark/Light live: rebuild the window in the new colours and put
        everything back (frequency, mode, filters, levels, mini meter, list window)."""
        if name not in THEMES or name == self.theme:
            return
        self.theme = name
        self.cfg["theme"] = name
        mini_vis, mini_manual = self.mini.visible(), self.mini.manual
        lv_vis, lv_manual = self.mini_lv.visible(), self.mini_lv.manual
        list_open = self.freq_win is not None and self.freq_win.winfo_exists()
        float_open = self.float_wf is not None and self.float_wf.visible()
        if float_open:
            self.float_wf.remember()
        self.float_wf = None
        if self.wf.ok:
            self.wf.save(self.cfg)
            self.wf.stop()
        self.mini.cancel_jobs()
        self.mini_lv.cancel_jobs()
        self.close_vscan()
        for w in self.root.winfo_children():
            w.destroy()
        self.freq_win = None
        self.mini = self.mini_lv = None        # destroyed above; new ones after _build (11-01a: the old ones broke the switch)
        C.update(THEMES[name])
        self.root.configure(bg=C["bg"])
        self._style()
        self._build()
        self.mini = MiniMeter(self)
        self.mini_lv = MiniLevels(self)
        self._restore_view()
        if mini_vis:
            self.mini.show(manual=mini_manual)
        if lv_vis:
            self.mini_lv.show(manual=lv_manual)
        if list_open:
            self.open_freq_list()
        if float_open:
            self.show_float()
        self._update_audio()
        save_config(self.cfg)
        self.log(f"Theme: {name}")

    def _restore_view(self):
        self._on_tables({"modes": self.modes, "bws": self.bws})
        if self.freq is not None:
            self.freq_disp.set(self.freq)
        self.mode_var.set(self.mode)
        if self.mode:
            self.vd.set(memory_kind(self.mode))
            self._mark_kind_buttons()
        self._status(*self.last_status)
        self.rig_val.config(text=self.xcvr or "--")
        self.sliders["power"].set_max(self.pmax)
        self.m_po.set_ticks(po_ticks(self.pmax))
        for k, v in self.levels.items():
            self.sliders[k].set(v)
        self.connect_btn.set_on(self.connected)
        self._show_vfo()
        self.ptt = None                         # forces TX/RX indicators to repaint on the next poll
        self._update_macro_row()

    # ---------------- layout ----------------
    def _style(self):
        st = ttk.Style()
        try:
            st.theme_use("clam")
        except tk.TclError:
            pass
        st.configure("TCombobox", fieldbackground=C["field"], background=C["btn"], foreground=C["fg"],
                     arrowcolor=C["fg"], bordercolor=C["btn_border"], lightcolor=C["field"], darkcolor=C["field"],
                     padding=2)
        st.map("TCombobox", fieldbackground=[("readonly", C["field"])], foreground=[("readonly", C["fg"])],
               selectbackground=[("readonly", C["field"])], selectforeground=[("readonly", C["fg"])],
               background=[("active", C["hover"])])
        self.root.option_add("*TCombobox*Font", (FONT.ui, 10, "bold"))
        rowh = tkfont.Font(family=FONT.ui, size=10).metrics("linespace") + 8
        st.configure("Freq.Treeview", background=C["field"], fieldbackground=C["field"], foreground=C["freq"],
                     rowheight=rowh, borderwidth=0, font=(FONT.mono, 10))
        st.map("Freq.Treeview", background=[("selected", C["on"])], foreground=[("selected", "#ffffff")])
        st.configure("Freq.Treeview.Heading", background=C["btn"], foreground=C["gold"], relief="flat",
                     font=(FONT.ui, 9, "bold"))
        st.map("Freq.Treeview.Heading", background=[("active", C["hover"])])
        for sb in ("Vertical.TScrollbar", "Horizontal.TScrollbar"):
            st.configure(sb, background=C["btn"], troughcolor=C["field"], arrowcolor=C["fg"],
                         bordercolor=C["border"], lightcolor=C["btn"], darkcolor=C["btn"], gripcount=0, arrowsize=14)
            st.map(sb, background=[("active", C["hover"]), ("pressed", C["on"])])
        self.root.option_add("*TCombobox*Listbox.selectForeground", "#ffffff")
        self.root.option_add("*TCombobox*Listbox.relief", "flat")
        self.root.option_add("*TCombobox*Listbox.borderWidth", 0)
        self.root.option_add("*TCombobox*Listbox.background", C["field"])
        self.root.option_add("*TCombobox*Listbox.foreground", C["fg"])
        self.root.option_add("*TCombobox*Listbox.selectBackground", C["on"])

    def _entry(self, master, width, value):
        e = tk.Entry(master, width=width, bg=C["field"], fg=C["fg"], insertbackground=C["fg"],
                     relief="flat", highlightthickness=1, highlightbackground=C["btn_border"],
                     highlightcolor=C["on"], font=(FONT.ui, 10, "bold"))
        e.insert(0, str(value))
        return e

    def _build(self):
        pad = dict(padx=8, pady=(8, 0))
        r = self.root

        # --- header band (shared look with the other station apps)
        hdr = tk.Frame(r, bg=C["header"], padx=16, pady=12)
        hdr.pack(fill="x")
        hk = dict(bg=C["header"], fg=C["header_fg"])
        # right-hand buttons first, so a narrow window squeezes the text, never the buttons
        go = dict(on_color=C["go"], on_fg=C["go_fg"])
        self.tune_btn = FlatButton(hdr, "TUNE", command=self.tune, font=(FONT.ui, 11, "bold"), base=C["tx"],
                                   base_fg="#ffffff", on_color="#ff2020")
        self.connect_btn = FlatButton(hdr, "Connect", command=self.connect, font=(FONT.ui, 11, "bold"), **go)
        self.mini_btn = FlatButton(hdr, "Mini Meter", command=lambda: self.mini.toggle(), font=(FONT.ui, 11, "bold"), **go)
        for i, b in enumerate((self.tune_btn, self.connect_btn, self.mini_btn)):
            b.config(padx=16, pady=9)
            b.pack(side="right", padx=(0, 0 if i == 0 else 6))
        # FT-891 only (show_scan_button): opens the VFO Scan window - the radio's own scan
        self.scan_btn = FlatButton(hdr, "Scan", command=self.toggle_vscan, font=(FONT.ui, 11, "bold"),
                                   base=THEMES["Dark"]["gold"],        # same bright gold in both themes
                                   base_fg="#1a1200", on_color="#ffd75e", on_fg="#1a1200")
        self.scan_btn.config(padx=16, pady=9)

        try:                                   # app icon left of the name (skipped if the file is missing)
            self._hdr_icon = tk.PhotoImage(file=os.path.join(RES_DIR, "icon_small.png"))
            tk.Label(hdr, image=self._hdr_icon, bg=C["header"]).pack(side="left", padx=(0, 10))
        except (tk.TclError, OSError):
            self._hdr_icon = None
        tk.Label(hdr, text=APP_NAME, font=(FONT.ui, 20, "bold"), **hk).pack(side="left")
        tk.Label(hdr, text=f"v{APP_VERSION}", font=(FONT.mono, 12, "bold"), **hk).pack(side="left", padx=(10, 20), pady=(6, 0))

        def hval(name, width):
            box = tk.Frame(hdr, bg=C["header"])
            box.pack(side="left", padx=(0, 14))
            tk.Label(box, text=name.upper(), font=(FONT.ui, 8, "bold"), bg=C["header"], fg="#9fb3c8").pack(anchor="w")
            v = tk.Label(box, text="--", width=width, anchor="w", font=(FONT.mono, 13, "bold"),
                         bg=C["header"], fg=C["header_val"])
            v.pack(anchor="w")
            return v
        self.flrig_val = hval("flrig", 9)
        self.rig_val = hval("Rig", 7)
        self.utc_val = hval("UTC", 8)

        tk.Frame(r, bg=C["accent"], height=2).pack(fill="x")       # thin accent line under the header

        # --- toolbar row: Label: [value] pairs
        tb = tk.Frame(r, bg=C["bg"], padx=10, pady=8)
        tb.pack(fill="x")
        label(tb, "Rig:").pack(side="left")
        self.rig_var = tk.StringVar(value=self.cfg.get("rig", "Auto-detect"))
        rig_combo = self.rig_combo = ttk.Combobox(tb, textvariable=self.rig_var, values=self.rig_combo_values(), width=14,
                                                  state="readonly")
        rig_combo.pack(side="left", padx=(6, 10))
        rig_combo.bind("<<ComboboxSelected>>", lambda e: self.on_rig_change())
        label(tb, "flrig Host:").pack(side="left")
        self.host_e = self._entry(tb, 12, self.cfg["host"])
        self.host_e.pack(side="left", padx=(6, 10), ipady=2)
        label(tb, "Port:").pack(side="left")
        self.port_e = self._entry(tb, 6, self.cfg["port"])
        self.port_e.pack(side="left", padx=(6, 10), ipady=2)
        for e in (self.host_e, self.port_e):
            e.bind("<Return>", lambda ev: self.connect())
        go = dict(on_color=C["go"], on_fg=C["go_fg"], font=(FONT.ui, 9, "bold"))
        blue = dict(base=C["on"], base_fg="#ffffff", font=(FONT.ui, 9, "bold"))
        # right side, packed right to left: Hot Keys, THEME [box], Settings - even gaps
        # (Compact View button removed 11-14d: Mini Meter + the Ctrl tap do the same; enter_compact kept)
        self.wf_btn = FlatButton(tb, "Waterfall", command=self.toggle_waterfall, **go)   # not shown: Shift+W
        self.keys_btn = FlatButton(tb, "Hot Keys", command=self.hotkey_menu, **blue)
        self.keys_btn.pack(side="right", padx=(0, 8))
        Tooltip(self.keys_btn, "Keyboard shortcuts (click one to use it)")
        self.theme_var = tk.StringVar(value=self.theme)
        th = ttk.Combobox(tb, textvariable=self.theme_var, values=list(THEMES), width=6, state="readonly")
        th.pack(side="right", padx=(6, 14))
        label(tb, "THEME:", fg=C["title"]).pack(side="right")
        self.settings_btn = FlatButton(tb, "Settings \u25be", command=self.settings_menu, **blue)
        self.settings_btn.pack(side="right", padx=(0, 14))
        th.bind("<<ComboboxSelected>>", lambda e: self.root.after(20, lambda: self.apply_theme(self.theme_var.get())))
        for combo in (rig_combo, th):           # the mouse wheel must never switch the radio or theme by accident
            for ev in ("<MouseWheel>", "<Button-4>", "<Button-5>"):
                combo.bind(ev, lambda e: "break")

        # --- status bar (packed now so it stays visible when the window is short)
        sb = tk.Frame(r, bg=C["status_bg"], padx=10, pady=4)
        sb.pack(side="bottom", fill="x")
        ver = tk.Label(sb, text=f"{APP_NAME} v{APP_VERSION} · build {APP_BUILD}", bg=C["status_bg"],
                       fg=C["status_fg"], font=(FONT.ui, 9), cursor="hand2")
        ver.pack(side="right")
        ver.bind("<Button-1>", lambda e: open_data_folder(self.log))   # settings + debug log live there
        self.log_lbl = tk.Label(sb, text=self.last_log, bg=C["status_bg"], fg=C["status_fg"], anchor="w", width=1,
                                font=(FONT.ui, 9, "bold"))
        self.log_lbl.pack(side="left", fill="x", expand=True)

        # --- frequency row
        fr = tk.Frame(r, bg=HUD["panel"], padx=10, pady=6, highlightthickness=1,
                      highlightbackground=HUD["edge"], highlightcolor=HUD["edge"])
        fr.pack(fill="x", padx=8, pady=(0, 0))
        self.tx_lbl = tk.Label(fr, text=" RX ", bg=C["go"], fg=C["go_fg"], font=(FONT.ui, 11, "bold"), padx=6)
        self.tx_lbl.pack(side="left", padx=(0, 12))
        self.freq_disp = FreqDisplay(fr, self.tune_to)
        self.freq_disp.pack(side="left")
        label(fr, "MHz", size=11, fg=HUD["hint"]).pack(side="left", padx=(4, 6), anchor="s", pady=10)
        self.mem_btn = FlatButton(fr, "▾", command=self.show_memories, font=(FONT.ui, 12, "bold"))
        self.mem_btn.pack(side="left", anchor="s", pady=8)

        vfo = tk.Frame(fr, bg=HUD["panel"])
        vfo.pack(side="left", padx=(16, 0))
        top = tk.Frame(vfo, bg=HUD["panel"])
        top.pack(anchor="w")
        self.other_lbl = tk.Label(top, text="VFO B", bg=HUD["panel"], fg=THEMES["Dark"]["gold"], font=(FONT.ui, 12, "bold"))
        self.other_lbl.pack(side="left")
        self.other_freq = tk.Label(top, text="--.---.---", bg=HUD["panel"], fg=HUD["value_dim"], font=(FONT.mono, 14, "bold"),
                                   cursor="hand2")
        self.other_freq.pack(side="left", padx=(6, 0))
        self.other_freq.bind("<Button-1>", lambda e: self.vfo_action("swap"))
        btns = tk.Frame(vfo, bg=HUD["panel"])
        btns.pack(anchor="w", pady=(3, 0))
        go = dict(on_color=C["go"], on_fg=C["go_fg"], font=(FONT.ui, 9, "bold"))
        self.vfo_btns = {}
        for key, text in (("A", "VFO A"), ("B", "VFO B")):
            b = FlatButton(btns, text, command=lambda k=key: self.vfo_action(k), **go)
            b.config(padx=7, pady=2)
            b.pack(side="left", padx=(0, 3))
            self.vfo_btns[key] = b
        for key, text in (("swap", "A\u21c4B"), ("copy", "A=B")):
            b = FlatButton(btns, text, command=lambda k=key: self.vfo_action(k), font=(FONT.ui, 9, "bold"))
            b.config(padx=7, pady=2)
            b.pack(side="left", padx=(0, 3))
            if key == "swap":
                self.swap_btn = b
        self.split_btn = FlatButton(btns, "Split", command=lambda: self.vfo_action("split"), **go)
        self.split_btn.config(padx=7, pady=2)
        self.split_btn.pack(side="left", padx=(6, 0))

        self._build_clar(fr, go)

        self.goto_e = self._entry(fr, 7, "")       # not shown: Shift+G opens goto_box()

        # --- band buttons
        bf = panel(r, padx=10, pady=6)
        bf.pack(fill="x", **pad)
        small_label(bf, "Band").pack(side="left", padx=(0, 8))
        self.band_btns = {}
        for b in BANDS:
            btn = FlatButton(bf, b[0] + "m", command=lambda b=b: self.pick_band(b), font=(FONT.ui, 9, "bold"))
            btn.pack(side="left", padx=1)
            self.band_btns[b[0]] = btn
        self.band_tail = tk.Frame(bf, bg=C["panel"])          # Tuner On / Off (per radio)
        self.band_tail.pack(side="right")

        # --- mode / bandwidth / tune row
        mf = panel(r, padx=10, pady=6)
        mf.pack(fill="x", **pad)
        self.vd = Segmented(mf, [("Voice", "voice"), ("Data", "data"), ("CW", "cw")], self.set_voice_data)
        self.vd.pack(side="left")
        for k, b in self.vd.buttons.items():           # say what a click does (Rig Setting of the same name or not)
            Tooltip(b, lambda k=k: (f"Apply {self.KIND_NAMES[k]} Settings (Edit Rig Settings > {self.KIND_NAMES[k]})"
                                    if self._has_macros() and self._kind_macro(k) else
                                    f"{self.KIND_NAMES[k]} mode and width. Make a Rig Setting named "
                                    f"{self.KIND_NAMES[k]} to set more with this button"))
        g = tk.Frame(mf, bg=C["panel"])                  # groups spread evenly across the row
        g.pack(side="left", expand=True)
        small_label(g, "Mode").pack(side="left", padx=(0, 6))
        self.mode_var = tk.StringVar()
        self.mode_combo = ttk.Combobox(g, textvariable=self.mode_var, width=9, state="readonly")
        self.mode_combo.pack(side="left")
        self.mode_combo.bind("<<ComboboxSelected>>", lambda e: self.set_mode(self.mode_var.get()))
        g = tk.Frame(mf, bg=C["panel"])
        g.pack(side="left", expand=True)
        small_label(g, "Bandwidth").pack(side="left", padx=(0, 6))
        self.bw_var = tk.StringVar()
        self.bw_combo = ttk.Combobox(g, textvariable=self.bw_var, width=9, state="readonly")
        self.bw_combo.pack(side="left")
        self.bw_combo.bind("<<ComboboxSelected>>", lambda e: self.set_bw())
        self._build_shift(mf)
        self.mode_ctl = tk.Frame(mf, bg=C["panel"])          # filled per radio (_build_mode_controls)
        self.mode_ctl.pack(side="left", expand=True)

        # --- FT-891 macros row (shown only for radios with macros)
        self.macro_row = panel(r, padx=10, pady=6)
        FlatButton(self.macro_row, "Edit Rig Settings", command=self.open_macro_editor,
                   font=(FONT.ui, 9, "bold"), base=C["on"], base_fg="#ffffff").pack(side="right", anchor="n")
        self.macro_inner = tk.Frame(self.macro_row, bg=C["panel"])
        self.macro_inner.pack(side="left", fill="x")
        self.macro_btns = {}

        # --- middle: meters | receive controls
        mid = tk.Frame(r, bg=C["bg"])
        mid.pack(fill="x", **pad)
        self.mid = mid
        self._build_macro_buttons()
        mid.columnconfigure(2, weight=1)

        met = section(mid, "Meters")
        met.grid(row=0, column=0, sticky="nsew", padx=(0, 8))
        hud = tk.Frame(met, bg=HUD["panel"], padx=4, pady=4, highlightthickness=1,
                       highlightbackground=HUD["edge"], highlightcolor=HUD["edge"])
        hud.pack(anchor="w")
        self.m_s = BarMeter(hud, "S", ticks=S_TICKS, zones=S_ZONES)
        self.m_po = BarMeter(hud, "Po", ticks=po_ticks(self.pmax))
        self.m_swr = BarMeter(hud, "SWR", ticks=SWR_TICKS)
        self.m_alc = BarMeter(hud, "ALC", ticks=ALC_TICKS)
        for m in (self.m_s, self.m_po, self.m_swr, self.m_alc):
            m.pack(anchor="w", pady=1)
        mrow = tk.Frame(met, bg=C["panel"])
        mrow.pack(anchor="w", pady=(6, 0))
        self.mini_btn2 = FlatButton(mrow, "Mini Meter\n(Shift+Z)", command=lambda: self.mini.toggle(),
                                    font=(FONT.ui, 9, "bold"), on_color=C["go"], on_fg=C["go_fg"])
        self.mini_btn2.pack(side="left")
        mopt = tk.Frame(mrow, bg=C["panel"])
        mopt.pack(side="left", padx=(8, 0))
        self.mini_auto_var = tk.BooleanVar(value=self.cfg.get("mini_auto", True))
        self.mini_always_var = tk.BooleanVar(value=self.cfg.get("mini_always", False))
        checkbox(mopt, "Pop up when transmitting", self.mini_auto_var, self._mini_opts_changed).pack(anchor="w")
        checkbox(mopt, "Always on screen", self.mini_always_var, self._mini_opts_changed).pack(anchor="w")

        lv = section(mid, "Levels")
        lv.grid(row=0, column=1, sticky="nsew", padx=(0, 8))
        self.sliders = {}
        lhud = tk.Frame(lv, bg=HUD["panel"], padx=6, pady=4, highlightthickness=1,
                        highlightbackground=HUD["edge"], highlightcolor=HUD["edge"])
        lhud.pack(anchor="w")
        for key, name, meth, unit, col in (("power", "RF Power", "rig.set_power", " W", "#ff4d4d"),       # red
                                           ("micgain", "Mic Gain", "rig.set_micgain", "", "#e040fb"),     # magenta
                                           ("rfgain", "RF Gain", "rig.set_rfgain", "", None),             # blue
                                           ("volume", "AF Volume", "rig.set_volume", "", "#2ee06e")):     # green
            holder = lhud
            if key == "volume":                 # AF Volume gets a Mute button beside it
                holder = tk.Frame(lhud, bg=HUD["panel"])
                holder.pack(anchor="w", pady=3)
            bar = LevelBar(holder, command=lambda v, k=key, m=meth: self.slider_moved(k, m, v), unit=unit, name=name,
                           color=col)
            if key == "volume":
                bar.pack(side="left")
                self._build_mute(holder)
            else:
                bar.pack(anchor="w", pady=3)
            self.sliders[key] = bar
        self._show_mute()
        tk.Label(lv, text="Click or drag a bar. Mouse wheel = 1 step.", bg=C["panel"], fg=C["dim"],
                 font=(FONT.ui, 8)).pack(anchor="w", pady=(6, 0))
        self.levels_var = tk.IntVar(value=1 if self.cfg.get("levels_per_kind", True) else 0)
        checkbox(lv, "Separate settings for Voice, Data and CW", self.levels_var,
                 lambda: self.cfg.__setitem__("levels_per_kind", bool(self.levels_var.get()))).pack(anchor="w")
        self.rf_band_var = tk.IntVar(value=1 if self.cfg.get("rf_per_band", True) else 0)
        cb = checkbox(lv, "RF gain per band", self.rf_band_var,
                      lambda: self.cfg.__setitem__("rf_per_band", bool(self.rf_band_var.get())))
        cb.pack(anchor="w")
        Tooltip(cb, "Each band keeps its own RF gain: change band and the RF gain you last used there comes back")
        lrow = tk.Frame(lv, bg=C["panel"])
        lrow.pack(anchor="w", pady=(6, 0))
        self.lv_btn = FlatButton(lrow, "Mini Levels\n(Shift+L)", command=lambda: self.mini_lv.toggle(),
                                 font=(FONT.ui, 9, "bold"), on_color=C["go"], on_fg=C["go_fg"])
        self.lv_btn.pack(side="left")
        lopt = tk.Frame(lrow, bg=C["panel"])
        lopt.pack(side="left", padx=(8, 0))
        self.lv_auto_var = tk.BooleanVar(value=self.cfg.get("lv_auto", False))
        self.lv_always_var = tk.BooleanVar(value=self.cfg.get("lv_always", False))
        checkbox(lopt, "Pop up when receiving", self.lv_auto_var, self._lv_opts_changed).pack(anchor="w")
        checkbox(lopt, "Always on screen", self.lv_always_var, self._lv_opts_changed).pack(anchor="w")

        self.rx_frame = section(mid, "Receive / Filters")
        self.rx_frame.grid(row=0, column=2, sticky="nsew")
        self.rx_body = tk.Frame(self.rx_frame, bg=C["panel"])
        self.rx_body.pack(fill="both", expand=True)
        self._build_rx_controls()

        # --- waterfall
        self.wf = Waterfall(r, self)
        self.wf_spacer = tk.Frame(r, bg=C["bg"], height=8)
        self.wf_spacer.pack(fill="x")
        if self.wf_shown:
            self.wf.frame.pack(fill="both", expand=True, padx=8, pady=(8, 0), before=self.wf_spacer)
        self.wf_btn.set_on(self.wf_shown)

    def _build_rx_controls(self):
        for c in self.rx_body.winfo_children():
            c.destroy()
        self.ctl_widgets = {}
        prof = self.profile
        self._build_mode_controls(prof)
        if not prof:
            msg = ("Connect to flrig to see your radio here.\nAny radio flrig supports works with RigPanel."
                   if not self.xcvr else
                   f"{self.xcvr} is working through flrig: frequency, mode,\n"
                   "bandwidth, VFOs, meters, levels and TUNE.\n\n"
                   "Receive filters, Rig Settings and menus are built in\n"
                   "for the IC-7300 and FT-891. Keep Rig on Auto-detect -\n"
                   "choosing one of those for a different radio can\nchange the wrong settings.")
            tk.Label(self.rx_body, text=msg, bg=C["panel"], fg=C["dim"], justify="left").pack(anchor="w")
            return
        grid = tk.Frame(self.rx_body, bg=C["panel"])
        grid.pack(anchor="w", fill="x")
        row = 0
        self.cw_only = []                       # rows shown only in CW (BKIN)
        for ctl in [c for c in prof.controls if c.kind == "select" and c.row == "rx"]:
            lbl = tk.Label(grid, text=ctl.label, bg=C["panel"], fg=C["fg"], font=(FONT.ui, 10, "bold"),
                           width=8, anchor="w")
            lbl.grid(row=row, column=0, sticky="w", pady=3)
            seg = Segmented(grid, ctl.options, lambda v, c=ctl: self.set_control(c, v))
            seg.grid(row=row, column=1, sticky="w")
            if ctl.key in self.CW_ONLY:
                self.cw_only += [lbl, seg]
            self.ctl_widgets[ctl.key] = seg
            row += 1
            if ctl.note:
                tk.Label(grid, text=ctl.note, bg=C["panel"], fg=C["dim"], font=(FONT.ui, 8)).grid(
                    row=row, column=1, sticky="w")
                row += 1
        tg = tk.Frame(self.rx_body, bg=C["panel"])
        tg.pack(anchor="w", pady=(8, 0))
        for ctl in [c for c in prof.controls if c.kind == "toggle" and c.row == "rx"]:
            b = FlatButton(tg, ctl.label, font=(FONT.ui, 10, "bold"), on_color=C["green"])
            b.command = lambda c=ctl: self.set_control(c, 0 if self.ctl_values.get(c.key) else 1)
            b.pack(side="left", padx=(0, 0 if ctl.level else 4))
            self.ctl_widgets[ctl.key] = b
            if ctl.level:                           # \u25be = pick the level (e.g. DNR 1-15)
                arrow = FlatButton(tg, "\u25be", font=(FONT.ui, 10, "bold"))
                arrow.config(padx=4)
                arrow.command = lambda c=ctl, w=arrow: self.level_menu(c, w)
                arrow.pack(side="left", padx=(1, 4))
                Tooltip(arrow, f"{ctl.label} level")
                self.worker.submit(lambda w, c=ctl: w.ctl_level(c))
        # 11-16g: "changed from your Voice settings" notice (packed only when the radio differs)
        self.kind_note = tk.Frame(self.rx_body, bg=C["panel"])
        self.kind_note_btn = FlatButton(self.kind_note, "Default Settings", font=(FONT.ui, 9, "bold"))
        self.kind_note_btn.pack(side="left", anchor="n")
        Tooltip(self.kind_note_btn, lambda: f"Return the radio to your {self.KIND_NAMES.get(memory_kind(self.mode or ''), 'Voice')}"
                                            " Rig Setting (Edit Rig Settings). Your last settings are kept until you click it")
        self.kind_note_lbl = tk.Label(self.kind_note, bg=C["panel"], fg=C["amber"], font=(FONT.ui, 9, "bold"),
                                      justify="left", anchor="w", wraplength=240)
        self.kind_note_lbl.pack(side="left", anchor="w", padx=(8, 0))
        self.kind_note_shown = None
        self.profile_lbl = tk.Label(self.rx_body, text=f"Profile: {prof.name}", bg=C["panel"], fg=C["profile"],
                                    font=(FONT.ui, 12, "bold"))
        self.profile_lbl.pack(anchor="w", pady=(8, 0))
        for key, v in self.ctl_values.items():
            self._show_ctl(key, v)
        self.m_alc.set_zone(prof.alc_zone)

    # ---------------- connection / profile ----------------
    def connect(self):
        host = self.host_e.get().strip() or "127.0.0.1"
        try:
            port = int(self.port_e.get().strip())
        except ValueError:
            port = 12345
        self.cfg["host"], self.cfg["port"] = host, port
        self.worker.connect(host, port)
        self._status("wait", f"Connecting to flrig at {host}:{port} ...")

    def on_rig_change(self):
        if self.rig_var.get() == self.ADD_RIG:          # last line of the Rig list: open Add my radio
            self.rig_var.set(self.cfg.get("rig", "Auto-detect"))
            self.root.after(10, self.open_add_radio)
            return
        self.cfg["rig"] = self.rig_var.get()
        self._apply_profile()

    def _apply_profile(self):
        self.ctl_values = {}
        self.macro_state = {}
        self.ex_unsupported = set()
        self.close_vscan()                       # a different radio
        self.profile = make_profile(self.rig_var.get(), self.xcvr, self.cfg.get("civ_addr", "94"),
                                    self.cfg.get("custom_rigs", []))
        prof = self.profile
        self.show_scan_button()
        self.worker.submit(lambda w: w.set_profile(prof))
        self._seed_radio_defaults()
        self._build_rx_controls()
        self._build_macro_buttons()
        self._update_macro_row()
        self.clar_on, self.clar_hz = False, 0
        self._show_clar()                       # "CLAR" on the FT-891, "RIT" on the IC-7300
        if self.connected and self.profile and self.xcvr and not find_custom(self.cfg.get("custom_rigs"), xcvr=self.xcvr):
            num = self.profile.name.split("-")[-1]
            if num not in self.xcvr:
                self.log(f"Warning: Rig is set to {self.profile.name} but flrig is driving '{self.xcvr}'.")

    def _seed_radio_defaults(self):
        """First time a radio connects on a PC with no stored frequencies / levels of its own:
        start from the operator's (RADIO_DEFAULTS). Runs once per radio per PC."""
        name = self.profile.name if self.profile else None
        seed = RADIO_DEFAULTS.get(name)
        if seed is None and self.profile is not None:     # an added radio: Icom / Yaesu mode names
            seed = RADIO_DEFAULTS["IC-7300" if isinstance(self.profile, IcomProfile) else "FT-891"]
        done = self.cfg.setdefault("seeded", [])
        if not seed or name in done:
            return
        added = []
        if not self.cfg.get("memories"):
            self.cfg["memories"] = json.loads(json.dumps(seed["memories"]))
            added.append("stored frequencies")
        if seed.get("levels_by_kind") and not self.cfg.get("levels_by_kind"):
            self.cfg["levels_by_kind"] = json.loads(json.dumps(seed["levels_by_kind"]))
            added.append("voice/data levels")
        done.append(name)
        save_config(self.cfg)
        if added:
            self.log(f"{name}: starting {' and '.join(added)} added - change them any time.")

    def _status(self, state, text):
        changed = (state, text) != self.last_status
        self.last_status = (state, text)
        word = {"ok": "Connected", "wait": "Waiting"}.get(state, "Offline")
        color = {"ok": C["header_val"], "wait": "#ffcc33"}.get(state, "#ff6b6b")
        self.flrig_val.config(text=word, fg=color)
        if changed or not self.last_log:
            self.log(text)

    def log(self, text):
        # width=1 on the label: a long message is cut off, it never widens the window
        if len(text) > 140:
            text = text[:137] + "..."
        debug_log("status: " + text)
        self.last_log = time.strftime("%H:%M:%S  ") + text
        self.log_lbl.config(text=self.last_log)

    # ---------------- messages from worker ----------------
    def _pump(self):
        if getattr(self, "dead", False):
            return
        try:
            while True:
                kind, data = self.out_q.get_nowait()
                if kind == "poll":
                    self._on_poll(data)
                elif kind == "ctl":
                    self.ctl_values[data[0]] = data[1]
                    self._show_ctl(*data)
                elif kind == "ctl_level":
                    key, v, wanted = data
                    name = next((c.label for c in (self.profile.controls if self.profile else []) if c.key == key), key)
                    if v is not None:
                        ctl = next((c for c in self.profile.controls if c.key == key), None) if self.profile else None
                        step = ctl.level[3] if ctl and len(ctl.level) > 3 else 1
                        self.ctl_levels[key] = int(round(v / step) * step)    # tick the nearest menu entry
                    if wanted is not None:
                        self.log(f"{name} level {v}" if v == wanted else
                                 f"{name} level: asked for {wanted}, radio says {v if v is not None else 'no answer'}")
                elif kind == "tables":
                    self._on_tables(data)
                elif kind == "connected":
                    self.connected = True
                    self.xcvr = data["xcvr"]
                    self.pmax = data["pmax"]
                    self.sliders["power"].set_max(self.pmax)
                    self.connect_btn.set_on(True)
                    self.m_po.set_ticks(po_ticks(self.pmax))
                    self.rig_val.config(text=self.xcvr or "--")
                    self._status("ok", f"flrig connected - {self.xcvr}")
                    self._apply_profile()
                    self.offer_add_radio()
                    if getattr(self.profile, "VFO_BY_SWAP", False):
                        # FT-891: closing flrig swaps VFOs (its restore_xcvr_vals selects B, then A), and every
                        # swap forces the data width to 500 - put the Data width back once connected (30a)
                        self.swap_check = time.monotonic() + 10
                elif kind == "down":
                    if self.connected:
                        self.log(data)
                    self.connected = False
                    self.connect_btn.set_on(False)
                    self.rig_val.config(text="--")
                    self._status("wait", data)
                elif kind == "log":
                    self.log(data)
                elif kind == "ex_unsupported":
                    self.ex_unsupported.add(data)
                    self.log(f"FT-891 menu {item_label(data)} can't be read or set over CAT on this radio "
                             f"- macros will skip it")
                    self._build_macro_buttons()
                elif kind == "macro_state":
                    self.macro_state.update(data)
                    self.refresh_macro_buttons()
                elif kind == "macro_done":
                    self._macro_done(data)
                elif kind == "vscan":
                    if self.vscan_win is not None and self.vscan_win.winfo_exists():
                        self.vscan_win.on_vscan(data)
                elif kind == "shift":
                    self._on_shift(data)
                elif kind == "clar":
                    self._on_clar(data)
                elif kind == "macro_capture":
                    if self.macro_win is not None and self.macro_win.winfo_exists():
                        self.macro_win.fill(*data)
        except queue.Empty:
            pass
        self.root.after(50, self._pump)

    def _recent(self, key):
        return time.monotonic() - self.touched.get(key, 0) < TOUCH_HOLD_S

    def _touch(self, key):
        self.touched[key] = time.monotonic()

    def _on_tables(self, t):
        if "modes" in t:
            self.modes = t["modes"]
            self.mode_combo["values"] = self.modes
        if "bws" in t:
            self.bws = t["bws"]
            self.bw_combo["values"] = self.bws
            kind, self.pending_bw = getattr(self, "pending_bw", None), None
            if kind and self.mode and memory_kind(self.mode) == kind:
                self._restore_bw(kind)            # the width list of the new mode is here: now put the width back

    def _on_poll(self, d):
        if not self._recent("freq"):
            self.freq = d["freq"]
            self.freq_disp.set(self.freq)
        b = band_of(self.freq or 0)
        for name, btn in self.band_btns.items():
            btn.set_on(b is not None and b[0] == name)
        if not self._recent("freq"):              # a poll from before a band click must not count as a change
            self._band_rf(b[0] if b else None)
        if b and self.freq:
            kind = memory_kind(d["mode"])
            self.cfg.setdefault("band_memory", {})[f"{b[0]}:{kind}"] = int(self.freq)

        if self._recent("mode") and d["mode"] and d["mode"] != self.mode_var.get():
            d["mode"] = self.mode or d["mode"]    # 11-06h: a late reading of the old mode - don't switch back
        if self.mode and d["mode"] and memory_kind(self.mode) != memory_kind(d["mode"]):
            self.mode = d["mode"]                 # 11-06b: the new mode first, or its width is saved as the old kind's
            self._restore_levels(memory_kind(d["mode"]))
        elif getattr(self, "swap_check", 0) and time.monotonic() < self.swap_check and d.get("bw") \
                and is_data_mode(d["mode"]) and parse_hz(d["bw"]) == 500 and self.levels_var.get():
            self.swap_check = 0
            self.bw_var.set(d["bw"])
            if self._restore_bw("data"):
                self.log("Data bandwidth put back (the FT-891 resets it to 500 on A/B and when flrig closes)")
        self.mode = d["mode"]
        self._show_shift_row()
        self._show_cw_rows()
        if not self._recent("mode"):
            self.mode_var.set(self.mode)
            self.vd.set(memory_kind(self.mode))
            self._mark_kind_buttons()
        if not self._recent("bw") and d.get("bw"):
            self.bw_var.set(d["bw"])
            fil, got = self.ctl_values.get("filter"), parse_hz(d["bw"])
            key = f"{memory_kind(self.mode)}:{fil}" if self.mode else None
            sent = self.cfg.get("fil_width_sent", {}).get(key)
            if fil in (1, 2, 3) and got and sent and abs(got - int(sent)) > 100 and not self.macro_busy:
                self.cfg["fil_width_sent"].pop(key, None)    # width changed on the radio: send it again next time

        if "ab" in d and not self._recent("vfo"):
            # FT-891: the radio only swaps, so "VFO A / B" is which side RigPanel last swapped to
            ab = self.cfg.get("ft891_vfo_side", "A") if getattr(self.profile, "VFO_BY_SWAP", False) else d["ab"]
            self.ab, self.other_hz = ab, d.get("other_freq")
            if d.get("split") is not None:
                self.split = d["split"]
            self._show_vfo()

        ptt = d.get("ptt", False)
        if ptt != self.ptt:
            self.ptt = ptt
            self.tx_lbl.config(text=" TX " if ptt else " RX ", bg=C["tx"] if ptt else C["go"],
                               fg="#ffffff" if ptt else C["go_fg"])
            self.tune_btn.set_on(ptt)
            self.mini.on_ptt(ptt)
            self.mini_lv.on_ptt(ptt)

        if "smeter" in d:
            v = d["smeter"]
            self.m_s.set(v / 100, s_text(v))
        if ptt:
            self.m_s.set(0, "--", dim=True)
            po = d.get("po", 0.0)
            self.m_po.set(po / max(1.0, self.pmax), f"{po:.0f} W", C["po"])
            if "swr" in d:
                self.last_swr = d["swr"]
                s = d["swr"]
                col = C["green"] if s < 1.5 else (C["amber"] if s < 2.0 else C["red"])
                self.m_swr.set((s - 1) / 2, f"{s:.1f}:1", col)
            if "alc" in d:
                a = d["alc"]
                zone = self.profile.alc_zone if self.profile else 0.5
                self.m_alc.set(a, f"{a * 100:.0f}%", C["alc"] if a <= zone else C["alc_over"])
        else:
            self.m_po.set(0, "0 W", dim=True)
            self.m_alc.set(0, "--", dim=True)
            if self.last_swr is not None:
                self.m_swr.set((self.last_swr - 1) / 2, f"{self.last_swr:.1f}:1", dim=True)

        if self._has_macros():
            self.refresh_macro_buttons()
        if self.mini.visible():
            self.mini.mirror()
        if self.mini_lv.visible():
            self.mini_lv.mirror()
        if self.float_wf is not None and self.float_wf.visible():
            self.float_wf.update_info()

        for key in ("power", "micgain", "rfgain", "volume"):
            if key in d and not self._recent(key):
                v = int(round(d[key]))
                self.levels[key] = v
                if self.sliders[key].get() != v:
                    self.sliders[key].set(v)

    def _show_vfo(self):
        other = "B" if self.ab == "A" else "A"
        self.other_lbl.config(text=f"VFO {other}")
        self.other_freq.config(text=fmt_freq(self.other_hz) if self.other_hz else "--.---.---",
                               fg=C["freq"] if self.split else C["freq_dim"])
        for k, b in self.vfo_btns.items():
            b.set_on(k == self.ab)
            # both radios show VFO A / VFO B (27k; the FT-891 does them by swapping)
            # winfo_manager (placed), not winfo_ismapped (drawn): right after a theme change nothing is drawn yet
            if not b.winfo_manager() and self.swap_btn.winfo_manager():
                b.pack(side="left", padx=(0, 3), before=self.swap_btn)
        self.split_btn.set_on(self.split)

    def vfo_action(self, what):
        if not self._need_link():
            return
        if self.ptt and what in ("A", "B", "swap", "copy"):
            self.log("Not while transmitting.")
            return
        self._touch("vfo")
        self._touch("freq")                     # the main readout changes with the VFO
        swap_only = bool(getattr(self.profile, "VFO_BY_SWAP", False))
        if swap_only and what in ("A", "B"):
            # FT-891: no VFO select over CAT - "VFO B" = swap to the other side (and back for "VFO A")
            if what == self.ab:
                return
            what, pick = "swap", True
        else:
            pick = False
        if what in ("A", "B"):
            if what != self.ab and self.other_hz:
                self.ab, self.other_hz, self.freq = what, self.freq, self.other_hz
                self.freq_disp.set(self.freq)
            self.ab = what
            self.worker.submit(lambda w: w.vfo_select(what))
            self.log(f"VFO {what}")
        elif what == "swap":
            if self.other_hz and self.freq:
                self.freq, self.other_hz = self.other_hz, self.freq
                self.freq_disp.set(self.freq)
            self.worker.submit(lambda w: w.vfo_swap())
            self.swap_check = time.monotonic() + 4
            if pick:                              # FT-891 VFO A / VFO B: now on the other side
                self.ab = "B" if self.ab == "A" else "A"
                self.cfg["ft891_vfo_side"] = self.ab
                self.log(f"VFO {self.ab}")
            else:
                self.log("VFO A and B swapped")
        elif what == "copy":
            self.other_hz = self.freq
            other = "B" if self.ab == "A" else "A"
            self.worker.submit(lambda w: w.vfo_copy())
            self.log(f"VFO {self.ab} copied to VFO {other}")
        elif what == "split":
            self.split = not self.split
            on = self.split
            self.worker.submit(lambda w: w.set_split(on))
            self.log("Split ON - transmit on VFO " + ("B" if self.ab == "A" else "A") if on else "Split OFF")
        self._show_vfo()

    def _build_mode_controls(self, prof):
        """Mode-row controls (IC-7300: FIL1/2/3 presets and Tuner on/off)."""
        for c in self.mode_ctl.winfo_children() + self.band_tail.winfo_children():
            c.destroy()
        for ctl in [c for c in (prof.controls if prof else []) if c.row == "mode"]:
            if ctl.kind == "select":
                small_label(self.mode_ctl, ctl.label).pack(side="left", padx=(14, 4))
                seg = Segmented(self.mode_ctl, ctl.options, lambda v, c=ctl: self.set_control(c, v, remember=False))
                seg.pack(side="left")
                self.ctl_widgets[ctl.key] = seg
            else:
                where = self.band_tail if ctl.key == "tuner" else self.mode_ctl
                text = f"{ctl.label} Off" if ctl.key == "tuner" else ctl.label
                b = FlatButton(where, text, font=(FONT.ui, 11 if ctl.key == "tuner" else 9, "bold"),
                               on_color=C["go"], on_fg=C["go_fg"])
                b.config(padx=18 if ctl.key == "tuner" else 10, pady=4 if ctl.key == "tuner" else 5)
                b.command = lambda c=ctl: self.set_control(c, 0 if self.ctl_values.get(c.key) else 1, remember=False)
                b.pack(side="left", padx=(14, 0))
                self.ctl_widgets[ctl.key] = b

    def level_menu(self, ctl, widget):
        if not self._need_link():
            return
        lo, hi = ctl.level[0], ctl.level[1]
        step = ctl.level[3] if len(ctl.level) > 3 else 1
        var = tk.IntVar(value=self.ctl_levels.get(ctl.key, -1))
        m = self._menu(self.root)
        m.config(selectcolor=C["go"])               # the tick on the current level, visible on dark menus
        m.add_command(label=f"{ctl.label} level", state="disabled")
        values = list(range(lo, hi + 1, step))
        per_col = 11 if len(values) > 16 else len(values)       # 11-16j: long lists (PROC 0-100) in columns
        for i, n in enumerate(values):
            m.add_radiobutton(label=f"{n} %" if hi == 100 else str(n), variable=var, value=n,
                              columnbreak=1 if i and i % per_col == 0 else 0,
                              command=lambda n=n: self.worker.submit(lambda w: w.ctl_level(ctl, n)))
        self.worker.submit(lambda w: w.ctl_level(ctl))           # refresh for next time
        # below the arrow, or above it if it doesn't fit - a menu opened over the mouse pointer on Linux
        # catches the button release and closes at once (11-16j: PROC's menu "won't stay up")
        m.update_idletasks()
        x, y = widget.winfo_rootx(), widget.winfo_rooty() + widget.winfo_height()
        if y + m.winfo_reqheight() > screen_bounds(widget)[3]:
            y = max(0, widget.winfo_rooty() - m.winfo_reqheight())
        popup_menu(m, x, y)

    def _show_ctl(self, key, value):
        w = self.ctl_widgets.get(key)
        if isinstance(w, Segmented):
            w.set(value)
        elif isinstance(w, FlatButton):
            w.set_on(bool(value))
            if key == "tuner":                    # the big band-row button says what it is
                w.config(text="Tuner On" if value else "Tuner Off")

    # ---------------- actions ----------------
    def _need_link(self):
        if not self.connected:
            self.log("Not connected to flrig yet.")
            return False
        return True

    def tune_to(self, hz):
        if not self._need_link():
            return
        hz = max(FREQ_MIN, min(FREQ_MAX, int(hz)))
        self.pending_freq = hz
        self.freq = hz
        self.freq_disp.set(hz)
        self._touch("freq")
        if not self.freq_job_queued:      # coalesce rapid clicks: one job sends the latest value
            self.freq_job_queued = True

            def job(w):
                self.freq_job_queued = False
                w.set_freq(self.pending_freq)
            self.worker.submit(job)

    # ---------------- stored frequencies ----------------
    # ---------------- settings: files, my default ----------------
    def settings_menu(self):
        m = self._menu(self.root)
        m.add_command(label="Save settings to a file...", command=self.export_settings)
        m.add_command(label="Load settings from a file...", command=self.import_settings)
        m.add_separator()
        m.add_command(label="Save as my default", command=self.save_my_default)
        m.add_command(label="Return to my default", command=self.return_to_default)
        m.add_command(label="Add my radio...", command=self.open_add_radio)
        m.add_separator()
        self.ctrl_tap_var = tk.BooleanVar(value=bool(self.cfg.get("ctrl_tap", True)))
        m.add_checkbutton(label="Tap Ctrl to bring RigPanel forward", variable=self.ctrl_tap_var,
                          command=lambda: self.set_ctrl_tap(self.ctrl_tap_var.get()))
        m.add_command(label="Open settings folder", command=lambda: open_data_folder(self.log))
        b = self.settings_btn
        popup_menu(m, b.winfo_rootx(), b.winfo_rooty() + b.winfo_height())

    def _settings_now(self):
        """The settings as they are this moment (what close() would save)."""
        self.cfg["rig"] = self.rig_var.get()
        self.cfg["theme"] = self.theme
        if self.float_wf is not None and self.float_wf.winfo_exists():
            self.float_wf.remember()
        if getattr(self, "wf", None):
            self.wf.save(self.cfg)
        return json.loads(json.dumps(self.cfg))

    def export_settings(self):
        name = f"RigPanel_settings_{socket.gethostname()}_{time.strftime('%Y-%m-%d')}.json"
        path = filedialog.asksaveasfilename(parent=self.root, title="Save RigPanel settings",
                                            initialdir=os.path.expanduser("~"), initialfile=name,
                                            defaultextension=".json", filetypes=[("RigPanel settings", "*.json")])
        if not path:
            return
        try:
            write_json(path, self._settings_now())
            self.log(f"Settings saved to {path}")
        except OSError as e:
            self.log(f"Couldn't save the settings file: {e}")

    def import_settings(self):
        path = filedialog.askopenfilename(parent=self.root, title="Load RigPanel settings",
                                          initialdir=os.path.expanduser("~"),
                                          filetypes=[("RigPanel settings", "*.json"), ("All files", "*.*")])
        if path:
            self._load_settings(path, "the settings file")

    def save_my_default(self):
        try:
            write_json(MY_DEFAULT_PATH, self._settings_now())
            self.log("Saved as my default. Settings > Return to my default brings this setup back.")
        except OSError as e:
            self.log(f"Couldn't save my default: {e}")

    def return_to_default(self):
        if os.path.exists(MY_DEFAULT_PATH):
            what, path = "your default", MY_DEFAULT_PATH
        else:
            what, path = "RigPanel's built-in defaults", None
        if not messagebox.askyesno("Return to my default",
                                   f"Replace the current settings with {what}?\n\nThis PC's sound device, flrig "
                                   "address, radio choice and window places are kept. The current settings are "
                                   "backed up first.", parent=self.root):
            return
        self._load_settings(path, what)

    def _load_settings(self, path, what):
        """Replace the settings (keeping this PC's own ones) and restart the window with them."""
        try:
            new = {}
            if path:
                with open(path, encoding="utf-8") as f:
                    new = json.load(f)
                if not isinstance(new, dict) or not ("theme" in new or "memories" in new or "host" in new):
                    raise ValueError("this isn't a RigPanel settings file")
        except (OSError, ValueError) as e:
            self.log(f"Couldn't load {what}: {e}")
            return
        now = self._settings_now()
        try:
            write_json(BACKUP_PATH, now)
        except OSError as e:
            self.log(f"Not loaded - couldn't back up the current settings first: {e}")
            return
        cfg = json.loads(json.dumps(DEFAULT_CONFIG))
        cfg.update(new)
        for k in PC_KEYS:                       # this PC's sound card, flrig, radio and screen stay
            if k in now:
                cfg[k] = now[k]
        debug_log(f"settings loaded from {path or 'built-in defaults'} (backup: {BACKUP_PATH})")
        self._restart_with(cfg, f"Loaded {what}. Your previous settings are backed up in settings_before_load.json.")

    def _menu(self, parent):
        return tk.Menu(parent, tearoff=0, bg=C["field"], fg=C["fg"], activebackground=C["on"],
                       activeforeground="#ffffff", disabledforeground=C["dim"], font=(FONT.ui, 10, "bold"))

    @staticmethod
    def _mem_label(mem):
        parts = [f"{fmt_freq(mem['hz'])} MHz", mem.get("mode") or ""]
        if mem.get("name"):
            parts.append(f"- {mem['name']}")
        return "   ".join(p for p in parts if p)

    def _memories(self):
        return sorted(self.cfg.setdefault("memories", []), key=lambda m: m["hz"])

    MEM_FLAT_MAX = 20     # more stored frequencies than this: the drop-down groups them by band

    def show_memories(self):
        mems = self._memories()
        menu = self._menu(self.root)
        cur = int(round(self.freq)) if self.freq else None
        def add(mn, mem):
            mark = "\u25cf  " if mem["hz"] == cur else "     "     # dot = where you are now
            mn.add_command(label=mark + self._mem_label(mem), command=lambda m=mem: self.recall_memory(m),
                           foreground=kind_color(mem.get("mode")), font=(FONT.mono, 10, "bold"))
        if mems and len(mems) > self.MEM_FLAT_MAX:
            # long list: this band's frequencies, then one submenu per band (11-14h)
            here = band_of(self.freq) if self.freq else None
            if here:
                for mem in mems:
                    if band_of(mem["hz"]) == here:
                        add(menu, mem)
                menu.add_separator()
            groups = {}
            for mem in mems:
                b = band_of(mem["hz"])
                groups.setdefault(b[0] + " m" if b else "Other", []).append(mem)
            for band, items in groups.items():
                sub = self._menu(menu)
                for mem in items:
                    add(sub, mem)
                menu.add_cascade(label=f"{band}  ({len(items)})", menu=sub, font=(FONT.ui, 10, "bold"))
        elif mems:
            for mem in mems:
                add(menu, mem)
        else:
            menu.add_command(label="No stored frequencies yet", state="disabled")
        menu.add_separator()
        menu.add_command(label="Green = Digital", foreground=C["freq"], activeforeground=C["freq"],
                         activebackground=C["field"], font=(FONT.ui, 11, "bold"))
        menu.add_command(label="Blue = Voice", foreground=C["voice"], activeforeground=C["voice"],
                         activebackground=C["field"], font=(FONT.ui, 11, "bold"))
        menu.add_command(label="Red = CW", foreground=C["red"], activeforeground=C["red"],
                         activebackground=C["field"], font=(FONT.ui, 11, "bold"))
        menu.add_command(label="Edit frequency list...", command=self.open_freq_list, font=(FONT.ui, 10, "bold"))
        popup_menu(menu, self.mem_btn.winfo_rootx(), self.mem_btn.winfo_rooty() + self.mem_btn.winfo_height())

    def recall_memory(self, mem):
        self.tune_to(mem["hz"])
        mode = mem.get("mode")
        if mode and self.modes and mode not in self.modes and DATA_MODE_SAME.get(mode) in self.modes:
            mode = DATA_MODE_SAME[mode]          # a list made on the other radio (USB-D <-> DATA-U)
        if mode and mode != self.mode and (not self.modes or mode in self.modes):
            self.set_mode(mode)

    def store_memory(self, hz, mode, name, replace_hz=None):
        """Add or replace a stored frequency. Same frequency already stored -> replaced."""
        drop = {hz, replace_hz}
        mems = [m for m in self.cfg.setdefault("memories", []) if m["hz"] not in drop]
        mems.append({"hz": int(hz), "mode": mode or "", "name": (name or "").strip()})
        self.cfg["memories"] = mems
        save_config(self.cfg)

    def delete_memory(self, hz):
        self.cfg["memories"] = [m for m in self.cfg.get("memories", []) if m["hz"] != hz]
        save_config(self.cfg)

    def open_freq_list(self):
        if self.freq_win is not None and self.freq_win.winfo_exists():
            self.freq_win.deiconify()
            self.freq_win.lift()
            self.freq_win.focus_freq()
            return
        self.freq_win = FreqListWindow(self)

    def goto_box(self):
        """Shift+G: a small box under the frequency - type kHz, Enter goes there, Esc closes."""
        if getattr(self, "goto_win", None) is not None and self.goto_win.winfo_exists():
            self.goto_win.lift()
            return
        w = self.goto_win = tk.Toplevel(self.root)
        w.overrideredirect(True)
        w.attributes("-topmost", True)
        f = tk.Frame(w, bg=HUD["panel"], padx=10, pady=8, highlightthickness=2, highlightbackground=THEMES["Dark"]["gold"])
        f.pack()
        tk.Label(f, text="Go to", bg=HUD["panel"], fg=THEMES["Dark"]["gold"], font=(FONT.ui, 11, "bold")).pack(side="left")
        e = tk.Entry(f, width=10, bg=HUD["bottom"], fg="#ffffff", insertbackground="#ffffff", relief="flat",
                     font=(FONT.mono, 14, "bold"), highlightthickness=1, highlightbackground=HUD["edge"])
        e.pack(side="left", padx=8, ipady=2)
        tk.Label(f, text="kHz   Enter = go, Esc = close", bg=HUD["panel"], fg=HUD["hint"],
                 font=(FONT.ui, 9, "bold")).pack(side="left")

        def go(ev=None):
            self.goto_e.delete(0, "end")
            self.goto_e.insert(0, e.get())
            close()
            self.goto()

        def close(ev=None):
            self.goto_win = None
            w.destroy()
        e.bind("<Return>", go)
        e.bind("<KP_Enter>", go)
        e.bind("<Escape>", close)
        e.bind("<FocusOut>", lambda ev: w.after(150, lambda: w.winfo_exists() and close()))
        fd = self.freq_disp
        w.geometry(f"+{fd.winfo_rootx()}+{fd.winfo_rooty() + fd.winfo_height() + 6}")
        w.update_idletasks()
        e.focus_force()

    def goto(self):
        try:
            khz = float(self.goto_e.get().replace(",", ""))
        except ValueError:
            self.log("Type a frequency in kHz, e.g. 14074")
            return
        self.tune_to(khz * 1000)

    def pick_mode(self, kind, hz):
        modes_up = {m.upper(): m for m in self.modes}
        if kind == "cw":                      # FT-891 CW-L (operator, 11-06f), IC-7300 CW
            return next((modes_up[c] for c in ("CW-L", "CW") if c in modes_up), None)   # CW on the lower side
        if kind == "data":
            for cand in DATA_UPPER:           # digital modes run upper sideband on every band
                if cand in modes_up:
                    return modes_up[cand]
            return None
        lower = hz < 10_000_000 and not (5_330_000 <= hz <= 5_410_000)
        want = "LSB" if lower else "USB"
        return modes_up.get(want, want)

    def set_mode(self, mode):
        if not mode or not self._need_link():
            return
        self.mode_var.set(mode)
        self.vd.set(memory_kind(mode))
        self._touch("mode")
        self.worker.submit(lambda w: w.set_mode(mode))

    KIND_NAMES = {"voice": "Voice", "data": "Data", "cw": "CW"}
    POWER_ITEMS = ("1601", "1602", "1603", "1604")   # FT-891 power menus: set by the RF Power slider instead

    def _kind_macro(self, kind):
        """The Rig Setting named Voice / Data / CW (11-06c: the mode row runs it; it has no button of its own)."""
        want = self.KIND_NAMES.get(kind, "").lower()
        return next((m for m in self.macro_list() if m["name"].strip().lower() == want), None)

    def set_voice_data(self, kind):
        m = self._kind_macro(kind) if self._has_macros() else None
        if m is not None:
            w = self.kind_width(m["items"])
            if w:                                 # its width is this kind's width from now on
                mem = self.cfg.setdefault("bw_by_kind", {}).setdefault(kind, {})
                mem["bw"] = str(w)
                for n in "123":                   # and each filter's width (IC-7300, 11-16b)
                    if m["items"].get(f"WIDTH{n}"):
                        mem.setdefault("bw_fil", {})[n] = str(m["items"][f"WIDTH{n}"])
                save_config(self.cfg)
            mode = self.pick_mode(kind, self.freq or 14_000_000)
            want = str(m["items"].get("MODE") or "")
            if want.upper() in {x.upper() for x in self.modes} and memory_kind(want) == kind:   # wrong kind: ignore
                mode = next(x for x in self.modes if x.upper() == want.upper())
            if mode and mode != self.mode:
                self.set_mode(mode)               # 11-06g: switch at once; the menu items follow in the background
                self.touched["mode"] = time.monotonic() + 4      # hold the new mode ~5 s against late readings
                bw = self.cfg.get("bw_by_kind", {}).get(kind, {}).get("bw") or self.DEFAULT_BW.get(kind)
                if bw:
                    self.bw_var.set(bw)           # show the new width at once too
                    self.touched["bw"] = time.monotonic() + 4
            self.root.after(300, lambda n=m["name"]: self.run_macro(n, quick=True, only_changed=True))
            return
        mode = self.pick_mode(kind, self.freq or 14_000_000)
        if not mode:
            self.log("flrig's mode list has no data mode for this rig.")
            return
        self.set_mode(mode)
        self.touched["mode"] = time.monotonic() + 4
        bw = self.cfg.get("bw_by_kind", {}).get(kind, {}).get("bw") or self.DEFAULT_BW.get(kind)
        if bw:
            self.bw_var.set(bw)
            self.touched["bw"] = time.monotonic() + 4

    def pick_band(self, b):
        kind = memory_kind(self.mode)
        if kind == "voice" and b[3] is None:      # 30 m: no phone
            kind = "data"
        start = {"voice": b[3], "data": b[4], "cw": b[3] if b[0] == "60" else b[1] + 25_000}[kind]   # CW: low end
        hz = self.cfg.get("band_memory", {}).get(f"{b[0]}:{kind}") or start
        self.tune_to(hz)
        self._band_rf(b[0])                       # RF gain per band: at once, not on the next poll
        if kind == "cw":                          # stay in CW / RTTY
            return
        mode = self.pick_mode(kind, hz)
        if mode and mode != self.mode:
            self.set_mode(mode)

    def set_bw(self):
        text = self.bw_var.get()
        if not text or not self._need_link():
            return
        idx = self.bws.index(text) if text in self.bws else 0
        self._touch("bw")
        mem = self._kind_memory("bw_by_kind")
        if mem is not None:
            mem["bw"] = text
            fil = self.ctl_values.get("filter")
            if fil in (1, 2, 3):                  # IC-7300: each filter keeps its own width (11-16b)
                mem.setdefault("bw_fil", {})[str(fil)] = text
                self.cfg.get("fil_width_sent", {}).pop(f"{memory_kind(self.mode)}:{fil}", None)
            save_config(self.cfg)
        self.worker.submit(lambda w: w.set_bandwidth(text, idx))

    def tune(self):
        if not self._need_link():
            return
        if self._has_macros() and self.macro_state.get("1615") == 0:
            self.log("TUNE: the radio's TUNER SELECT is OFF (No Tuner) - pick ATAS or External Tuner first.")
            return
        self.worker.submit(lambda w: w.tune())

    def _kind_memory(self, section):
        """cfg["by_kind"][section][voice|data] for the current mode (None if mode unknown)."""
        if not self.mode:
            return None
        kind = memory_kind(self.mode)
        return self.cfg.setdefault(section, {}).setdefault(kind, {})

    def set_control(self, ctl, value, remember=True):
        if not self.profile or not self._need_link():
            return
        mem = self._kind_memory("ctl_by_kind") if remember else None
        if mem is not None:
            mem[ctl.key] = value
            save_config(self.cfg)
        self.ctl_values[ctl.key] = value
        self._show_ctl(ctl.key, value)
        if ctl.key == "filter":
            self.worker.submit(lambda w: w.set_filter(ctl, value))
            return
        if ctl.key == "bkin":                    # FT-891 needs BI + menu 07-08 (11-09a)
            self.worker.submit(lambda w: w.set_bkin(value))
            return
        s = self.profile.set_string(ctl, value)

        def job(w):
            w.cat(s)
            w.read_control(ctl)
        self.worker.submit(job)

    LEVEL_METHODS = {"power": "rig.set_power", "micgain": "rig.set_micgain",
                     "rfgain": "rig.set_rfgain", "volume": "rig.set_volume"}
    LEVEL_NAMES = {"power": "RF Power", "micgain": "Mic Gain", "rfgain": "RF Gain", "volume": "AF Volume"}

    def slider_moved(self, key, method, value, remember=True):
        v = int(value)
        self.levels[key] = v
        if key == "rfgain" and remember and self.rf_band_var.get() and getattr(self, "rf_band", None):
            self.cfg.setdefault("rf_by_band", {})[self._rf_key(self.rf_band)] = v
        if key == "volume" and remember and self.muted_vol is not None:
            self.muted_vol = None                 # you set the volume yourself: no longer muted
            self._show_mute()
        if self.mode and remember:        # remember it for this kind of mode (voice / data)
            kind = memory_kind(self.mode)
            self.cfg.setdefault("levels_by_kind", {}).setdefault(kind, {})[key] = v
            save_config(self.cfg)
        self._touch(key)
        if key in self.slider_jobs:
            self.root.after_cancel(self.slider_jobs[key])
        self.slider_jobs[key] = self.root.after(
            150, lambda: self.connected and self.worker.submit(lambda w: w.set_level(key, method, v)))

    # ---------------- RF gain per band ----------------
    def _rf_key(self, band):
        return f"{getattr(self.profile, 'name', '?')}:{band}"

    def _band_rf(self, band):
        """Band changed (BAND button, the radio's knob...): save the old band's RF gain
        - whatever it is now, even if set on the radio - and put back the new band's."""
        last = getattr(self, "rf_band", None)
        self.rf_band = band
        if band == last or last is None or band is None or not self.rf_band_var.get():
            return
        mem = self.cfg.setdefault("rf_by_band", {})
        mem[self._rf_key(last)] = self.sliders["rfgain"].get()
        v = mem.get(self._rf_key(band))
        if v is None or v == self.sliders["rfgain"].get():
            return
        self.sliders["rfgain"].set(v)
        self.slider_moved("rfgain", "rig.set_rfgain", v, remember=False)
        self.log(f"RF gain {v} for {band} m (RF gain per band)")

    def _restore_levels(self, kind):
        """The FT-891 (and IC-7300) keep RF power, mic gain, RF gain and AF volume radio-wide,
        not per VFO. When the radio goes from a voice mode to a data mode (A<>B, Voice/Data,
        a macro or the radio's own controls), put back the levels last set for that kind."""
        if not self.levels_var.get():
            return
        saved = self.cfg.get("levels_by_kind", {}).get(kind, {})
        done = []
        for key, v in saved.items():
            if key not in self.sliders or self.sliders[key].get() == v:
                continue
            if key == "rfgain" and self.rf_band_var.get():
                continue                          # RF gain per band decides RF gain
            self.sliders[key].set(v)
            self.levels[key] = v
            self._touch(key)
            meth = self.LEVEL_METHODS[key]
            self.worker.submit(lambda w, k=key, m=meth, val=v: w.set_level(k, m, val))
            done.append(f"{self.LEVEL_NAMES[key]} {v}")
        # receive filters the radio keeps radio-wide (FT-891: DNR, Notch, DNF) - put back
        # whatever differs from what was last set for this kind
        for key, v in self.cfg.get("ctl_by_kind", {}).get(kind, {}).items():
            ctl = next((c for c in (self.profile.controls if self.profile else []) if c.key == key), None)
            if ctl is not None and self.ctl_values.get(key) is not None and self.ctl_values[key] != v:
                self.set_control(ctl, v, remember=False)
                done.append(f"{ctl.label} {'on' if v == 1 and ctl.kind == 'toggle' else v}")
        if self._restore_bw(kind):
            done.append(f"bandwidth {self.cfg.get('bw_by_kind', {}).get(kind, {}).get('bw') or self.DEFAULT_BW.get(kind)}")
        if done:
            self.log(f"{ {'cw': 'CW'}.get(kind, kind.title())} settings put back: " + ", ".join(done))

    CW_ONLY = ("bkin",)

    def _show_cw_rows(self):
        cw = memory_kind(self.mode) == "cw"
        for w in getattr(self, "cw_only", []):
            if w.winfo_exists():
                w.grid() if cw else w.grid_remove()

    DEFAULT_BW = {"voice": "2400", "data": "3000", "cw": "500"}   # until the operator picks their own

    def _restore_bw(self, kind, wait=False):
        mem = self.cfg.get("bw_by_kind", {}).get(kind, {})
        fil = self.ctl_values.get("filter")
        want = (mem.get("bw_fil", {}).get(str(fil)) if fil in (1, 2, 3) else None) \
            or mem.get("bw") or self.DEFAULT_BW.get(kind)
        if wait:                                  # mode just changed: wait for its width list (_on_tables)
            self.pending_bw = kind
            return bool(want)
        if not want or want not in self.bws:      # always send: the box may already show it (11-06h)
            return False
        self.bw_var.set(want)
        self.set_bw()
        return True

    def _mini_opts_changed(self):
        self.mini.set_options(auto=bool(self.mini_auto_var.get()), always=bool(self.mini_always_var.get()))

    def _lv_opts_changed(self):
        self.mini_lv.set_options(auto=bool(self.lv_auto_var.get()), always=bool(self.lv_always_var.get()))
        if self.lv_auto_var.get() and not self.ptt:
            self.mini_lv.show(manual=False)

    # Shift + letter shortcuts, the same on both radios: (key, action)
    HOTKEYS = (("V", "voice"), ("D", "data"), ("E", "edit"), ("A", "vfo_a"), ("B", "vfo_b"),
               ("Z", "mini"), ("L", "levels"), ("W", "waterfall"),
               ("M", "mute"),
               ("G", "goto"))
    HOTKEY_TEXT = {"voice": "Apply Voice settings", "data": "Apply Data settings", "edit": "Edit Rig Settings",
                   "vfo_a": "VFO A", "vfo_b": "VFO B",
                   "mini": "Mini Meter", "levels": "Mini Levels", "waterfall": "Waterfall on / off",
                   "mute": "Mute / unmute AF Volume", "goto": "Go to a frequency (kHz)"}

    def _hotkey(self, e, action):
        """Shift + letter, except while typing in a text box (so capitals still work there)."""
        try:
            if e.widget.winfo_class() in ("Entry", "TEntry", "TCombobox", "Text", "Spinbox", "TSpinbox"):
                return None
        except (AttributeError, tk.TclError):
            pass
        self.do_hotkey(action)
        return "break"

    def do_hotkey(self, action):
        if action == "mute":
            return self.toggle_mute()
        if action == "goto":
            return self.goto_box()
        if action == "mini":
            self.mini.toggle()
        elif action == "levels":
            self.mini_lv.toggle()
        elif action == "waterfall":
            self.toggle_waterfall()
        elif action == "edit":
            self.open_macro_editor()
        elif action in ("voice", "data"):
            self.set_voice_data(action)           # same as the mode row's button (runs the Rig Setting of that name)
        elif action in ("vfo_a", "vfo_b"):
            self.vfo_action("A" if action == "vfo_a" else "B")     # FT-891: by swapping

    HIDDEN_HOTKEYS = ("waterfall",)   # 11-14e: waterfall still being worked on - Shift+W / Ctrl+W work, not listed

    def hotkey_menu(self):
        m = self._menu(self.root)
        for key, action in self.HOTKEYS:
            if action in self.HIDDEN_HOTKEYS:
                continue
            m.add_command(label=self.HOTKEY_TEXT[action], accelerator=f"Shift+{key}",
                          command=lambda a=action: self.do_hotkey(a))
        m.add_separator()
        m.add_command(label="RigPanel forward / back (from any program)", accelerator="tap Ctrl",
                      command=self.toggle_front)
        b = self.keys_btn
        popup_menu(m, b.winfo_rootx(), b.winfo_rooty() + b.winfo_height())

    # ---------------- FT-891 macros ----------------
    def macro_list(self):
        """The operator's macros (a fresh copy). Older configs with just Voice/Digital are upgraded."""
        saved = self.cfg.get(MACROS.cfg_key)
        if isinstance(saved, list) and all(isinstance(m, dict) and m.get("name") for m in saved):
            return json.loads(json.dumps(saved))
        lst = json.loads(json.dumps(MACROS.defaults))
        old = self.cfg.get("ft891_macros") if MACROS.rig == "FT-891" else None
        if isinstance(old, dict):
            for m in lst:
                if m["name"] in old and isinstance(old[m["name"]], dict):
                    m["items"] = dict(old[m["name"]])
        return lst

    def save_macro_list(self, lst):
        self.cfg[MACROS.cfg_key] = json.loads(json.dumps(lst))
        self.cfg.pop("ft891_macros", None)
        save_config(self.cfg)
        self._build_macro_buttons()
        self._update_macro_row()

    def _find_macro(self, name):
        return next((m for m in self.macro_list() if m["name"] == name), None)

    def _has_macros(self):
        return bool(getattr(self.profile, "has_macros", False))

    def _build_macro_buttons(self):
        for w in self.macro_inner.winfo_children():
            w.destroy()
        self.macro_btns = {}
        # a macro made only of menu items this radio won't do over CAT can't do anything:
        # leave its button off (on the operator's FT-891: the ATAS / tuner macros)
        kinds = {n.lower() for n in self.KIND_NAMES.values()}     # Voice / Data / CW: run by the mode row
        shown = [m for m in self.macro_list() if m.get("show", True) and m["name"].strip().lower() not in kinds
                 and not (m["items"] and set(m["items"]) <= self.ex_unsupported)]
        groups = [(g, [m for m in shown if m.get("group", "Operating") == g]) for g in MACROS.groups]
        one_line = len(shown) <= 7
        line = None
        go = dict(on_color=C["go"], on_fg=C["go_fg"], font=(FONT.ui, 11, "bold"))
        for g, ms in groups:
            if not ms:
                continue
            if line is None or not one_line:
                line = tk.Frame(self.macro_inner, bg=C["panel"])
                line.pack(anchor="w", pady=1)
            label(line, "RIG SETTINGS:" if g == "Operating" else "ANTENNA:", fg=C["title"], size=11).pack(
                side="left", padx=(0 if not line.winfo_children()[:-1] else 14, 8))
            for m in ms:
                b = FlatButton(line, m["name"], command=lambda n=m["name"]: self.run_macro(n), **go)
                b.config(padx=16, pady=5)
                b.pack(side="left", padx=(0, 6))
                self.macro_btns[m["name"]] = b
                Tooltip(b, f"Apply {m['name']} Settings")
        self.refresh_macro_buttons()

    def _update_macro_row(self):
        if self._has_macros():
            if not self.macro_row.winfo_ismapped():
                self.macro_row.pack(fill="x", padx=8, pady=(8, 0), before=self.mid)
            codes = set(MACROS.always_read)         # FT-891: TUNE checks 16-15 TUNER SELECT
            for m in self.macro_list():
                codes |= {k for k in m["items"] if k in MACROS.menu}
            first = set()
            for k in self.KIND_NAMES:
                m = self._kind_macro(k)
                first |= {c for c in (m["items"] if m else {}) if c in MACROS.menu}
            self.worker.submit(lambda w: (setattr(w, "macro_codes", codes), setattr(w, "macro_first", first),
                                          setattr(w, "macro_read_due", 0.0)))
        else:
            self.macro_row.pack_forget()
            self.worker.submit(lambda w: setattr(w, "macro_codes", set()))
        if self.root.state() == "normal" and not self.wf_shown:
            self.root.geometry("")
        self.refresh_macro_buttons()

    def _macro_steps(self, name):
        m = self._find_macro(name)
        if m is None:
            raise ValueError("that macro no longer exists")
        steps = []
        kind_button = m["name"].strip().lower() in {n.lower() for n in self.KIND_NAMES.values()}
        kind_of_button = next((k for k, n in self.KIND_NAMES.items() if n.lower() == m["name"].strip().lower()), None)
        for key in MACROS.all_items:                   # fixed order: mode, width, menus, filters, ATAS, tuner
            v = m["items"].get(key)
            if not v or v == SKIP:
                continue
            if kind_button and key in self.POWER_ITEMS:
                continue      # Voice / Data / CW leave power to the slider (operator, 11-06i)
            if kind_button and key == "MODE" and v != SSB_BY_BAND and memory_kind(v) != kind_of_button:
                continue      # e.g. Mode CW saved in the Voice setting by "Read from radio" (11-06k)
            if key in MACROS.menu:
                steps.append((key, menu_encode(key, v)))
            elif key.startswith("WIDTH"):
                steps.append((key, int(v)))
            else:
                steps.append((key, v))
        return steps

    @staticmethod
    def kind_width(items):
        """The width a Rig Setting gives its starting filter (Width, or Width FILn of its Filter)."""
        n = str(items.get("FILTER") or "FIL1")[-1]
        return items.get(f"WIDTH{n}") or items.get("WIDTH")

    def run_macro(self, name, quick=False, only_changed=False):
        if not self._need_link() or not self._has_macros():
            return
        if self.ptt:
            self.log(f"{name}: not while transmitting.")
            return
        if self.macro_busy:
            self.log(f"Still applying {self.macro_busy}...")
            return
        try:
            steps = self._macro_steps(name)
        except ValueError as e:
            self.log(f"{name}: {e} - fix it with Edit...")
            return
        if only_changed:
            steps = self._only_changed(name, steps)
            if not steps:
                self.log(f"{name}: the radio already matches - nothing to send.")
                self._mark_kind_buttons()
                return
        self.macro_busy = name
        self.macro_running = (name, steps)
        self._remember_macro_ctls(name, steps)
        b = self.macro_btns.get(name)
        if b is not None:
            b.set_on(True, C["amber"])
        self.log(f"{name}: setting {len(steps)} item(s)...")
        self.worker.submit(lambda w: w.run_macro(name, steps, quick))
        token = object()
        self.macro_token = token

        def unstick():        # never leave a macro "applying" if its result got lost
            if self.macro_busy == name and getattr(self, "macro_token", None) is token:
                self._macro_done({"name": name, "ok": 0, "failed": ["no answer from flrig in 90 s"]})
        self.root.after(90_000, unstick)

    def _remember_macro_ctls(self, name, steps):
        """A Rig Setting's NB / NR / Notch / ... become that kind's remembered receive filters, so Separate
        settings for Voice, Data and CW doesn't put the old ones back right after (11-16d)."""
        if not self.profile:
            return
        kind = next((k for k, n in self.KIND_NAMES.items() if n.lower() == name.strip().lower()), None)
        if kind is None:
            mode = next((v for k, v in steps if k == "MODE"), None)
            kind = "voice" if mode == SSB_BY_BAND else memory_kind(mode) if mode else \
                (memory_kind(self.mode) if self.mode else None)
        if kind is None:
            return
        mem = self.cfg.setdefault("ctl_by_kind", {}).setdefault(kind, {})
        changed = False
        for key, v in steps:
            ck = MACROS.filters.get(key)
            if ck and v in ("ON", "OFF"):
                mem[ck] = 1 if v == "ON" else 0
                changed = True
        if changed:
            save_config(self.cfg)

    def _macro_done(self, r):
        self.macro_busy = None
        name, steps = getattr(self, "macro_running", (None, []))
        if name == r["name"]:
            kind = self._run_kind(name, steps)
            for key, val in steps:
                if key in ("WIDTH1", "WIDTH2", "WIDTH3") and item_label(key) not in r["failed"]:
                    self.cfg.setdefault("fil_width_sent", {})[f"{kind}:{key[-1]}"] = str(val)
            save_config(self.cfg)
        b = self.macro_btns.get(r["name"])
        if b is not None and b.winfo_exists():
            b.on_color = C["go"]
        cat_only = [f for f in r["failed"] if "not available over CAT" in f]
        real = [f for f in r["failed"] if f not in cat_only]
        skipped = ", ".join(f.split(" (")[0].split(" ", 1)[0] for f in cat_only)
        if real:
            msg, col = f"{r['name']}: {r['ok']} set, NOT confirmed: {', '.join(real)} (click the version text for the log)", "red"
        elif cat_only and not r["ok"]:
            msg, col = f"{r['name']}: nothing to do - this radio won't allow menu {skipped} over CAT; set it on the radio", "amber"
        elif cat_only:
            msg, col = f"{r['name']}: {r['ok']} settings confirmed ✓ (menu {skipped} skipped - not over CAT)", "green"
        else:
            msg, col = f"{r['name']}: all {r['ok']} settings applied and confirmed \u2713", "green"
        self.log(msg)
        if self.macro_win is not None and self.macro_win.winfo_exists():
            self.macro_win.say(msg, C[col])          # Save (in use): the answer shows in the editor too
        self.refresh_macro_buttons()

    def _macro_matches(self, name):
        try:
            if any(self.macro_state.get(k) is None for k, _ in self._macro_steps(name) if k in MACROS.menu
                   and k not in self.ex_unsupported):
                return False                  # green only once everything has been read
        except ValueError:
            return False
        diffs, checked = self._macro_diffs(name)
        return diffs == [] and checked > 0

    def _macro_diffs(self, name):
        """([labels of the settings the radio doesn't match], number checked)."""
        st = self.macro_state
        diffs = []
        try:
            steps = self._macro_steps(name)
        except ValueError:
            return ["?"], 0
        if not steps:
            return [], 0
        checked = 0
        own_filter = any(k == "FILTER" for k, _ in steps)
        for key, val in steps:
            if key in ("WIDTH1", "WIDTH2", "WIDTH3"):
                continue          # only the filter in use shows its width
            if own_filter and key in ("FILTER", "WIDTH"):
                continue          # the filter is only the starting choice - you switch FIL1/2/3 as signals need
            ok = self._step_ok(key, val)
            if ok is None:
                continue                               # the radio / flrig won't tell us: ignore it
            if not ok:
                diffs.append(self._diff_label(key))
            checked += 1
        return diffs, checked

    def _step_ok(self, key, val):
        """Does the radio already have this Rig Setting step? None = not known (yet)."""
        st = self.macro_state
        if key == "MODE":
            if not self.mode:
                return None
            return self.mode in ("LSB", "USB") if val == SSB_BY_BAND else self.mode == val
        if key == "WIDTH":
            got = parse_hz(self.bw_var.get() or "")
            return None if got is None else abs(got - val) <= 100
        if key == "FILTER":
            got = self.ctl_values.get("filter")
            return None if got is None else got == int(str(val)[-1])
        if key == "BKIN":
            got = self.ctl_values.get("bkin")
            if got is None:
                return None
            want = BKIN_VALUES.index(val)
            if len(next((c.options for c in self.profile.controls if c.key == "bkin"), ())) == 2:
                want = min(want, 1)                # BKIN OFF / ON radios
            return got == want
        if key in MACROS.filters:
            got = self.ctl_values.get(MACROS.filters[key])
            return None if got is None else bool(got) == (val == "ON")
        if key in self.ex_unsupported or st.get(key) == UNREADABLE:
            return None
        if key in MACROS.menu:
            return st.get(key) == val if st.get(key) is not None else None    # not read yet
        return False

    def _only_changed(self, name, steps):
        """11-16h: Save and Default Settings send only what differs (6 s -> ~1 s on flrig 2.0.09).
        Width FIL1/2/3 are sent again only if a different width went to that filter since."""
        kind = self._run_kind(name, steps)
        sent = self.cfg.get("fil_width_sent", {})
        out = []
        for key, val in steps:
            if key in ("WIDTH1", "WIDTH2", "WIDTH3"):
                if sent.get(f"{kind}:{key[-1]}") != str(val):
                    out.append((key, val))
            elif key in ("FILTER", "WIDTH"):
                out.append((key, val))          # decided below
            elif self._step_ok(key, val) is not True:
                out.append((key, val))
        if not any(k in ("WIDTH1", "WIDTH2", "WIDTH3") for k, _ in out):
            out = [(k, v) for k, v in out if not (k in ("FILTER", "WIDTH") and self._step_ok(k, v))]
        return out

    def _run_kind(self, name, steps):
        kind = next((k for k, n in self.KIND_NAMES.items() if n.lower() == name.strip().lower()), None)
        if kind is None:
            mode = next((v for k, v in steps if k == "MODE"), None)
            kind = "voice" if mode == SSB_BY_BAND else memory_kind(mode) if mode else \
                (memory_kind(self.mode) if self.mode else None)
        return kind

    def _diff_label(self, key):
        if key in MACROS.filters:
            ck = MACROS.filters[key]
            return next((c.label for c in self.profile.controls if c.key == ck), key) if self.profile else key
        return {"MODE": "Mode", "WIDTH": "Width", "BKIN": "BKIN"}.get(key) or item_label(key)

    def refresh_macro_buttons(self):
        if not self._has_macros():
            return
        for name, b in self.macro_btns.items():
            if not b.winfo_exists() or name == self.macro_busy:
                continue
            b.set_on(self._macro_matches(name), C["go"])
        self._mark_kind_buttons()

    def _mark_kind_buttons(self):
        """11-16g: under RECEIVE / FILTERS a "Default Settings" button (always there when the mode in use has a
        Voice / Data / CW Rig Setting) puts that Rig Setting back; beside it, in amber, what the radio has changed
        from it. RigPanel never puts it back on its own - your last settings stay, also after a restart."""
        note = getattr(self, "kind_note", None)
        if note is None or not note.winfo_exists():
            return
        here = memory_kind(self.mode) if self.mode else None
        m = self._kind_macro(here) if here and self._has_macros() and self.connected else None
        text = ""
        if m is not None and self.macro_busy is None and not self._recent("mode"):
            try:
                keys = [key for key, _ in self._macro_steps(m["name"]) if key in MACROS.menu]
            except ValueError:
                keys = []
            if True:              # 11-16i: show what's known at once; menu items join as they're read
                diffs, _ = self._macro_diffs(m["name"])
                if diffs:
                    shown = ", ".join(diffs[:4]) + (f" and {len(diffs) - 4} more" if len(diffs) > 4 else "")
                    text = f"\u26a0 Changed from your {self.KIND_NAMES[here]} settings: {shown}"
        state = (m is not None, here, text)
        if state == self.kind_note_shown:
            return
        self.kind_note_shown = state
        if m is None:
            note.pack_forget()
            return
        self.kind_note_btn.command = lambda k=here: self.set_voice_data(k)
        self.kind_note_btn.set_on(bool(text), C["amber"])
        self.kind_note_lbl.config(text=text)
        if not note.winfo_ismapped():
            note.pack(anchor="w", fill="x", pady=(8, 0), before=self.profile_lbl)

    def open_macro_editor(self):
        if self.macro_win is not None and self.macro_win.winfo_exists():
            self.macro_win.lift()
            return
        self.macro_win = MacroBuilder(self)

    # ---------------- waterfall on/off, pop-out, Compact View ----------------
    def toggle_waterfall(self):
        """Show or hide the waterfall panel. Hidden = smaller window and no audio capture."""
        self.wf_shown = not self.wf_shown
        self.cfg["wf_show"] = self.wf_shown
        if self.wf_shown:
            self.wf.frame.pack(fill="both", expand=True, padx=8, pady=(8, 0), before=self.wf_spacer)
        else:
            self.wf.frame.pack_forget()
        if self.root.state() == "normal":
            self.root.geometry("")              # let the window grow / shrink to fit
        self.wf_btn.set_on(self.wf_shown)
        self._update_audio()
        save_config(self.cfg)

    def _float_visible(self):
        return self.float_wf is not None and self.float_wf.winfo_exists() and self.float_wf.visible()

    def _update_audio(self):
        """Capture audio only while some waterfall is actually on screen."""
        if not self.wf.ok:
            return
        need = self.wf_shown or self._float_visible()
        if need and not self.wf.running:
            self.wf.start()
        elif not need and self.wf.running:
            self.wf.stop()

    def show_float(self):
        if not self.wf.ok:
            self.log("The waterfall needs numpy, sounddevice and pillow (see README).")
            return
        if self.float_wf is None or not self.float_wf.winfo_exists():
            self.float_wf = FloatWaterfall(self)
        self.float_wf.set_compact(self.compact)
        self.float_wf.deiconify()
        self.float_wf.lift()
        self.float_wf.update_info()
        self._update_audio()
        self._sync_view_buttons()

    def hide_float(self):
        if self.float_wf is not None and self.float_wf.winfo_exists():
            self.float_wf.remember()
            self.float_wf.withdraw()
            save_config(self.cfg)
        if self.compact:                       # closing it in Compact View brings the panel back
            self.exit_compact()
        self._update_audio()
        self._sync_view_buttons()

    def toggle_float(self):
        if self.float_wf is not None and self.float_wf.winfo_exists() and self.float_wf.visible():
            self.hide_float()
        else:
            self.show_float()

    def enter_compact(self):
        """Main panel to the taskbar; the mini meter stays, plus the waterfall window
        when the Waterfall is switched on."""
        self.mini_before_compact = self.mini.visible()
        self.compact = True
        if self.wf_shown and self.wf.ok:
            self.show_float()
        self.mini.show(manual=True)
        self.mini.set_compact(True)
        self.root.iconify()
        self._sync_view_buttons()
        self.log("Compact View - click Full Panel to come back.")

    def exit_compact(self):
        if not self.compact:
            return
        self.compact = False
        self.root.deiconify()
        self.root.lift()
        if self.float_wf is not None and self.float_wf.winfo_exists():
            self.float_wf.remember()
            self.float_wf.withdraw()
        self.mini.set_compact(False)
        if not self.mini_before_compact and not self.mini.always_var.get():
            self.mini.hide()
        self._update_audio()
        save_config(self.cfg)
        self._sync_view_buttons()

    def _on_main_restored(self, e):
        # main panel opened from the taskbar while in Compact View: leave the windows as they are
        if e.widget is self.root and self.compact:
            self.compact = False
            if self.float_wf is not None and self.float_wf.winfo_exists():
                self.float_wf.set_compact(False)
            self.mini.set_compact(False)
            self._sync_view_buttons()

    def _sync_view_buttons(self):
        on = self.float_wf is not None and self.float_wf.winfo_exists() and self.float_wf.visible()
        for name, state in (("float_btn", on), ("compact_btn", self.compact)):
            b = getattr(self, name, None)
            if b is not None and b.winfo_exists():
                b.set_on(state)

    def close(self):
        self.cfg["rig"] = self.rig_var.get()
        self.cfg["theme"] = self.theme
        if self.float_wf is not None and self.float_wf.winfo_exists():
            self.float_wf.remember()
        if getattr(self, "wf", None):
            self.wf.save(self.cfg)
            if self.wf.ok:
                self.wf.stop()
        save_config(self.cfg)
        self.worker.alive = False
        self.root.withdraw()                    # window goes away at once; flrig gets a clean goodbye
        self.worker.join(timeout=3.0)           # let a request in progress finish (never cut flrig off mid-reply)
        self.root.destroy()

    def _restart_with(self, cfg, msg):
        """Rebuild RigPanel in the same window with new settings (like a restart, without one)."""
        if getattr(self, "wf", None) and self.wf.ok:
            self.wf.stop()
        self.worker.alive = False
        self.dead = True                        # this App's clock, pump and waterfall timers stop themselves
        for w in self.root.winfo_children():
            w.destroy()
        save_config(cfg)
        new = App(self.root)
        new.root.after(2500, lambda: new.log(msg))      # after the "connected" message
