# -*- mode: python ; coding: utf-8 -*-
#
# PyInstaller spec for ShadowBridge
#
# Build with:
#   pyinstaller ShadowBridge.spec
#
# Output: dist/ShadowBridge.exe

from PyInstaller.utils.hooks import collect_all

block_cipher = None

# Collect all sub-modules, data files, and binaries for packages that
# PyInstaller can't fully discover through static import analysis.
pil_datas,     pil_binaries,     pil_hiddenimports     = collect_all('PIL')
pystray_datas, pystray_binaries, pystray_hiddenimports = collect_all('pystray')
pa_datas,      pa_binaries,      pa_hiddenimports      = collect_all('pyaudiowpatch')

a = Analysis(
    ['ShadowBridge.py'],
    pathex=[],
    binaries=[
        *pil_binaries,
        *pystray_binaries,
        *pa_binaries,
    ],
    datas=[
        # Bundle the icon so resource_path() can find it at runtime
        ('audiobridge_icon.ico', '.'),
        *pil_datas,
        *pystray_datas,
        *pa_datas,
    ],
    hiddenimports=[
        # pystray Win32 backend
        'pystray._win32',
        # Pillow — only the pieces we actually use
        'PIL.Image',
        'PIL.ImageDraw',
        # pyaudiowpatch / PortAudio
        'pyaudiowpatch',
        # audioop is absent in Python 3.13+; the code has a fallback,
        # but include it when present so the faster path is used.
        'audioop',
        *pil_hiddenimports,
        *pystray_hiddenimports,
        *pa_hiddenimports,
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    # Keep the bundle lean — nothing here is used by ShadowBridge
    excludes=['matplotlib', 'numpy', 'scipy', 'IPython', 'pytest'],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='ShadowBridge',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    # UPX shrinks the exe by ~30 %. Set upx=False if antivirus flags it.
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    # No console window
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='audiobridge_icon.ico',
)

# ── Post-build ──────────────────────────────────────────────────────────────
import os as _os, datetime as _dt

_exe_out = _os.path.join(DISTPATH, 'ShadowBridge.exe')
if _os.path.exists(_exe_out):
    _mb  = _os.path.getsize(_exe_out) / (1024 * 1024)
    _ts  = _dt.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    print(f"\n  Build complete  [{_ts}]")
    print(f"  Output : {_exe_out}")
    print(f"  Size   : {_mb:.1f} MB\n")
else:
    print(f"\n  WARNING: exe not found at expected path: {_exe_out}\n")
