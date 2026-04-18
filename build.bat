@echo off
cd /d "%~dp0"
echo.
echo  Building ShadowBridge...
echo  -----------------------------------------------
python -m PyInstaller ShadowBridge.spec --noconfirm
echo  -----------------------------------------------
if %errorlevel% == 0 (
    echo  SUCCESS: dist\ShadowBridge.exe is ready.
) else (
    echo  FAILED : PyInstaller exited with code %errorlevel%.
    echo  Check the output above for errors.
)
echo.
pause
