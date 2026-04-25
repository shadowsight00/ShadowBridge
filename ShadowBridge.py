import ctypes
ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID('shadowbridge.app')

import winreg
import tkinter as tk
from tkinter import scrolledtext, colorchooser, filedialog
import pyaudiowpatch as pyaudio
import socket
import threading
import queue
import struct
import json
import os
import re
import sys
import uuid
import logging
import datetime
import time
import traceback
import asyncio
import base64
import io
import math

try:
    import websockets
    WS_AVAILABLE = True
except ImportError:
    WS_AVAILABLE = False

try:
    from pycaw.pycaw import AudioUtilities
    import psutil
    PYCAW_AVAILABLE = True
except ImportError:
    PYCAW_AVAILABLE = False

try:
    import pystray
    from PIL import Image as PILImage, ImageTk as PILImageTk
    TRAY_AVAILABLE = True
except ImportError:
    TRAY_AVAILABLE = False
    PILImageTk = None

try:
    from winotify import Notification as _WiNotification
    NOTIF_AVAILABLE = True
except ImportError:
    NOTIF_AVAILABLE = False

try:
    import audioop
    def _scale_volume(data, volume_pct):
        if volume_pct >= 100:
            return data
        return audioop.mul(data, 2, volume_pct / 100.0)
except ImportError:
    def _scale_volume(data, volume_pct):
        if volume_pct >= 100:
            return data
        vol = volume_pct / 100.0
        count = len(data) // 2
        if count == 0:
            return data
        samples = struct.unpack(f"{count}h", data)
        return struct.pack(f"{count}h", *[max(-32768, min(32767, int(s * vol))) for s in samples])

VERSION = "0.4.0"

STRIP_W       = 80    # fixed channel strip width (px)
N_BARS        = 14    # level meter segments
INSTANCE_PORT = 47778 # single-instance enforcement port

_instance_server_sock = None


def _enforce_single_instance():
    """Bind the instance port. If already bound, signal the running instance and exit."""
    global _instance_server_sock
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 0)
    try:
        sock.bind(('127.0.0.1', INSTANCE_PORT))
        sock.listen(5)
        _instance_server_sock = sock
    except OSError:
        sock.close()
        try:
            notify = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            notify.settimeout(2)
            notify.connect(('127.0.0.1', INSTANCE_PORT))
            notify.sendall(b'SHOW\n')
            notify.close()
        except Exception:
            pass
        sys.exit(0)


class _NoOp:
    """Dummy widget stub — absorbs .config() calls without error."""
    def config(self, **kw):   pass
    def configure(self, **kw): pass

# ── HUD font families (registered at runtime from Google Fonts TTFs) ──────────
FONT_ORBITRON = "Orbitron"
FONT_MONO     = "Share Tech Mono"
FONT_RAJDHANI = "Rajdhani"
# #00d4e8 at ~20 % opacity blended onto #040e14
CYAN_DIM      = "#033e45"

_UUID_RE = re.compile(
    r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$',
    re.IGNORECASE
)

BG     = "#040e14"
BG2    = "#1a1a1a"
BG3    = "#242424"
BORDER = "#2e2e2e"
TEXT   = "#e8e8e8"
MUTED  = "#666666"
GREEN  = "#4ade80"
GREEN2 = "#166534"
RED    = "#f87171"
RED2   = "#7f1d1d"
AMBER  = "#fbbf24"
AMBER2 = "#78350f"
BLUE   = "#60a5fa"
BLUE2  = "#1e3a5f"
DIM    = "#404040"
PURPLE  = "#a855f7"
PURPLE2 = "#3b0764"

ORANGE  = "#fb923c"
ORANGE2 = "#7c2d12"

_DIR_META = {
    'out':     (GREEN2,  GREEN,  "OUT",     "🔊"),
    'in':      (BLUE2,   BLUE,   "IN",      "🎧"),
    'mic':     (AMBER2,  AMBER,  "MIC",     "🎙️"),
    'mic-in':  (AMBER2,  AMBER,  "MIC-IN",  "🎙️"),
    'mic-out': (ORANGE2, ORANGE, "MIC-OUT", "🔈"),
    'app':     (PURPLE2, PURPLE, "APP",     "🖥️"),
}

_STRIP_STYLE = {
    'out':     {'bg': '#0d1f14', 'border': '#1a3a22', 'fg': '#4ade80', 'badge_bg': '#166534'},
    'in':      {'bg': '#0a1929', 'border': '#1e3a5f', 'fg': '#60a5fa', 'badge_bg': '#1e3a5f'},
    'mic':     {'bg': '#1a1200', 'border': '#3a2800', 'fg': '#fbbf24', 'badge_bg': '#78350f'},
    'mic-in':  {'bg': '#1a1200', 'border': '#3a2800', 'fg': '#fbbf24', 'badge_bg': '#78350f'},
    'mic-out': {'bg': '#1a0800', 'border': '#3a1400', 'fg': '#fb923c', 'badge_bg': '#7c2d12'},
    'app':     {'bg': '#150f26', 'border': '#2e1a4a', 'fg': '#a855f7', 'badge_bg': '#3b0764'},
    'skyblue': {'bg': '#0a1520', 'border': '#1a3050', 'fg': '#38bdf8', 'badge_bg': '#0c4a6e'},
}
_DIR_BADGE_STYLE = {
    'out':     {'bg': '#166534', 'fg': '#4ade80', 'text': 'OUT'},
    'in':      {'bg': '#1e3a5f', 'fg': '#60a5fa', 'text': 'IN'},
    'mic':     {'bg': '#78350f', 'fg': '#fbbf24', 'text': 'MIC'},
    'mic-in':  {'bg': '#78350f', 'fg': '#fbbf24', 'text': 'MIC-IN'},
    'mic-out': {'bg': '#7c2d12', 'fg': '#fb923c', 'text': 'MIC-OUT'},
    'app':     {'bg': '#3b0764', 'fg': '#a855f7', 'text': 'APP'},
    'skyblue': {'bg': '#0c4a6e', 'fg': '#38bdf8', 'text': 'IN'},
}

_SKYBLUE_NAMES = ('discord', 'comms', 'voice', 'teamspeak', 'ts3', 'ventrilo', 'mumble')

def _channel_style_key(channel):
    """Return _STRIP_STYLE key based on channel name keywords, then direction."""
    name = channel.get('name', '').lower()
    if any(k in name for k in _SKYBLUE_NAMES):
        return 'skyblue'
    d = channel.get('direction', 'out')
    # 'mic' is legacy alias for 'mic-in'
    return d if d in _STRIP_STYLE else 'out'

MIXER_BG = "#00080e"  # rgba(0,10,16,0.5) blended on #040e14

DARK_PALETTE = {
    'BG': '#040e14', 'BG2': '#1a1a1a', 'BG3': '#242424',
    'BORDER': '#2e2e2e', 'TEXT': '#e8e8e8', 'MUTED': '#666666',
    'GREEN': '#4ade80', 'GREEN2': '#166534',
    'RED': '#f87171', 'RED2': '#7f1d1d',
    'AMBER': '#fbbf24', 'AMBER2': '#78350f',
    'BLUE': '#60a5fa', 'BLUE2': '#1e3a5f',
    'DIM': '#404040',
    'PURPLE': '#a855f7', 'PURPLE2': '#3b0764',
}

def _apply_palette(palette):
    global BG, BG2, BG3, BORDER, TEXT, MUTED
    global GREEN, GREEN2, RED, RED2, AMBER, AMBER2, BLUE, BLUE2, DIM, PURPLE, PURPLE2
    BG     = palette['BG'];    BG2    = palette['BG2'];  BG3    = palette['BG3']
    BORDER = palette['BORDER']; TEXT  = palette['TEXT']; MUTED  = palette['MUTED']
    GREEN  = palette['GREEN']; GREEN2 = palette['GREEN2']
    RED    = palette['RED'];   RED2   = palette['RED2']
    AMBER  = palette['AMBER']; AMBER2 = palette['AMBER2']
    BLUE   = palette['BLUE'];  BLUE2  = palette['BLUE2']
    DIM    = palette['DIM']
    PURPLE  = palette.get('PURPLE', '#a855f7')
    PURPLE2 = palette.get('PURPLE2', '#3b0764')
    STATUS_COLORS[STATUS_IDLE]         = MUTED
    STATUS_COLORS[STATUS_ACTIVE]       = GREEN
    STATUS_COLORS[STATUS_ERROR]        = RED
    STATUS_COLORS[STATUS_RECONNECTING] = AMBER

STATUS_IDLE         = "idle"
STATUS_ACTIVE       = "active"
STATUS_ERROR        = "error"
STATUS_RECONNECTING = "reconnecting"

STATUS_COLORS = {
    STATUS_IDLE:         MUTED,
    STATUS_ACTIVE:       GREEN,
    STATUS_ERROR:        RED,
    STATUS_RECONNECTING: AMBER,
}

APP_DIR  = os.path.join(os.path.expanduser("~"), "Documents", "ShadowBridge")
LOG_DIR  = os.path.join(APP_DIR, "logs")
CFG_FILE = os.path.join(APP_DIR, "config.json")
os.makedirs(LOG_DIR, exist_ok=True)

def resource_path(relative):
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, relative)
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), relative)

class ABLogger:
    def __init__(self):
        self.ui_queue = queue.Queue()
        log_file = os.path.join(LOG_DIR, f"shadowbridge_{datetime.date.today()}.log")
        logging.basicConfig(
            filename=log_file, level=logging.DEBUG,
            format="%(asctime)s [%(levelname)s] %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )
        self.file_logger = logging.getLogger("shadowbridge")

    def info(self, msg):
        self.file_logger.info(msg)
        self.ui_queue.put(("normal", msg))

    def success(self, msg):
        self.file_logger.info(msg)
        self.ui_queue.put(("green", msg))

    def warning(self, msg):
        self.file_logger.warning(msg)
        self.ui_queue.put(("amber", msg))

    def error(self, msg):
        self.file_logger.error(msg)
        self.ui_queue.put(("red", msg))

logger = ABLogger()

# ── Customization presets ─────────────────────────────────────────────────────
PRESET_COLORS = [
    "#00d4e8", "#4ade80", "#f87171", "#fbbf24",
    "#a855f7", "#60a5fa", "#f472b6", "#34d399",
    "#fb923c", "#e879f9", "#38bdf8", "#a3e635",
    "#facc15", "#c084fc", "#f9a8d4", "#94a3b8",
]

PRESET_ICONS = [
    "🎵", "🎶", "🎙️", "🎚️", "🎛️", "🔊", "🔔", "💬",
    "🖥️", "🎮", "🎧", "📡", "🔗", "⚡", "🌐", "🎤",
    "📻", "🎼", "🎹", "🥁", "🎸", "🎺", "🎻", "🔉",
]


def _pil_to_b64(img) -> str:
    """Encode a PIL Image to a base64 PNG string for storage in channel config."""
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return "b64:" + base64.b64encode(buf.getvalue()).decode()


def _get_exe_friendly_name(exe_path: str) -> str | None:
    """Read FileDescription (or ProductName) from a Windows exe version resource."""
    try:
        size = ctypes.windll.version.GetFileVersionInfoSizeW(exe_path, None)
        if not size:
            return None
        buf = ctypes.create_string_buffer(size)
        if not ctypes.windll.version.GetFileVersionInfoW(exe_path, None, size, buf):
            return None
        p_trans = ctypes.c_void_p()
        n_trans = ctypes.c_uint()
        if (ctypes.windll.version.VerQueryValueW(
                buf, r'\VarFileInfo\Translation',
                ctypes.byref(p_trans), ctypes.byref(n_trans)) and n_trans.value >= 4):
            lang = ctypes.cast(p_trans, ctypes.POINTER(ctypes.c_ushort))
            cp = f"{lang[0]:04x}{lang[1]:04x}"
        else:
            cp = "040904b0"
        p_val = ctypes.c_void_p()
        n_val = ctypes.c_uint()
        for field in ('FileDescription', 'ProductName'):
            if (ctypes.windll.version.VerQueryValueW(
                    buf, f'\\StringFileInfo\\{cp}\\{field}',
                    ctypes.byref(p_val), ctypes.byref(n_val)) and n_val.value > 1):
                name = ctypes.wstring_at(p_val.value, n_val.value - 1).strip()
                if name:
                    return name
    except Exception:
        pass
    return None


def _extract_exe_icon_image(process_name: str, size: int = 34, exe_path: str = None):
    """Extract the icon from a process's executable as a PIL RGBA Image.
    Returns None on failure. Pass exe_path to skip the process lookup."""
    try:
        from PIL import Image as _PILImage
        proc_path = exe_path
        if not proc_path:
            for proc in psutil.process_iter(['name', 'exe']):
                try:
                    if proc.info['name'] and proc.info['name'].lower() == process_name.lower():
                        proc_path = proc.info['exe']
                        break
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
        if not proc_path or not os.path.exists(proc_path):
            return None

        SHGFI_ICON      = 0x000000100
        SHGFI_LARGEICON = 0x000000000
        SHGFI_SMALLICON = 0x000000001
        SHIL_EXTRALARGE = 0x00000002   # 48×48

        class SHFILEINFOW(ctypes.Structure):
            _fields_ = [
                ("hIcon",         ctypes.c_void_p),
                ("iIcon",         ctypes.c_int),
                ("dwAttributes",  ctypes.c_ulong),
                ("szDisplayName", ctypes.c_wchar * 260),
                ("szTypeName",    ctypes.c_wchar * 80),
            ]

        shell32 = ctypes.windll.shell32
        info = SHFILEINFOW()
        flags = SHGFI_ICON | SHGFI_LARGEICON
        res = shell32.SHGetFileInfoW(proc_path, 0, ctypes.byref(info),
                                     ctypes.sizeof(info), flags)
        if not res or not info.hIcon:
            return None

        # Convert HICON → PIL Image via ICONINFO + GetDIBits
        user32  = ctypes.windll.user32
        gdi32   = ctypes.windll.gdi32
        hdc     = user32.GetDC(None)

        class ICONINFO(ctypes.Structure):
            _fields_ = [
                ("fIcon",    ctypes.c_bool),
                ("xHotspot", ctypes.c_ulong),
                ("yHotspot", ctypes.c_ulong),
                ("hbmMask",  ctypes.c_void_p),
                ("hbmColor", ctypes.c_void_p),
            ]

        class BITMAPINFOHEADER(ctypes.Structure):
            _fields_ = [
                ("biSize",          ctypes.c_ulong),
                ("biWidth",         ctypes.c_long),
                ("biHeight",        ctypes.c_long),
                ("biPlanes",        ctypes.c_ushort),
                ("biBitCount",      ctypes.c_ushort),
                ("biCompression",   ctypes.c_ulong),
                ("biSizeImage",     ctypes.c_ulong),
                ("biXPelsPerMeter", ctypes.c_long),
                ("biYPelsPerMeter", ctypes.c_long),
                ("biClrUsed",       ctypes.c_ulong),
                ("biClrImportant",  ctypes.c_ulong),
            ]

        ii = ICONINFO()
        user32.GetIconInfo(info.hIcon, ctypes.byref(ii))

        bih = BITMAPINFOHEADER()
        bih.biSize = ctypes.sizeof(BITMAPINFOHEADER)
        gdi32.GetDIBits(hdc, ii.hbmColor, 0, 0, None, ctypes.byref(bih), 0)
        w, h = abs(bih.biWidth), abs(bih.biHeight)
        if w == 0 or h == 0:
            user32.ReleaseDC(None, hdc)
            user32.DestroyIcon(info.hIcon)
            return None

        bih.biBitCount   = 32
        bih.biCompression = 0
        bih.biHeight     = -h  # top-down DIB
        buf_size = w * h * 4
        buf = (ctypes.c_byte * buf_size)()
        gdi32.GetDIBits(hdc, ii.hbmColor, 0, h, buf, ctypes.byref(bih), 0)
        user32.ReleaseDC(None, hdc)
        user32.DestroyIcon(info.hIcon)
        if ii.hbmColor:  gdi32.DeleteObject(ii.hbmColor)
        if ii.hbmMask:   gdi32.DeleteObject(ii.hbmMask)

        # BGRA → RGBA
        raw   = bytes(buf)
        pixels = bytearray(buf_size)
        for i in range(0, buf_size, 4):
            pixels[i]   = raw[i+2]  # R
            pixels[i+1] = raw[i+1]  # G
            pixels[i+2] = raw[i]    # B
            pixels[i+3] = raw[i+3]  # A
        img = _PILImage.frombuffer("RGBA", (w, h), bytes(pixels), "raw", "RGBA", 0, 1)
        img = img.resize((size, size), _PILImage.LANCZOS)
        return img
    except Exception:
        return None

CRASH_LOG = os.path.join(APP_DIR, "crash.log")

def _write_crash_log(text):
    try:
        with open(CRASH_LOG, "a", encoding="utf-8") as f:
            f.write(text)
    except Exception:
        pass

def _excepthook(exc_type, exc_value, exc_tb):
    msg = "".join(traceback.format_exception(exc_type, exc_value, exc_tb))
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    logger.error(f"Unhandled exception:\n{msg}")
    _write_crash_log(f"\n[{timestamp}] UNHANDLED EXCEPTION:\n{msg}")
    sys.__excepthook__(exc_type, exc_value, exc_tb)

sys.excepthook = _excepthook

DEFAULT_GAMING_CHANNELS = [
    {"id": str(uuid.uuid4()), "name": "Game Audio",   "direction": "out", "device": "Game (Elgato Virtual Audio)",         "port": 5000, "enabled": True},
    {"id": str(uuid.uuid4()), "name": "Discord",      "direction": "out", "device": "Discord (Elgato Virtual Audio)",      "port": 5001, "enabled": True},
    {"id": str(uuid.uuid4()), "name": "Spotify",      "direction": "out", "device": "Spotify (Elgato Virtual Audio)",      "port": 5002, "enabled": True},
    {"id": str(uuid.uuid4()), "name": "Lumia Stream", "direction": "out", "device": "Lumia Stream (Elgato Virtual Audio)", "port": 5003, "enabled": True},
    {"id": str(uuid.uuid4()), "name": "OBS Alerts",   "direction": "in",  "device": "Headset Earphone (CORSAIR VOID ELITE Wireless Gaming Headset)", "port": 5011, "enabled": True},
]

DEFAULT_STREAMING_CHANNELS = [
    {"id": str(uuid.uuid4()), "name": "Game Audio",   "direction": "in",  "device": "Game (Elgato Virtual Audio)",       "port": 5000, "enabled": True},
    {"id": str(uuid.uuid4()), "name": "Discord",      "direction": "in",  "device": "VC Audio (Elgato Virtual Audio)",   "port": 5001, "enabled": True},
    {"id": str(uuid.uuid4()), "name": "Spotify",      "direction": "in",  "device": "Spotify (Elgato Virtual Audio)",    "port": 5002, "enabled": True},
    {"id": str(uuid.uuid4()), "name": "Lumia Stream", "direction": "in",  "device": "TTS (Elgato Virtual Audio)",        "port": 5003, "enabled": True},
    {"id": str(uuid.uuid4()), "name": "OBS Alerts",   "direction": "out", "device": "OBS Studio (Elgato Virtual Audio)", "port": 5011, "enabled": True},
]

def get_local_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except:
        return "unknown"

_RUN_KEY  = r"Software\Microsoft\Windows\CurrentVersion\Run"
_REG_NAME = "ShadowBridge"

def _startup_registered():
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, _RUN_KEY) as k:
            winreg.QueryValueEx(k, _REG_NAME)
            return True
    except FileNotFoundError:
        return False

