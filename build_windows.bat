@echo off
rem ======================================================================
rem  RigPanel - Windows build: makes output\RigPanel_Setup_<ver>.exe
rem  Needs: Python 3.9+ (Add to PATH) and Inno Setup 6 (free, jrsoftware.org)
rem  Double-click this file in the RigPanel folder.
rem ======================================================================
setlocal
cd /d "%~dp0"
set VER=1.4.3
rem On GitHub (CI set) never wait for a key
if defined CI (set "PAUSE=ver>nul") else (set "PAUSE=pause")

where py >nul 2>nul && (set PY=py) || (set PY=python)
%PY% --version >nul 2>nul || (echo Python not found. Install Python 3.9+ with "Add to PATH". & %PAUSE% & exit /b 1)

echo.
echo [1/3] Installing build tools (PyInstaller, numpy, sounddevice, pillow)...
%PY% -m pip install --upgrade --quiet pyinstaller numpy sounddevice pillow || (echo pip failed - are you online? & %PAUSE% & exit /b 1)

echo.
echo [2/3] Building RigPanel.exe...
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist
%PY% -m PyInstaller --noconfirm --clean --windowed --name RigPanel --icon icon.ico ^
  --add-data "icon.png;." --add-data "icon_small.png;." --add-data "icon.ico;." ^
  --collect-all sounddevice --hidden-import PIL._tkinter_finder run_rigpanel.py || (echo PyInstaller failed. & %PAUSE% & exit /b 1)

echo.
echo [3/3] Making the installer...
set ISCC=
if exist "%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe" set ISCC="%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe"
if exist "%ProgramFiles%\Inno Setup 6\ISCC.exe" set ISCC="%ProgramFiles%\Inno Setup 6\ISCC.exe"
if exist "%LOCALAPPDATA%\Programs\Inno Setup 6\ISCC.exe" set ISCC="%LOCALAPPDATA%\Programs\Inno Setup 6\ISCC.exe"
if not defined ISCC (
  echo Inno Setup 6 not found - get it from https://jrsoftware.org/isdl.php and run this again.
  echo The program itself is ready in dist\RigPanel\RigPanel.exe
  %PAUSE% & exit /b 1
)
if not exist output mkdir output
%ISCC% /Q /DMyVersion=%VER% RigPanel.iss || (echo Inno Setup failed. & %PAUSE% & exit /b 1)

echo.
echo Done: output\RigPanel_Setup_%VER%.exe
%PAUSE%
