"""Program entry point."""
from .core import *  # noqa: F401,F403
from .radios import *  # noqa: F401,F403
from .worker import *  # noqa: F401,F403
from .widgets import *  # noqa: F401,F403
from .waterfall import *  # noqa: F401,F403
from .freqlist import *  # noqa: F401,F403
from .minis import *  # noqa: F401,F403
from .builder import *  # noqa: F401,F403
from .app import *  # noqa: F401,F403

def set_app_icon(root):
    """Window / taskbar icon from icon.png / icon.ico next to rigpanel.py (skipped if missing)."""
    here = RES_DIR
    try:
        if SYS == "Windows" and os.path.exists(os.path.join(here, "icon.ico")):
            # the .ico has hand-made small sizes (plain meter, no tiny text) for the title bar
            root.iconbitmap(default=os.path.join(here, "icon.ico"))   # also used by Toplevels
            return
        imgs = [tk.PhotoImage(file=os.path.join(here, f)) for f in ("icon.png", "icon_small.png")
                if os.path.exists(os.path.join(here, f))]
        if imgs:                 # Linux/macOS: big one with the name + 32 px plain one for title bars
            root._icon_imgs = imgs
            root.iconphoto(True, *imgs)
    except (tk.TclError, OSError):
        pass


def main():
    if SYS == "Windows":          # sharp text on high-DPI screens instead of blurry scaling
        try:
            import ctypes
            ctypes.windll.shcore.SetProcessDpiAwareness(1)
            # own taskbar button + icon instead of grouping under python.exe
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("RigPanel.1")
        except Exception:
            pass
    ensure_data_dir()
    root = tk.Tk(className="RigPanel")   # Linux WM_CLASS "Rigpanel" = StartupWMClass in the .desktop entry
    pick_fonts(root)
    set_app_icon(root)
    App(root)
    root.mainloop()