def _set_startup(enable):
    if enable:
        exe = sys.executable if getattr(sys, 'frozen', False) else os.path.abspath(sys.argv[0])
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, _RUN_KEY, 0,
                            winreg.KEY_SET_VALUE) as k:
            winreg.SetValueEx(k, _REG_NAME, 0, winreg.REG_SZ, f'"{exe}"')
    else:
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, _RUN_KEY, 0,
                                winreg.KEY_SET_VALUE) as k:
                winreg.DeleteValue(k, _REG_NAME)
        except FileNotFoundError:
            pass


def load_config():
    try:
        with open(CFG_FILE, "r") as f:
            return json.load(f)
    except:
        return {}

def save_config(cfg):
    try:
        with open(CFG_FILE, "w") as f:
            json.dump(cfg, f, indent=2)
    except Exception as e:
        logger.error(f"Failed to save config: {e}")

def get_next_port(channels):
    used = {c['port'] for c in channels}
    port = 5000
    while port in used:
        port += 1
    return port

def get_loopback_devices(pa):
    devices = []
    seen = set()
    for i in range(pa.get_device_count()):
        info = pa.get_device_info_by_index(i)
        if '[Loopback]' in info['name']:
            name = info['name'].replace(' [Loopback]', '').strip()
            if name not in seen:
                seen.add(name)
                devices.append(name)   # full name — never truncate here
    return devices

def get_output_devices(pa):
    devices = []
    seen = set()
    for i in range(pa.get_device_count()):
        info = pa.get_device_info_by_index(i)
        if info['maxOutputChannels'] > 0 and '[Loopback]' not in info['name']:
            name = info['name']        # full name — never truncate here
            if name not in seen:
                seen.add(name)
                devices.append(name)
    return devices

def find_loopback(pa, name):
    for i in range(pa.get_device_count()):
        info = pa.get_device_info_by_index(i)
        if name in info['name'] and '[Loopback]' in info['name']:
            return i
    return None

def get_input_devices(pa):
    devices = []
    seen = set()
    for i in range(pa.get_device_count()):
        info = pa.get_device_info_by_index(i)
        if info['maxInputChannels'] > 0 and '[Loopback]' not in info['name']:
            name = info['name']
            if name not in seen:
                seen.add(name)
                devices.append(name)
    return devices

def get_app_audio_sources(pa):
    """Enumerate running applications currently producing audio.

    Uses pycaw AudioUtilities.GetAllSessions() — captures ALL processes with
    active audio sessions, including browser renderers (Opera, Chrome, Firefox).
    Falls back to pyaudiowpatch loopback device names when pycaw is unavailable.
    """
    sources = []
    seen = set()

    if PYCAW_AVAILABLE:
        try:
            sessions = AudioUtilities.GetAllSessions()
            for session in sessions:
                try:
                    # Resolve PID: prefer session.Process.pid, fall back to
                    # the raw COM interface so we catch renderer sub-processes
                    # (browsers route audio through a renderer, not the main exe).
                    pid = None
                    if session.Process is not None:
                        try:
                            pid = session.Process.pid
                        except Exception:
                            pass
                    if pid is None:
                        try:
                            pid = session._ctl.GetProcessId()
                        except Exception:
                            pass
                    if not pid:
                        continue

                    try:
                        ps = psutil.Process(pid)
                        proc_name = ps.name()
                        exe_path  = ps.exe()
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        continue

                    if not proc_name:
                        continue
                    key = proc_name.lower()
                    if key in seen:
                        continue
                    seen.add(key)

                    # Friendly display name from exe version resource
                    display_name = _get_exe_friendly_name(exe_path) if exe_path else None
                    if not display_name:
                        display_name = os.path.splitext(proc_name)[0]

                    sources.append({
                        'process_name': proc_name,
                        'display_name': display_name,
                        'exe_path':     exe_path,
                        'pid':          pid,
                    })
                except Exception:
                    continue
            return sources
        except Exception as e:
            logger.error(f"get_app_audio_sources (pycaw): {e}")

    # Fallback: enumerate pyaudiowpatch loopback device names
    try:
        for i in range(pa.get_device_count()):
            info = pa.get_device_info_by_index(i)
            if '[Loopback]' in info['name'] and info.get('maxInputChannels', 0) > 0:
                display = info['name'].replace(' [Loopback]', '').strip()
                if display not in seen:
                    seen.add(display)
                    sources.append({
                        'process_name': display,
                        'display_name': display,
                        'exe_path':     None,
                        'pid':          None,
                    })
    except Exception as e:
        logger.error(f"get_app_audio_sources (fallback): {e}")

    return sources

def find_input(pa, name):
    best = None
    for i in range(pa.get_device_count()):
        info = pa.get_device_info_by_index(i)
        if name in info['name'] and info['maxInputChannels'] > 0 and '[Loopback]' not in info['name']:
            if info['defaultSampleRate'] == 48000.0:
                return i
            if best is None:
                best = i
    return best

def find_output(pa, name):
    best = None
    for i in range(pa.get_device_count()):
        info = pa.get_device_info_by_index(i)
        if name in info['name'] and info['maxOutputChannels'] > 0 and '[Loopback]' not in info['name']:
            if info['defaultSampleRate'] == 48000.0:
                return i
            if best is None:
                best = i
    return best

def get_level(data):
    count = len(data) // 2
    if count == 0:
        return 0
    samples = struct.unpack(f"{count}h", data)
    return min(max(abs(s) for s in samples) / 32767.0, 1.0)


def _load_google_fonts():
    """Download Google Fonts TTFs once and register them with the Windows GDI so Tkinter can use them."""
    import urllib.request
    fonts_dir = os.path.join(APP_DIR, "fonts")
    os.makedirs(fonts_dir, exist_ok=True)
    font_specs = [
        ("Orbitron",        "Orbitron[wght].ttf",        "https://github.com/google/fonts/raw/main/ofl/orbitron/Orbitron%5Bwght%5D.ttf"),
        ("Share Tech Mono", "ShareTechMono-Regular.ttf",  "https://github.com/google/fonts/raw/main/ofl/sharetechmono/ShareTechMono-Regular.ttf"),
        ("Rajdhani",        "Rajdhani-Regular.ttf",        "https://github.com/google/fonts/raw/main/ofl/rajdhani/Rajdhani-Regular.ttf"),
    ]
    for family, fname, url in font_specs:
        fpath = os.path.join(fonts_dir, fname)
        try:
            if not os.path.exists(fpath):
                logger.info(f"Downloading font: {family}")
                urllib.request.urlretrieve(url, fpath)
            ctypes.windll.gdi32.AddFontResourceExW(fpath, 0x10, 0)
        except Exception as e:
            logger.warning(f"Font load failed ({family}): {e}")


class AudioEngine:
    def __init__(self, on_status_change, on_level):
        self.on_status_change = on_status_change
        self.on_level = on_level
        self.running = False
        self.pa = None
        self.streams = {}
        self.pa_streams = {}   # ch_id → live PortAudio stream handle
        self.statuses = {}
        self.stop_events = {}
        self.channel_map = {}
        self.dest_ip = ""
        self.mode = 'gaming'
        self.watchdog_thread = None
        self.sample_rate  = 48000
        self.buffer_size  = 1024

    def start(self, channels, dest_ip, mode='gaming', sample_rate=48000, buffer_size=1024):
        if self.running:
            return
        self.running = True
        self.dest_ip     = dest_ip
        self.mode        = mode
        self.sample_rate = sample_rate
        self.buffer_size = buffer_size
        self.pa = pyaudio.PyAudio()
        self.channel_map = {ch['id']: ch for ch in channels}
        logger.success(f"Audio engine starting — destination: {dest_ip}, mode: {mode}")
        for ch in channels:
            if ch['enabled']:
                self._start_channel(ch)
        self.watchdog_thread = threading.Thread(target=self._watchdog, daemon=True)
        self.watchdog_thread.start()

    def stop(self):
        if not self.running:
            return
        self.running = False
        # Step 1 — signal all stream threads to stop.
        for ev in self.stop_events.values():
            ev.set()
        # Step 2 — force-stop every live PA stream from this thread so that any
        # blocking stream.read() or stream.write() call in the worker thread
        # unblocks immediately.  This must happen BEFORE the joins below.
        for ch_id, pa_stream in list(self.pa_streams.items()):
            try:
                pa_stream.stop_stream()
            except Exception:
                logger.error(f"engine.stop(): force stop_stream({ch_id}) error:\n{traceback.format_exc()}")
        # Step 3 — join every stream thread.  Track whether they all exited;
        # pa.terminate() is only safe when no PA calls are still in flight.
        all_stopped = True
        for ch_id, t in list(self.streams.items()):
            t.join(timeout=5)
            if t.is_alive():
                logger.warning(f"engine.stop(): stream thread {ch_id} did not exit — skipping pa.terminate() to avoid segfault.")
                all_stopped = False
        self.streams.clear()
        self.stop_events.clear()
        self.pa_streams.clear()
        # Step 4 — join the watchdog.
        if self.watchdog_thread and self.watchdog_thread.is_alive():
            logger.info("engine.stop(): waiting for watchdog thread to exit...")
            self.watchdog_thread.join(timeout=8)
            if self.watchdog_thread.is_alive():
                logger.warning("engine.stop(): watchdog did not exit within timeout.")
        self.statuses.clear()
        self.channel_map.clear()
        # Step 5 — terminate PortAudio only when every thread exited cleanly.
        if self.pa:
            if all_stopped:
                time.sleep(0.1)  # drain any in-flight C-layer callbacks
                try:
                    self.pa.terminate()
                except Exception:
                    logger.error(f"engine.stop(): pa.terminate() error:\n{traceback.format_exc()}")
            else:
                logger.warning("engine.stop(): pa.terminate() skipped — thread(s) still alive.")
            self.pa = None
        logger.info("Audio engine stopped.")

    def _start_channel(self, ch):
        ev = threading.Event()
        self.stop_events[ch['id']] = ev
        self._set_status(ch['id'], STATUS_IDLE)
        t = threading.Thread(target=self._run_channel, args=(ch, ev), daemon=True)
        t.start()
        self.streams[ch['id']] = t

    def _set_status(self, ch_id, status):
        self.statuses[ch_id] = status
        self.on_status_change(ch_id, status)

    def _run_channel(self, ch, stop_ev):
        try:
            direction = ch['direction']
            ch_id, name, device, port = ch['id'], ch['name'], ch['device'], ch['port']
            # Guard: device must be a non-empty device name, never a UUID or the channel id
            if not device or _UUID_RE.match(device):
                logger.error(
                    f"Channel '{name}': device field is {'a UUID' if device else 'empty'} "
                    f"({device!r}) — device not configured. Skipping."
                )
                self._set_status(ch_id, STATUS_ERROR)
                return
            if direction == "out":
                self._stream_out(ch_id, name, device, port, stop_ev)
            elif direction == "app":
                self._stream_app(ch_id, name, ch.get('process', device), port, stop_ev)
            elif direction == "mic-in":
                # Capture from microphone input, send over network
                self._stream_mic(ch_id, name, device, port, stop_ev)
            elif direction == "mic-out":
                # Receive mic audio from network, play to output device
                self._stream_in(ch_id, name, device, port, stop_ev)
            elif direction == "mic":
                # Legacy: mode-dependent behaviour (kept for backward compat)
                if self.mode == 'streaming':
                    self._stream_mic(ch_id, name, device, port, stop_ev)
                else:
                    self._stream_in(ch_id, name, device, port, stop_ev)
            else:
                # "in" and anything unknown: receive from network → output device
                self._stream_in(ch_id, name, device, port, stop_ev)
        except Exception as e:
            logger.error(f"Channel '{ch['name']}' fatal error: {e}")
            self._set_status(ch['id'], STATUS_ERROR)

    def _stream_out(self, ch_id, name, device, port, stop_ev):
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            idx = find_loopback(self.pa, device)
            if idx is None:
                logger.error(f"'{name}': loopback not found for '{device}'")
                self._set_status(ch_id, STATUS_ERROR)
                return
            logger.success(f"'{name}': sending → {self.dest_ip}:{port}")
            self._set_status(ch_id, STATUS_ACTIVE)
            stream = self.pa.open(
                format=pyaudio.paInt16, channels=2, rate=self.sample_rate,
                input=True, input_device_index=idx, frames_per_buffer=self.buffer_size
            )
            self.pa_streams[ch_id] = stream
            while not stop_ev.is_set():
                data = stream.read(self.buffer_size, exception_on_overflow=False)
                data = _scale_volume(data, self.channel_map[ch_id].get('volume', 100))
                self.on_level(ch_id, get_level(data))
                sock.sendto(data, (self.dest_ip, port))
            self.pa_streams.pop(ch_id, None)
            stream.stop_stream()
            time.sleep(0.05)
            stream.close()
        except Exception as e:
            self.pa_streams.pop(ch_id, None)
            logger.error(f"'{name}' error: {e}")
            self._set_status(ch_id, STATUS_ERROR)
        finally:
            sock.close()
            self.on_level(ch_id, 0)

    def _stream_mic(self, ch_id, name, device, port, stop_ev):
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            idx = find_input(self.pa, device)
            if idx is None:
                logger.error(f"'{name}': input device not found for '{device}'")
                self._set_status(ch_id, STATUS_ERROR)
                return
            logger.success(f"'{name}': mic sending → {self.dest_ip}:{port}")
            self._set_status(ch_id, STATUS_ACTIVE)
            stream = self.pa.open(
                format=pyaudio.paInt16, channels=2, rate=self.sample_rate,
                input=True, input_device_index=idx, frames_per_buffer=self.buffer_size
            )
            self.pa_streams[ch_id] = stream
            while not stop_ev.is_set():
                data = stream.read(self.buffer_size, exception_on_overflow=False)
                data = _scale_volume(data, self.channel_map[ch_id].get('volume', 100))
                self.on_level(ch_id, get_level(data))
                sock.sendto(data, (self.dest_ip, port))
            self.pa_streams.pop(ch_id, None)
            stream.stop_stream()
            time.sleep(0.05)
            stream.close()
        except Exception as e:
            self.pa_streams.pop(ch_id, None)
            logger.error(f"'{name}' error: {e}")
            self._set_status(ch_id, STATUS_ERROR)
        finally:
            sock.close()
            self.on_level(ch_id, 0)

    def _stream_in(self, ch_id, name, device, port, stop_ev):
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.settimeout(1.0)
        try:
            sock.bind(("0.0.0.0", port))
            idx = find_output(self.pa, device)
            if idx is None:
                logger.error(f"'{name}': output not found for '{device}'")
                self._set_status(ch_id, STATUS_ERROR)
                return
            logger.success(f"'{name}': receiving ← port {port}")
            self._set_status(ch_id, STATUS_ACTIVE)
            stream = self.pa.open(
                format=pyaudio.paInt16, channels=2, rate=self.sample_rate,
                output=True, output_device_index=idx, frames_per_buffer=self.buffer_size
            )
            self.pa_streams[ch_id] = stream
            while not stop_ev.is_set():
                try:
                    data, _ = sock.recvfrom(65536)
                    if stop_ev.is_set():
                        break
                    data = _scale_volume(data, self.channel_map[ch_id].get('volume', 100))
                    self.on_level(ch_id, get_level(data))
                    stream.write(data)
                except socket.timeout:
                    continue
            self.pa_streams.pop(ch_id, None)
            stream.stop_stream()
            time.sleep(0.05)
            stream.close()
        except Exception as e:
            self.pa_streams.pop(ch_id, None)
            logger.error(f"'{name}' error: {e}")
            self._set_status(ch_id, STATUS_ERROR)
        finally:
            sock.close()
            self.on_level(ch_id, 0)

    def _stream_app(self, ch_id, name, process_name, port, stop_ev):
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            if not process_name:
                logger.error(f"'{name}': no process name configured")
                self._set_status(ch_id, STATUS_ERROR)
                return
            # Try to find a per-process loopback device by matching the process name
            # (pyaudiowpatch exposes these as devices whose name contains the exe name)
            proc_stem = os.path.splitext(process_name)[0].lower()
            idx = None
            for i in range(self.pa.get_device_count()):
                info = self.pa.get_device_info_by_index(i)
                dev_name = info['name']
                if info.get('maxInputChannels', 0) > 0 and '[Loopback]' in dev_name:
                    if proc_stem in dev_name.lower():
                        idx = i
                        break
            # Fall back to the generic find_loopback match (device name substring)
            if idx is None:
                idx = find_loopback(self.pa, process_name)
            if idx is None:
                logger.error(f"'{name}': process '{process_name}' not found — no matching loopback device")
                self._set_status(ch_id, STATUS_ERROR)
                return
            logger.success(f"'{name}': app loopback '{process_name}' → {self.dest_ip}:{port}")
            self._set_status(ch_id, STATUS_ACTIVE)
            stream = self.pa.open(
                format=pyaudio.paInt16, channels=2, rate=self.sample_rate,
                input=True, input_device_index=idx, frames_per_buffer=self.buffer_size
            )
            self.pa_streams[ch_id] = stream
            while not stop_ev.is_set():
                data = stream.read(self.buffer_size, exception_on_overflow=False)
                data = _scale_volume(data, self.channel_map[ch_id].get('volume', 100))
                self.on_level(ch_id, get_level(data))
                sock.sendto(data, (self.dest_ip, port))
            self.pa_streams.pop(ch_id, None)
            stream.stop_stream()
            time.sleep(0.05)
            stream.close()
        except Exception as e:
            self.pa_streams.pop(ch_id, None)
            logger.error(f"'{name}' app stream error: {e}")
            self._set_status(ch_id, STATUS_ERROR)
        finally:
            sock.close()
            self.on_level(ch_id, 0)

    def start_channel(self, ch):
        """Start a single channel while the engine is running (for TOGGLE_CHANNEL)."""
        if not self.running:
            return
        ch_id = ch['id']
        self.channel_map[ch_id] = ch
        if ch_id in self.streams and self.streams[ch_id].is_alive():
            return
        self._start_channel(ch)

    def stop_channel(self, ch_id):
        """Stop a single channel while the engine is running (for TOGGLE_CHANNEL)."""
        if ch_id in self.stop_events:
            self.stop_events[ch_id].set()
        if ch_id in self.pa_streams:
            try:
                self.pa_streams[ch_id].stop_stream()
            except Exception:
                pass
        self._set_status(ch_id, STATUS_IDLE)

    def _watchdog(self):
        logger.info("Watchdog active.")
        # Poll in 0.5 s ticks so stop() doesn't wait for a full sleep interval
        for _ in range(10):          # 10 × 0.5 s = 5 s between checks
            if not self.running:
                break
            time.sleep(0.5)
        while self.running:
            try:
                for ch_id, thread in list(self.streams.items()):
                    if not thread.is_alive() and self.running:
                        status = self.statuses.get(ch_id)
                        if status in (STATUS_ACTIVE, STATUS_RECONNECTING):
                            ch = self.channel_map.get(ch_id)
                            if ch:
                                logger.warning(f"'{ch['name']}' dropped — reconnecting in 3s...")
                                self._set_status(ch_id, STATUS_RECONNECTING)
                                # Wait in 0.5 s ticks so stop() can interrupt the delay
                                for _ in range(6):   # 6 × 0.5 s = 3 s
                                    if not self.running:
                                        break
                                    time.sleep(0.5)
                                if self.running:
                                    self._start_channel(ch)
                                    logger.success(f"'{ch['name']}' reconnected.")
            except Exception:
                # pa may have been terminated mid-reconnect; exit cleanly.
                logger.error(f"Watchdog caught exception (engine stopping):\n{traceback.format_exc()}")
                break
            # 5 s inter-check delay in 0.5 s ticks
            for _ in range(10):
                if not self.running:
                    break
                time.sleep(0.5)
        logger.info("Watchdog exited.")


