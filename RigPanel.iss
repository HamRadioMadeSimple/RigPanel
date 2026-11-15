; RigPanel installer (Inno Setup 6). Built by build_windows.bat.
#ifndef MyVersion
  #define MyVersion "1.4.3"
#endif

[Setup]
AppId={{6B1F2C1E-7A0B-4E39-9C1D-52A6D3F0E7A1}
AppName=RigPanel
AppVersion={#MyVersion}
AppPublisher=KW3KW
DefaultDirName={commonpf32}\RigPanel
DefaultGroupName=RigPanel
; installs in C:\Program Files (x86)\RigPanel for all users (asks for admin once)
PrivilegesRequired=admin
OutputDir=output
OutputBaseFilename=RigPanel_Setup_{#MyVersion}
SetupIconFile=icon.ico
UninstallDisplayIcon={app}\RigPanel.exe
Compression=lzma2
SolidCompression=yes
WizardStyle=modern

[Tasks]
; ticked by default
Name: "desktopicon"; Description: "Create a desktop icon"; GroupDescription: "Shortcuts:"

[Files]
Source: "dist\RigPanel\*"; DestDir: "{app}"; Flags: recursesubdirs createallsubdirs ignoreversion

[Icons]
Name: "{group}\RigPanel"; Filename: "{app}\RigPanel.exe"; IconFilename: "{app}\RigPanel.exe"
Name: "{group}\Uninstall RigPanel"; Filename: "{uninstallexe}"
Name: "{autodesktop}\RigPanel"; Filename: "{app}\RigPanel.exe"; IconFilename: "{app}\RigPanel.exe"; Tasks: desktopicon

[Run]
Filename: "{app}\RigPanel.exe"; Description: "Start RigPanel now"; Flags: nowait postinstall skipifsilent
