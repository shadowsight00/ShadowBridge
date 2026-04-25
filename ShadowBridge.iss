; Inno Setup script for ShadowBridge
; Compile with: iscc ShadowBridge.iss
; Output: Output\ShadowBridge_Setup.exe

#define AppName      "ShadowBridge"
#define AppVersion   "0.4.0"
#define AppPublisher "Your Name or Company"
#define AppExeName   "ShadowBridge.exe"
#define AppIcoName   "shadowbridge_icon.ico"
#define AppDataDir   "{userdocs}\ShadowBridge"

[Setup]
AppId={{A1B2C3D4-E5F6-7890-ABCD-EF1234567890}
AppName={#AppName}
AppVersion={#AppVersion}
AppPublisherURL=https://github.com/
AppPublisher={#AppPublisher}
DefaultDirName={autopf}\{#AppName}
DefaultGroupName={#AppName}
AllowNoIcons=yes
OutputDir=Output
OutputBaseFilename=ShadowBridge_Setup
SetupIconFile=shadowbridge_icon.ico
UninstallDisplayIcon={app}\{#AppIcoName}
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=admin
ArchitecturesInstallIn64BitMode=x64compatible
; Don't offer to run the app at the end of install — user may need to
; configure IPs first.
DisableFinishedPage=no

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "Create a &desktop shortcut"; GroupDescription: "Additional shortcuts:"; Flags: unchecked

[Files]
; Main executable — pulled from dist/ after running build.bat / PyInstaller
Source: "C:\Users\ajsme\OneDrive\Documents\GitHub\ShadowBridge\dist\{#AppExeName}"; DestDir: "{app}"; Flags: ignoreversion

; Icon (used by shortcuts and the uninstaller entry)
Source: "C:\Users\ajsme\OneDrive\Documents\GitHub\ShadowBridge\{#AppIcoName}"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
; Start Menu shortcut
Name: "{group}\{#AppName}"; Filename: "{app}\{#AppExeName}"; IconFilename: "{app}\{#AppIcoName}"

; Start Menu uninstall shortcut
Name: "{group}\Uninstall {#AppName}"; Filename: "{uninstallexe}"

; Optional Desktop shortcut (only created when user ticks the task)
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\{#AppExeName}"; IconFilename: "{app}\{#AppIcoName}"; Tasks: desktopicon

[Dirs]
; Create the user data folder on first install so the app can write config
; and logs immediately.  The folder is intentionally NOT listed in [UninstallDelete]
; so the uninstaller leaves it — and all user data — intact.
Name: "{userdocs}\{#AppName}"; Flags: uninsneveruninstall

[Run]
; Refresh Windows icon cache so new icon appears immediately in Start Menu / Desktop.
Filename: "ie4uinit.exe"; Parameters: "-show"; Flags: runhidden nowait

; Offer to launch the app after installation finishes.
Filename: "{app}\{#AppExeName}"; Description: "Launch {#AppName}"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
; Remove only what we put in Program Files — never touch the data folder.
Type: filesandordirs; Name: "{app}"