class PeerDiscovery:
    ANNOUNCE_INTERVAL = 5.0
    PEER_TIMEOUT      = 15.0

    def __init__(self, get_announce_data, on_peer_found, on_peer_lost, on_port_sync,
                 on_command=None, discovery_port=47777, command_port=47778):
        self.get_announce_data = get_announce_data
        self.on_peer_found     = on_peer_found
        self.on_peer_lost      = on_peer_lost
        self.on_port_sync      = on_port_sync
        self.on_command        = on_command
        self.discovery_port    = int(discovery_port)
        self.command_port      = int(command_port)
        self._running          = False
        self._peer_last_seen   = 0.0
        self._peer_ip          = None
        self._peer_mode        = None
        self._lock             = threading.Lock()

    def start(self):
        if self._running:
            return
        with self._lock:
            self._peer_last_seen = 0.0
            self._peer_ip        = None
            self._peer_mode      = None
        self._running = True
        threading.Thread(target=self._listen_loop,    daemon=True).start()
        threading.Thread(target=self._cmd_listen_loop, daemon=True).start()
        threading.Thread(target=self._announce_loop,  daemon=True).start()
        threading.Thread(target=self._timeout_loop,   daemon=True).start()

    def stop(self):
        self._running = False

    def is_peer_connected(self):
        with self._lock:
            return self._peer_ip is not None

    def get_peer_info(self):
        with self._lock:
            return self._peer_ip, self._peer_mode

    def send_command(self, dest_ip, cmd):
        try:
            msg = json.dumps({'app': 'ShadowBridge', 'type': 'CMD', 'cmd': cmd})
            encoded = msg.encode()
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.sendto(encoded, (dest_ip, self.command_port))
            sock.close()
            logger.info(f"UDP TX CMD:{cmd} → {dest_ip}:{self.command_port} ({len(encoded)}b)")
        except Exception as e:
            logger.error(f"Failed to send {cmd} command: {e}")

    def _announce_loop(self):
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        while self._running:
            try:
                data = self.get_announce_data()
                data['type'] = 'ANNOUNCE'
                sock.sendto(json.dumps(data).encode(), ('255.255.255.255', self.discovery_port))
            except Exception as e:
                logger.error(f"Discovery announce: {e}")
            deadline = time.time() + self.ANNOUNCE_INTERVAL
            while self._running and time.time() < deadline:
                time.sleep(0.25)
        try:
            sock.close()
        except:
            pass

    def _listen_loop(self):
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.settimeout(1.0)
        try:
            sock.bind(('', self.discovery_port))
        except OSError as e:
            logger.error(f"Discovery: cannot bind port {self.discovery_port}: {e}")
            return
        local_ip = get_local_ip()
        logger.info(f"Discovery listener bound to 0.0.0.0:{self.discovery_port}, local_ip={local_ip}")
        while self._running:
            try:
                raw, addr = sock.recvfrom(4096)
                sender_ip = addr[0]
                if sender_ip == local_ip:
                    continue
                try:
                    msg = json.loads(raw.decode())
                except Exception:
                    continue
                if msg.get('app') != 'ShadowBridge':
                    continue  # silently ignore packets from other apps (e.g. old AudioBridge)
                logger.info(f"UDP RX {sender_ip}:{addr[1]} → {len(raw)}b: {raw[:120]}")
                msg_type = msg.get('type')
                if msg_type not in ('ANNOUNCE', 'ACK'):
                    continue
                self._handle_message(msg, sender_ip)
            except socket.timeout:
                continue
            except Exception:
                pass
        try:
            sock.close()
        except:
            pass

    def _cmd_listen_loop(self):
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.settimeout(1.0)
        try:
            sock.bind(('', self.command_port))
        except OSError as e:
            logger.error(f"Discovery: cannot bind command port {self.command_port}: {e}")
            return
        local_ip = get_local_ip()
        logger.info(f"Command listener bound to 0.0.0.0:{self.command_port}, local_ip={local_ip}")
        while self._running:
            try:
                raw, addr = sock.recvfrom(4096)
                sender_ip = addr[0]
                if sender_ip == local_ip:
                    continue
                try:
                    msg = json.loads(raw.decode())
                except Exception:
                    continue
                if msg.get('app') != 'ShadowBridge':
                    continue
                logger.info(f"UDP CMD RX {sender_ip}:{addr[1]} → {len(raw)}b: {raw[:120]}")
                if msg.get('type') == 'CMD' and self._running and self.on_command and msg.get('cmd'):
                    self.on_command(msg['cmd'], sender_ip)
            except socket.timeout:
                continue
            except Exception:
                pass
        try:
            sock.close()
        except:
            pass

    def _handle_message(self, msg, sender_ip):
        peer_mode = msg.get('mode')
        channels  = msg.get('channels', [])
        fire_found = False
        with self._lock:
            fire_found           = (self._peer_ip is None)
            self._peer_last_seen = time.time()
            self._peer_ip        = sender_ip
            self._peer_mode      = peer_mode
        if fire_found:
            self.on_peer_found(sender_ip, peer_mode)
        if channels:
            self.on_port_sync(channels)
        if msg.get('type') == 'ANNOUNCE':
            self._send_ack(sender_ip)

    def _send_ack(self, dest_ip):
        try:
            data = self.get_announce_data()
            data['type'] = 'ACK'
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.sendto(json.dumps(data).encode(), (dest_ip, self.discovery_port))
            sock.close()
        except:
            pass

    def _timeout_loop(self):
        while self._running:
            for _ in range(4):          # 4 × 0.5 s = 2 s poll cycle
                time.sleep(0.5)
                if not self._running:
                    return
            if not self._running:
                return
            fire_lost = False
            with self._lock:
                if self._peer_ip is not None:
                    if time.time() - self._peer_last_seen > self.PEER_TIMEOUT:
                        self._peer_ip   = None
                        self._peer_mode = None
                        fire_lost = True
            if fire_lost and self._running:  # don't fire after stop
                self.on_peer_lost()


class WsServer:
    PORT = 8765

    def __init__(self, app):
        self._app            = app
        self._loop           = None
        self._clients        = set()
        self._cached_status  = None   # JSON string, always built on the main thread

    def start(self):
        threading.Thread(target=self._run_loop, daemon=True).start()

    def _run_loop(self):
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)
        self._loop.run_until_complete(self._serve())

    async def _serve(self):
        try:
            async with websockets.serve(self._handler, "localhost", self.PORT):
                logger.success(f"WS API: ws://localhost:{self.PORT}")
                await asyncio.Future()
        except Exception as e:
            logger.error(f"WsServer: {e}")

    async def _handler(self, ws):
        self._clients.add(ws)
        try:
            if self._cached_status:
                await ws.send("STATUS " + self._cached_status)
            else:
                self._app.root.after(0, self.push_status)
            async for msg in ws:
                self._dispatch(msg.strip())
        except Exception:
            pass
        finally:
            self._clients.discard(ws)

    def _dispatch(self, msg):
        if msg == "START":
            self._app.root.after(0, self._app._start)
        elif msg == "STOP":
            self._app.root.after(0, self._app._stop)
        elif msg.startswith("TOGGLE_CHANNEL "):
            ch_id = msg[len("TOGGLE_CHANNEL "):]
            self._app.root.after(0, lambda cid=ch_id: self._app._toggle_channel(cid))
        elif msg.startswith("SET_VOLUME "):
            parts = msg.split()
            logger.info(f"WS RX: {msg!r}")
            if len(parts) == 3:
                try:
                    vol = max(0, min(100, int(parts[2])))
                    ch_id = parts[1]
                    logger.info(f"SET_VOLUME dispatching: id={ch_id} vol={vol}")
                    self._app.root.after(0, lambda cid=ch_id, v=vol: self._app._set_volume(cid, v))
                except ValueError:
                    logger.warning(f"SET_VOLUME: bad volume value in {msg!r}")
            else:
                logger.warning(f"SET_VOLUME: malformed message {msg!r}")

    def _build_status(self, full=False):
        """Build the STATUS payload.

        full=False (default, periodic push): omits icon/icon_b64 to keep
        the 250 ms broadcast small (~200 bytes vs ~7 KB with icons).
        full=True (config-change push): includes icon and icon_b64.
        """
        channels = []
        for ch in self._app._channels():
            ch_id = ch['id']
            row   = self._app.rows.get(ch_id)
            direction = ch.get('direction', 'out')
            # 'mic' is a legacy alias — normalise to 'mic-in' for the plugin
            if direction == 'mic':
                direction = 'mic-in'
            meta = _DIR_META.get(direction, _DIR_META['out'])
            entry = {
                "id":        ch_id,
                "name":      ch['name'],
                "enabled":   ch.get('enabled', True),
                "volume":    ch.get('volume', 100),
                "level":     round(row.smooth_level, 3) if row else 0.0,
                "status":    self._app.engine.statuses.get(ch_id, STATUS_IDLE),
                "color":     ch.get('color') or meta[1],
                "direction": direction,
            }
            if full:
                raw_icon = ch.get('icon')
                is_b64   = bool(raw_icon and isinstance(raw_icon, str) and raw_icon.startswith('b64:'))
                entry["icon"] = meta[3] if is_b64 else (raw_icon or meta[3])
                if is_b64:
                    entry["icon_b64"] = raw_icon[4:]   # base64 PNG bytes, no "b64:" prefix
            channels.append(entry)
        return {
            "running":        self._app.engine.running,
            "peer_connected": self._app._discovery.is_peer_connected(),
            "channels":       channels,
        }

    def push_status(self):
        """Compact push — level/volume/status only, no icon data. Called every 250 ms."""
        payload = json.dumps(self._build_status(full=False))
        self._cached_status = payload
        if self._loop is None or not self._clients:
            return
        asyncio.run_coroutine_threadsafe(
            self._broadcast("STATUS " + payload), self._loop
        )

    def push_status_full(self):
        """Full push — includes icon/icon_b64. Called on config changes."""
        payload = json.dumps(self._build_status(full=True))
        self._cached_status = payload          # new clients get the full picture
        if self._loop is None or not self._clients:
            return
        asyncio.run_coroutine_threadsafe(
            self._broadcast("STATUS " + payload), self._loop
        )

    async def _broadcast(self, msg):
        dead = set()
        for ws in list(self._clients):
            try:
                await ws.send(msg)
            except Exception:
                dead.add(ws)
        self._clients -= dead


