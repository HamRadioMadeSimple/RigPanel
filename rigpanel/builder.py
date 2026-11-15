"""Macro Builder window."""
from .core import *  # noqa: F401,F403
from .radios import *  # noqa: F401,F403
from .worker import *  # noqa: F401,F403
from .widgets import *  # noqa: F401,F403
from .waterfall import *  # noqa: F401,F403
from .freqlist import *  # noqa: F401,F403
from .minis import *  # noqa: F401,F403

# --------------------------------------------------------------------------
# FT-891 macro builder: make, clone, change and arrange macros
# --------------------------------------------------------------------------
class MacroBuilder(tk.Toplevel):
    def __init__(self, app):
        super().__init__(app.root)
        self.app = app
        self.title(f"{MACROS.rig} Edit Rig Settings")
        self.configure(bg=C["bg"])
        self.transient(app.root)
        self.resizable(True, True)              # drag a corner: longer tables show more rows (27m)
        self.work = app.macro_list()            # working copy; nothing changes until Save
        self.sel = None
        self.dirty = False
        self.confirm = None                     # second-click confirmations (delete, close)

        body = tk.Frame(self, bg=C["bg"])
        body.pack(fill="both", expand=True, padx=8, pady=(8, 0))

        # --- left: the list of macros
        left = panel(body, padx=10, pady=8)
        left.pack(side="left", fill="y")
        label(left, "Rig Settings", size=11).pack(anchor="w", pady=(0, 6))
        self.lb = tk.Listbox(left, width=24, height=19, bg=C["field"], fg=C["fg"], font=(FONT.ui, 10, "bold"),
                             selectbackground=C["on"], selectforeground="#ffffff", activestyle="none",
                             highlightthickness=1, highlightbackground=C["btn_border"], relief="flat",
                             exportselection=False)
        self.lb.pack(fill="y", expand=True)
        self.lb.bind("<<ListboxSelect>>", lambda e: self._on_select())
        lb_btns = tk.Frame(left, bg=C["panel"])
        lb_btns.pack(fill="x", pady=(6, 0))
        for text, cmd, tip in (
                ("New", self.new, "Start a new, empty Rig Setting"),
                ("Clone", self.clone, "Copy the selected Rig Setting - then change a few values and rename it"),
                ("Delete", self.delete, "Delete the selected Rig Setting (Save to make it final)"),
                ("\u25b2", lambda: self.move(-1), "Move up - the order of the buttons in the main window"),
                ("\u25bc", lambda: self.move(1), "Move down - the order of the buttons in the main window")):
            b = FlatButton(lb_btns, text, command=cmd, font=(FONT.ui, 9, "bold"))
            b.config(padx=7)
            b.pack(side="left", padx=(0, 3))
            Tooltip(b, tip)
        tk.Label(left, text="Clone a Rig Setting, change a\nfew values, give it a new name.", bg=C["panel"],
                 fg=C["title"], font=(FONT.ui, 9, "bold"), justify="left").pack(anchor="w", pady=(6, 0))

        # --- right: the selected macro
        right = panel(body, padx=12, pady=8)
        right.pack(side="left", fill="both", expand=True, padx=(8, 0))
        head = tk.Frame(right, bg=C["panel"])
        head.pack(fill="x", pady=(0, 6))
        label(head, "Name:").pack(side="left")
        self.name_var = tk.StringVar()
        self.name_e = tk.Entry(head, textvariable=self.name_var, width=18, bg=C["field"], fg=C["fg"],
                               insertbackground=C["fg"], relief="flat", highlightthickness=1,
                               highlightbackground=C["btn_border"], highlightcolor=C["on"], font=(FONT.ui, 10, "bold"))
        self.name_e.pack(side="left", padx=(6, 12), ipady=2)
        self.btn_opts = opts = tk.Frame(head, bg=C["panel"])   # Row + Show as a button (not for Voice / Data / CW)
        opts.pack(side="left")
        self.kind_note = tk.Label(head, bg=C["panel"], fg=C["title"], font=(FONT.ui, 9, "bold"))
        label(opts, "Row:").pack(side="left")
        self.group_var = tk.StringVar()
        row_box = ttk.Combobox(opts, textvariable=self.group_var, values=MACROS.groups, width=10, state="readonly")
        row_box.pack(side="left", padx=(6, 12))
        Tooltip(row_box, "Which row of the main window the button goes in")
        Tooltip(self.name_e, "The button's name in the main window (Shift+V / Shift+D use Voice / Data)")
        self.show_var = tk.BooleanVar(value=True)
        show_cb = checkbox(opts, "Show as a button", self.show_var)
        show_cb.pack(side="left")
        Tooltip(show_cb, "Untick to keep this Rig Setting without a button in the main window")

        tools = tk.Frame(right, bg=C["panel"])
        tools.pack(fill="x", pady=(0, 6))
        b = FlatButton(tools, "Read from radio", command=lambda: self.capture(False), font=(FONT.ui, 9, "bold"))
        b.pack(side="left")
        Tooltip(b, "Fill the settings this Rig Setting uses with what the radio has now (then Save)")
        self.read_all_btn = FlatButton(tools, "Read all settings", command=lambda: self.capture(True),
                                       font=(FONT.ui, 9, "bold"))
        self.read_all_btn.pack(side="left", padx=4)
        Tooltip(self.read_all_btn, "Common view: read every Common setting from the radio.\n"
                                   "All Menus: read the menu group on screen into the green 'Radio now' column")
        b = FlatButton(tools, "Clear all", command=self.clear_all, font=(FONT.ui, 9, "bold"))
        b.pack(side="left")
        Tooltip(b, "Set every item to \u2014 (leave it alone) - the Rig Setting then changes nothing")
        b = FlatButton(tools, "Save as new", command=self.save_as_new, font=(FONT.ui, 9, "bold"), base=C["go"],
                       base_fg=C["go_fg"])
        b.pack(side="left", padx=(12, 0))
        Tooltip(b, "Save what's on the form as a NEW Rig Setting - the one you started from stays as it was")
        tk.Label(tools, text=f"{SKIP} = leave it alone", bg=C["panel"], fg=C["dim"],
                 font=(FONT.ui, 8)).pack(side="right")

        # One StringVar per setting, shared by both views, so a change in one shows in the other
        self.cells = {key: tk.StringVar(value=SKIP) for key in MACROS.all_items}
        for var in self.cells.values():
            var.trace_add("write", lambda *a: self._mark())
        self.view = "common"
        if MACROS.sections:                     # FT-891: Common | All Menus
            self.view = app.cfg.get("rs_view", "common")
            vs = tk.Frame(right, bg=C["panel"])
            vs.pack(fill="x", pady=(0, 8))
            tk.Label(vs, text="VIEW", bg=C["panel"], fg=C["gold"], font=(FONT.ui, 10, "bold")).pack(side="left", padx=(0, 8))
            self.view_btns = {}
            for v, text in (("common", "Common"), ("all", "All Menus")):
                b = FlatButton(vs, f"  {text}  ", command=lambda v=v: self.set_view(v), font=(FONT.ui, 9, "bold"))
                b.pack(side="left", padx=(0, 3))
                Tooltip(b, "The settings most used for Voice and Data" if v == "common"
                        else "Every menu item of the radio, by menu group")
                self.view_btns[v] = b
            tk.Label(vs, text="Common = the settings most used for Voice and Data", bg=C["panel"], fg=C["dim"],
                     font=(FONT.ui, 8)).pack(side="left", padx=8)
        self.common_f = tk.Frame(right, bg=C["panel"])
        self._grid_rows(self.common_f, MACROS.common, width=18)
        self.all_f = tk.Frame(right, bg=C["panel"])
        if MACROS.sections:
            self._build_all_view(self.all_f)
        for v in (self.name_var, self.group_var, self.show_var):
            v.trace_add("write", lambda *a: (self._mark(), self._live_label()))
        self.name_var.trace_add("write", lambda *a: self._kind_hint())

        foot = tk.Frame(self, bg=C["bg"])
        foot.pack(fill="x", padx=8, pady=8)
        tips = (("  Save  ", self.save, dict(font=(FONT.ui, 10, "bold"), base=C["tx"], base_fg="#ffffff"), (0, 0),
                 "Save your changes (the radio isn't changed until you press the button)"),
                ("Save & Apply", self.save_apply, dict(font=(FONT.ui, 10, "bold"), base=C["go"], base_fg=C["go_fg"]),
                 (6, 0), "Save, then send this Rig Setting to the radio now"),
                ("Defaults", self.defaults, dict(font=(FONT.ui, 9, "bold")), (6, 6),
                 "Replace ALL Rig Settings with RigPanel's starting set (click twice; Save to keep them)"))
        for text, cmd, kw, pad, tip in tips:
            b = FlatButton(foot, text, command=cmd, **kw)
            b.pack(side="left", padx=pad)
            Tooltip(b, tip)
        self.status = tk.Label(foot, text="Pick a Rig Setting on the left.", bg=C["bg"], fg=C["dim"], font=(FONT.ui, 10, "bold"))
        self.status.pack(side="left", padx=8)
        b = FlatButton(foot, "Close", command=self.close, font=(FONT.ui, 9, "bold"))
        b.pack(side="right")
        Tooltip(b, "Close the editor (asks if you have unsaved changes)")
        self.protocol("WM_DELETE_WINDOW", self.close)

        self._loading = False
        self.set_view(self.view)
        self._refresh_list(0)
        self.update_idletasks()
        self.minsize(self.winfo_reqwidth(), self.winfo_reqheight())    # never smaller than it opens
        geom = app.cfg.get("rs_geom")
        if geom:
            try:
                self.geometry(geom)
            except tk.TclError:
                pass

    # ---- the two views ----
    def _combo(self, master, key, width):
        numeric = key == "WIDTH" or (key in MACROS.menu and not isinstance(MACROS.menu[key][2], dict))
        return ttk.Combobox(master, textvariable=self.cells[key], values=macro_choices(key, self.app),
                            width=width, state="normal" if numeric else "readonly")

    def _grid_rows(self, master, keys, width):
        for row, key in enumerate(keys):
            tk.Label(master, text=item_label(key), bg=C["panel"], fg=C["fg"], font=(FONT.ui, 9, "bold"),
                     anchor="w").grid(row=row, column=0, sticky="w", pady=1)
            self._combo(master, key, width).grid(row=row, column=1, padx=(12, 0), pady=1)

    def _build_all_view(self, f):
        quick = tk.Frame(f, bg=C["panel"])
        quick.pack(fill="x")
        top_keys = [k for k in ("MODE", "FILTER", "WIDTH", "BKIN") if k in MACROS.all_items]   # FILTER: IC-7300 only
        self._grid_rows(quick, top_keys, width=18)
        names = " / ".join(k if k.isupper() and len(k) <= 3 else k.title() for k in MACROS.filters)
        tk.Label(quick, text=names, bg=C["panel"], fg=C["fg"], font=(FONT.ui, 9, "bold"),
                 anchor="w").grid(row=len(top_keys), column=0, sticky="w", pady=1)
        four = tk.Frame(quick, bg=C["panel"])
        four.grid(row=len(top_keys), column=1, sticky="w", padx=(12, 0), pady=1)
        for key in MACROS.filters:
            self._combo(four, key, 4).pack(side="left", padx=(0, 3))
        tk.Frame(f, bg=C["border"], height=1).pack(fill="x", pady=8)

        g = tk.Frame(f, bg=C["panel"])
        g.pack(fill="x")
        tk.Label(g, text="MENU GROUP", bg=C["panel"], fg=C["gold"], font=(FONT.ui, 10, "bold")).pack(side="left")
        self.sec_var = tk.StringVar()
        self.sec_box = ttk.Combobox(g, textvariable=self.sec_var, width=20, state="readonly")
        self.sec_box.pack(side="left", padx=8)
        self.sec_box.bind("<<ComboboxSelected>>", lambda e: self.show_section())
        tk.Label(g, text="(n) = settings used in this group", bg=C["panel"], fg=C["dim"],
                 font=(FONT.ui, 8)).pack(side="left")

        head = tk.Frame(f, bg=C["panel"])
        head.pack(fill="x", pady=(6, 2))
        for text, w in (("Setting", 27), ("This Rig Setting", 17), ("Radio now - click to copy", 22)):
            tk.Label(head, text=text, width=w, anchor="w", bg=C["panel"], fg=C["dim"],
                     font=(FONT.ui, 8, "bold")).pack(side="left")

        box = tk.Frame(f, bg=C["panel"])
        box.pack(fill="both", expand=True)
        self.canvas = tk.Canvas(box, bg=C["panel"], highlightthickness=0, width=560, height=330)
        sb = ttk.Scrollbar(box, orient="vertical", command=self.canvas.yview)
        self.canvas.configure(yscrollcommand=sb.set)
        self.canvas.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")
        self.sec_frames, self.name_lbls, self.radio_lbls = {}, {}, {}
        for num, _name in MACROS.sections:
            fr = tk.Frame(self.canvas, bg=C["panel"])
            codes = section_codes(num)
            for row, code in enumerate(codes):
                nl = tk.Label(fr, text=item_label(code), width=27, anchor="w", bg=C["panel"], fg=C["fg"],
                              font=(FONT.ui, 9, "bold"))
                nl.grid(row=row, column=0, sticky="w", pady=1)
                if code in MACROS.locked:
                    tk.Label(fr, text="read only" if code in MACROS.readonly else "locked (CAT link)", width=17, anchor="w",
                             bg=C["panel"], fg=C["dim"], font=(FONT.ui, 9)).grid(row=row, column=1, sticky="w")
                else:
                    cb = self._combo(fr, code, 15)
                    cb.grid(row=row, column=1, sticky="w", padx=(0, 8), pady=1)
                    self._wheel(cb)
                    self.name_lbls[code] = nl
                rl = tk.Label(fr, text="", width=20, anchor="w", bg=C["panel"], fg=C["green"],
                              font=(FONT.mono, 9, "bold"), cursor="hand2")
                rl.grid(row=row, column=2, sticky="w")
                rl.bind("<Button-1>", lambda e, c=code: self._copy_radio(c))
                self.radio_lbls[code] = rl
                for w in (nl, rl):
                    self._wheel(w)
            self._wheel(fr)
            self.sec_frames[num] = fr
        self.sec_win = self.canvas.create_window(0, 0, window=self.sec_frames[MACROS.sections[0][0]], anchor="nw")
        self._wheel(self.canvas)
        self.radio_vals = {}
        sec = self.app.cfg.get(f"rs_section_{MACROS.rig}", MACROS.sections[0][0] if MACROS.rig != "FT-891" else "16")
        self.cur_sec = sec if sec in self.sec_frames else MACROS.sections[0][0]
        for var in self.cells.values():
            var.trace_add("write", lambda *a: self._show_used())

    def _wheel(self, w):
        """Mouse wheel scrolls the list (and never spins a dropdown's value by accident)."""
        def scroll(e):
            if e.num == 4 or getattr(e, "delta", 0) > 0:
                self.canvas.yview_scroll(-2, "units")
            else:
                self.canvas.yview_scroll(2, "units")
            return "break"
        for ev in ("<MouseWheel>", "<Button-4>", "<Button-5>"):
            w.bind(ev, scroll)

    def set_view(self, v):
        if not MACROS.sections:
            v = "common"
        self.view = v
        self.common_f.pack_forget()
        self.all_f.pack_forget()
        (self.all_f if v == "all" else self.common_f).pack(fill="both", expand=True)
        if MACROS.sections:
            for k, b in self.view_btns.items():
                b.set_on(k == v)
            self.app.cfg["rs_view"] = v
            self.read_all_btn.config(text="Read this group" if v == "all" else "Read all settings")
            if v == "all":
                self.show_section(self.cur_sec)

    def _sec_title(self, num, name):
        base = sec_title(num, name)
        n = sum(1 for c in section_codes(num) if c in self.cells
                and self.cells[c].get() not in ("", SKIP))
        return base + (f"  ({n})" if n else "")

    def _show_used(self):
        """Group counts in the dropdown, and blue names for settings this Rig Setting uses."""
        if not MACROS.sections or not hasattr(self, "sec_box"):
            return
        titles = [self._sec_title(n, name) for n, name in MACROS.sections]
        self.sec_box.config(values=titles)
        for (num, _), t in zip(MACROS.sections, titles):
            if num == self.cur_sec and self.sec_var.get() != t:
                self.sec_var.set(t)
        for code, nl in self.name_lbls.items():
            nl.config(fg=C["on"] if self.cells[code].get() not in ("", SKIP) else C["fg"])

    def show_section(self, num=None):
        if num is None:
            i = self.sec_box.current()
            num = MACROS.sections[i][0] if i >= 0 else self.cur_sec
        self.cur_sec = num
        self.app.cfg[f"rs_section_{MACROS.rig}"] = num
        self.canvas.itemconfig(self.sec_win, window=self.sec_frames[num])
        self.sec_frames[num].update_idletasks()
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        self.canvas.yview_moveto(0)
        self._show_used()
        if self.app.connected and not any(c in self.radio_vals for c in section_codes(num)):
            self.read_section(quiet=True)

    def read_section(self, quiet=False):
        """Read the shown group from the radio into the 'Radio now' column (the Rig Setting is not changed)."""
        if not self.app.connected:
            return self.say("Not connected to the radio.", C["amber"])
        codes = section_codes(self.cur_sec)
        for c in codes:
            self.radio_lbls[c].config(text="...", fg=C["dim"])
        if not quiet:
            self.say(f"Reading group {self.cur_sec} from the radio...")
        self.app.worker.submit(lambda w: w.capture_macro(("radio", self.cur_sec), codes))

    def _copy_radio(self, code):
        if code in MACROS.locked:
            return self.say(f"{item_label(code)} is not changed by RigPanel.", C["amber"])
        v = self.radio_vals.get(code)
        if v is None:
            return self.say("Read the group from the radio first.", C["amber"])
        self.cells[code].set(v)
        self.say(f"{item_label(code)} = {v} copied into this Rig Setting.", C["green"])

    # ---- helpers ----
    def say(self, text, color=None):
        self.status.config(text=text, fg=color or C["dim"])

    def _mark(self):
        if not self._loading:
            self.dirty = True

    def _list_text(self, m):
        tag = "" if m.get("group") == "Operating" else "   \u00b7 antenna"
        return f"{m['name']}{tag}{'' if m.get('show', True) else '   (hidden)'}"

    def _live_label(self):
        """Keep the list entry in step while you type a name or change the row."""
        if self._loading or self.sel is None or self.sel >= self.lb.size():
            return
        m = {"name": self.name_var.get().strip() or "(no name)", "group": self.group_var.get(),
             "show": bool(self.show_var.get())}
        self.lb.delete(self.sel)
        self.lb.insert(self.sel, self._list_text(m))
        self.lb.itemconfig(self.sel, fg=C["voice"] if m["group"] == "Antenna" else C["fg"])
        self.lb.selection_set(self.sel)

    def _refresh_list(self, select):
        self.lb.delete(0, "end")
        for m in self.work:
            self.lb.insert("end", self._list_text(m))
            self.lb.itemconfig("end", fg=C["voice"] if m.get("group") == "Antenna" else C["fg"])
        if self.work:
            select = max(0, min(select, len(self.work) - 1))
            self.lb.selection_clear(0, "end")
            self.lb.selection_set(select)
            self.lb.see(select)
            self._load(select)

    def _kind_hint(self):
        """Voice / Data / CW run from the MODE row's button of the same name - say so instead of Row / Show."""
        n = self.name_var.get().strip().lower()
        kind = next((k for k in ("Voice", "Data", "CW") if k.lower() == n), None)
        if kind:
            self.btn_opts.pack_forget()
            self.kind_note.config(text=f"Runs from the {kind} button on the MODE row")
            self.kind_note.pack(side="left")
        else:
            self.kind_note.pack_forget()
            self.btn_opts.pack(side="left")

    def _load(self, i):
        self._loading = True
        self.sel = i
        m = self.work[i]
        self.name_var.set(m["name"])
        self.group_var.set(m.get("group", "Operating"))
        self.show_var.set(m.get("show", True))
        for key, var in self.cells.items():
            var.set(m["items"].get(key) or SKIP)
        self._loading = False

    def _commit(self):
        """Form -> working list. Returns an error message, or None if it's fine."""
        if self.sel is None or self.sel >= len(self.work):
            return None
        name = self.name_var.get().strip()
        if not name:
            return "Give the Rig Setting a name."
        if any(i != self.sel and m["name"].lower() == name.lower() for i, m in enumerate(self.work)):
            return f"There's already a Rig Setting called '{name}'."
        items = {}
        for key, var in self.cells.items():
            v = var.get().strip()
            if not v or v == SKIP:
                continue
            try:
                if key in MACROS.menu:
                    menu_encode(key, v)
                elif key == "WIDTH" and not v.isdigit():
                    raise ValueError("Width: enter a number of Hz, e.g. 2400")
            except ValueError as e:
                return str(e)
            items[key] = v
        self.work[self.sel] = {"name": name, "group": self.group_var.get() or "Operating",
                               "show": bool(self.show_var.get()), "items": items}
        return None

    def _on_select(self):
        cur = self.lb.curselection()
        if not cur or cur[0] == self.sel:
            return
        err = self._commit()
        if err:
            self.lb.selection_clear(0, "end")
            self.lb.selection_set(self.sel)
            self.say(err, C["red"])
            return
        new = cur[0]
        self._refresh_list(new)
        self.say(f"Editing '{self.work[new]['name']}'.")

    def _unique(self, base):
        names = {m["name"].lower() for m in self.work}
        if base.lower() not in names:
            return base
        n = 2
        while f"{base} {n}".lower() in names:
            n += 1
        return f"{base} {n}"

    # ---- list buttons ----
    def new(self):
        err = self._commit()
        if err:
            return self.say(err, C["red"])
        self.work.append({"name": self._unique("New Setting"), "group": "Operating", "show": True, "items": {}})
        self.dirty = True
        self._refresh_list(len(self.work) - 1)
        self.name_e.focus_set()
        self.name_e.select_range(0, "end")
        self.say("New Rig Setting: name it, pick values (or Read from radio), then Save.")

    def clone(self):
        err = self._commit()
        if err:
            return self.say(err, C["red"])
        src = self.work[self.sel]
        copy = {"name": self._unique(f"{src['name']} copy"), "group": src.get("group", "Operating"),
                "show": True, "items": dict(src["items"])}
        self.work.insert(self.sel + 1, copy)
        self.dirty = True
        self._refresh_list(self.sel + 1)
        self.name_e.focus_set()
        self.name_e.select_range(0, "end")
        self.say(f"Cloned '{src['name']}' - rename it, change what you need, then Save.", C["green"])

    def delete(self):
        if not self.work:
            return
        name = self.work[self.sel]["name"]
        self.confirm = None                     # one click: nothing is gone until Save (Close can still undo it)
        del self.work[self.sel]
        self.dirty = True
        self.sel = None
        self._refresh_list(max(0, (self.lb.curselection() or (0,))[0] - 1))
        self.say(f"Deleted '{name}' - Save to keep the change, or Close without saving to undo it.", C["amber"])

    def move(self, d):
        err = self._commit()
        if err:
            return self.say(err, C["red"])
        i, j = self.sel, self.sel + d
        if 0 <= j < len(self.work):
            self.work[i], self.work[j] = self.work[j], self.work[i]
            self.dirty = True
            self._refresh_list(j)

    # ---- form buttons ----
    def clear_all(self):
        for var in self.cells.values():
            var.set(SKIP)       # every setting, in both views
        self.say("All settings cleared - pick the ones this Rig Setting should set.")

    def capture(self, everything):
        if everything and self.view == "all":
            return self.read_section()
        if not self.app.connected:
            return self.say("Not connected to the radio.", C["amber"])
        keys = [k for k in (MACROS.common if everything else MACROS.all_items)
                if everything or self.cells[k].get() not in ("", SKIP)]
        if not keys:
            return self.say("This Rig Setting has no settings yet - use 'Read all settings'.", C["amber"])
        self.say("Reading the radio...")
        if self.view == "all":
            self.read_section(quiet=True)       # the green "Radio now" column of the group on screen too
        self.app.worker.submit(lambda w: w.capture_macro(self.sel, keys))

    def fill(self, tag, vals):
        if isinstance(tag, tuple) and tag[0] == "radio":
            for code in section_codes(tag[1]):
                v = vals.get(code)
                if v is not None:
                    self.radio_vals[code] = v
                self.radio_lbls[code].config(text=v if v is not None else "no answer",
                                             fg=C["green"] if v is not None else C["dim"])
            return self.say(f"Group {sec_title(tag[1], dict(MACROS.sections)[tag[1]])}: {len(vals)} setting(s) read. Click a green value to copy it.",
                            C["green"])
        if tag != self.sel:
            return
        for key, v in vals.items():
            cur = self.cells[key].get()
            if key == "MODE" and cur == SSB_BY_BAND and v in ("LSB", "USB"):
                continue                     # keep 'by band' rather than pinning one sideband
            self.cells[key].set(v)
        where = ""
        if MACROS.sections and vals:            # say where the values went (they may be in other groups)
            parts = ["top rows"] if any(k not in MACROS.menu for k in vals) else []
            groups = [sec_title(n, name) for n, name in MACROS.sections
                      if any(MACROS.section_of(k) == n for k in vals if k in MACROS.menu)]
            if groups:
                parts.append(("group " if len(groups) == 1 else "groups ") + ", ".join(groups))
            if self.view == "common":
                where = ""
            else:
                where = ": " + " and ".join(parts)
        self.say(f"Filled {len(vals)} setting(s) from the radio{where} - check them, then Save.", C["green"])

    def save_as_new(self):
        """Save what's on the form as a NEW Rig Setting; the one you started from stays as it was."""
        if self.sel is None or self.sel >= len(self.work):
            return
        i, orig = self.sel, json.loads(json.dumps(self.work[self.sel]))
        name = self.name_var.get().strip()
        if not name or name.lower() == orig["name"].lower():
            self.name_var.set(self._unique(f"{orig['name']} copy"))
        self.work.insert(i + 1, dict(orig))
        self.sel = i + 1
        err = self._commit()
        if err:
            del self.work[i + 1]
            self.sel = i
            return self.say(err, C["red"])
        self.work[i] = orig                       # the original keeps its old values
        self.app.save_macro_list(self.work)
        self.dirty = False
        self._refresh_list(i + 1)
        self.say(f"Saved as new: '{self.work[i + 1]['name']}' ('{orig['name']}' is unchanged).", C["green"])

    def defaults(self):
        if self.confirm != ("defaults",):
            self.confirm = ("defaults",)
            return self.say("Click Defaults again to replace ALL Rig Settings with the starting set.", C["amber"])
        self.confirm = None
        self.work = [json.loads(json.dumps(m)) for m in MACROS.defaults]
        self.dirty = True
        self.sel = None
        self._refresh_list(0)
        self.say("Defaults loaded - Save to keep them.")

    def save(self):
        err = self._commit()
        if err:
            return self.say(err, C["red"])
        self.app.save_macro_list(self.work)
        self.dirty = False
        self._refresh_list(self.sel or 0)
        self.say("Saved - the buttons are updated.", C["green"])

    def save_apply(self):
        """Save, then send this Rig Setting to the radio now (same as its button in the main window)."""
        err = self._commit()
        if err:
            return self.say(err, C["red"])
        if self.sel is None or self.sel >= len(self.work):
            return self.say("Pick a Rig Setting first.", C["amber"])
        self.save()
        name = self.work[self.sel]["name"]
        self.say(f"Saved - applying '{name}' to the radio...", C["green"])
        self.app.run_macro(name)

    def close(self):
        self._commit()
        if self.dirty and self.confirm != ("close",):
            self.confirm = ("close",)
            return self.say("You have unsaved changes - Save, or click Close again to discard them.", C["amber"])
        try:
            self.app.cfg["rs_geom"] = self.geometry()                  # size and place, for next time
        except tk.TclError:
            pass
        self.destroy()
