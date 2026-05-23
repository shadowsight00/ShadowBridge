; ShadowBridge NSIS Installer Template
; Tauri injects: $PRODUCTNAME, $VERSION, $MANUFACTURER, $INSTALLDIR, $MAINBINARYNAME
; and all standard MUI pages / macros.

!include "MUI2.nsh"
!include "LogicLib.nsh"
!include "WinMessages.nsh"

; ── Branding ─────────────────────────────────────────────────────────────────
Name "${PRODUCTNAME}"
OutFile "${OUTFILE}"
Unicode True
SetCompressor /SOLID lzma
RequestExecutionLevel user   ; currentUser install

; ── MUI Settings ─────────────────────────────────────────────────────────────
!define MUI_ABORTWARNING
!define MUI_ICON "${TAURI_ICONS_DIR}\icon.ico"
!define MUI_UNICON "${TAURI_ICONS_DIR}\icon.ico"

; Header / sidebar images
!define MUI_HEADERIMAGE
!define MUI_HEADERIMAGE_BITMAP "${NSIS_ASSETS_DIR}\header.bmp"
!define MUI_HEADERIMAGE_RIGHT
!define MUI_WELCOMEFINISHPAGE_BITMAP "${NSIS_ASSETS_DIR}\sidebar.bmp"
!define MUI_UNWELCOMEFINISHPAGE_BITMAP "${NSIS_ASSETS_DIR}\sidebar.bmp"

; Colors (dark theme approximation via text overrides)
!define MUI_BGCOLOR "090D13"
!define MUI_TEXTCOLOR "E6EDF3"

; ── Pages ─────────────────────────────────────────────────────────────────────
!insertmacro MUI_PAGE_WELCOME
!insertmacro MUI_PAGE_LICENSE "${NSIS_ASSETS_DIR}\license.rtf"
!insertmacro MUI_PAGE_DIRECTORY
!insertmacro MUI_PAGE_INSTFILES
!define MUI_FINISHPAGE_RUN "$INSTDIR\${MAINBINARYNAME}.exe"
!define MUI_FINISHPAGE_RUN_TEXT "Launch ShadowBridge"
!insertmacro MUI_PAGE_FINISH

!insertmacro MUI_UNPAGE_WELCOME
!insertmacro MUI_UNPAGE_CONFIRM
!insertmacro MUI_UNPAGE_INSTFILES
!insertmacro MUI_UNPAGE_FINISH

!insertmacro MUI_LANGUAGE "English"

; ── Helpers ───────────────────────────────────────────────────────────────────
; Detect and silently remove old Python-based ShadowBridge / AudioBridge
!macro RemoveOldInstall REG_KEY_NAME
  ReadRegStr $0 HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\${REG_KEY_NAME}" "UninstallString"
  ${If} $0 != ""
    DetailPrint "Removing previous ${REG_KEY_NAME} installation..."
    ExecWait '"$0" /S' $1
    DetailPrint "Old uninstaller exited with code $1"
  ${EndIf}
  ReadRegStr $0 HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${REG_KEY_NAME}" "UninstallString"
  ${If} $0 != ""
    DetailPrint "Removing previous ${REG_KEY_NAME} (system) installation..."
    ExecWait '"$0" /S' $1
    DetailPrint "Old uninstaller exited with code $1"
  ${EndIf}
!macroend

; Migrate config from old location to new
!macro MigrateConfig OLD_DIR NEW_DIR
  ${If} ${FileExists} "${OLD_DIR}\config.json"
  ${AndIfNot} ${FileExists} "${NEW_DIR}\config.json"
    CreateDirectory "${NEW_DIR}"
    CopyFiles /SILENT "${OLD_DIR}\config.json" "${NEW_DIR}\config.json"
    DetailPrint "Migrated config from ${OLD_DIR} to ${NEW_DIR}"
  ${EndIf}
!macroend

; ── Installer Sections ────────────────────────────────────────────────────────
Section "MainSection" SEC01
  SetOutPath "$INSTDIR"

  ; Remove old installations before installing
  !insertmacro RemoveOldInstall "ShadowBridge"
  !insertmacro RemoveOldInstall "AudioBridge"

  ; Migrate config from old AudioBridge location
  !insertmacro MigrateConfig "$DOCUMENTS\AudioBridge" "$DOCUMENTS\ShadowBridge"
  ; Also try old ShadowBridge Python location
  !insertmacro MigrateConfig "$APPDATA\ShadowBridge" "$DOCUMENTS\ShadowBridge"

  ; Install files (Tauri injects this)
  !insertmacro TAURI_INSTALL_FILES

  ; Write uninstall registry keys
  WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\ShadowBridge" \
    "DisplayName" "ShadowBridge"
  WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\ShadowBridge" \
    "DisplayVersion" "${VERSION}"
  WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\ShadowBridge" \
    "Publisher" "${MANUFACTURER}"
  WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\ShadowBridge" \
    "UninstallString" '"$INSTDIR\Uninstall ShadowBridge.exe"'
  WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\ShadowBridge" \
    "InstallLocation" "$INSTDIR"
  WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\ShadowBridge" \
    "DisplayIcon" "$INSTDIR\${MAINBINARYNAME}.exe"
  WriteRegDWORD HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\ShadowBridge" \
    "NoModify" 1
  WriteRegDWORD HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\ShadowBridge" \
    "NoRepair" 1

  ; App-specific registry key (for future detection)
  WriteRegStr HKCU "Software\ShadowBridge" "InstallDir" "$INSTDIR"
  WriteRegStr HKCU "Software\ShadowBridge" "Version" "${VERSION}"

  ; Start menu shortcut
  CreateDirectory "$SMPROGRAMS\ShadowBridge"
  CreateShortcut "$SMPROGRAMS\ShadowBridge\ShadowBridge.lnk" \
    "$INSTDIR\${MAINBINARYNAME}.exe" "" "$INSTDIR\${MAINBINARYNAME}.exe" 0

  ; Desktop shortcut
  CreateShortcut "$DESKTOP\ShadowBridge.lnk" \
    "$INSTDIR\${MAINBINARYNAME}.exe" "" "$INSTDIR\${MAINBINARYNAME}.exe" 0

  WriteUninstaller "$INSTDIR\Uninstall ShadowBridge.exe"
SectionEnd

; ── Uninstaller ───────────────────────────────────────────────────────────────
Section "Uninstall"
  ; Remove autostart entry if present
  DeleteRegValue HKCU "Software\Microsoft\Windows\CurrentVersion\Run" "ShadowBridge"

  ; Remove files (Tauri injects this)
  !insertmacro TAURI_UNINSTALL_FILES

  Delete "$INSTDIR\Uninstall ShadowBridge.exe"
  RMDir "$INSTDIR"

  ; Remove shortcuts
  Delete "$SMPROGRAMS\ShadowBridge\ShadowBridge.lnk"
  RMDir "$SMPROGRAMS\ShadowBridge"
  Delete "$DESKTOP\ShadowBridge.lnk"

  ; Remove registry keys
  DeleteRegKey HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\ShadowBridge"
  DeleteRegKey HKCU "Software\ShadowBridge"
SectionEnd
