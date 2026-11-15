@echo off
rem RigPanel for Windows - double-click to start.
rem Uses the "py" launcher if present, otherwise "python".
rem Installs the waterfall packages the first time if they are missing.
cd /d "%~dp0"

set "PY=py"
where py >nul 2>nul || set "PY=python"
where %PY% >nul 2>nul || (
    echo Python was not found. Install Python 3.9+ from python.org and tick "Add Python to PATH".
    pause
    exit /b 1
)

%PY% -c "import numpy, sounddevice, PIL" >nul 2>nul || (
    echo Installing waterfall packages: numpy sounddevice pillow ...
    %PY% -m pip install --user numpy sounddevice pillow
)

%PY% run_rigpanel.py
if errorlevel 1 (
    echo.
    echo RigPanel exited with an error - see the messages above.
    pause
)
