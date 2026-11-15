"""The flrig link: the one thread that talks to flrig (XML-RPC), and its poll loop."""
from .core import *  # noqa: F401,F403
from .radios import *  # noqa: F401,F403

# --------------------------------------------------------------------------
# flrig XML-RPC worker thread (all network calls happen here)
# --------------------------------------------------------------------------
class TimeoutTransport(xmlrpc.client.Transport):
    def __init__(self, timeout):
        super().__init__()
        self._timeout = timeout

    def make_connection(self, host):
        conn = super().make_connection(host)
        conn.timeout = self._timeout
        return conn


RPC_TIMEOUT_S = 10.0     # flrig can be slow while it waits on the radio's serial port (FT-891 at 4800 baud)
SLOW_REPLY_S = 1.0       # replies slower than this are noted in the debug log
TIMEOUTS_BEFORE_LOST = 3 # one late reply is not a lost connection; 3 in a row is
# Background radio reads (raw CAT through flrig) are paced so flrig stays free for the
# digital apps. Intervals are for a quick radio and stretch automatically (up to 8x)
# when CAT replies are slow (the FT-891 at 4800 baud).
CTL_READ_S = 1.5         # one receive control (AGC, NB, ...) per this many seconds
CAT_LEVEL_S = 5.0        # RF gain read straight from the radio
MACRO_CYCLE_S = 30.0     # all FT-891 macro menu items re-read once per cycle, one per poll
MENU_TRUST_S = 600.0     # Voice / Data / CW trust a menu value read or set this recently (11-06j)
CAT_QUICK_S = 0.15       # a CAT reply this fast needs no slowing down


