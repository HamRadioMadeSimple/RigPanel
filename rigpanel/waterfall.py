"""Audio waterfall (main panel) and its pop-out window."""
from .core import *  # noqa: F401,F403
from .radios import *  # noqa: F401,F403
from .worker import *  # noqa: F401,F403
from .widgets import *  # noqa: F401,F403

# --------------------------------------------------------------------------
# Audio waterfall (radio's USB audio codec)
# --------------------------------------------------------------------------
DEMO_DEVICE = "Demo (test tones)"


class Waterfall:
    """Receive-audio waterfall, tuned to look like the usual digital-mode waterfalls: ~3 Hz
    frequency bins, several overlapping FFTs averaged into each line, and a dark
    noise floor so signals stand out."""
    W, H, FMAX = 780, 170, 3500        # W and H follow the window; these are the starting size
    AXIS = 18                          # pixels under the image for the Hz scale
    TICK_MS = 100                                  # one FFT every 100 ms
    BIN_HZ = 3.0                                   # target frequency resolution
    SPEEDS = {"Fast": 1, "Normal": 3, "Slow": 6}   # FFTs averaged per waterfall line
    NOISE_BAND = (300, 2700)                       # where to measure the noise floor

    def __init__(self, parent, app):
        self.app = app
        self.frame = section(parent, "Audio Waterfall  (0 - 3.5 kHz)")
        if np is None or Image is None:
            tk.Label(self.frame, bg=C["panel"], fg=C["amber"], justify="left",
                     text="Waterfall needs extra packages:  pip install numpy sounddevice pillow").pack(anchor="w")
            self.ok = False
            return
        self.ok = True
        tbtn = tk.Frame(self.frame, bg=C["panel"])
        tbtn.place(relx=1.0, x=0, y=-2, anchor="ne")
        go = dict(on_color=C["go"], on_fg=C["go_fg"], font=(FONT.ui, 9, "bold"))
        app.float_btn = FlatButton(tbtn, "Pop Out  (Ctrl+W)", command=app.toggle_float, **go)
        app.float_btn.pack(side="right")
        bar = tk.Frame(self.frame, bg=C["panel"])
        bar.pack(fill="x", pady=(0, 6))
        label(bar, "Audio in:").pack(side="left")
        self.dev_var = tk.StringVar()
        self.dev_combo = ttk.Combobox(bar, textvariable=self.dev_var, width=22, state="readonly")
        self.dev_combo.pack(side="left", padx=6)
        self.dev_combo.bind("<<ComboboxSelected>>", lambda e: self.start())
        self.run_btn = FlatButton(bar, "Start", command=self.toggle, font=(FONT.ui, 9))
        self.run_btn.pack(side="left", padx=4)
        self.auto_var = tk.BooleanVar(value=app.cfg.get("wf_auto", True))
        checkbox(bar, "Auto level", self.auto_var).pack(side="left", padx=8)
        label(bar, "Speed:").pack(side="left")
        self.speed_var = tk.StringVar(value=app.cfg.get("wf_speed", "Normal"))
        ttk.Combobox(bar, textvariable=self.speed_var, values=list(self.SPEEDS), width=7,
                     state="readonly").pack(side="left", padx=(4, 8))
        label(bar, "Floor:").pack(side="left")
        self.floor = tk.Scale(bar, from_=-160, to=-20, orient="horizontal", length=90, showvalue=False,
                              bg=C["panel"], troughcolor=C["panel2"], highlightthickness=0, bd=0)
        self.floor.set(app.cfg.get("wf_floor_db", -110))
        self.floor.pack(side="left")
        label(bar, "Contrast:").pack(side="left", padx=(6, 0))
        # Contrast = how many dB above the floor reach full brightness (smaller = punchier)
        self.rng = tk.Scale(bar, from_=60, to=15, orient="horizontal", length=80, showvalue=False,
                            bg=C["panel"], troughcolor=C["panel2"], highlightthickness=0, bd=0)
        self.rng.set(app.cfg.get("wf_contrast_db", 24))
        self.rng.pack(side="left")

        self.canvas = tk.Canvas(self.frame, width=600, height=120 + self.AXIS, bg="black", highlightthickness=0)
        self.canvas.pack(fill="both", expand=True)
        self.resize_job = None
        self.canvas.bind("<Configure>", self._on_configure)
        self._draw_axis()

        self.img = np.zeros((self.H, self.W, 3), np.uint8)
        self.photo = ImageTk.PhotoImage(Image.fromarray(self.img))
        self.img_item = self.canvas.create_image(0, 0, image=self.photo, anchor="nw")
        self.lut = self._lut()
        self.lock = threading.Lock()
        self._setup_fft(48000)
        self.stream = None
        self.running = False
        self.sr = 48000
        self.demo_t = 0.0
        self.noise_est = None
        self._fill_devices()            # audio starts only when a waterfall is on screen (App._update_audio)

    def _draw_axis(self):
        self.canvas.delete("axis")
        step = 250 if self.W >= 1100 else 500
        for hz in range(0, self.FMAX + 1, step):
            x = hz / self.FMAX * (self.W - 1)
            self.canvas.create_line(x, self.H, x, self.H + 5, fill=C["dim"], tags="axis")
            anchor = "nw" if hz == 0 else ("ne" if hz == self.FMAX else "n")
            self.canvas.create_text(x, self.H + 5, text=f"{hz}", fill=C["dim"], anchor=anchor,
                                    font=(FONT.ui, 8), tags="axis")

    def _on_configure(self, e):
        if self.resize_job:
            self.canvas.after_cancel(self.resize_job)
        self.resize_job = self.canvas.after(120, self._resize)

    def _resize(self):
        """Stretch the waterfall to the space it has (keeps the history, rescaled)."""
        self.resize_job = None
        w = max(200, self.canvas.winfo_width())
        h = max(60, self.canvas.winfo_height() - self.AXIS)
        if (w, h) == (self.W, self.H):
            return
        self.img = np.asarray(Image.fromarray(self.img).resize((w, h), Image.NEAREST)).copy()
        self.W, self.H = w, h
        self._map_columns()
        self._draw_axis()
        self.photo = ImageTk.PhotoImage(Image.fromarray(self.img))
        self.canvas.itemconfig(self.img_item, image=self.photo)

    def _setup_fft(self, sr):
        """FFT size for ~3 Hz bins at this sample rate, and the bin -> pixel-column map."""
        self.sr = sr
        n = 1
        while sr / n > self.BIN_HZ:
            n *= 2
        self.N = n                                           # 48 kHz -> 16384 (2.9 Hz bins)
        self.window = np.hanning(n).astype(np.float32)
        self.wnorm = float(np.sum(self.window) ** 2)
        with self.lock:
            self.buf = np.zeros(n, np.float32)
        self._map_columns()

    def _map_columns(self):
        """Which FFT bins land in each pixel column (depends on width and sample rate)."""
        n, sr = self.N, self.sr
        freqs = np.arange(n // 2 + 1) * sr / n
        edges = np.linspace(0, self.FMAX, self.W + 1)
        self.e0 = np.searchsorted(freqs, edges[:-1])
        self.e1 = np.searchsorted(freqs, edges[1:])
        centers = (edges[:-1] + edges[1:]) / 2
        self.nearest = np.clip(np.round(centers / (sr / n)).astype(int), 0, len(freqs) - 1)
        cx = (centers >= self.NOISE_BAND[0]) & (centers <= self.NOISE_BAND[1])
        self.noise_cols = cx
        self.acc = np.zeros(self.W)
        self.nacc = 0

    def _columns(self, p):
        """Average FFT power into the waterfall's pixel columns (no smearing between bins)."""
        csum = np.concatenate(([0.0], np.cumsum(p)))
        cnt = self.e1 - self.e0
        s = csum[self.e1] - csum[self.e0]
        return np.where(cnt > 0, s / np.maximum(cnt, 1), p[self.nearest])

    @staticmethod
    def _lut():
        # Digital-mode style: black/navy noise, blue weak signals, yellow -> orange strong ones
        stops = [(0, (0, 0, 0)), (0.18, (0, 0, 70)), (0.38, (0, 20, 170)), (0.55, (30, 110, 255)),
                 (0.7, (250, 240, 40)), (0.86, (255, 150, 0)), (1.0, (255, 255, 255))]
        xs = np.linspace(0, 1, 256)
        lut = np.zeros((256, 3), np.uint8)
        for c in range(3):
            lut[:, c] = np.interp(xs, [s[0] for s in stops], [s[1][c] for s in stops])
        return lut

    def _fill_devices(self):
        names = []
        self.dev_index = {}
        if sd is not None:
            try:
                for i, d in enumerate(sd.query_devices()):
                    if d.get("max_input_channels", 0) > 0:
                        label = f"{i}: {d['name']}"
                        names.append(label)
                        self.dev_index[label] = i
            except Exception:
                pass
        names.append(DEMO_DEVICE)
        self.dev_combo["values"] = names
        if sd is None:
            hint = ("sudo apt install libportaudio2" if SYS == "Linux" and "PortAudio" in SD_ERROR
                    else "pip install sounddevice")
            tk.Label(self.frame, text=f"No sound input available ({hint}) - only the Demo source works.",
                     bg=C["panel"], fg=C["amber"], font=(FONT.ui, 9)).pack(anchor="w", before=self.canvas)
        saved = self.app.cfg.get("audio_device", "")
        pick = next((n for n in names if saved and n.split(": ", 1)[-1] == saved.split(": ", 1)[-1]), None)
        if not pick:  # both radios show up as "USB Audio CODEC"
            pick = next((n for n in names if "USB AUDIO CODEC" in n.upper()), "")
        self.dev_var.set(pick)

    def toggle(self):
        if self.running:
            self.stop()
        else:
            self.start()

    def start(self):
        self.stop()
        name = self.dev_var.get()
        if not name:
            return
        self.app.cfg["audio_device"] = name
        if name != DEMO_DEVICE:
            if sd is None:
                self.app.log("sounddevice is not installed - pip install sounddevice")
                return
            idx = self.dev_index.get(name)
            try:
                self._setup_fft(int(sd.query_devices(idx)["default_samplerate"]) or 48000)
                try:
                    self.stream = sd.InputStream(device=idx, channels=1, samplerate=self.sr,
                                                 blocksize=1024, dtype="float32", callback=self._cb)
                except Exception as e1:   # some Linux hw: devices only open in stereo
                    if "channel" not in str(e1).lower():
                        raise
                    self.stream = sd.InputStream(device=idx, channels=2, samplerate=self.sr,
                                                 blocksize=1024, dtype="float32", callback=self._cb)
                self.stream.start()
            except Exception as e:
                self.stream = None
                msg = str(e)
                if any(k in msg.lower() for k in ("unavailable", "busy", "-9985", "-9996")):
                    msg = (f"'{name.split(': ', 1)[-1]}' is in use by another program (WSJT-X?)."
                           + (" On Linux pick 'pipewire' or 'pulse' in Audio in, and choose the radio as"
                              " RigPanel's input in Sound settings / pavucontrol." if SYS == "Linux" else ""))
                    self.app.log(msg)
                else:
                    self.app.log(f"Could not open audio device: {msg}")
                return
        else:
            self._setup_fft(12000)
        self.noise_est = None
        self.running = True
        self.run_btn.config(text="Stop")
        self.run_btn.set_on(True, C["green"])
        self._tick()

    def stop(self):
        self.running = False
        if self.stream is not None:
            try:
                self.stream.stop()
                self.stream.close()
            except Exception:
                pass
            self.stream = None
        if self.ok:
            self.run_btn.config(text="Start")
            self.run_btn.set_on(False)

    def _cb(self, indata, frames, time_info, status):
        x = indata[:, 0]
        with self.lock:
            n = len(x)
            if n >= self.N:
                self.buf[:] = x[-self.N:]
            else:
                self.buf[:-n] = self.buf[n:]
                self.buf[-n:] = x

    def _demo_fill(self):
        n = int(self.sr * self.TICK_MS / 1000)
        t = self.demo_t + np.arange(n) / self.sr
        self.demo_t = t[-1]
        sig = np.random.normal(0, 0.003, n)
        slot = int(self.demo_t // 3) % 4
        for k, base in enumerate((600, 1100, 1450, 1900, 2350, 2800)):
            if (k + slot) % 3:
                tone = base + 6.25 * ((self.demo_t * 6.25 + k) // 1 % 8)
                sig += 0.02 * np.sin(2 * np.pi * tone * t)
        with self.lock:
            self.buf[:-n] = self.buf[n:]
            self.buf[-n:] = sig.astype(np.float32)

    def _tick(self):
        if getattr(self.app, "dead", False):
            return
        if not self.running:
            return
        if self.dev_var.get() == DEMO_DEVICE:
            self._demo_fill()
        with self.lock:
            x = self.buf * self.window
        p = (np.abs(np.fft.rfft(x)) ** 2) / self.wnorm
        self.acc += self._columns(p)
        self.nacc += 1
        if self.nacc >= self.SPEEDS.get(self.speed_var.get(), 3):
            self._draw_line(10 * np.log10(self.acc / self.nacc + 1e-20))
            self.acc[:] = 0
            self.nacc = 0
        self.app.root.after(self.TICK_MS, self._tick)

    def _draw_line(self, db):
        if self.auto_var.get():
            # noise floor = median inside the passband (so the filtered-off region above
            # ~3 kHz doesn't drag it down); noise then sits near black
            noise = float(np.median(db[self.noise_cols]))
            self.noise_est = noise if self.noise_est is None else 0.85 * self.noise_est + 0.15 * noise
            self.floor.set(int(round(self.noise_est - 1)))
        floor, rng = self.floor.get(), max(5, self.rng.get())
        norm = np.clip((db - floor) / rng, 0, 1)
        self.img[1:] = self.img[:-1]
        self.img[0] = self.lut[(norm * 255).astype(np.int32)]
        self.photo = ImageTk.PhotoImage(Image.fromarray(self.img))
        self.canvas.itemconfig(self.img_item, image=self.photo)
        fw = self.app.float_wf
        if fw is not None and fw.visible():
            fw.push(norm, self.lut)

    def save(self, cfg):
        if self.ok:
            cfg["wf_auto"] = bool(self.auto_var.get())
            cfg["wf_floor_db"] = int(self.floor.get())
            cfg["wf_contrast_db"] = int(self.rng.get())
            cfg["wf_speed"] = self.speed_var.get()



# --------------------------------------------------------------------------
# Pop-out waterfall window (Ctrl+W) and Compact View
# --------------------------------------------------------------------------
class FloatWaterfall(tk.Toplevel):
    """Its own window with its own picture buffer, fed the same lines as the main
    waterfall, so it can be any size. Remembers where it was and how big."""
    AXIS = 18

    def __init__(self, app):
        super().__init__(app.root)
        self.app = app
        self.withdraw()
        self.title(f"{APP_NAME} - Waterfall")
        self.configure(bg=C["panel"])
        self.minsize(360, 160)
        self.protocol("WM_DELETE_WINDOW", app.hide_float)

        bar = tk.Frame(self, bg=C["panel"], padx=8, pady=5)
        bar.pack(fill="x")
        self.tx_lbl = tk.Label(bar, text=" RX ", bg=C["go"], fg=C["go_fg"], font=(FONT.ui, 9, "bold"))
        self.tx_lbl.pack(side="left")
        self.freq_lbl = tk.Label(bar, text="", bg=C["panel"], fg=C["freq"], font=(FONT.mono, 13, "bold"))
        self.freq_lbl.pack(side="left", padx=(10, 6))
        self.mode_lbl = tk.Label(bar, text="", bg=C["panel"], fg=C["fg"], font=(FONT.ui, 10, "bold"))
        self.mode_lbl.pack(side="left")
        self.full_btn = FlatButton(bar, "Full Panel", command=app.exit_compact, font=(FONT.ui, 9, "bold"),
                                   base=C["tx"], base_fg="#ffffff")
        self.mini_btn = FlatButton(bar, "Mini Meter", command=lambda: app.mini.toggle(), font=(FONT.ui, 9, "bold"),
                                   on_color=C["go"], on_fg=C["go_fg"])
        self.mini_btn.pack(side="right")
        self.top_var = tk.BooleanVar(value=app.cfg.get("wf_float_top", True))
        checkbox(bar, "On top", self.top_var, self._top_changed).pack(side="right", padx=8)

        self.canvas = tk.Canvas(self, bg="black", highlightthickness=0, width=780, height=220 + self.AXIS)
        self.canvas.pack(fill="both", expand=True)
        self.W, self.H = 780, 220
        self.img = np.zeros((self.H, self.W, 3), np.uint8)
        self.photo = ImageTk.PhotoImage(Image.fromarray(self.img))
        self.img_item = self.canvas.create_image(0, 0, image=self.photo, anchor="nw")
        self.resize_job = None
        self.canvas.bind("<Configure>", self._on_configure)
        self._draw_axis()
        self.attributes("-topmost", bool(self.top_var.get()))
        self._place()

    def visible(self):
        return self.state() == "normal"

    def _place(self):
        g = self.app.cfg.get("wf_float_geom")
        m = re.fullmatch(r"(\d+)x(\d+)([+-]-?\d+)([+-]-?\d+)", g or "")
        if not m:
            self.geometry("820x300")
            return
        w, h, x, y = int(m.group(1)), int(m.group(2)), int(m.group(3)), int(m.group(4))
        left, top, right, bottom = screen_bounds(self)
        x = max(left, min(x, right - min(w, 300)))       # keep it reachable if a monitor went away
        y = max(top, min(y, bottom - 80))
        self.geometry(f"{w}x{h}+{x}+{y}")

    def remember(self):
        if self.visible():
            self.app.cfg["wf_float_geom"] = self.geometry()

    def _top_changed(self):
        self.attributes("-topmost", bool(self.top_var.get()))
        self.app.cfg["wf_float_top"] = bool(self.top_var.get())

    def set_compact(self, on):
        if on:
            self.full_btn.pack(side="right", padx=(6, 0), before=self.mini_btn)
        else:
            self.full_btn.pack_forget()

    def _draw_axis(self):
        self.canvas.delete("axis")
        step = 250 if self.W >= 1100 else 500
        for hz in range(0, Waterfall.FMAX + 1, step):
            x = hz / Waterfall.FMAX * (self.W - 1)
            self.canvas.create_line(x, self.H, x, self.H + 5, fill=C["dim"], tags="axis")
            anchor = "nw" if hz == 0 else ("ne" if hz == Waterfall.FMAX else "n")
            self.canvas.create_text(x, self.H + 5, text=f"{hz}", fill=C["dim"], anchor=anchor,
                                    font=(FONT.ui, 8), tags="axis")

    def _on_configure(self, e):
        if self.resize_job:
            self.after_cancel(self.resize_job)
        self.resize_job = self.after(120, self._resize)

    def _resize(self):
        self.resize_job = None
        w = max(200, self.canvas.winfo_width())
        h = max(60, self.canvas.winfo_height() - self.AXIS)
        if (w, h) != (self.W, self.H):
            self.img = np.asarray(Image.fromarray(self.img).resize((w, h), Image.NEAREST)).copy()
            self.W, self.H = w, h
            self._draw_axis()
            self._show()
        self.remember()

    def _show(self):
        self.photo = ImageTk.PhotoImage(Image.fromarray(self.img))
        self.canvas.itemconfig(self.img_item, image=self.photo)

    def push(self, norm, lut):
        """One new waterfall line (0..1 per column of the main waterfall), resampled to this width."""
        row = np.interp(np.linspace(0, len(norm) - 1, self.W), np.arange(len(norm)), norm)
        self.img[1:] = self.img[:-1]
        self.img[0] = lut[(row * 255).astype(np.int32)]
        self._show()

    def update_info(self):
        a = self.app
        ptt = bool(a.ptt)
        self.tx_lbl.config(text=" TX " if ptt else " RX ", bg=C["tx"] if ptt else C["go"],
                           fg="#ffffff" if ptt else C["go_fg"])
        self.freq_lbl.config(text=f"{fmt_freq(a.freq)} MHz" if a.freq else "")
        self.mode_lbl.config(text=a.mode or "", fg=kind_color(a.mode))
        self.mini_btn.set_on(a.mini.visible())