class ChannelRow(tk.Frame):
    """Vertical mixer-style channel strip (80px wide)."""

    def __init__(self, parent, channel, loopback_devices, output_devices,
                 on_remove, on_change, on_refresh=None, mode='gaming', **kwargs):
        style_key  = _channel_style_key(channel)
        style      = _STRIP_STYLE.get(style_key, _STRIP_STYLE['out'])
        self._strip_bg     = channel.get('_bg')     or style['bg']
        self._strip_fg     = channel.get('color')   or style['fg']
        self._badge_bg     = channel.get('_bbg')    or style['badge_bg']
        self._strip_border = channel.get('_border') or style['border']
        super().__init__(parent, bg=self._strip_bg,
                         highlightbackground=self._strip_border, highlightthickness=1,
                         width=STRIP_W, **kwargs)
        self.channel      = channel
        self.on_remove    = on_remove
        self.on_change    = on_change
        self.on_refresh   = on_refresh
        self.mode         = mode
        self.level_queue  = queue.Queue(maxsize=10)
        self.smooth_level = 0.0
        self.vol_var      = tk.IntVar(value=self.channel.get('volume', 100))
        self.device_btn   = _NoOp()
        self._build(loopback_devices, output_devices)

    def _dmeta(self):
        return _DIR_META.get(self.channel.get('direction', 'out'), _DIR_META['out'])

    def _build(self, loopback_devices, output_devices):
        sbg  = self._strip_bg
        sfg  = self._strip_fg
        bbg  = self._badge_bg
        _, _, dir_text, dir_icon = self._dmeta()
        accent_col = self.channel.get('color', sfg)

        # ── Pack order: bottom anchors first, then fader (expand), then top ─────
        # tkinter allocates BOTTOM/TOP space first; expand=True element gets rest.

        # ── 3px accent bar — very top ─────────────────────────────────────────
        self._accent = tk.Frame(self, height=3, bg=accent_col)
        self._accent.pack(side="top", fill="x")
        self._accent.bind("<Button-1>", self._open_color_picker)

        # ── BOTTOM anchors (packed first = closest to bottom of strip) ────────

        # Source button — absolute bottom
        self._src_cv = tk.Canvas(self, width=STRIP_W, height=20,
                                  bg=sbg, highlightthickness=0, cursor="hand2")
        self._src_cv.pack(side="bottom", fill="x", padx=4, pady=(0, 6))
        self._src_bg  = self._src_cv.create_polygon([0, 0], fill=MIXER_BG, outline="", width=1)
        self._src_txt = self._src_cv.create_text(0, 0, text="",
                                                  fill="#00d4e8", font=(FONT_MONO, 8))
        self._src_cv.bind("<Button-1>",  lambda e: self._open_source_popup())
        self._src_cv.bind("<Configure>", lambda e: self._draw_src_btn())
        self._src_cv.after(70, self._draw_src_btn)

        # Info + Delete buttons
        self._br = br = tk.Frame(self, bg=sbg)
        br.pack(side="bottom", fill="x", padx=4, pady=(0, 3))
        tk.Button(br, text="ⓘ",
                  font=(FONT_MONO, 9),
                  bg="#1e3a5f", fg="#60a5fa",
                  relief="flat", bd=0, cursor="hand2",
                  highlightthickness=1, highlightbackground="#2a5a8f",
                  activebackground="#1e3a5f", activeforeground=TEXT,
                  height=1, command=self._open_info_popup
                  ).pack(side="left", expand=True, fill="x", padx=(0, 2))
        tk.Button(br, text="✕",
                  font=(FONT_MONO, 9),
                  bg="#3f0f0f", fg="#f87171",
                  relief="flat", bd=0, cursor="hand2",
                  highlightthickness=1, highlightbackground="#7f1d1d",
                  activebackground="#3f0f0f", activeforeground="#f87171",
                  height=1, command=lambda: self.on_remove(self.channel['id'])
                  ).pack(side="left", expand=True, fill="x")

        # ON/OFF toggle
        self._en_cv = tk.Canvas(self, width=STRIP_W, height=22,
                                bg=sbg, highlightthickness=0, cursor="hand2")
        self._en_cv.pack(side="bottom", fill="x", padx=4, pady=(0, 3))
        self._en_bg  = self._en_cv.create_polygon([0, 0], fill=GREEN2, outline="", width=0)
        self._en_txt = self._en_cv.create_text(
            0, 0, text="ON", fill=GREEN, font=(FONT_RAJDHANI, 9, "bold"))
        self._en_cv.bind("<Button-1>",  lambda e: self._toggle_enable())
        self._en_cv.bind("<Configure>", lambda e: self._draw_en_btn())
        self._en_cv.after(60, self._draw_en_btn)

        # Status row
        self._sr = sr = tk.Frame(self, bg=sbg)
        sr.pack(side="bottom", fill="x", padx=5, pady=(0, 2))
        self._dot_cv   = tk.Canvas(sr, width=6, height=6, bg=sbg, highlightthickness=0)
        self._dot_cv.pack(side="left", padx=(0, 2))
        self._dot_item = self._dot_cv.create_oval(0, 0, 6, 6, fill=MUTED, outline="")
        self.status_label = tk.Label(
            sr, text="idle", font=(FONT_MONO, 8), bg=sbg, fg="#555555")
        self.status_label.pack(side="left")

        # Volume % label
        self._vol_pct_lbl = tk.Label(
            self, text=f"{self.channel.get('volume', 100)}%",
            font=(FONT_MONO, 9), bg=sbg, fg="#666666", anchor="center")
        self._vol_pct_lbl.pack(side="bottom", fill="x", pady=(0, 2))

        # ── TOP elements below accent ──────────────────────────────────────────

        # Icon badge
        self._badge_cv = tk.Canvas(self, width=34, height=34, bg=sbg,
                                   highlightthickness=0, cursor="hand2")
        self._badge_cv.pack(side="top", pady=(8, 2))
        rr = [8,0, 26,0, 34,8, 34,26, 26,34, 8,34, 0,26, 0,8]
        self._badge_oval = self._badge_cv.create_polygon(rr, fill=bbg, outline="")
        icon_val = self.channel.get('icon') or dir_icon
        self._badge_txt = self._badge_cv.create_text(
            17, 17, text=icon_val, fill=TEXT,
            font=("Segoe UI Emoji", 15))
        self._badge_cv.bind("<Button-1>", self._open_icon_picker)
        if self.channel.get('icon', '').startswith('b64:'):
            self._render_badge_icon()

        # Channel name
        name = self.channel.get('name', '')
        disp = (name[:8] + '…') if len(name) > 8 else name
        self._name_lbl = tk.Label(
            self, text=disp,
            font=(FONT_RAJDHANI, 11, "bold"),
            bg=sbg, fg="#e8e8e8",
            anchor="center", justify="center")
        self._name_lbl.pack(side="top", fill="x", padx=5, pady=(0, 2))

        # Direction badge
        ds = _DIR_BADGE_STYLE.get(_channel_style_key(self.channel), _DIR_BADGE_STYLE['out'])
        self.dir_btn = tk.Button(
            self, text=ds['text'],
            font=(FONT_MONO, 7),
            bg=ds['bg'], fg=ds['fg'],
            relief="flat", bd=0, cursor="hand2",
            activebackground=ds['bg'], activeforeground=ds['fg'],
            padx=6, pady=2,
            command=self._open_direction_popup)
        self.dir_btn.pack(side="top", pady=(0, 4))

        # ── Fader canvas — expands to fill remaining middle space ─────────────
        #  Configure binding keeps _tt/_tb in sync with actual rendered height.
        self._fc = tk.Canvas(self, width=STRIP_W, height=80,
                             bg=sbg, highlightthickness=0)
        self._fc.pack(side="top", fill="both", expand=True)

        self._tx  = 20   # fader track center x
        self._tt  = 8    # fader track top y    (updated in _on_fc_resize)
        self._tb  = 70   # fader track bottom y (updated in _on_fc_resize)
        self._hw  = 20   # handle width
        self._hh  = 8    # handle height
        self._mx1 = 52   # meter left edge x
        self._mx2 = 60   # meter right edge x

        self._fc.create_line(self._tx, self._tt, self._tx, self._tb,
                              fill="#1e1e1e", width=3, capstyle="round",
                              tags="ftrack")
        self._fader_fill = self._fc.create_rectangle(
            self._tx - 1, self._tb, self._tx + 1, self._tb,
            fill=sfg, outline="")
        self._handle = self._fc.create_rectangle(
            0, 0, 1, 1, fill=TEXT, outline="", tags="handle")
        self._bars = [
            self._fc.create_rectangle(0, 0, 1, 1, fill="#2a2a2a", outline="")
            for _ in range(N_BARS)
        ]

        self._fc.bind("<Button-1>",  self._fader_click)
        self._fc.bind("<B1-Motion>", self._fader_drag)
        # Configure fires when tkinter gives the canvas its actual height
        self._fc.bind("<Configure>", self._on_fc_resize)

        self._apply_enable_state()
        self.after(80, lambda: self._bind_right_click(self))

    # ── Fader canvas resize: sync track bounds then redraw ───────────────────
    def _on_fc_resize(self, event):
        h = event.height
        if h < 20:
            return
        self._tt = 8
        self._tb = max(self._tt + 60, h - 10)  # min 60px fader travel
        self._fc.coords("ftrack", self._tx, self._tt, self._tx, self._tb)
        self._redraw_fader()
        self._redraw_meter()

    # ── ON/OFF angled button ──────────────────────────────────────────────────
    def _draw_en_btn(self):
        c = self._en_cv
        w, h = c.winfo_width(), c.winfo_height()
        if w < 4 or h < 4:
            return
        cut = 4
        pts = [cut, 0,  w, 0,  w - cut, h,  0, h]
        enabled = self.channel.get('enabled', True)
        if enabled:
            # Use custom color for ON bg/fg when a color has been picked
            if self.channel.get('color'):
                bg = self._strip_border
                fg = self._strip_fg
            else:
                bg = "#166534"
                fg = "#4ade80"
        else:
            bg = "#222222"
            fg = "#555555"
        txt = "ON" if enabled else "OFF"
        c.coords(self._en_bg, *pts)
        c.itemconfig(self._en_bg,  fill=bg, outline="")
        c.coords(self._en_txt, w // 2, h // 2)
        c.itemconfig(self._en_txt, text=txt, fill=fg,
                     font=(FONT_RAJDHANI, 9, "bold"))

    # ── Source button (angled, cyan border) ───────────────────────────────────
    def _draw_src_btn(self):
        c = self._src_cv
        w, h = c.winfo_width(), c.winfo_height()
        if w < 4 or h < 4:
            return
        cut = 4
        pts = [cut, 0,  w, 0,  w - cut, h,  0, h]
        c.coords(self._src_bg, *pts)
        c.itemconfig(self._src_bg, fill=MIXER_BG, outline="#00d4e8")
        direction = self.channel.get('direction', 'out')
        device    = (self.channel.get('device') or self.channel.get('process') or '').strip()
        if direction in ('out', 'mic-in', 'mic'):
            placeholder = 'Select Source'
        elif direction in ('in', 'mic-out'):
            placeholder = 'Select Output'
        elif direction == 'app':
            placeholder = 'Select App'
        else:
            placeholder = 'Select Source'
        label = (device[:10] + '…') if len(device) > 10 else (device or placeholder)
        c.coords(self._src_txt, w // 2, h // 2)
        c.itemconfig(self._src_txt, text=label, fill="#00d4e8", font=(FONT_MONO, 8))

    # ── Fader ─────────────────────────────────────────────────────────────────
    def _redraw_fader(self):
        vol  = self.vol_var.get()
        span = self._tb - self._tt
        hy   = self._tb - (vol / 100.0) * span
        hw   = self._hw // 2
        hh   = self._hh // 2
        self._fc.coords(self._handle,
                         self._tx - hw, hy - hh,
                         self._tx + hw, hy + hh)
        self._fc.coords(self._fader_fill,
                         self._tx - 1, hy,
                         self._tx + 1, self._tb)

    def _fader_click(self, event): self._fader_set_y(event.y)
    def _fader_drag(self,  event): self._fader_set_y(event.y)

    def _fader_set_y(self, y):
        span = self._tb - self._tt
        vol  = max(0, min(100, int((self._tb - y) / span * 100)))
        self.vol_var.set(vol)
        self._on_volume_change(vol)

    # ── Level meter ───────────────────────────────────────────────────────────
    def _redraw_meter(self):
        level = math.sqrt(max(0.0, min(1.0, self.smooth_level)))
        span = self._tb - self._tt
        slot = span / N_BARS
        bh  = max(2, int(slot * 5 / 7))
        gap = max(1, int(slot * 2 / 7))
        for i, bid in enumerate(self._bars):
            bot = self._tb - i * (bh + gap)
            top = bot - bh
            self._fc.coords(bid, self._mx1, top, self._mx2, bot)
            frac = (i + 1) / N_BARS
            if frac <= level:
                color = (RED   if i >= int(N_BARS * 0.85)
                         else AMBER if i >= int(N_BARS * 0.60)
                         else self._strip_fg)
            else:
                color = "#2a2a2a"
            self._fc.itemconfig(bid, fill=color)

    # ── Enable / disable ──────────────────────────────────────────────────────
    def _toggle_enable(self):
        self.channel['enabled'] = not self.channel.get('enabled', True)
        self._apply_enable_state()
        self.on_change()

    def _apply_enable_state(self):
        enabled = self.channel.get('enabled', True)
        self.configure(highlightbackground=self._strip_border if enabled else "#2a2a2a")
        self._name_lbl.config(fg=TEXT if enabled else DIM)
        self._vol_pct_lbl.config(fg="#666666" if enabled else DIM)
        self.status_label.config(fg="#555555" if enabled else DIM)
        self._draw_en_btn()

    def _on_volume_change(self, val):
        v = int(float(val))
        self.channel['volume'] = v
        self._vol_pct_lbl.config(text=f"{v}%")
        self._redraw_fader()
        self.on_change()

    def set_volume(self, vol: int) -> None:
        self.channel['volume'] = vol
        self.vol_var.set(vol)
        self._vol_pct_lbl.config(text=f"{vol}%")
        self._redraw_fader()
        self._fc.update_idletasks()

    # ── Color picker / channel color ──────────────────────────────────────────
    def _apply_channel_color(self, color: str):
        self.channel['color'] = color
        r = int(color[1:3], 16)
        g = int(color[3:5], 16)
        b = int(color[5:7], 16)
        sbg  = f"#{max(0,r//6):02x}{max(0,g//6):02x}{max(0,b//6):02x}"
        sbdr = f"#{min(255,r//3):02x}{min(255,g//3):02x}{min(255,b//3):02x}"
        bbg  = f"#{min(255,r//2):02x}{min(255,g//2):02x}{min(255,b//2):02x}"
        self._strip_bg     = sbg
        self._strip_fg     = color
        self._badge_bg     = bbg
        self._strip_border = sbdr
        # Persist derived values so _build() restores them correctly on rebuild
        self.channel['_bg']     = sbg
        self.channel['_border'] = sbdr
        self._accent.config(bg=color)
        self.configure(bg=sbg, highlightbackground=sbdr)
        self._badge_cv.configure(bg=sbg)
        # Badge oval and badge text are NOT recolored — icon stays as-is
        self._fc.configure(bg=sbg)
        self._fc.itemconfig(self._fader_fill, fill=color)
        self._redraw_meter()
        # Direction badge keeps its standard direction color — not recolored
        self._name_lbl.config(bg=sbg)
        self._vol_pct_lbl.config(bg=sbg)
        self._sr.config(bg=sbg)
        self._dot_cv.configure(bg=sbg)
        self.status_label.config(bg=sbg)
        self._en_cv.configure(bg=sbg)
        self._draw_en_btn()
        self._src_cv.configure(bg=sbg)
        self._draw_src_btn()
        self._br.config(bg=sbg)
        self.on_change()

    def _apply_pil_icon(self, img):
        b64 = _pil_to_b64(img)
        self.channel['icon'] = b64
        self._render_badge_icon()
        self.on_change()

    def _render_badge_icon(self):
        icon_val = self.channel.get('icon')
        if not icon_val:
            return
        if icon_val.startswith("b64:"):
            try:
                from PIL import Image as _PILImage
                data = base64.b64decode(icon_val[4:])
                img  = _PILImage.open(io.BytesIO(data)).convert("RGBA").resize((28, 28))
                self._badge_photo = PILImageTk.PhotoImage(img) if PILImageTk else None
                if self._badge_photo:
                    self._badge_cv.delete(self._badge_txt)
                    self._badge_txt = self._badge_cv.create_image(17, 17, image=self._badge_photo)
            except Exception:
                pass
        else:
            self._badge_cv.itemconfig(self._badge_txt, text=icon_val,
                                      font=("Segoe UI Emoji", 15))

    # ── Color picker popup ────────────────────────────────────────────────────
    def _open_color_picker(self, event=None):
        CYAN = "#00d4e8"
        popup = tk.Toplevel(self)
        popup.title("Choose Color")
        popup.geometry("300x280")
        popup.configure(bg=BG)
        popup.resizable(False, False)
        popup.grab_set()

        tk.Label(popup, text="CHANNEL COLOR", font=(FONT_MONO, 10, "bold"),
                 bg=BG, fg=CYAN).pack(anchor="w", padx=14, pady=(14, 2))
        tk.Frame(popup, height=1, bg=CYAN_DIM).pack(fill="x", padx=14, pady=(0, 10))

        # Preset grid
        grid = tk.Frame(popup, bg=BG)
        grid.pack(padx=14)
        for i, c in enumerate(PRESET_COLORS):
            row, col = divmod(i, 8)
            swatch = tk.Canvas(grid, width=24, height=24, bg=c,
                               highlightthickness=1, highlightbackground=BG3,
                               cursor="hand2")
            swatch.grid(row=row, column=col, padx=2, pady=2)
            swatch.bind("<Button-1>", lambda e, clr=c: _pick(clr))

        # Hex entry + preview
        hex_row = tk.Frame(popup, bg=BG)
        hex_row.pack(fill="x", padx=14, pady=(10, 6))
        tk.Label(hex_row, text="#", font=(FONT_MONO, 10), bg=BG, fg=MUTED).pack(side="left")
        hex_var = tk.StringVar(value=self.channel.get('color', CYAN).lstrip('#'))
        hex_entry = tk.Entry(hex_row, textvariable=hex_var, width=8,
                             font=(FONT_MONO, 10), bg=BG2, fg=TEXT,
                             insertbackground=TEXT, relief="flat",
                             highlightthickness=1, highlightbackground=BORDER)
        hex_entry.pack(side="left", padx=(2, 8))
        preview = tk.Canvas(hex_row, width=28, height=22, highlightthickness=0)
        preview.pack(side="left")
        preview_rect = preview.create_rectangle(0, 0, 28, 22,
                                                fill=self.channel.get('color', CYAN), outline="")

        def _update_preview(*_):
            val = hex_var.get().strip().lstrip('#')
            if len(val) == 6:
                try:
                    preview.itemconfig(preview_rect, fill=f"#{val}")
                except tk.TclError:
                    pass
        hex_var.trace_add("write", _update_preview)

        # OS color dialog button
        def _os_picker():
            result = colorchooser.askcolor(
                color=f"#{hex_var.get().lstrip('#')}",
                title="Pick a color", parent=popup)
            if result and result[1]:
                hex_var.set(result[1].lstrip('#'))
                _update_preview()
        tk.Button(hex_row, text="…", font=(FONT_MONO, 9), bg=BG3, fg=MUTED,
                  relief="flat", bd=0, cursor="hand2",
                  command=_os_picker, padx=4).pack(side="left")

        def _pick(clr):
            self._apply_channel_color(clr)
            popup.destroy()

        def _confirm():
            val = "#" + hex_var.get().strip().lstrip('#')
            try:
                self.winfo_rgb(val)   # validates the color
                _pick(val)
            except tk.TclError:
                pass

        bf = tk.Frame(popup, bg=BG)
        bf.pack(fill="x", padx=14, pady=(4, 14))
        tk.Button(bf, text="APPLY", font=(FONT_MONO, 9, "bold"),
                  bg=CYAN_DIM, fg=CYAN, relief="flat", bd=0,
                  cursor="hand2", command=_confirm,
                  padx=8, pady=5).pack(side="left", expand=True, fill="x", padx=(0, 4))
        tk.Button(bf, text="CANCEL", font=(FONT_MONO, 9),
                  bg=BG3, fg=MUTED, relief="flat", bd=0,
                  cursor="hand2", command=popup.destroy,
                  padx=8, pady=5).pack(side="left")

    # ── Icon selector popup ───────────────────────────────────────────────────
    def _open_icon_picker(self, event=None):
        CYAN = "#00d4e8"
        popup = tk.Toplevel(self)
        popup.title("Choose Icon")
        popup.geometry("320x320")
        popup.configure(bg=BG)
        popup.resizable(False, False)
        popup.grab_set()

        tk.Label(popup, text="CHANNEL ICON", font=(FONT_MONO, 10, "bold"),
                 bg=BG, fg=CYAN).pack(anchor="w", padx=14, pady=(14, 2))
        tk.Frame(popup, height=1, bg=CYAN_DIM).pack(fill="x", padx=14, pady=(0, 8))

        tab_row = tk.Frame(popup, bg=BG)
        tab_row.pack(fill="x", padx=14, pady=(0, 6))
        body = tk.Frame(popup, bg=BG)
        body.pack(fill="both", expand=True, padx=14)

        preset_frame = tk.Frame(body, bg=BG)
        custom_frame = tk.Frame(body, bg=BG)

        def _show_preset():
            custom_frame.pack_forget()
            preset_frame.pack(fill="both", expand=True)
            tab_preset.config(bg=BG3, fg=TEXT)
            tab_custom.config(bg=BG2, fg=MUTED)

        def _show_custom():
            preset_frame.pack_forget()
            custom_frame.pack(fill="both", expand=True)
            tab_custom.config(bg=BG3, fg=TEXT)
            tab_preset.config(bg=BG2, fg=MUTED)

        tab_preset = tk.Button(tab_row, text="PRESET ICONS", font=(FONT_MONO, 8, "bold"),
                               bg=BG3, fg=TEXT, relief="flat", bd=0, padx=8, pady=3,
                               cursor="hand2", command=_show_preset)
        tab_preset.pack(side="left", padx=(0, 2))
        tab_custom = tk.Button(tab_row, text="CUSTOM ICON", font=(FONT_MONO, 8, "bold"),
                               bg=BG2, fg=MUTED, relief="flat", bd=0, padx=8, pady=3,
                               cursor="hand2", command=_show_custom)
        tab_custom.pack(side="left")

        # Preset grid — dark teal cells matching HUD theme
        _IC_BG      = "#002432"   # dark teal panel
        _IC_BG_HOV  = "#003d52"   # hover tint
        _IC_BORDER  = "#003a48"   # dim cyan cell border
        _IC_SEL_BD  = "#00d4e8"   # bright cyan for hover border

        for i, emoji in enumerate(PRESET_ICONS):
            row, col = divmod(i, 8)
            lbl = tk.Label(preset_frame, text=emoji, font=("Segoe UI Emoji", 14),
                           bg=_IC_BG, fg="#00d4e8", cursor="hand2", width=2,
                           highlightthickness=1, highlightbackground=_IC_BORDER)
            lbl.grid(row=row, column=col, padx=2, pady=2)
            lbl.bind("<Button-1>", lambda e, em=emoji, p=popup: self._pick_emoji(em, p))
            lbl.bind("<Enter>",    lambda e, w=lbl: w.config(bg=_IC_BG_HOV,
                                                              highlightbackground=_IC_SEL_BD))
            lbl.bind("<Leave>",    lambda e, w=lbl: w.config(bg=_IC_BG,
                                                              highlightbackground=_IC_BORDER))

        # Custom tab
        tk.Label(custom_frame, text="Select an image file (PNG/JPG):",
                 font=(FONT_MONO, 8), bg=BG, fg=MUTED).pack(anchor="w", pady=(6, 4))

        def _browse():
            path = filedialog.askopenfilename(
                parent=popup,
                title="Choose icon image",
                filetypes=[("Image files", "*.png *.jpg *.jpeg *.bmp *.gif *.ico"),
                           ("All files", "*.*")])
            if path:
                try:
                    from PIL import Image as _PILImage
                    img = _PILImage.open(path).convert("RGBA").resize((34, 34),
                                                                       _PILImage.LANCZOS)
                    self._apply_pil_icon(img)
                    popup.destroy()
                except Exception as ex:
                    tk.Label(custom_frame, text=f"Error: {ex}", font=(FONT_MONO, 8),
                             bg=BG, fg=RED, wraplength=280).pack()

        tk.Button(custom_frame, text="Browse…", font=(FONT_MONO, 9),
                  bg=BG3, fg=TEXT, relief="flat", bd=0, cursor="hand2",
                  padx=10, pady=5, command=_browse).pack(anchor="w", pady=4)

        _show_preset()

        # Reset button at bottom
        def _reset():
            self.channel.pop('icon', None)
            _, _, _, dir_icon = self._dmeta()
            self._badge_cv.itemconfig(self._badge_txt, text=dir_icon,
                                      font=("Segoe UI Emoji", 12), fill=TEXT)
            if hasattr(self, '_badge_photo'):
                del self._badge_photo
            self.on_change()
            popup.destroy()

        tk.Button(popup, text="Reset to default", font=(FONT_MONO, 8),
                  bg=BG, fg=MUTED, relief="flat", bd=0, cursor="hand2",
                  command=_reset).pack(pady=(6, 8))

    def _pick_emoji(self, emoji: str, popup: tk.Toplevel):
        self.channel['icon'] = emoji
        self._badge_cv.itemconfig(self._badge_txt, text=emoji,
                                  font=("Segoe UI Emoji", 14))
        if hasattr(self, '_badge_photo'):
            del self._badge_photo
        self.on_change()
        popup.destroy()

    # ── Rename popup ──────────────────────────────────────────────────────────
    def _open_rename_popup(self):
        CYAN = "#00d4e8"
        popup = tk.Toplevel(self)
        popup.title("Rename Channel")
        popup.geometry("280x140")
        popup.configure(bg=BG)
        popup.resizable(False, False)
        popup.grab_set()

        tk.Label(popup, text="RENAME CHANNEL", font=(FONT_MONO, 9, "bold"),
                 bg=BG, fg=CYAN).pack(anchor="w", padx=14, pady=(14, 6))
        var = tk.StringVar(value=self.channel.get('name', ''))
        ent = tk.Entry(popup, textvariable=var, font=(FONT_RAJDHANI, 12),
                       bg=BG2, fg=TEXT, insertbackground=TEXT, relief="flat",
                       highlightthickness=1, highlightbackground=BORDER)
        ent.pack(fill="x", padx=14, pady=(0, 10))
        ent.select_range(0, tk.END)
        ent.focus_set()

        def _apply():
            name = var.get().strip()
            if name:
                self.channel['name'] = name
                disp = (name[:8] + '…') if len(name) > 8 else name
                self._name_lbl.config(text=disp)
                self.on_change()
            popup.destroy()

        ent.bind("<Return>", lambda e: _apply())
        bf = tk.Frame(popup, bg=BG)
        bf.pack(fill="x", padx=14, pady=(0, 14))
        tk.Button(bf, text="OK", font=(FONT_MONO, 9, "bold"),
                  bg=CYAN_DIM, fg=CYAN, relief="flat", bd=0, cursor="hand2",
                  command=_apply, padx=8, pady=4).pack(side="left", expand=True,
                                                        fill="x", padx=(0, 4))
        tk.Button(bf, text="CANCEL", font=(FONT_MONO, 9),
                  bg=BG3, fg=MUTED, relief="flat", bd=0, cursor="hand2",
                  command=popup.destroy, padx=8, pady=4).pack(side="left")

    # ── Right-click context menu ──────────────────────────────────────────────
    def _show_context_menu(self, event):
        CYAN = "#00d4e8"
        menu = tk.Toplevel(self)
        menu.overrideredirect(True)
        menu.configure(bg="#00d4e8")   # 1px cyan border via bg padding

        inner = tk.Frame(menu, bg="#001820", padx=1, pady=1)
        inner.pack(fill="both", expand=True, padx=1, pady=1)

        enabled = self.channel.get('enabled', True)
        toggle_text = "Turn OFF" if enabled else "Turn ON"

        items = [
            ("Rename Channel",   self._open_rename_popup),
            ("Select Source",    self._open_source_popup),
            ("Change Direction", self._open_direction_popup),
            ("Change Color",     self._open_color_picker),
            ("Change Icon",      self._open_icon_picker),
            (toggle_text,        self._toggle_enable),
            ("Channel Info",     self._open_info_popup),
            ("separator",        None),
            ("Delete Channel",   lambda: self._confirm_delete(menu)),
        ]

        def _close(e=None):
            try:
                menu.destroy()
            except Exception:
                pass

        for label, cmd in items:
            if label == "separator":
                tk.Frame(inner, height=1, bg=CYAN_DIM).pack(fill="x", padx=4, pady=2)
                continue
            is_delete = label == "Delete Channel"
            fg = RED if is_delete else TEXT

            lbl = tk.Label(inner, text=label, font=(FONT_MONO, 9),
                           bg="#001820", fg=fg, anchor="w", padx=12, pady=5,
                           cursor="hand2")
            lbl.pack(fill="x")

            def _make_handler(c, close_fn=_close):
                def _handler(e=None):
                    close_fn()
                    if c:
                        c()
                return _handler

            lbl.bind("<Button-1>",  _make_handler(cmd))
            lbl.bind("<Enter>",     lambda e, w=lbl, d=is_delete:
                                    w.config(bg=RED2 if d else BG3))
            lbl.bind("<Leave>",     lambda e, w=lbl: w.config(bg="#001820"))

        menu.update_idletasks()
        mx = event.x_root
        my = event.y_root
        sw = menu.winfo_width()
        sh = menu.winfo_height()
        sw = menu.winfo_reqwidth()
        sh = menu.winfo_reqheight()
        screen_w = menu.winfo_screenwidth()
        screen_h = menu.winfo_screenheight()
        if mx + sw > screen_w:
            mx = screen_w - sw - 4
        if my + sh > screen_h:
            my = screen_h - sh - 4
        menu.geometry(f"+{mx}+{my}")
        menu.lift()
        menu.focus_set()
        menu.bind("<FocusOut>", _close)
        menu.bind("<Escape>",   _close)

    def _confirm_delete(self, menu=None):
        if menu:
            try:
                menu.destroy()
            except Exception:
                pass
        CYAN = "#00d4e8"
        dlg = tk.Toplevel(self)
        dlg.title("Confirm Delete")
        dlg.geometry("260x120")
        dlg.configure(bg=BG)
        dlg.resizable(False, False)
        dlg.grab_set()
        name = self.channel.get('name', 'this channel')
        tk.Label(dlg, text=f"Delete «{name}»?", font=(FONT_MONO, 9),
                 bg=BG, fg=TEXT, wraplength=230).pack(pady=(20, 10))
        bf = tk.Frame(dlg, bg=BG)
        bf.pack(padx=16, pady=(0, 16), fill="x")
        tk.Button(bf, text="DELETE", font=(FONT_MONO, 9, "bold"),
                  bg=RED2, fg=RED, relief="flat", bd=0, cursor="hand2",
                  command=lambda: [dlg.destroy(),
                                   self.on_remove(self.channel['id'])],
                  padx=8, pady=4).pack(side="left", expand=True, fill="x", padx=(0, 4))
        tk.Button(bf, text="CANCEL", font=(FONT_MONO, 9),
                  bg=BG3, fg=MUTED, relief="flat", bd=0, cursor="hand2",
                  command=dlg.destroy, padx=8, pady=4).pack(side="left")

    def _bind_right_click(self, widget):
        widget.bind("<Button-3>", self._show_context_menu)
        for child in widget.winfo_children():
            self._bind_right_click(child)

    def _open_info_popup(self):
        popup = tk.Toplevel(self)
        popup.title("Channel Info")
        popup.geometry("340x210")
        popup.configure(bg=BG)
        popup.resizable(False, False)
        popup.grab_set()

        tk.Label(popup, text="CHANNEL INFO", font=("Segoe UI", 12, "bold"),
                 bg=BG, fg=TEXT).pack(anchor="w", padx=16, pady=(16, 4))
        tk.Frame(popup, height=1, bg=BORDER).pack(fill="x", padx=16, pady=(0, 12))

        def info_row(label, value, value_fg=TEXT, mono=False):
            f = tk.Frame(popup, bg=BG)
            f.pack(fill="x", padx=16, pady=2)
            tk.Label(f, text=label, font=("Segoe UI", 9),
                     bg=BG, fg=MUTED, width=12, anchor="w").pack(side="left")
            vfont = ("Courier New", 9) if mono else ("Segoe UI", 9)
            tk.Label(f, text=value, font=vfont,
                     bg=BG, fg=value_fg, anchor="w").pack(side="left")

        ch = self.channel
        _dir_fg_map   = {"out": GREEN, "mic": AMBER, "in": BLUE, "app": PURPLE}
        _dir_text_map = {"out": "OUT →", "mic": "MIC ↑", "in": "← IN", "app": "APP →"}
        dir_fg     = _dir_fg_map.get(ch['direction'], MUTED)
        cur_status = self.status_label.cget("text")
        status_fg  = STATUS_COLORS.get(cur_status, MUTED)

        info_row("name",      ch.get('name', '—'))
        info_row("direction", _dir_text_map.get(ch['direction'], ch['direction']), dir_fg)
        if ch.get('direction') == 'app':
            info_row("process",   ch.get('process') or '—', PURPLE)
        info_row("device",    ch.get('device') or '—')
        info_row("port",      str(ch.get('port', '—')), mono=True)
        info_row("volume",    f"{ch.get('volume', 100)}%")
        info_row("status",    cur_status, status_fg)

        tk.Frame(popup, height=1, bg=BORDER).pack(fill="x", padx=16, pady=(12, 0))
        tk.Button(popup, text="CLOSE", font=("Segoe UI", 9, "bold"),
                  bg=BG3, fg=MUTED, relief="flat", bd=0,
                  cursor="hand2", command=popup.destroy,
                  padx=8, pady=6).pack(pady=12, padx=16, fill="x")

    # ── Direction picker popup (OUT / IN / MIC-IN / MIC-OUT — APP set automatically) ──
    def _open_direction_popup(self):
        CYAN = "#00d4e8"
        popup = tk.Toplevel(self)
        popup.title("Set Direction")
        popup.geometry("280x280")
        popup.configure(bg=BG)
        popup.resizable(False, False)
        popup.grab_set()

        tk.Label(popup, text="CHANNEL DIRECTION", font=(FONT_MONO, 9, "bold"),
                 bg=BG, fg=CYAN).pack(anchor="w", padx=16, pady=(14, 2))
        tk.Frame(popup, height=1, bg=CYAN_DIM).pack(fill="x", padx=16, pady=(0, 12))
        tk.Label(popup, text="APP direction is set automatically\nwhen you select an application source.",
                 font=(FONT_MONO, 8), bg=BG, fg=MUTED, justify="left"
                 ).pack(anchor="w", padx=16, pady=(0, 10))

        options = [
            ("OUT",     "Outgoing (send audio)",    GREEN2,  GREEN,   "out"),
            ("IN",      "Incoming (receive audio)", BLUE2,   BLUE,    "in"),
            ("MIC-IN",  "Mic capture → send",       AMBER2,  AMBER,   "mic-in"),
            ("MIC-OUT", "Receive → mic output",     ORANGE2, ORANGE,  "mic-out"),
        ]

        def _pick(new_dir):
            old_dir = self.channel.get('direction', 'out')
            self.channel['direction'] = new_dir
            self.channel.pop('process', None)  # clear any app-mode process
            ds = _DIR_BADGE_STYLE.get(new_dir, _DIR_BADGE_STYLE['out'])
            self.dir_btn.config(text=ds['text'], bg=ds['bg'], fg=ds['fg'],
                                activebackground=ds['bg'], activeforeground=ds['fg'])
            self.on_change()
            popup.destroy()
            if self.on_refresh:
                self.on_refresh()

        for badge, label, dbg, dfg, direction in options:
            row = tk.Frame(popup, bg=BG)
            row.pack(fill="x", padx=16, pady=3)
            tk.Button(row, text=badge, font=(FONT_MONO, 8, "bold"),
                      bg=dbg, fg=dfg, relief="flat", bd=0, cursor="hand2",
                      activebackground=dbg, activeforeground=dfg,
                      width=5, padx=4, pady=4,
                      command=lambda d=direction: _pick(d)
                      ).pack(side="left", padx=(0, 8))
            tk.Label(row, text=label, font=(FONT_MONO, 9),
                     bg=BG, fg=TEXT, anchor="w").pack(side="left")

        tk.Button(popup, text="CANCEL", font=(FONT_MONO, 8),
                  bg=BG3, fg=MUTED, relief="flat", bd=0, cursor="hand2",
                  command=popup.destroy, padx=8, pady=4
                  ).pack(pady=(4, 14))

    def _open_source_popup(self):
        popup = tk.Toplevel(self)
        popup.title("Select Source")
        popup.geometry("480x520")
        popup.configure(bg=BG)
        popup.resizable(False, False)
        popup.grab_set()

        tk.Label(popup, text="SELECT SOURCE", font=("Segoe UI", 12, "bold"),
                 bg=BG, fg=TEXT).pack(anchor="w", padx=16, pady=(16, 4))
        tk.Frame(popup, height=1, bg=BORDER).pack(fill="x", padx=16, pady=(0, 8))

        _dev_devices = []
        _app_sources = []

        # ── Device Sources ────────────────────────────────────────────────────
        dev_hdr = tk.Frame(popup, bg=BG)
        dev_hdr.pack(fill="x", padx=16, pady=(0, 2))
        tk.Label(dev_hdr, text="DEVICE SOURCES", font=("Segoe UI", 8, "bold"),
                 bg=BG, fg=MUTED).pack(side="left")
        tk.Button(dev_hdr, text="↻ Refresh", font=(FONT_MONO, 8),
                  bg=BG3, fg=MUTED, relief="flat", bd=0,
                  cursor="hand2", padx=4, pady=1,
                  command=lambda: populate_devices()).pack(side="right")
        dev_outer = tk.Frame(popup, bg=BG)
        dev_outer.pack(fill="both", expand=True, padx=16, pady=(0, 8))
        dev_lb = tk.Listbox(dev_outer, font=("Segoe UI", 9), height=5,
                            bg=BG2, fg=TEXT, selectbackground=BG3, selectforeground=GREEN,
                            relief="flat", bd=0, highlightthickness=1,
                            highlightbackground=BORDER, activestyle="none")
        dev_sb = tk.Scrollbar(dev_outer, orient="vertical", command=dev_lb.yview)
        dev_lb.configure(yscrollcommand=dev_sb.set)
        dev_sb.pack(side="right", fill="y")
        dev_lb.pack(side="left", fill="both", expand=True)

        def populate_devices():
            nonlocal _dev_devices
            try:
                pa = pyaudio.PyAudio()
            except Exception:
                logger.error(f"_open_source_popup populate_devices: PyAudio init failed:\n{traceback.format_exc()}")
                return
            try:
                direction = self.channel['direction']
                if direction in ("out", "app"):
                    devs = get_loopback_devices(pa)
                elif direction in ("mic", "mic-in"):
                    devs = get_input_devices(pa)
                elif direction == "mic-out":
                    devs = get_output_devices(pa)
                else:
                    devs = get_output_devices(pa)
            except Exception:
                logger.error(f"_open_source_popup populate_devices failed:\n{traceback.format_exc()}")
                devs = []
            finally:
                pa.terminate()
            _dev_devices = devs
            dev_lb.delete(0, tk.END)
            for d in devs:
                dev_lb.insert(tk.END, d[:60] + '...' if len(d) > 60 else d)
            current = self.channel.get('device', '')
            if current in devs and self.channel.get('direction') != 'app':
                idx = devs.index(current)
                dev_lb.selection_set(idx)
                dev_lb.see(idx)

        populate_devices()

        # ── App Sources ───────────────────────────────────────────────────────
        tk.Frame(popup, height=1, bg=BORDER).pack(fill="x", padx=16, pady=(0, 6))
        app_hdr = tk.Frame(popup, bg=BG)
        app_hdr.pack(fill="x", padx=16, pady=(0, 2))
        tk.Label(app_hdr, text="APPLICATION SOURCES", font=("Segoe UI", 8, "bold"),
                 bg=BG, fg=MUTED).pack(side="left")
        tk.Button(app_hdr, text="↻ Refresh", font=(FONT_MONO, 8),
                  bg=BG3, fg=MUTED, relief="flat", bd=0,
                  cursor="hand2", padx=4, pady=1,
                  command=lambda: populate_apps()).pack(side="right")
        app_outer = tk.Frame(popup, bg=BG)
        app_outer.pack(fill="both", expand=True, padx=16, pady=(0, 8))
        app_lb = tk.Listbox(app_outer, font=("Segoe UI", 9), height=5,
                            bg=BG2, fg=TEXT, selectbackground=BG3, selectforeground=PURPLE,
                            relief="flat", bd=0, highlightthickness=1,
                            highlightbackground=BORDER, activestyle="none")
        app_sb = tk.Scrollbar(app_outer, orient="vertical", command=app_lb.yview)
        app_lb.configure(yscrollcommand=app_sb.set)
        app_sb.pack(side="right", fill="y")
        app_lb.pack(side="left", fill="both", expand=True)

        def populate_apps():
            nonlocal _app_sources
            try:
                pa = pyaudio.PyAudio()
            except Exception:
                logger.error(f"_open_source_popup populate_apps: PyAudio init failed:\n{traceback.format_exc()}")
                return
            try:
                sources = get_app_audio_sources(pa)
            except Exception:
                logger.error(f"_open_source_popup populate_apps failed:\n{traceback.format_exc()}")
                sources = []
            finally:
                pa.terminate()
            _app_sources = sources
            app_lb.delete(0, tk.END)
            for s in sources:
                display = s['display_name']
                proc    = s['process_name']
                label   = f"{display}  ({proc})" if display != proc else display
                app_lb.insert(tk.END, label[:60] + '...' if len(label) > 60 else label)
            current_proc = self.channel.get('process', '')
            if self.channel.get('direction') == 'app' and current_proc:
                for i, s in enumerate(sources):
                    if s['process_name'] == current_proc:
                        app_lb.selection_set(i)
                        app_lb.see(i)
                        break

        populate_apps()

        # Mutual exclusion between the two lists
        dev_lb.bind("<<ListboxSelect>>", lambda e: app_lb.selection_clear(0, tk.END))
        app_lb.bind("<<ListboxSelect>>", lambda e: dev_lb.selection_clear(0, tk.END))

        def select():
            dev_sel = dev_lb.curselection()
            app_sel = app_lb.curselection()
            if dev_sel:
                device    = _dev_devices[dev_sel[0]]
                direction = self.channel['direction']
                if direction == 'app':
                    direction = 'out'
                old_dir = self.channel['direction']
                self.channel['direction'] = direction
                self.channel['device']    = device
                self.channel.pop('process', None)
                if direction == "out":
                    dir_bg, dir_fg, dir_text = GREEN2, GREEN, "OUT →"
                elif direction == "mic":
                    dir_bg, dir_fg, dir_text = AMBER2, AMBER, "MIC ↑"
                else:
                    dir_bg, dir_fg, dir_text = BLUE2, BLUE, "← IN"
                self.dir_btn.config(text=dir_text, bg=dir_bg, fg=dir_fg,
                                    activebackground=dir_bg, activeforeground=dir_fg)
                label = device[:42] + "..." if len(device) > 42 else device
                self.device_btn.config(text=label)
                self.on_change()
                self._draw_src_btn()
                popup.destroy()
                if old_dir != direction and self.on_refresh:
                    self.on_refresh()
            elif app_sel:
                source  = _app_sources[app_sel[0]]
                self.channel['direction'] = 'app'
                self.channel['process']   = source['process_name']
                self.channel['device']    = source['display_name']
                ds = _DIR_BADGE_STYLE.get('app', _DIR_BADGE_STYLE['out'])
                self.dir_btn.config(text=ds['text'], bg=ds['bg'], fg=ds['fg'],
                                    activebackground=ds['bg'], activeforeground=ds['fg'])
                label = source['display_name']
                label = label[:42] + "..." if len(label) > 42 else label
                self.device_btn.config(text=label)
                # Always auto-apply exe icon when an application is selected
                ico_img = _extract_exe_icon_image(
                    source['process_name'], size=34,
                    exe_path=source.get('exe_path'))
                if ico_img:
                    self._apply_pil_icon(ico_img)
                self.on_change()
                self._draw_src_btn()
                popup.destroy()
                if self.on_refresh:
                    self.on_refresh()

        dev_lb.bind("<Double-Button-1>", lambda e: select())
        app_lb.bind("<Double-Button-1>", lambda e: select())

        bf = tk.Frame(popup, bg=BG)
        bf.pack(fill="x", padx=16, pady=(0, 14))
        tk.Button(bf, text="SELECT", font=("Segoe UI", 9, "bold"),
                  bg=GREEN2, fg=GREEN, relief="flat", bd=0,
                  cursor="hand2", command=select,
                  padx=8, pady=5).pack(side="left", expand=True, fill="x", padx=(0, 4))
        tk.Button(bf, text="CANCEL", font=("Segoe UI", 9),
                  bg=BG3, fg=MUTED, relief="flat", bd=0,
                  cursor="hand2", command=popup.destroy,
                  padx=8, pady=5).pack(side="left")

    def _toggle_direction(self):
        old_dir = self.channel['direction']
        ch_name = self.channel.get('name', '?')
        ch_id   = self.channel.get('id', '?')
        logger.info(f"_toggle_direction START — channel='{ch_name}' id={ch_id} old_dir='{old_dir}'")
        try:
            # Step 1 — compute new direction
            if old_dir == "out":
                new_dir = "in"
            elif old_dir == "in":
                new_dir = "mic"
            else:
                new_dir = "out"
            logger.info(f"_toggle_direction [1/6] new_dir='{new_dir}'")

            # Step 2 — write new direction into channel dict
            self.channel['direction'] = new_dir
            logger.info(f"_toggle_direction [2/6] channel dict updated, direction now='{self.channel['direction']}'")

            # Step 3 — update button appearance
            if new_dir == "out":
                dir_bg, dir_fg, dir_text = GREEN2, GREEN, "OUT →"
            elif new_dir == "mic":
                dir_bg, dir_fg, dir_text = AMBER2, AMBER, "MIC ↑"
            else:
                dir_bg, dir_fg, dir_text = BLUE2, BLUE, "← IN"
            self.dir_btn.config(text=dir_text, bg=dir_bg, fg=dir_fg,
                                 activebackground=dir_bg, activeforeground=dir_fg)
            logger.info(f"_toggle_direction [3/6] dir_btn updated to '{dir_text}'")

            # Step 4 — clear device selection
            self.channel['device'] = ""
            self.device_btn.config(text="Select Device")
            logger.info(f"_toggle_direction [4/6] device cleared")

            # Step 5 — save config via on_change callback
            logger.info(f"_toggle_direction [5/6] calling on_change() to save config")
            self.on_change()
            logger.info(f"_toggle_direction [5/6] on_change() returned — verifying saved direction")
            # Confirm the channel dict still holds the right value after save
            saved_dir = self.channel.get('direction', '<missing>')
            if saved_dir != new_dir:
                logger.error(f"_toggle_direction [5/6] CONFIG MISMATCH after save: expected '{new_dir}', got '{saved_dir}'")
            else:
                logger.info(f"_toggle_direction [5/6] config OK — direction='{saved_dir}'")

            # Step 6 — rebuild channel rows via on_refresh
            if self.on_refresh:
                logger.info(f"_toggle_direction [6/6] calling on_refresh() to rebuild channel rows")
                self.on_refresh()
                logger.info(f"_toggle_direction [6/6] on_refresh() returned")
            else:
                logger.info(f"_toggle_direction [6/6] on_refresh is None — skipping row rebuild")

            logger.info(f"_toggle_direction DONE — '{ch_name}' is now '{new_dir}'")

        except Exception:
            logger.error(f"_toggle_direction EXCEPTION (reverting '{ch_name}' to '{old_dir}'):\n{traceback.format_exc()}")
            self.channel['direction'] = old_dir

    def _open_device_popup(self):
        popup = tk.Toplevel(self)
        popup.title("Select Device")
        popup.geometry("440x320")
        popup.configure(bg=BG)
        popup.resizable(False, False)
        popup.grab_set()

        tk.Label(popup, text="SELECT DEVICE", font=("Segoe UI", 12, "bold"),
                 bg=BG, fg=TEXT).pack(anchor="w", padx=16, pady=(16, 4))
        tk.Frame(popup, height=1, bg=BORDER).pack(fill="x", padx=16, pady=(0, 8))

        list_frame = tk.Frame(popup, bg=BG)
        list_frame.pack(fill="both", expand=True, padx=16, pady=(0, 8))

        lb = tk.Listbox(list_frame, font=("Segoe UI", 9),
                        bg=BG2, fg=TEXT, selectbackground=BG3, selectforeground=GREEN,
                        relief="flat", bd=0, highlightthickness=1,
                        highlightbackground=BORDER, activestyle="none")
        sb_scroll = tk.Scrollbar(list_frame, orient="vertical", command=lb.yview)
        lb.configure(yscrollcommand=sb_scroll.set)
        sb_scroll.pack(side="right", fill="y")
        lb.pack(side="left", fill="both", expand=True)

        self._popup_devices = []

        def populate():
            try:
                pa = pyaudio.PyAudio()
            except Exception:
                logger.error(f"_open_device_popup: PyAudio init failed:\n{traceback.format_exc()}")
                return
            try:
                direction = self.channel['direction']
                if direction in ("out", "app"):
                    devs = get_loopback_devices(pa)
                elif direction == "mic":
                    # Streaming PC captures from a real input device (Wave XLR).
                    # Gaming PC plays received mic audio to an output device.
                    devs = get_input_devices(pa) if self.mode == 'streaming' else get_output_devices(pa)
                elif direction == "in":
                    devs = get_output_devices(pa)
                else:
                    logger.error(f"_open_device_popup: unknown direction '{direction}'")
                    devs = []
            except Exception:
                logger.error(f"_open_device_popup: device enumeration failed:\n{traceback.format_exc()}")
                devs = []
            finally:
                pa.terminate()
            self._popup_devices = devs  # full names — used when saving to config
            lb.delete(0, tk.END)
            for d in devs:
                lb.insert(tk.END, d[:60] + '...' if len(d) > 60 else d)  # truncate display only
            current = self.channel.get('device', '')
            if current in devs:
                idx = devs.index(current)
                lb.selection_set(idx)
                lb.see(idx)

        def select():
            sel = lb.curselection()
            if not sel:
                return
            device = self._popup_devices[sel[0]]   # always the full, untruncated name
            self.channel['device'] = device         # store full name in config
            label = device[:42] + "..." if len(device) > 42 else device  # display only
            self.device_btn.config(text=label)
            self.on_change()
            popup.destroy()

        populate()
        lb.bind("<Double-Button-1>", lambda e: select())

        bf = tk.Frame(popup, bg=BG)
        bf.pack(fill="x", padx=16, pady=(0, 14))
        tk.Button(bf, text="SELECT", font=("Segoe UI", 9, "bold"),
                  bg=GREEN2, fg=GREEN, relief="flat", bd=0,
                  cursor="hand2", command=select,
                  padx=8, pady=5).pack(side="left", expand=True, fill="x", padx=(0, 4))
        tk.Button(bf, text="REFRESH", font=("Segoe UI", 9),
                  bg=BG3, fg=MUTED, relief="flat", bd=0,
                  cursor="hand2", command=populate,
                  padx=8, pady=5).pack(side="left", padx=(0, 4))
        tk.Button(bf, text="CANCEL", font=("Segoe UI", 9),
                  bg=BG3, fg=MUTED, relief="flat", bd=0,
                  cursor="hand2", command=popup.destroy,
                  padx=8, pady=5).pack(side="left")

    def set_status(self, status):
        color = STATUS_COLORS.get(status, MUTED)
        self._dot_cv.itemconfig(self._dot_item, fill=color)
        self.status_label.config(text=status, fg=color)

    def set_level(self, level):
        try:
            self.level_queue.put_nowait(level)
        except Exception:
            pass

    def update_level(self):
        target = self.smooth_level
        while not self.level_queue.empty():
            try:
                target = self.level_queue.get_nowait()
            except Exception:
                pass
        self.smooth_level = self.smooth_level * 0.7 + target * 0.3
        self._redraw_meter()


class _HudTooltip:
    """500 ms delayed HUD-themed tooltip attached to a widget."""
    _TOOLTIP_BG  = "#040e14"
    _TOOLTIP_FG  = "#cce9ef"
    _TOOLTIP_BD  = "#00d4e8"
    _TOOLTIP_FNT = (FONT_MONO, 8)

    def __init__(self, widget, text):
        self._widget = widget
        self._text   = text
        self._tip    = None
        self._after  = None
        widget.bind("<Enter>",  self._on_enter, add="+")
        widget.bind("<Leave>",  self._on_leave, add="+")
        widget.bind("<Destroy>", lambda e: self._cancel(), add="+")

    def _on_enter(self, event):
        self._cancel()
        self._after = self._widget.after(500, self._show)

    def _on_leave(self, event):
        self._cancel()
        self._hide()

    def _cancel(self):
        if self._after is not None:
            try:
                self._widget.after_cancel(self._after)
            except Exception:
                pass
            self._after = None

    def _show(self):
        self._after = None
        if self._tip:
            return
        x = self._widget.winfo_rootx() + 4
        y = self._widget.winfo_rooty() + self._widget.winfo_height() + 4
        self._tip = tw = tk.Toplevel(self._widget)
        tw.wm_overrideredirect(True)
        tw.wm_geometry(f"+{x}+{y}")
        tw.configure(bg=self._TOOLTIP_BD)
        inner = tk.Frame(tw, bg=self._TOOLTIP_BG, padx=8, pady=5)
        inner.pack(padx=1, pady=1)
        tk.Label(inner, text=self._text, font=self._TOOLTIP_FNT,
                 bg=self._TOOLTIP_BG, fg=self._TOOLTIP_FG,
                 wraplength=300, justify="left").pack()

    def _hide(self):
        if self._tip:
            try:
                self._tip.destroy()
            except Exception:
                pass
            self._tip = None


class SettingsPanel(tk.Toplevel):
    _CYAN   = "#00d4e8"
    _ENTRY_BG = "#061820"

    def __init__(self, parent, cfg, on_save):
        super().__init__(parent)
        self.title("Settings — ShadowBridge")
        self.geometry("520x640")
        self.resizable(False, False)
        self.configure(bg=BG)
        self.cfg     = cfg
        self.on_save = on_save
        self._build()

    # ── helpers ──────────────────────────────────────────────────────────────

    def _section(self, text):
        tk.Label(self, text=text, font=(FONT_MONO, 9, "bold"),
                 bg=BG, fg=self._CYAN).pack(anchor="w", padx=24, pady=(18, 2))
        tk.Frame(self, height=1, bg=self._CYAN).pack(fill="x", padx=24, pady=(0, 6))

    def _row(self, label, widget_factory, tip_text):
        f = tk.Frame(self, bg=BG)
        f.pack(fill="x", padx=24, pady=4)
        lbl = tk.Label(f, text=label, font=(FONT_MONO, 9),
                       bg=BG, fg=TEXT, width=30, anchor="w")
        lbl.pack(side="left")
        w = widget_factory(f)
        w.pack(side="left", fill="x", expand=True)
        _HudTooltip(lbl, tip_text)
        _HudTooltip(w,   tip_text)
        return w

    def _dropdown(self, parent, var, choices):
        opt = tk.OptionMenu(parent, var, *choices)
        opt.config(bg=self._ENTRY_BG, fg=TEXT,
                   activebackground=BG3, activeforeground=TEXT,
                   highlightthickness=1, highlightbackground=self._CYAN,
                   relief="flat", font=(FONT_MONO, 9), padx=6, pady=3,
                   indicatoron=True, bd=0)
        opt["menu"].config(bg=self._ENTRY_BG, fg=TEXT,
                           activebackground=self._CYAN, activeforeground=BG,
                           font=(FONT_MONO, 9))
        return opt

    def _entry(self, parent, var):
        return tk.Entry(parent, textvariable=var, font=(FONT_MONO, 9),
                        bg=self._ENTRY_BG, fg=TEXT, insertbackground=self._CYAN,
                        relief="flat", highlightthickness=1,
                        highlightbackground=self._CYAN, highlightcolor=self._CYAN,
                        width=14)

    def _checkbox(self, parent, var):
        return tk.Checkbutton(parent, variable=var,
                              bg=BG, fg=TEXT, selectcolor=self._ENTRY_BG,
                              activebackground=BG, activeforeground=TEXT,
                              highlightthickness=0, bd=0, cursor="hand2")

    # ── layout ───────────────────────────────────────────────────────────────

    def _build(self):
        tk.Label(self, text="SETTINGS", font=(FONT_MONO, 13, "bold"),
                 bg=BG, fg=self._CYAN).pack(anchor="w", padx=24, pady=(20, 2))
        tk.Frame(self, height=1, bg=self._CYAN).pack(fill="x", padx=24, pady=(0, 4))

        # ── Audio ─────────────────────────────────────────────────────────
        self._section("AUDIO")

        self.buf_var = tk.StringVar(value=str(self.cfg.get('buffer_size', 1024)))
        self._row("Buffer Size",
                  lambda p: self._dropdown(p, self.buf_var, ["256", "512", "1024", "2048"]),
                  "Controls the audio buffer size. Smaller = lower latency but may crackle. "
                  "Larger = more stable but adds slight delay.")

        self.rate_var = tk.StringVar(value=str(self.cfg.get('sample_rate', 48000)))
        self._row("Sample Rate",
                  lambda p: self._dropdown(p, self.rate_var, ["44100", "48000"]),
                  "Audio sample rate for all channels. 48000 Hz recommended for streaming. "
                  "Must match on both PCs.")

        # ── Network ───────────────────────────────────────────────────────
        self._section("NETWORK")

        _active_disc = str(self.cfg.get('discovery_port', 47777))
        _active_cmd  = str(self.cfg.get('command_port',   47778))

        self.disc_port_var = tk.StringVar(value=_active_disc)
        self._row("Discovery Port",
                  lambda p: self._entry(p, self.disc_port_var),
                  "UDP port used for peer discovery. Change if port 47777 conflicts with "
                  "another app. Must match on both PCs.")
        self._disc_warn = tk.Label(self, font=(FONT_MONO, 8), bg=BG, fg=BG,
                                   text="  \u26a0  Restart required for port changes to take effect")
        self._disc_warn.pack(anchor="w", padx=48, pady=(0, 2))

        self.cmd_port_var = tk.StringVar(value=_active_cmd)
        self._row("Command Port",
                  lambda p: self._entry(p, self.cmd_port_var),
                  "TCP port used for Start/Stop commands between PCs. Must match on both PCs.")
        self._cmd_warn = tk.Label(self, font=(FONT_MONO, 8), bg=BG, fg=BG,
                                  text="  \u26a0  Restart required for port changes to take effect")
        self._cmd_warn.pack(anchor="w", padx=48, pady=(0, 2))

        def _check_disc_warn(*_):
            changed = self.disc_port_var.get().strip() != _active_disc
            self._disc_warn.config(fg=AMBER if changed else BG)
        def _check_cmd_warn(*_):
            changed = self.cmd_port_var.get().strip() != _active_cmd
            self._cmd_warn.config(fg=AMBER if changed else BG)
        self.disc_port_var.trace_add("write", _check_disc_warn)
        self.cmd_port_var.trace_add("write", _check_cmd_warn)

        # ── Startup & Behavior ────────────────────────────────────────────
        self._section("STARTUP & BEHAVIOR")

        self.startup_var = tk.BooleanVar(value=_startup_registered())
        self._row("Launch on Windows startup",
                  lambda p: self._checkbox(p, self.startup_var),
                  "Automatically launch ShadowBridge when Windows starts, minimized to the "
                  "system tray.")

        self.autostart_var = tk.BooleanVar(value=bool(self.cfg.get('auto_start', False)))
        self._row("Auto-start streams on peer detect",
                  lambda p: self._checkbox(p, self.autostart_var),
                  "Automatically start all streams as soon as the other PC is detected. "
                  "No need to click Start All manually.")

        self.minimized_var = tk.BooleanVar(value=bool(self.cfg.get('start_minimized', False)))
        self._row("Start minimized",
                  lambda p: self._checkbox(p, self.minimized_var),
                  "Launch ShadowBridge directly to the system tray without showing the main "
                  "window.")

        # ── Notifications ─────────────────────────────────────────────────
        self._section("NOTIFICATIONS")

        self.notif_peer_var = tk.BooleanVar(value=bool(self.cfg.get('notify_peer', False)))
        self._row("Peer connect/disconnect",
                  lambda p: self._checkbox(p, self.notif_peer_var),
                  "Show a Windows desktop notification when the other PC connects or "
                  "disconnects.")

        self.notif_err_var = tk.BooleanVar(value=bool(self.cfg.get('notify_errors', False)))
        self._row("Channel error notifications",
                  lambda p: self._checkbox(p, self.notif_err_var),
                  "Show a Windows desktop notification when a channel errors or drops "
                  "unexpectedly.")

        # ── Buttons ───────────────────────────────────────────────────────
        tk.Frame(self, height=1, bg=BORDER).pack(fill="x", padx=24, pady=(20, 12))
        bf = tk.Frame(self, bg=BG)
        bf.pack(fill="x", padx=24, pady=(0, 20))
        tk.Button(bf, text="SAVE", font=(FONT_MONO, 10, "bold"),
                  bg=GREEN2, fg=GREEN, relief="flat", bd=0,
                  activebackground="#14532d", cursor="hand2",
                  command=self._save, pady=8).pack(side="left", expand=True, fill="x", padx=(0, 4))
        tk.Button(bf, text="CANCEL", font=(FONT_MONO, 10, "bold"),
                  bg=self._ENTRY_BG, fg=MUTED, relief="flat", bd=0,
                  cursor="hand2", command=self.destroy, pady=8).pack(side="left", expand=True, fill="x", padx=(4, 0))

    def _save(self):
        self.cfg['gaming_ip']             = self.cfg.get('gaming_ip', '192.168.4.225')
        self.cfg['streaming_ip']          = self.cfg.get('streaming_ip', '192.168.4.224')
        self.cfg['buffer_size']           = int(self.buf_var.get())
        self.cfg['sample_rate']           = int(self.rate_var.get())
        self.cfg['discovery_port']        = int(self.disc_port_var.get().strip())
        self.cfg['command_port']          = int(self.cmd_port_var.get().strip())
        _set_startup(self.startup_var.get())
        self.cfg['launch_on_startup']     = self.startup_var.get()
        self.cfg['auto_start']            = self.autostart_var.get()
        self.cfg['start_minimized']       = self.minimized_var.get()
        self.cfg['notify_peer']   = self.notif_peer_var.get()
        self.cfg['notify_errors'] = self.notif_err_var.get()
        self.on_save(self.cfg)
        self.destroy()


class ShadowBridgeApp:
    def __init__(self):
        self.cfg  = load_config()
        self.rows = {}
        self._log_popup_text  = None
        self._streams_active  = False
        self._app_alive       = True
        self._shutting_down   = False
        self._save_after_id   = None
        self._user_stopped    = False
        self._notif_last_sent = {}   # ch_id → timestamp, for 30 s debounce
        self._init_config()
        _load_google_fonts()
        self.engine = AudioEngine(
            on_status_change=self._on_status_change,
            on_level=self._on_level
        )
        self._build_ui()
        self._setup_tray()
        self._discovery = PeerDiscovery(
            get_announce_data=self._get_announce_data,
            on_peer_found=self._on_peer_found,
            on_peer_lost=self._on_peer_lost,
            on_port_sync=self._on_port_sync,
            on_command=self._on_remote_command,
            discovery_port=self.cfg.get('discovery_port', 47777),
            command_port=self.cfg.get('command_port', 47778),
        )
        self._discovery.start()
        self._ws_server = WsServer(self) if WS_AVAILABLE else None
        if not WS_AVAILABLE:
            logger.warning("websockets not installed — Stream Deck WS API disabled.")
        self._refresh_channels()

    def _init_config(self):
        local_ip = get_local_ip()
        if 'gaming_ip' not in self.cfg:
            self.cfg['gaming_ip']    = '192.168.4.225'
        if 'streaming_ip' not in self.cfg:
            self.cfg['streaming_ip'] = '192.168.4.224'
        if 'mode' not in self.cfg:
            if local_ip == self.cfg['gaming_ip']:
                self.cfg['mode'] = 'gaming'
            elif local_ip == self.cfg['streaming_ip']:
                self.cfg['mode'] = 'streaming'
            else:
                self.cfg['mode'] = 'gaming'
        if 'gaming_channels' not in self.cfg:
            self.cfg['gaming_channels'] = DEFAULT_GAMING_CHANNELS
        if 'streaming_channels' not in self.cfg:
            self.cfg['streaming_channels'] = DEFAULT_STREAMING_CHANNELS
        if 'buffer_size' not in self.cfg:
            self.cfg['buffer_size'] = 1024
        if 'sample_rate' not in self.cfg:
            self.cfg['sample_rate'] = 48000
        if 'discovery_port' not in self.cfg:
            self.cfg['discovery_port'] = 47777
        if 'command_port' not in self.cfg:
            self.cfg['command_port'] = 47778
        if 'auto_start' not in self.cfg:
            self.cfg['auto_start'] = False
        if 'start_minimized' not in self.cfg:
            self.cfg['start_minimized'] = False
        if 'launch_on_startup' not in self.cfg:
            self.cfg['launch_on_startup'] = False
        if 'notify_peer' not in self.cfg:
            self.cfg['notify_peer'] = False
        if 'notify_errors' not in self.cfg:
            self.cfg['notify_errors'] = False
        _apply_palette(DARK_PALETTE)
        self._migrate_channel_devices()
        save_config(self.cfg)

    def _migrate_channel_devices(self):
        for key in ('gaming_channels', 'streaming_channels'):
            for ch in self.cfg.get(key, []):
                device = ch.get('device', '')
                if device and _UUID_RE.match(device):
                    logger.warning(
                        f"Channel '{ch.get('name', '?')}': device field contained "
                        f"a UUID — cleared (please re-select the device)."
                    )
                    ch['device'] = ''

    def _channels(self):
        return self.cfg.get(f"{self.cfg['mode']}_channels", [])

    def _dest_ip(self):
        if self.cfg['mode'] == 'gaming':
            return self.cfg.get('streaming_ip', '192.168.4.224')
        return self.cfg.get('gaming_ip', '192.168.4.225')

    def _build_ui(self):
        self.root = tk.Tk()
        self.root.report_callback_exception = self._on_tk_exception
        self.root.title("ShadowBridge")
        self.root.geometry("960x720")
        self.root.resizable(True, True)
        self.root.minsize(600, 500)
        self.root.configure(bg=BG)

        try:
            self.root.iconbitmap(resource_path('shadowbridge_icon.ico'))
            self.root.wm_iconbitmap(resource_path('shadowbridge_icon.ico'))
        except:
            pass
        self.root.after(100, self._set_taskbar_icon)

        # ── Top cyan glow line ────────────────────────────────────────────────
        tk.Frame(self.root, height=2, bg="#00d4e8").pack(fill="x")

        # ── Scanline texture canvas (sits behind pack-managed content) ────────
        self._scanline_cv = tk.Canvas(self.root, bg=BG, highlightthickness=0, bd=0)
        self._scanline_cv.place(x=0, y=2, relwidth=1, relheight=1)
        tk.Misc.lower(self._scanline_cv)   # lower widget stacking order, not canvas items

        def _draw_scanlines(event=None):
            c = self._scanline_cv
            c.delete("scanline")
            h = self.root.winfo_height()
            w = self.root.winfo_width()
            for y in range(0, h, 4):
                c.create_line(0, y, w, y, fill="#00d4e8", stipple="gray12",
                               tags="scanline")
        self.root.bind("<Configure>", _draw_scanlines)
        self.root.after(100, _draw_scanlines)

        # ── Corner bracket decorations ────────────────────────────────────────
        arm, lw, cc = 18, 2, "#00d4e8"
        self._corners = []
        for anchor in ("nw", "ne", "sw", "se"):
            cv = tk.Canvas(self.root, width=arm+4, height=arm+4,
                           bg=BG, highlightthickness=0, bd=0)
            cv.place(relx=1 if "e" in anchor else 0,
                     rely=1 if "s" in anchor else 0,
                     anchor=anchor)
            ox = arm+1 if "e" in anchor else 1
            oy = arm+1 if "s" in anchor else 1
            dx = -1  if "e" in anchor else 1
            dy = -1  if "s" in anchor else 1
            cv.create_line(ox, oy, ox + dx*arm, oy,         fill=cc, width=lw)
            cv.create_line(ox, oy, ox,           oy + dy*arm, fill=cc, width=lw)
            tk.Misc.lift(cv)   # lift widget stacking order, not canvas items
            self._corners.append(cv)

        header = tk.Frame(self.root, bg=BG)
        header.pack(fill="x", padx=20, pady=(12, 4))

        # Left: icon + stacked subtitle / title
        title_left = tk.Frame(header, bg=BG)
        title_left.pack(side="left")
        self._title_icon_photo = None
        if TRAY_AVAILABLE and PILImageTk is not None:
            try:
                _ico = PILImage.open(resource_path("shadowbridge_icon.png")).resize((44, 44), PILImage.LANCZOS)
                self._title_icon_photo = PILImageTk.PhotoImage(_ico)
                tk.Label(title_left, image=self._title_icon_photo,
                         bg=BG, bd=0).pack(side="left", padx=(0, 10))
            except Exception:
                pass
        title_text = tk.Frame(title_left, bg=BG)
        title_text.pack(side="left")
        tk.Label(title_text, text="DUAL PC AUDIO SYSTEM",
                 font=(FONT_MONO, 8), bg=BG, fg=AMBER).pack(anchor="w")
        tk.Label(title_text, text="ShadowBridge",
                 font=(FONT_RAJDHANI, 26, "bold"), bg=BG, fg="#00d4e8").pack(anchor="w")

        # Right: mode pill + utility buttons
        right = tk.Frame(header, bg=BG)
        right.pack(side="right")
        tk.Button(right, text="⚙ SETTINGS", font=(FONT_MONO, 8),
                  bg=BG3, fg=MUTED, relief="flat", bd=0,
                  activebackground=BG2, activeforeground=TEXT,
                  cursor="hand2", command=self._open_settings,
                  padx=8, pady=5).pack(side="right", padx=(4, 0))
        tk.Button(right, text="[ LOG ]", font=(FONT_MONO, 8),
                  bg=BG3, fg=MUTED, relief="flat", bd=0,
                  activebackground=BG2, activeforeground=TEXT,
                  cursor="hand2", command=self._open_log_popup,
                  padx=8, pady=5).pack(side="right", padx=(4, 0))
        self.mode_btn = tk.Button(right, text="", font=(FONT_MONO, 8, "bold"),
                                   relief="flat", bd=0, cursor="hand2",
                                   command=self._switch_mode, padx=10, pady=5)
        self.mode_btn.pack(side="right")

        tk.Frame(self.root, height=1, bg=BORDER).pack(fill="x", padx=20, pady=(8, 0))

        sb = tk.Frame(self.root, bg=BG2)
        sb.pack(fill="x")
        self.peer_dot = tk.Label(sb, text="●", font=(FONT_MONO, 9), bg=BG2, fg="#00d4e8")
        self.peer_dot.pack(side="left", padx=(20, 4), pady=6)
        self.peer_label = tk.Label(sb, text="searching for peer...",
                                    font=(FONT_MONO, 9), bg=BG2, fg=MUTED)
        self.peer_label.pack(side="left", pady=6)
        tk.Label(sb, text="//", font=(FONT_MONO, 9), bg=BG2, fg=BORDER).pack(side="left", padx=10, pady=6)
        self.status_ip_label = tk.Label(sb, text="", font=(FONT_MONO, 9), bg=BG2, fg=MUTED)
        self.status_ip_label.pack(side="left", pady=6)
        tk.Frame(self.root, height=1, bg=BORDER).pack(fill="x")

        # ── Footer + bottom bar: packed BOTTOM first so expand=True mixer never clips them ──
        footer = tk.Frame(self.root, bg=BG, height=20)
        footer.pack(side="bottom", fill="x", pady=0)
        footer.pack_propagate(False)
        tk.Label(footer,
                 text=f"ShadowBridge v{VERSION}  //  Dual PC Audio Routing  //  SYS: NOMINAL",
                 font=(FONT_MONO, 8), bg=BG, fg=CYAN_DIM).pack(side="left", padx=20, pady=2)

        bf = tk.Frame(self.root, bg=BG)
        bf.pack(side="bottom", fill="x", padx=20, pady=(6, 6))

        # Canvas-based parallelogram (angled clip-path) buttons
        self._btn_start_enabled = True
        self._btn_stop_enabled  = False

        self.btn_start = tk.Canvas(bf, height=38, bg=BG, highlightthickness=0, cursor="hand2")
        self.btn_start.pack(side="left", expand=True, fill="x", padx=(0, 4))
        self.btn_stop = tk.Canvas(bf, height=38, bg=BG, highlightthickness=0, cursor="hand2")
        self.btn_stop.pack(side="left", expand=True, fill="x", padx=(4, 0))

        def _draw_para_btn(cv, text, bg_fill, border_col, text_col, enabled):
            cv.delete("all")
            w = cv.winfo_width() or 160
            h = cv.winfo_height() or 38
            sk = 10  # skew offset
            pts = [sk, 0, w, 0, w - sk, h, 0, h]
            cv.create_polygon(pts, fill=bg_fill, outline=border_col, width=1)
            cv.create_text(w // 2, h // 2, text=text,
                           font=(FONT_ORBITRON, 10, "bold"),
                           fill=text_col if enabled else MUTED)

        def _redraw_start():
            if self._btn_start_enabled:
                _draw_para_btn(self.btn_start, "START ALL",
                               "#0c1f10", "#166534", "#4ade80", True)
            else:
                _draw_para_btn(self.btn_start, "START ALL",
                               BG3, BG3, MUTED, False)

        def _redraw_stop():
            if self._btn_stop_enabled:
                _draw_para_btn(self.btn_stop, "STOP ALL",
                               "#1f0808", "#7f1d1d", "#f87171", True)
            else:
                _draw_para_btn(self.btn_stop, "STOP ALL",
                               BG3, BG3, MUTED, False)

        self._redraw_start = _redraw_start
        self._redraw_stop  = _redraw_stop

        def _on_start_click(e):
            if self._btn_start_enabled:
                self._start()
        def _on_stop_click(e):
            if self._btn_stop_enabled:
                self._stop()

        self.btn_start.bind("<Button-1>", _on_start_click)
        self.btn_stop.bind("<Button-1>", _on_stop_click)
        self.btn_start.bind("<Configure>", lambda e: _redraw_start())
        self.btn_stop.bind("<Configure>", lambda e: _redraw_stop())
        self.root.after(50, _redraw_start)
        self.root.after(50, _redraw_stop)

        tk.Frame(self.root, height=1, bg=CYAN_DIM).pack(side="bottom", fill="x", padx=0, pady=(0, 4))

        self.text_log = scrolledtext.ScrolledText(
            self.root, height=0, font=(FONT_MONO, 9),
            state=tk.DISABLED, bg=BG2, fg=MUTED,
            relief="flat", bd=0, padx=10, pady=0,
            insertbackground=TEXT
        )
        self.text_log.tag_config("green",  foreground=GREEN)
        self.text_log.tag_config("red",    foreground=RED)
        self.text_log.tag_config("amber",  foreground=AMBER)
        self.text_log.tag_config("normal", foreground=MUTED)

        # ── Mixer area: fixed-height strips, scrollable both axes ────────────
        mixer_outer = tk.Frame(self.root, bg=MIXER_BG)
        mixer_outer.pack(fill="both", expand=True, padx=0, pady=(0, 0))

        self.mixer_canvas = tk.Canvas(mixer_outer, bg=MIXER_BG, highlightthickness=0, bd=0)
        h_sb = tk.Scrollbar(mixer_outer, orient="horizontal",
                             command=self.mixer_canvas.xview)
        v_sb = tk.Scrollbar(mixer_outer, orient="vertical",
                             command=self.mixer_canvas.yview)
        self.mixer_frame = tk.Frame(self.mixer_canvas, bg=MIXER_BG)
        self.mixer_frame.bind("<Configure>", lambda e: self.mixer_canvas.configure(
            scrollregion=self.mixer_canvas.bbox("all")))
        self._mixer_window = self.mixer_canvas.create_window((0, 0), window=self.mixer_frame, anchor="nw")
        self.mixer_canvas.configure(xscrollcommand=h_sb.set, yscrollcommand=v_sb.set)
        # Keep mixer_frame height = canvas height so fill="y" children expand properly
        self.mixer_canvas.bind("<Configure>", lambda e: (
            self.mixer_canvas.itemconfig(self._mixer_window, height=e.height),
            self.mixer_canvas.configure(scrollregion=self.mixer_canvas.bbox("all"))
        ))
        h_sb.pack(side="bottom", fill="x")
        v_sb.pack(side="right",  fill="y")
        self.mixer_canvas.pack(side="top", fill="both", expand=True)

        # Wheel scrolls vertically; Shift+wheel scrolls horizontally
        def _on_wheel(event):
            if event.state & 0x0001:  # Shift held
                self.mixer_canvas.xview_scroll(-1 * (event.delta // 120), "units")
            else:
                self.mixer_canvas.yview_scroll(-1 * (event.delta // 120), "units")
        self.mixer_canvas.bind("<MouseWheel>", _on_wheel)
        self.mixer_frame.bind("<MouseWheel>",  _on_wheel)

        self.root.protocol("WM_DELETE_WINDOW", self._hide_to_tray)
        self._update_mode_ui()

    def _set_taskbar_icon(self):
        try:
            hwnd = ctypes.windll.user32.GetParent(self.root.winfo_id())
            icon_path = resource_path('shadowbridge_icon.ico')
            icon_handle = ctypes.windll.user32.LoadImageW(
                0, icon_path, 1, 0, 0, 0x00000010 | 0x00000040)
            ctypes.windll.user32.SendMessageW(hwnd, 0x0080, 1, icon_handle)
            ctypes.windll.user32.SendMessageW(hwnd, 0x0080, 0, icon_handle)
        except:
            pass

    def _update_mode_ui(self):
        mode = self.cfg['mode']
        local = get_local_ip()
        if mode == 'gaming':
            self.mode_btn.config(text="[ GAMING PC ]", bg=GREEN2, fg=GREEN,
                                  activebackground="#14532d", activeforeground=GREEN,
                                  font=(FONT_MONO, 8, "bold"))
            dest = self.cfg.get('streaming_ip', '?')
            self.status_ip_label.config(text=f"this: {local}  //  stream: {dest}")
            self.root.title("ShadowBridge — Gaming PC")
        else:
            self.mode_btn.config(text="[ STREAMING PC ]", bg=BLUE2, fg=BLUE,
                                  activebackground="#1e3a8a", activeforeground=BLUE,
                                  font=(FONT_MONO, 8, "bold"))
            dest = self.cfg.get('gaming_ip', '?')
            self.status_ip_label.config(text=f"this: {local}  //  gaming: {dest}")
            self.root.title("ShadowBridge — Streaming PC")

    def _get_device_lists(self):
        """Return (loopbacks, outputs) — re-enumerates at most every 30 seconds."""
        now = time.monotonic()
        cache_age = now - getattr(self, '_dev_cache_ts', 0)
        if not hasattr(self, '_dev_cache') or cache_age > 30:
            try:
                pa = pyaudio.PyAudio()
                self._dev_cache = (get_loopback_devices(pa), get_output_devices(pa))
                pa.terminate()
            except Exception:
                logger.error(f"_get_device_lists failed:\n{traceback.format_exc()}")
                self._dev_cache = ([], [])
            self._dev_cache_ts = now
        return self._dev_cache

    def _refresh_channels(self):
        channels = self._channels()
        logger.info(f"_refresh_channels START — {len(channels)} channel(s)")

        try:
            loopbacks, outputs = self._get_device_lists()
        except Exception:
            logger.error(f"_refresh_channels device list failed:\n{traceback.format_exc()}")
            return

        # Clear the mixer frame
        for w in self.mixer_frame.winfo_children():
            w.destroy()
        self.rows.clear()

        mode = self.cfg.get('mode', 'gaming')
        out_channels = [ch for ch in channels if ch.get('direction') in ('out', 'app')]
        in_channels  = [ch for ch in channels if ch.get('direction') == 'in']
        mic_channels = [ch for ch in channels if ch.get('direction') in ('mic', 'mic-in', 'mic-out')]

        def _build_strip(ch, parent):
            try:
                strip = ChannelRow(
                    parent, ch, loopbacks, outputs,
                    on_remove=self._remove_channel,
                    on_change=self._save_channels,
                    on_refresh=self._refresh_channels,
                    mode=mode,
                )
                strip.pack(side="left", fill="y", padx=(0, 3), pady=4)
                self.rows[ch['id']] = strip
            except Exception:
                logger.error(f"_refresh_channels strip failed '{ch.get('name','?')}':\n{traceback.format_exc()}")

        def _draw_section_label(cv, text, color):
            cv.delete("all")
            h = cv.winfo_height()
            if h < 10:
                cv.after(50, lambda: _draw_section_label(cv, text, color))
                return
            # vertical-rl + rotate(180deg) = bottom-to-top text, angle=90 in canvas
            cv.create_text(10, h // 2, text=text, angle=90,
                           fill=color, font=(FONT_MONO, 8, "bold"), anchor="center")

        def _draw_divider(cv):
            cv.delete("all")
            h = cv.winfo_height()
            if h < 10:
                cv.after(50, lambda: _draw_divider(cv))
                return
            # 1px line at x=14 (14px padding each side), gradient transparent→cyan→transparent
            cx = 14
            for y in range(h):
                frac = y / max(h - 1, 1)
                if frac < 0.30:
                    alpha = frac / 0.30 * 0.35
                elif frac < 0.70:
                    alpha = 0.35
                else:
                    alpha = (1.0 - frac) / 0.30 * 0.35
                r = int(0   * alpha)
                g = int(212 * alpha + 8  * (1 - alpha))
                b = int(232 * alpha + 14 * (1 - alpha))
                cv.create_line(cx, y, cx, y + 1,
                               fill=f"#{r:02x}{g:02x}{b:02x}", width=1)

        def _draw_add_btn(cv, color):
            cv.delete("all")
            w, h = cv.winfo_width(), cv.winfo_height()
            if w < 4 or h < 4:
                cv.after(50, lambda: _draw_add_btn(cv, color))
                return
            cut = 4
            pts = [cut, 0,  w, 0,  w - cut, h,  0, h]
            cv.create_polygon(pts, fill=MIXER_BG, outline=color, width=1)
            cv.create_text(w // 2, h // 2, text="+", fill=color,
                           font=(FONT_ORBITRON, 11, "bold"))

        def _add_section(label, direction, ch_list, color, new_dir=None):
            # new_dir: direction for newly added channels (may differ from the
            # grouping direction used to filter ch_list).
            _new_dir = new_dir if new_dir is not None else direction

            sec = tk.Frame(self.mixer_frame, bg=MIXER_BG)
            sec.pack(side="left", fill="y", padx=(0, 0))

            # Section header column: label + button centered vertically as a group
            hdr = tk.Frame(sec, bg=MIXER_BG)
            hdr.pack(side="left", fill="y", padx=(4, 4), pady=(8, 8))

            # center_f floats in the middle of hdr via expand=True
            center_f = tk.Frame(hdr, bg=MIXER_BG)
            center_f.pack(expand=True, anchor="center")

            # Vertical section label — fixed height so text is legible
            lbl_cv = tk.Canvas(center_f, width=20, height=130,
                                bg=MIXER_BG, highlightthickness=0)
            lbl_cv.pack()
            lbl_cv.bind("<Configure>",
                        lambda e, cv=lbl_cv, t=label, c=color: _draw_section_label(cv, t, c))

            # + button directly below the label
            add_cv = tk.Canvas(center_f, width=22, height=22,
                               bg=MIXER_BG, highlightthickness=0, cursor="hand2")
            add_cv.pack(pady=(6, 0))
            add_cv.bind("<Configure>", lambda e, cv=add_cv, c=color: _draw_add_btn(cv, c))
            add_cv.bind("<Button-1>",  lambda e, d=_new_dir: self._add_channel(d))
            add_cv.after(80, lambda cv=add_cv, c=color: _draw_add_btn(cv, c))

            # Strips container
            strips_f = tk.Frame(sec, bg=MIXER_BG)
            strips_f.pack(side="left", fill="y", pady=(8, 8))
            for ch in ch_list:
                _build_strip(ch, strips_f)
            return sec

        def _add_divider():
            # Total width = 14px pad + 1px line + 14px pad = 29px
            div = tk.Canvas(self.mixer_frame, width=29, bg=MIXER_BG, highlightthickness=0)
            div.pack(side="left", fill="y")
            div.bind("<Configure>", lambda e, cv=div: _draw_divider(cv))

        _add_section("OUTGOING",   "out", out_channels, GREEN)
        _add_divider()
        _add_section("INCOMING",   "in",  in_channels,  BLUE)
        _add_divider()
        _add_section("MIC INPUTS", "mic", mic_channels, AMBER, new_dir="mic-in")

        logger.info(f"_refresh_channels DONE — {len(self.rows)} strip(s)")
        self.mixer_canvas.update_idletasks()
        self.mixer_canvas.configure(scrollregion=self.mixer_canvas.bbox("all"))

    def _save_channels(self):
        """Debounced save — batches rapid calls into a single disk write after 400 ms."""
        if hasattr(self, '_save_after_id') and self._save_after_id:
            try:
                self.root.after_cancel(self._save_after_id)
            except Exception:
                pass
        self._save_after_id = self.root.after(400, self._flush_save)

    def _flush_save(self):
        self._save_after_id = None
        mode = self.cfg.get('mode', '?')
        channels = self.cfg.get(f'{mode}_channels', [])
        snapshot = [(c.get('name', '?'), c.get('direction', '?')) for c in channels]
        logger.info(f"_flush_save: writing config — mode={mode}, channels={snapshot}")
        save_config(self.cfg)
        logger.info("_flush_save: done")
        # Push full STATUS so Stream Deck reflects any color/icon/config changes
        if self._ws_server:
            self._ws_server.push_status_full()

    def _add_channel(self, direction="out"):
        if self.engine.running:
            logger.warning("Stop all streams before adding channels.")
            return
        channels = self._channels()
        new_ch = {
            "id":        str(uuid.uuid4()),
            "name":      f"Channel {len(channels) + 1}",
            "direction": direction,
            "device":    "",
            "port":      get_next_port(channels),
            "volume":    100,
            "enabled":   True
        }
        channels.append(new_ch)
        save_config(self.cfg)
        self._refresh_channels()
        logger.info(f"Added channel: {new_ch['name']}")

    def _remove_channel(self, ch_id):
        if self.engine.running:
            logger.warning("Stop all streams before removing channels.")
            return
        mode = self.cfg['mode']
        self.cfg[f'{mode}_channels'] = [c for c in self._channels() if c['id'] != ch_id]
        save_config(self.cfg)
        self._refresh_channels()
        logger.info("Channel removed.")

    def _switch_mode(self):
        if self.engine.running:
            logger.warning("Stop all streams before switching mode.")
            return
        self.cfg['mode'] = 'streaming' if self.cfg['mode'] == 'gaming' else 'gaming'
        save_config(self.cfg)
        self._update_mode_ui()
        self._refresh_channels()
        logger.info(f"Switched to {self.cfg['mode'].upper()} PC mode.")

    def _open_settings(self):
        def on_save(new_cfg):
            self.cfg.update(new_cfg)
            save_config(self.cfg)
            self._update_mode_ui()
            logger.success("Settings saved.")
        SettingsPanel(self.root, self.cfg, on_save)

    def _start(self, send_remote=True):
        self._shutting_down = False   # clear before guard so callbacks re-enable on next start
        self._user_stopped  = False
        if self.engine.running or self._streams_active:
            logger.info(f"_start() called but blocked by guard (engine.running={self.engine.running}, _streams_active={self._streams_active}, send_remote={send_remote})")
            return
        # Guard passed — this log confirms _start() is actually executing.
        logger.info(f"_start(): guards passed, send_remote={send_remote} — proceeding.")
        if not send_remote:
            logger.info("CMD:START: _start() executing — streams not yet active, proceeding")
        if send_remote and not self._discovery.is_peer_connected():
            logger.warning("Peer not connected — remote start command may not be received.")

        logger.info("_start(): step 1 — setting _streams_active = True")
        self._streams_active = True
        self._poll_log()
        self._update_levels()
        self._ws_push_loop()

        logger.info("_start(): step 2 — syncing peer status bar")
        peer_ip, peer_mode = self._discovery.get_peer_info()
        if peer_ip:
            self._update_peer_status(True, peer_ip, peer_mode)

        logger.info("_start(): step 3 — updating buttons")
        self._btn_start_enabled = False
        self._btn_stop_enabled  = True
        self._redraw_start()
        self._redraw_stop()

        logger.info(f"_start(): step 4 — calling engine.start(), dest={self._dest_ip()}, mode={self.cfg['mode']}, channels={len(self._channels())}")
        self.engine.start(
            self._channels(), self._dest_ip(), mode=self.cfg['mode'],
            sample_rate=int(self.cfg.get('sample_rate', 48000)),
            buffer_size=int(self.cfg.get('buffer_size', 1024)),
        )

        if send_remote:
            logger.info("_start(): step 5 — sending CMD:START to peer.")
            self._discovery.send_command(self._dest_ip(), 'START')
        else:
            logger.info("_start(): step 5 — send_remote=False, NOT sending CMD:START (remote-triggered).")

        if self._ws_server:
            self._ws_server.push_status_full()
        logger.info("_start(): all steps complete.")

    def _stop(self, send_remote=True):
        logger.info(f"_stop(): called, send_remote={send_remote}")
        if send_remote:
            self._user_stopped = True
        # Step 1 — raise shutdown flag; blocks audio-engine callbacks from
        # touching the UI while we tear down. Discovery keeps running so peer
        # callbacks are re-enabled as soon as _shutting_down is cleared below.
        self._shutting_down  = True
        self._streams_active = False
        # Step 2 — send remote command (only when locally triggered).
        try:
            if send_remote:
                logger.info("_stop(): sending CMD:STOP to peer.")
                self._discovery.send_command(self._dest_ip(), 'STOP')
            else:
                logger.info("_stop(): send_remote=False — NOT sending CMD:STOP (remote-triggered).")
        except Exception:
            logger.error(f"_stop() CRASH at send_command:\n{traceback.format_exc()}")
        # Step 3 — update Start/Stop buttons.
        try:
            self._btn_start_enabled = True
            self._btn_stop_enabled  = False
            self._redraw_start()
            self._redraw_stop()
        except Exception:
            logger.error(f"_stop() CRASH at btn redraw:\n{traceback.format_exc()}")
        # Step 4 — reset every channel row.
        try:
            for row in self.rows.values():
                row.set_status(STATUS_IDLE)
                row.set_level(0)
        except Exception:
            logger.error(f"_stop() CRASH at row reset:\n{traceback.format_exc()}")
        # Step 5 — stop audio engine in background (PortAudio terminate is slow).
        try:
            logger.info("_stop(): launching engine.stop() background thread.")
            threading.Thread(target=self.engine.stop, daemon=True).start()
        except Exception:
            logger.error(f"_stop() CRASH at engine.stop() thread launch:\n{traceback.format_exc()}")
        # Step 6 — clear shutdown flag so discovery peer callbacks re-enable.
        # Discovery never stopped, so the peer status bar stays live.
        self._shutting_down = False
        if self._ws_server:
            self._ws_server.push_status_full()
        logger.info("_stop(): all stop steps completed.")

    def _on_status_change(self, ch_id, status):
        if self._shutting_down or not self._streams_active or not self._app_alive:
            return
        self.root.after(0, lambda: self._apply_status_change(ch_id, status))

    def _apply_status_change(self, ch_id, status):
        if self._shutting_down or not self._streams_active:
            return
        if ch_id in self.rows:
            self.rows[ch_id].set_status(status)
        if self._ws_server:
            self._ws_server.push_status()
        if status in (STATUS_ERROR, STATUS_RECONNECTING):
            logger.info(f"Channel error — notify_errors={self.cfg.get('notify_errors', False)}")
        if self.cfg.get('notify_errors', False) and status in (STATUS_ERROR, STATUS_RECONNECTING):
            now = time.time()
            if now - self._notif_last_sent.get(ch_id, 0) >= 30:
                self._notif_last_sent[ch_id] = now
                ch = self.engine.channel_map.get(ch_id, {})
                name = ch.get('name', ch_id)
                if status == STATUS_ERROR:
                    logger.info("Attempting to show channel error notification")
                    self._toast('ShadowBridge — Channel Error',
                                f'Channel {name} encountered an error and stopped')
                else:
                    logger.info("Attempting to show channel reconnecting notification")
                    self._toast('ShadowBridge',
                                f'Channel {name} dropped — reconnecting...')

    def _on_level(self, ch_id, level):
        if self._shutting_down or not self._streams_active or not self._app_alive:
            return
        if ch_id in self.rows:
            self.rows[ch_id].set_level(level)

    def _on_tk_exception(self, exc_type, exc_value, exc_tb):
        msg = "".join(traceback.format_exception(exc_type, exc_value, exc_tb))
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        logger.error(f"tkinter callback exception:\n{msg}")
        _write_crash_log(f"\n[{timestamp}] TKINTER CALLBACK EXCEPTION:\n{msg}")

    def _poll_log(self):
        if not self._streams_active:
            return  # loop cancelled; _start() will restart it
        while not logger.ui_queue.empty():
            try:
                color, msg = logger.ui_queue.get_nowait()
                ts = datetime.datetime.now().strftime("%H:%M:%S")
                line = f"[{ts}] {msg}\n"
                self.text_log.config(state=tk.NORMAL)
                self.text_log.insert(tk.END, line, color)
                self.text_log.config(state=tk.DISABLED)
                if self._log_popup_text is not None:
                    try:
                        self._log_popup_text.config(state=tk.NORMAL)
                        self._log_popup_text.insert(tk.END, line, color)
                        self._log_popup_text.see(tk.END)
                        self._log_popup_text.config(state=tk.DISABLED)
                    except:
                        self._log_popup_text = None
            except:
                pass
        self.root.after(100, self._poll_log)

    def _update_levels(self):
        if not self._streams_active:
            return  # loop cancelled; _start() will restart it
        for row in self.rows.values():
            row.update_level()
        self.root.after(40, self._update_levels)

    def _ws_push_loop(self):
        """Push compact STATUS to WS clients every 250 ms while streams are active (live level meters)."""
        if not self._streams_active:
            return  # loop cancelled; _start() will restart it
        if self._ws_server:
            self._ws_server.push_status()
        self.root.after(250, self._ws_push_loop)

    def _copy_log(self):
        content = self.text_log.get("1.0", tk.END)
        self.root.clipboard_clear()
        self.root.clipboard_append(content)
        logger.info("Log copied to clipboard.")

    def _open_log_popup(self):
        popup = tk.Toplevel(self.root)
        popup.title("Log — ShadowBridge")
        popup.geometry("700x420")
        popup.configure(bg=BG)
        popup.resizable(True, True)

        hdr = tk.Frame(popup, bg=BG)
        hdr.pack(fill="x", padx=16, pady=(14, 4))
        tk.Label(hdr, text="LOG", font=("Segoe UI", 12, "bold"),
                 bg=BG, fg=TEXT).pack(side="left")
        tk.Button(hdr, text="open log folder", font=("Segoe UI", 9),
                  bg=BG3, fg=MUTED, relief="flat", bd=0,
                  cursor="hand2", command=lambda: os.startfile(LOG_DIR),
                  padx=6, pady=2).pack(side="right")
        tk.Button(hdr, text="copy log", font=("Segoe UI", 9),
                  bg=BG3, fg=MUTED, relief="flat", bd=0,
                  cursor="hand2", command=self._copy_log,
                  padx=6, pady=2).pack(side="right", padx=(0, 4))
        tk.Frame(popup, height=1, bg=BORDER).pack(fill="x", padx=16, pady=(0, 8))

        log_widget = scrolledtext.ScrolledText(
            popup, font=("Segoe UI", 9),
            state=tk.DISABLED, bg=BG2, fg=MUTED,
            relief="flat", bd=0, padx=10, pady=6,
            insertbackground=TEXT
        )
        log_widget.pack(fill="both", expand=True, padx=16, pady=(0, 16))
        log_widget.tag_config("green",  foreground=GREEN)
        log_widget.tag_config("red",    foreground=RED)
        log_widget.tag_config("amber",  foreground=AMBER)
        log_widget.tag_config("normal", foreground=MUTED)

        existing = self.text_log.get("1.0", tk.END)
        if existing.strip():
            log_widget.config(state=tk.NORMAL)
            log_widget.insert("1.0", existing)
            log_widget.see(tk.END)
            log_widget.config(state=tk.DISABLED)

        self._log_popup_text = log_widget

        def on_close():
            self._log_popup_text = None
            popup.destroy()

        popup.protocol("WM_DELETE_WINDOW", on_close)

    def _toast(self, title, message):
        if not NOTIF_AVAILABLE:
            logger.warning("_toast: winotify not available — notification suppressed.")
            return
        icon = resource_path('shadowbridge_icon.ico')
        def _fire():
            try:
                n = _WiNotification(
                    app_id='ShadowBridge',
                    title=title,
                    msg=message,
                    icon=icon,
                    duration='short',
                )
                n.show()
            except Exception:
                logger.error(f"_toast('{title}'): winotify error:\n{traceback.format_exc()}")
        threading.Thread(target=_fire, daemon=True).start()

    def _bring_to_front(self):
        if self.root.state() == 'withdrawn':
            self.root.deiconify()
        self.root.lift()
        self.root.focus_force()

    def _start_instance_listener(self):
        if _instance_server_sock is None:
            return
        def _listen():
            while self._app_alive:
                try:
                    conn, _ = _instance_server_sock.accept()
                    try:
                        data = conn.recv(64).decode('utf-8', errors='ignore').strip()
                    finally:
                        conn.close()
                    if data == 'SHOW':
                        self.root.after(0, self._bring_to_front)
                except Exception:
                    break
        threading.Thread(target=_listen, daemon=True).start()

    def _hide_to_tray(self):
        self.root.withdraw()
        logger.info("Minimized to tray.")

    def _toggle_window(self):
        if self.root.state() == 'withdrawn':
            self.root.deiconify()
            self.root.lift()
            self.root.focus_force()
        else:
            self.root.withdraw()

    def _quit_app(self):
        self._app_alive = False
        if self.engine.running:
            self.engine.stop()
        try:
            self._discovery.stop()
        except:
            pass
        try:
            self._tray_icon.stop()
        except:
            pass
        try:
            if _instance_server_sock:
                _instance_server_sock.close()
        except:
            pass
        self.root.destroy()

    def _setup_tray(self):
        if not TRAY_AVAILABLE:
            return
        try:
            icon_path = resource_path('shadowbridge_icon.ico')
            if os.path.exists(icon_path):
                img = PILImage.open(icon_path).resize((64, 64))
            else:
                img = PILImage.new('RGBA', (64, 64), color=(74, 222, 128, 255))
        except:
            try:
                img = PILImage.new('RGBA', (64, 64), color=(74, 222, 128, 255))
            except:
                return

        def on_show_hide(icon, item):
            self.root.after(0, self._toggle_window)

        def on_quit(icon, item):
            self.root.after(0, self._quit_app)

        menu = pystray.Menu(
            pystray.MenuItem("Show / Hide", on_show_hide, default=True),
            pystray.MenuItem("Quit", on_quit),
        )
        self._tray_icon = pystray.Icon("ShadowBridge", img, "ShadowBridge", menu)
        threading.Thread(target=self._tray_icon.run, daemon=True).start()
        logger.info("System tray initialized.")

    def _get_announce_data(self):
        channels = [{'name': ch['name'], 'port': ch['port']} for ch in self._channels()]
        return {
            'app':      'ShadowBridge',
            'version':  VERSION,
            'mode':     self.cfg['mode'],
            'ip':       get_local_ip(),
            'channels': channels,
        }

    def _on_peer_found(self, peer_ip, peer_mode):
        if self._shutting_down or not self._app_alive:
            return
        self.root.after(0, lambda: self._handle_peer_found(peer_ip, peer_mode))

    def _on_peer_lost(self):
        if self._shutting_down or not self._app_alive:
            return
        self.root.after(0, self._handle_peer_lost)

    def _on_port_sync(self, peer_channels):
        if not self._streams_active or not self._app_alive:
            return
        self.root.after(0, lambda: self._apply_port_sync(peer_channels))

    def _handle_peer_found(self, peer_ip, peer_mode):
        our_mode = self.cfg.get('mode', 'gaming')
        if peer_mode and peer_mode != our_mode:
            ip_key = f"{peer_mode}_ip"
            if self.cfg.get(ip_key) != peer_ip:
                self.cfg[ip_key] = peer_ip
                save_config(self.cfg)
                self._update_mode_ui()
        logger.success(f"Peer discovered: {peer_mode or 'unknown'} PC at {peer_ip}")
        self._update_peer_status(True, peer_ip, peer_mode)
        if self._ws_server:
            self._ws_server.push_status_full()
        logger.info(f"Peer found — notify_peer={self.cfg.get('notify_peer', False)}")
        if self.cfg.get('notify_peer', False):
            label = f"{peer_mode} PC" if peer_mode else "Peer"
            logger.info("Attempting to show peer notification")
            self._toast('ShadowBridge', f'{label} connected — {peer_ip}')
        if (self.cfg.get('auto_start', False)
                and not self._streams_active
                and not self.engine.running
                and not self._user_stopped):
            logger.info("auto_start: peer detected, starting streams automatically.")
            self._start(send_remote=True)

    def _handle_peer_lost(self):
        logger.warning("Peer connection lost — searching...")
        self._update_peer_status(False, None, None)
        if self._ws_server:
            self._ws_server.push_status()
        logger.info(f"Peer lost — notify_peer={self.cfg.get('notify_peer', False)}")
        if self.cfg.get('notify_peer', False):
            logger.info("Attempting to show peer notification")
            self._toast('ShadowBridge', 'Streaming PC disconnected — searching for peer...')

    def _apply_port_sync(self, peer_channels):
        if not self._streams_active:
            return
        my_channels = self._channels()
        peer_port_map = {ch['name']: ch['port'] for ch in peer_channels}
        changed_ids = []
        for my_ch in my_channels:
            if my_ch['name'] in peer_port_map:
                new_port = peer_port_map[my_ch['name']]
                if my_ch['port'] != new_port:
                    my_ch['port'] = new_port
                    changed_ids.append(my_ch['id'])
        if not changed_ids:
            logger.info("Port sync: no changes.")
            return
        save_config(self.cfg)
        logger.info(f"Port sync: updated {len(changed_ids)} channel(s) — {changed_ids}")
        # Restart only the affected streams; never rebuild the UI.
        if self.engine.running:
            for ch in my_channels:
                if ch['id'] in changed_ids:
                    self.engine.stop_channel(ch['id'])
                    if ch.get('enabled', True):
                        self.engine.start_channel(ch)

    def _toggle_channel(self, ch_id):
        ch = next((c for c in self._channels() if c['id'] == ch_id), None)
        if ch is None:
            logger.warning(f"TOGGLE_CHANNEL: unknown id {ch_id}")
            return
        ch['enabled'] = not ch.get('enabled', True)
        save_config(self.cfg)
        if ch_id in self.rows:
            self.rows[ch_id]._apply_enable_state()
        if self.engine.running:
            if ch['enabled']:
                self.engine.start_channel(ch)
            else:
                self.engine.stop_channel(ch_id)
        if self._ws_server:
            self._ws_server.push_status()
        logger.info(f"Channel '{ch['name']}' toggled {'ON' if ch['enabled'] else 'OFF'} via WS.")

    def _set_volume(self, ch_id, vol):
        known = [(c['id'], c['name']) for c in self._channels()]
        logger.info(f"_set_volume: looking for id={ch_id!r} among {len(known)} channels: {known}")
        ch = next((c for c in self._channels() if c['id'] == ch_id), None)
        if ch is None:
            logger.warning(f"SET_VOLUME: id {ch_id!r} not found. Known IDs: {[k[0] for k in known]}")
            return
        old_vol = ch.get('volume', 100)
        ch['volume'] = vol
        save_config(self.cfg)
        engine_updated = False
        if self.engine.running and ch_id in self.engine.channel_map:
            self.engine.channel_map[ch_id]['volume'] = vol
            engine_updated = True
        if ch_id in self.rows:
            try:
                self.rows[ch_id].set_volume(vol)
            except Exception:
                logger.error(f"SET_VOLUME: row update failed for '{ch['name']}':\n{traceback.format_exc()}")
        if self._ws_server:
            self._ws_server.push_status()
        logger.success(f"SET_VOLUME applied: '{ch['name']}' {old_vol}% → {vol}% (engine_updated={engine_updated})")

    def _on_remote_command(self, cmd, sender_ip):
        # Called on the discovery listener background thread — delegate immediately.
        self._handle_remote_command(cmd, sender_ip)

    def _handle_remote_command(self, cmd, sender_ip):
        # Called from the discovery background thread.
        # Only schedule UI work via root.after — never call _start/_stop directly here.
        try:
            if not self._app_alive:
                return
            if cmd == 'START':
                logger.info(f"CMD:START received from {sender_ip} — scheduling _start(send_remote=False) on main thread.")
                self.root.after(0, lambda: self._start(send_remote=False))
            elif cmd == 'STOP':
                logger.info(f"CMD:STOP received from {sender_ip} — scheduling _stop(send_remote=False) on main thread.")
                self.root.after(0, lambda: self._stop(send_remote=False))
            else:
                logger.warning(f"Unknown remote command '{cmd}' from {sender_ip} — ignored.")
        except Exception:
            logger.error(f"_handle_remote_command('{cmd}') error:\n{traceback.format_exc()}")

    def _update_peer_status(self, connected, peer_ip, peer_mode):
        if connected:
            self.peer_dot.config(fg=GREEN)
            mode_str = f"{peer_mode} pc" if peer_mode else "peer"
            self.peer_label.config(
                text=f"{mode_str}   {peer_ip}   connected", fg=GREEN)
        else:
            self.peer_dot.config(fg=MUTED)
            self.peer_label.config(text="searching for peer...", fg=MUTED)

    def run(self):
        logger.success(f"ShadowBridge v{VERSION} started.")
        logger.info(f"Mode: {self.cfg['mode'].upper()} PC")
        logger.info(f"This PC: {get_local_ip()}")
        logger.info(f"Config: {CFG_FILE}")
        logger.info(f"Logs:   {LOG_DIR}")
        self._start_instance_listener()
        if self._ws_server:
            self._ws_server.start()
        if self.cfg.get('start_minimized', False):
            self.root.after(0, self._hide_to_tray)
        # DEBUG — startup notification test; remove once confirmed working
        logger.info(f"NOTIF_AVAILABLE={NOTIF_AVAILABLE}")
        self.root.after(2000, lambda: self._toast('ShadowBridge', 'Notifications are working'))
        try:
            self.root.mainloop()
        except Exception:
            logger.error(f"tkinter mainloop crashed:\n{traceback.format_exc()}")
            sys.exit(1)


if __name__ == "__main__":
    _enforce_single_instance()
    app = ShadowBridgeApp()
    app.run()