class FlrigWorker(threading.Thread):
    NET_ERRORS = (OSError, http.client.HTTPException, xmlrpc.client.ProtocolError)

    def __init__(self, out_q):
        super().__init__(daemon=True)
        self.out_q = out_q
        self.jobs = queue.Queue()
        self.url = None
        self.proxy = None
        self.methods = set()
        self.profile = None
        self.enabled = False
        self.alive = True
        self.cycle = 0
        self.last_mode = None
        self.ctl_rr = 0
        self.full_read = False
        self.cat_read_failed = set()   # levels whose CAT read-back couldn't be parsed (logged once)
        self.macro_codes = set()       # FT-891 menu items whose values the panel shows (empty = no macros)
        self.macro_read_due = 0.0
        self.pmax = 100.0
        self.timeouts = 0              # late replies in a row
        self.slow_noted = 0.0          # when the status bar last said flrig is slow
        self.cat_avg = 0.0             # running average of raw CAT reply time (s)
        self.pace_logged = 1.0
        self.ctl_due = 0.0             # next background receive-control read
        self.level_cat_due = 0.0       # next RF-gain read from the radio
        self.ex_unsupported = set()    # FT-891 menu items the radio won't read over CAT
        self.menu_known = {}           # menu code -> (value, when read/confirmed) - quick Voice/Data/CW
        self.cur_ab = "A"              # VFO in use, as last read (flrig keeps a mode per VFO)
        self.ctl_pending = []          # controls still to read after connect / rig change
        self.macro_pending = []        # macro menu items still to read this cycle
        self.extra_due = {}            # next background read of SHIFT / CLAR (see EXTRA_READS)

    # ---- API used by the UI thread ----
    def connect(self, host, port):
        self.url = f"http://{host}:{int(port)}/RPC2"
        self.proxy = None
        self.enabled = True

    def submit(self, job):
        self.jobs.put(job)

    def set_profile(self, profile):
        self.profile = profile
        self.full_read = True
        self.macro_pending = []
        self.cat_read_failed = set()
        self.macro_read_due = 0.0
        self.ex_unsupported = set()
        self.menu_known = {}           # menu code -> (value, when read/confirmed) - quick Voice/Data/CW
        self.ex_fail = {}

    # ---- helpers (worker thread) ----
    def post(self, kind, data=None):
        self.out_q.put((kind, data))

    def has(self, method):
        return not self.methods or method in self.methods

    def rpc(self, method, *args, read=None):
        if read is None:
            read = method.startswith("rig.get_") or method.startswith("system.")
        t0 = time.monotonic()
        try:
            result = getattr(self.proxy, method)(*args)
        except socket.timeout:
            dt = time.monotonic() - t0
            debug_log(f"flrig timeout after {dt:.1f}s: {method}{args!r}")
            self._fresh_connection()
            # a read is safe to ask again (on a new connection); a command is not
            # (it may already have happened, e.g. VFO swap), so that just reports the timeout
            if not read:
                raise
            t0 = time.monotonic()
            result = getattr(self.proxy, method)(*args)
        dt = time.monotonic() - t0
        if dt > SLOW_REPLY_S:
            debug_log(f"slow flrig reply: {method}{args!r} took {dt:.1f}s")
        if method == "rig.cat_string":
            self.cat_avg = dt if not self.cat_avg else 0.8 * self.cat_avg + 0.2 * dt
            pace = self.pace()
            if abs(pace - self.pace_logged) >= 1:
                self.pace_logged = pace
                debug_log(f"CAT replies average {self.cat_avg:.2f}s: background reads now {pace:.0f}x slower")
        return result

    def pace(self):
        """1 for a quick radio, up to 8 when raw CAT through flrig is slow."""
        return max(1.0, min(8.0, self.cat_avg / CAT_QUICK_S)) if self.cat_avg else 1.0

    def _fresh_connection(self):
        """Drop the kept-alive HTTP connection so the next call opens a new one
        (a stalled socket is a common cause of a late reply)."""
        try:
            self.proxy("close")()
        except Exception:
            pass

    def try_rpc(self, method, *args):
        if not self.has(method):
            return None
        try:
            return self.rpc(method, *args)
        except xmlrpc.client.Fault:
            return None

    def set_freq(self, hz):
        if self.has("rig.set_frequency"):
            self.rpc("rig.set_frequency", float(hz))
        else:
            self.rpc("rig.set_vfo", float(hz))

    def _md_cat(self):
        """FT-891 on VFO B: flrig can't set or report the mode there, so talk to the radio."""
        codes = getattr(self.profile, "MD_CODES", None)
        return codes if codes and self.cur_ab == "B" and self.has("rig.cat_string") else None

    def set_mode(self, mode):
        codes = self._md_cat()
        if codes and mode in codes:
            self.cat(f"MD0{codes[mode]};")
            self.md_cache = (mode, time.monotonic())
            return
        m = f"rig.set_mode{self.cur_ab}"
        self.rpc(m if m in self.methods else "rig.set_mode", mode)

    def get_mode(self):
        codes = self._md_cat()
        if codes:
            cached = getattr(self, "md_cache", None)
            if cached and time.monotonic() - cached[1] < 0.6:      # read the radio ~2x a second
                return cached[0]
            reply = str(self.cat_read("MD0;"))
            mt = re.search(r"MD0([0-9A-F])", reply)
            names = {v: k for k, v in codes.items()}
            if mt and mt.group(1) in names:
                self.md_cache = (names[mt.group(1)], time.monotonic())
                return names[mt.group(1)]
        m = f"rig.get_mode{self.cur_ab}"
        return str(self.rpc(m if m in self.methods else "rig.get_mode"))

    def set_bandwidth(self, text, index):
        hz = parse_hz(text)
        if self.has("rig.set_bandwidth") and hz:
            self.rpc("rig.set_bandwidth", int(hz))
        else:
            self.rpc("rig.set_bw", int(index))

    LEVEL_GET = {"power": "rig.get_power", "volume": "rig.get_volume",
                 "rfgain": "rig.get_rfgain", "micgain": "rig.get_micgain"}
    NAMES = {"power": "RF Power", "volume": "AF Volume", "rfgain": "RF Gain", "micgain": "Mic Gain"}

    def _cat_level_ok(self, key):
        p = self.profile
        return p is not None and hasattr(p, "level_set_string") and p.level_set_string(key, 0) is not None

    def _cat_read_level(self, key):
        reply = self.cat_read(self.profile.level_read_string(key))
        return self.profile.parse_level(key, reply), reply

    def read_level(self, key):
        """Levels the profile can do by CAT (RF gain) are read from the radio itself;
        flrig only reports what it was last told, which may not be what the radio has."""
        if self._cat_level_ok(key):
            try:
                v, reply = self._cat_read_level(key)
            except xmlrpc.client.Fault as e:
                v, reply = None, f"Fault: {e.faultString}"
            if v is not None:
                return v
            if key not in self.cat_read_failed:
                self.cat_read_failed.add(key)
                debug_log(f"{self.NAMES[key]}: CAT read {self.profile.level_read_string(key)!r} -> {reply!r} "
                          f"(could not parse; using flrig's value)")
        v = self.try_rpc(self.LEVEL_GET[key])
        return None if v is None else float(v)

    def set_level(self, key, method, value):
        if not self._cat_level_ok(key):
            self.rpc(method, int(value))
            return
        name, cmd = self.NAMES[key], self.profile.level_set_string(key, value)
        try:
            set_reply = self.cat(cmd)
            back, read_reply = self._cat_read_level(key)
        except xmlrpc.client.Fault as e:
            set_reply, back, read_reply = f"Fault: {e.faultString}", None, ""
        debug_log(f"{name} -> {value}%: sent {cmd!r} reply {set_reply!r}; "
                  f"read {self.profile.level_read_string(key)!r} reply {read_reply!r} -> {back}")
        if back is not None and abs(back - value) <= 2:
            return                                   # the radio has it
        if back is None and getattr(self.profile, "level_hidden", None) and self.profile.level_hidden(key, read_reply):
            return            # flrig 2.0.12 hid the value (32-39 % on the operator's IC-7300): sent, not failed
        # direct CAT didn't do it: try flrig's own command as well
        self.rpc(method, int(value))
        time.sleep(0.3)
        try:
            back2, rr = self._cat_read_level(key)
        except xmlrpc.client.Fault:
            back2, rr = None, ""
        debug_log(f"{name} -> {value}%: flrig {method}({int(value)}); radio now reads {back2} ({rr!r})")
        if back2 is None or abs(back2 - value) > 2:
            self.post("log", f"{name}: sent {int(value)}, but the radio reads {back2 if back2 is not None else back}. "
                             f"Details are in {DEBUG_LOG}")

    # ---- VFO A / B (flrig's own methods - it handles each radio's commands)
    def vfo_select(self, ab):
        self.rpc("rig.set_AB", ab)
        self.cur_ab = "B" if str(ab).upper().startswith("B") else "A"
        self.reread_all()

    def _swap_only(self):
        return bool(getattr(self.profile, "VFO_BY_SWAP", False)) and self.has("rig.cat_string")

    def vfo_swap(self):
        if self._swap_only():
            self.cat("SV;")
        elif isinstance(self.profile, IcomProfile) and self.has("rig.cat_string"):
            self.cat(self.profile._frame([0x07, 0xB0]))     # IC-7300: exchange VFO A and B (flrig's swap only selected B, 11-05c)
        else:
            self.rpc("rig.swap")
        self.reread_all()

    def reread_all(self):
        """The radio keeps receive settings and levels per VFO: after a swap / VFO change,
        read them all straight away instead of waiting for the slow background cycle."""
        prof = self.profile
        if prof and prof.controls and self.has("rig.cat_string"):
            for ctl in prof.controls:
                self.read_control(ctl)
        self.ctl_pending = []
        self.level_cat_due = 0.0
        self.cycle = 0                         # next poll (cycle 1) reads every level
        self.macro_pending = []
        self.macro_read_due = 0.0              # and the macro menu items

    def vfo_copy(self):
        """A=B: copy the VFO in use (frequency) to the other one."""
        if self._swap_only():
            self.cat("AB;")                    # FT-891: VFO A -> VFO B (frequency and mode)
            return
        ab = str(self.try_rpc("rig.get_AB") or "A").strip().upper()[:1]
        f = float(self.rpc("rig.get_vfo"))
        self.rpc("rig.set_vfoA" if ab == "B" else "rig.set_vfoB", f)

    def set_split(self, on):
        self.rpc("rig.set_split", 1 if on else 0)

    def tune(self):
        # flrig's own tune (same as its Tune button) works on both radios - use it first.
        # Raw CAT (FT-891 AC001/AC002) is only the fallback for an flrig without rig.tune.
        if "rig.tune" in self.methods:
            for args in ((), (1,)):
                try:
                    reply = self.rpc("rig.tune", *args)
                    debug_log(f"TUNE: flrig rig.tune{args} reply {reply!r}")
                    self.post("log", "TUNE sent through flrig - watch SWR / Po.")
                    return
                except xmlrpc.client.Fault as e:
                    debug_log(f"TUNE: flrig rig.tune{args} fault {e.faultString}")
        cmds = getattr(self.profile, "tune_cmds", None)
        if cmds and self.has("rig.cat_string"):
            for c in cmds:
                reply = self.cat(c)
                debug_log(f"TUNE: sent {c!r} reply {reply!r}")
                time.sleep(0.15)
            self.post("log", "TUNE: tuner start sent to the radio (AC001 / AC002) - watch SWR / Po.")
            return
        try:
            self.rpc("rig.tune")
        except xmlrpc.client.Fault:
            self.rpc("rig.tune", 1)
        self.post("log", "TUNE sent - watch SWR / Po.")

    def cat(self, s):
        """Raw CAT command that changes something (not repeated after a timeout)."""
        if isinstance(self.profile, YaesuProfile):
            back = yaesu_readback(s)
            if getattr(self, "yaesu_cmd_string", False):
                # flrig 2.0.12+: send the set with rig.cmd_string (writes, no waiting - an FT-891 set
                # never answers), then read it back on its own (checked, see cat_read). 2026-10-27
                self.rpc("rig.cmd_string", "".join(f"x{b:02X}" for b in s.encode()), read=False)
                return self.cat_read(back) if back else ""
            # flrig 2.0.09: a Yaesu "set" gets no answer and flrig waits 6 s for one. Send the matching
            # read in the same string: the radio answers at once (and confirms the change).
            return self._yaesu_send(s + (back or ""), read=False)
        return self.rpc("rig.cat_string", s, read=False)

    YAESU_READ_TRIES = 3

    def cat_read(self, s):
        """Raw CAT query (safe to repeat on a fresh connection after a timeout)."""
        if isinstance(self.profile, YaesuProfile):
            # flrig 2.0.12 sometimes hands back another answer (its own poll's MD0..., or the previous
            # request's) - measured on the FT-891 2026-10-27. The answer must start like the question
            # ("NB0;" -> "NB0..."); if not, ask again (~0.07 s) instead of using a wrong value.
            want = s.split(";")[0]
            reply = ""
            for n in range(self.YAESU_READ_TRIES):
                reply = self._yaesu_send(s, read=True)
                text = str(reply)
                if want in text or "?;" in text or "No response" in text:
                    return reply
                if n == 0:
                    debug_log(f"{s} answered {text!r} - not ours (flrig 2.0.12), asking again")
            return reply
        return self.rpc("rig.cat_string", s, read=True)

    def _yaesu_send(self, s, read):
        """Every Yaesu command goes as hex, 3 characters per byte and no spaces ("x46x41x3B").
        flrig 2.0.09 garbles plain strings containing an X; flrig 2.0.12 reads every string
        as hex. The hex answer is turned back into text."""
        wire = "".join(f"x{b:02X}" for b in s.encode())
        return hex_reply_text(self.rpc("rig.cat_string", wire, read=read))

    # ---- FT-891 menu items and macros ----
    def ex_read(self, code):
        if code in self.ex_unsupported:
            return None
        reply = str(self.cat_read(self.profile.menu_read_string(code)))
        v = self.profile.menu_parse(code, reply)
        if v is None and isinstance(self.profile, IcomProfile):
            # flrig 2.0.12 sometimes hands back its own poll's answer instead (seen in the
            # operator's menu dump 2026-10-26): one quick second try
            reply = str(self.cat_read(self.profile.menu_read_string(code)))
            v = self.profile.menu_parse(code, reply)
        if v is not None:
            getattr(self, "ex_fail", {}).pop(code, None)
            if v != UNREADABLE:
                self.menu_known[code] = (v, time.monotonic())
            return v
        # "?;" (flrig may show it as hex "3F 3B") or flrig's "No response": the radio won't
        # do this menu item over CAT. Stop asking - each "No response" costs flrig 6 s.
        bad = getattr(self, "ex_fail", {})
        self.ex_fail = bad
        bad[code] = bad.get(code, 0) + 1
        debug_log(f"menu {code}: no usable answer ({reply!r}), try {bad[code]}")
        if bad[code] >= 3:
            self.ex_unsupported.add(code)
            debug_log(f"menu {code}: radio replied {reply!r} - not available over CAT, no longer read")
            self.post("ex_unsupported", code)
        return None

    def ex_write(self, code, num):
        if code in self.ex_unsupported:
            return
        self.cat(self.profile.menu_write_string(code, num))

    def read_macro_state(self, codes=None):
        state = {}
        for code in sorted(codes or self.macro_codes):
            try:
                state[code] = self.ex_read(code)
            except (xmlrpc.client.Fault, socket.timeout):
                state[code] = None
        self.post("macro_state", state)
        return state

    def _control(self, key):
        return next((c for c in self.profile.controls if c.key == key), None)

    def run_macro(self, name, steps, quick=False):
        """steps: [(key, value)] already validated by the UI. Each one is set, then read back.
        quick (Voice / Data / CW): menu items the radio was seen to have recently are not re-read."""
        self.quick = quick
        if bool(int(self.try_rpc("rig.get_ptt") or 0)):
            self.post("macro_done", {"name": name, "ok": 0, "failed": ["radio is transmitting - nothing changed"]})
            return
        ok, failed, seen = 0, [], {}
        try:
            self._run_steps(name, steps, failed, seen)
            ok = len(steps) - len(failed)
        finally:                 # always report back, or the button stays "applying" forever
            if seen:
                self.post("macro_state", seen)
            self.macro_read_due = time.monotonic() + MACRO_CYCLE_S * self.pace()
            self.macro_pending = []
            if len(failed) + ok < len(steps):          # stopped part-way (flrig gone)
                failed.append("stopped - flrig stopped answering")
            self.post("macro_done", {"name": name, "ok": ok, "failed": failed})

    def _run_steps(self, name, steps, failed, seen):
        for key, val in steps:
            label = item_label(key, self.profile.macro_spec)
            try:
                if key == "MODE":
                    if val == SSB_BY_BAND:
                        hz = float(self.rpc("rig.get_vfo"))
                        val = "LSB" if hz < 10_000_000 and not 5_330_000 <= hz <= 5_410_000 else "USB"
                    self.set_mode(val)
                    time.sleep(0.25)
                    good = self.get_mode() == val
                    if good:
                        self.last_mode = None          # filter table changes with the mode
                        self.post("tables", {"bws": self.get_bws()})
                elif key == "FILTER":                 # IC-7300 FIL1/2/3, before the width (each has its own)
                    ctl = self._control("filter")
                    want = int(str(val)[-1])
                    self.set_filter(ctl, want)
                    time.sleep(0.15)
                    got = self.profile.parse_read(ctl, self.cat_read(self.profile.read_string(ctl)))
                    good = got == want
                elif key == "WIDTH":
                    self.set_bandwidth(str(val), 0)
                    time.sleep(0.2)
                    bw = self.try_rpc("rig.get_bw")
                    bw = bw[0] if isinstance(bw, (list, tuple)) and bw else bw
                    got = parse_hz(bw or "")
                    good = got is not None and abs(got - int(val)) <= 100
                elif key == "BKIN":
                    want = self.bkin_want(val)
                    good = self.set_bkin(want) == want
                elif key in self.profile.macro_spec.filters:
                    ctl = self._control(self.profile.macro_spec.filters[key])
                    want = 1 if val == "ON" else 0
                    self.cat(self.profile.set_string(ctl, want))
                    reply = self.cat_read(self.profile.read_string(ctl))
                    got = self.profile.parse_read(ctl, reply)
                    good = got is not None and bool(got) == bool(want)
                    if got is not None:
                        self.post("ctl", (ctl.key, got))
                else:
                    known = self.menu_known.get(key)
                    if getattr(self, "quick", False) and known and known[0] == val \
                            and time.monotonic() - known[1] < MENU_TRUST_S:
                        seen[key] = val                # read or set within the last 10 min: already right
                        debug_log(f"macro {name}: {label} known {val} - not re-read")
                        continue
                    # Read first and only write if it differs: re-writing a menu item the radio
                    # already has can disturb it (16-15 TUNER SELECT turns the FT-891's tuner off)
                    got = self.ex_read(key)
                    if key in self.ex_unsupported:
                        debug_log(f"macro {name}: {label} skipped - the radio doesn't allow it over CAT")
                        failed.append(f"{label} (not available over CAT - set it on the radio)")
                        continue
                    if got is None:
                        good = False                   # couldn't read it: don't write blind
                    elif got == UNREADABLE or got != val:
                        self.ex_write(key, val)
                        got = self.ex_read(key)
                        good = got == val or got == UNREADABLE   # flrig 2.0.12 can hide some values
                        if got == UNREADABLE:
                            debug_log(f"macro {name}: {label} sent - flrig 2.0.12 can't show this value back")
                    else:
                        debug_log(f"macro {name}: {label} already {val} - not re-sent")
                        good = True
                    seen[key] = got
                debug_log(f"macro {name}: {label} -> {val}: {'ok' if good else 'NOT CONFIRMED'}")
            except xmlrpc.client.Fault as e:
                good = False
                debug_log(f"macro {name}: {label} -> {val}: fault {e.faultString}")
            except socket.timeout:
                good = False
                debug_log(f"macro {name}: {label} -> {val}: no reply from flrig")
                self._fresh_connection()
            if not good:
                failed.append(label)

    def capture_macro(self, tag, keys):
        """Read what the radio is set to now (for the macro builder's 'Read from radio')."""
        vals, missed = {}, []
        try:
            self._capture(keys, vals, missed)
        finally:                 # always answer, or the builder sits on "Reading the radio..."
            if missed:
                debug_log(f"Read from radio: no reply for {', '.join(missed)}")
            self.post("macro_capture", (tag, vals))

    def _capture(self, keys, vals, missed):
        for key in keys:
            try:
                if key == "MODE":
                    vals[key] = self.get_mode()
                elif key == "WIDTH":
                    bw = self.try_rpc("rig.get_bw")
                    bw = bw[0] if isinstance(bw, (list, tuple)) and bw else bw
                    hz = parse_hz(bw or "")
                    if hz:
                        vals[key] = str(hz)
                elif key == "FILTER" and self._control("filter") is not None:
                    ctl = self._control("filter")
                    got = self.profile.parse_read(ctl, self.cat_read(self.profile.read_string(ctl)))
                    if got:
                        vals[key] = f"FIL{got}"
                elif key == "BKIN":
                    got = self.read_bkin()
                    if got is not None:
                        vals[key] = BKIN_VALUES[got]
                elif key in self.profile.macro_spec.menu:
                    v = self.ex_read(key)
                    if v is not None and menu_decode(key, v) is not None:
                        vals[key] = menu_decode(key, v)
                elif key in self.profile.macro_spec.filters:
                    ctl = self._control(self.profile.macro_spec.filters[key])
                    got = self.profile.parse_read(ctl, self.cat_read(self.profile.read_string(ctl)))
                    if got is not None:
                        vals[key] = "ON" if got else "OFF"
            except xmlrpc.client.Fault:
                pass
            except socket.timeout:
                missed.append(item_label(key, self.profile.macro_spec))
                self._fresh_connection()

    def set_filter(self, ctl, fil):
        """IC-7300 FIL1/2/3: keep the mode (and data mode) as it is, change only the filter."""
        prof = self.profile
        s = prof.filter_strings(self.cat_read(prof._frame([0x1A, 0x06])), self.cat_read(prof._frame([0x04])), fil)
        if s:
            self.cat(s)
        else:
            debug_log("filter: couldn't read the mode, filter not changed")
        self.read_control(ctl)
        self.post("tables", {"bws": self.get_bws()})     # bandwidth follows the filter

    # Background reads of the 1.4.1 controls: (worker method, profile attribute it needs, voice only)
    EXTRA_READS = (("shift", "shift_read_string", True), ("clar", "clar_read_strings", False))

    def shift(self, hz=None):
        """Passband SHIFT (voice): set it (hz given), then read it back. Posts ("shift", (read, sent))."""
        prof = self.profile
        if prof is None or not hasattr(prof, "shift_read_string") or not self.has("rig.cat_string"):
            return
        mode = self.get_mode()
        if hz is not None:
            self.cat(prof.shift_set_string(hz, mode))
        try:
            v = prof.parse_shift(self.cat_read(prof.shift_read_string()), mode)
        except xmlrpc.client.Fault:
            v = None
        self.post("shift", (v, hz))

    def clar(self, on=None, hz=None):
        """CLAR / RIT: switch it (on), set the offset (hz), then read both back. Posts ("clar", ...)."""
        prof = self.profile
        if prof is None or not hasattr(prof, "clar_read_strings") or not self.has("rig.cat_string"):
            return
        if on is not None:
            self.cat(prof.clar_on_string(on))
        if hz is not None:
            for s in prof.clar_offset_strings(hz):
                self.cat(s)
        try:
            v = prof.parse_clar([self.cat_read(s) for s in prof.clar_read_strings()])
        except xmlrpc.client.Fault:
            v = (None, None)
        self.post("clar", (v, on, hz))

    def ctl_level(self, ctl, value=None):
        """Read (and with value, first set) a control's level - e.g. FT-891 DNR level 1-15."""
        prof = self.profile
        if not prof or not ctl.level:
            return
        if value is not None:
            self.cat(prof.ctl_level_set(ctl, value))
        v = prof.ctl_level_parse(ctl, self.cat_read(prof.ctl_level_read(ctl)))
        self.post("ctl_level", (ctl.key, v, value))

    def set_bkin(self, v):
        """BKIN 0 OFF / 1 SEMI / 2 FULL. FT-891: BI0;/BI1; plus menu 07-08 (0 SEMI, 1 FULL). IC-7300: 16 47."""
        ctl = self._control("bkin")
        if ctl is None:
            return None
        if isinstance(self.profile, YaesuProfile):
            menu = getattr(self.profile, "BKIN_MENU", "0708")   # FT-891: 07-08 BK-IN TYPE; others: on / off only
            if v and menu:
                self.ex_write(menu, v - 1)
            self.cat("BI1;" if v else "BI0;")
        else:
            self.cat(self.profile.set_string(ctl, v))
        return self.read_bkin()

    def bkin_want(self, val):
        """Rig Settings BKIN value -> control value (radios without a break-in type: SEMI / FULL = ON)."""
        want = BKIN_VALUES.index(val)
        if isinstance(self.profile, YaesuProfile) and not getattr(self.profile, "BKIN_MENU", "0708"):
            want = min(want, 1)
        return want

    def read_bkin(self):
        ctl = self._control("bkin")
        if ctl is None:
            return None
        on = self.profile.parse_read(ctl, self.cat_read(self.profile.read_string(ctl)))
        if on and isinstance(self.profile, YaesuProfile) and getattr(self.profile, "BKIN_MENU", "0708"):
            t = self.ex_read(self.profile.BKIN_MENU if hasattr(self.profile, "BKIN_MENU") else "0708")
            on = None if t is None else (2 if str(t).upper() in ("1", "FULL") else 1)
        if on is not None:
            self.post("ctl", ("bkin", on))
        return on

    def read_control(self, ctl):
        prof = self.profile
        if not prof:
            return
        if ctl.key == "bkin":
            self.read_bkin()
            return
        try:
            reply = self.cat_read(prof.read_string(ctl))
        except xmlrpc.client.Fault:
            return
        v = prof.parse_read(ctl, reply)
        if v is not None:
            self.post("ctl", (ctl.key, v))

    def get_bws(self):
        raw = self.try_rpc("rig.get_bws")
        lst = raw
        if isinstance(raw, (list, tuple)) and raw and isinstance(raw[0], (list, tuple)):
            lst = raw[0]
        out = []
        for item in lst or []:
            s = str(item).strip()
            if s and re.search(r"\d", s):
                out.append(s)
        return out

    # ---- FT-891 VFO Scan: the radio scans by itself, RigPanel only starts / stops it ----
    def vscan_cmd(self, cmd, start_hz=None):
        """cmd = up / down / stop. start_hz: go there first (Start at the band edge)."""
        prof = self.profile
        if not getattr(prof, "HAS_VFO_SCAN", False):
            return
        if cmd != "stop":
            if int(self.try_rpc("rig.get_ptt") or 0):
                self.post("log", "VFO Scan: not while transmitting.")
                return
            if start_hz:
                self.cat(prof.scan_string("stop"))
                self.set_freq(start_hz)
        reply = self.cat(prof.scan_string(cmd))           # sent with SC; - the radio confirms
        state = prof.parse_scan(reply)
        debug_log(f"VFO Scan: {cmd}{f' from {start_hz}' if start_hz else ''} -> {state}")
        self.post("vscan", {"scan": state})

    def vscan_goto(self, hz):
        """A HEARD station clicked: stop the radio's scan, go there."""
        prof = self.profile
        if getattr(prof, "HAS_VFO_SCAN", False):
            self.post("vscan", {"scan": prof.parse_scan(self.cat(prof.scan_string("stop")))})
        self.set_freq(hz)

    def vscan_read(self, all_=False):
        """Scan state (once a second while the window is open); squelch and resume on opening."""
        prof = self.profile
        if not getattr(prof, "HAS_VFO_SCAN", False):
            return
        out = {"scan": prof.parse_scan(self.cat_read("SC;"))}
        if all_:
            out["sql"] = prof.parse_squelch(self.cat_read("SQ0;"))
            code = prof.SCAN_RESUME_MENU
            out["resume"] = prof.menu_parse(code, self.cat_read(prof.menu_read_string(code)))
        self.post("vscan", out)

    def vscan_squelch(self, n):
        prof = self.profile
        if getattr(prof, "HAS_VFO_SCAN", False):
            self.post("vscan", {"sql": prof.parse_squelch(self.cat(prof.squelch_string(n)))})

    def vscan_resume(self, v):
        prof = self.profile
        if getattr(prof, "HAS_VFO_SCAN", False):
            code = prof.SCAN_RESUME_MENU
            self.post("vscan", {"resume": prof.menu_parse(code, self.cat(prof.menu_write_string(code, v)))})

    # ---- thread loop ----
    def run(self):
        while self.alive:
            if not self.enabled:
                time.sleep(0.2)
                continue
            if self.proxy is None and not self._connect():
                time.sleep(2.0)
                continue
            deadline = time.monotonic() + POLL_S
            while self.proxy is not None:
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    break
                if not self.alive:
                    break
                try:
                    job = self.jobs.get(timeout=remaining)
                except queue.Empty:
                    break
                self._guard(job)
            if self.proxy is not None and self.alive:
                self._guard(lambda w: w._poll())
        if self.proxy is not None:               # RigPanel is closing: hang up on flrig cleanly
            self._fresh_connection()
            self.proxy = None
            debug_log("closed the connection to flrig")

    def _guard(self, job):
        try:
            job(self)
            self.timeouts = 0
        except socket.timeout:
            # a late reply: flrig is still there, just busy with the radio
            self.timeouts += 1
            if self.timeouts >= TIMEOUTS_BEFORE_LOST:
                self.timeouts = 0
                self.proxy = None
                self.post("down", f"Lost flrig: no reply in {RPC_TIMEOUT_S:.0f} s, {TIMEOUTS_BEFORE_LOST} times in a row")
            elif time.monotonic() - self.slow_noted > 30:
                self.slow_noted = time.monotonic()
                self.post("log", "flrig is slow to answer (busy with the radio?) - still connected")
        except self.NET_ERRORS as e:
            self.timeouts = 0
            self.proxy = None
            self.post("down", f"Lost flrig: {e}")
        except xmlrpc.client.Fault as e:
            self.post("log", f"flrig refused a command: {e.faultString}")
        except Exception as e:
            self.post("log", f"Error: {e}")

    def _connect(self):
        try:
            proxy = xmlrpc.client.ServerProxy(self.url, transport=TimeoutTransport(RPC_TIMEOUT_S), allow_none=True)
            try:
                methods = set(proxy.system.listMethods())
            except xmlrpc.client.Fault:
                methods = set()
            xcvr = str(proxy.rig.get_xcvr())
        except Exception:
            self.post("down", f"Waiting for flrig at {self.url.split('/RPC2')[0]} ...")
            return False
        self.proxy, self.methods = proxy, methods
        self.last_mode = None
        try:
            pm = self.try_rpc("rig.get_pwrmax")
            self.pmax = float(pm) if pm and float(pm) > 0 else 100.0
        except (ValueError, TypeError):
            self.pmax = 100.0
        self.post("connected", {"xcvr": xcvr, "pmax": self.pmax})
        ver = ""
        if "main.get_version" in methods:
            try:
                ver = f", flrig {proxy.main.get_version()}"
            except Exception:
                pass
        # flrig 2.0.12 on: FT-891 sets go with rig.cmd_string (no wait) - see cat()
        nums = [int(x) for x in re.findall(r"\d+", ver)[:3]]
        self.yaesu_cmd_string = "rig.cmd_string" in methods and len(nums) == 3 and tuple(nums) >= (2, 0, 12)
        debug_log(f"connected to flrig at {self.url}, rig '{xcvr}', {len(methods)} methods{ver}, "
                  f"{platform.system()} {platform.release()}, Python {platform.python_version()}")
        modes = [str(m) for m in (self.try_rpc("rig.get_modes") or [])]
        self.post("tables", {"modes": modes, "bws": self.get_bws()})
        return True

    def _poll(self):
        d = {}
        d["freq"] = float(self.rpc("rig.get_vfo"))
        d["mode"] = self.get_mode()
        bw = self.try_rpc("rig.get_bw")
        if isinstance(bw, (list, tuple)):
            bw = bw[0] if bw else ""
        d["bw"] = str(bw or "")
        d["ptt"] = bool(int(self.try_rpc("rig.get_ptt") or 0))
        if self.cycle % 2 == 0 and self._swap_only():
            d["ab"] = self.cur_ab = "A"
            if str(self.try_rpc("rig.get_AB") or "A").strip().upper()[:1] == "B":
                # flrig's own "VFO B" swapped the registers: undo it, so flrig and RigPanel agree
                self.rpc("rig.set_AB", "A")
                self.post("log", "flrig was on its 'VFO B' (a swap on the FT-891) - put back to A")
            fb = re.search(r"FB(\d+)", str(self.cat_read("FB;")))
            d["other_freq"] = float(fb.group(1)) if fb else None
            sp = self.try_rpc("rig.get_split")
            d["split"] = bool(int(sp)) if sp not in (None, "") else None
        elif self.cycle % 2 == 0 and self.has("rig.get_AB"):
            ab = str(self.try_rpc("rig.get_AB") or "A").strip().upper()[:1]
            d["ab"] = "B" if ab == "B" else "A"
            self.cur_ab = d["ab"]
            other = self.try_rpc("rig.get_vfoA" if d["ab"] == "B" else "rig.get_vfoB")
            try:
                d["other_freq"] = float(other) if other not in (None, "") else None
            except (TypeError, ValueError):
                d["other_freq"] = None
            sp = self.try_rpc("rig.get_split")
            d["split"] = bool(int(sp)) if sp not in (None, "") else None

        if d["ptt"]:
            po = None
            if self.profile and hasattr(self.profile, "po_string"):    # the radio's own meter, our scale
                try:
                    po = self.profile.parse_po(self.cat_read(self.profile.po_string()))
                except xmlrpc.client.Fault:
                    po = None
            if po is not None:
                d["po"] = float(po)
            else:
                pwr = self.try_rpc("rig.get_pwrmeter")
                if pwr is not None:
                    scale = self.try_rpc("rig.get_pwrmeter_scale") if "rig.get_pwrmeter_scale" in self.methods else None
                    d["po"] = float(pwr) * (float(scale) if scale else 1.0)
            if "rig.get_SWR" in self.methods:
                v = self.try_rpc("rig.get_SWR")
                if v is not None:
                    d["swr"] = float(v)
            else:
                v = self.try_rpc("rig.get_swrmeter")
                if v is not None:
                    d["swr"] = swr_from_deflection(float(v))
            if self.profile and self.has("rig.cat_string"):
                try:
                    a = self.profile.parse_alc(self.cat_read(self.profile.alc_string()))
                    if a is not None:
                        d["alc"] = a
                except xmlrpc.client.Fault:
                    pass
        else:
            s = self.try_rpc("rig.get_smeter")
            if s is not None:
                d["smeter"] = float(s)

        self.cycle += 1
        now = time.monotonic()
        if self.cycle % 8 == 1:
            keys = ["power", "volume", "rfgain", "micgain"]
            cat_keys = [k for k in ("rfgain", "volume") if self._cat_level_ok(k)]   # read from the radio: paced
            if cat_keys:
                if now >= self.level_cat_due:
                    self.level_cat_due = now + CAT_LEVEL_S * self.pace()
                else:
                    keys = [k for k in keys if k not in cat_keys]
            for key in keys:
                try:
                    v = self.read_level(key)
                    if v is not None:
                        d[key] = float(v)
                except (TypeError, ValueError, xmlrpc.client.Fault):
                    pass

        if d["mode"] != self.last_mode:          # filter table depends on mode
            if self.last_mode is not None:
                self.post("tables", {"bws": self.get_bws()})
            self.last_mode = d["mode"]

        self.post("poll", d)

        # Background CAT reads, at most ONE per poll so flrig is never tied up:
        # 1) every receive control once after connect / rig change, 2) the FT-891 macro
        # menu items once per MACRO_CYCLE_S, 3) one receive control every CTL_READ_S so the
        # panel follows changes made on the radio. All intervals stretch when CAT is slow.
        prof = self.profile
        if not prof or d["ptt"] or not self.has("rig.cat_string"):
            return
        if self.full_read:
            self.full_read = False
            self.ctl_pending = list(prof.controls)
        if self.ctl_pending:
            self.read_control(self.ctl_pending.pop(0))
            return
        if self.macro_codes:
            if not self.macro_pending and now >= self.macro_read_due:
                self.macro_pending = sorted(self.macro_codes - self.ex_unsupported)
                self.macro_read_due = now + MACRO_CYCLE_S * self.pace()
            if self.macro_pending:
                self.read_macro_state([self.macro_pending.pop(0)])
                return
        for name, needs, voice_only in self.EXTRA_READS:     # SHIFT / CLAR follow the radio's own knobs
            if hasattr(prof, needs) and now >= self.extra_due.get(name, 0.0) and \
                    (not voice_only or str(d.get("mode", "")).upper() in ("USB", "LSB")):
                self.extra_due[name] = now + CTL_READ_S * 3 * self.pace()
                getattr(self, name)()
                return
        if prof.controls and now >= self.ctl_due:
            self.ctl_due = now + CTL_READ_S * self.pace()
            self.ctl_rr = (self.ctl_rr + 1) % len(prof.controls)
            self.read_control(prof.controls[self.ctl_rr])
