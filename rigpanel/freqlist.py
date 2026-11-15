"""Stored frequencies window."""
from .core import *  # noqa: F401,F403
from .radios import *  # noqa: F401,F403
from .worker import *  # noqa: F401,F403
from .widgets import *  # noqa: F401,F403
from .waterfall import *  # noqa: F401,F403

# --------------------------------------------------------------------------
# Stored-frequency list editor (stays open while you enter many)
# --------------------------------------------------------------------------
class FreqListWindow(tk.Toplevel):
    def __init__(self, app):
        super().__init__(app.root)
        self.app = app
        self.title("Stored frequencies")
        self.configure(bg=C["bg"])
        self.transient(app.root)
        self.minsize(560, 420)
        self.protocol("WM_DELETE_WINDOW", self.destroy)

        form = panel(self, padx=10, pady=8)
        form.pack(fill="x", padx=8, pady=(8, 0))
        lab = dict(bg=C["panel"], fg=C["gold"], font=(FONT.ui, 9, "bold"))
        tk.Label(form, text="Frequency", **lab).grid(row=0, column=0, sticky="w")
        tk.Label(form, text="Mode", **lab).grid(row=0, column=1, sticky="w", padx=(10, 0))
        tk.Label(form, text="Name (optional)", **lab).grid(row=0, column=2, sticky="w", padx=(10, 0))
        self.freq_e = app._entry(form, 14, "")
        self.freq_e.grid(row=1, column=0, sticky="w")
        self.mode_var = tk.StringVar(value=self._default_mode())
        self.mode_cb = ttk.Combobox(form, textvariable=self.mode_var, values=app.modes, width=10)
        self.mode_cb.grid(row=1, column=1, sticky="w", padx=(10, 0))
        self.name_e = app._entry(form, 22, "")
        self.name_e.grid(row=1, column=2, sticky="we", padx=(10, 0))
        form.columnconfigure(2, weight=1)
        tk.Label(form, text="Type 7.074 (MHz), 7074 (kHz) or 7.074.000.  Enter adds it and clears for the next one.",
                 bg=C["panel"], fg=C["dim"], font=(FONT.ui, 8)).grid(row=2, column=0, columnspan=3, sticky="w", pady=(4, 0))

        btns = tk.Frame(form, bg=C["panel"])
        btns.grid(row=3, column=0, columnspan=3, sticky="w", pady=(8, 0))
        FlatButton(btns, "Add", command=self.add, font=(FONT.ui, 9, "bold"), on_color=C["green"]).pack(side="left", padx=(0, 4))
        FlatButton(btns, "Update selected", command=self.update_selected, font=(FONT.ui, 9)).pack(side="left", padx=(0, 4))
        FlatButton(btns, "Delete selected", command=self.delete_selected, font=(FONT.ui, 9)).pack(side="left", padx=(0, 4))
        FlatButton(btns, "Use radio's frequency", command=self.use_current, font=(FONT.ui, 9)).pack(side="left", padx=(0, 4))

        lst = panel(self, padx=10, pady=8)
        lst.pack(fill="both", expand=True, padx=8, pady=(8, 0))
        key = tk.Frame(lst, bg=C["panel"])
        key.pack(side="top", fill="x", pady=(0, 6))
        label(key, "Frequencies").pack(side="left")
        tk.Label(key, text="●  Voice (USB / LSB / AM / FM)", bg=C["panel"], fg=C["voice"],
                 font=(FONT.ui, 9, "bold")).pack(side="right")
        tk.Label(key, text="●  CW", bg=C["panel"], fg=C["red"],
                 font=(FONT.ui, 9, "bold")).pack(side="right", padx=(0, 16))
        tk.Label(key, text="●  Digital", bg=C["panel"], fg=C["freq"],
                 font=(FONT.ui, 9, "bold")).pack(side="right", padx=(0, 16))
        self.tree = ttk.Treeview(lst, columns=("freq", "mode", "name"), show="headings", selectmode="browse",
                                 style="Freq.Treeview")
        for col, text, w, anchor in (("freq", "Frequency (MHz)", 130, "e"), ("mode", "Mode", 90, "w"),
                                     ("name", "Name", 240, "w")):
            self.tree.heading(col, text=text, anchor=anchor)
            self.tree.column(col, width=w, anchor=anchor, stretch=(col == "name"))
        sb = ttk.Scrollbar(lst, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=sb.set)
        self.tree.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")

        foot = tk.Frame(self, bg=C["bg"])
        foot.pack(fill="x", padx=8, pady=8)
        FlatButton(foot, "  Tune to selected  ", command=self.tune_selected, font=(FONT.ui, 10, "bold"),
                   base=C["tx"], base_fg="#ffffff").pack(side="left")
        self.status = tk.Label(foot, text="Double-click a row to tune.", bg=C["bg"], fg=C["dim"], font=(FONT.ui, 9))
        self.status.pack(side="left", padx=10)
        FlatButton(foot, "Close", command=self.destroy, font=(FONT.ui, 9)).pack(side="right")

        for e in (self.freq_e, self.name_e, self.mode_cb):
            e.bind("<Return>", lambda ev: self.add())
        self.tree.tag_configure("new", background=C["green"], foreground="#ffffff")
        self.tree.tag_configure("voice", foreground=C["voice"])
        self.tree.tag_configure("data", foreground=C["freq"])
        self.tree.tag_configure("cw", foreground=C["red"])
        self.tree.bind("<<TreeviewSelect>>", lambda ev: self._fill_from_selection())
        self.tree.bind("<Double-1>", lambda ev: self.tune_selected())
        self.tree.bind("<Return>", lambda ev: self.tune_selected())
        self.tree.bind("<Delete>", lambda ev: self.delete_selected())
        self.refresh()
        self.focus_freq()

    # ---- helpers ----
    def _default_mode(self):
        if is_data_mode(self.app.mode or ""):
            return self.app.mode
        return self.app.pick_mode("data", self.app.freq or 14_000_000) or self.app.mode or ""

    def focus_freq(self):
        self.freq_e.focus_set()
        self.freq_e.select_range(0, "end")

    def say(self, text, color=None):
        self.status.config(text=text, fg=color or C["dim"])

    def refresh(self, select_hz=None, flash_hz=None):
        self.mode_cb["values"] = self.app.modes
        self.tree.delete(*self.tree.get_children())
        for m in self.app._memories():
            self.tree.insert("", "end", iid=str(m["hz"]), values=(fmt_freq(m["hz"]), m.get("mode", ""), m.get("name", "")),
                             tags=(mode_kind(m.get("mode")),))
        if select_hz is not None and self.tree.exists(str(select_hz)):
            self.tree.selection_set(str(select_hz))
            self.tree.see(str(select_hz))
        if flash_hz is not None and self.tree.exists(str(flash_hz)):
            # show the new row without selecting it (selecting refills the boxes)
            iid = str(flash_hz)
            self.tree.see(iid)
            kind = mode_kind(self.tree.set(iid, "mode"))
            self.tree.item(iid, tags=("new",))
            self.after(1500, lambda: self.winfo_exists() and self.tree.exists(iid) and self.tree.item(iid, tags=(kind,)))

    def _selected_hz(self):
        sel = self.tree.selection()
        return int(sel[0]) if sel else None

    def _fill_from_selection(self):
        hz = self._selected_hz()
        mem = next((m for m in self.app._memories() if m["hz"] == hz), None)
        if not mem:
            return
        self.freq_e.delete(0, "end")
        self.freq_e.insert(0, fmt_freq(hz))
        self.mode_var.set(mem.get("mode", ""))
        self.name_e.delete(0, "end")
        self.name_e.insert(0, mem.get("name", ""))

    def _read_form(self):
        hz = parse_freq_input(self.freq_e.get())
        if hz is None:
            self.say("Not a frequency I understand - try 7.074, 7074 or 7.074.000", C["red"])
            self.focus_freq()
            return None
        return hz, self.mode_var.get().strip(), self.name_e.get().strip()

    # ---- actions ----
    def add(self):
        got = self._read_form()
        if not got:
            return
        hz, mode, name = got
        existed = any(m["hz"] == hz for m in self.app._memories())
        self.app.store_memory(hz, mode, name)
        self.refresh(flash_hz=hz)
        self.say(f"{'Replaced' if existed else 'Added'} {fmt_freq(hz)} {mode}", C["green"])
        self.freq_e.delete(0, "end")              # ready for the next one; mode stays
        self.name_e.delete(0, "end")
        self.focus_freq()

    def update_selected(self):
        old = self._selected_hz()
        if old is None:
            self.say("Select a row to update, or use Add.", C["amber"])
            return
        got = self._read_form()
        if not got:
            return
        hz, mode, name = got
        self.app.store_memory(hz, mode, name, replace_hz=old)
        self.refresh(select_hz=hz)
        self.say(f"Updated {fmt_freq(hz)} {mode}", C["green"])

    def delete_selected(self):
        hz = self._selected_hz()
        if hz is None:
            self.say("Select a row to delete.", C["amber"])
            return
        nxt = self.tree.next(str(hz)) or self.tree.prev(str(hz))
        self.app.delete_memory(hz)
        self.refresh(select_hz=int(nxt) if nxt else None)
        self.say(f"Deleted {fmt_freq(hz)}")

    def use_current(self):
        if self.app.freq is None:
            self.say("Not connected to the radio yet.", C["amber"])
            return
        self.freq_e.delete(0, "end")
        self.freq_e.insert(0, fmt_freq(self.app.freq))
        if self.app.mode:
            self.mode_var.set(self.app.mode)
        self.name_e.focus_set()

    def tune_selected(self):
        hz = self._selected_hz()
        mem = next((m for m in self.app._memories() if m["hz"] == hz), None)
        if not mem:
            self.say("Select a row to tune.", C["amber"])
            return
        self.app.recall_memory(mem)
        self.say(f"Tuned to {fmt_freq(hz)} {mem.get('mode', '')}", C["green"])
