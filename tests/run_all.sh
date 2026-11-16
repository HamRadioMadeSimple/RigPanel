#!/bin/bash
# Full test run (Linux, needs Xvfb + openbox + python3 with Tk): bash tests/run_all.sh [python]
# names check, then regress.py and features.py against the practice radio in the key modes.
PY=${1:-python3}
HERE=$(cd "$(dirname "$0")/.." && pwd)
T=$(mktemp -d)
echo '{"port": 12401, "audio_device": "Demo (test tones)"}' > "$T/.rigpanel.json"
$PY "$HERE/tests/names_check.py" || exit 1
Xvfb :91 -screen 0 1400x1000x24 >/dev/null 2>&1 & X=$!; sleep 1
export DISPLAY=:91 HOME=$T
unset XDG_CONFIG_HOME   # settings must go to the throwaway HOME (GitHub sets this variable)
openbox >/dev/null 2>&1 & O=$!; sleep 1
run() {  # run <test> <rig> [mock flag]
  rm -rf "$T/.config"
  $PY "$HERE/mock_flrig.py" --rig "$2" --port 12401 $3 > "$T/mock.log" 2>&1 & M=$!; sleep 1.5
  timeout 240 $PY "$HERE/tests/$1" "$T" "$2" "${3:-normal}" 2>&1 | grep -E "FAIL|=="
  kill $M; wait $M 2>/dev/null; sleep 0.5
}
for t in regress.py features.py; do
  run $t FT-891 --real891
  run $t IC-7300 --flrig212
done
kill $O $X
