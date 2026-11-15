# Helping with RigPanel

Thanks for helping! Bug reports, reports of which radios work, and code are all welcome.

## Reporting a problem

Open an issue on the [Issues page](https://github.com/HamRadioMadeSimple/RigPanel/issues) with:
- what you did and what happened (a screenshot helps a lot)
- the build shown at the bottom right of RigPanel, Windows or Linux version, your radio, and your
  flrig version (flrig > Help > About)
- the file `rigpanel_debug.log` - click the build text in RigPanel to open its folder
  (`%APPDATA%\RigPanel` on Windows, `~/.config/rigpanel` on Linux)

Radios added with **Settings ▾ > Add my radio** are tested by users: please report what works and what
doesn't. The scripts in `tools/` read a radio's settings for a report (read-only unless the name says
*write*, and those put everything back).

## Running from source

Python 3.9+ with Tk (Linux: `sudo apt install python3-tk`). No radio needed: start the practice radio first.

```
python3 mock_flrig.py --rig IC-7300     # in one terminal (or --rig FT-891)
python3 -m rigpanel                     # in another
```

## Tests

Linux, needs Xvfb and openbox (`sudo apt install xvfb openbox`) and the packages in `requirements.txt`:

```
bash tests/run_all.sh
```

Every line should end in `passed` with no `FAIL`. GitHub runs the same tests on every push.

## Where things are

The full picture (modules, how RigPanel talks to flrig, radio details) is in
[docs/RIGPANEL_ARCHITECTURE_Version_1_4_3.md](docs/RIGPANEL_ARCHITECTURE_Version_1_4_3.md);
flrig version notes are in [docs/FLRIG_COMPATIBILITY.md](docs/FLRIG_COMPATIBILITY.md).
Every module does `from .earlier import *`; `tests/names_check.py` catches names defined twice or used
before they exist.

## Making a release

Bump `APP_VERSION` / `APP_BUILD` in `rigpanel/core.py` and `VER=` in `build_linux.sh` and
`build_windows.bat`, and add a `## <version>` section at the top of `CHANGELOG.md`. Then create a release
with the tag `v<version>` on GitHub: the Release workflow builds and attaches all files.

## License

By contributing you agree that your work is released under the GPL-3.0 (see LICENSE).
